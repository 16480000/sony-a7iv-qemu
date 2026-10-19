# A7M4 6.02: Dataflow legacy command 0x0205

Static protocol review, 2026-10-18 (Asia/Shanghai). No VM, public scripts, runtime libraries, or firmware were changed for this review. The private `agent-hardware-readonly.py` reader was extended to inspect the original AP ELF without importing scripts that produce shared output files.

## Key result

`type 0x2001 / cmd 0x0205`, sent to `0x9059000e`, is **VDF service SetTimeCode**. This is established independently by the original AP function-name string and original CP RTTI/handler.

For a valid request, the original CP replies with **cmd `0x1205`**, a **12-byte inner frame**, and **32-bit status `0` at inner offset `+8`**. The original type and header word at `+6` are copied from the request. For the observed request type `0x2001` and `+6 = 1`, the inner normal reply is:

```text
01 20 05 12 0c 00 01 00 00 00 00 00
```

Do not copy `0x0205` unchanged into the reply. Do not use the unrelated ReleaseLock result `0xf000`: this protocol returns native status `0` for this successful acceptance path.

## Original artifacts

- AP: `/opt/sony-a7iv/menu-a7m4/runtime/analysis/menu-root/usr/lib/appFw.so`.
- CP: `/opt/sony-a7iv/menu-a7m4/runtime/analysis/menu-root/cp/cpapp-b.bin`.
- CP length: 16,236,816 bytes.
- CP SHA-256: `7b9b137d696e5972d20db7f9119076172ed8e0730805d7f0b4c31b87689e2c2b`.
- AP addresses below are ELF virtual addresses. CP addresses below are **file offsets**. The reviewed CP's embedded pointer VA corresponds to file offset plus `0x108000`.

## AP request evidence

At AP `0x35bad24`, the function constructs the inner frame. Its diagnostic function-name string at AP `0x4bfb588` is:

```text
void infra_wrapper_bb::detail::vdf_srvc_set_timecode(
  const infra_wrapper_bb::vdf_srvc_set_timecode_in_t&,
  infra_wrapper_bb::vdf_srvc_set_timecode_out_t&)
```

Source-name string at AP `0x4bfa422`: `infra_wrapper_bb_ipsx_ls_branch.cpp`.

Original writes:

| Inner offset | Construction | Evidence |
|---|---|---|
| `+0` | `u16 0x2001` | AP `0x35bad38`, `0x35bad44` |
| `+2` | `u16 0x0205` | AP `0x35bad48`, `0x35bad54` |
| `+4` | `u16 0x001c` (28 bytes) | AP `0x35bad58`, `0x35bad60` |
| `+6` | `u16 1` | AP `0x35bad28`, `0x35bad50` |
| `+8` | first body byte `1` | AP `0x35bad5c` |
| remaining body | initialized to zero; conditional byte at inner `+0x10` | AP `0x35bad40`, `0x35bad64..68`, `0x35bae1c` |

The function passes 28 bytes to AP `0x35d8878` and destination `0x9059000e` at `0x35badac..0x35badc0`. It then receives 12 bytes at AP `0x35badc4..0x35badd0`, extracts inner offset `+8` at AP `0x35baddc`, and maps it through `0x35b7b80`.

The 52-byte OSAL request observed by the parent therefore includes framing beyond this 28-byte inner frame. The outer source/reply token and Dataflow wrapper must be preserved by the parent endpoint implementation; this review does not invent those bytes.

## CP command identity and behavior

Original command declaration at CP file `0x51ee1a`:

```text
0x51ee1a: movw r0,#0x2001
0x51ee1e: strh r0,[r1]
0x51ee20: movw r0,#0x205
0x51ee24: strh r0,[r2]
```

Its command object's original vtable/RTTI region:

```text
file+0xabba40 = 0x00626e1b   declaration method -> file+0x51ee1a
file+0xabba44 = 0x00626e2b   validation method  -> file+0x51ee2a
file+0xabba48 = 0x00626e91   execution method   -> file+0x51ee90
file+0xabba50 = 0x00b83ab0   original RTTI name pointer
file+0xa7bab0 = N3VDF21VdfSrvcCmdSetTimeCodeE
                             VDF::VdfSrvcCmdSetTimeCode
```

