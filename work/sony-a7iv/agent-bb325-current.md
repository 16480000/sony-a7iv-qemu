# A7M4 6.02 BB 0x0325 / 0x1325: ADF audio function availability

**0x0325 queries audio function availability (`adf_get_func`), not imaging or general camera capabilities.** Its 28-byte 0x1325 reply contains a result word at +8 and 16 audio-function bytes at +12. Ordinary function bytes use 0 for available and 0x80 for unavailable; the low-cut byte also admits 0x81, representing a distinct AVIO-backed low-cut capability path. Availability and query result are independent.

For the current emulator, which has no virtual microphone or audio-capture implementation, an explicit all-unavailable audio-function profile is justified. A normal query-result 0 with all 16 function bytes = 0x80 is compatible with the original API. This describes emulator capabilities; it is **not a recovered physical A7M4 capability table**. Returning zero for all 16 fields would instead advertise unsupported audio controls as available.

Read-only evidence: original `/opt/sony-a7iv/menu-a7m4/runtime/analysis/menu-root/cp/cpapp-b.bin` (SHA-256 `7b9b137d696e5972d20db7f9119076172ed8e0730805d7f0b4c31b87689e2c2b`) and `usr/lib/appFw.so`. CP addresses are raw file offsets, runtime VA = offset +0x108000; Thumb pointers also set bit 0. AP addresses are ELF VAs. No public scripts, firmware, or VM changes.

## Current transaction and forwarding

Parent captured native-49 request `0d20250308000180`, destination 0x92840747, expected reply 28 bytes. AP `0x35bb464..0x35bb4b8` constructs exactly BB type0x200d/cmd0x0325/length8/flags0x8001 and calls the synchronous BB sender with reply length0x1c. Wrapper `0x359a55c..0x359a598` calls this function. Original AP string `adf_get_func` is at VA `0x4fa92a4`; its output model is `ds_adf_availability_t` (RTTI/name strings in the ELF).

CP `0xb2764..0xb27b2` constructs downstream **type0x2004/cmd0x0128/length8/version1**, sends to **0x9058003f** with return source **0x928407b9**. Inline failure string at file `0xb27b4` is `SendADF_ProcGetFunc ERR_FATAL`. The audio processor replies 0x8128, then BB converts that response to 0x1325 using method `0xafd3c..0xb032a` (called at `0xabd60`). The broad numeric cmd0x0325 occurring in VDF/2001 code at `0x51c586` is a different protocol; it must not be used to model BB/200d/0325.

## 28-byte reply contract

| Offset | Type | Field | Normal values |
|---|---|---|---|
| +0 | u16 | BB frame type | 0x200d |
| +2 | u16 | response command | 0x1325 |
| +4 | u16 | total length | 28 |
| +6 | u16 | flags/version | 0x8001 |
| +8 | u32 | query result | 0 on successful query |
| +12 | u8 | inProSetIntMicSens | 0 / 0x80 |
| +13 | u8 | inProSetInputType | 0 / 0x80 |
| +14 | u8 | inProSetInputTrim | 0 / 0x80 |
| +15 | u8 | inProSetChSource | 0 / 0x80 |
| +16 | u8 | inProSetRecLevelMode | 0 / 0x80 |
| +17 | u8 | inProSetAgcLink | 0 / 0x80 |
| +18 | u8 | inProSetManualGainLink | 0 / 0x80 |
| +19 | u8 | inProSetRecLevelLimitter | 0 / 0x80 |
| +20 | u8 | inSetLowCut | 0 / 0x80 / 0x81 |
| +21 | u8 | inSetWindNr | 0 / 0x80 |
| +22 | u8 | inSetIvoice | 0 / 0x80 |
| +23 | u8 | inSetMyvoiceCanceling | 0 / 0x80 |
| +24 | u8 | inSetPremiumCloserVoice | 0 / 0x80 |
| +25 | u8 | prcSetZoomNrEe | 0 / 0x80 |
| +26 | u8 | inProSetShoeMic | 0 / 0x80 |
| +27 | u8 | inSetWindNrMode | 0 / 0x80 |

Header and result construction: CP `0xafd5c..0xafd80`. Reply source fields are copied from downstream reply +12..27. Ordinary value checks explicitly accept 0/0x80 before copying (`0xafd8a..0xafdfc` and subsequent repeated branches through `0xb0124`). Low-cut has a special 0x81 check at `0xb0088..0xb00b8`. Sending the final 28 bytes occurs at `0xb0318..0xb0320` via BB reply helper `0xae298`.

The names and order are embedded as original diagnostic strings: file `0xcd2b32..0xcd2d1e` lists the first 13; file `0xb032c`, `0xb0358`, `0xb0384` supplies ZoomNrEe, ShoeMic, WindNrMode. They match the response stores and diagnostic arguments in the converter.

