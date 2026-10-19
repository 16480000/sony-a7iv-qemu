# A7M4 6.02 CP: 0x403d / 0xf000 read-only review

Reviewed 2026-10-18 (Asia/Shanghai). This is static review of the original CP payload. It does not establish execution of the original CP or of its peripherals.

## Result

- `0x403d` is a **ReleaseLock S2 restriction-mask update command**, with an optional delayed completion reply. It is not a device identifier, audio command, display-init command, or a read of hardware readiness.
- In the request `05003d40020000800080000001000000`, the command sets the `0x8000` restriction bit. A byte flag of `1` means set; other values take the clear path in this handler. The token is `0x80000002`.
- The original CP emits a type-1, code-`0x403d`, 12-byte reply containing that token and `0x0000f000`. In this module, `0xf000` is the normal/no-blocking-result branch, not evidence of an error. The exact original C/C++ enum name is unknown.
- A matching type-1 reply can complete this AP wait, and its bytes match an original firmware reply for an idle S2 arbiter. This **does not** prove that a real CP, capture pipeline, sensor, or display has started.

## Artifact identity / coordinates

Original file:

`/opt/sony-a7iv/menu-a7m4/runtime/analysis/menu-root/cp/cpapp-b.bin`

- Length: 16,236,816 bytes.
- SHA-256: `7b9b137d696e5972d20db7f9119076172ed8e0730805d7f0b4c31b87689e2c2b`.
- All code locations below are **file offsets**, disassembled as little-endian Thumb. An embedded pointer in the reviewed image corresponds to the file offset plus `0x108000`.
- Focused read helper: `work/sony-a7iv/agent-hardware-readonly.py`. It reads the original CP and prints disassembly, immediate matches, pointer matches, and strings. It does not write into the public runtime or source directories.
- REA identity opened successfully earlier; its native provider cannot analyze this ARM ELF on this Windows host (Windows Ghidra provider accepts PE only). This review uses Capstone instructions and raw original data, not provider pseudocode.

## 1. Command route and object identity

The task loop at file `0x2cceb4` receives messages for endpoint `0x90040193` (constant formed at `0x2ccebe` / `0x2cced6`). It reads the message code at `0x2ccefe`. Its `0x4036..0x4040` dispatch table at `0x2ccf5c` sends code `0x403d` through `0x2ccfb6..0x2ccfb8` to handler `0x8d0506`.

The handler's top-level object is at CP VA `0x01410000`. Its subobject at `this + 0x294` is initialized at file `0x8d02b4` with vptr `0x00d28a38`:

```text
file+0x8d02b4: movw r1,#0x8a30
file+0x8d02b8: movt r1,#0xd2
file+0x8d02bc: adds r1,#8
file+0x8d02be: str r1,[r0]
```

Original RTTI chain:

```text
file+0xc20a34 = 0x00d28a40     typeinfo pointer before vptr
file+0xc20a44 = 0x00b93d40     type name pointer
file+0xa8bd40 = N6Camera11ReleaseLock9RelLockS2E
                                  Camera::ReleaseLock::RelLockS2
```

The related arbiter constructor at `0x8d111a` uses vptr `0x00d28a50`. Its type name pointer at file `0xc20a5c` points to `Camera::ReleaseLock::RelS2Arbiter` at file `0xa8bdd0`.

This establishes the command family independently of nearby descriptive strings. The nearby strings agree:

- File `0x2cc518`: `FW: RelMgr) BootCap AcqRelRight ...`
- File `0x2cc5b4` / `0x2cc5f4`: CapIdTblMgr boot-capture checking start/end.
- File `0x2cc71c`: `FW: RelMgr) BootCap FreeRelRight ...`
- File `0xd369fa`: `FW: it is a strange trig in GetS1S2PairTrigger ...`

## 2. Exact request processing

Request decoding:

| Offset | Bytes | Observed role |
|---|---|---|
| `+0` | `05` | Request type |
| `+1` | `00` | Padding/reserved; no semantic use established here |
| `+2` | `3d40` | Command `0x403d` |
| `+4` | `02000080` | Reply/correlation token `0x80000002` |
| `+8` | `00800000` | Restriction mask `0x00008000` |
| `+0xc` | `01` | Set flag |
| `+0xd..f` | `000000` | No semantic use established here |

`0x8d054a` loads the token and mask with `ldrd r8,r5,[message,#4]`; `0x8d054e` reads the flag at message `+0xc`. The mask helpers are trivial original instructions:

