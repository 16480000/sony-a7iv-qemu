echo A7IV_FIRMWARE_SHELL_RUNNING
cat /proc/version
grep processor /proc/cpuinfo
/usr/bin/openssl version
/sbin/qemu-load-ipc
echo IPC_HELPER_STATUS=$?
mount
echo A7IV_PROBE_DONE
