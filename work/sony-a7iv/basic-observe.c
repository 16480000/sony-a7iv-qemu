/* Initial A7M4 port: scheduling adaptation and loader evidence only.
 * No offsets from the A7C2 application are installed here.
 * SPDX-License-Identifier: GPL-2.0-or-later
 */
typedef unsigned long size_t;
typedef unsigned long pthread_t;
extern void *dlvsym(void *, const char *, const char *);
extern int open(const char *, int, ...);
extern long write(int, const void *, size_t);
extern int close(int);
extern int snprintf(char *, size_t, const char *, ...);
static void *(*lookup)(void *,const char *);
static void *(*load)(const char *,int);
static int (*attr_policy)(void *,int);
static int (*attr_param)(void *,const void *);
static int (*thread_param)(pthread_t,int,const void *);
static int (*scheduler)(int,int,const void *);
static void *(*application_init)(void *);
static int same(const char *a,const char *b) { while(*a && *a==*b) {a++;b++;} return *a==*b; }
static void record(const char *tag,const char *name,void *p) {
    char text[384];
    int count=snprintf(text,sizeof text,"A7M4_OBS %s %s %p\n",tag,name?name:"(null)",p);
    if(count<0 || count>=(int)sizeof text) return;
    int fd=open("/tmp/loader.log",0x441,0644);
    if(fd>=0) {write(fd,text,count);close(fd);}
    if(same(tag,"APP_INIT_ENTER") || same(tag,"APP_INIT_RETURN") || same(tag,"FAILED")) {
        fd=open("/dev/console",1); if(fd>=0) {write(fd,text,count);close(fd);}
    }
}
__attribute__((constructor)) static void initialize(void) {
    lookup=dlvsym((void *)-1,"dlsym","GLIBC_2.17");
    load=lookup((void *)-1,"dlopen");
    attr_policy=lookup((void *)-1,"pthread_attr_setschedpolicy");
    attr_param=lookup((void *)-1,"pthread_attr_setschedparam");
    thread_param=lookup((void *)-1,"pthread_setschedparam");
    scheduler=lookup((void *)-1,"sched_setscheduler");
}
static void *observe_init(void *argument) {
    record("APP_INIT_ENTER","Application_System_Init",application_init);
    void *result=application_init(argument);
    record("APP_INIT_RETURN","Application_System_Init",result);
    return result;
}
void *dlopen(const char *name,int flags) {
    if(!load) initialize();
    void *result=load(name,flags & ~8);
    record(result?"LOADED":"FAILED",name,result);
    return result;
}
void *dlsym(void *handle,const char *name) {
    if(!lookup) initialize();
    void *result=lookup(handle,name);
    record(result?"RESOLVED":"NO_SYMBOL",name,result);
    if(result && same(name,"Application_System_Init")) {application_init=result;return observe_init;}
    return result;
}
int pthread_attr_setschedpolicy(void *a,int p) {if(!attr_policy)initialize();return attr_policy(a,0);}
int pthread_attr_setschedparam(void *a,const void *p) {if(!attr_param)initialize();int zero=0;return attr_param(a,&zero);}
int pthread_setschedparam(pthread_t t,int p,const void *s) {if(!thread_param)initialize();int zero=0;return thread_param(t,0,&zero);}
int sched_setscheduler(int t,int p,const void *s) {if(!scheduler)initialize();int zero=0;return scheduler(t,0,&zero);}
