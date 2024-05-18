#!/usr/bin/env bash
if [ "$(id -u)" != "0" ]; then
    echo "This script must be run as root" 1>&2
    exit 1
fi
systemctl stop BridgeConfig.service
export FLASK_DEBUG=1
export FLASK_APP=app.py
flask run --host=0.0.0.0
