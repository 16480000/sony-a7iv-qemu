# A7M4 6.02 cold-start abort: independent read-only review

Reviewed 2026-10-18. No firmware, observer, launcher, or VM files were changed by this review.

## Conclusion

The captured stack is credible, but `appFw+0x3178320` identifies a **shared fatal exit**, not a uniquely date-related failure. The six inspected failures consistently preserve the register arrangement of the later `model::sequence_boot::run_i()` API checks, not the earlier date-add error path. The absence of both date GOT observer calls and the validated `0x3797480` entry probe is therefore consistent with the stack. A date root cause is not established.

The strongest current narrowing is a checked API call between `appFw+0x3179478` and `appFw+0x3179bb4`, before the instructions at `0x3179c20` change the preserved registers. A forwarding probe on the original formatter at `0x37258d4` can recover the original source line and error code and distinguish these calls without changing their result.

## Binary identity and address conversion

- Examined `/opt/sony-a7iv/menu-a7m4/runtime/analysis/menu-root/usr/lib/appFw.so`.
- SHA-256 independently read: `1e1b9202eaa69198f20df03dbfdab2f103b206cc4ebcd2e7bd817e6a710018a2`.
- ELF executable `PT_LOAD`: file offset `0`, virtual address `0`, file size `0x50bba57`.
- The second data `PT_LOAD` differs: file offset `0x50bc648`, virtual address `0x50cc648`. Thus the current unwinder's file-offset notation should not be reused as an ELF virtual address for this data segment. This does **not** affect the executable return addresses discussed here.
- `native-32-resource` executable load base is `0x7f59196000`. Its return addresses map directly to `0x364badc`, `0x3178320`, `0x317ab00`, `0x32edf8c`, and `0x3796ab0` by subtracting that base.
- Static identity and conversion match. A separate live instruction-byte comparison, prepared by the parent, remains useful to establish runtime code identity after observation patches.

## Stack-chain verification

Source: `D:/CodexWork/sony-a7iv-qemu/menu-a7m4/native-32-resource/console.log`, its `[register dump]` and `[stack dump]`, interpreted using only printed stack words.

Relevant frames:

| Saved frame pointer | Saved return address | Static interpretation |
|---|---|---|
| `0x7f46473600` | libc `+0x2a97c` | `__assert_fail` called libc assertion base/abort path |
| `0x7f46473650` | app `+0x364badc` | return from the `bl __assert_fail` at app `0x364bad8` |
| `0x7f46473680` | app `+0x3178320` | return from `bl 0x364bab4` at app `0x317831c` |
| `0x7f464736d0` | app `+0x317ab00` | `run_i()` caller return, after `bl 0x31780b4` at `0x317aafc` |
| `0x7f46473830` | app `+0x32edf8c` | outer dispatch caller |

The apparent gap in frame sizes is explained by the actual prologue at `0x31780b4`: it subtracts `0x1a0` from SP and establishes FP as SP+`0x40`. With outer FP/SP `0x7f46473830`, its FP is exactly `0x7f464736d0`, and its call-time SP is `0x7f46473690`. The fatal wrapper allocates `0x10`, giving FP `0x7f46473680`. libc `__assert_fail` allocates `0x30`, giving FP `0x7f46473650`. These exact sizes match the dump; no invented frame or stale linear stack scan is needed.

`0x364badc` itself begins another function, but its appearance in the stack is the return PC immediately after a nonreturning assertion call. It does not mean that following function ran.

## Why the return address does not establish a date failure

The direct date-add call at `0x3178248` calls `0x3797480`. A nonzero result enters date error formatting and eventually reaches:

```
0x3178310  mov w0, #0x86a0
0x3178314  movk w0, #1, lsl #16
0x3178318  bl usleep
0x317831c  bl 0x364bab4
0x3178320  ... unreachable normal epilogue ...
```

However, this formatter/fatal tail is shared. Within the containing function (`0x31780b4` through `0x317aacc`), static Capstone review finds:

- Three explicit branches to `0x31782f0` (`0x3178424`, `0x317850c`, `0x3178818`).
- One explicit branch to `0x31782f4` (`0x3178744`).
- **41** explicit branches to `0x3178740`, which routes to `0x31782f4`.
- Two branches directly to the normal epilogue `0x3178320`; those bypass the fatal call and cannot themselves explain a saved LR of `0x3178320` inside the fatal wrapper.

