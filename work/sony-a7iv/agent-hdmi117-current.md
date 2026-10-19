# A7M4 6.02 HDMI 0x0117: output frame-rate settings

Read-only original CP and AP verification. CP file offsets below map to runtime VA by adding0x108000; Thumb pointers also set bit0. AP addresses are ELF VAs. No shared scripts, firmware, or VM modifications.

**0x0117 is `HDMI::ApiHandler::handle_set_output_frame_rate`.** The request body is four separate u8 fields: HDMI definition selector, HDMI output-frame-rate value, DP definition selector, DP output-frame-rate value. It is not two halfword business parameters. The original RSEN-low state stores the HDMI rate for the selected definition and replies **0x8117, 12 bytes, version1, status0** without activating HDMI output.

Current complete request from parent/native-50:

`002517010c00010000000000`

Current matching response:

`002517810c00010000000000`

## CP evidence

- Parser at file `0x10fb34..0x10fbbe` checks request length>=12 (`cmp size,#0xb`, branch <= at `0x10fb44`), reads four bytes at request+8..11, and reconstructs them into one transport word.
- Its diagnostic string at file `0xce25d3` explicitly names fields in order: `ApiHandler::handle_set_output_frame_rate : hdmi_definition:0x%x hdmi_output_frame_rate:0x%x dp_definition:0x%x dp_output_frame_rate:0x%x`. Assertion-name string at `0xce2553` spells the full handler name.
- Parser calls `0x577210` at `0x10fb96`. That dispatcher passes a pointer to the reconstructed four bytes to state vtable+0x80 (`0x577222..0x577228`).
- RSEN-low vtable begins at file `0xae221c`; its +0x80 entry at file `0xae229c` contains Thumb pointer0x2193bd, resolving to file **0x1113bc**. The table's RTTI at file `0xae22cc` names `HDMI::RSEN_Lo` through name pointer0xdedcfe.
- Handler `0x1113bc..0x111490` loads current per-definition rate bytes at SharedData+0x9e,0x9f,0xa0,0xa1,0xa2. Global SharedData pointer is at runtime0x01228710.
- It reads body[0] at `0x111408`; for selector0..4, its jump table selects which of those five cached bytes to replace with body[1] (`0x111418..0x111430`). Selectors>=5 leave them unchanged; the function still follows the same normal ACK path. There is no rate-value range check in this state.
- It stores all five rate bytes back at `0x111434..0x111444`. Bytes at SharedData+0xa3..0xa7 are preserved. The DP pair at body[2:4] is parsed/logged by the API but not used by this original M4 RSEN-low handler.
- Reply construction `0x11145e..0x111480`: type0x2500, command0x8117, total length12, version1, 32-bit status0 at+8. Sends via `0x110a14` at `0x111484`; returns0 at `0x111488`, selecting no next HDMI state and making no HDMI hardware call.

## AP evidence and repeated boot calls

AP `0x35c1928..0x35c195c` is the 117 request constructor; `0x35c1960..0x35c1988` constructs the expected 8117 reply. Current wrapper `0x35c198c..0x35c1a18` reads the input selector byte, duplicates it into request+8 and+10 (`0x35c19b4..0x35c19cc`), reads the rate from input+4, and duplicates it into request+9 and+11 (`0x35c19dc..0x35c19e8`). Thus AP uses the same definition/rate pair for HDMI and DP fields.

It calls `0x35b8bdc` at `0x35c19fc`, then reads result+8 at `0x35c1a00` and maps through `0x35b7ab8`. That mapper accepts status0 and1 as normal, but the verified RSEN-low CP 117 implementation specifically emits **0**.

Boot code `0x317a15c` puts the loop index into the selector input, calls the wrapper through `0x359ae9c` at `0x317a174`, increments the index at `0x317a1e8`, and loops until5 at `0x317a1ec..0x317a1f0`. These are updates of five definition-specific settings, not five retries of a failed single request. A literal table at AP0x4ba5020 contains five words0,0,0x11,0x11,0; the exact branch used to choose each rate also depends on surrounding AP state and should be checked against the live request stream.

## Minimum faithful no-cable model

Keep an array of five u8 HDMI output-frame-rate choices. For this request class, when body[0]<5 set rate[body[0]]=body[1]; otherwise retain the array. Reply 2500/8117/12/version1/status0 for each call. Do not turn on HPD/RSEN or start output as a consequence of these setters. The source-verified path only persists settings while disconnected.

Unknowns: complete symbolic definition/rate enums and active-output reconfiguration details. This report does not infer visible UI startup or completion of `sequence_boot::run_i()` from other threads' audio requests.
