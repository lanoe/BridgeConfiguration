#!/usr/bin/env bash
# Make sure only root can run our script
if [ "$(id -u)" != "0" ]; then
    echo "This script must be run as root" 1>&2
    exit 1
fi

emmc_mount_path="/media/emmc_rootfs"

board=bridge
disk_type=eMMC
disk=$(lsblk | grep mmcblk2p1 | awk '{print $1}' | cut -c 7-14)

if [ "$disk" == "" ]; then
    disk=sda
    disk_type=USB-mSATA
fi

partition1="$disk"1
partition2="$disk"2

# Mount the disk flashed

if grep -qs "$emmc_mount_path/home" /proc/mounts; then
    echo "Umount $disk_type home"
    umount $emmc_mount_path/home
    cryptsetup luksClose /dev/mapper/dsi
fi

if grep -qs "$emmc_mount_path" /proc/mounts; then
    echo "Umount $disk_type rootfs"
    umount $emmc_mount_path
fi

if ! grep -qs "$emmc_mount_path" /proc/mounts; then
    echo "Mount $disk_type rootfs"
    mount /dev/$partition1 $emmc_mount_path
fi

# Mount eMMC encrypted partition
if [ -f $emmc_mount_path/root/.to136 ]; then
    echo "Mount $disk_type home"
    /home/debian/dsi-storage/decrypt-dsi-storage /dev/$partition2 dsi
    mount -t ext4 /dev/mapper/dsi $emmc_mount_path/home
fi

if [ -f /tmp/bridge_info.json ]; then
    dsiSN=$(grep -Po '"dsiSN":.*?[^\\]",' /tmp/bridge_info.json | awk '{print $2}') && dsiSN=${dsiSN::-1} && dsiSN=$(echo "${dsiSN//\"}")
    jwt=$(grep -Po '"jwt":.*?[^\\]",' /tmp/bridge_info.json | awk '{print $2}') && jwt=${jwt::-1} && jwt=$(echo "${jwt//\"}")
    id=$(grep -Po '"id":.*?[^\\]",' /tmp/bridge_info.json | awk '{print $2}') && id=${id::-1} && id=$(echo "${id//\"}")
else
    if [ -f /tmp/serial_number ]; then
        dsiSN=$(cat /tmp/serial_number)
        jwt=""
        id=""
	board=translator
        if [ "$dsiSN" == "" ]; then
            echo "ERROR | No serial_number"
        fi
    else
        echo "ERROR | No bridge info file /tmp/bridge_info.json or /tmp/serial_number"
    fi
fi

if [ -f /tmp/mqtt_ip_address ]; then
    mqtt_server=$(cat /tmp/mqtt_ip_address)
    if [ "$mqtt_server" == "serv-dev2.dsinstruments.fr" ]; then
        TEST=_test
    fi
else
    echo "ERROR | No mqtt file /tmp/mqtt_ip_address"
fi

# Init
tests_success=0

# Validating /etc/hosts
hosts_path="$emmc_mount_path/etc/hosts"
hosts_ref_path="$PWD/ref_files/hosts"
hosts_ref_tmp="/tmp/hosts"
cp $hosts_ref_path $hosts_ref_tmp && sync
if [ "$board" == "translator" ]; then
    sed -i "s/Bridge_dsiSN/BLETranslator$dsiSN/g" $hosts_ref_tmp
else
    sed -i "s/_dsiSN/$dsiSN/g" $hosts_ref_tmp
fi
diff --brief <(sort $hosts_path) <(sort $hosts_ref_tmp) >/dev/null
if [ $? -eq 1 ]
then
    echo "ERROR | $hosts_ref_tmp and $hosts_path are different."
    tests_success=1
fi

# Validating /etc/hostname
hostname_path="$emmc_mount_path/etc/hostname"
hostname_ref_path="$PWD/ref_files/hostname"
hostname_ref_tmp="/tmp/hostname"
cp $hostname_ref_path $hostname_ref_tmp && sync
if [ "$board" == "translator" ]; then
    sed -i "s/Bridge_dsiSN/BLETranslator$dsiSN/g" $hostname_ref_tmp
else
    sed -i "s/_dsiSN/$dsiSN/g" $hostname_ref_tmp
fi
diff --brief <(sort $hostname_path) <(sort $hostname_ref_tmp) >/dev/null
if [ $? -eq 1 ]
then
    echo "ERROR | $hostname_ref_tmp and $hostname_path are different."
    tests_success=1
