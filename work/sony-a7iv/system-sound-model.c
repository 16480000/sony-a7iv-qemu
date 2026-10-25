/* Original CP b1830 ->2004/0311,63d00,4beb6a,4f2d2c.
 * CP b28a0 ->2004/020a,4d57b8,4d583a,4f31a8.
 * Virtual backing storage and volume configuration; no audio playback. */
#define A7M4_SOUND_PHYSICAL 0x41ea00000UL
#define A7M4_SOUND_SIZE 0x20000UL
#define A7M4_SOUND_FILE_SIZE 77504UL
static unsigned long a7m4_sound_lock[6];
static unsigned char *a7m4_sound_memory;
static unsigned char a7m4_system_volume[2];
static unsigned char a7m4_system_sounds[21][32];
static unsigned char a7m4_sound_volumes[21];
static unsigned char a7m4_sound_output_mask;
static int a7m4_sound_load(void) {
    if(a7m4_sound_memory)return 0;
    int mem=open("/dev/mem",2),file=open("/usr/share/avsystemsound/SysSound.bin",0);
    if(mem<0 || file<0){if(mem>=0)close(mem);if(file>=0)close(file);return -1;}
    unsigned char *area=mmap(0,A7M4_SOUND_SIZE,3,1,mem,A7M4_SOUND_PHYSICAL);close(mem);
    if(area==(void *)-1){close(file);return -1;}
    for(unsigned long i=0;i<A7M4_SOUND_SIZE;++i)area[i]=0;
    unsigned long offset=0;
    while(offset<A7M4_SOUND_FILE_SIZE) {
        long count=read(file,area+offset,A7M4_SOUND_FILE_SIZE-offset);
        if(count<=0){close(file);munmap(area,A7M4_SOUND_SIZE);return -1;}
        offset+=count;
    }
    unsigned char extra;long end=read(file,&extra,1);close(file);
    if(end!=0){munmap(area,A7M4_SOUND_SIZE);return -1;}
    a7m4_sound_memory=area;
    record("BOOT_LOG_SYSTEM_SOUND ","original SysSound.bin77504 bytes loaded at reservedPA41ea00000; no playback");
    return 0;
}
static int a7m4_audio_config(unsigned int id,void *message,int *handled) {
    *handled=0;
    unsigned short *head=message;
    unsigned char *request=message;
    unsigned int size=real_msg_size(message),source=real_get_source(message),reply_size=0;
    if(id==0x92840747 && message && size>=8 && head[0]==0x200d) {
        static unsigned int observed;
        unsigned int n=__atomic_add_fetch(&observed,1,__ATOMIC_RELAXED);
        if(n<=4000) {
            unsigned int shown=size<40?size:40;
            char text[220];
            int used=snprintf(text,sizeof text,"n=%u cmd=%#x size=%u flags=%#x src=%#x bytes=",
                              n,head[1],size,head[3],source);
            for(unsigned int i=0;i<shown && used+2<(int)sizeof text;++i)
                used+=snprintf(text+used,sizeof text-used,"%02x",request[i]);
            record("A7M4_BB_REQ ",text);
        }
    }
    if(id!=0x92840747 || !source || head[0]!=0x200d || head[2]!=size || head[3]!=0x8001)return 0;
    if(head[1]==0x32e && size==10 && request[8]>=1 && request[8]<=16 && !request[9])reply_size=12;
    if(head[1]==0x33d && size==8 && getenv("QEMU_SYSTEM_SOUND_BUFFER"))reply_size=24;
    if(head[1]==0x327 && size==40 && getenv("QEMU_SYSTEM_SOUND_BUFFER") &&
       request[20]<21 && request[21]<=15 && request[22]<=1 && request[23]<=1 && request[24]<=1 &&
       !request[25] && !request[26] && !request[27] && !((unsigned int *)message)[9]) {
        unsigned long address=*(unsigned long *)(request+8);
        unsigned int length=((unsigned int *)message)[4];
        if(!request[22] || (a7m4_sound_memory && length && address>=A7M4_SOUND_PHYSICAL &&
           address-A7M4_SOUND_PHYSICAL<A7M4_SOUND_FILE_SIZE &&
           length<=A7M4_SOUND_FILE_SIZE-(address-A7M4_SOUND_PHYSICAL)))reply_size=12;
    }
    if(head[1]==0x32a && size==10 && request[8]<=16 && request[9]<21 &&
       a7m4_system_sounds[request[9]][14]==1)reply_size=12;
    if(head[1]==0x328 && size==10 && request[8]<=7 && !request[9])reply_size=12;
    /* AP adf_sys_request: CP SendADF_SysRequest reads kind at+8, option at+9,
       sound id at+0xa and a u32 at+0xc, then emits2004/0203/16/1. Retain the
       real request and acknowledge it; decoding/playback is the host's job. */
    if(head[1]==0x329 && size>=16 && size<=40 && getenv("QEMU_SYSTEM_SOUND_BUFFER") &&
       request[8]<=2 && request[9]<=1)reply_size=12;
    if(!reply_size)return 0;
    pthread_mutex_lock(a7m4_sound_lock);
    if(reply_size==24 && a7m4_sound_load()) {
        pthread_mutex_unlock(a7m4_sound_lock);
        record("BOOT_LOG_SYSTEM_SOUND_ERROR ","reserved memory or original sound resource unavailable; no success reply");
        *handled=1;return -1024;
    }
    void *reply=0;int result=real_allocate_msg(source,&reply,reply_size,1);
    if(result){pthread_mutex_unlock(a7m4_sound_lock);*handled=1;return result;}
    unsigned char *bytes=reply;for(unsigned int i=0;i<reply_size;++i)bytes[i]=0;
    unsigned short *out=reply;out[0]=0x200d;out[1]=head[1]+0x1000;out[2]=reply_size;out[3]=0x8001;
    if(reply_size==24) {
        /* BB133d has result+8, reserved+12, address+16. */
        *(unsigned long *)(bytes+16)=A7M4_SOUND_PHYSICAL;
    } else if(head[1]==0x327) {
        /* BBb0a70 forwards descriptor to2004/0201;4f2aee builds1327.
           Retain only descriptors backed by the original virtual bank. */
        for(unsigned int i=0;i<32;++i)a7m4_system_sounds[request[20]][i]=request[8+i];
        int fd=open("/tmp/a7m4-system-sounds.bin",1|64|512,0600);
        if(fd>=0){write(fd,a7m4_system_sounds,sizeof a7m4_system_sounds);close(fd);}
        char text[180];snprintf(text,sizeof text,"id=%u enabled=%u address=%#lx bytes=%u original-bank descriptor retained; no playback",request[20],request[22],*(unsigned long *)(request+8),((unsigned int *)message)[4]);
        record("BOOT_LOG_SOUND_DESCRIPTOR ",text);
    } else if(head[1]==0x328) {
        /* CPb0d48 stores request[8]&7 in2004/0202;4f2b40->1328.
           This retains routing intent without a physical audio device. */
        a7m4_sound_output_mask=request[8]&7;
        int fd=open("/tmp/a7m4-sound-output-mask.bin",1|64|512,0600);
        if(fd>=0){write(fd,&a7m4_sound_output_mask,1);close(fd);}
        record("BOOT_LOG_SOUND_OUTPUT ","three-bit system-sound output mask retained; no playback device");
    } else if(head[1]==0x32a) {
        /* CPb0fc4 forwards per-sound volume/id to2004/0204;
           4f2be4 returns132a/status. No playback is requested. */
        a7m4_sound_volumes[request[9]]=request[8];
        int fd=open("/tmp/a7m4-sound-volumes.bin",1|64|512,0600);
        if(fd>=0){write(fd,a7m4_sound_volumes,sizeof a7m4_sound_volumes);close(fd);}
        char text[100];snprintf(text,sizeof text,"sound_id=%u volume=%u retained; no playback",request[9],request[8]);
        record("BOOT_LOG_SOUND_VOLUME ",text);
    } else if(head[1]==0x329) {
        /* The AP app's real adf_sys_request. Keep the exact fields and bind
           them to the descriptor bank for host-side firmware audio output. */
        unsigned int kind=request[8],option=request[9],sound_id=request[10];
        unsigned int param=0;memcpy(&param,request+12,4);
        unsigned long address=0;unsigned int length=0,enabled=0,volume=0;
        if(sound_id<21){
            memcpy(&address,a7m4_system_sounds[sound_id],8);
            memcpy(&length,a7m4_system_sounds[sound_id]+8,4);
            enabled=a7m4_system_sounds[sound_id][14];
            volume=a7m4_sound_volumes[sound_id];
        }
        char text[260];
        snprintf(text,sizeof text,
                 "kind=%u option=%u sound_id=%u param=%#x addr=%#lx len=%u enabled=%u volume=%u; original adf_sys_request",
                 kind,option,sound_id,param,address,length,enabled,volume);
        record("A7M4_SOUND_PLAY ",text);
        int fd=open("/tmp/a7m4-sound-play.bin",1|64|512,0600);
        if(fd>=0){
            unsigned char event[64];unsigned int stored=size<56?size:56;
            event[0]=stored;event[1]=0;event[2]=0;event[3]=0;
            memcpy(event+4,message,stored);
            write(fd,event,4+stored);close(fd);
        }
    } else {
        /* Native1..16 maps to stored0..15 (CP63d62..63d90). */
        a7m4_system_volume[0]=request[8];a7m4_system_volume[1]=request[8]-1;
        int fd=open("/tmp/a7m4-system-volume.bin",1|64|512,0600);
        if(fd>=0){write(fd,a7m4_system_volume,2);close(fd);}
        record("BOOT_LOG_SYSTEM_VOLUME ","native system-volume setting retained; no playback");
    }
    pthread_mutex_unlock(a7m4_sound_lock);
    real_set_source(reply,id);result=real_send_msg(source,reply);
    if(result)real_free_msg(source,reply);else real_free_msg(id,message);
    *handled=1;return result;
}
