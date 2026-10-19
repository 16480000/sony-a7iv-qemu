# A7M4 native runtime investigation, 2026-10-18

Target: Sony ILCE-7M4 6.02, official BODYDATA SHA256
ad6df47a0a93a46336b9920a0d8891d0c766f8c96fa68ebda8685f6c21621188.
Reference: chocotan/a7c2-re at 25efb56d7f0c69355f9225d1da50454207532e7f.

## Observed

- Original, unmodified 6.02 kernel and original application run on our QEMU 11.1.2
  with the reference board/timer/input patch and a new SCU DFS handshake model.
- Original Backup defaults, native IPC, kernel drivers, resource archives and
  original AP widget/raster output are used. Ten IMDB component masks are filtered;
  software service/raster/OSD models replace absent hardware endpoints.
- Native menu screenshot and real navigation accepted in native-26-input:
  DOWN, UP, ENTER, MENU each traverse QMP -> Sony UI input device -> socket ->
  original OSAL input queue -> original application. All four change AP pixels;
  UP restores baseline; MENU after ENTER restores baseline. Five QEMU ramfb
  screenshots match independently decoded AP pixels byte for byte.
- Actual baseline pixel SHA256:
  c4ab293effca43eb98311b1cc393fc97dcf203524d5b5bc3feeb8144da5bffcf.
  Native 640x480 menu has 157 RGB colors and includes My Menu Setting/Add Item.
- Further root MENU exits to black. Next MENU fails to reopen in native-28-home.
  Therefore full shooting home/liveview/capture is NOT achieved.
- GTK host startup cannot open this machine's WSLg X display (XOpenDisplay fails).
  The owned browser panel displays actual QEMU ramfb screenshots instead and
  routes controls through the same tested QMP/device/socket/native-IPC path.
- Live panel native-37-panel, port 18764, URL recorded in D:/CodexWork/
  sony-a7iv-qemu/menu-a7m4/live-panel.json. Its RESTART was verified to return
  to the accepted 157-color native menu; original idle shutdown goes black.

## Important corrected inference

The first presumed M4 menu constructor 1dc27bc and mode346 were WRONG:
that constructor installs RTTI dlt24_controller (delete screen), vptr58cc7e0.
Instruction-prefix similarity and a reused numeric mode were insufficient.
Earlier native-16 through native-24 are diagnostics, not menu acceptance.

The actual M4 menu is RTTI 19rep_menu_controller:
vptr599e090, GOT5a300a0 -> vtable599e080, constructor1dc7504 stores354,
factory1dc769c at 5118520+354*96+8. Native init210a28c selects child2d4/2d5/2d6;
observed child2d6 creates44 widgets and renders the real menu.
This is now checked by prepare-display-port.py before installing hooks.

## Current next question

Without MENU_APPLY_MENU, native-30-coldboot passed clock/display initialization
and waited for CP opcode403d. Native-32 and later pass that wait but abort in
model::sequence_boot::run_i(). Preserve menu-window.cpio (accepted menu) and live
panel while experimental builds use separate native-boot*.cpio images.

Native clock initial default is 2021-01-01 plus retained offset540. Measured
BY_BOOT/op2 round trip returns initial+540 minutes, not initial-540. Prior helper
status8 was a bad expected-value check; the native setter and read returned0.
Native-30 validated DATE_CLOCK_READY and DATE_SEED_STATUS=0. Timebase is correct:
long guest/host elapsed times match. Do not change cntfrq based on idle blackness.

CP403d is Camera::ReleaseLock::RelLockS2 set/clear mask (RTTI and CP8d0506,
OR/BIC helpers8d02d2/8d02da). Idle virtual S2 can immediately ACK with the
original token and F000 (8d05d6 ->8d32b2), preserving actual mask state.
The same module query8d0e28 chooses F000 when blocked bits==0, F001 otherwise.
Only observed 0x8000/0x200000 masks and 16-byte validated requests are modeled.
This does not mean real CP, S2, or imaging hardware has been initialized.

Important second corrected inference: abort LR app+3178320 is a shared fatal
exit reached by over 40 branches, not proof of failed date arithmetic. Forwarding
GOT and direct-entry date probes do not observe the suspected 30-day operation;
removing clock seed also produces the same abort. Six native exceptions agree:
saved registers and local values point to run_i() region3179478..3179bb4.
Independent read-only review in agent-init-current.md confirms FP layout and
ELF mapping. Native-41 adds a verified 37258d4 logger-entry probe, saves all
arguments/NZCV, replays original prologue and forwards unchanged, to recover
the actual source line/error code before original fatal. No checks bypassed.

