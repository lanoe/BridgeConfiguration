#!/usr/bin/env bash
if [ "$(id -u)" != "0" ]; then
    echo "This script must be run as root" 1>&2
    exit 1
fi

if [ $? -eq 1 ]; then
    echo "Update SSH key"
    ssh-keyscan serv-prod1.dsinstruments.fr >> $HOME/.ssh/known_hosts
fi

pip_version=9.0.1
check_pip=$(pip --version | grep "$pip_version")
if [ "$check_pip" = "" ]; then
    apt-get update
    apt-get -y install python3-pip libffi-dev libssl-dev
    pip3 install -r requirements.txt --ignore-installed
fi

cp BridgeConfig.service /lib/systemd/system/.

if [ -f install_config_env.sh ]; then
  bash install_config_env.sh
  rm -f install_config_env.sh
fi

systemctl enable BridgeConfig.service
systemctl start BridgeConfig.service
