/* Read-only kernel-ring snapshot inside the isolated guest. */
extern int klogctl(int,char *,int);
extern long write(int,const void *,unsigned long);
extern int __libc_start_main(int (*)(int,char **),int,char **,void *,void *,void *,void *);
__asm__(".global _start\n.type _start,%function\n_start:\nmov x0,sp\nbl entry\nbrk #0\n");
static char buffer[1048576];
static int run(int argc,char **argv){
 (void)argv;if(argc!=1)return 2;
 int n=klogctl(3,buffer,sizeof buffer);if(n<0)return 3;
 return write(1,buffer,n)==n?0:4;
}
void entry(unsigned long *s){__libc_start_main(run,(int)s[0],(char **)(s+1),0,0,0,0);}
