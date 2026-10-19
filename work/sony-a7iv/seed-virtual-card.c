/* Explicit virtual slot-2 insertion for the original file-backed media driver.
 * mcmn_drv.ko .text1000..1238 accepts a >=7-byte port-state notification on
 * 8028017c. libInfraMediaDetect.so ParseInternalMessage 0x10a9c requires
 * byte0=2 (the kernel forwards this header unchanged). Byte3 bits0..2 mark
 * valid ports; bytes4..6 bit0 is hold, bit1 insertion, bits4..7 removal count.
 * This notification only reports virtual media; it does not produce images. */
extern int printf(const char *,...);
extern int strcmp(const char *,const char *);
extern int osal_valloc_msg_wait(unsigned int,void **,unsigned int,int);
extern int osal_set_msg_src(void *,unsigned int),osal_snd_msg(unsigned int,void *),osal_free_msg(unsigned int,void *);
extern int __libc_start_main(int (*)(int,char **),int,char **,void *,void *,void *,void *);
__asm__(".global _start\n.type _start,%function\n_start:\nmov x0,sp\nbl entry\nbrk #0\n");
static int run(int argc,char **argv){
 int inserted=1;
 if(argc==2 && !strcmp(argv[1],"--remove"))inserted=0;
 else if(argc!=1)return 2;
 void *message=0;unsigned int queue=0x8028017c;
 int rc=osal_valloc_msg_wait(queue,&message,7,1);
 if(rc||!message){printf("VIRTUAL_CARD_ALLOC=%d\n",rc);return 3;}
 unsigned char *b=message;for(unsigned int i=0;i<7;++i)b[i]=0;
 /* Native slot2 has mask2 and /nondev/rm2 -> /dev/mmca. Slot1 mask5
  * requires the hybrid PCI/SxS backend, absent from the file driver. */
 b[0]=2;b[3]=7;b[5]=inserted?2:0;osal_set_msg_src(message,0x92840747);
 rc=osal_snd_msg(queue,message);if(rc)osal_free_msg(queue,message);
 printf("VIRTUAL_CARD_PORT_SEND result=%d slot2_inserted=%d slot1=empty port2=empty; file-backed model only\n",rc,inserted);
 return rc?4:0;
}
__attribute__((noreturn)) void entry(unsigned long *s){__libc_start_main(run,(int)s[0],(char **)(s+1),0,0,0,s);__builtin_trap();}
