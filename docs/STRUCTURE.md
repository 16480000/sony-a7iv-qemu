# 工程结构

为保留现有脚本的路径约定，本次整理不批量移动运行文件；通过根目录 README 和本索引提供入口。

```text
VERSION                         固定项目版本 0.1
README.md                       项目概况、完成度与文档导航
CHANGELOG.md                    按日期记录基线和后续实验
NOTICE.md                       上游来源与权利说明
docs/                           结构、复现说明
work/sony-a7iv/                  源码、构建/分析/审计脚本、研究笔记
outputs/sony-a7iv-qemu/
  source/                       内核配置、补丁、QEMU 参考补丁与清单
  evidence/                     早期用户空间与分区验证 JSON
  native/
    runtime/                    当前宿主运行脚本、面板与浏览器检查脚本
    evidence/                   冻结的验证结果、截图和诊断样本
    Start-Camera.cmd            固定带卡基线的本机入口
    *.zh-CN.md                  使用说明、进展、历史状态
```

## 主要源码

| 文件 | 作用 |
| --- | --- |
| [build-reference-qemu.sh](../work/sony-a7iv/build-reference-qemu.sh) | 构建固定版本 QEMU 与上游参考补丁 |
| [sony_scu_dfs.c](../work/sony-a7iv/sony_scu_dfs.c) / [install-scu-model.py](../work/sony-a7iv/install-scu-model.py) | A7M4 SCU 电源模式握手模型及安装 |
| [prepare-menu-a7m4.py](../work/sony-a7iv/prepare-menu-a7m4.py) | 提取、校验 A7M4 资源并准备独立运行目录 |
| [prepare-display-port.py](../work/sony-a7iv/prepare-display-port.py) | 原厂地址核对、显示/控制端点与诊断接收适配 |
| [stage-runtime-a7m4.py](../work/sony-a7iv/stage-runtime-a7m4.py) | 驱动、服务和可选模型配置，生成派生镜像 |
| [native-session.py](../outputs/sony-a7iv-qemu/native/runtime/native-session.py) | 已部署的宿主启动、按键、帧校验、网页与虚拟 CP 音效路径 |
| [panel-server.py](../outputs/sony-a7iv-qemu/native/runtime/panel-server.py) | 回环网页面板、视频输入和模拟回放 |
| [browser-verify.mjs](../outputs/sony-a7iv-qemu/native/runtime/browser-verify.mjs) | 使用本机 Chrome CDP 检查面板并保存证据 |
| [card-audit.c](../work/sony-a7iv/card-audit.c) / [diagnostic-export.c](../work/sony-a7iv/diagnostic-export.c) | 只读卡审计和诊断记录验证/导出 |
| [virtual-photo-capture.c](../work/sony-a7iv/virtual-photo-capture.c) / [prepare-virtual-video.py](../work/sony-a7iv/prepare-virtual-video.py) | 模拟 JPEG 写卡与宿主视频帧准备 |
| [system-sound-model.c](../work/sony-a7iv/system-sound-model.c) / [sound-hook](../work/sony-a7iv/sound-hook/a7m4_snd.c) | 原厂音效资源注册与实验消息观察 |

`work/` 还保留了早期运行脚本副本。宿主当前发布入口以 `native/runtime/` 为准，两处不能假定内容相同。研究笔记保留失败和修正过程，应结合日期与对应证据阅读。

## 保留在本机的内容

固件更新包、分区、initramfs、虚拟卡、生成的视频帧/照片、用户视频、编译产物、常规运行日志和发布工具不进入 Git。`.gitignore` 只排除版本控制，不删除本地文件。冻结在 `native/evidence/` 的诊断与音频样本属于研究证据，保留原始字节。
