/* Read-only integrity and bounded FAT32 directory audit of the isolated card. */
extern int printf(const char *,...),open64(const char *,int,...),close(int);
extern long read(int,void *,unsigned long),pread64(int,void *,unsigned long,long);
extern int SHA256_Init(void *),SHA256_Update(void *,const void *,unsigned long),SHA256_Final(unsigned char *,void *);
extern int __libc_start_main(int (*)(int,char **),int,char **,void *,void *,void *,void *);
__asm__(".global _start\n.type _start,%function\n_start:\nmov x0,sp\nbl entry\nbrk #0\n");
static unsigned char buffer[4096];
static unsigned int u16(const unsigned char *b){return b[0]|b[1]<<8;}
static unsigned int u32(const unsigned char *b){return u16(b)|u16(b+2)<<16;}
static unsigned long partition,fat,data_start,cluster_bytes,max_cluster;
static unsigned int files,directories;
static int at(int fd,unsigned long off,void *out,unsigned long n){
 if(off>67108864 || n>67108864-off)return -1;
 return pread64(fd,out,n,(long)off)==(long)n?0:-1;
}
static int directory(int fd,unsigned int cluster,const char *parent,unsigned int depth){
 unsigned char block[4096],next[4];unsigned int chain=0;
 if(depth>4)return -1;
 while(cluster>=2 && cluster<0xffffff8){
  if(cluster>max_cluster || ++chain>64 || at(fd,data_start+(cluster-2)*cluster_bytes,block,cluster_bytes))return -1;
  for(unsigned int i=0;i<cluster_bytes;i+=32){
   unsigned char *p=block+i;
   if(!p[0])return 0;
   if(p[0]==0xe5 || p[0]=='.' || p[11]==15 || (p[11]&8))continue;
   char path[256];unsigned int pos=0;
   while(parent[pos] && pos<200){path[pos]=parent[pos];++pos;}
   path[pos++]='/';
   for(unsigned int j=0;j<8 && p[j]!=' ';++j)path[pos++]=(char)p[j];
   if(p[8]!=' '){path[pos++]='.';for(unsigned int j=8;j<11 && p[j]!=' ';++j)path[pos++]=(char)p[j];}
   path[pos]=0;
   unsigned int child=(u16(p+20)<<16)|u16(p+26),size=u32(p+28);
   if(p[11]&16){
    ++directories;printf("CARD_AUDIT_DIR path=%s cluster=%u\n",path,child);
    if(directory(fd,child,path,depth+1))return -1;
   }else{
    unsigned char magic[4]={0};++files;
    if(size && child>=2 && child<=max_cluster && at(fd,data_start+(child-2)*cluster_bytes,magic,size<4?size:4))return -1;
    printf("CARD_AUDIT_FILE path=%s size=%u magic=%02x%02x%02x%02x\n",path,size,magic[0],magic[1],magic[2],magic[3]);
   }
   if(files+directories>1024)return -1;
  }
  if(at(fd,fat+cluster*4,next,4))return -1;
  cluster=u32(next)&0xfffffff;
 }
 return 0;
}
static int run(int argc,char **argv){
 (void)argv;if(argc!=1)return 2;
 int fd=open64("/image_mmca",0);if(fd<0)return 3;
 unsigned long ctx[64]={0};unsigned char digest[32];unsigned long total=0;long n;
 if(!SHA256_Init(ctx))return 4;
 while((n=read(fd,buffer,sizeof buffer))>0){
  total+=(unsigned long)n;if(total>67108864 || !SHA256_Update(ctx,buffer,(unsigned long)n))return 5;
 }
 if(n<0 || total!=67108864 || !SHA256_Final(digest,ctx))return 6;
 printf("CARD_AUDIT_SHA256 bytes=%lu digest=",total);
 for(unsigned int i=0;i<32;++i)printf("%02x",digest[i]);printf("\n");
 if(at(fd,0,buffer,512) || u16(buffer+510)!=0xaa55 || buffer[450]!=12)return 7;
 partition=(unsigned long)u32(buffer+454)*512;
 if(at(fd,partition,buffer,512) || u16(buffer+11)!=512 || !buffer[13] || buffer[13]>8 || u16(buffer+510)!=0xaa55)return 8;
 cluster_bytes=buffer[13]*512;fat=partition+(unsigned long)u16(buffer+14)*512;
 data_start=fat+(unsigned long)buffer[16]*u32(buffer+36)*512;
 max_cluster=(67108864-data_start)/cluster_bytes+1;
 int result=directory(fd,u32(buffer+44),"",0);close(fd);
 printf("CARD_AUDIT_DONE result=%d files=%u directories=%u readonly=1\n",result,files,directories);
 return result?9:0;
}
__attribute__((noreturn)) void entry(unsigned long *s){__libc_start_main(run,(int)s[0],(char **)(s+1),0,0,0,s);__builtin_trap();}