Native-41 resolves the real error: caller3179b78, source line0x520, error0x13.
3179b34 ->359e28c ->35d4d34 is infra_wrapper_bus_power::set_buspower_setting,
sending MWF6107/1000 to012282f6. libBusPower.so had been filtered from IMDB.
Native-42 re-enables original BusPower and passes this check but app exits with
undefined iCrypt_HasPublicKey. Native-43 restores original libInfraCrypt as well;
only eight services remain filtered. No abort, original SeqQueueCommon reaches
3179d1c waiting for Dataflow/CP9059000e legacy2001/0205 (set timecode).

Native-44 captures the exact52-byte Dataflow request. Header: replyid/source
81cf61c4, markerA0A0A0A0, count1, total52, first-offset24, end52, reserved0.
Inner2001/0205 size28/version1/body20. CP RTTI and code51ee1a..51eeb8 identify
VDF::VdfSrvcCmdSetTimeCode. CP checks body[0]!=0, body[1]<2, body[12]<3;
valid config is stored/published before reply2001/1205 size12/status0. Invalid
config returnsstatus1. Native-45 models this one shape with retained20-byte
state and a36-byte Dataflow reply preserving replyid/version. Native-45 proves
the original receiver accepts it and advances to3179e8c. Next wait:200d/0164,
request10 bytes/body02 00, source81cf61c4, dest92840747.

CP b4e10 names164 'display resolution_size'; forwards toVDF2001/0118.
VDF RTTI: VdfDisplayCmdSetPanelResolution, handler51bc82 requires body0 bit1,
51bcc2 checks resolution(body1)<3. CP4f27aa makes1164/12-byte statuscompletion.
Native-46 retains selector2/resolution0 and returns that exact valid-state
completion, accepted: original boot reaches317a03c. Original20b is
VdfSrvcCmdSetEvfTempInfoEvent, no synchronous120b;
its callback source is81cf6189. Temperature model not implemented yet.

Native-47: hdmi_set_definition_hd requests2500/010a/12/version1/body0.
AP trace table also identifiesQFHD as body2. OriginalCP handle_set_definition
10f798 ->57709c ->state vtable+70; RSEN_Lo handler5797ae stores desired setting
and replies810a/status1, unchanged-setting branch57bd48 likewise replies1.
AP35b7ab8 accepts0/1. Our disconnected HDMI retains onlyHD0/QFHD2 with three
remaining bytes0, preserves cable/link state, returnsoriginal810a/status1.
Original firmware accepts this and advances to317a0b4, waitingHDMI0101/16B
with bodyu32(0,6). Actual AP and independent QEMU ramfb remain identical black
(pixelSHA34c69899504b36f13e8b22120cf0fd894e61fcd6b046fb8535b79cc491fa3b3f).

Correction of wire interpretation:101 is five independent bytes
HD/SD/QFHD/UHD/RAW (CP10f4c8), not two semanticu32 fields. AP35c1614's own
factory ctor stores0/0/0/0/6, padding0. RSEN_Lo CP579314 retains them and
replies8101/status0 without link activation. Native-49 accepts this completion
and advances beyond the preceding checks; a concurrent query waits in app317563c ->359a588
->35bb4bc ->35b8b9c for BB0325/8B ->expected1325/28B. No main UI yet.

User observed the idle black panel. Replaced native37 panel with native48 and
the same accepted menu-window.cpio; current URL in live-panel.json. Improved
responsive layout and explicit black/partial status. RESTART now terminates
only its owned VM and recreates it with fresh memory, retaining the webserver;
actual cold restart accepted baselineSHA c4ab... and157colors again. Do not
use QMPsystem_reset as a substitute for a fresh raw-kernel memory image.

Native-50: audio capability325 was a concurrent operation, not proof that
run_i() had returned. It now receives an explicit virtual no-audio profile:
1325/28B/status0 and16 bytes80(unavailable), as original BB/ADF conversion
and AP consumers specify. No microphone/processing capabilities are claimed.
Native-51: five HDMI0117 settings are saved by definition0..4, as the CP
RSEN_Lo1113bc path does;8117/status0. Actual rates0,0,17,17,0, DP bytes ignored
by originalM4 handler. Boot now waits317a3d8 on a Dataflow topology query.

