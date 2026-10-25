# REPOSITORY PACKAGING 2026-10-25 — V0.1; PRIVATE GITHUB REQUEST

User requested organization and GitHub publication, explicitly choosing PRIVATE.
Root README, CHANGELOG, NOTICE and docs/STRUCTURE + docs/REPRODUCING now index
the existing scripts and archived 2026-10-20/21 experiments without moving paths.
Ignore generated personal video/JPEG/RGBA assets, module build products and publishing tools.
Keep VERSION=0.1 and original v0.1 tag at3fcc1c3; archive new code/evidence on main.
Packaging checks: Python syntax, Node/PowerShell syntax, local documentation links,
credential-pattern scan, generated-artifact exclusion. No camera runtime rerun.
GitHub CLI is installed only under ignored work/publish-tools/gh/bin/gh.exe.
Publication depends on GitHub account authorization; inspect gh auth status and
git remote -v for actual completion. Do not claim upload before push/read-back.
Previous runtime findings below are preserved as historical evidence.

# CURRENT 2026-10-21 — FIRMWARE-REGISTERED SOUND → VIRTUAL CP → BROWSER

User rejected extracted/web-only shutter sounds and asked to connect real firmware feedback
(focus prompt etc.) so firmware sound edits can be heard. Passive GDB tracing of
`osal_snd_msg` and the AP `adf_sys_request` wrapper (`appFw+0x359b41c` →
`+0x35c10c0`, BB `200d/0329/16/8001`) showed no AP sound request on MENU/HALF/SHUTTER:
the original CP/AIP (not executed here) owns the UI/focus/shutter beep trigger.

Implemented a host-side virtual CP: parse the original AP's boot-registered beep table
(`BOOT_LOG_SOUND_DESCRIPTOR/VOLUME`, 16 IDs) and, on the real native HALF/SHUTTER key
actions, QMP-pmemsave the descriptor's guest SysSound.bin bytes and play them in the
browser. HALF uses registered FocusLock (ID4); SHUTTER uses the page-selected electronic
Kasha (ID3), mechanical Ka+Sha (ID1/2), Kasha-continuous (ID7), or off. The original AP
`adf_sys_request` handler is also installed and would surface as `来源=AP` if it fires.
The page shows source (AP vs virtual CP). User calibration on 2026-10-21 confirmed
FocusLock at 48 kHz; the live path now derives the rate from the bank entry header
(0x17 -> 48 kHz, 0x07 -> 16 kHz). Browser test after the change: AudioContext running,
FocusLock and Kasha at 48000 Hz, no errors. Kasha/electronic-shutter ID and the 0x07
group still need listening verification. User then requested a Chinese UI and stated the
A7 IV electronic shutter has no stock prompt sound. The panel/calibration pages are now
Chinese; electronic shutter defaults to silent (no Kasha); mechanical Ka+Sha and a
virtual-CP Kasha audition remain explicit options. Browser test: HALF -> FocusLock
48 kHz; SHUTTER -> no host sound; AudioContext running, plays=1. Mechanical test then
produced Ka+Sha at 48 kHz. The camera OSD/menu language is still English and was not
changed.

Boundary: CP/AIP decode and trigger logic are still not executed. Audio is 1-byte-entry
header + signed 8-bit PCM, not verified AA_RT; focus is a virtual lock; shutter mode is a
page choice; CP-native menu beeps are not triggered. Old web candidates remain only as a
clearly labeled old experiment. Evidence: `native/evidence/firmware-sound-virtual-cp-20261021/`
(browser AudioContext running, plays=2, Focus Lock → Kasha; WAVs and guest bytes).
Final instance `sound-cp-zh-20261021` at the existing S5 URL.

# CURRENT 2026-10-20 — IMAGER-CONTROL SINK EXPERIMENT; NO LIVEVIEW

User asked to continue unimplemented content and verify in a browser. No browser MCP is
configured in this Claude Code session; local Chrome over CDP was used instead
(outputs/native/runtime/browser-verify.mjs).

Audit result: the 0x40xx/0x41xx records to 0x90030001 are one-way imager-control sends
from AP source 0x80020002 via osal_snd_msg, not synchronous requests awaiting fabricated
replies. IWrapperImaging (tid286) waits on queue 0x80020002. /dev/stream2 maps reserved
guest physical memory (64MiB at 0x416000000 is the leading liveview candidate), but no
producer fills it. Do not ACK these messages or inject a test pattern as liveview.

Implemented an env-gated silent sink (QEMU_A7M4_IMAGER_CONTROL) in prepare-display-port.py:
it consumes only the observed wire shape/commands from source0x80020002 to endpoint
0x90030001, appends exact records to /tmp/a7m4-imager-control.bin (4B length + bytes,
256KiB cap), logs BOOT_LOG_IMAGER_CONTROL, and sends no completion. stage-runtime-a7m4.py
gained --imager-control; native-session.py allows imager-control-test.cpio for --auto-main.

Test image imager-control-test.cpio SHA256
677e08219e500d7226b30d76583e379b42142f0896b5e0ee6d7fccd5cbe3fab7, 471859200B,
kernel3f301473..., DTB078d664e.... Run verify-20261020-imager-control reached original
main UI. 69/69 imager requests from source0x80020002 produced 69 sink records; no unmatched
0x90030001 sends. Residual UIPC: one 0x1 (unrelated) and three 0x193 from the unmodeled
ReleaseLock 0x4037 path. No exception/fatal. OSD persisted through seq4096.

Chrome verified FN, MENU, PLAY, PLAY over CDP; final original main frame SHA256
707f200eae994e689996c20cc806ba114930820a2f2caa16c6f1b6ab4eecbe64. Two unique watch
hashes are the card-indicator blink, NOT liveview. No sensor/ISP/AF/JPEG/frame produced.
Evidence outputs/native/evidence/imager-control-sink.json plus browser-report.json and
screenshots. Test VM was stopped after verification; main-virtual-card-stable.cpio was
not promoted or overwritten. This is not a liveview or camera-imaging success.

# CURRENT 2026-10-19 — V0.1 GIT BASELINE; NATIVE117 ACTIVE

