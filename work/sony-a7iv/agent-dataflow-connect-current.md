# A7M4 6.02 Dataflow PIN_GET and connection protocol

**1000/0000 is PIN_GET. It queries a declared pin and its current connection state.** The current `(type0, direction2, number1)` pin exists in the original CP definition table for owner **0x9284074a**. Its constructor initializes state **1 = disconnected**. A successful query must preserve that state; it does not establish a connection or produce an imaging stream.

Original-compatible initial-state inner response for the captured current request:

`0010008020000200000000000200000001000000010000004a07849200000000`

This is32 bytes: type1000/cmd8000/length32/flags2, pin type0/direction2/number1, state1, raw owner9284074a, query result0.

Read-only original CP `/opt/sony-a7iv/menu-a7m4/runtime/analysis/menu-root/cp/cpapp-b.bin`, SHA-256 `7b9b137d696e5972d20db7f9119076172ed8e0730805d7f0b4c31b87689e2c2b`, and original AP `usr/lib/appFw.so`. CP addresses below are file offsets; runtime VA=file offset+0x108000; Thumb pointers set bit0. AP addresses are ELF VAs. No shared scripts, firmware, or VM modifications.

## PIN_GET request and reply fields

Parent captured native-53 complete48-byte Dataflow payload:

`c461cf81a0a0a0a00100300018000000300000007f000000001000001800020000000000020000000100000000000000`

The24-byte outer envelope carries source0x81cf61c4, then the24-byte inner request:

| Inner offset | Type | Field / current value |
|---|---|---|
| +0 | u16 | type0x1000 |
| +2 | u16 | cmd0x0000 / PIN_GET |
| +4 | u16 | length24 |
| +6 | u16 | flags2 |
| +8 | u32 | pin type0 |
| +12 | u32 | direction2 |
| +16 | u32 | pin number1 |
| +20 | u32 | reserved0 |

Destination owner0x9284074a comes from routing; it is not a fourth business argument in the request body.

| Reply offset | Type | Field / initial answer |
|---|---|---|
| +0 | u16 | type0x1000 |
| +2 | u16 | cmd0x8000 / PIN_GET_COMP |
| +4 | u16 | length32 |
| +6 | u16 | flags2 |
| +8 | u32 | pin type0 |
| +12 | u32 | direction2 |
| +16 | u32 | pin number1 |
| +20 | u32 | current connection state1 |
| +24 | u32 | **raw owner0x9284074a** |
| +28 | s32 | query result0 |

CP destination loop starts at file `0xba760`. The type1000/cmd0 dispatch is `0xba802..0xba8da`, branching to `0xbaae6`. It initializes the8000 reply header there, iterates the19 defined pin objects at runtime table0x00f5801c (`0xbab1e..0xbab4c`), reads each identity through `0x4e2e2e`, and compares the first three words against request+8/+12/+16. On match it takes `0xbaea4..0xbaeda`:

- `0x4e2e2e` copies object+0x18..0x27, the four words `{type,dir,no,owner}`.
- `0x4e2e28` reads object+0x28, the connection state.
- `0xbaeb0..0xbaec4` writes the first three identity words to reply+8/+12/+16.
- `0xbaec8..0xbaecc` writes state to reply+20.
- `0xbaed0..0xbaed4` writes the original owner word to reply+24.
- `0xbaed8..0xbaeda` writes result0 to reply+28.
- `0xbaeee..0xbaf20` wraps/sends32 bytes, assigning source/reply identity0x9284074a.

No match sets result **-32** (`mvn r0,#0x1f` at `0xbab56`), not a fabricated successful pin. Existing connected/disconnected states are returned by GET; they do not make the query itself fail.

## Original pin definitions and constructor state

Exported machine-readable records: `agent-dataflow-original-pins.json` in this same work directory. It contains all19 records with each definition file offset, runtime VA, object pointer's file offset, object runtime VA, owner, and constructor-state evidence.

