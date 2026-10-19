# A7M4 6.02 AP request 0x2500/0x0101: read-only review

Reviewed 2026-10-18. No shared code, firmware, observer, or VM was modified.

## Conclusion

The next cold-boot request is the factory API **`hdmi_init_resolution`**. Its original AP implementation deliberately sends the fixed 16-byte initialization packet observed in `native-47-hdmi`:

```
00 25 01 01 10 00 01 00 00 00 00 00 06 00 00 00
```

The original response is **12 bytes**, `0x2500 / 0x8101 / 12 / 1`, with a native four-byte result at offset 8. The same factory HDMI result mapper accepts native `0` or `1` as success.

The apparent two words `(0,6)` must not be treated as a proven pair of 32-bit enum fields. AP writes the payload as individual bytes. Neighboring resolution setters address bytes 8, 9, 10, 11, and 12 independently. The AP evidence establishes the business purpose and wire bytes; it does not preserve the exact C++ enumerator names or all slot names for `0` and `6`. The CP decoder is the appropriate independent source for those names and complete admitted ranges.

## Trace-name and boot evidence

Original binary: `/opt/sony-a7iv/menu-a7m4/runtime/analysis/menu-root/usr/lib/appFw.so`, SHA-256 `1e1b9202eaa69198f20df03dbfdab2f103b206cc4ebcd2e7bd817e6a710018a2`.

The factory trace-name table at file offset `0x582a448` holds method `0x87`, pointing to string VA `0x4fa9564`, exactly `hdmi_init_resolution`. Wrapper `0x359ae5c` records trace `(category=0, method=0x87)` and calls detail implementation `0x35c165c` at `0x359ae84`.

In `model::sequence_boot::run_i()`:

```
0x317a038  call hdmi_set_definition_hd
0x317a03c  check its business result
...
0x317a0b0  call 0x359ae5c  // hdmi_init_resolution
0x317a0b4  check result at FP+0x130
```

A failure at the latter check logs `sequence/sequence_boot.cpp` line `0x65b`; it is separate from the previous definition check at line `0x647`.

`native-47-hdmi/console.log` line 41634 records the actual request as frame `0x2500`, command `0x101`, bytes `16`, flags/version `1`, value `0`, source `0x81cf61c5`, following the accepted definition request at line 41627. The full body supplied by the parent matches the original constructor exactly.

## Exact constructor and field widths

`0x35c1614` initializes a request object using byte stores:

| Offset | Factory initialization | Evidence |
|---:|---|---|
| 0..1 | `0x2500` | header |
| 2..3 | `0x0101` | request command |
| 4..5 | `16` | total request length |
| 6..7 | `1` | version/flags |
| 8 | `0` | `strb wzr,[x0,#8]` |
| 9 | `0` | byte store |
| 10 | `0` | byte store |
| 11 | `0` | byte store |
| 12 | `6` | `strb w2,[x0,#0xc]`, w2=6 |
| 13..15 | `0` | byte stores |

`0x35c165c` ignores its input object, invokes that constructor, and repeats the same fixed values. Therefore this is an initialization/reset-to-default operation, not reading two arbitrary model parameters from the caller.

AP format context:

- General `hdmi_set_resolution`, detail `0x35c1704`, computes a one-byte native format. It copies that byte to offsets **8, 10, and 11**, explicitly clears offset 9, and clears offset 12.
- `hdmi_set_resolution_qfhd`, detail `0x35c1820`, initializes the same object and updates offset **10** only; the constructor's offset-12 default of 6 remains.
- This conversion is corroborated by the original diagnostic string at `0x4bfcb98`: `HDMI::FORMAT infra_wrapper_bb::detail::convert_hdmi_resolution(model::setting_output_resolution_t)`.
- The inlined conversion admits native byte values including `0`, `3`, `5`, `6`, and `8`, depending on the model input. Thus `6` is a valid native HDMI-format-related value, not a generic success code or connection state.
- Exact enum spellings such as `AUTO`, `D5`, or `1080P` are **not** directly retained in the examined AP code/string evidence. Calling 0 automatic and 6 1080p is plausible, but should remain an inference until corroborated by CP. It is especially unsafe to infer the complete wire layout from those two labels alone.

## Completion and mapper

At `0x35c169c` onward the initializer prepares a separate result object:

```
header: 0x2500, 0x8101, 12, 1
result: 0xefffffff initially
```

It invokes the original transport helper at `0x35c16e8` with destination `0x909a015a`, request length `16`, and completion copy length `12`. The transport allocates a temporary reply queue, sets the actual request source, sends the message, then performs an infinite receive. Completion must go to that request source, not the separately retained HDMI notification destination.

At `0x35c16ec` it reads the four-byte native result at response offset 8 and calls mapper `0x35b7ab8`:

| Native result | AP business result |
|---:|---:|
| `0` | `0` |
| `1` | `0` |
| `0xe0000001` | `0x8d` |
| `0xe0000002` | `0x8e` |
| `0xe0000003` | `0x8f` |
| `0xe0000004` | `0x90` |
| `0xefffffff` | `0x91` |
| other unrecognized values | `2` |

The initializer writes that business result to its caller output. There is no returned format payload in this completion.

## Minimum implementation boundary

Until the independently analyzed CP supplies full enum/slot semantics, the strictly supported cold-boot operation can admit **only** the exact factory `0x2500/0x0101/16/1` initialization packet above. Preserve all five addressed configuration bytes in endpoint state; do not collapse the whole request into a single resolution or overwrite actual negotiated output state.

The native status should follow the real CP disconnected-state behavior. A verified `0` or `1` will be accepted by AP, but its choice is a receiver-state decision, not justification for generic acknowledgement. Return the 12-byte `0x8101` completion once, to the actual dynamic source. Keep cable disconnected and link/output inactive unless another verified operation changes them.

Do not automatically admit later general setters merely because they share command `0x0101`; their payloads update distinct byte slots and require the CP's field/range interpretation. Do not fabricate output-format notifications or hotplug while completing this default initialization.