Most of the 41 branches arise after unrelated API return checks. Therefore the LR alone cannot select the date path.

## Preserved register evidence selects the later checks

libc `__assert_fail` at `0x2a930` saves original x19/x20 at FP+`0x10`, and x21/x22 at FP+`0x20`. This is verified from its original instructions, not inferred from variable names.

Across `native-32-resource`, `native-34-date-check`, `native-35-date-check`, `native-36-date-check`, `native-38-date-check`, and `native-40-date-check`, the saved values are identical after subtracting each run's app base:

| Register | Saved value / decoded original string |
|---|---|
| x19 | app `+0x4ba5a88`: `void model::sequence_boot::run_i()` |
| x20 | app `+0x4ba54be`: `sequence/sequence_boot.cpp` |
| x21 | app `+0x4a8afed`: `[SEQ]` |
| x22 | `0x15` |

The earlier date-add error path sets **x20 to `[SEQ]` and x21 to the source path**, the reverse of the captured arrangement. Later API-failure blocks such as `0x3179484` onward set exactly the captured x19/x20/x21 arrangement.

Within this function, the later x22=`0x15` assignment occurs at `0x317945c`, followed by a checked `bl 0x35adf4c` at `0x3179478`. The next x22 change is at `0x3179d8c`. In the captured abort, original x25 is FP+`0xf8`, x26 is FP+`0xe0`, x27 is `8`, and x28 is still a full 64-bit model pointer. `0x3179c20` onward would replace w28 and w25 with small return values, which excludes that later interval for this captured register combination.

These combined observations support the interval `0x3179478` through `0x3179bb4`. They do not yet select a single check within that interval.

## Existing date diagnostics

`native-40-date-check/console.log` records:

- `DATE_BOOT_READBACK expected=662806800 actual=662806800 ... timezone=540`.
- Periodic original `date_time_add_seconds` calls with `2021-1-1T9:0:...`, delta `-32400`, and native result `0`.
- `DATE_CHECK_BIND` and `DATE_CHECK_APP_BOUND` installation success.
- Seven `DATE_CHECK_SLOT` readbacks retaining the private forwarding observer address.
- No `DATE_CHECK_APP` call record before the same abort.

The validated shim entry probe remaining unused corroborates the later-API interpretation. It is not evidence that the diagnostic observer changed a date result.

## Candidate error code and limits

In the captured `run_i` frame, FP+`0x130` currently contains `0x13`. Several candidate later API calls use this location for their result. Other fields in this frame are reused; treating `0x13` as the final API error remains an inference until the shared formatter reports its original arguments.

For comparison, original conversion helper `0x3640040` uses this confirmed table:

| Native OSAL result | Converted result |
|---:|---:|
| -1024 | 0x0f |
| -1023 | 0x10 |
| -1022 | 0x11 |
| -1021 | 0x12 |
| -1020 | 0x13 |
| -1019 | 0x14 |
| -1018 | 0x15 |

The many nearby `-1021` messages cannot alone establish the failing call. If the frame value `0x13` is the actual final result, the conversion would correspond to `-1020`, not `-1021`.

## Smallest next observation

Original logger `0x37258d4` is variadic and formats its arguments using the original `vsnprintf`, then routes the resulting text onward. Its first 16 bytes contain no PC-relative instruction:

```
sub sp, sp, #0x200
stp x29, x30, [sp, #-0x20]!
mov x29, sp
str x19, [sp, #0x10]
```

A preserving entry observer can copy the format and x1-x7 for the sequence-boot errors, then execute those original instructions and continue at `0x37258e4`. On the common error-format call, x1 holds `sequence/sequence_boot.cpp`, w2 the original source line, and w3 the error. This is a more discriminating next observation than additional date substitutions. It must preserve floating-point arguments too because the original function is variadic.

Still unknown: the precise failing source line, its immediate device/OSAL operation, whether a missing queue, invalid resource state, or other CP contract causes its return, and runtime instruction readback at the specific failure block. No claim of a fully native cold boot is warranted from these logs.
