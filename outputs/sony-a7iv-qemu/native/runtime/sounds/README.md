# Experimental electronic-shutter sound candidates

These WAVs are **not decoded by the original camera's CP/AIP audio engine**. They are an
experimental extraction used by the loopback web page's shutter-sound selector and for
download/audition.

Source: original `/usr/share/avsystemsound/SysSound.bin` and per-sound `.bin` files
(SysSound.bin SHA-256 `dae3d18d37b85a22398573f04090a4a95a97052380f4b2b4402a374516399dfb`).

Extraction hypothesis:
- each sound is stored as 32-byte blocks (`Size` values in `beeplist.txt` are multiples
  of 0x20);
- each block begins with a one-byte value < 0x20, treated here as a block header and skipped;
- the remaining 31 bytes are treated as signed 8-bit PCM.

The two candidate sample rates, 8 kHz and 16 kHz, are both auditionable because the original
AA_RT header/rate handling is still unknown. This produces plausible-looking PCM and strong
tonal peaks, but it is **not proof** of the original codec. The original CP ADF/AIP path is
not executed by this QEMU setup; its AA_RT codec has not been decoded.

Files:
- `shutter-ka-sha-8k.wav`: Shutter_Ka + 40 ms gap + Shutter_Sha at 8 kHz
- `shutter-ka-sha-16k.wav`: same at 16 kHz
- `shutter-kasha-8k.wav`: `Dslr_Emnt_High_10FPS_Kasha.bin` at 8 kHz
- `shutter-kasha-16k.wav`: same at 16 kHz

Do not flash these into a real camera. They are web-layer audition assets only.