Static definition table: file **0xe4feec..0xe5001b** (19 records,16 bytes each); runtime **0x00f57eec**. Each record is `{type,dir,no,owner}`. Every owner in this table is raw0x9284074a. Object-pointer table: file **0xe5001c..0xe50067**, runtime0x00f5801c.

| Index range | Type | Direction | Numbers |
|---|---:|---:|---|
| 0..3 | 0 | 1 | 0,1,2,3 |
| 4..7 | 0 | 2 | 0,1,2,3 |
| 8 | 8 | 1 | 0 |
| 9 | 8 | 2 | 0 |
| 10 | 6 | 2 | 0 |
| 11..14 | 0 | 1 | 10,11,12,13 |
| 15..18 | 0 | 2 | 10,11,12,13 |

Current pin is index5, definition file **0xe4ff3c** / VA0x00f57f3c, object pointer file **0xe50030**, object **VA0x0121fe68**. Initializer `0x4f80ae..0x4f80c2` passes that exact definition and object to constructor `0x4e2006`.

Constructor `0x4e2012..0x4e2020` copies all four identity words into object+0x18..0x24, and `0x4e2022..0x4e2028` sets state1 at object+0x28. It also initializes the cached peer identity to `{0xff,0xff,0,0}` at object+8..0x17 and pending-transaction fields to0 (`0x4e202a..0x4e2036`). This is constructor state before later runtime graph changes. It is not a claim that all19 pins remain disconnected forever; internal setup can connect some later.

The parent's AP name-table extraction identifies `_INFRA_PIN_ATOM(IMAGING, YC, OUT, 1)` for the current logical pin. That naming table is useful for symbolic names, while the CP definitions/constructor above provide existence, raw routing owner and initial state. The obsolete extraction grouped24 bytes incorrectly and was not used here.

## AP identity comparison and owner format

AP `0x35d8b74` is `get_infra_pin` (string0x4c09628). It routes using input identity's first word, and builds the inner request from the other three words (`0x35d8ba0..0x35d8bcc`). After reading8000 it returns an output identity in AP's order:

`{reply+24 owner, reply+8 type, reply+12 dir, reply+16 number}`

Proof: stores `0x35d8cec..0x35d8d08`. There is **no owner-enum conversion** in this path. Therefore out[0] must be raw0x9284074a for this CP-defined pin, not module-enum0. State+20 is separately returned through an optional pointer (`0x35d8ce0..0x35d8ce8`).

The caller compares all four returned identity words against its input using `0x35d86ec..0x35d873c`; mismatch asserts in `check_and_connect_infra_pin` (`0x35d9050..0x35d9078`). The logical names IMAGING/YC/OUT do not replace raw routing IDs in these identity words.

## Subsequent connect/disconnect framing and state machine

The generic `DataflowInfraPin` object state is **0 connected, 1 disconnected, 2 transition**. The source-verified initial state is1. Successful peer connection handling sets0 (`0x4e23ea..0x4e23ec`), successful disconnect handling sets1 and clears peer fields (`0x4e2728..0x4e273a`, `0x4e284c..0x4e285e`). Transaction initiation sets2 and records pending reply routing.

All pin identities **inside protocol frames** are ordered `{type,dir,no,owner}` (four u32 words). AP's `ds_infra_pin` uses `{owner,type,dir,no}`, so AP wrappers reorder them at frame construction/consumption.

| Command | Length | Flags | Body / role |
|---|---:|---:|---|
| 0000 | 24 | 2 | GET: type,dir,no,reserved |
| 8000 | 32 | 2 | GET_COMP: type,dir,no,state,owner,result |
| 0001 | 40 | 2 | caller requests connect; two pin identities |
| 0100 | 40 | 1 | initiator sends peer connection request; two identities |
| 8100 | 48 | 1 | peer completes request; two identities, result+40, reserved+44 |
| 8001 | 32 | 2 | caller connect completion; own identity+8..23, **result+24**, reserved+28 |
| 0002 | 24 | 2 | caller requests disconnect: type,dir,no,reserved0; owner from routing |
| 0101 | 40 | 1 | initiator sends peer disconnect request; two identities |
| 8101 | 48 | 1 | peer completion; two identities, result+40, reserved+44 |
| 8002 | 32 | 2 | caller disconnect completion; own identity+8..23, **result+24**, reserved+28 |

