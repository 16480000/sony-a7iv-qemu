echo A7IV_FIRMWARE_SHELL_RUNNING
cat /proc/version
export TOPRC=/etc/toprc
export MALLOC_OPTIONS=gfffffffff
export MALLOC_MMAP_THRESHOLD_=131072
export MALLOC_CHECK_=3
export LT_ABORTREASON=0
export WBSHD=/tmp_wbshd/shared.XXXXXX
mkdir -p /tmp_wbshd
mount -t tmpfs none /tmp_wbshd
insmod /kmod/devno.ko
echo DEVNO_STATUS=$?
echo set > /proc/udm/drivers
echo UDIF_SET_STATUS=$?
insmod /usr/kmod/osal_utm.ko
echo UTM_STATUS=$?
insmod /usr/kmod/osal_uipc.ko
echo UIPC_STATUS=$?
insmod /usr/kmod/backup.ko Backup_load=0
echo BACKUP_STATUS=$?
ls -l /dev/uipc /dev/backup
/usr/bin/bootin.elf > /tmp/bootin.log 2>&1 &
bootin_pid=$!
sleep 2
cat /tmp/bootin.log
kill "$bootin_pid" 2>/dev/null
echo A7IV_PROBE_DONE
