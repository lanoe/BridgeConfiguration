// App.js
Terminal.applyAddon(fit);
var logs_flash_term = new Terminal();
var logs_FlashMaster_term = new Terminal();
var logs_term = new Terminal();
var logs_test_term = new Terminal();

function getFirmwareList() {
    var request = new XMLHttpRequest();
    request.onload = function() {
        document.getElementById("firmwareFileSelection").innerHTML = request.responseText;
    };

    request.open("GET", "/firmware_list", true);
    request.send();
};

function getLoginState() {
    var request = new XMLHttpRequest();
    request.onload = function() {
        document.getElementById("top-navbar").innerHTML = request.responseText;

        username = localStorage.getItem("username");
        if (username != null) document.getElementById("username").value = username;

        server = localStorage.getItem("dandelionServerSelection");
        if (server != null) document.getElementById("dandelionServerSelection").value = server;
    };

    request.open("GET", "/loginform", true);
    request.send();
};

function getTestList() {
    var request = new XMLHttpRequest();
    request.onload = function() {
        document.getElementById("test_list").innerHTML = request.responseText;
    };

    request.open("GET", "/tests_list", true);
    request.send();
};

function initSocketIO() {
    var socket_logs = io.connect(location.protocol+'//'+location.hostname+(location.port ? ':'+location.port: '') + '/logs');
    var socket_alert = io.connect(location.protocol+'//'+location.hostname+(location.port ? ':'+location.port: '') + '/alert');

    socket_logs.on("flash-log", function(msg) {
        logs_flash_term.write(msg.data);
    });

    socket_logs.on("flashmaster-log", function(msg) {
        logs_FlashMaster_term.write(msg.data);
    });

    socket_logs.on("config-log", function(msg) {
        logs_term.write(msg.data);
    });

    socket_logs.on("test-log", function(msg) {
        logs_test_term.write(msg.data);
    });

    socket_alert.on("alert-state", function(msg) {
        parent_elem = document.getElementById(msg.test_name).parentElement;
        result_label = parent_elem.lastElementChild
        if (msg.state) {
            result_label.lastElementChild.style.display = "inline-block";
            result_label.firstElementChild.style.display = null;
        }
        else {
            result_label.firstElementChild.style.display = "inline-block";
            result_label.lastElementChild.style.display = null;
        }
    });
};

function addAlert(type, message) {
    var alertDiv = document.getElementById("alertsMain");

    var alert = document.createElement("DIV");
    alert.className = "alert alert-" + type;

    var button = document.createElement("BUTTON");
    button.className = "close";
    button.nodeType = "button";
    button.setAttribute("data-dismiss", "alert");
    button.innerHTML = "&times;"

    var text = document.createTextNode(message);

    alert.appendChild(button);
    alert.appendChild(text);

    alertDiv.appendChild(alert);

    setTimeout(function() {
        alertDiv.removeChild(alert);
    }, 5000);
};

function genParams(test_name) {
    params = []
    switch (test_name) {
        case "ble_test.sh":
            ble_mac_address = document.getElementById("ble_mac_address").value;
            localStorage.setItem("ble_mac_address", ble_mac_address);
            params.push(ble_mac_address);

            ble_pin_code = document.getElementById("ble_pin_code").value;
            localStorage.setItem("ble_pin_code", ble_pin_code);
            params.push(ble_pin_code);
            break;
        case "wifi_test.sh":
            wifi_ssid = document.getElementById("wifi_ssid").value;
            localStorage.setItem("wifi_ssid", wifi_ssid);
            params.push(wifi_ssid);

            wifi_passphrase = document.getElementById("wifi_passphrase").value;
            localStorage.setItem("wifi_passphrase", wifi_passphrase);
            params.push(wifi_passphrase);

            wifi_hidden = document.getElementById("wifi_hidden").checked;
            localStorage.setItem("wifi_hidden", wifi_hidden);
            if (wifi_hidden == true) params.push("true");
            else params.push("false");
            break;
        default: break;
    }
    return params
}