User requested Git version control, keeping v0.1. Workspace root is now local Git
main branch, VERSION=0.1, annotated tag v0.1 marks this baseline. Keep version0.1
unless explicitly requested otherwise; future work uses new commits without moving tag.
Track source/scripts/docs/frozen evidence; exclude firmware/images/generated artifacts
and runtime logs. No remote configured. Local identity Codex <codex@localhost>.
See outputs/sony-a7iv-qemu/native/版本管理.zh-CN.md. Upstream QEMU reference patch
and manifest also snapshotted under outputs/sony-a7iv-qemu/source/qemu-reference/.

Latest user request: 把当前进展整理到文档. Completed consolidated output
outputs/sony-a7iv-qemu/native/项目进展报告.zh-CN.md with current capabilities,
actual storage/playback/restart evidence, limitations, reproducibility, next acceptance criteria.
README/BASIC/MAIN/STATUS synchronized. Local document links validated.

PRIMARY native-117-card-main ACTIVE at SAME S5 URL port18764; final web frame is main.
Cold start and actual RESTART passed (~103.97s); QEMU269067 ->270922.
Before and after restart AP/HTTP entire RGB equality true, all6 afterrestart
action screenshots match native116 refs. Card metadata files present; logrotation bounded.
card-profile-promotion.json primary_activated:true. Only117 VM, no secondary.
Stable image ef7ed4046bcd3ccc0ea42f03550a958459272fb134ac61fac6f7a734f2a304d4.
Start-Camera sameargs coldstart+restart verified; launcherfile not independently coldinvoked.

NO SENSOR/LIVEVIEW/ISP/AF/JPEG/CAPTURE. Shutter audits cardSHA unchanged.
Original AP menus/Fn/Slot2 FAT32 metadata writes/empty playback work. FullCP not executed.
Virtual card and settings reset on restart. Do not claim full camera functionality.

Historical checkpoints below are superseded by current state above.

# ACTIVE117 2026-10-19 — PRIMARY SWITCH IN PROGRESS
116ENDED successfully: noerror,ALL6controlschecks true, nooriginalassertion, cardSHAunchanged.
8controlframesAP/QMPexacttrue. NewdiagnostictailSHAfromoriginalguest MATCHEShostsample.
116 audit fullsource8141934B/68951records SHA3391b35b4c9ae57d0fd1d1ce1764c43aae5a5f516b2c182ed2e5172c378c5e10;
tail523611B/3784records SHAe7c378ae6cc39ebec291e8afd72aedb86974f7e0c70b38154394841c80b62f05.
ActualROTATED generation1 observed afterexport at8MiB, twofullrecordsegments only.
record-capture-audits now12runs105..116, proofincludesrawtails, kernel,stderr,recoveryJSON.

PRIMARY87 STOPped CLEANLY viaownedS5 API. ConfirmedZEROqemu afterward.
Copied116testedmain-virtual-card-info.cpio toNEW main-virtual-card-stable.cpio.
Verifiedwholeimage SHA ef7ed4046bcd3ccc0ea42f03550a958459272fb134ac61fac6f7a734f2a304d4
matches116preboot runtime-artifacts SHA. Oldmain-ap-state-consumer.cpio HASH7a39...unchanged.
Currenthiddenlaunch native-117-card-main WindowsPID33600, logsD/menu-a7m4/native117-host.log/.err.
Usingoutputs/native/runtime/native-session.py --displaynone --web --auto-main --card-main
--initramfs main-virtual-card-stable.cpio --panel-token SAME S5. Port18764 default.
WaitforA7M4_PANEL_URL andmanifest run117; don'tuseoldmanifest87asreadiness.
ONLY117launchingnow; nosecondary/oldprimary. Usertoldtemporaryconnectioninterruption.

ALL4currentruntimescripts copiedoutputs/runtimebefore117launch. Startuprequiresconfigure
originalSlot2menuandexactreferenceRGB; --card-main isNEWliveflow, NEEDACTUALtest.
Start-Camera.ps1 UPDATEDnewstableimageHASHabove,--card-main and240sreadinessdeadline.
PSSYNTAXPASS. Reusesexistingpanel; coldlauncheritselfnotyetinvoked (manual117sameargs).
PanelRESTARTwait160s. Newfooterreflectsslot2virtual64MiB/noJPEG/resetclearscardsettings.

IMMEDIATE: Wait117coldready(card-main/validation.json) andHTTPnewmanifest. Verifyactualweb
PLAY->Noimages, PLAYreturn, FN/MENU. ThenACTUALRESTARTAPItest andsamecontrolsagain.
Needupdate live-guest-read.py allowedruns117 ONLYformodes --export-frame/NEW --card-health;
derivepidfrommanifest+parentchildren, noQMPextra. export-frame viahelper, capture-a7m4-frame
absoluteRUN validatesAP; comparetoHTTPframewhenstaticNoImages. Cardhealthreadonly
auditor+ls-ltwodiagsegments+/tmpim.loglast40 optional. Avoidoldfixedaddressmodeson117.
If117failsrestoreold87legacyimageafterexplicitstopowned117. No needapprovalauthorized.
Updateproofcard-profile-promotion.json primary_activated trueONLYafterverified; currentlyfalse.
DocsBASIC/MAIN/STATUS/README stillstale87/noCARD/failedplayback; UPDATEafteractual117test.
FinalChineseshortnewworkingcard+recoveredplayback/Fn, BUTNOsensor/ISP/JPEG/AF, nophoto.

