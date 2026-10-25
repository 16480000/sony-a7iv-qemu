# 修改固件验证：BODYDATA_all_quiet35（2026-10-21）

验证对象：`D:\sony\work\BODYDATA_all_quiet35.dat`  
文件大小：757,480,856 字节  
SHA-256：`549afab72beb9100821b500bc07f05dc504baf016a03b21b4241932044aa5f05`

这是 `D:\sony\work` 中**最新**的一个修改版（2026-10-09 14:48）。  
候选运行镜像：`menu-a7m4/firmware-candidate-allquiet35.cpio`，538,057,216 字节，
SHA-256 `0ea7b28c55f740597fd94becc1b8cb3343452a0d1e56e7b1a83128ef6dd52736`。  
实例：`firmware-candidate-allquiet35-20261021`  
页面：<http://localhost:18764/S5jrCd45BfZKkoQmYa7c0ASfeT12LoLl/>

## 结论

**通过（仅限 AP 启动、原厂中文 UI、AP 注册表与修改后的前三条快门音效）。**

- 修改版能从原厂首次设置向导进入主界面，日志出现
  `A7M4_ORIGINAL_MAIN_READY`；中文语言页、中文菜单和主界面截图均正常。
- AP 启动时仍注册了 16 条 beep 描述符（ID 1..16），地址与修改版 SysSound.bin
  的偏移一致。
- 修改后的 ID 1/2/3（Ka、Sha、Kasha）确实由 guest 里的 AP 音效表读出并播放：
  48 kHz、volume 4；事件哈希与修改后 SysSound.bin 的对应切片**逐字节一致**。
- CP 应用 `cpapp-b.bin` 未修改；本次验证没有触及 CP/AIP 的实际执行。
- 这不是“整包可刷真机”的验证。BODYDATA 外层 CRC/签名、升级器接受性、CP/AIP
  和真实电子快门触发均未覆盖。

## 修改内容（从包内提取）

### nflasha8 `/cp/SysSound.bin`

- 原版 SHA-256：`dae3d18d37b85a22398573f04090a4a95a97052380f4b2b4402a374516399dfb`
- 修改版 SHA-256：`4bd1b46bcf62f7ba60c6c006a91a9357ecce6c845a966f3536f4f16dcde89abf`
- 差异集中在文件前 `0x1800` 字节；ID 1/2/3 被替换为新的音频，ID 4（对焦锁定）
  未变。
- 修改版各入口切片哈希：
  - ID 1（offset 0, 256 B）：`f1f55108a4c0e9e7dbe5f9254a9562cbe8b0ca740beb0ed3de17baa6c1f6a90f`
  - ID 2（offset 0x100, 2944 B）：`a775a0c549e6d6b069f0557a46a4ab850277dcbd6e4ceeab54c0843072c12268`
  - ID 3（offset 0xC80, 2944 B）：`ac23c3a5362cd146e25e429246e608b228585b25f6fadead34472051637ff9cf`
  - ID 4（offset 0x1800, 3712 B）：`691ead99b54206c601f1725f29e66446645c3a8a9f6062cbe83fc3f2b5ec826d`
    （与未修改版相同）

### nflasha15 `/share/avsystemsound/Dslr_Emnt_High_10FPS_Kasha.bin`

- 原版 SHA-256：`af5ee85594e2b455053e69b9932070a6038406686ac549de4fbd2c54b130d03f`
- 修改版 SHA-256：`ac23c3a5362cd146e25e429246e608b228585b25f6fadead34472051637ff9cf`
- 与 SysSound.bin 的 ID 3 切片完全一致，说明修改版声库与独立 Kasha 资源同步。

### nflasha15 `/lib/appFw.so`

- 原版 SHA-256：`1e1b9202eaa69198f20df03dbfdab2f103b206cc4ebcd2e7bd817e6a710018a2`
- 修改版 SHA-256：`5b22d6b24b335ff157d79db496ff8081a828ab96dcfaa983e1e77bfb1dc90f10`
- 只差 32 字节：
  - LUT 目录字符串 `/PRIVATE/M4ROOT/GENERAL/LUT` → `/PRIVATE/LUT`；
  - `/Private/Sony/PRO/LUT` → `/Private/LUT`；
  - 文件偏移 `0x3139945` 的两字节 AArch64 立即数比较指令变化
    （`1f 00 60 f1` → `1f fc 7f f1`）。
- 本次只验证到“打补丁的 appFw 能启动且不破坏中文 UI”；没有专门验证 LUT
  菜单/导入行为。这个 2 字节补丁的语义也尚未逐条解释。

