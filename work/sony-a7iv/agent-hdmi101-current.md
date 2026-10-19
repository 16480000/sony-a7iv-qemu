# A7M4 6.02 HDMI 0x0101 read-only protocol verification

**0x0101 is HDMI `handle_set_resolution`, setting five resolution choices (HD, SD, QFHD, UHD, RAW).** The captured body `0000000006000000` is five byte-sized business fields plus three padding bytes, not two u32 business arguments. It requests HD=0, SD=0, QFHD=0, UHD=0, RAW=6. This exact payload comes from the original AP default constructor. In the original CP RSEN-low state, the command saves those choices and replies **0x8101, total length 12, version 1, result 0**. That normal response does not assert cable connection or a working video output.

Scope: read-only original `/opt/sony-a7iv/menu-a7m4/runtime/analysis/menu-root/cp/cpapp-b.bin` and `usr/lib/appFw.so`; no public runtime-script/firmware/VM changes. CP SHA-256 `7b9b137d696e5972d20db7f9119076172ed8e0730805d7f0b4c31b87689e2c2b`. CP addresses below are raw offsets; runtime VA = offset +0x108000; Thumb pointers also set bit 0. AP addresses are ELF VAs.

## Request and parameter proof

Captured complete legacy request (parent, native-47):

`00250101100001000000000006000000`

| Offset | Size | Meaning / captured value |
|---|---:|---|
| +0 | u16 | frame type 0x2500 |
| +2 | u16 | command 0x0101 |
| +4 | u16 | total length 16 |
| +6 | u16 | version 1 |
| +8 | u8 | HD resolution = 0 |
| +9 | u8 | SD resolution = 0 |
| +10 | u8 | QFHD resolution = 0 |
| +11 | u8 | UHD resolution = 0 |
| +12 | u8 | RAW resolution = 6 |
| +13..15 | 3 bytes | padding, zero from AP |

CP parser `0x10f4c8..0x10f53e` verifies that the complete incoming range is at least 16 bytes (`cmp size,#0xf`, branch on <= at `0x10f4d8`). It extracts exactly the five bytes at request+8..12 at `0x10f4dc..0x10f50a`. Its log at `0x10f51a..0x10f528` references string file `0xce248c`: `ApiHandler::handle_set_resolution : hd:0x%x sd:0x%x qfhd:0x%x uhd:0x%x raw:0x%x`. Assertion name string at `0xce2413` spells `HDMI::ApiHandler::handle_set_resolution`.

Parser `0x10f532` calls `0x576f6c`, which invokes current-state vtable +0x54 at `0x576f7a..0x576f7e`. The RSEN-low vtable starts at file `0xae221c`, so +0x54 at file `0xae2270` contains Thumb pointer `0x681315` -> file handler `0x579314`. The same table's typeinfo `0xae22cc` points to name `HDMI::RSEN_Lo` (`name VA 0xdedcfe`).

AP constructor `0x35c1614..0x35c1658` independently constructs the exact 16-byte request. It zeroes +8..11, writes 6 to +12 (`0x35c1618`, `0x35c1644`), and zeroes padding +13..15. Current default wrapper `0x35c165c..0x35c1700` retains these choices, sends 16 bytes to `0x909a015a` at `0x35c16e8`, and expects a 12-byte 8101 reply. This proves RAW=6 is an original default field value, not evidence of an invalid request.

Range interpretation: the parser and RSEN-low setter enforce no resolution enum bounds or cross-field validation. Each field is an unsigned byte; the five values are stored unchanged. There is no clamp or reject for RAW=6 in this path. Semantic support for arbitrary other enum values is a separate question; this report does not invent an unsupported full enum range. AP conversion helpers `0x35b7624..0x35b76f4` and `0x35b76f8..0x35b7778` produce values including 0,3,5,6,8, while factory defaults use 0 and 6.

## Reply and no-cable semantics

CP handler `0x579314..0x579380` copies the five bytes to `SharedData+0x8e..0x92` (global pointer at VA `0x01228710`) without calling HDMI hardware. It then builds:

| Offset | Size | Value |
|---|---:|---|
| +0 | u16 | 0x2500 |
| +2 | u16 | 0x8101 |
| +4 | u16 | 12 |
| +6 | u16 | 1 |
| +8 | u32 | result 0 |

Proof: header construction `0x57934c..0x57936e`, result zero `0x579372..0x579374`, send of 12 bytes at `0x579378` via `0x110a14`. The handler returns 0, meaning no next HDMI state is selected by this method. Exact original-compatible response:

`002501810c00010000000000`

This same save-and-ack method is in eight HDMI state tables (pointer occurrences file `0xae2270`, `0xae23dc`, `0xae2494`, `0xae254c`, `0xae282c`, `0xae28e4`, `0xae299c`, `0xae2a5c`). Another method `0x57d4c2..0x57d52e` also saves all five fields and sends the same 8101/result0 reply. Active-state method `0x1116c0..0x11178e` sends result0 first, then may choose a reconfiguration state if the currently selected definition's resolution changed. A further reply construction at `0x111a30..0x111a5a` likewise uses result0. Thus result0 acknowledges the setting; it does not distinguish outputting from disconnected.

AP `0x35c16ec..0x35c16f4` reads reply result+8 and maps it through `0x35b7ab8`, whose explicit comparisons `0x35b7b1c..0x35b7b28` accept result0 or1 as normal. For this CP command the demonstrated normal setter paths all write result **0**, so it is the justified response for the captured request.

Minimal faithful model: persist the five resolution-choice bytes; on this request reply to source `0x81cf61c5` using endpoint identity `0x909a015a` and the 12-byte frame above. Preserve the emulated no-cable/RSEN-low state; do not invent HPD-high or video output because a resolution setter succeeded. This task supplies a protocol contract, not proof that the complete camera UI or imaging pipeline has booted.

Unknowns: symbolic resolution enum names for all numeric values, actual cable/EDID negotiation, and hardware output support. These do not prevent the correctly scoped no-cable setter response.
