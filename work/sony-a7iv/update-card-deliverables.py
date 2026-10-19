"""Publish the verified live-card status after cold-start and restart checks."""
from pathlib import Path
import json,shutil
w=Path(__file__).resolve().parent;o=w.parent.parent/'outputs/sony-a7iv-qemu/native';e=o/'evidence'
before=json.loads((e/'live117-before-restart-audit.json').read_text())
after=json.loads((e/'live117-after-restart-audit.json').read_text())
restart=json.loads((e/'live117-restart-api.json').read_text(encoding='utf-8-sig'))
assert restart['result']['ok'] and before['qemu_pid']!=after['qemu_pid']
assert before['http_frame_matches_original_ap_rgb'] and after['http_frame_matches_original_ap_rgb']
assert all(json.loads((e/'live117-after-restart-pixels.json').read_text()).values())
promotion=json.loads((e/'card-profile-promotion.json').read_text())
promotion.update({'primary_activated':True,'primary_run':'native-117-card-main','url':after['url'],'live_before_restart':before,'live_after_restart':after,'restart':restart})
(e/'card-profile-promotion.json').write_text(json.dumps(promotion,indent=2))
shutil.copyfile(e/'live117-after-restart-main.png',o/'basic-main-current.png')
(o/'BASIC-FUNCTIONS.zh-CN.md').write_text('''# 基础功能进展（2026-10-19）

ILCE-7M4 6.02 原厂主界面已更新为带卡配置 native117。[打开当前界面](http://localhost:18764/S5jrCd45BfZKkoQmYa7c0ASfeT12LoLl/)。**实时取景、自动对焦和拍照仍未实现。**

| 功能 | 实测结果 |
| --- | --- |
| 方向键、确认、MENU | 操作原厂菜单并返回主界面 |
| Fn | 打开原厂快捷面板，返回后仍能继续操作 |
| 虚拟卡 | 原厂文件系统挂载 64 MiB FAT32 卡槽 2，照片记录目标设为 Slot 2 |
| 回放 | 显示原厂“No images”空卡页面，能返回主界面，再使用 Fn、MENU |
| 存储写入 | 原厂程序创建 DATABASE.BIN（9,670,656 字节）和 MEDIAPRO.XML（405 字节） |
| 半按、快门 | 发送原厂按键事件；整卡哈希未变化，没有新增照片 |
| 重新启动 | 已实际重启，自动重做初始设置、关闭省电、挂载虚拟卡并重新选择照片 Slot 2；重启后回放、Fn、MENU 再次通过 |

网页来自实际 QEMU 显示缓冲。带卡主界面、回放、返回及 Fn 的八个检查画面，与独立校验的原厂 AP 快照逐字节一致；网页实例在重启前后也通过 AP/HTTP 整帧 RGB 比对。

这次修复了两个阻塞点：精确接收并释放原厂单向诊断消息，避免日志队列阻塞；按照原厂 CP 的定义接受 EVF 优先级 0–2，解决回放发出值 2 时被虚拟显示端拒绝、触发原厂断言的问题。调试记录保留最近两段，每段最多 8 MiB，已实测轮换。

虚拟卡和个人设置保存在当前虚拟机内存中，重启会清空；初始化步骤通过原厂界面重放。卡槽 1 的混合介质 PCI/SxS 后端仍未实现。当前软件模型覆盖部分控制协议，没有执行完整 CP 成像固件，也没有传感器、ISP、对焦或 JPEG 编码数据。

证据：

- [回放修复前后对比](evidence/evf-priority-playback-fix.json)：合法枚举的原厂代码位置、六项连续操作及八次显示校验。
- [快门与卡写入审计](evidence/capture-and-card-audits.json)：只读整卡 SHA-256、文件列表、各轮原始结果。保留失败的诊断导出及后续恢复说明。
- [当前配置与实际重启验证](evidence/card-profile-promotion.json)：镜像哈希、网页实例、重启前后不同 QEMU 进程及显示比对。
- [带卡主界面](slot2-main-verified.png)、[空卡回放](slot2-playback-empty.png)、[Fn 面板](slot2-fn-verified.png)：实际 QEMU 截图。

实验只使用隔离虚拟机中的文件，没有接入真实相机或物理存储设备。
''',encoding='utf-8')
(o/'MAIN-UI.zh-CN.md').write_text('''# 当前主界面使用说明

2026-10-19，ILCE-7M4 6.02，当前带卡实例 native117：

[打开本机相机界面](http://localhost:18764/S5jrCd45BfZKkoQmYa7c0ASfeT12LoLl/)

方向键和确认键操作原厂界面；MENU 进入菜单或返回；Fn 打开原厂快捷面板。回放显示“No images”，再次按回放返回主界面。当前卡槽 2 为 64 MiB FAT32 虚拟卡，照片记录目标已设为 Slot 2。

实时取景和照片生成尚未实现。半按及快门按钮发送原厂按键事件，目前没有 JPEG 输出。“保存截图”保存当前 QEMU 界面的 PNG。

重新启动会清空虚拟卡和个人设置，自动重放原厂语言、区域、日期和操作向导，关闭省电，再设置照片记录到 Slot 2。该流程已实际重启验证，重启后回放与 Fn 仍能使用。

重新打开本机环境使用 Start-Camera.cmd：先复用现有网页，没有实例时校验固定镜像哈希，再启动带卡主界面。PowerShell 启动器已通过语法检查；同参数的实际冷启动、网页操作和重启均已验证。启动器文件本身尚未另行关闭实例后独立运行。

镜像位于 D:\\CodexWork\\sony-a7iv-qemu\\menu-a7m4\\main-virtual-card-stable.cpio，依赖本机 Codex-Z8-Qemu WSL 和既有 QEMU 环境。本目录不是可移植固件包。旧主界面镜像仍保留。

完整限制和证据见 [基础功能进展](BASIC-FUNCTIONS.zh-CN.md)。
''',encoding='utf-8')
(o/'README.zh-CN.md').write_text('''# Sony A7 IV 6.02 QEMU

双击 Start-Camera.cmd 打开当前原厂主界面，或 [直接打开网页](http://localhost:18764/S5jrCd45BfZKkoQmYa7c0ASfeT12LoLl/)。

当前配置包含 64 MiB FAT32 虚拟卡槽 2。原厂菜单、Fn、空卡回放、返回主界面和重启已验证；原厂程序可以写入媒体数据库。实时取景、对焦和照片生成尚未实现。重启会清空虚拟卡和个人设置，再自动重做初始设置。

详见 [使用说明](MAIN-UI.zh-CN.md) 和 [基础功能与验证](BASIC-FUNCTIONS.zh-CN.md)。停止使用面板按钮。Start-Menu.cmd 是保留的旧菜单专用配置。

依赖本机 Codex-Z8-Qemu WSL、D:\\CodexWork\\sony-a7iv-qemu 固件数据，以及 /opt/sony-a7iv 下已构建的 QEMU 和原厂运行库；此目录不包含完整 Sony 固件，也不是可复制到其他电脑直接运行的镜像。
''',encoding='utf-8')
old=(o/'STATUS.zh-CN.md').read_text()
marker='以下为 2026-10-18 的主界面里程碑和原始显示证据。'
historical=old[old.index(marker):] if marker in old else old
(o/'STATUS.zh-CN.md').write_text('''2026-10-19 当前状态：网页已切换至带卡实例 native117。卡槽 2 的 FAT32 虚拟卡、原厂数据库写入、空卡回放、返回主界面、Fn 和实际重启均已验证。实时取景、自动对焦和照片生成尚未实现。详见 [基础功能进展](BASIC-FUNCTIONS.zh-CN.md) 及 [当前配置验证](evidence/card-profile-promotion.json)。

原先 native104–114 带卡回放卡死的问题已定位至虚拟显示端拒绝合法 EVF 优先级 2；native115/116 修复后的连续操作和显示比对通过。历史记录中的回放失败只适用于修复前的实验。

'''+historical,encoding='utf-8')
print('LIVE_CARD_DELIVERABLES_UPDATED')