```text
0x8d02d2: ldr r2,[r0,#8]; orrs r1,r2; str r1,[r0,#8]  # set mask bits
0x8d02da: ldr r2,[r0,#8]; bic r1,r2,r1; str r1,[r0,#8] # clear mask bits
0x8d02e4: OR into [r0,#0xc]                           # temporary override bits
0x8d02ec: BIC from [r0,#0xc]
0x8d02f6: effective_mask = [r0,#8] & ~[r0,#0xc]
```

`RelLockS2 +8` / `+0xc` field names above are analyst descriptions, not recovered source names.

For the exact source endpoint `0x80020002`:

1. Flag `1` sets the mask (`0x8d0560..0x8d0564`).
2. A mask containing bit 15 (`0x8000`) branches at `0x8d056c..0x8d056e` to `0x8d05bc`.
3. The helper `0x8d1442` reads `RelS2Arbiter +0x19`.
4. If that flag is `1`, `0x8d05ce` saves the token at arbiter `+0x1c` through helper `0x8d143e`; the ACK is deferred.
5. Otherwise `0x8d05d4..0x8d05d6` emits the reply immediately through `0x8d32b2`.
6. If arbiter `+0x18` is set, `0x8d05e4..0x8d05ea` also ORs `0x8000` into temporary overrides. The original flow allows the active arbitration operation to reach its completion path before the new restriction fully applies.
7. The deferred completion paths at `0x8d1408..0x8d1416` and `0x8d1428..0x8d1436` send the same reply for a stored token and then reset token storage to `-1`.

Other source/mask paths should not be generalized from this one exchange. For example the same set handler checks bit 21 separately, and several paths deliberately do not call this ACK helper.

## 3. Exact reply and meaning of 0xf000

Original helper at file `0x8d32b2` allocates a 12-byte message for source `0x90040193`, destination `0x80020002`, then writes:

```text
0x8d32d2: movs r5,#1
0x8d32d4: movw r1,#0x403d
0x8d32d8: strb r5,[reply]
0x8d32da: strh r1,[reply,#2]
0x8d32dc: mov.w r1,#0xf000
0x8d32e0: strd r4,r1,[reply,#4] # r4 is original token
0x8d3310: call message send
```

All five direct BL callers are at `0x8d0576`, `0x8d058a`, `0x8d05d6`, `0x8d140e`, `0x8d142e`. This helper contains no computation of a hardware error and no alternate result assignment.

For token `0x80000002`, a zero reserved byte yields:

```text
01 00 3d 40 02 00 00 80 00 f0 00 00
```

An independent branch in the **same ReleaseLock module** distinguishes `0xf000` and `0xf001`. Handler `0x8d0dea` (task dispatch `0x2ccfce..0x2ccfd0`, code `0x4040`) calculates:

```text
0x8d0e06: effective = set_mask & ~override_mask       # helper 0x8d02f6
0x8d0e0a: requested = request[8]
0x8d0e24: blocked = requested & effective
0x8d0e28: result = 0xf001
0x8d0e34: IT EQ                                    # blocked == 0
0x8d0e36: result = 0xf000                           # no requested restriction active
0x8d0e3a: reply[4]=token; reply[8]=result
0x8d0e3e: reply[0xc]=blocked
```

This gives strong local evidence that `0xf000` is the favorable/normal completion result; calling the `0x403d` reply an error would be incorrect. It does **not** recover a literal Sony enum name such as `RESULT_OK`, so use the numeric value and its demonstrated branch meaning.

Additional consistency: CP file `0x90ee7a..0x90eeaa` constructs a type-1 reply choosing `0xf000` for a true/nonzero condition and `0xf001` for false/zero. It supports the branch interpretation, but it is not needed to establish this command's identity.

## 4. Consequences for a software endpoint model

For a CP endpoint model handling this exact AP cold-start request:

- Record the `0x8000` bit in its S2 release-lock state.
- With no capture/S2 arbitration in flight, emit the original normal reply immediately, preserving source, destination, code, and token.
- If actual S2 activity is modeled, preserve the original delayed-token behavior. Do not universally ACK unknown message codes or unknown sources.
- A trace should say **“ReleaseLock S2 mask 0x8000 set; emulated endpoint sent firmware-format normal completion”**, not “CP/audio/display hardware initialized”.

This reply is consistent with an idle S2 arbiter. An implementation that sends only bytes without retaining the restriction state may unblock the AP, but it is not a complete implementation of the command's side effects.

## Unknown / unproven

1. The original symbolic enum name for `0xf000` and its exact global result taxonomy.
2. The exact named enum for restriction bit `0x8000`; its use in S2 arbitration is established, but a user-facing reason such as power/media/mode should not be invented.
3. AP's full later consumption of this reply and the later live/capture behavior, not traced in this CP-focused review.
4. Original CP execution, framebuffer output, physical input routing, image pipeline, or complete camera startup. Static reply construction and AP continuation do not establish these.

