# 网页 JPEG 回放层与合成系统音（2026-10-21）

实例：`web-video-20261021f`（WSL `Codex-Z8-Qemu`，QEMU 原厂 6.02 AP）
页面：http://localhost:18764/S5jrCd45BfZKkoQmYa7c0ASfeT12LoLl/

## 实测

使用本机 Chrome（CDP，非 MCP）加载用户视频 `10月3日.mp4`，走网页视频输入，
按下网页快门并点回放：

- 浏览器取当前视频帧生成 JPEG，补到 65,536 字节；网页到 guest 的串口桥把它写入
  虚拟卡 FAT32 中的 `DSC00001.JPG` 数据区（offset 2,083,328），helper 返回 0。
- 回放覆盖层显示 `DSC00001.JPG`、`1/1 · JPEG` 和 `MENU 返回`；点返回后覆盖层隐藏，
  回到取景。回放不向 guest 发送 PLAY，因此原厂 OSD 不会变黑。
- QEMU 扫描帧在整轮前后 SHA-256 相同（`707f200e...`）；原厂界面仍保持取景。
- Web Audio `AudioContext` 状态为 `running`。振荡器启动计数：系统音开关测试后为 1，
  快门+进入回放后为 3，返回后为 4。说明按键/快门/回放路径确实在合成声音。
  未录制实际声卡输出，仅验证音频调度执行。
- 转码输出经 ffprobe 确认为 H.264 640×264 + AAC 44.1 kHz 双声道；浏览器里用
  “开启声音/关闭声音”控制视频音轨。

## 范围与诚实说明

- 回放界面是**网页虚拟层**，不是原厂固件的 JPEG 回放 OSD。照片显示用浏览器自己
  捕获的 JPEG，并没有经过原厂 CP/JPEG 解码器。
- 系统音是 Web Audio **合成音**，不是原厂 `SysSound.bin`/`.bin` 采样；原厂 AA 类
  压缩音频代码目前仍未解码或接入 guest 音频路径。
- JPEG 写卡是真实完成的（虚拟卡文件内数据），并已由 guest helper 验证大小/读回。
- 播放画面的上半/下半黑边一部分来自 640×480 取景画布的黑底（视频按比例居中），
  覆盖层状态栏也在这些黑边上。

## 文件

- `page-photo-playback.png`：回放覆盖层实际页面截图
- `page-photo-return.png`：按 `MENU 返回` 后恢复取景的页面截图
- `guest-frame-final.png`：返回后 guest 原厂扫描帧
- `report.json`：完整 CDP 报告（含音频探测、覆盖层断言、帧哈希）
- `summary.json`：关键结果摘要
