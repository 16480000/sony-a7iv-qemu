# A7M4 6.02 AP HDMI definition request: read-only review

Reviewed 2026-10-18. No firmware, shared script, observer, or VM was changed.

## Conclusion

The blocked `0x2500 / 0x010a` request is **`hdmi_set_definition_hd`**, selecting the HDMI output definition as HD. The adjacent helper with payload byte `2` is **`hdmi_set_definition_qfhd`**. These are configuration operations, not hotplug state changes, connection tests, or output-enable commands.

The minimum model can preserve the requested definition while HDMI remains disconnected and return the original completion to the request's actual source queue. It must not manufacture a cable-connect event or active HDMI output. Parent-supplied independent CP evidence establishes that the disconnected receiver stores the definition and returns native status `1`; AP independently accepts this as success.

## Binary and captured execution

Examined original `appFw.so` SHA-256 `1e1b9202eaa69198f20df03dbfdab2f103b206cc4ebcd2e7bd817e6a710018a2` at `/opt/sony-a7iv/menu-a7m4/runtime/analysis/menu-root/usr/lib/appFw.so`.

`native-46-resolution/console.log` line 41621 captures:

```
HDMI_PHOTO_REQUEST tid=308 frame=0x2500 command=0x10a bytes=12 flags=0x1 value=0 source=0x81cf61c5
```

The captured request matches the exact factory constructor in `0x35c2028`. The run ended after its bounded 45-second observation, with `bootstrap_complete=true`, `backup_loaded=true`, `app_init_entered=true`, and `exception=false`; the stack's `0x35b8b9c` return PC is the instruction after a blocking receive, not an abort site.

## Business identity from two independent AP structures

The wrapper at `0x359afdc` records trace category `0`, method `0x8d`, calls detail helper `0x35c2028`, and records method return at `0x359b008`. The neighboring wrapper at `0x359b01c` records method `0x8e` and calls detail helper `0x35c20b8`.

The original trace-name table supplies exact method names:

| Method | Name-table file offset | Original name string VA | Name |
|---|---:|---:|---|
| `0x8c` | `0x582a498` | `0x4fa95d3` | `hdmi_set_definition` |
| `0x8d` | `0x582a4a8` | `0x4fa95e7` | `hdmi_set_definition_hd` |
| `0x8e` | `0x582a4b8` | `0x4fa95fe` | `hdmi_set_definition_qfhd` |
| `0x8f` | `0x582a4c8` | `0x4fa9617` | `hdmi_set_definition_raw` |
| `0x90` | `0x582a4d8` | `0x4fa962f` | `hdmi_set_output_bitwidth` |

Each table entry is the method ID and name length in the first eight bytes, followed by the name pointer. These file offsets belong to the second LOAD, so their ELF VAs are file offset+`0x10000`.

The cold-boot caller is `model::sequence_boot::run_i()`: `0x317a038` calls the HD wrapper; `0x317a03c` loads the result from its output object, and a nonzero business result enters the common fatal logger with source line `0x647`.

The direct HD wrapper has one direct call in the inspected executable range, the cold-boot call above. QFHD has two direct calls:

- `0x3182b18`, inside the routine whose factory diagnostic string is `void model::sequence_change_hdmi_resolution::set_hdmi_4k_rec()` at `0x4ba6948`.
- `0x346d140`, whose diagnostic string is `void model::sequence_mode_transition::common_set_hdmi_resolution_4k_rec()` at `0x4bc4a40`.

This use during resolution changes further corroborates that the state is output definition, not physical connector state.

## Exact request, result, and wait contract

`0x35c1e68` initializes the 12-byte request as four 16-bit little-endian fields followed by four bytes cleared to zero:

| Offset | Size | Meaning / observed value |
|---:|---:|---|
| 0 | 2 | frame/category `0x2500` |
| 2 | 2 | command `0x010a` |
| 4 | 2 | total message bytes `12` |
| 6 | 2 | version/flags `1` |
| 8 | 1 | desired definition: HD helper writes `0`; QFHD helper writes `2` |
| 9 | 3 | reserved/padding, cleared to zero |

The payload is demonstrably a **one-byte definition plus three zero bytes**, even though the observer prints it as a four-byte `value`. Calling it an arbitrary 32-bit state bitmask would overstate the evidence.

Both helpers initialize a 12-byte result object with header `0x2500 / 0x810a / 12 / 1` and result at byte 8, initially `0xefffffff`. They call `0x35b8ab4` with destination `0x909a015a`, the 12-byte request, and a 12-byte response destination.

`0x35b8ab4` allocates a temporary reply queue, copies the original request, sets its actual source via `osal_set_msg_src`, and sends it. At `0x35b8b98` it calls `osal_rcv_msg_tmo` with timeout `-1`. On receipt it copies 12 bytes to the response object and frees the message/temporary queue. There is no evidence of polling or a date dependency here.

The sender does not independently validate every response-header field before copying it. The emulated receiver should therefore be strict: only answer an admitted `0x2500 / 0x010a / 12 / 1` request; reply once to that request's actual source; use `0x2500 / 0x810a / 12 / 1`; place the four-byte native result at offset 8. Do not reuse the unrelated persistent notification subscriber queue as the per-request completion destination.

`0x35b7ab8` maps both native results `0` and `1` to business result `0`, so native status `1` does not imply a failure. Native values other than these are not broadly accepted; for example the initial `0xefffffff` maps to a nonzero error.

## Stateful model boundary

AP evidence alone supports definition state values `HD=0` and `QFHD=2`, with physical connection and link activity tracked separately. The original A7M4 branch's `hdmi_set_definition_raw` wrapper calls `0x35bf7a8`, which simply writes business error `2` and returns without sending this CP request. The emulator should not extend success to raw or other unknown definitions on the basis of the adjacent names.

The parent relayed separately verified CP behavior: `0x57bd48` returns `1` for unchanged definition and `0` for a changed definition; `0x5797ae` under `RSEN_Lo` preserves the requested definition and returns `1`. That supports this minimal disconnected-state behavior:

1. Admit only the verified message form and supported definition values.
2. Save the requested definition in endpoint state.
3. Keep cable/RSEN disconnected and actual link/output inactive.
4. Return native status `1` in the exact original completion to the dynamic request source.
5. Emit no unsolicited hotplug, link-enable, rendered-display, or successful video-negotiation event.

Unknown or unsupported requests need their real error/unsupported behavior, not a generic zero completion. Bit width, output frame rate, negotiated resolution, output enable, and observer registration have separate APIs and should not be implicitly changed by `0x010a`.

## Remaining limits

This AP review identifies business purpose and response consumption. It does not independently establish the entire CP hardware state machine or prove that QFHD rendering works. The exact disconnected status behavior above comes from the parent's independent CP analysis; AP confirms it is accepted. No claim of a working physical HDMI link follows from an accepted definition completion.