### CP

`nflasha8` 的 `cpapp-b.bin` 与基线 SHA-256 相同
（`7b9b137d696e5972d20db7f9119076172ed8e0730805d7f0b4c31b87689e2c2b`），
说明本次变体没有改 CP 代码。

## 验证过程

1. 从该包的 `verify_BODYDATA_all_quiet35/fdat_image.bin` 中提取 nflasha15、
   nflasha8；nflasha15 的 ext2 超级块定位在 fdat 偏移 `0x5D2C200`，nflasha8 的
   FAT 引导区在 `0x2B176000`。
2. 用 `debugfs`/`mtools` 把修改后的 `SysSound.bin`、`Dslr_Emnt_High_10FPS_Kasha.bin`
   和 `appFw.so` 放入基于已工作中文 root 的候选 root（保留中文 seed、字体和
   init），重新打包为候选 cpio。
3. 用现有宿主启动器启动候选；动态修正 `/chosen` 的 initrd 大小。
4. 自动重放首次设置：中文语言页 → 日期/提示 → 主界面；无 `FirmwareFault`。
5. 在面板中分别选择“机械 Ka+Sha”和“试听 Kasha”，按 SHUTTER，读取
   `/fw-sounds.json` 并核对事件中的 `encoded_sha256`。

### 声音事件核对

| 触发 | ID | 名称 | 事件 SHA-256 | 与修改版 SysSound 切片 |
| --- | ---: | --- | --- | --- |
| 机械 | 1 | 快门轻响 Ka | `f1f55108…f6a90f` | 一致 |
| 机械 | 2 | 快门动作 Sha | `a775a0c5…c12268` | 一致 |
| Kasha 试听 | 3 | Kasha 快门音 | `ac23c3a5…37ff9cf` | 一致 |
| HALF | 4 | 对焦锁定提示音 | `691ead99…ec826d` | 未修改 |

事件 `source` 均为 `virtual-cp`，速率 48000 Hz，volume 4。  
**注意：** 面板的电子快门默认仍为“静音（原厂）”；以上是通过虚拟 CP 的显式
机械/Kasha 选项触发的音效试听，不是相机在真实电子快门下自动触发。

## 边界与未验证项

- 没有把整包 BODYDATA 交给真实升级器；QEMU 只验证从包内提取的 AP/UI/资源。
- 没有验证 BODYDATA/FDAT 的外层 CRC、签名或升级器接受性。
- 原厂 CP/AIP 未执行。若“电子快门提示音”的触发修改在 CP 中，当前 QEMU 无法
  验证该触发；本变体的 CP 二进制也未修改。
- appFw 的 LUT 目录/2 字节补丁只验证了不崩溃；没有验证 LUT 导入路径的实际
  行为。
- 没有连接真实相机、实体存储或 USB；候选 cpio 不是刷机包。

## 目录中的其他变体

`D:\sony\work` 中还有：

| 文件 | 音频内容 | appFw LUT 补丁 |
| --- | --- | --- |
| `BODYDATA_silent.dat` | ID 1/2/3 为常量（静音） | 部分 |
| `BODYDATA_mod.dat` | 与 silent 相同的音频 | 部分 |
| `BODYDATA_all_silent.dat` | 与 silent 相同的音频 | 是 |
| `BODYDATA_lutdir.dat` | 原始音频 | 是 |
| `BODYDATA_all_quiet35.dat` | 新的自定义 ID 1/2/3 音频（本次验证） | 是 |

如果目标是“验证静音版”，`BODYDATA_all_silent.dat` 是更对应的候选；它的
ID 1/2/3 切片哈希分别是
`4f751f27…d312b8`、`9ca2a473…a6ed20`、`ec9b4ef4…056cc1`，可作为下一轮候选。

## 证据文件

- `language.png`：候选版首次设置语言页（简体中文高亮）。SHA-256
  `f7dec7906b511b41ce997c92c435a111b33103a8bdd80038f0b726b8f536ef08`
- `menu.png`：候选版原厂中文菜单。SHA-256
  `949577125d0f55d7309e15a25370be6107e40d71979f0e2fbf5a5326d8261201`
- `main.png`：候选版主界面。SHA-256
  `cde143b54920123aee3065c44cf0c880f44d6e14128e52b67a2cd5dc20c657f7`
- 候选镜像：`D:\CodexWork\sony-a7iv-qemu\menu-a7m4\firmware-candidate-allquiet35.cpio`
- 运行目录（WSL）：`/opt/sony-a7iv/menu-a7m4/runs/firmware-candidate-allquiet35-20261021`