# ACTIVE116 2026-10-19 — PLAYBACK FIX WORKS; PREPARE LIVE CARD PROFILE
Primary87 STILLrunning SAME S5 URL. Onlysecondary116 native-116-card-controls exec78310
180sec. All105..115ended. DoNOToverwrite main-virtual-card-info.cpio until116ended.
Native115 FIXEDactualoriginalplayback: Noimages frameSHA42cff1354061ea97b3c4cdda221a14224fdef4ec5c5b6fa75de8eeb5123e494d.
PLAYreturnsMain7281..., FNreturnsaff399..., MENUreturnsMain; ALL6storage_controls_checks=true,
ALL8slot2/controlsframeAP/QMPexactRGBtrue. No originalassertion. Cardbefore/afterSHAstill
b9ab56589e96e79845e2e1f40ae9339f318e186fc106941af445fe6d0d1b99c5, NOJPEG.
114stderr/taildiagnosticsidentifiedabort: infra_wrapper_bb_ipsx_ls_branch.cpp:876,
send_no_wait_with_main_thread_i, AP35b8340 send->35b8358assert. LASTBB118shape22B has
byte20=2 onPLAY whileoldguardonlyallowed1. CP a80e0 parser a814a loadswire+20 ->context624;
CPa18ce..a18f6 cmpfield,3 +unsignedbelow3 VALIDATES0/1/2. FieldnameoriginalCPdd9ab5
isEVFpriority. UpdatedONLYbyte20allowed0..2, allother21bytesstrictoriginalshape.
No genericACK/abortbypass. BothoriginalAPandCPfilesunchanged. 115actualNoImagescreenshot
outputs/native/slot2-playback-empty.png. Evidence evf-priority-playback-fix.json.
Thus doNOTchaseF001candidate115 below; realcausewasunsupportedEVFpriority2.

115'sFUNCTIONALchecksallpassed butdiagnosticexportfailedbecausekernelwarning86finterleaved
b64. Newnative_frame removesONLYidentified8fc/86fno-registered-sndwarninglines, keepsraw.
recover-diagnostic-audit.py recovered115tail523611B/3784records, validatesALLheadersbounds+
exactoriginalbyte/countsummary, butoldhelperhasNOindependentsamplesha; limitationexplicit.
Originalfailedsessionresult/logUNMODIFIED. Recoveryjsonsaved, proofreportseparatesfailure.
Newdiagnostic-export.c independentlySHAhashessampledlast512KiB ANDfullsourcefile; native-session
requiresbothvalid. 116testingthis. CurrentChelpersemanticslastcompleterecords, notprefix.

Current116imageaddslive rollingdiagnostics (--rolling-diagnostics ->ROTATE8env): serialize
append/renamewithatomiclock+schedule_yield; everyrecordretainedbeforefree; rotatescurrentto
previous at8MiB, max2segments16MiB. Scopeboundedretention, notlifetimearchive. Probe115full
logwas8.1MB at151s; 116shouldrotateby180s, checkBOOT_LOG_DIAGNOSTIC_ROTATED generation1.
Musttestnewchecksum/rolling. 116controlsframesALREADYallpassed throughmain-after-fn.

native-session ADDED --card-main requiring --auto-main &main-virtual-card-stable.cpio.
Codeprepareonly, imageNOTYETcreated! Refactoredconfigure_slot2('slot2') identicalprobe labels,
newliveconfigure_slot2('card') setsphotoSlot2throughoriginalmenu/referenceRGBcheck.
initialize_card() originalremove/insertcycle requiredinitial andNOWrestartbeforewizard.
--card-main coldinitial+restartconfigured; parserguardssafe. NeedLIVEtestbeforeclaims.
Planwhen116cleanpassed: copytestedinfoimage toSTABLEnewname, hashcheckagainst116artifacts;
copycurrent4runtimescripts tooutputs/runtime. Stopprimary87throughitsownedSTOPAPI, then
hiddenlaunch native-117-card-main on SAMEport18764/tokenS5 withstableimage--auto-main--card-main.
KeepoldprimaryimageHASH7a39...unchangedfallback. Needactualcoldstart/card/PLAYreturn/FN and
RESTARTtest. PanelRESTARTwaitincreased160. Launcherupdateaftertestedimagehashknown.
Currentpublicpanelfootereditedtolabeled64MiBslot2/emptyplayback/noJPEG/resetclearscardsettings,
butold87memoryunchanged. Newcardstatusconditiononly --card-main, oldprofileunchanged.
Don'tpromoteif116errorwithoutinvestigation. Mainfullcamera_bootfalsealwayscorrect.

Toolsrecord-capture-audits currentlylists105..115 butnot116, addnext; reporthasrecoveryjson
notyetincludedneedaddfilename. DocsBASIC/MAIN/STATUS/README stillsayold87/nonworkingplayback;
UPDATEafterlivepromotion. Addlatecrashproof114/113 and115recovery honestseparately.
Latest syntaxcompile passedbeforelatestsmallstatus/footerchanges; retestappropriate.

# ACTIVE114 2026-10-19 — PLAYBACK ABORT / ORIGINAL FATAL TRACE
PRIMARY87 unchanged, healthHTTP confirmed. ALLsecondary105..113 ended. Currentsecondary114
native-114-abort-origin exec38324,160s. DoNOToverwrite main-virtual-card-info.cpio untilend.
Native110..113 Fn-before-shutter changes pixels andMENUreturns, exactAP/QMPtrue.
AllcapturecardSHAstillidenticalbefore/after, noJPEG. OriginalDATABASE/XMLwriteproven.
Correctfull diagnostic receiver size33..4096/payload=size-32 SAMEcaller3724ff8+source8f013a
now consumesoriginalonewayrecords, logsfirst8/powers2. UnknownIPCuntouched.
112 audit SUCCESS: fullstream6294903B/55148records SHA0444d3cfbe4577b3041f535656ac1b0ef159d3eae11d2aff445d65925330afcb.
Read-only diagnostic-export.c hashes/validatesEVERYrecord; savedfirst524133B/8905records
asdiagnostic-events.bin. 111exportfailedcap4MiB andisNOTpassed. 110busyboxbase64absent.
Currenthelper114exportsLASTcomplete512KiBrecords afterfullhash, tocatchfatalerrortail.
Native113 independentPRE_PTRACE kernel snapshot confirmsSeqQueueDispSwi isalready
do_coredump->stop_all_threads_timeout BEFOREanyptrace; AppFw/CameraBackgroundSTOPPED.
SeqQueueCommon remainsinsidekerneludate_wait_for_distribution_done path. Kernelkallsyms
showsuipc_oom+88/ce0 butstaticsymbolsize80B; don'tclaimactualOOMbasedonnearestexportname!
NoUnhandledfaultPCinklog. /proc/330/syscall PC7fa775f07c resolveslibc+3107c =raise+9c!
Thereforeexplicitfatal-signalpath (signalnotyetconfirmed), notjustmissingUIrender.
114newobserverinterposesabort/raiseONLYlogswhenDIAGNOSTIC_SINK enabled; forwardsoriginal,
doesNOTsuppressfailure. SafeFPchainread /proc/self/mem, dladdr module+offset,24frames.
prefixesBOOT_LOG_FATAL_SIGNAL/STACK; native_frame cleaner covers them. Preservesrawlog.
114alsoarchiveslast160linesoriginal/tmp/im.log asoriginal-stderr.console; previouslyonly
menu-load.log wastailread. kernel-log-read.c usesread-onlyklogctl3,1MiBmax.

