/* Experimental guest-side receiver for the UIPC sound queue(s).
 * Registers the same user-facing callback ABI used by appFw:
 *   osal_reg_msg_queue_cb(qid, &handle, callback, context)
 * callback(x0=message). It only logs; it is not an audio decoder. */
typedef unsigned long size_t;
extern int printf(const char *, ...);
extern int fflush(void *);
extern int osal_reg_msg_queue_cb(unsigned int, void **, void (*)(void *), void *);
extern unsigned int osal_get_msg_src(void *);
extern unsigned int osal_msg_size(void *);
extern int __libc_start_main(int (*)(int, char **), int, char **,
                             void (*)(void), void (*)(void), void (*)(void), void *);
extern int sleep(unsigned int);
extern unsigned long strtoul(const char *, char **, int);
__asm__(".global _start\n.type _start, %function\n_start:\nmov x0, sp\nbl entry\nbrk #0\n");

static volatile unsigned int count;
static void message_cb(void *message) {
    unsigned int n = ++count;
    unsigned int size = message ? osal_msg_size(message) : 0;
    unsigned int source = message ? osal_get_msg_src(message) : 0;
    printf("SNDSINK_MSG n=%u msg=%p size=%u source=%#x bytes=", n, message, size, source);
    if (message) {
        unsigned int shown = size > 96 ? 96 : size;
        const unsigned char *p = message;
        for (unsigned int i = 0; i < shown; ++i) printf("%02x", p[i]);
    }
    printf("\n");
    fflush(0);
}

static int run(int argc, char **argv) {
    unsigned int qid = 0x8fc;
    void *handle = 0;
    if (argc > 1) qid = (unsigned int)strtoul(argv[1], 0, 0);
    printf("SNDSINK_START qid=%#x\n", qid);
    fflush(0);
    int rc = osal_reg_msg_queue_cb(qid, &handle, message_cb, 0);
    printf("SNDSINK_REG qid=%#x rc=%d handle=%p\n", qid, rc, handle);
    fflush(0);
    if (rc) return 2;
    for (;;) sleep(3600);
}
__attribute__((noreturn)) void entry(unsigned long *s) {
    __libc_start_main(run, (int)s[0], (char **)(s + 1), 0, 0, 0, s);
    __builtin_trap();
}