function loadTestLocalStorage() {
    ble_mac_address = localStorage.getItem("ble_mac_address");
    if (ble_mac_address != null) document.getElementById("ble_mac_address").value = ble_mac_address;

    ble_pin_code = localStorage.getItem("ble_pin_code");
    if (ble_pin_code != null) document.getElementById("ble_pin_code").value = ble_pin_code;

    wifi_ssid = localStorage.getItem("wifi_ssid");
    if (wifi_ssid != null) document.getElementById("wifi_ssid").value = wifi_ssid;

    wifi_passphrase = localStorage.getItem("wifi_passphrase");
    if (wifi_passphrase != null) document.getElementById("wifi_passphrase").value = wifi_passphrase;

    wifi_hidden = localStorage.getItem("wifi_hidden");
    if (wifi_hidden != null) document.getElementById("wifi_hidden").checked = wifi_hidden;
}

function launch_test(test_name) {
    var request = new XMLHttpRequest();

    request.onload = function() {
        if (request.status === 200)
            addAlert("success", request.responseText, test_name);
        else
            addAlert("danger", request.responseText, test_name);

        parent_elem = document.getElementById(test_name).parentElement;
        button = parent_elem.children[parent_elem.children.length -2]
        button.textContent = "Launch";
        button.disabled = false;
    };

    var params = {
        "test_name": test_name,
        "params": genParams(test_name)
    };

    logs_test_term.clear();
    request.open("POST", "/launch_test", true);
    request.setRequestHeader("Content-Type", "application/json");
    request.send(JSON.stringify(params));

    child_list = document.getElementById(test_name).parentElement.children;
    button = child_list[child_list.length -2]
    button.textContent = "Running";
    button.disabled = true;
}

function launch_all_tests() {
    var request = new XMLHttpRequest();
    launchAll = document.getElementById("launchAllTests");

    check_list = document.getElementById("test_list").getElementsByClassName("tests");
    test_list = {};
    for(var i = 0; i < check_list.length; i++){
        test_check = check_list[i].getElementsByClassName("form-check-input")[0];
        if(test_check.checked){
            test_list[test_check.id] = genParams(test_check.id);
        }
    }

    request.onload = function() {
        if (request.status === 200)
            addAlert("success", request.responseText);
        else
            addAlert("danger", request.responseText);

        for(var i = 0; i < check_list.length; i++){
            button = check_list[i].children[check_list[i].children.length -2]
            button.textContent = "Launch";
            button.disabled = false;
        }
        launchAll.textContent = "Launch all selected Test";
        launchAll.disabled = false;
    };

    logs_test_term.clear();
    request.open("POST", "/launch_all_tests", true);
    request.setRequestHeader("Content-Type", "application/json");
    request.send(JSON.stringify(test_list));

    for(var i = 0; i < check_list.length; i++){
        button = check_list[i].children[check_list[i].children.length -2];
        button.textContent = "Running";
        button.disabled = true;
    }
    launchAll.textContent = "Running all selected Test";
    launchAll.disabled = true;
}

function flash() {
    var request = new XMLHttpRequest();
    request.onload = function() {
        if (request.status === 200)
            addAlert("success", request.responseText);
        else
            addAlert("danger", request.responseText);
    };

    var image_path = document.getElementById("image_path").value;
    var encrypt = document.getElementById("encrypt").checked;
    var fuseBootOnEmmc = document.getElementById("fusebootemmc").checked;
    var fuseBootOnSDcard = document.getElementById("fusebootsdcard").checked;

    var params = {
        "image_path": image_path,
        "encrypt": encrypt,
        "fuseBootOnEmmc" : fuseBootOnEmmc,
        "fuseBootOnSDcard" : fuseBootOnSDcard
    };

    logs_flash_term.clear();
    request.open("POST", "/flash", true);
    request.setRequestHeader("Content-Type", "application/json");
    request.send(JSON.stringify(params));
}

function flash_master() {
    var request = new XMLHttpRequest();
    request.onload = function() {
        if (request.status === 200)
            addAlert("success", request.responseText);
        else
            addAlert("danger", request.responseText);
    };

    var e = document.getElementById("firmwareFileSelection");
    var firmware = e.options[e.selectedIndex].value;

    var params = {
        "firmware_file_name": firmware,
    };

    logs_FlashMaster_term.clear();
    request.open("POST", "/flashMaster", true);
    request.setRequestHeader("Content-Type", "application/json");
    request.send(JSON.stringify(params));
}

