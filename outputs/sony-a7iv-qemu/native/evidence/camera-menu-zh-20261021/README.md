# 原厂相机菜单改为简体中文（2026-10-21）

实例：`language-zh-allfonts-20261021`  
页面：<http://localhost:18764/S5jrCd45BfZKkoQmYa7c0ASfeT12LoLl/>  
运行目录（WSL）：`/opt/sony-a7iv/menu-a7m4/runs/language-zh-allfonts-20261021`  
镜像：`menu-a7m4/language-zh-seed.cpio`，538,057,216 字节，SHA-256 `1f1ba05b0ae1f491dbb33f7c77958d0cedc0516d006e76011950cc703dc6130a`

## 结果

原厂相机 UI、首次设置页和主菜单已经是**简体中文**：

- [语言选择页](language-selection.png)：首次设置的语言列表，高亮项为“简体中文”，
  上一项是“繁體中文”；页面标题“语言”也是中文。
- [原厂菜单](menu-settings-power.png)：`设置 > 电源设置选项`，菜单项如
  “自动关显示屏 / 自动关机开始时间 / 通过显示屏节电 / 自动关机温度”均为中文。
- [主界面](main.png)：首次设置自动重放完成后进入原厂拍摄主界面。

本次自动重放完成，日志出现 `A7M4_ORIGINAL_MAIN_READY`；最终主界面快照
`setup-main/validation.json` 为 123 种颜色、`ramfb_matches_ap_pixels=true`。
这台实例的网页面板标签也仍是中文。

## 关键修改

### 1. 原厂 backup 语言项

`/setting` 的 `Backup.bin` 中，对应原厂设施项 `0x2cf03a6` 的 1 字节数据位于
文件数据偏移 **`0x9b090`**。原值 `1` 是日语；改为 **`25`** 对应“简体中文”
（首次设置列表中已由高亮项核实）。

同时，把 `seed-backup.bin` 和 `seed-setting/Backup.bin` 两处都改为 25。原厂
BK4 文件头 `0x20` 是 4 字节累加校验和：

- 长度取头部 `0x18` + `0x1c` 两个字段之和 = **994,788 字节**；
- 计算时把 `0x20..0x23` 清零，再把长度范围内的所有字节按 32 位累加；
- 日语原值校验和为 `0x0196ada5`；语言字节改为 25 后为 `0x0196adbd`。

不做这一步，备份会被固件视为无效：界面黑屏、首次设置页不出现或无法继续。
本次镜像中两个 seed 文件的 SHA-256 均为
`fdd1ed67a0a2ef08c3d8d0e37ec7ccfffc1bd562d6d7b4f11f217b3df8d5e060`。

### 2. 从固件本体补回中文字体

原厂 `fontlist.dat` 要求：

```
FONT_S_CHINESE  /tmp/images/MYingHeiC-GB18030-SJ_wIcon.ltt
FONT_T_CHINESE  /tmp/images/MYingHeiC-Big5-SJ_wIcon.ltt
```

这两个文件原本只在固件的 `firmware.fdat` 里，路径为
`0800_appli/tmp/images/...`；派生 initramfs 没有把它们放进根文件系统。直接
选择中文时，应用在 `open screen: scr0039_boot -> scr0099_0001` 后退出，画面
全黑——不是中文编码错误，而是字体文件缺失导致 UI 初始化失败。

已从 6.02 的 `unpacked/firmware.fdat` 中按 tar 条目原样提取：

| 文件 | 字节数 | SHA-256 |
| --- | ---: | --- |
| `MYingHeiC-GB18030-SJ_wIcon.ltt` | 2,054,740 | `e25ccca0ea0c4c0837b04e5008496c342f53c98c2a868541ba89eaead9798205` |
| `MYingHeiC-Big5-SJ_wIcon.ltt` | 1,150,740 | `732b896098b8ceed3820ff42e456d0aa87aeba5deb0b39c3ad9f0b72bc7ff6c1` |

两字体文件都带有合法的 LTT 头和内部 `embeddedoffset/embeddedsize`，文件长度
与条目大小完全一致。

启动 `init` 在挂载 `/tmp` tmpfs 后执行：

```sh
mkdir -p /tmp/images
cp -f /usr/share/app/MYingHeiC-Big5-SJ_wIcon.ltt /tmp/images/
cp -f /usr/share/app/MYingHeiC-GB18030-SJ_wIcon.ltt /tmp/images/
cp -f /usr/share/app/MYingHeiC-KSX1001-SJ_wIcon.ltt /tmp/images/
cp -f /usr/share/app/UniversOTS-SJ_wIcon.ltt /tmp/images/
cp -f /usr/share/app/HeiseiKakuGothW5-SJ_wIcon.ltt /tmp/images/
cp -f /usr/share/app/Sony_DI_Icons.ttf /tmp/images/
```

只补两个中文字体仍会在中文页面初始化时崩溃；把 `Sony_DI_Icons.ttf` 及可用的
字体也放进 `/tmp/images` 后，中文界面正常打开。原厂 tar 的 `tmp/images` 本身
就包含 Big5、GB18030 与 `Sony_DI_Icons.ttf`。

### 3. appFw 恢复原版

本次不再使用之前无效的 appFw 语言数组重排。`usr/lib/appFw.so` 已恢复为
`/tmp/appFw.so.orig-language`（SHA-256
`1e1b9202eaa69198f20df03dbfdab2f103b206cc4ebcd2e7bd817e6a710018a2`）。中文
语言项完全走原厂 `backup_set_language` 的同一字节与 BK4 校验格式。

### 4. initrd 尺寸与 DTB

宿主启动器现在按实际镜像大小动态更新 `/chosen/linux,initrd-end`、
`linux,initrd-start` 和 `ramdisk_size`，不再依赖为早期镜像生成的固定 DTB。
本次镜像为 538,057,216 字节，修正后 initrd-end 为 `0x460121a00`，
`ramdisk_size=525447`。修正前内核会报
`VFS: Unable to mount root fs on unknown-block(1,0)`。

## 声音回归验证（同一实例）

在中文界面下按 HALF：`/fw-sounds.json` 记录 `sound_id=4`、
`对焦锁定提示音`、`source=virtual-cp`、`rate=48000`、`samples=3711`。
随后按 SHUTTER：事件序列保持为 1 条，没有新增提示音，符合用户 A7 IV
电子快门无提示音的原厂行为。

## 证据文件

- `language-selection.png` — 原厂首次设置语言列表，简体中文高亮。SHA-256
  `f7dec7906b511b41ce997c92c435a111b33103a8bdd80038f0b726b8f536ef08`
- `menu-settings-power.png` — 原厂中文菜单。SHA-256
  `949577125d0f55d7309e15a25370be6107e40d71979f0e2fbf5a5326d8261201`
- `main.png` — 中文设置完成后的主界面。SHA-256
  `cde143b54920123aee3065c44cf0c880f44d6e14128e52b67a2cd5dc20c657f7`

## 边界

- 这是隔离 QEMU 中的原厂 AP/UI 资源，不连接真实相机、USB、实体卡或固件刷写。
- 中文来自原厂 `string_simplifiedchinese*.uxc` 与固件自带的 GB18030 字体，
  不是网页翻译或宿主合成文字。
- 自动省电参考图是英文版像素，因此本次记录
  `power_save_reference_mismatch`；位置导航和中文页面本身已完成，不能把该
  像素差异当成失败。
- 实时取景、自动对焦和照片保存仍未实现；本证据只证明界面语言和声音路径。
