echo A7IV_FIRMWARE_SHELL_RUNNING
cat /proc/version
echo ORIGINAL_UIPC_MODULE_CHECK
insmod /kmod/devno.ko
echo DEVNO_STATUS=$?
insmod /usr/kmod/osal_utm.ko
echo UTM_STATUS=$?
insmod /usr/kmod/osal_uipc.ko
echo UIPC_STATUS=$?
ls -l /dev/uipc /dev/utm
/usr/bin/bootin.elf > /tmp/bootin.log 2>&1 &
bootin_pid=$!
sleep 2
cat /tmp/bootin.log
kill "$bootin_pid" 2>/dev/null
dmesg | /bin/busybox tail -n 25
echo A7IV_PROBE_DONE
