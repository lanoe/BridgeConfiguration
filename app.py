from flask import Flask, render_template, redirect, url_for, request
from flask_socketio import SocketIO
from gevent import monkey
from context import AppContext
import threading, webbrowser
import subprocess
import os
from os import listdir

monkey.patch_all()

# App declaration
app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret_of_the_year'
socketio = SocketIO(app)
socketio.async_mode = 'eventlet'
#app.debug = True

context = None
if app.debug:
  print ("Launched in debug mode")
else:
  print ("Launched in production mode")

context = AppContext('prod.cfg')

# Index Route
@app.route('/', methods=['GET'])
def index():
  return render_template('index.html')

# Login form if not logged in, message otherwise
@app.route('/loginform', methods=['GET'])
def login_form():
  if context.dandelion_token is None:
    servers_file = open("config/dandelion_server_list.txt", "r")
    servers = servers_file.readlines()
    return render_template('dandelion_form.html', option_list=servers)
  else:
    return render_template('dandelion_logged.html', server=context.mqtt_ip_address)

# Firmware list
@app.route('/firmware_list', methods=['GET'])
def firmware_list():
  firmware_list = (f for f in listdir(context.firmware_dir_path) if f.endswith('.hex'))
  return render_template('list.html', option_list=firmware_list)

# Tests list
@app.route('/tests_list', methods=['GET'])
def tests_list():
  tests_list = (f for f in listdir(context.tests_script_dir) if f.endswith('.sh'))
  return render_template('test_form.html', test_list=tests_list)

# Logs in Dandelion
@app.route('/login', methods=['POST'])
def login():
  request_json = request.get_json()
  requested_param = ["server", "username", "password"]
  for param in requested_param:
    if param not in request_json:
      return "{0} parameter missing, please check your inputs".format(param), 400, {'Content-Type': 'text/plain'}

  server = request.get_json()['server']
  username = request.get_json()['username']
  password = request.get_json()['password']

  if not server:
    return "Missing 'server' to login, please check your inputs", 400, { 'Content-Type': 'text/plain' }
  if not username:
    return "Missing 'username' to login, please check your inputs", 400, { 'Content-Type': 'text/plain' }
  if not password:
    return "Missing 'password' to login, please check your inputs", 400, { 'Content-Type': 'text/plain' }

  context.ws_url = "https://" + server.rstrip() + "/api"
  context.mqtt_ip_address = server.rstrip()

  print ("ws_url=",context.ws_url)

  # Trigger login via AppContext
  status = context.login(username, password)
  if status == 200:
    return "Log in Dandelion successfully", 200, { 'Content-Type': 'text/plain' }
  else:
    return "Login failed, try again", 403, { 'Content-Type': 'text/plain' }

# Logout from Dandelion
@app.route('/logout', methods=['POST'])
def logout():
  context.logout()
  return "Logout from Dandelion successfully", 200, { 'Content-Type': 'text/plain' }

