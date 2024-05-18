import requests
import json
import configparser

class AppContext:
  def __init__(self, config_file):
    self.reset_context()
    self.load_config(config_file)

  # Reset context (mainly for init)
  def reset_context(self):
    self.ws_url = None
    self.logged_server = None
    self.dandelion_token = None
    self.bridge_guid = None
    self.jwt = None
    self.mqtt_ip_address = None
    self.enable_amber_dongle = None
    self.om_polling_interval = None
    self.amber_port = None
    self.configure_vpn = None
    self.serial_number = None

  # Load configuration
  def load_config(self, config_file):
    self.config_parser = configparser.ConfigParser()
    self.config_parser.read('config/%s' % config_file)
    self.config_path = self.config_parser.get(section="config", option="bridge_config_path")
    self.emmc_flash_path = self.config_parser.get(section="flash", option="emmc_flash_path")
    self.firmware_dir_path = self.config_parser.get(section="flash", option="firmware_dir_path")
    self.openocd_flash_utility = self.config_parser.get(section="flash", option="openocd_flash_utility_path")
    self.tests_script_dir = self.config_parser.get(section="test", option="test_scripts_dir")
    print("bridge_config_path=", self.config_path)
    print("emmc_flash_path=", self.emmc_flash_path)
    print("firmware_dir_path=", self.firmware_dir_path)
    print("openocd_flash_utility=", self.openocd_flash_utility)
    print("tests_script_dir=", self.tests_script_dir)

  # Save configuration
  def save_bridge_config(self):
    self.bridge_config = ConfigParser()
    self.bridge_config.add_section('infos')
    self.bridge_config.set('infos', 'bridge_id', self.bridge_guid)
    self.bridge_config.set('infos', 'ip_address', self.mqtt_ip_address)
    self.bridge_config.set('infos', 'read_from_amber_dongle', self.enable_amber_dongle)
    self.bridge_config.set('infos', 'amber_dongle_port', self.amber_port)
    self.bridge_config.set('infos', 'polling_interval', self.om_polling_interval)
    self.bridge_config.set('infos', 'password', self.jwt)
    with open('/tmp/bridge.cfg', 'w') as configfile:
      self.bridge_config.write(configfile)

  # Sends a login POST request to Dandelion
  def login(self, username, password):
    payload = { 'username': username, 'password': password }
    server = self.ws_url + "/Accounts/login"
    print("log in server=", server)
    #print "log payload=", payload
    r = requests.post(server, payload)

    if r.status_code == 200:
      #print "JSON LOGIN: ", r.json()
      self.dandelion_token = r.json()['id']
      self.logged_server=self.ws_url
    else:
      print(r)
      self.dandelion_token = None

    return r.status_code

  # Delete dandelion token
  def logout(self):
    self.dandelion_token = None

  # Check logged in state
  def is_logged_in(self, server):
    if self.logged_server != server:
        self.dandelion_token = None
    return self.dandelion_token != None

  # Check ready state
  def is_ready(self):
    if not self.serial_number:
      return self.mqtt_ip_address and self.bridge_guid
    else:
      return True

  # Get Bridge Information
  def get_bridge_info(self):
    server = self.ws_url + "/Bridges/" + self.bridge_guid
    payload = { 'access_token': self.dandelion_token }
    print("req bridge server=", server)
    #print "req payload=", payload

    r = requests.get(server, payload)

    if r.status_code == 200:
      #print "JSON INFO: ", r.json()
      with open('/tmp/bridge_info.json', 'w') as f:
        f.write(r.text)
      self.serial_number = r.json()['dsiSN']
      self.jwt = r.json()['jwt']
    else:
      print(r)
      self.serial_number = None

    return r.status_code
