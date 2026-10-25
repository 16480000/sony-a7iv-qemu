/* Guest-side virtual photo capture for the isolated virtual-sensor profile.
 * Overwrites the pre-indexed DSC00001.JPG data run in /image_mmca with the
 * next padded virtual-sensor JPEG, refreshes the virtual photo display layer,
 * and marks a display reload. The directory entry size/name is unchanged.
 * This is a virtual-sensor demo, not an original ISP/JPEG capture path. */
typedef unsigned long size_t;
extern int printf(const char *, ...);
extern int open(const char *, int, ...), close(int);
extern long read(int, void *, size_t), write(int, const void *, size_t);
extern long pread(int, void *, size_t, long), pwrite(int, const void *, size_t, long);
extern int __libc_start_main(int (*)(int, char **), int, char **,
                            void (*)(void), void (*)(void), void (*)(void), void *);
extern void _exit(int) __attribute__((noreturn));
__asm__(".global _start\n.type _start, %function\n_start:\nmov x0, sp\nbl entry\nbrk #0\n");

static int read_all(int fd, void *buffer, size_t length) {
    unsigned char *p = buffer;
    while (length) {
        long got = read(fd, p, length);
        if (got <= 0) return -1;
        p += got;
        length -= (size_t)got;
    }
    return 0;
}
static int write_all_fd(int fd, const void *buffer, size_t length) {
    const unsigned char *p = buffer;
    while (length) {
        long put = write(fd, p, length);
        if (put <= 0) return -1;
        p += put;
        length -= (size_t)put;
    }
    return 0;
}
static int copy_file(const char *source, const char *target) {
    int in = open(source, 0), out = -1;
    static unsigned char buffer[65536];
    int ok = in >= 0 && (out = open(target, 0x241, 0644)) >= 0;
    while (ok) {
        long got = read(in, buffer, sizeof buffer);
        if (got == 0) break;
        if (got < 0 || write_all_fd(out, buffer, (size_t)got)) { ok = 0; break; }
    }
    if (in >= 0 && close(in)) ok = 0;
    if (out >= 0 && close(out)) ok = 0;
    return ok ? 0 : -1;
}
static int run(int argc, char **argv) {
    const char *source_path = argc > 1 ? argv[1] : "/simulation/virtual-photo-next.jpg";
    int web_capture = argc > 1;
    unsigned char layout[12];
    int layout_fd = open("/simulation/virtual-photo-layout", 0);
    if (layout_fd < 0 || read_all(layout_fd, layout, sizeof layout)) {
        printf("VIRTUAL_PHOTO_CAPTURE error=layout\n");
        return 2;
    }
    close(layout_fd);
    unsigned long long offset = 0;
    for (unsigned int i = 0; i < 8; ++i) offset |= (unsigned long long)layout[i] << (8 * i);
    unsigned int size = 0;
    for (unsigned int i = 0; i < 4; ++i) size |= (unsigned int)layout[8 + i] << (8 * i);
    if (size == 0 || size > 65536) {
        printf("VIRTUAL_PHOTO_CAPTURE error=size size=%u\n", size);
        return 2;
    }
    static unsigned char jpeg[65536], verify[65536];
    int source = open(source_path, 0);
    if (source < 0 || read_all(source, jpeg, size)) {
        printf("VIRTUAL_PHOTO_CAPTURE error=source path=%s\n", source_path);
        return 3;
    }
    close(source);
    int card = open("/image_mmca", 2);
    int ok = card >= 0 && pwrite(card, jpeg, size, (long)offset) == (long)size;
    if (ok) {
        ok = pread(card, verify, size, (long)offset) == (long)size;
        for (unsigned int i = 0; ok && i < size; ++i) if (verify[i] != jpeg[i]) ok = 0;
    }
    if (card >= 0 && close(card)) ok = 0;
    if (!ok) {
        printf("VIRTUAL_PHOTO_CAPTURE error=card offset=%llu size=%u\n", offset, size);
        return 4;
    }
    if (web_capture) {
        printf("VIRTUAL_PHOTO_CAPTURE source=web offset=%llu size=%u result=0; browser JPEG written to virtual card\n", offset, size);
        return 0;
    }
    if (copy_file("/simulation/virtual-photo-next.rgb4444", "/simulation/virtual-photo.rgb4444")) {
        printf("VIRTUAL_PHOTO_CAPTURE error=display\n");
        return 5;
    }
    int marker = open("/tmp/a7m4-photo-refresh", 0x241, 0600);
    if (marker >= 0) close(marker);
    printf("VIRTUAL_PHOTO_CAPTURE offset=%llu size=%u result=0; virtual JPEG overwritten and display layer refreshed\n", offset, size);
    return 0;
}
__attribute__((noreturn)) void entry(unsigned long *stack) {
    __libc_start_main(run, (int)stack[0], (char **)(stack + 1), 0, 0, 0, stack);
    _exit(127);
}
