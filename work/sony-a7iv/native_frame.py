"""Separate identified observer records from an original binary frame export.

The original decoder still validates the full decoded container and checksum.
Keep the unmodified serial log; never repair or synthesize encoded frame bytes.
"""
import re

OBSERVER_RECORD=re.compile(
 rb'OBS (?:DATE_CHECK_(?:ENTER|RETURN)|BOOT_LOG_AP_STATE_CONSUMED|'
 rb'BOOT_LOG_IMAGING_REQUEST|BOOT_LOG_MEDIA_[A-Z_]+|BOOT_LOG_BACKGROUND_[A-Z_]+|BOOT_LOG_FATAL_[A-Z_]+|BOOT_LOG_DIAGNOSTIC_(?:RETAINED|ROTATED)) [^\n]*\n'
)
KERNEL_EXPORT_NOISE=re.compile(rb'(?:<4>)?\[\s*\d+\.\d+\] \[K\]\*\*UIPC ERROR\*\* osal_snd_msg: No snd_msg registered\. Skip snd to 0x(?:86f|8fc)\n')

def clean_native_export(data):
 clean,count=OBSERVER_RECORD.subn(b'',data.replace(b'\r\n',b'\n'))
 clean,kernel_count=KERNEL_EXPORT_NOISE.subn(b'',clean)
 return clean,count+kernel_count
