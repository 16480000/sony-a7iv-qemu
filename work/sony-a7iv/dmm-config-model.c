/* Configuration queries only; no allocation or physical memory promise.
 * Original dmm.ko GetUnitSize9e90 resolves first extent, GetExtentSizeb858
 * returns its size field. Reply builder5b60 uses8018,status+2,size+16. */
static const unsigned int a7m4_dmm_unit_sizes[][2]={
/* ORIGINAL_DMM_UNITS */
};
static int a7m4_dmm_size_query(unsigned int id,void *request,int *handled) {
    *handled=0;
    if(id!=0x9061003c || !request || !real_msg_size || real_msg_size(request)!=40)return 0;
    unsigned char *in=request;unsigned short *head=request;
    if(head[0]!=0x18)return 0;
    for(unsigned int i=2;i<40;++i)if((i<4 || i>=8) && in[i])return 0;
    unsigned int key=((unsigned int *)request)[1],size=0,found=0,source=real_get_source(request);
    if(!source)return 0;
    for(unsigned int i=0;i<sizeof a7m4_dmm_unit_sizes/sizeof a7m4_dmm_unit_sizes[0];++i)
        if(a7m4_dmm_unit_sizes[i][0]==key){found=1;size=a7m4_dmm_unit_sizes[i][1];break;}
    if(!found)return 0;
    void *reply=0;int result=real_allocate_msg(source,&reply,40,1);
    *handled=1;if(result)return result;
    unsigned char *out=reply;for(unsigned int i=0;i<40;++i)out[i]=0;
    ((unsigned short *)reply)[0]=0x8018;((unsigned short *)reply)[3]=head[10];
    ((unsigned int *)reply)[4]=size;
    real_set_source(reply,id);result=real_send_msg(source,reply);
    if(result){real_free_msg(source,reply);return result;}
    char text[180];snprintf(text,sizeof text,"unit_type=%#x original_config_unit_size=%#x; metadata query only, no allocation",key,size);
    record("BOOT_LOG_DMM_UNIT_SIZE ",text);real_free_msg(id,request);return 0;
}