IMPORTANTNEXTcandidate115 after114identifiesorigin: combine --background-failure (F001)
WITH fixed --diagnostic-sink. Native106failure wasBEFOREreceiverfix, so its frozenplayback
isNOTevidencefailuremodecannotrecoverUI. CurrentcontrolF0003006mayallowdisplaytransition
withoutneededYUVbackend andtriggerabort; explicitoriginalfailuremayhandlelackofpipeline
gracefully. Testthencompare; donotuniversallyACKorignoreabort. Primaryneverusedmodel.

record-capture-audits.py currentlycovers105..112(8runs), shouldadd113/114/115whenended.
Copies512KiBrawsample+hashfulldata+kernel112proof tooutputs/evidence. Addpreptracekernel
andoriginalstderrfiles too. DocsBASIC/STATUSupdatedrealwrites/correct301c; addcrashstate.
outputs/runtime stillneedscopylatesttestednative-session/native_frame/serial/panel scripts.
No promotion. Start-Camera unchangedstablehash. NoactualCPfirmware/sensor/ISP/JPEG.

# ACTIVE110 2026-10-19 — DIAGNOSTIC PRODUCER / CARD AUDIT
Primary87 unchanged and healthy on SAME S5 URL. Secondary109 ended, no photo/no GUI recovery.
CURRENT secondary110 native-110-diagnostic-wire, exec44966, bounded160sec (tests may exceed).
DO NOT overwrite main-virtual-card-info.cpio until110 ends. Only primary87+110.
109 received4730+ exact57B diagnostics but AppFw then blocked sending60B diagnostic
atapp3724ff8 callerchain3728410 (payload28). Originalproducer3724f4c accepts1..0xfe0,
allocatespayload+32 and sendsONEWAY. Current sink validates SAMEcaller+source+header,
size33..4096 and declaredlength=size-32, retainsALLwirebytes with4Blength beforefree.
Observerlogs onlyfirst8/powers2, rawretainedfilekeepsALLrecords. No broadIPCacks.
110 alreadypassedoriginalfirstbootandPowerSaveOfffullRGBreference, enteredsetupmain.
AddedFn-before-shutter/main-before-shutter snapshots and retaineddiagnosticexport.
native-session exports base64 /tmp/a7m4-diagnostic-events.bin atprobeend, validates
EVERYheader+allocationlength and retainsdiagnostic-events.bin withSHA/count/lengths.
Couldexceed8MBsinglecommandlimit ifrecordsverymany; neverdrop/fabricaterawbytes.
record-capture-audits.py nowcovers105..110 whenfinished, compactdiagnosticlogfirst/last,
copiesretainedbin tooutputs/evidence. Currentproof5runs105..109. DocsBASIC/STATUS
updatedrealnativeDATABASE/XMLwriteproof andcorrected301csharedcallmisread.
outputs/runtime stillneedsrecopyafter110 verification. No imagepromotion yet.

# ACTIVE CHECKPOINT 2026-10-19 — CAPTURE AUDITS / CP CONTROL / DIAGNOSTIC IPC
PRIMARY still native87 stable on SAME S5 URL port18764, no virtual card. All105..108 ended.
SECONDARY109 native-109-diagnostic-exact running bounded160s, execsession30720.
Await results; do NOT overwrite main-virtual-card-info.cpio until109 ended. MAX2 QEMUs.

New meaningful evidence:
- card-audit.c compiled into guest as /simulation/card-audit for --virtual-card.
  Uses original libcrypto SHA256_Init/Update/Final,512B context, streaming4KiB;
  opens ONLY /image_mmca readonly, requires64MiB, bounded FAT32 directory walk.
  Guest BusyBox sha256sum missing no longer blocks actual hashing.
- Native105 original firmware CREATED /PRIVATE/DATABASE/DATABASE.BIN 9670656B
  magic9c0cdd8b and /PRIVATE/M4ROOT/MEDIAPRO.XML405B magic3c3f786d. Initialstage
  card has only DCIM/100MSDCF dirs. Audit helper creates NOTHING. Native writes proven.
- Native105 before/afterSHUTTER SHA BOTH46008c1b10bc6a9c15e9417a7ad50373c5fa05758d93d7e82ab88f0487b0901d.
  Two metadata files,11dirs, no new JPEG; card_changed_after_shutter=false.
- Native105 slot2-main,after-shutter,after-play AP/QMP fullRGBmatch true.
- Native107 setup-main AND slot2-main etc fullRGBmatch true as well.
- Native105..108 reachmain, setphotoSlot2, auditbefore,HALF+SHUTTER,auditafter,PLAY.
  All stayed main actual frame afterPLAY as of108. No photography.

Corrected CP interpretation (IMPORTANT):
libObj EA818 setsw1=3006 thenB EA910; EA90c supplies301c to SAME callEA914.
LR EA918 alone CANNOT establish301c request. Direct wire now logs tid/caller and
confirmsCameraBackground274 sends3006 fromlibObj+e9c6c. Previous301c blockingclaim
was a shared-call-site misread. Do NOT implement301c based on that old stack.

New isolated opt-in models, never applied primary:
- stage --background-failure ->QEMU_A7M4_BACKGROUND_FAILURE.
  Exact24B cmd3006/source8102*/callerlibObj+e9c6c ->original12BF001 failure completion.
  Native CP31eb66/31eb7a/90f086/320bb4 andAPe9cdc..e9d00 justifyfailurecontract.
  Native106 proved internal e9be0 wait exits; thread returns ordinaryeaa24 receive.
  Still no workingplayback/photo. Modelexplicitlyreportsfailure,notready.
