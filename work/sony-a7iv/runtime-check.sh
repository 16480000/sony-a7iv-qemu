echo A7IV_FIRMWARE_SHELL_RUNNING
uname -a
grep processor /proc/cpuinfo
ls -l /usr/bin/bootin.elf /usr/lib/appFw.so /system/vmlinux.bin
/usr/bin/openssl version
echo ORIGINAL_APP_LOADER_DEPENDENCIES
/lib/ld-linux-aarch64.so.1 --list /usr/bin/bootin.elf
echo ORIGINAL_APP_START_ATTEMPT
/usr/bin/bootin.elf > /tmp/bootin.log 2>&1 &
bootin_pid=$!
sleep 2
cat /tmp/bootin.log
kill "$bootin_pid" 2>/dev/null
echo ORIGINAL_APP_START_ATTEMPT_END
echo A7IV_PROBE_DONE
