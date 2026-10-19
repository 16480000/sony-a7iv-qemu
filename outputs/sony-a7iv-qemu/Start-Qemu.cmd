@echo off
setlocal
set "QEMU_EXE=D:\soft\qemu\qemu-system-aarch64.exe"
if defined A7IV_QEMU_EXE set "QEMU_EXE=%A7IV_QEMU_EXE%"
if not exist "%QEMU_EXE%" (
    echo QEMU was not found at "%QEMU_EXE%".
    echo Set A7IV_QEMU_EXE to the full path of qemu-system-aarch64.exe.
    pause
    exit /b 1
)
echo Sony A7 IV 6.02 original user-space, adapted Sony GPL kernel, QEMU virt.
echo Camera menus and image-processing hardware are not running.
echo Exit QEMU with Ctrl+A followed by X.
"%QEMU_EXE%" ^
 -M virt,gic-version=2,highmem=off ^
 -cpu cortex-a35,cntfrq=2000000 -smp 4 -m 1024 ^
 -kernel "%~dp0images\Image" ^
 -initrd "%~dp0images\qemu-initramfs.cpio.gz" ^
 -append "earlycon=pl011,0x09000000 console=ttyAMA0,115200 loglevel=6 rdinit=/init panic=-1" ^
 -drive "if=none,id=A7IV_USR,file=%~dp0images\usr.ext2,format=raw,readonly=on" ^
 -device virtio-blk-device,drive=A7IV_USR,serial=A7IV_USR ^
 -drive "if=none,id=A7IV_SYSTEM,file=%~dp0images\system.vfat,format=raw,readonly=on" ^
 -device virtio-blk-device,drive=A7IV_SYSTEM,serial=A7IV_SYSTEM ^
 -drive "if=none,id=A7IV_CP,file=%~dp0images\cp.vfat,format=raw,readonly=on" ^
 -device virtio-blk-device,drive=A7IV_CP,serial=A7IV_CP ^
 -display none -serial mon:stdio -monitor none -nic none -no-reboot
exit /b %ERRORLEVEL%
