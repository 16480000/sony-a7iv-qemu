# A7M4 6.02 virtual topology model

Original CP SHA256: `7b9b137d696e5972d20db7f9119076172ed8e0730805d7f0b4c31b87689e2c2b`.
CP addresses are file offsets. This is an in-process software control-plane
model in an AP observer, not execution of the original CP processor or ISP.

`dataflow-pin-model.c` supports GET against declared pins and fresh compatible
two-endpoint bindings. It keeps each endpoint's identity, connection state,
peer and pending caller/operation. It locally delivers typed0100/8100 frames
before committing both endpoints and returning8001. No physical data stream
is produced. Other states, unsupported commands and unknown pins are forwarded
unchanged; they do not receive generic success replies.

The initializer in `prepare-display-port.py` reads definitions from the
hash-verified original CP and emits a machine-readable profile. Static record
formats differ; these mappings were checked against their initializer code:

| Owner | Definition file offset | Count/stride | Initializer | Source layout |
|---|---|---|---|---|
| 9284074a | e4feec | 19/16 | 4f8010 onwards | type,dir,no,owner |
| 905a0048 | adf43c | 16/16 | 54e10a | no,type,dir,owner |
| 90590818 | abd698 | 13/16 | 52d85a | no,type,dir,owner |
| 91670464 | c589ac | 10/16 | a06834 | no,type,dir,owner |
| 9058003f | aabeb0 | 10/12 | 4d25ee | type,dir,u8 no; literal owner |
| 928d0783 | aa1040 | 2/12 | 4950f4 | type,dir,u8 no; literal owner |
| 909a015a | literal | 2 | 5774f4,57752e | type4/5,dir1,no0 |
| 9080003b | literal | 1 | 3d1116 | type1,dir3,no0 |

Each calls constructor4e2006, whose4e2022..4e2028 sets state1(disconnected).
The fresh-connect contract and direction/type check come from4e204e,
4e229c,4e242a and902cc; see agent-dataflow-connect-current.md.

Runtime progression, all without injected menu entry:

- native55 accepts imaging GET and proceeds to peer GET.
- native56 accepts both GETs and issues actual0001/40/flags2 connection.
- native57 completes YC and RAW imaging-to-VEF bindings; asks VDF peer.
- native58 completes five virtual bindings; requests91670464 peer.
- native59 passes that binding and requests9058003f YC input.
- native60 passes that binding and requests928d0783 SYSND input.
- native61 completes eight virtual bindings and requests HDMI video input.
- native62 passes HDMI video binding and requests GRM OSD INOUT.
- native63 completes eleven bindings, including GRM OSD and HDMI audio.
  SeqQueueCommon advances to317a49c waiting on queued asynchronous startup
  tasks. SeqThreadPool1 waits on BB032e/adf_set_volume, while pool2 waits on
  BB033d/adf_sys_get_system_sound_address. These requests were concurrent with
  earlier topology work; completing the graph alone does not finish boot.

Every measured AP frame remains all black, independently equal to QEMU ramfb.
No main camera UI or finished `sequence_boot::run_i()` is established.