# Launches configuration route
@app.route('/config', methods=['POST'])
def launch():
  request_json = request.get_json()

  requested_param = ["guid", "configure_vpn", "use_amber_dongle", "omPollingInt", "amber_is_serial", "config_translator", "serial_number"]

  for param in requested_param:
    if param not in request_json:
      return "{0} parameter missing, please check your inputs".format(param), 400, {'Content-Type': 'text/plain'}

  guid = request.get_json()['guid']
  configure_vpn = request.get_json()['configure_vpn']
  use_amber_dongle = request.get_json()['use_amber_dongle']
  om_polling_int = request.get_json()['omPollingInt']
  amber_is_serial = request.get_json()['amber_is_serial']
  enable_translator = request.get_json()['config_translator']
  serial_number = request.get_json()['serial_number']

  print ("guid =",guid)
  print ("configure_vpn =",configure_vpn)
  print ("use_amber_dongle =",use_amber_dongle)
  print ("om_polling_int =",om_polling_int)
  print ("amber_is_serial =",amber_is_serial)
  print ("enable_translator =",enable_translator)
  print ("serial_number =",serial_number)

  if enable_translator:
    if not serial_number:
      return "Missing 'Serial Number', please check your inputs", 400, { 'Content-Type': 'text/plain' }
  else:
    if not guid:
      return "Missing 'Bridge GUID', please check your inputs", 400, { 'Content-Type': 'text/plain' }

  # Run configuration
  context.bridge_guid = guid
  context.enable_amber_dongle = use_amber_dongle
  context.om_polling_interval = om_polling_int
  context.configure_vpn = configure_vpn

  if enable_translator:
    context.serial_number = serial_number
  else:
    context.serial_number = None

  if not enable_translator and amber_is_serial:
    context.amber_port = "/dev/ttymxc0"
  else:
    context.amber_port = "/dev/dongle_amber"

  if not enable_translator and not context.is_logged_in(context.ws_url):
    return "Please connect to Dandelion", 403
  elif not context.is_ready():
    return "Missing parameters", 400
  else:
    if enable_translator:
      board_type="BLETranslator"
    else:
      board_type="Bridge"
      # Request Serial Number
      print('Get Bridge Serial Number ...')
      status = context.get_bridge_info()
      if status != 200:
        return "Get Bridge information failed, try again", 403, { 'Content-Type': 'text/plain' }

    config_command = [context.config_path, board_type, context.serial_number]

    if configure_vpn:
      config_command.append("true")

    print ("command {0}".format(config_command))

    config_done = False

    context.save_bridge_config()

    try:
      socketio.emit('config-log', {'data': "{0}\n\r".format(" ".join(config_command))}, namespace='/logs')
      socketio.sleep(0)
      # Launch the config command action
      process = subprocess.Popen(" ".join(config_command), shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
      # wait for logs and program end
      char = ""
      last_line = ""
      time_buffer = 0
      while process.poll() is None or char != "" or time_buffer < 4:
        char = process.stdout.read(1)
        if char != "\n" and char != "\r":
          last_line += char
        if "Configuration done !" in last_line :
          config_done = True
        if char == "\n":
          last_line = ""
          char = "\n\r"
        socketio.emit('config-log', {'data': "{0}".format(char)}, namespace='/logs')
        socketio.sleep(0)
        if process.poll() is not None and char == "":
          time_buffer += 1
          socketio.sleep(0.25)
      if config_done == True:
        return "Bridge configuration finished successfully", 200, {'Content-Type': 'text/plain'}
      else:
        return "Error while configuring the bridge !", 400, {'Content-Type': 'text/plain'}

    except Exception as e:
      socketio.emit('config-log', {'data': "Error while configuring the bridge ({0})\n\r".format(e)}, namespace='/logs')
      socketio.sleep(0)
      return "Error while configuring the bridge ({0})\n\r".format(e), 400, {'Content-Type': 'text/plain'}


# Launches emmc or mSATA flash actions
@app.route('/flash', methods=['POST'])
def flash():
  request_json = request.get_json()

  requested_param = ["image_path", "encrypt", "fuseBootOnEmmc", "fuseBootOnSDcard"]

  for param in requested_param:
    if param not in request_json:
      return "{0} parameter missing, please check your inputs".format(param), 400, {'Content-Type': 'text/plain'}

  image_path = request_json['image_path']
  encrypt = request_json['encrypt']
  fuseBootOnEmmc = request_json['fuseBootOnEmmc']
  fuseBootOnSDcard = request_json['fuseBootOnSDcard']

  flash_command = [context.emmc_flash_path, image_path]

  if not encrypt :
    flash_command.append("no_encryption")

  if fuseBootOnEmmc:
    flash_command.append("fuse_boot_on_emmc")

  if fuseBootOnSDcard:
    flash_command.append("fuse_boot_on_sdcard")

  print ("command {0}".format(flash_command))

  flash_done = False

  try:
    socketio.emit('flash-log', {'data': "{0}\n\r".format(" ".join(flash_command))}, namespace='/logs')
    socketio.sleep(0)
    # Launch the flash command action
    process = subprocess.Popen(" ".join(flash_command), shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    # wait for logs and program end
    char = ""
    last_line = ""
    time_buffer = 0
    while process.poll() is None or char != "" or time_buffer < 4:
      char = process.stdout.read(1)
      if char != "\n" and char != "\r":
          last_line += char
      if "ready !" in last_line :
        flash_done = True
      if char == "\n":
        last_line = ""
        char = "\n\r"
      socketio.emit('flash-log', {'data': "{0}".format(char)}, namespace='/logs')
      socketio.sleep(0)
      if process.poll() is not None and char == "":
        time_buffer += 1
        socketio.sleep(0.25)
    if flash_done == True:
      return "Emmc flash finished successfully", 200, {'Content-Type': 'text/plain'}
    else:
      return "Error while flashing the system !", 400, {'Content-Type': 'text/plain'}

  except Exception as e:
    socketio.emit('flash-log', {'data': "Error while flashing the system ({0})\n\r".format(e)}, namespace='/logs')
    socketio.sleep(0)
    return "Error while flashing the system ({0})\n\r".format(e), 400, {'Content-Type': 'text/plain'}

# Launches emmc or mSATA flash actions
@app.route('/flashMaster', methods=['POST'])
def flash_master():
  request_json = request.get_json()

  requested_param = ["firmware_file_name"]

  for param in requested_param:
    if param not in request_json:
      return "{0} parameter missing, please check your inputs".format(param), 400, {'Content-Type': 'text/plain'}

  firmware_file_path = context.firmware_dir_path+"/"+request.get_json()['firmware_file_name']

  flash_command = ["python", context.openocd_flash_utility+"/main.py", firmware_file_path]

  print ("command {0}".format(flash_command))

  try:
    socketio.emit('flashmaster-log', {'data': "{0}\n\r".format(" ".join(flash_command))}, namespace='/logs')
    socketio.sleep(0)
    # Launch the flash command action
    process = subprocess.Popen(flash_command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    # wait for logs and program end
    char = ""
    time_buffer = 0
    while process.poll() is None or char != "" or time_buffer < 4:
      char = process.stdout.read(1)
      if char == "\n":
        char = "\n\r"
      socketio.emit('flashmaster-log', {'data': "{0}".format(char)}, namespace='/logs')
      socketio.sleep(0)
      if process.poll() is not None and char == "":
        time_buffer += 1
        socketio.sleep(0.25)

    return "Flash Master finished successfully", 200, {'Content-Type': 'text/plain'}

  except Exception as e:
    socketio.emit('flashmaster-log', {'data': "Error while flashing the Master ({0})\n\r".format(e)}, namespace='/logs')
    socketio.sleep(0)
    return "Error while flashing the Master ({0})\n\r".format(e), 400, {'Content-Type': 'text/plain'}


# Launches test
@app.route('/launch_all_tests', methods=['POST'])
def launch_all_tests():
  tests_list = request.get_json()
  for f in listdir(context.tests_script_dir) :
    if f in tests_list.keys():
      try:
        success = execute_test(f, tests_list[f])
        socketio.emit('alert-state', {"test_name":f, "state":success}, namespace='/alert')
        if success == False :
          return "Error with the test '{0}'".format(f), 400, {'Content-Type': 'text/plain'}
      except Exception as e:
        return "Error while launching test ({0})".format(e), 400, {'Content-Type': 'text/plain'}

  return "launching tests finished successfully", 200, {'Content-Type': 'text/plain'}

# Launches test
@app.route('/launch_test', methods=['POST'])
def launch_test():
  request_json = request.get_json()

  requested_param = ["test_name", "params"]

  for param in requested_param:
    if param not in request_json:
      return "{0} parameter missing, please check your inputs".format(param), 400, {'Content-Type': 'text/plain'}

  try:
    success = execute_test(request_json["test_name"], request_json["params"])
    socketio.emit('alert-state', {"test_name":request_json["test_name"], "state":success}, namespace='/alert')
    if success == False :
      return "Error with the test '{0}'".format(request_json["test_name"]), 400, {'Content-Type': 'text/plain'}

  except Exception as e:
    return "Error while launching test ({0})".format(e), 400, {'Content-Type': 'text/plain'}

  return "launching test '{0}' finished successfully".format(request_json["test_name"]), 200, {'Content-Type': 'text/plain'}

def execute_test(test_name, params):
  test_file_path = context.tests_script_dir + test_name

  test_command = ["/bin/bash", test_file_path]
  for param in params:
      test_command.append(param);

  socketio.emit('test-log', {'data': "LAUNCH TEST {0}\n\r".format(test_name)}, namespace='/logs')
  socketio.sleep(0)

  print ("command {0}".format(test_command))

  success = True
  try:
    socketio.emit('test-log', {'data': "{0}\n\r".format(" ".join(test_command))}, namespace='/logs')
    socketio.sleep(0)
    # Launch the flash command action
    process = subprocess.Popen(test_command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    # wait for logs and program end
    char = ""
    last_line = ""
    time_buffer = 0
    while process.poll() is None or char != "" or time_buffer < 4:
      char = process.stdout.read(1)
      if char != "\n" and char != "\r":
          last_line += char
      if "Failed" in last_line :
        success = False
      if char == "\n":
        last_line = ""
        char = "\n\r"
      socketio.emit('test-log', {'data': "{0}".format(char)}, namespace='/logs')
      socketio.sleep(0)
      if process.poll() is not None and char == "":
        time_buffer += 1
        socketio.sleep(0.25)
    socketio.emit('test-log', {'data': "END TEST {0}\n\r".format(test_name)}, namespace='/logs')
    socketio.sleep(0)
  except Exception as e:
    socketio.emit('test-log', {'data': "Error while launching test ({0})\n\r".format(e)}, namespace='/logs')
    socketio.sleep(0)
    raise(e)

  return success

# Handles wrong URLs
@app.errorhandler(404)
def not_found(e):
  return redirect(url_for('index'))

# SocketIO handlers
@socketio.on('connect', namespace='/logs')
def connect():
  print('Client connected')

@socketio.on('disconnect', namespace='/logs')
def disconnect():
  print('Client disconnected')

if __name__ == "__main__":
  if app.debug:
    url = "http://localhost:5000"
    threading.Timer(1.25, lambda: webbrowser.open(url)).start()
    socketio.run(app, host='0.0.0.0', port=5000)
  else:
    url = "http://localhost:4242"
    threading.Timer(1.25, lambda: webbrowser.open(url)).start()
    socketio.run(app, host='0.0.0.0', port=4242)