- --background-control ->QEMU_A7M4_BACKGROUND_CONTROL mutuallyexcludesfailure.
  ONLY3006/3007 samewire/callsite guards, softwarestateinitial3007, atomicstatechange,
  original12BF000completion, no CP codeexecution/sensor/ISP/frame/JPEG produced.
  Native107/108 model logs3007->3006, but AppFw still blocks elsewhere afterPLAY.
  Legacy always-idle3007 fallback disabled only underthismodel.
- Stageflags requireisolated--virtual-card; primaryimage untouched.

Current diagnostic IPC investigation:
Native106afterPLAY AppFw276 waits under app3724ff8->osal_snd_msg, queue8f013a.
AP37282c0 ->3724f4c diagnostic event buildsheader{u16type2,u16cmd83,u32kind,u32len25},
usesnativeclock3724b24 at+16, payloadat+24, source8f013a, send3724ff4.
CRITICAL allocation ispayload+0x20 at3724f74, thus57B not49B!
--diagnostic-sink ->QEMU_A7M4_DIAGNOSTIC_SINK catches ONLY that precise57B event,
callerappFw+3724ff8/source8f013a/header2,83/len25. SavesALL57B with4Blength inone
appendwrite to /tmp/a7m4-diagnostic-events.bin, then consumes/freesoriginalmessage.
No syncqueries/other messages/camera completions handled.
Native108 used WRONG49B guard, nevermatched; not proofreceiverfailedsemantically.
Native109 fixes57B guard. Check BOOT_LOG_DIAGNOSTIC_RETAINED counts and after-playframe.
Ifstillnomatch, addreadonlyobservedtrace for exactcallsite; don'tbroadenunknownIPC.

native-session new --probe-storage-controls requires --probe-virtual-card --auto-main:
Originalmenu routeknown ->snapshotSlot2exactRGB reference ->MENUtwice ->slot2main.
Readonlyauditbefore/afterHALF+SHUTTER, thenPLAY snapshot.
NEW109 also PLAYreturn,FN,MENU snapshots play-return/fn-after-play/main-after-fn.
Aftertests takesCameraBackground/AppFw/IWrapperImaging stacks thenboundedend.
Native107+ records runtime-artifacts.json hasheskernel/initramfs/dtb/scripts and
initial-card-profile.json BEFOREboot. Native105/106 imagehashnotretained; don'tinventit.
NewtraceBOOT_LOG_IMAGING_REQUEST nowincludes tid/source/callerlib+offset/bytes/payload.
Nativeframecleaner covers BACKGROUND_* and DIAGNOSTIC_RETAINED observers too.

record-capture-audits.py writes outputs/native/evidence/capture-and-card-audits.json,
currently105..108 only; add109 to names afterend. Copies slot2-main-verified.png and
slot2-after-shutter.png from105 actualQMP. These are full AP/QMPexactmatch true.
Older basic-functions/docs still saywriteunverified and301c maybeblocked; UPDATEafter109.
outputs/runtime copied BEFOREthisturnchanges; recopy currentnative-session/native_frame/
serial/panel afterverification. Start-Camera currentlystilllaunchesoldstableimagebyhash.
No latestprofilepromotion or CPcaptureclaim. Userprimaryremainsrunning untouched.
# Continuation checkpoint 2026-10-19 — SLOT2 CARD NOW MOUNTS / PHOTO TARGET SELECTED
PRIMARY still native-87-basic-stable, same S5 URL/port18764; unchanged original image.
All secondary probes through native104 are ENDED. Only primary87 should run now.
Do not claim photography or working playback. No new CP completion model implemented.

Key fixes verified this turn:
- seed-virtual-card.c byte0 MUST=2; native libInfraMediaDetect ParseInternalMessage
  0x10a9c compares byte0 to2. Kernel accepted0 but user-space rejects it.
- Native notification state0/1 includes initialization; NOT raw insertion status.
- Removed speculative A2=1,A3=0,A4=0 dummy status overrides. All original defaults1.
  Front insertion comes from exact7B record independently.
- Native RM config 112B: entry0 disabled; entry1 id1 mask2 type2 SD/dev/mmca;
  entry2 id2 mask5 type6 hybrid mmcb+SxS. Slot2=>device1010,/nondev/rm2,port1.
- Current seed sends byte0=2,byte3=7,byte5=2 (SLOT2 inserted); ports0/2 empty.
- Native100 original Fsys_Mount rm2 ->0, driveA; DriveInfo and FreeSpace ->0,
  FAT32 64MiB valid. Stays original language12e, no view330 warning.
- Native101 auto-main with explicit --probe-virtual-card reaches original main0/585,
  original powerOff page exact RGB reference passes. Main AP/QMP check false due
  asynchronous render; do NOT claim whole-frame equality for main101/104 snapshots.
- Native104 actual original menu changed PHOTO Recording Media Slot1 ->Slot2.
  Screenshot outputs/native/slot2-recording-media.png; checked actual main shows boxed2,
  no NO CARD text. Video target remainsSlot1 (not changed).
- Native104 PLAY creates352/8f but AP and QMP remain original main overlay.
  Last logged CP request3006 source810261c3, while CameraBackground274 stack waits
  libObj e9ca8 viaea918 (301c call). BOTH missing transitions may be relevant.
  Audited stack/data retained in native104/card-audit.console; no generic success ACK.
- BusyBox sha256sum APPLET MISSING; audit did not produce card hash. NO write/photo proof.

Slot1 failure research:
- Native98 diagnostic mcmn_drv_debug_error_rootdevctrl=>error80000004 sourceD lineB23.
  In libInfraMediaCommon3a698 hybrid mount, calls3a4a8 to read PCI config.
  /proc/bus/pci/0001:01/00.0 missing. Config class at+8&ffffff00:
  01080200 ->state1,01800000->state0,other->state2.
- Native99 narrow open64 fallback to256B class metadata got pastB23 but failedB39:
  selected hybrid submodule absent (/dev/sxs_blk0 fromnativecfgtypeB0).
  The fallback and fixture generation were REMOVED from current sources before100.
  An unused old simulation/virtual-sd-pci-config.bin may remain ROOT, never referenced.
  Do not revive it or pretend it emulates PCI/SxS.