function configure() {
    var request = new XMLHttpRequest();
    request.onload = function() {
        if (request.status === 200)
            addAlert("success", request.responseText);
        else
            addAlert("danger", request.responseText);
    };

    var guidInput = document.getElementById("guidInput").value;
    var configure_vpn = document.getElementById("configurevpn").checked;
    var use_amber_dongle = document.getElementById("enableAmberDongle").checked;
    var amber_is_serial = document.getElementById("amberType").checked;
    var omPollingInt = document.getElementById("omPollingInt").value;
    var config_translator = document.getElementById("confmicrobridge").checked;
    var snInput = document.getElementById("snInput").value;

    var params = {
        "guid": guidInput,
        "configure_vpn" : configure_vpn,
        "use_amber_dongle" : use_amber_dongle,
        "amber_is_serial" : amber_is_serial,
        "omPollingInt" : omPollingInt,
        "config_translator" : config_translator,
        "serial_number": snInput
    };

    logs_term.clear();
    request.open("POST", "/config", true);
    request.setRequestHeader("Content-Type", "application/json");
    request.send(JSON.stringify(params));
}

// Logs in Dandelion
function login() {
    var request = new XMLHttpRequest();
    request.onload = function() {
        if (request.status != 200) {
            addAlert("danger", request.responseText);
        }
        else {
            addAlert("success", request.responseText);
            getLoginState();
        }
    };

    var dandelionServerSelection = document.getElementById("dandelionServerSelection").value;
    localStorage.setItem("dandelionServerSelection", dandelionServerSelection);
    var username = document.getElementById("username").value;
    localStorage.setItem("username", username);
    var password = document.getElementById("password").value;

    var credentials = {
        "server": dandelionServerSelection,
        "username": username,
        "password": password
    };

    request.open("POST", "/login", true);
    request.setRequestHeader("Content-Type", "application/json");
    request.send(JSON.stringify(credentials));
}

// Logout from Dandelion
function logout() {
    var request = new XMLHttpRequest();
    request.onload = function() {
        if (request.status != 200) {
            addAlert("danger", request.responseText);
        }
        else {
            addAlert("success", request.responseText);
            getLoginState();
        }
    };

    request.open("POST", "/logout", true);
    request.send();
}

function selectBridge() {
    var configMicroBridge = document.getElementById("confmicrobridge").checked;
    if (configMicroBridge) {
        document.getElementById("enableAmberDongle").checked = false;
        document.getElementById("configurevpn").checked = false;
        document.getElementById("guidInput").value = "";
        document.getElementById("omPollingInt").value = "";
    }
    else {
        document.getElementById("configurevpn").checked = true;
        document.getElementById("snInput").value = "";
        document.getElementById("omPollingInt").value = "30";
    }
    document.getElementById("snInput").disabled = !configMicroBridge;
    document.getElementById("omPollingInt").disabled = configMicroBridge;
    document.getElementById("guidInput").disabled = configMicroBridge;
    document.getElementById("enableAmberDongle").disabled = configMicroBridge;
    document.getElementById("configurevpn").disabled = configMicroBridge;
}

// When the page finishes to load...
addEventListener("DOMContentLoaded", function() {
    logs_flash_term.open(document.getElementById('log-flash'));
    logs_flash_term.fit();

    $('a[data-toggle="tab"]').on('shown.bs.tab', function (e) {
        switch (e.currentTarget.hash) {
            case "#pFlash":
                if (logs_flash_term.element === undefined){
                    logs_flash_term.open(document.getElementById('log-flash'));
                    logs_flash_term.fit();
                }
                break;
            case "#pFlashMaster":
                if (logs_FlashMaster_term.element === undefined){
                    logs_FlashMaster_term.open(document.getElementById('logFlashMaster-window'));
                    logs_FlashMaster_term.fit();
                }
                break;
            case "#pConfig":
                if (logs_term.element === undefined){
                    logs_term.open(document.getElementById('log-window'));
                    logs_term.fit();
                }
                break;
            case "#pTests":
                if (logs_test_term.element === undefined){
                    logs_test_term.open(document.getElementById('log-test-window'));
                    logs_test_term.fit();
                }
                break;
        }
    });

    // Display the login form or a logged in message if already logged
    getLoginState();

    // Get Firmware list
    getFirmwareList();

    // Get test list
    getTestList();

    var loaded = setInterval(function(){
        if (document.getElementById("launchAllTests") != null) {
            loadTestLocalStorage();
            clearInterval(loaded);
        }
    }, 100)

    // Init socketIO
    initSocketIO();

    // Bridge selection
    selectBridge();
}, true);
