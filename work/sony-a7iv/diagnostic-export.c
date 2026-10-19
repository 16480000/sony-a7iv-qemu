/* Export a fixed, read-only prefix of the owned diagnostic stream. */
extern int printf(const char *,...),open64(const char *,int,...),close(int);
extern long read(int,void *,unsigned long),write(int,const void *,unsigned long),lseek64(int,long,int);
extern int SHA256_Init(void *),SHA256_Update(void *,const void *,unsigned long),SHA256_Final(unsigned char *,void *);
extern int __libc_start_main(int (*)(int,char **),int,char **,void *,void *,void *,void *);
__asm__(".global _start\n.type _start,%function\n_start:\nmov x0,sp\nbl entry\nbrk #0\n");
static const char alphabet[]="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
static unsigned char sample[524288],record[4100];
static unsigned int u32(const unsigned char *p){return p[0]|p[1]<<8|p[2]<<16|(unsigned int)p[3]<<24;}
static int run(int argc,char **argv){
 (void)argv;if(argc!=1)return 2;
 int fd=open64("/tmp/a7m4-diagnostic-events.bin",0);if(fd<0)return 3;
 long total=lseek64(fd,0,2);if(total<0 || total>67108864 || lseek64(fd,0,0))return 4;
 unsigned long ctx[64]={0};unsigned char digest[32],sample_digest[32];
 if(!SHA256_Init(ctx))return 9;
 unsigned long at=0,sampled=0,count=0,sample_count=0;
 unsigned long sample_start=total>(long)sizeof sample?(unsigned long)total-sizeof sample:0;
 while(at<(unsigned long)total){
  if(total-at<4 || read(fd,record,4)!=4)return 10;
  unsigned int size=u32(record);
  if(size<33 || size>4096 || size>(unsigned long)total-at-4 || read(fd,record+4,size)!=(long)size)return 11;
  if(record[4]!=2 || record[5] || record[6]!=0x83 || record[7] || u32(record+12)!=size-32)return 12;
  if(!SHA256_Update(ctx,record,size+4))return 13;
  if(at>=sample_start && sampled+size+4<=sizeof sample){
   for(unsigned int i=0;i<size+4;++i)sample[sampled+i]=record[i];
   sampled+=size+4;++sample_count;
  }
  at+=size+4;++count;
 }
 if(!SHA256_Final(digest,ctx))return 14;
 if(!SHA256_Init(ctx) || !SHA256_Update(ctx,sample,sampled) || !SHA256_Final(sample_digest,ctx))return 15;
 printf("DIAGNOSTIC_SNAPSHOT total=%ld records=%lu exported_records=%lu exported_bytes=%lu sha256=",total,count,sample_count,sampled);
 for(unsigned int i=0;i<32;++i)printf("%02x",digest[i]);printf(" sample_sha256=");
 for(unsigned int i=0;i<32;++i)printf("%02x",sample_digest[i]);printf("\n");
 char begin[]="\nA7M4_DIAG_BEGIN\n";if(write(1,begin,sizeof begin-1)!=sizeof begin-1)return 5;
 char output[65];long left=sampled;unsigned long cursor=0;
 while(left){
  unsigned long wanted=left<48?(unsigned long)left:48;
  const unsigned char *input=sample+cursor;
  unsigned int n=0;
  for(unsigned int i=0;i<wanted;i+=3){
   unsigned int v=input[i]<<16;
   if(i+1<wanted)v|=input[i+1]<<8;
   if(i+2<wanted)v|=input[i+2];
   output[n++]=alphabet[v>>18];output[n++]=alphabet[(v>>12)&63];
   output[n++]=i+1<wanted?alphabet[(v>>6)&63]:'=';
   output[n++]=i+2<wanted?alphabet[v&63]:'=';
  }
  output[n++]='\n';if(write(1,output,n)!=(long)n)return 7;
  left-=wanted;cursor+=wanted;
 }
 close(fd);char end[]="A7M4_DIAG_END\n";
 return write(1,end,sizeof end-1)==sizeof end-1?0:8;
}
void entry(unsigned long *s){__libc_start_main(run,(int)s[0],(char **)(s+1),0,0,0,0);}