fi

# Validating /etc/hostapd/hostapd.conf
hostapd_path="$emmc_mount_path/etc/hostapd/hostapd.conf"
hostapd_ref_path="$PWD/ref_files/hostapd.conf"
hostapd_ref_tmp="/tmp/hostapd.conf"
cp $hostapd_ref_path $hostapd_ref_tmp && sync
if [ "$board" == "translator" ]; then
    sed -i "s/bdg_dsiSN/BLETranslator$dsiSN/g" $hostapd_ref_tmp
else
    sed -i "s/_dsiSN/$dsiSN/g" $hostapd_ref_tmp
fi
diff --brief <(sort $hostapd_path) <(sort $hostapd_ref_tmp) >/dev/null
if [ $? -eq 1 ]
then
    echo "ERROR | $hostapd_ref_tmp and $hostapd_path are different."
    tests_success=1
fi

if [ "$board" == "translator" ]; then
    # Validating /home/dsi/DsiBridge/config/ble_translator.cfg
    defaultcfg_path="$emmc_mount_path/home/dsi/DsiBridge/config/ble_translator.cfg"
    defaultcfg_ref_path="$PWD/ref_files/ble_translator.cfg"
    defaultcfg_ref_tmp="/tmp/ble_translator.cfg"
else
    # Validating /home/dsi/DsiBridge/config/default.cfg
    defaultcfg_path="$emmc_mount_path/home/dsi/DsiBridge/config/default.cfg"
    defaultcfg_ref_path="$PWD/ref_files/default.cfg"
    defaultcfg_ref_tmp="/tmp/default.cfg"
fi
cp $defaultcfg_ref_path $defaultcfg_ref_tmp && sync
sed -i "s/_mqttjwt/$jwt/g" $defaultcfg_ref_tmp
sed -i "s/_bdgId/$id/g" $defaultcfg_ref_tmp
sed -i "s/_mqttserver/$mqtt_server\n/g" $defaultcfg_ref_tmp
diff --brief <(sort $defaultcfg_path) <(sort $defaultcfg_ref_tmp) >/dev/null
if [ $? -eq 1 ]
then
    echo "ERROR | $defaultcfg_ref_tmp and $defaultcfg_path are different."
    tests_success=1
fi

if [ "$board" != "translator" ]; then
    # Validating number of files in /etc/openvpn
    openvpn_path="$emmc_mount_path/etc/openvpn"
    nb_files=$(/bin/ls -1U $openvpn_path | wc -l)
    if [ $nb_files -ne 8 ]
    then
        echo "ERROR | $openvpn_path doesn't contain the required number of files."
        tests_success=1
    fi

    # Validating files presence in /etc/openvpn
    if [ ! -f $openvpn_path/Bridge_$dsiSN$TEST.crt ]; then
        echo "ERROR | No file $openvpn_path/Bridge_$dsiSN$TEST.crt"
        tests_success=1
    fi
    if [ ! -f $openvpn_path/Bridge_$dsiSN$TEST.csr ]; then
        echo "ERROR | No file $openvpn_path/Bridge_$dsiSN$TEST.csr"
        tests_success=1
    fi
    if [ ! -f $openvpn_path/Bridge_$dsiSN$TEST.key ]; then
        echo "ERROR | No file $openvpn_path/Bridge_$dsiSN$TEST.key"
        tests_success=1
    fi
    if [ ! -f $openvpn_path/ca.crt ]; then
        echo "ERROR | No file $openvpn_path/ca.crt"
        tests_success=1
    fi
    if [ ! -f $openvpn_path/client.conf ]; then
        echo "ERROR | No file $openvpn_path/client.conf"
        tests_success=1
    fi
fi

if grep -qs "$emmc_mount_path/home" /proc/mounts; then
    echo "Umount $disk_type home"
    umount $emmc_mount_path/home
    cryptsetup luksClose /dev/mapper/dsi
fi

if grep -qs "$emmc_mount_path" /proc/mounts; then
    echo "Umount $disk_type rootfs"
    umount $emmc_mount_path
fi

# Everything went fine
if [ $tests_success -eq 0 ]
then
    echo "SUCCESS | All the files are valid."
    exit 0
else
    echo "FAILURE | At least one test is failed."
    exit 1
fi
