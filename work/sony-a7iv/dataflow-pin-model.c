/* Included after original OSAL declarations in generated menu-observe.c.
 * CP4e2006/4e204e/4e229c/4e242a: finite in-process virtual pin graph.
 * Internal0100/8100 frames are locally delivered, not executed by the CP.
 * This models control-plane bindings only; it produces no image/audio data. */
struct a7m4_virtual_pin {
    unsigned int identity[4]; /* type,direction,number,raw routing owner */
    unsigned int state,peer,pending_source,pending_operation;
};
static struct a7m4_virtual_pin a7m4_pins[]={
/* ORIGINAL_PIN_RECORDS */
};
static unsigned long a7m4_pin_lock[6];
static int a7m4_find_pin(const unsigned int *identity) {
    for(unsigned int i=0;i<sizeof a7m4_pins/sizeof a7m4_pins[0];++i) {
        unsigned int j=0;for(;j<4 && a7m4_pins[i].identity[j]==identity[j];++j){}
        if(j==4)return (int)i;
    }
    return -1;
}
static void a7m4_pin_trace(const char *stage,const void *frame,unsigned int size) {
    const unsigned char *b=frame;char text[210],hex[100]={0};unsigned int at=0;
    for(unsigned int i=0;i<size && i<48;++i)at+=snprintf(hex+at,sizeof hex-at,"%02x",b[i]);
    snprintf(text,sizeof text,"virtual-local %s bytes=%u inner=%s; control-plane only",stage,size,hex);
    record("BOOT_LOG_PIN_HANDSHAKE ",text);
}
static int a7m4_pin_reply(unsigned int id,void *request,unsigned int source,
                         unsigned short command,const unsigned int *body) {
    void *reply=0;int result=real_allocate_msg(source,&reply,56,1);
    if(result)return result;
    unsigned char *out=reply,*in=request;
    for(unsigned int i=0;i<24;++i)out[i]=in[i];
    unsigned short *head=(unsigned short *)(out+24);unsigned int *words=(unsigned int *)out;
    ((unsigned short *)out)[5]=56;words[4]=56;
    head[0]=0x1000;head[1]=command;head[2]=32;head[3]=2;
    for(unsigned int i=0;i<6;++i)words[8+i]=body[i];
    real_set_source(reply,id);result=real_send_msg(source,reply);
    if(result){real_free_msg(source,reply);return result;}
    real_free_msg(id,request);return 0;
}
static int a7m4_pin_model(unsigned int id,void *message,int *handled) {
    *handled=0;
    if(!message || !real_msg_size)return 0;
    unsigned int owner_known=0;
    for(unsigned int i=0;i<sizeof a7m4_pins/sizeof a7m4_pins[0];++i)
        if(a7m4_pins[i].identity[3]==id)owner_known=1;
    if(!owner_known)return 0;
    unsigned int size=real_msg_size(message);
    if(size!=48 && size!=64)return 0;
    unsigned int *words=message,source=real_get_source(message);
    unsigned short *header=message,*inner=(unsigned short *)((unsigned char *)message+24);
    if(!source || words[0]!=source || words[1]!=0xa0a0a0a0 || header[4]!=1 ||
       header[5]!=size || words[3]!=24 || words[4]!=size ||
       inner[0]!=0x1000 || inner[2]!=size-24 || inner[3]!=2)return 0;
    unsigned int identity[4]={words[8],words[9],words[10],id},body[6];
    pthread_mutex_lock(a7m4_pin_lock);
    if(inner[1]==0 && size==48 && !words[11]) {
        int index=a7m4_find_pin(identity);
        if(index>=0) {
            struct a7m4_virtual_pin *pin=a7m4_pins+index;
            body[0]=identity[0];body[1]=identity[1];body[2]=identity[2];
            body[3]=pin->state;body[4]=id;body[5]=0;
            char text[180];snprintf(text,sizeof text,"owner=%#x type=%u dir=%u number=%u state=%u query_status=0; no stream",id,identity[0],identity[1],identity[2],pin->state);
            record("BOOT_LOG_PIN_GET ",text);
            *handled=1;
        }
    } else if(inner[1]==1 && size==64 && words[11]==id) {
        int own=a7m4_find_pin(words+8),peer=a7m4_find_pin(words+12);
        /* Fresh connections only. Other states remain unsupported until
           their exact original branches are needed and verified. */
        if(own>=0 && peer>=0 && own!=peer) {
            struct a7m4_virtual_pin *a=a7m4_pins+own,*b=a7m4_pins+peer;
            unsigned int ad=a->identity[1],bd=b->identity[1];
            if(a->state==1 && b->state==1 && a->identity[0]==b->identity[0] &&
               ((ad==1 && bd==2)||(ad==2 && bd==1)||(ad==3 && bd==3))) {
                unsigned int transaction[12]={0};unsigned short *th=(unsigned short *)transaction;
                th[0]=0x1000;th[1]=0x100;th[2]=40;th[3]=1;
                for(unsigned int i=0;i<4;++i){transaction[2+i]=a->identity[i];transaction[6+i]=b->identity[i];}
                a->state=2;a->peer=peer+1;a->pending_source=source;a->pending_operation=1;
                a7m4_pin_trace("SEND0100",transaction,40);
                /* Locally deliver to the declared peer, with both identities
                   and the original compatibility rule already checked. */
                b->peer=own+1;b->state=0;
                th[1]=0x8100;th[2]=48;transaction[10]=0;transaction[11]=0;
                a7m4_pin_trace("RECV8100",transaction,48);
                /* Initiator commits only after peer completion. */
                if(a->state==2 && a->pending_operation==1 && a->pending_source==source &&
                   b->state==0 && b->peer==(unsigned int)own+1 && !transaction[10]) {
                    a->state=0;a->pending_operation=0;a->pending_source=0;
                    for(unsigned int i=0;i<4;++i)body[i]=a->identity[i];
                    body[4]=0;body[5]=0;*handled=1;
                    record("BOOT_LOG_PIN_CONNECT ","virtual graph endpoints connected after local0100/8100; no sensor/ISP data");
                }
            }
        }
    }
    pthread_mutex_unlock(a7m4_pin_lock);
    if(!*handled)return 0;
    return a7m4_pin_reply(id,message,source,inner[1]==0?0x8000:0x8001,body);
}