- 80cf016d is ORIGINAL libInfraMediaConfig callback (ctor6688, CallbackPoint62e8),
  not missing kernel/input frontend. Don't chase input.ko/media.ko for this queue.

Infrastructure fixes:
- native_frame.py new shared cleaner removes only identified OBS DATE/AP_STATE/
  IMAGING_REQUEST/MEDIA diagnostics from frame export; original capture validates
  full container+checksum. Raw serial logs remain untouched. native103 failed b64
  export was reprocessed successfully (snapshotSHA68ff224b...). Native104 3 exports
  passed first attempt with new cleaner. snap stores export-N.console, max3 retries.
- Native102 was stopped early because101 had not ended when launcher was started.
  It is not a passed test. Added startup max2-QEMU process guard to native-session.py.
- Nondefault web port writes live-panel-18765.json; primary manifest is preserved.
- Native104 test web18765 was stopped cleanly through its own STOP API.

Current experimental image main-virtual-card-info.cpio, observerSHA:
63fc0be67bfb5cfa31cd006ff5ef7aed55a18ce0351868a676602084f8ef3a58
Verified SHA in cpio matches built observer. No image promotion to primary.
--auto-main now allows explicit --probe-virtual-card +main-virtual-card-info.cpio.

Outputs updated: BASIC-FUNCTIONS.zh-CN.md, STATUS, MAIN-UI, README, runtime scripts
including new native_frame.py. Start-Camera.cmd/ps1 opens existing panel or validates
old primary imageSHA7a39d7cf... and launches --auto-main. PS syntax passes; launch route
itself previously tested via87 restart. Launcher NOT independently cold-launch tested.
Evidence basic-controls-native87.json, virtual-card-probes.json contain11 probes93..104,
including103 failed then recovered export. basic-fn.png, slot2-recording-media.png,
slot2-selected-main.png actual QMP output. Final links only outputs/ directory.

Potential next work CP protocol, NOT yet implemented:
- CP31e656 checks3006 via90e848->90b8fc: mode3006 alreadyready if global143c0fc==1.
  Alreadyready sendsF000 via90f086->320bb4 (12B kind1/cmd3006/token/status).
- Else31eb44 calls90deac; that sends native query920162 to92a20845, checks flag at
  *919a82()+54 ->byte2; ifset returns-1. 31eb66 then sendsF001 (failure) via90f086.
  Successful90deac sets savedtoken and requestsstate3006 via90df5e/31cd0c.
- libObj e9be0 request24B onlyinitializesbyte0 andcommand+2; other bytes uninitialized.
  It waitsdynamic8102 replyqueue. StatusF001 ->return0; F002 ->special; F000 ->return1.
- CP90f092 success301c reply is12B kind1/cmd301c/token/F000; need locate full301c
  handler and state preconditions before implementing. Don't fabricate universalACK.
# Latest continuation 2026-10-19 — BASIC CONTROLS / VIRTUAL CARD WORK
Current PRIMARY: native-87-basic-stable, SAME URL S5jrCd45BfZKkoQmYa7c0ASfeT12LoLl.
Hidden Windows launcher PID10140. Host logs native87-host.log/.err on D/menu-a7m4.
Primary image remains main-ap-state-consumer.cpio, no experimental virtual card.
Start with --auto-main. Original firstboot UI replay now automated with original view-ID
checks, English, Beijing+8, host date, native Power Save Off. Initial run AND actual panel
RESTART completed; actions.jsonl records successful RESTART with final original main.
Fn7095 opens original Drive Mode quick grid; Play1f7 opens original no-card playback,
second Play returns. DISP1f9, Half1f1, Shutter half1f1/full a7, Delete1f8 added to panel.
SHUTTER STILL DOES NOT PRODUCE PHOTO. No sensor/ISP/CP imaging engine.
New native-serial.py retains the complete console: reference menu_live.serial_command
truncates at16MiB, while native-session had non-APPEND stdout; this created sparse logs
and broke view-ID restart checks. Native-session now uses own no-truncation serial
transport plus APPEND log and actions.jsonl. Key delay .25s with auto-main and guarded
MENU view2d6 avoids previous native85 Lens popup race under2-VM load. Native85 failed
power screen acceptance and ended; do not claim it passed.

Storage experiments: native86/88 FAT12 and native89/90/91/92 FAT32 probes ended bounded.
Only primary87 should remain unless next probe explicitly running. MAX2 QEMU VMs.
Added stage --virtual-card requires --file-media --native-media-driver. seed-virtual-card.c
sends exact7B original mcmn_drv port record to8028017c source92840747, byte3=7 validports,
byte4=2 slot0 inserted, other ports empty. --remove sets byte4=0. Original kernel
mcmn_drv.ko .text1000..1238 consumes this; original driver confirms first record.
Original mcmn file backend selected via EXISTMEDIADRIVER0. DO NOT bypass omit-write.
Archive fwtool.writeFat ALWAYS FAT12; unsuitable64MiB image (cluster count too large).
Now uses installed Ubuntu dosfstools/mtools, standard64MiB MBR+FAT32 partition atLBA2048,
DCIM/100MSDCF directories. fsck.fat -n passes. Profile D/menu-a7m4/work/virtual-sd1-profile.json.
Native91: original dummy open /dev/mmca fd42, sector_bytes512, sectors131072, status1.
Fsys_Mount /nondev/rm2 ->result0 drive65(A); ORIGINAL GetDriveInfo AND GetFreeSpace ->0.
So native FS can read FAT32/free clusters; APP STILL SHOWS SLOT1 CARD UNREADABLE.
Native92 event diagnostics show BOTH device1000(mask5) AND1010(mask2) state0 then1.
File backend defaults all three DBG_DRV_DUMMY_RM{1,2,3}_STATUS=1, so it reports inserted
cards for unused/missing backing devices too. Current next hypothesis: align dummy
ports with single-card profile. prepare-display-port now sets named A2=1,A3=0,A4=0
ONLY if QEMU_A7M4_VIRTUAL_CARD, identity checked, no original outputs overwritten.
Stage sets this variable for --virtual-card only. Rebuild execsession71035 currently
running/completing; next stage main-virtual-card-info.cpio then native93 bounded probe.
Keep user primary87 running; do not replace it until virtual-card UX validated.

