# A7M4 6.02: BB command 0x0164 and VDF 0x020b

Read-only original-firmware review, 2026-10-18 (Asia/Shanghai). No public scripts, firmware, libraries, or VM were changed. AP locations below are ELF virtual addresses; CP locations are offsets in the original `cpapp-b.bin` (SHA-256 `7b9b137d696e5972d20db7f9119076172ed8e0730805d7f0b4c31b87689e2c2b`). Embedded CP pointers map to file offset by subtracting `0x108000` and clearing the Thumb bit when applicable.

## Current synchronous wait: 0x200d / 0x0164

The command sets **panel/display resolution size** through the BB wrapper and VDF display command. The current request body `02 00` supplies a valid selector/mode byte with bit 1 set, plus resolution-size enum `0`. The exact names for the two enum values were not recovered; do not rename them as EVF/panel hardware selection or a specific pixel resolution without further evidence.

The original normal reply is 12 bytes:

```text
0d 20 64 11 0c 00 01 80 00 00 00 00
```

That is type `0x200d`, response command `0x1164`, size `0x000c`, flags `0x8001`, and a 32-bit result `0` at `+8`. This is an OSAL/BB legacy response, not the Dataflow envelope used by the preceding timecode command.

## AP evidence

AP `0x35babc0..0x35bac34` constructs:

| Offset | Value | Evidence |
|---|---|---|
| `+0` | `u16 0x200d` | `0x35babc4`, `0x35babe4` |
| `+2` | `u16 0x0164` | `0x35babe8`, `0x35babf0` |
| `+4` | `u16 10` | `0x35babf4`, `0x35babfc` |
| `+6` | `u16 0x8001` | `0x35bac00`, `0x35bac08` |
| `+8` | `02 00` | `0x35babec`, `0x35bac0c..10` |

Destination is `0x92840747` (`0x35bac14..1c`). The send/receive helper `0x35b8ab4` sets the request's source to a temporary reply queue (`0x35b8b58..60`), sends 10 bytes (`0x35b8b64..6c`), waits on that queue (`0x35b8b8c..98`), and copies 12 response bytes (`0x35b8b9c..ac`). AP reads response `+8` at `0x35bac20` and maps the result using `0x35b6e80`.

The generic AP mapper accepts result `0` as wrapper success (`0x35b6ec8` -> `0x35b6fac`). No `0xf000` result belongs in this reply.

## CP BB handler and exact reply

The BB dispatch branch at CP file `0xab1d2` calls `0xb4e10` for this request. The command's reply constructor has two call sites:

- File `0xab1f2`: immediate rejection/send-error path when `0xb4e10` returns nonzero.
- File `0xabbce`: downstream result/callback path; it forwards the received result word at message `+8`.

Both use original reply constructor **file `0x4f27aa..0x4f27fa`**:

```text
0x4f27b4: preserve result argument in r5
0x4f27c8: movw r0,#0x1164
0x4f27d0: strh r0,[sp,#6]     # reply+2
0x4f27d4: movs r0,#0xc
0x4f27d6: strh r0,[sp,#8]     # reply+4
0x4f27da: movw r0,#0x200d
0x4f27de: strh r0,[sp,#4]     # reply+0
0x4f27e2: movw r0,#0x8001
0x4f27e6: strh r0,[sp,#0xa]   # reply+6
0x4f27ea: str r5,[sp,#0xc]    # reply+8 result
0x4f27f0: call 0xae298        # resolve original return queue and send
```

The helper `0xae298` resolves a return queue from the saved request/callback key at `0xae2a8..0xae2ae`, sets response source `0x92840747` at `0xae2e4..0xae2ee`, copies the original reply bytes, then sends to the resolved queue (`0xae310..0xae314`). Preserving the live request's source/reply queue matters; sending to a guessed application queue is insufficient.

## Parameter processing and actual business meaning

The request-side function is **CP file `0xb4e10..0xb4f12`**:

- It constructs an internal Dataflow frame `type 0x2001 / cmd 0x0118 / size 12 / version 1` at `0xb4e1e..0xb4e3c`.
- It reads/normalizes the first request byte at `0xb4e46..0xb4e84`; for value `2`, it remains `2`.
- It reads the second byte, checks it against `3`, and logs bad values at `0xb4e86..0xb4eaa`.
- It copies both bytes to the internal payload at `0xb4e7e` / `0xb4eb2`.
- Original diagnostic string at file **`0xb4f14`**: `[DISP]:resolution_size = 0x%02x`.
- It sends the internal command to `0x9059000e` at `0xb4eee..0xb4f00`.
- A send error becomes `-1` at `0xb4f04..0xb4f08`; otherwise it leaves the later result to the downstream callback.

The downstream CP command declaration at **file `0x51bc72`** explicitly pairs type `0x2001` with command `0x0118`. Its original RTTI proves the operation:

```text
file+0xabb2d8 = 0x00623c73 -> declaration file+0x51bc72
file+0xabb2dc = 0x00623c83 -> validator   file+0x51bc82
file+0xabb2e0 = 0x00623cc3 -> executor    file+0x51bcc2
file+0xabb2e8 = 0x00b83160 -> name file+0xa7b160
file+0xa7b160 = N3VDF31VdfDisplayCmdSetPanelResolutionE
                               VDF::VdfDisplayCmdSetPanelResolution
```

The validator (`0x51bc82..0x51bcc0`) requires payload byte `0` **bit 1** set. Otherwise it sends response command `0x1118` with native result `1`. It does not interpret that first byte as an integer bound in this check.

The executor (`0x51bcc2..0x51bd38`) requires payload byte `1` below `3`. It calls `0x5317e0` with selector `2` and that resolution enum, returns the helper's result through `0x1118`, and only updates the retained service state on success (`0x51bd06..0x51bd14`). Invalid resolution enum returns `1`.

The lower adapter at `0x5317e0..0x53183c` maps its driver operation's results to native `0`, `1`, or `5`: ordinary completion -> `0`; rejected/invalid branch -> `1`; another lower-layer failure branch -> `5`. The BB callback propagates the result to `0x1164`.

Therefore `status=0` is a faithful normal result for a model that accepts and retains selector `2` / resolution enum `0`. The original code has real error branches; a universal hardcoded success response would not implement the command fully. A successful configuration acknowledgment alone does not prove that any physical LCD/EVF output or framebuffer is active.

## Additional asynchronous registration: 0x2001 / 0x020b

This command is **register EVF temperature information events**, not a second synchronous timecode reply requirement.

Independent original CP evidence:

```text
file+0x51e52c..0x51e538: declare type=0x2001, cmd=0x020b
file+0xabb9bc = 0x0062652d -> declaration file+0x51e52c
file+0xabb9c0 = 0x0062653d -> registration handler file+0x51e53c
file+0xabb9cc = 0x00b83a40 -> RTTI string file+0xa7ba40
file+0xa7ba40 = N3VDF29VdfSrvcCmdSetEvfTempInfoEventE
                               VDF::VdfSrvcCmdSetEvfTempInfoEvent
```

The handler at `0x51e53c` removes older queued registrations of the same type/cmd (`0x51e564..0x51e598`), reads the 8-byte body (`0x51e59a..0x51e5a8`), and retains it through a service method at virtual offset `+0x7d4` (`0x51e5ae..0x51e5b8`). This body contains a 32-bit destination queue plus two event-option bytes (the captured `01,01`; their precise enum/option names remain unknown).

If either option is `1`, the handler examines the current EVF temperature state (`0x51e5d0..0x51e65c`). It may send an initial notification to the registered queue. The notification constructor at `0x51e676` builds **type `0x2001`, notification cmd `0x120c`, size 12, version 1**, with four temperature/status bytes at `+8` (`0x51e680..0x51e6c2`), then routes using the registered queue (`0x51e6ea..0x51e6f8`).

No `0x120b` response is sent by this reviewed registration branch. This agrees with AP `0x35bac98..0x35bad20`: it builds the 16-byte registration with the persistent queue at body `+0`, sends it, releases its temporary sender scope, and returns without calling the Dataflow receive helper.

Do not manufacture a `0x120b` acknowledgment to resolve the current wait. The current synchronous dependency is BB `0x0164` / response `0x1164`.

