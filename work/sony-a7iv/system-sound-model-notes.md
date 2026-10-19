# Original A7M4 system-sound startup contracts

All CP locations are raw file offsets in SHA256
7b9b137d696e5972d20db7f9119076172ed8e0730805d7f0b4c31b87689e2c2b.
AP locations are ELF VAs. This is a finite virtual configuration/resource
model, not audio playback or execution of the original CP.

Native63 completes11 virtual topology bindings. Its startup thread308 waits
in3157b38, called from317a49c. Concurrent pool305 waits in35bbaac on032e;
pool306 waits in35bc870 on033d. The original application treats errors from
these initialization calls as fatal (3173518..31735a8 and317c9c8..317ca60).

## 032e system volume

Observed request: 200d/032e/10/8001, bytes+8..9=08,00. AP35bba10 builds
this setter; original string4bfa7d0 names `adf_set_volume`. CPb1830 converts
it to2004/0311/12/1 for9058003f. ADF4beb52 invokes63d00, then4beb6a builds
8311/12/1/status0. BB4f2d2c returns132e/12/8001, preserving that result.

CP63d24..63d66 accepts values1..16 and normalizes them to0..15.63d90 retains
the normalized setting; the function also calls AVIO when applicable. The
virtual implementation retains both representations and returns the normal
configuration completion. It provides no audio output.

## 033d original system-sound resource address

AP35bc818 constructs200d/033d/8/8001 and expects133d/24/8001. Result is+8,
and the64-bit address is+16 (35bc870..35bc880). String4ba5587 names
`Success adf_sys_get_system_sound_address`.

CPb28a0 sends2004/020a/8/1 to9058003f.4d57b8 obtains a pointer to the
driver's64-bit address using propertykey00fa01a0, reads both words, and
4d583a builds2004/820a/24/1: address+8, result+16. BB4f31a8 explicitly
recognizes820a and copies address+8 to133d+16 while placing result at+8.

The virtual resource is original `/usr/share/avsystemsound/SysSound.bin`,
77504bytes, SHA256 dae3d18d37b85a22398573f04090a4a95a97052380f4b2b4402a374516399dfb.
The CP copy is byte-identical. `beeplist.txt` contains offsets into it.
The model loads this file into a separate0x20000-byte reserved physical
range41ea00000..41ea1ffff before publishing the address. Stage option
`--system-sound` enables both the guest model and exactly one memrsv entry;
staging verifies that the range does not overlap other reservations.

This establishes backed virtual resource storage, not a real sound engine.
Native64 accepts both additions and issues0327 to register beep1 at the
published bank, length256. Native65 accepts that descriptor and issues032a,
the per-sound volume setter (bytes04,01 = volume4 for soundID1). CPb0fc4
forwards it as2004/0204;4f2be4 builds132a/12/8001/status.

Native65 independently dumps the whole reserved range using QMP pmemsave:
the first77504bytes exactly equal original SysSound.bin with the SHA above,
and every remaining byte is zero. Original AP still has a black frame. The
native66 probe retains bounded per-sound volume settings; original AP registers
active IDs1..16 and their volumes, and pool306 returns to idle. Main boot
reaches317a4e8 awaiting0328. CPb0d48 maps requestbyte8&7 to2004/0202;4f2b40
builds1328/12/8001. Native67 retains that three-bit output path mask and the
original logger reports `Success adf_sys_set_path` at317a4fc. Main thread
advances to317a5d4 and waits on digital-level enable (912f0335/cmd3/24bytes).