## Why 0x80 means unavailable, and why result can remain zero

This is not inferred only from BB accepting the bytes. Original capability builders calculate 0x80 from unsupported lower-layer capabilities while returning **0** as the operation result. Example CP `0x4bc532..0x4bc566` queries AIP capability through `0x65bc0`; when its capability word equals1, the result function byte is0; otherwise it writes0x80 at `0x4bc558..0x4bc562`, then returns0. A lower-layer query error instead returns0xefff (`0x4bc54e..0x4bc554`). Other feature builders follow the same separation of query error and function availability.

AP `0x35bb4bc..0x35bb568` independently converts selected fields into its availability model. Examples:

- reply+13 ==0 -> output-model byte+0xb=true;
- reply+20 ==0 -> output+7=true, while reply+20 ==0x81 -> output+6=true;
- reply+21 ==0 -> output+0xd=true;
- reply+24 ==0 -> output+0xc=true;
- reply+23 ==0 -> output+0x13=true;
- reply+25 ==0 -> output+0x14=true.

Some AP flags are inverse pairs (for example reply+12 populates both !=0 and ==0 flags at output+4/+5), so an unavailable profile does not imply every output-structure byte becomes zero. Output+0x15 is unconditionally set to1 by AP at `0x35bb55c..0x35bb560`. These are AP-side modeling details, not extra capabilities supplied by the CP reply.

The ADF handler `ProcMsgGetFunc` at `0x65a80..0x65ae0` copies its cached function block when the accumulated error at object+0x50 is zero and chooses query result0 (`0x65ac2..0x65ace`). If object+0x50 is nonzero, it follows the error path and replies0xefff. The cached individual 0x80 values are not consulted when deciding query result. `0x4bfd7a..0x4bfe04` builds the downstream 32-byte 2004/8128 reply and overwrites its +8 with the separate query result.

Therefore a virtual implementation can successfully answer what functions it implements, with result0 and every function unavailable. This does not require simulating a failed query or pretending that a physical microphone exists.

## Original data sources and the special low-cut 0x81

`0x4bfd70` returns the persistent `ProcMsgGetFunc` object at runtime VA **0x00f43678**. Its function storage is object+0x38..0x4f; the reply's 16 named fields derive from object+0x3c..0x4b. The object also caches lower-layer AVIO/AIP queries and an accumulated error at+0x50.

- `0x65b0c..0x65b92` obtains/caches AVIO function information: calls the AVIO provider from `0x558264`, virtual+0x1c, with command selector **0x0b**.
- `0x65bc0..0x65c32` obtains/caches AIP function information: dispatches selector **0x124** through the AIP provider `0x381484(1)`, virtual+0x24.
- `0x65c5c..0x65ccc` obtains/caches AIP ZNR information: selector **0x205** through `0x381484(2)`, virtual+0x24.
- `0x65d00..0x65e14` stores derived per-function availability and propagates initialization errors. For example selector0x422 updates cached LowCut at object+0x44.

Low-cut capability constructor `0x4bae7e..0x4baee6` first queries AIP ZNR info. If its word is3 it sets low-cut availability0x80 (`0x4baeaa..0x4baeb4`). Otherwise it queries AVIO function data; if the relevant AVIO word is zero it sets **0x81**, and when nonzero it sets **0** (`0x4baec6..0x4baed0`). It stores selector0x422 through `0x65d00` at `0x4baeda..0x4baede`. Together with AP's separate tests for0 and0x81, this proves 0x81 is a **distinct supported low-cut implementation capability**, not a generic failure. The exact symbolic enum names and whether the UI names it frequency-selection or a particular filter mode have not been recovered, so those names are not asserted.

The CP file's static initializer at file `0xe3b678` has the object vptr and otherwise zero function storage (`0xe3b6b0..0xe3b6c7`). Those bytes are **pre-initialization storage**, not a trustworthy physical-camera default capability response: boot functions later populate them from AVIO/AIP. No runtime physical microphone capability data was read in this task.

## Explicit no-audio model response

For the parent-reported current virtual machine, use query-result0 and all16 function bytes0x80:

`0d2025131c0001800000000080808080808080808080808080808080`

Length:28 bytes. This is an explicit emulator capability profile, preserving unsupported functions as unsupported. It is not a claim about the physical A7M4's capabilities. Use0x81 only after implementing and deliberately exposing the corresponding low-cut implementation; the current no-audio profile needs no0x81 value.

Remaining unknowns: exact physical runtime AVIO/AIP capability words; symbolic low-cut0x81 enum name; future audio requests sent independently of these availability flags. Successful acceptance of this query by AP still requires parent runtime verification.