Important: GET's result is at+28; connect/disconnect completion results are at+24. A generic32-byte ACK parser would conflate different fields.

### Connect evidence

AP `0x35d8d10..0x35d8e58` builds0001/40/flags2 from two AP identities and expects8001/32/flags2. It checks result at reply+24 (`0x35d8e2c`).

CP loop dispatches0001 to `0xbab5c`, locates the first identity and invokes `0x4e204e` at `0xbaf7e`. That method checks current state and peer compatibility. Validator `0x902cc..0x90316` requires matching pin type and compatible directions (table at0x90318 maps1<->2 and3<->3). Type mismatch yields-23 and direction mismatch-22. Existing other-peer connection and transition states have distinct errors; the code does not blindly accept every request.

For a fresh valid connection, `0x4e217e..0x4e21ba` constructs0100/40/flags1 with own identity first and peer identity second. At `0x4e21ca..0x4e21e2` it records state2, operation1, peer identity, and pending caller routing. It sends to peer owner via `0x4e32e0` at `0x4e21f0`.

The receiving peer's0100 dispatch looks up the second identity and calls `0x4e229c` at `0xbac08`. That handler validates type/direction and state; its successful branch `0x4e237c..0x4e2408` constructs8100/48/flags1/result0, saves the peer, sets state0, and sends the peer completion. The initiator receives8100, calls `0x4e242a` at `0xbae0c`, and constructs the final8001/32/flags2 with result copied from incoming+40 (`0x4e246a..0x4e249c`). Pending caller routing at object+0x2c determines the recipient. GET after a completed successful exchange must reportstate0.

The already-connected/same-peer path has special handling (`0x4e2070..0x4e214a`); do not reduce it to unconditional success for an arbitrary different peer. Some error-completion cleanup details merit exact per-branch follow-up when encountered; this report asserts the demonstrated success path, rather than inventing a full error recovery policy.

### Disconnect evidence

CP0002 looks up the first identity at `0xba8ea..0xba91c`, then calls `0x4e250a` at `0xbadc0`. That method rejects transition with-24 and disconnected with-26, otherwise constructs0101/40/flags1 (`0x4e25c8..0x4e2620`), sets state2, records disconnect operation2/pending reply routing at `0x4e262e..0x4e2634`, and sends to the cached peer owner.

Peer0101 invokes `0x4e267a` at `0xbac7c`. Successful branch sends8101/48/flags1/result0 and, when connected, sets state1 and clears cached peer (`0x4e26a6..0x4e2744`). The initiator's8101 handler `0x4e27fc` is called at `0xbae5c`; incoming result0 at+40 causes it to setstate1 and clear peer (`0x4e284c..0x4e285e`), then send8002/32/flags2 with the result at+24.

## Model implications

1. Implement GET against declared pin records and each record's persistent connection state. Current record exists and starts disconnected; unknown pins must not receive a successful fabricated identity.
2. Keep peer identity, state and pending connect/disconnect routing per pin. A connection request is a stateful two-endpoint transaction, not a register acknowledgment. Register and bind supported peer endpoints before emitting its success completion.
3. A completed logical pin binding establishes graph transport only. It does not certify sensor data, a decoded frame, audio capture, or a visible camera UI. Unsupported data-plane services must remain explicit.
4. Preserve routing owner values verbatim. Match incoming requests to the declared owner/type/direction/number; do not infer existence solely from an AP display-name string.

Parent is running the strict GET implementation and will capture the next actual transaction. No current success of a future connection or completed UI boot is claimed here.
