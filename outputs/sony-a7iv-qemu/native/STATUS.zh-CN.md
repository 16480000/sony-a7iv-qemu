2026-10-21 当前状态：实例 `language-zh-allfonts-20261021` 已把**原厂相机菜单改为简体中文**，首次设置语言页高亮“简体中文”，主菜单显示“设置 > 电源设置选项”等中文内容。语言来自原厂 `string_simplifiedchinese*.uxc` 与固件自带 GB18030/Big5 字体；从 `firmware.fdat` 补回 `/tmp/images` 字体（含 `Sony_DI_Icons.ttf`）后才正常渲染。原厂 `Backup.bin` 语言项 `0x2cf03a6`（数据偏移 `0x9b090`）设为 25，并重算 994,788 字节的累加校验和。宿主面板、固件音面板仍为中文；HALF 产生 48 kHz FocusLock，电子快门默认静音。证据见 [原厂相机菜单简体中文](evidence/camera-menu-zh-20261021/README.md)。当前入口为 <http://localhost:18764/S5jrCd45BfZKkoQmYa7c0ASfeT12LoLl/>。

2026-10-21 修改固件验证：已用 `D:\sony\work\BODYDATA_all_quiet35.dat`（SHA-256 `549afab7…`）生成候选镜像并启动通过。AP 注册 16 条 beep；ID 1/2/3 的新 Ka/Sha/Kasha 音频从 guest SysSound.bin 读出，事件哈希与修改切片一致；中文 UI 保留。完整 BODYDATA 的 CRC/签名、真机刷写、CP/AIP 和电子快门实际触发仍未覆盖，不能据此认定整包可刷。详见 [修改固件验证](evidence/firmware-validation-allquiet35-20261021/README.md)。

2026-10-19 状态：网页已切换至带卡实例 native117。卡槽 2 的 FAT32 虚拟卡、原厂数据库写入、空卡回放、返回主界面、Fn 和实际重启均已验证。实时取景、自动对焦和照片生成尚未实现。详见 [基础功能进展](BASIC-FUNCTIONS.zh-CN.md) 及 [当前配置验证](evidence/card-profile-promotion.json)。

原先 native104–114 带卡回放卡死的问题已定位至虚拟显示端拒绝合法 EVF 优先级 2；native115/116 修复后的连续操作和显示比对通过。历史记录中的回放失败只适用于修复前的实验。

以下为 2026-10-18 的主界面里程碑和原始显示证据。

最新：已经从原厂冷启动流程完成语言、区域、日期和操作提示向导，显示原厂拍摄主界面。实际画面有 J.FINE、14M、AF-S、MECH、AF ON 和 NO CARD，见 [主界面截图](main-ui.png)。独立 QMP 显示像素与校验过的原厂 AP 快照逐字节一致，见 [主界面验证](evidence/main-ui-native83.json)。已从主界面进入原厂菜单、关闭 Power Save Start Time，再返回主界面；干净内存重新启动后也已重放向导并复现。

关闭省电后，在不输入任何按键的情况下连续观察了 105.167 秒，主界面的相机与触摸框标记持续存在，没有回到全黑；见 [空闲运行验证](evidence/main-ui-stability-native83.json)。该验证允许原厂 NO CARD 指示闪烁和其他指示自动隐藏。

这是原厂拍摄界面叠加层显示成功。中央没有传感器取景数据；实时取景、ISP、自动对焦和拍照仍未实现，不能称为完整相机功能跑通。部分指标会随原厂界面自动隐藏，NO CARD 会闪烁。

当前运行入口为 `http://localhost:18764/S5jrCd45BfZKkoQmYa7c0ASfeT12LoLl/`。重启会自动重新完成首次设置和省电设置；个人设置不持久保存。Start-Camera.cmd 启动已验证的主界面配置，旧 Start-Menu.cmd 保留菜单配置。详情见 [当前主界面使用说明](MAIN-UI.zh-CN.md)。

原厂菜单已经显示并能操作。方向键上下移动、确认进入子菜单、MENU 返回均通过实际运行验证。五张 QEMU 显示缓冲截图，与独立解码的原生 AP 像素逐字节一致。证据在 [按键与显示验证](evidence/menu-and-keys.json)，实际截图为 [原厂菜单](original-menu.png) 和 [原厂子菜单](original-submenu.png)。

此前单独菜单配置退出根菜单会回到黑屏；这个限制不应套用到最新冷启动主界面配置。最新配置的菜单进入和返回主界面已经通过。旧菜单启动器的自动省电设置证据见 [自动省电设置验证](evidence/power-save-native-ui.json)，最新原厂设置画面见 [主界面配置的省电 Off](main-power-save-off.png)。

最新冷启动配置保留原厂 BusPower 和 InfraCrypt 服务，并加载原厂 mcmn_drv.ko，解除此前卡槽检测错误。软件端点保存控制状态和提示音资源；新的 AP 状态消息接收者释放已消费的消息，修复持续绘制时消息池耗尽。它们不执行原始 CP 固件，也不产生传感器图像。早期 native70 的读卡错误截图仅作历史证据保存。

本机已保存 Start-Menu.cmd，可重新打开已验证的菜单演示；使用方法见 README.zh-CN.md。

这次使用 6.02 更新包中未经修改的原始内核、相机应用和界面资源。运行环境是定制 QEMU 11.1.2、派生 initramfs、经过筛选的十项 IMDB 启动配置，以及有限的软件设备模型。菜单入口通过核对 A7M4 自身的 RTTI、构造函数和工厂表后调用原厂生命周期；这不代表真实 BootROM 到相机拍摄系统的完整冷启动。

参考项目固定为 [chocotan/a7c2-re 的该提交](https://github.com/chocotan/a7c2-re/tree/25efb56d7f0c69355f9225d1da50454207532e7f/report/2026-10-17-qemu-native-camera)。A7M4 的地址和协议单独核对，没有将 A7C2 的应用二进制用作 A7M4 运行时。

本机运行数据保存在 `D:\CodexWork\sony-a7iv-qemu` 和 WSL 发行版 `Codex-Z8-Qemu` 中。实验没有连接真实相机、物理存储设备或相机 USB。