Native-53 captures9284074a/48B: Dataflow header24/count1/offset24/end48;
header word+20 is0x7f (uninitialized/padding, do not assign semantics).
Inner1000/0000/24/flags2, bodyu32(0,2,1,0), reply queue81cf61c4.
AP35d8b74 expects1000/8000/32/flags2: status@28 and multiple identity fields
then35d86ec validates the returned16-byte identity. This is under review;
do not fake a generic register-success response.

Menu power issue: original UI proves Power Save Start Time default1 Min.
Changed through original menus toOff and accepted original confirmation.
Native-52 tests automatic native key navigation toOff, exact settings PNG
SHA b247af07d2a9cf43798b1118b5bec182e407a7d38a807d8529335371b343d4b3,
AP/QEMU pixel match, then restores original menu baselinec4ab...;100s run.
Host --keep-menu-awake repeats this original configuration on fresh restart,
requires the verified baseline and final settings image (no direct AP/global
or Backup writes). Start-Menu.cmd now selects this option. Original image
menu-window.cpio remains unchanged. Live native54 panel replaces48 using the
same URL token; status now explicitly indicates disabled auto power save.

Probe script exception detection corrected after native-41: Sony's actual marker
is 'Entering exception monitor.', not only 'Exception monitor:'. Historical
native-41 result.json incorrectly says exception=false; console proves abort.
Native-42's bootstrap_complete=true likewise only means shell, not living app.

## Evidence roots

Native68 accepts digital-level command3 under an explicitly disabled inertial
feature profile. OriginalCP3ee620->3ee67c returns0 without a sensor request
for ready2/feature0; no orientation samples are supplied. Main passes317a5d4
and reaches317a7f0, waiting for CP DMMunit-size query18/resource50b58.

Native69 accepts original CP DmmCfg.bin query value0x09600000(150MiB).
Config SHA7e7c09a3bb6922d5a1e5cfbddd29600b2fbc709264ac40bbde35b3f5ea2c54fd:
unit map94fc key50b58 ->firstextentf0; extent5730 size+12=9600000.
Parser follows original dmm.ko ext_tbl_Init80Bheaders/20Brecords then
unit_tbl_Init8Bheaders/4BterminatedIDlists. Kernel GetUnitSize9e90 and
GetExtentSizeb858 show the lookup; builder5b60 uses8018/status+2/size+16.
This is a metadata query, not a150MiB allocation. Main now waits317a95c on
the remaining worker305's BB0119 image-orientation configuration.

IMPORTANT correction from direct original disassembly: app3178320 is the
shared function epilogue (restore registers/return), NOT a fatal tail by
itself. Historical aborts were proved by actual exception logs and their
earlier checks; a future transition through3178320 may be a normal return.
BB119CPb3130 maps hrev/vrev/osdRev/rotation toVDF2001/0101; ae01c creates
1119/12B and maps special590000 to0. Current request hrev1/vrev1/osdRev0,
rotation0. Native70 pending strict configuration-retention model.

Native57..63: finite local virtual Dataflow pin model now completes11 fresh
logical bindings across hash-verified CP-declared endpoints, including GRM
OSD and HDMI video/audio. It maintains identity/state/peer/pending operation,
locally models0100/8100 before8001, and does not produce image/audio streams.
Original AP progresses beyond317a3d8 topology setup to317a49c's async task
wait. It remains in sequence_boot::run_i, not the main camera UI. Profile
export and all record-format conversions in topology-model-notes.md.

Native63 async tasks305/306 were independently waiting for BB032e(system
volume) and033d(system-sound resource address), requests issued concurrently
with earlier boot setup. Native64 accepts both new finite models.032e
retains native1..16 volume and normalized0..15; no playback.033d publishes a
new reservedPA41ea00000/0x20000 bank only after loading original77504-byte
SysSound.bin(SHA dae3d18d37b85a22398573f04090a4a95a97052380f4b2b4402a374516399dfb).
Stage --system-sound enables the guest and verifies exactly one nonoverlapping
memrsv entry. Original AP now requests0327/40B registration of beep1 at that
bank, length256; thread306 reaches35bc780,317b958,317c9b0. See
system-sound-model-notes.md for original CP field/response evidence.

