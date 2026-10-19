原生菜单已有新进展，见 [当前状态](native/STATUS.zh-CN.md)。本页以下保留 2026-10-17 早期用户空间方案的测试记录；`Start-Qemu.cmd` 仍是该早期 Shell 启动器。

索尼 A7 IV（ILCE-7M4）6.02 的 QEMU 用户空间环境，2026-10-17 实测。

已能进入原固件的 BusyBox Shell，挂载原始系统分区，执行原程序，并加载原 UTM/UIPC 软件驱动。完整相机系统与菜单仍未启动。本环境使用适配后的 Sony 开源内核和 QEMU virt 虚拟板，没有实现 CXD90057 的完整硬件模型。

双击同目录的 `Start-Qemu.cmd`。出现 `QEMU_USERSPACE_READY` 和 `/ #` 后即可输入命令。按 Ctrl+A，再按 X 退出 QEMU。启动器使用本机 `D:\soft\qemu\qemu-system-aarch64.exe`；如需换位置，可设置环境变量 `A7IV_QEMU_EXE` 为完整可执行文件路径。

可直接验证：

```sh
uname -a
grep processor /proc/cpuinfo
mount
/usr/bin/openssl version
/sbin/qemu-load-ipc
ls -l /dev/uipc
```

原始分区通过 Virtio 只读挂载，根目录是放在内存中的派生 initramfs；在 Shell 中的修改会随虚拟机退出而消失。运行时没有网络设备，也没有连接真实相机。CPU 计数器以 `cntfrq=2000000` 设为 Sony 代码使用的 2 MHz，避免默认 62.5 MHz 导致固定频率换算出现差异；应用启动异常在校准后仍可复现，见 `logs/app-attempt-2mhz.log`。

最终的 2 MHz 配置复核日志是 `logs/final-smoke.log`。本次已实际验证的范围如下：

| 项目 | 结果与证据 |
|---|---|
| 最新官方更新 | 6.02，2026-05-28 发布，757,480,856 字节 |
| 包解析 | CXD90057_k8 解密成功，FDAT 明文版本为 6.02 |
| 内部完整性 | 外层 CRC、解密块检查、FDAT 头 CRC、5 个分区的长度和 CRC 全部通过 |
| 原始根文件系统 | 可将未修改的 `nflasha7` 直接作为 ext2 initrd 启动，见 `logs/raw-rootfs-boot.log` |
| 用户程序 | 原 BusyBox 1.34.1、glibc 2.25、OpenSSL 3.0.2 实际运行，见 `logs/userspace-and-openssl.log` |
| CPU 与分区 | 四核 Cortex-A35；原 `/usr`、`/system`、`/cp` 分区均挂载成功 |
| 软件驱动 | 原 `devno.ko`、`osal_utm.ko`、`osal_uipc.ko` 均返回加载成功，实际生成 `/dev/uipc` |
| 相机应用 | `bootin.elf` 能启动 `im.elf`，但后者发生用户态访问异常；菜单未出现 |
| 原硬件驱动阶段 | 执行原 `insmod_drv2` 时，`pcieatu` 访问 `0xfffffffff7300004` 触发内核页错误 |

最初 `bootin.elf` 报缺少 `/dev/uipc`。补齐真实实现与内核配置后，这一步已解决。接着观察到 `im.elf` 在 `libMWF.so` 的 `MonQueue::GetQueueRemain()` 中以空对象地址执行读取（文件虚拟偏移 `0x409d0`），进入 Sony 异常监视器。此处是对空对象的访问，不能据此认定它由某一个硬件设备单独造成；队列未建立的完整原因尚未恢复。另一次原始驱动阶段实验确认了独立的板级限制：PCIe ATU 驱动会直接访问 Sony 地址空间，QEMU virt 没有对应映射。原始日志分别保存在 `logs/ipc-driver-and-app-attempt.log` 和 `logs/original-driver-hardware-fault.log`；最终 2 MHz 配置下的对应复核日志为 `logs/app-attempt-2mhz.log` 和 `logs/hardware-driver-2mhz.log`。

因此，此交付可以用于运行和调试原固件用户空间，不能作为相机菜单、拍摄、AF、ISP、协处理器或整机启动已经成功的证明。要继续到相机菜单，需要恢复应用初始化依赖，并为 CXD90057 的 PCIe、协处理器通信及显示等设备提供实际模型；仅追加 QEMU 命令行参数不能完成这些工作。

`images/Image` 是从 Sony 为 Ver.6.00 发布的 GPL 内核源码镜像编译的 **4.9.337-scel**，不是 6.02 更新包内未经修改的内核。源码镜像固定于 `fa5c6f6aba58f675691e5adf291b155b76e6e93e`。6.02 的原内核仍保留在原 `/system/vmlinux.bin` 中，本次没有用它成功启动整机。最终启动使用 QEMU 自动生成的设备树；Sony 自带的 `qemu.dts` 仅用于初步实验。

源码改动在 `source/patches/`，实际配置在 `source/kernel.config`。改动仅用于虚拟板适配及修复源码条件编译缺项：排除真机 GIC/UDIF IRQ 映射、正确约束 PM/恢复代码、启用软件驱动需要的真实跟踪与冻结实现，并使用架构计时器。没有用空函数冒充 UIPC 或其他相机接口。派生 initramfs 保留原根文件系统所有常规文件内容和符号链接，增加 `/init`、`/sbin/qemu-load-ipc` 以及同一更新包中的 `/setting` 资源；原 `/sbin/init` 保留，但默认不作为 PID 1。细目见 `evidence/initramfs-manifest.json`。

重建内核需 Linux、GNU make、AArch64 GCC、bc、flex、bison、libssl-dev、libelf-dev 等工具。准备干净的固定版本源码后，执行：

```sh
sh source/Rebuild-Kernel.sh /absolute/path/to/linux-kernel /absolute/path/to/new-build
```

该脚本会向指定源码应用所附补丁，使用单独构建目录。编译器和构建时间不同会改变二进制摘要；附录中的 SHA-256 用于确认本次交付文件。

原 `BODYDATA.DAT` 的 SHA-256 为 `ad6df47a0a93a46336b9920a0d8891d0c766f8c96fa68ebda8685f6c21621188`。这是本地计算值；没有把内部 CRC 校验描述成 Sony 数字签名验证。镜像的 SHA-256、QEMU 版本与可执行文件摘要见 `evidence/delivery-manifest.json`。本机实测 QEMU 为 11.1.0。

来源：[Sony 中国 6.02 固件页](https://service.sony.com.cn/download/firm/00003010.html)、[Sony 全球 6.02 固件页](https://www.sony.com/electronics/support/e-mount-body-ilce-7-series/ilce-7m4/software/00280505)、[Sony GPL 源码页](https://oss.sony.net/Products/Linux/DI/ILCE-7M4_Ver600.html)、[固定版本源码镜像](https://github.com/DavidBuchanan314/Sony-ILCE-7M4-Linux/tree/fa5c6f6aba58f675691e5adf291b155b76e6e93e)、[fwtool CXD90057 支持 PR](https://github.com/ma1co/fwtool.py/pull/52)、[ILCE-7M4 原作者硬件研究](https://github.com/DavidBuchanan314/ILCE-7M4-RE)。

本次 REA 固件工具要求 Linux 后端，其本地 Windows 后端不适用于这个固件解析任务；实际解包使用固定提交 `3955d7890fc38daf942bb52827599bfe35de4a14` 的 fwtool、Python、ELF 工具和 QEMU 执行证据。交付中的日志与 JSON 是本地证据，没有伪装成 REA Evidence ID。
