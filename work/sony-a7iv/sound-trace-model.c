/* Temporary sound-path probe: log appFw->OSAL sound sends that reach the
 * preload interposer. Kernel-side drops (e.g. the UIPC "No snd_msg" logs)
 * will not appear here; those need a kernel endpoint model. */
static int a7m4_snd_trace_id(unsigned int id) {
    /* Full BB endpoint ids are 0x9284xxxx; older probes compared the whole
       value against 16-bit suffixes and therefore never matched. */
    switch(id & 0xffff) {
    case 0x747: case 0x8fc: case 0x86f: case 0x83f: case 0x8f7: case 0x964:
    case 0x85c: case 0x738: case 0x7ec: case 0x5c5: case 0x14d:
        return 1;
    default:
        return 0;
    }
}
static void a7m4_snd_trace(unsigned int id, void *message) {
    if(!message || !real_msg_size || !real_get_source || !a7m4_snd_trace_id(id)) return;
    unsigned int size=real_msg_size(message);
    if(size<1 || size>512) return;
    /* Never let a small boot-time quota hide later adf_sys_request traffic. */
    static unsigned int seen;
    unsigned int n=__atomic_add_fetch(&seen,1,__ATOMIC_RELAXED);
    if(n>4000) return;
    unsigned int shown=size<96?size:96;
    char text[420];
    unsigned long caller=(unsigned long)__builtin_return_address(0);
    unsigned long offset=appfw_base && caller>=appfw_base?caller-appfw_base:caller;
    int used=snprintf(text,sizeof text,"dest=%#x size=%u src=%#x caller_off=%#lx bytes=",
                      id,size,real_get_source(message),offset);
    for(unsigned int i=0;i<shown && used+2<(int)sizeof text;++i)
        used+=snprintf(text+used,sizeof text-used,"%02x",((unsigned char *)message)[i]);
    record("A7M4_SND_TRACE ",text);
}
