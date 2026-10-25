# 环境与复现说明

这是已有运行环境的研究源码归档，尚未做成跨电脑的一键构建包。仅克隆仓库不足以启动：Sony 固件、完整 QEMU/内核依赖、上游运行库和本机实验镜像需要自行准备。

## 固定输入

| 输入 | 当前记录 |
| --- | --- |
| 目标 | Sony ILCE-7M4 / A7M4，固件 6.02 |
| 原始 BODYDATA SHA-256 | `ad6df47a0a93a46336b9920a0d8891d0c766f8c96fa68ebda8685f6c21621188` |
| QEMU | 11.1.2，参考板级补丁加 A7M4 SCU 模型 |
| a7c2-re 参考提交 | `25efb56d7f0c69355f9225d1da50454207532e7f` |
| 原开发环境 | Windows + WSL `Codex-Z8-Qemu`；Linux 数据在 `/opt/sony-a7iv` |

输入身份与校验清单见 `work/sony-a7iv/*manifest.json`、`outputs/sony-a7iv-qemu/source/qemu-reference/manifest.json` 及各实验证据。不要混用 A7C2 的应用二进制作为 A7M4 应用。

## 准备顺序

1. 自行取得相应官方更新包，使用仓库中的下载、解包与分区校验脚本核对输入身份。仓库不分发固件。历史下载 URL 不保证持续有效。
2. 准备固定提交的参考项目和 QEMU 源码，按 `build-reference-qemu.sh` 构建，再按 `install-scu-model.py` 安装 A7M4 模型并重新构建。
3. 准备 Linux 编译/分析依赖：Clang/LLD、AArch64 工具链、Python 3.11 或更新版本、pyelftools、Capstone、Pillow、NumPy，以及脚本调用的文件系统/归档工具。视频实验另需 FFmpeg；浏览器检查需要 Node.js 与 Chrome。
4. 检查脚本中的 `DATA`、`DEST`、`W`、`PREV` 等路径。尤其部分脚本从开发机其他项目目录加载 fwtool 和 Python 依赖，该目录不随仓库提供；需改为自己的依赖位置。
5. 按 `prepare-menu-a7m4.py` → 服务/显示适配 → `stage-runtime-a7m4.py` 的依赖顺序生成候选镜像。服务选择、init 脚本与可选模型应使用对应实验的参数；这里没有宣称所有候选均可由同一条命令重建。
6. 使用 `native/runtime/native-session.py --help` 查看启动选项。启动器默认仍校验固定带卡镜像的 SHA-256；新构建即使功能相同，哈希也未必相同，应先独立验收再调整启动配置。

上述是依赖顺序说明，本次 GitHub 整理没有在干净电脑执行完整构建。原厂中文字体补齐、Backup 校验及修改固件候选的操作细节保存在对应证据 README 中，尚未统一为构建入口。

## 本机启动与验证

已有完整环境时：

```powershell
.\outputs\sony-a7iv-qemu\native\Start-Camera.cmd
```

页面仅监听本机回环地址。历史文档中的 `localhost` 链接对应原开发机运行实例，不是 GitHub 演示地址。

当前验收应分别检查：

- 原厂 AP 快照、QEMU 显示与 HTTP 帧的一致性。
- 方向键、MENU、Fn、原厂空卡回放和返回的连续操作。
- 虚拟卡整卡哈希及文件列表，区分媒体数据库与 JPEG。
- 音效事件的字节来源与 `AP` / `virtual-cp` 标记。
- 网页模拟取景、JPEG 捕获和回放覆盖层独立检查，不当作原厂成像能力。

## 证据边界

基线启动镜像、后续中文镜像和修改固件候选不是同一个文件。每项结论只适用于其记录的配置、哈希和实验。完整 CP/AIP 执行、传感器、ISP、自动对焦、原厂 JPEG 编码及实体升级验证仍缺失。
