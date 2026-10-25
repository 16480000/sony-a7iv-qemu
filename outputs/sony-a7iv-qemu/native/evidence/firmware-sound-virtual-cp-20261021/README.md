# 固件注册音效 → 虚拟 CP → 浏览器播放（2026-10-21）

实例：`sound-cp-zh-20261021`  
页面：<http://localhost:18764/S5jrCd45BfZKkoQmYa7c0ASfeT12LoLl/>  
运行目录（WSL）：`/opt/sony-a7iv/menu-a7m4/runs/sound-cp-zh-20261021`  
镜像：`menu-a7m4/sound-live-test.cpio`（SHA-256 见运行目录 `runtime-artifacts.json`）

> 2026-10-21 后续更新：同一套固件音路径已在原厂相机菜单为**简体中文**的实例中
> 回归验证（HALF → ID 4 FocusLock 48 kHz；电子快门静音）。相机菜单中文的
> 备份项/字体修复见
> [camera-menu-zh-20261021](../camera-menu-zh-20261021/README.md)。

## 校准结论（2026-10-21）

用户试听校准页后确认 **FocusLock 48K** 正确。由此把 live 路径从固定
16 kHz 改为按固件条目头自动选率：`0x17` → 48 kHz，`0x07` → 16 kHz。
Kasha 也是 `0x17`，但用户指出 **A7 IV 电子快门原厂没有提示音**，因此 live 默认改为
“电子快门静音”；Kasha 只保留为虚拟 CP 的试听实验项。机械快门 Ka+Sha 仍可手动选择。

## 本次实现

- 从原厂 AP 启动日志解析真实注册的 beep 表：
  `BOOT_LOG_SOUND_DESCRIPTOR id=… address=… bytes=…` 与
  `BOOT_LOG_SOUND_VOLUME sound_id=… volume=…`。当前 16 个 ID 全部 enabled。
- HALF（半按）触发 **FocusLock**（ID 4，地址 `0x41ea01800`，3712 字节）；
  SHUTTER（原厂快门）按页面选择触发注册音效：
  默认电子快门静音（原厂行为）；机械 Ka+Sha（ID 1/2）、试听 Kasha（ID 3）、
  Kasha 连续（ID 7）为显式虚拟 CP 选项。
- 宿主用 QMP `pmemsave` **从 guest 物理内存**读取描述符指向的 SysSound.bin
  字节，再生成 8 kHz / 16 kHz 两版 WAV，通过回环页面播放。不是读取旧的
  `native/runtime/sounds` 候选，也不是网页独立合成音。
- 原厂 AP 的 `adf_sys_request`（BB `200d/0329`）也已在 guest observer 中接入：
  若原厂 AP 真的发出请求，会显示 `来源=AP` 并走同一播放路径。
- 面板明确区分来源：`来源=AP adf_sys_request` 与
  `来源=虚拟CP 注册表`。

## 证据

- `browser-report-zh-silent.json`：中文界面 + 电子快门静音默认；HALF 只产生
  FocusLock 48 kHz，SHUTTER 不产生宿主音效；AudioContext running，plays=1。
- `page-zh-silent.png`：中文面板与“电子快门静音（原厂）”状态。
- `browser-report-48k.json`：48 kHz 自动率版本，Chrome headless + CDP，点击 HALF、SHUTTER 后：
  - `window.__fw.ctx = "running"`
  - `window.__fw.plays = 2`
  - `window.__fw.last = {name:"Kasha", rate:48000, duration:0.061}`
  - 事件序列：ID 4 Focus Lock → ID 3 Kasha
  - 无页面错误、无 AudioContext 错误。
- `browser-report.json`：更早的 16 kHz 版本，保留作对比。
- `48k/fw-sound-1-48k.wav`、`48k/fw-sound-2-48k.wav`：48 kHz FocusLock / Kasha 渲染。
- `page-48k.png`：48 kHz 自动率面板状态。
- `page.png`：新的固件音面板与事件状态（`固件音 #2 · Kasha · 184 ms`，
  来源=虚拟CP 注册表，`addr=0x41ea00c80 len=2944 volume=4`）。
- `fw-sound-1.bin` / `fw-sound-1-16k.wav`：FocusLock 条目的 guest 字节与
  渲染结果；SHA-256 `691ead99…`。
- `fw-sound-2.bin` / `fw-sound-2-16k.wav`：Kasha 条目与渲染结果；
  SHA-256 `af5ee855…`。
- `fw-sounds.jsonl`：事件审计。

## 关键限制（不要当成原厂 CP/AIP 已运行）

- 原厂 CP/AIP **没有执行**；测试中 MENU、HALF、SHUTTER 都没有让原厂 AP
  发出 `200d/0329 adf_sys_request`。原厂 UI/快门/对焦提示音主要由未运行的
  CP 触发，因此本实现用“虚拟 CP”在真实原厂按键动作上触发 AP 已注册的
  音效，并读取 guest 固件资源。
- 因此 **触发时序是近似**：半按的“对焦锁定”是虚拟锁定，不是真实 AF 传感器
  /对焦结果；相机仍在 MECH 模式，机械/电子音效由页面选择，不是从相机模式
  读取的自动判定；MENU/UI 的 CP 原生提示音尚未触发。
- **电子快门原厂静音**：默认不播放任何音效，避免把 Kasha 误当成电子快门提示音。
  若要通过固件给电子快门新增提示音，需要先确定改哪个资源/ID 以及 CP 的触发
  路径；页面里的“试听 Kasha”只是虚拟 CP  audition，不代表固件已会响。
- **解码仍不是原厂 AIP**：每个 SysSound 条目跳过一个 1 字节头后按 8 位有符号
  PCM 渲染。用户已校准确认 **FocusLock 48 kHz** 正确；同组 `0x17` 用 48 kHz，
  `0x07` 组按 16 kHz。这个结果很可能是 AA_RT 条目的真实率/布局，但原厂
  CP/AIP 解码器仍未执行，音色与 AIP 处理仍可能有差异；音效字节、注册表、
  描述符和音量来自 guest 固件。
- 旧的网页候选（合成哔声、8k/16k 实验解包、自定义文件）仍在页面下方，但已
  明确标为“旧实验，与固件反馈无关”。

## 下一步

1. 运行/逆向 CP 的按键与 AF/shutter → beep 触发表，替换虚拟 CP 的按键映射。
2. 用校准结果继续验证 Kasha / 0x07 组 16k；把 AA_RT 解码器与 AIP 处理补实。
3. 从相机状态读取实际快门类型（MECH/ELEC）并自动选择音效；验证 Kasha 是否为电子快门真实提示音。
4. 接入 CP 原生的菜单/UI 提示音。
5. 若要验证固件改动：修改 guest `/usr/share/avsystemsound/SysSound.bin`（或
   相应 per-sound 资源/beeplist）并重启，原厂 AP 会重新注册描述符；宿主按
   新描述符和 guest bank 播放，因此改动会反映到声音。