Validation at CP file `0x51ee2a..0x51ee8e` reads the body, not the outer header:

- Body byte `+0xc` must be below `3` (`0x51ee3a..0x51ee3e`).
- Body byte `+0` must be nonzero (`0x51ee40..0x51ee42`).
- Body byte `+1` must be below `2` (`0x51ee44..0x51ee48`).
- If a condition fails, this method sends response cmd `0x1205`, body length `4`, with status `1` (`0x51ee58..0x51ee88`).
- On valid input it changes the command state to `1` via the context at vtable offset `+0x74` and returns `0` (`0x51ee4a..0x51ee56`).

The observed AP initialization sets body byte zero to `1`, keeps byte one at `0`, and initializes body `+0xc` to `0`, satisfying these three checks. The exact C/C++ field names of those byte parameters were not recovered and should not be fabricated.

Execution at CP file `0x51ee90`:

```text
0x51ee98: call 0x51eeb8                # dispatch/update work
0x51ee9c: movs r0,#0
0x51ee9e: movw r1,#0x1205
0x51eea2: movs r3,#4
0x51eea4: str r0,[sp,#4]               # status 0 payload
0x51eea8: load context virtual reply method +0x88
0x51eeb0: invoke reply(cmd=0x1205, payload=&zero, size=4)
```

The dispatch/update function `0x51eeb8..0x51ef20` copies five 32-bit words (20 body bytes) into an internal event and publishes it:

```text
0x51eede..0x51eee6: internal header type=0x2001, command=0xf033
0x51eee8..0x51eeee: internal size=0x1c, header +6=1
0x51eef0..0x51eef4: copy original 20-byte request body
0x51ef06..0x51ef0e: endpoint 0x9059000e, selector/mask 4
0x51ef14: call dispatch helper 0xe4b6c
```

Thus status `0` at this command boundary acknowledges acceptance/dispatch of the timecode setting. It is not a hardware readiness measurement or proof that a live video timecode generator is running.

## Exact reply header construction

The CP context is `VDF::MsgAccessor`:

```text
file+0x533d5e constructor -> vptr 0x00bc5da4
file+0xabdda4: context vtable begins
file+0xabde2c = 0x0063bedb -> file+0x533eda (vtable +0x88)
file+0xabde44 -> type name VDF::MsgAccessor at file+0xa7d030
```

Its original reply method at CP file `0x533eda..0x533f52` builds the inner response:

| Reply offset | Original behavior | Evidence |
|---|---|---|
| `+0` | copy original request type | `0x533f02..0x533f0a`; getter at `0x533da2` |
| `+2` | write supplied reply command (`0x1205`) | `0x533f0e` |
| `+4` | `8 + payload_size` (`12`) | `0x533f12..0x533f16` |
| `+6` | copy original request word at `+6` | `0x533f1a..0x533f22`; getter at `0x533db4` |
| `+8` | copy supplied 4-byte status payload | `0x533f26..0x533f2e` |

It checks a nonzero reply destination/context before sending (`0x533ef8..0x533f00`). The outer dispatch uses that original reply context. A byte-correct inner response alone will not satisfy the AP if the Dataflow reply ID or outer destination is lost.

For status `1` (parameter validation failure), only the final four bytes change:

```text
01 20 05 12 0c 00 01 00 01 00 00 00
```

## AP status interpretation

AP `0x35b7b80` explicitly maps native `0` to wrapper result `0` (`0x35b7ba4` -> `0x35b7c78`), while native `1` maps to wrapper `0x96` (`0x35b7ba8..0x35b7bb0`). This agrees with the CP normal execution path returning `0` and validation-rejection path returning `1`.

Other accepted-native values in this generic mapper are not required for command `0x0205` and should not replace the specific original status `0` in its normal reply.

## Implementation consequence / limits

For the current valid initialization request, a stateful endpoint model can retain the original 20-byte timecode settings and return the original `0x1205` / status-`0` frame using the captured Dataflow reply context. Invalid body values should produce status `1`, as the CP validation path does.

This review establishes the command's actual business meaning, validity checks, original inner response layout, and status semantics. It does not establish timing, clocking, downstream event consumption, framebuffer output, or full CP execution. The wrapper byte layout is deliberately left to the parent's live request/response inspection.

