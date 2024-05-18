
# Install OpenVPN
bash /home/debian/script/install_openvpn.sh
rm -f /home/debian/script/install_openvpn.sh

# Build library for TO136
bash /home/debian/script/build_to136.sh
rm -f /home/debian/script/build_to136.sh

# Update OpenOCD
bash /home/debian/script/update_openocd.sh
rm -f /home/debian/script/update_openocd.sh

# Update ofono
bash /home/debian/script/update_ofono.sh
rm -f /home/debian/script/update_ofono.sh

# Build Hardware Test
bash /home/debian/script/build_hardware_tests.sh
rm -f /home/debian/script/build_hardware_tests.sh

# Update usb_modeswitch for Huawei 3G dongle
usbmodeswitch=$(usb_modeswitch --version | grep 'Version 2.5.0')
if [ "$usbmodeswitch" = "" ]; then
    apt-get -y install usb-modeswitch
fi

# Build UBoot tools
bash /home/debian/script/uboot-tools.sh
rm -f /home/debian/script/uboot-tools.sh

systemctl enable resize.service
systemctl disable serial-getty@ttymxc0.service
systemctl stop serial-getty@ttymxc0.service
sync
dsi_hostname=$(cat /etc/hostname)
echo "BridgeConfig is ready, connect to http://$dsi_hostname:4242"