prepare-display-port diagnostic wrappers original-forward unchanged: mcmn_drv_open,
dummy_open (geometry), Fsys_Mount plus readonly GetDriveInfo/GetFreeSpace, original
NotifyInOutEvent and NotifyInOutEventByMediaInfo payload fields. No status forced.
No new image stream or fake JPEG. Native libInfraMediaDetect events dynamic PLT wrappers
work; no vtable/inline patch needed. Do not implement proposed inline/vtable hooks.

Failed persistence experiment: Backup_sync_all with Backup_save1 BLOCKS indefinitely
waiting missing hardware/CP. Stopped old native83 cleanly via owned panel; guest tmpfs
was destroyed. Removed save-live-settings.py/backup-sync-export.c/build helper sources.
Do not retry this live; user personal settings NOT persisted, only UI replay implemented.
live-guest-read.py now accepts exact83/84/87 names, validates live PID descendants, only
83 permits hardcoded --input-layout/--physical-input-table. --export-frame on87 works.
Latest87 checked AP export snapshotSHA2efc2af5bc9da83a617e2083d02d6b961da368dfc53ecd076089f4b060730779,
sequence7932/source7920,148RGBAcolors. capture-a7m4-frame.py run absolute path.
outputs/native/basic-fn.png copied from actual87 QMP scanout. Need update final status
and save restart/key/storage evidence once current probe result available.
CUA userCameraTab tab5 browser2 sameS5 URL, controls new. After summary rewrite docs.
Last clicked RESTART completed successfully, actual original main. Mark deliverable final.
# Continuation checkpoint 2026-10-18
LATEST OVERRIDES: MAIN UI OVERLAY NOW SHOWN AND VERIFIED. Native83 live aftera cold
RESTART plusoriginalwizardreplay. English,Beijing+8,2026-10-18 setthroughUI; native
DELETEcode1f8 selects Setonthecamera onCreatorsAppintro. Closedoptionaltempandtutorials.
Originalview0/count585 showsJ.FINE14M/AF-S/MECH/AFON/NOCARD. NO liveview/ISP/AF/photo.
QMPactualPNG matchedentirecheckedAPsnapshot exactRGB SHA9a8fcc29922344d82a9907834452d51e2295af92ca76fa6e44e3ca47947d553d.
Evidence outputs/native/evidence/main-ui-native83.json andactualmain-ui.png.
OriginalMENUentersMainhome menu, MENUreturns. SetupPowerSaveStartTimeOff setthroughUI,
confirmationUPENTER, actualmain-power-save-off.png saved. CurrentOffwasappliedAFTER
coldrestart;no futurefirstboot/autopower replayimplemented yet. CurrentrunningVMkeepalive.
Idle QMP stability check105.167seconds PASSED,execsession60725complete.
NO CARD blinks andsomeindicatorsautohide; checkerrequiresnativegreen-cameraandbottom
touchmarkerregionsconstant, notallRGBidenticalacrosstime. NOT sensorstreamacceptance.
Currentuserbrowsergoodtab5 bounduserCameraTab nowS5URLandmarkedDeliverablethisturn.
Tab2coldBootTabsameURL, leaveoldblocked3/4alone. Bothnative54and81stopped;only83running.
live-guest-read.py updatedguardnative83. --export-frame read-onlyAPexportworks;
--set-on-camera emitsoriginalDELETEshortcutonly forknownCreatorAppsetupcontext.
capture-a7m4-frame.py nowselectsLASTcompletedexport, removesonlyidentifiedDate/APstate
progressrecords,andoriginalwhole-containerlength/checksumidentitystillchecked.
README/STATUS/MAIN-UI docs updated. Do NOT claim completecamera/emulatedoriginalCP.
NeedfinalChineseconcise mainUIexists/menuworks/powerOff/no livevieworphoto,linkliveURL
andactualoutputs/native/main-ui.png. Awaitstabilityresultbeforeclaimingidlepass.

User wants FULL original ILCE-7M4 6.02 QEMU main UI ASAP. Main UI overlay achieved; still NO liveview/capture.
Major progress this turn: unforced cold boot now reaches original first-boot LANGUAGE page.

Current live VM is native-83-cold-panel (launching); URL:
http://localhost:18764/S5jrCd45BfZKkoQmYa7c0ASfeT12LoLl/
Host hidden launcher PID38552, logs D:/CodexWork/sony-a7iv-qemu/menu-a7m4/native83-host.log/.err.
Image main-ap-state-consumer.cpio, NO --menu injection, --native-media-driver.
Old native54 and native81 were cleanly STOPped via owned panel API. Do not revive old live54.
Max2 QEMU VMs (RAM7.7GB). Native82 bounded test ended successfully. Only83 should run.

Immediate task: finish actual original first-boot wizard via panel keys, then verify main UI.
Native82 fixed DOWN/UP/ENTER/MENU: pixels changed, DOWN/UP restored Japanese selection,
ENTER opened view1e3/count11, MENU returned language12e. Every QMP/AP frame matched.
Language baseline pixelSHA b127de144dbac6d6b031fa020639331efe78992e649098908a218b685a40cbcf.
Select English with UP then ENTER (for diagnosis; user Chinese, chooseChinese later if useful).
Need screenshots after each page. Do not blindly click through terms if any appears.
New panel-server label says original boot debugging / main UI incomplete.
Old accepted menu-only Start-Menu.cmd remains, don't call it full boot.

Critical fixes:
1. Native70 BB0119 reverse config completion accepted. Original UI first showed Japanese
   slot1 unreadable-card warning,14colors pixelSHA0aead4673f7e7dcbab95196a921b88ef8ee77a79639dd32e9eb42da8b2d38e33.
2. Native73 background idle CP3007 reply accepted; four main workers returned idle.
   Original CP31e67e->90e0ca already-state3007 ->90f0ae->320bb4 builds12B kind1/cmd3007/token/f000.
   AP CameraBackground libObj ea668->e9be0 waits this before replying original app10/20 request.
   Strict model holds idle (no running imaging pipeline), preserves token/source; no sensor transition.
