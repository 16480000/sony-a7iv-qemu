# A7M4 6.02 HDMI 0x010a read-only protocol verification

The command is `HDMI::ApiHandler::handle_set_definition`, a selection of HDMI output definition. It is not the separate output-frame-rate command. Its reply is **0x810a**, 12 bytes, with a 32-bit result at +8. Both result 0 and result 1 are explicitly normal results in the original AP. In a disconnected/RSEN-low state, the original CP saves the requested setting and returns **1** without starting video output. Therefore an accepted 810a/1 does not establish a physical HDMI output or a rendered camera UI.

Scope: original `cp/cpapp-b.bin` and `usr/lib/appFw.so`, read only; no firmware, VM, or public runtime-script edits. CP file size 16,236,816; SHA-256 `7b9b137d696e5972d20db7f9119076172ed8e0730805d7f0b4c31b87689e2c2b`. CP addresses below are raw file offsets; runtime VA = file offset + 0x108000; Thumb function pointers additionally have bit 0 set. AP addresses are ELF virtual addresses.

## Business and request

- CP file `0x10f798..0x10f7c0`: reads request byte +8, logs it using inline string at `0x10f7c4`, `ApiHandler::handle_set_definition : definition:0x%x`, then calls `0x57709c` at `0x10f7b6`.
- CP `0x57709c..0x5770b6`: passes the single byte to the current HDMI state through vtable +0x70. The RSEN-low table has its +0x70 at file `0xae228c`, containing runtime Thumb pointer `0x6817af` -> file handler `0x5797ae`. Typeinfo at `0xae22cc` names `HDMI::RSEN_Lo` through name pointer `0xdedcfe`.
- CP `0x5797b4..0x5797c8`, `0x57bd4e..0x57bd66`, `0x57c804..0x57c81c`, `0x57d9d2..0x57d9ea`: byte values 0..4 are retained; values >=5 are normalized to 0. The selected value is saved at `SharedData +0xdc`, using global SharedData pointer at runtime address `0x01228710`.
- AP current function `0x35c2028`: calls constructor `0x35c1e68`; byte +8 is explicitly zeroed at `0x35c2044`; header is type 0x2500, command 0x010a, total length 12, version 1. It sends to `0x909a015a` at `0x35c209c`, with expected reply size 12. Exact legacy request is `00250a010c00010000000000`.
- AP strings include `hdmi_set_definition`, `hdmi_set_definition_hd`, `hdmi_set_definition_qfhd`, `hdmi_set_definition_raw` at `0x4fa95d3`, `0x4fa95e7`, `0x4fa95fe`, `0x4fa9617`. The next wrapper `0x35c20b8` sends the same command with byte +8 = 2. The general wrapper `0x35c1e9c` chooses 0, 2, or 3 from its input settings. This supports definition selection; a complete symbolic enumeration is not required for the current request and has not been asserted here.

## Exact reply and result semantics

| Offset | Size | Value |
|---|---:|---|
| +0 | u16 | 0x2500 |
| +2 | u16 | 0x810a |
| +4 | u16 | 12 |
| +6 | u16 | 1 |
| +8 | u32 | result (0 or 1 on these normal paths) |

The original RSEN-low handler `0x5797ae..0x5797f8` saves the setting, builds those four halfwords at `0x5797cc..0x5797e8`, writes result **1** at `0x5797ec`, and sends 12 bytes via `0x110a14` at `0x5797f0`. It returns no next state. Faithful normal reply in this state:

`00250a810c00010001000000`

Handlers `0x57bd48..0x57bda8` and `0x57c7fe..0x57c85c` compare the previous value at SharedData+0xdc with the normalized request. Same value yields result **1**; changed value yields result **0** and selects a next state (state-manager vtable +0x84 or +0x7c). Handler `0x57d9cc..0x57da24` uses the same old/new comparison and results, but returns no next state. Thus 1 can mean accepted with no active reconfiguration/unchanged; calling it a failure would be incorrect. Conversely 0 is not evidence of a visible external video signal.

The getter handler `0x5797fa..0x579840` replies with command **0x820a**, total length 16, version 1, result **0** at +8, and the saved definition byte at +12. It does not include this byte in the setter's 12-byte reply.

AP `0x35c20a0` reads the reply result; mapper `0x35b7ab8` accepts exactly **0 and 1** as normal (comparison at `0x35b7b1c`, return zero at `0x35b7b28`). Its other mappings are `0xe0000001 -> 0x8d`, `0xe0000002 -> 0x8e`, `0xe0000003 -> 0x8f`, `0xe0000004 -> 0x90`, `0xefffffff -> 0x91`; other values map to 2. No symbolic names for these error enum values have been recovered.

## Practical minimal model and limits

Persist one normalized definition byte, initially matching the chosen CP state, and answer a 2500/010a setter with 2500/810a/12/version1. In the emulated no-cable state, the directly verified RSEN-low branch uses result **1**. Do not invent HPD/RSEN-high, EDID availability, or output-start notifications because this request was accepted. A future 020a getter must return the stored byte in the separately verified 16-byte getter format.

Parent reports native-47 accepted this original-compatible reply and that AP and QEMU remain identically black. This is runtime continuation evidence, not a completed camera UI boot.

Unknowns: complete symbolic DEFINITION enumeration, every error enum name, and real output pipeline availability. They do not change the current request/reply contract above.