Native65 accepts finite backed beep descriptors, constrained to
21 AP entries and the actual original bank range. New --verify-system-sound
uses QMP pmemsave to independently compare guest physical data to the original
firmware and check zero tail: exact77504-byte match and all-zero tail passed.
Next request032a/10B body04,01 is per-sound volume4 for beep1, not playback.
Native66 is testing that retained configuration (CPb0fc4->2004/0204,
4f2be4->132a/12B/status). Do not call this audio playback or UI success.

Native-55: strict original imaging GET_PIN query succeeds, state1(disconnected)
and raw owner9284074a. Original AP accepts identity and proceeds to peer GET
owner905a0048/type0/dir1/no1. Still black, AP/QMP agree on1color. No connect
completion has been fabricated. CP peer definitions at fileadf43c..adf533
have layout{number,type,direction,owner}; initializer54e10a..54e12a explicitly
reorders them into constructor{type,direction,number,owner}, unlike the imaging
table's already-native layout.16 peers: YC dir1/2 numbers0..6; RAW dir1/2 no0.
Constructor4e2006 establishes state1 for these as well. Do not copy raw VEF
table words as an unconverted protocol identity.

- D:/CodexWork/sony-a7iv-qemu/menu-a7m4/native-26-input (accepted menu/key/ramfb)
- D:/CodexWork/sony-a7iv-qemu/menu-a7m4/native-28-home (exit/reopen limitation)
- D:/CodexWork/sony-a7iv-qemu/menu-a7m4/native-25-rep-menu (first menu capture)
- /opt/sony-a7iv/menu-a7m4/runtime/analysis (generated original-ABI helpers)
- work/sony-a7iv/*.py, sony_scu_dfs.c (port/build/analysis sources)

Native70: BB0119 reverse config accepted; first unforced coldboot frame is
original Japanese slot1 unreadable-card warning,14colors, pixelSHA
0aead4673f7e7dcbab95196a921b88ef8ee77a79639dd32e9eb42da8b2d38e33.
Independent QMP image equals decoded AP pixels. No menu injection. Native71
DOWN/UP/ENTER/MENU did not dismiss this warning. Not a camera main UI.
Native72: main waits on CameraBackground20B request10/20. Thread268 waits
for original CP3007 reply; source8102 dynamic queue. CP31e67e checks state3007
via90e0ca and already-idle path90f0ae->320bb4 builds12B reply1/3007/token/f000.
Native73 strict virtual-idle completion is accepted. Threads305..308 all return
to idle358d5a4. Original UI creates315,12e,330; actual frame remains card error.
No imaging stream or original CP execution. Investigating original removable
media status next; diagnostic wrapper must preserve original result/bytes.

Native80 original mcmn_drv.ko loads successfully (no patch). This replaces the
unreadable-card warning with original firstboot language page; actual no-card
state is now available. Native81 initially freezes after~459 frames because AP
snapshot messages to unregisteredCP9088076b leak the shared OSAL message pool.
AppFw blocks allocating748B snapshots; InputMain blocks in logging timestamp
allocation/sync910042. Native82 consumes validated AP model snapshots, retains
exact bytes and real_free_msg: input resumes, DOWN/UP/ENTER/MENU pixel tests pass.

Native83: ORIGINAL MAIN UI OBSERVED after real firstboot wizard, NO injected
menu entry. Selected English, acknowledged nonbinding privacy notice, used
native DELETE shortcut for Set on the camera, set Beijing +8 and2026-10-18,
chose Set Later for temperature, closed smartphone/touch tutorials. Original
main view0/count585, visibleJ.FINE14M/AF-S/MECH/AF ON/NO CARD. A cold restart and
same wizard route reproduced main UI. MENU enters original Main settings, MENU
returns to main. Power Save Start Time Off set through native settings +confirmation.
QMP RGB equals full checked AP snapshot exactly; RGB SHA
9a8fcc29922344d82a9907834452d51e2295af92ca76fa6e44e3ca47947d553d.
Native NO CARD blinks and some other indicators auto-hide during idle, so
stability should check persistent camera/touch markers, not whole-frame equality.
Still NO sensor/liveview/ISP/AF/photo implementation. UI overlay only.

Never describe bootstrapped shell, black frame, mode346 delete view, or injected
menu entry as full camera cold boot. No actual CP execution, sensor/ISP/AF,
physical storage, camera USB, or physical camera has been used.