3. Card problem FIXED with original /usr/kmod/mcmn_drv.ko loaded after upm.
   All dependencies already met. Native80 NATIVE_MEDIA_DRIVER_STATUS=0, extra5threads,
   original firstboot language page instead of card error. Driver untouched.
   Stage --native-media-driver inserts direct insmod; DO NOT use busybox timeout (not compiled).
4. Native81 language page got frozen due SHARED MESSAGE POOL LEAK, not key codes.
   AP sends748B everyframe to CP9088076b with no receiver, real_send returns0 but leaks.
   UI eventually blocked allocating9088076b; InputMain208 blocked logger timestamp910042
   also because shared pool exhausted. Native82 strict model consumes/frees these snapshots.
   AP serializer183c9a0 (bulk),183cac0(single), send return183ca4c,183cbxx.
   Headeru32kind,u32payloadsize (size-8); bulkkind0 contains up to64 entries {u32id,u32len,data}.
   Validate bounds, persist EXACT APbytes /tmp/a7m4-ap-model-state.bin then real_free_msg.
   No fabricated rendered pixel or completion; CP composition not implemented.
   BOOT_LOG_AP_STATE_CONSUMED logs powers of2,256/512/1024/>1790 accepted, NO error76b.
   Native82 input resumes andAP/QMP actualimages change. This is key current fix.

Optional ORIGINAL file storage experiment (native77/78) did NOT fix card error; notcurrent83.
Stage --file-media hashchecksM4libInfraMediaCommon.so ec454c50b13aa78621fd8f0a6a9a8899b5194e446ed1b5fcefb34996b3f73a39.
mcmn_param_init forwardsoriginal, namechecks EXISTMEDIADRIVER=0x69,DBG_DRV_DUMMY_OMIT_WRITE=0xf9;
sets original filebackend0, leavesOMIT_WRITE0. Two isolated4MBFAT files image_mmca/mmcb.
Files remain inmenu-root, but env notenabled unless--file-media. No physical media touched.
Diagnostic wrappers original RMGetInOutStatus/Fsys_Mount forward unchanged, no calls observed.

Native sessions/tools:
WSL Codex-Z8-Qemu root only, cwdWindows C:/Users/16483/Documents/Codex/2026-10-17/new-chat.
work/sony-a7iv scripts, D:/CodexWork/sony-a7iv-qemu large assets.
A=/opt/sony-a7iv/menu-a7m4/runtime/analysis; R=A/menu-root.
prepare-display-port.py --window compiles all current models. No --menu for coldboot.
stage-runtime-a7m4.py --init menu-init-display --image UNIQUE.cpio --window --system-sound
 --native-media-driver --enable-service libBusPower.so --enable-service libInfraCrypt.so.
native-session.py --display none --name UNIQUE --initramfs UNIQUE.cpio --test OR --seconds60.
--inspect-manager reads manager+398..3d8; --inspect-threads ID... tolerate ptrace6 via||true.
Script menu_boot fixed now trueonly menu-window.cpio; visible_boot newflag; full_camera_boot false.
Live83 launched beforethis cosmeticresultsflagchange, soitsresultsold menu_bootcolorflagnotacceptance.
resolve-guest-stacks.py RUN --tid N resolvesactualmappings. IDs shift+5 whennativeMCMN loaded.
Native83 IDs likely193 im.elf,275AppFw,208InputMain,210InputRecv,313..316workers; verifyfreshlogs.
Disassembly: disassemble-firmware.py app VA LEN or cp RAW_FILEOFFSET LEN; CPVA=file+108000.
inspect-media.py LIB.so VA LEN genericELF, q LIB.so POINTER..., mode IDs, symbols LIB REGEX,
strings APPVA LEN, endpoint scansMOVZ/MOVK8102021f (already identifiedCameraBackground).
disassemble-module.py SYMBOL LEN --module mcmn_drv.ko/upm.ko etc --offset=... (defaultdmm).

REA skill already used/read. Provider supportsPE only; staticoriginalCapstone fallbackapproved.
All old agents usage-limited, do not retry/spawn. No new goal set.
No physicalcamera/USB/networkguest touched. Clock2MHzverifiedoriginal, do notchangeforidle.

Browser CUA documentation read this turn. Selectedbrowserid2. Binding coldBootTab tab2 on
S5URL above, works; screenshot/AX available. Last screenshot Japanese language selection.
Old a7m4StableTab tab5 on24E6 URL now404; usermaystillbeonthisoldtab. open_in_codex(newURL)
was queued; can navigate tab5 toverifiedS5URL if needed, don't touch blockedtabs3/4.
Aftercompaction call cua.rewriteDocumentation beforebrowseractions. UsefreshAX orPWbuttonnames.
Buttons ↑/↓/←/→,确认,MENU / 返回. AfterclickAX immediatelydisabled, nextPWclick waits.
Current handoff screen shouldremain shown: markDeliverable on actualtabbeforefinal.
Avoid snapshotsensitiveotherapps, capture_screen_context voiceonlyforbidden.

Owned live guest diagnostic helper live-guest-read.py currently HARDCODED native81 ONLY,
whichhasbeenstopped. Do notrununtilupdateguard to83 and rederiveanyaddresses.
It validates live-panel.json Linuxparent PID, traverses children toexactowned qemu,
opens /proc/QEMU_PID/fd/0 O_WRONLY andwritesbounded serialcommand (noextraQMPclient).
This works! Currentdefault readsall I-InputMain/I-InputEvent/AppFw stacks; --held-up native
300ms keytest didnotfix81poolleak. Notneedednow82fixworks. SerialreadhelpersnoAPmutation.
Use /bin/busybox grep/tail explicitly (shelltail symlinkmissing); timeoutappletabsent.

Deliverables outputs/sony-a7iv-qemu/native:
firstboot-language.png =actualnative80QMP, evidence/coldboot-language-native80.json.
coldboot-card-warning.png native70, evidence/coldboot-visible-native70.json.
evidence/firstboot-input-native82.json verifieslanguagekeys andnexte3view.
STATUS.zh-CN.md currentlyupdatedonlynative73, mustupdate80/82/latestfirstbootresult.
EarlierREADME/Start-Menu acceptedmenuonly keep honest. Finalfilelinks ONLY outputsabsolute.
FinalshouldnotclaimmainUIunlessactualverified. Showactualscreenshotifhelpful.

