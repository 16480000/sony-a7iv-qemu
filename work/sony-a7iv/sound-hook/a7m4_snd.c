/* Experimental SOUND feedback capture for the A7M4 emulator.
 *
 * The AP kernel sends public UIPC messages whose low 16 bits identify the
 * 0x8fc sound endpoint (observed full id 0x92a208fc). The original camera
 * routes these to pcie-if.ko, which forwards the payload to the CP. The CP is
 * not executed in this emulator, so this hook installs a public callback,
 * copies the payload synchronously while it is still valid, and lets a
 * kthread print it. It does not decode or play audio itself. */
#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/init.h>
#include <linux/kallsyms.h>
#include <linux/kthread.h>
#include <linux/delay.h>
#include <linux/spinlock.h>
#include <linux/string.h>
#define SND_ID 0x92a208fcUL

typedef int (*reg_public_fn)(void *);
typedef int (*unreg_public_fn)(void);

#define MAX_DATA 128
#define RING 64

struct snd_rec {
    unsigned long id;
    unsigned int size;
    unsigned char data[MAX_DATA];
};

static void *public_table[4];
static reg_public_fn reg_public;
static unreg_public_fn unreg_public;
static struct snd_rec ring[RING];
static unsigned int head, tail;
static DEFINE_SPINLOCK(ring_lock);
static struct task_struct *worker_task;
static unsigned int logged;

static long public_cb(unsigned long a, unsigned long b, unsigned long c, unsigned long d)
{
    struct snd_rec rec;
    unsigned long flags;

    if (a != SND_ID || !b || b < 0xffff000000000000UL)
        return 0;
    rec.id = a;
    rec.size = 64;
    memcpy(rec.data, (const void *)b, rec.size);
    spin_lock_irqsave(&ring_lock, flags);
    if (head - tail < RING) {
        ring[head & (RING - 1)] = rec;
        head++;
    }
    spin_unlock_irqrestore(&ring_lock, flags);
    return 0;
}

static int dump_worker(void *unused)
{
    struct snd_rec batch;
    unsigned long flags;

    while (!kthread_should_stop()) {
        unsigned int have = 0;
        msleep(500);
        spin_lock_irqsave(&ring_lock, flags);
        if (tail < head) {
            batch = ring[tail & (RING - 1)];
            tail++;
            have = 1;
        }
        spin_unlock_irqrestore(&ring_lock, flags);
        if (have && logged < 200) {
            logged++;
            pr_info("A7M4_SND7 n=%u id=%#lx size=%u data=%*phN\n",
                    logged, batch.id, batch.size, batch.size, batch.data);
        }
    }
    return 0;
}

static int __init a7m4_snd_init(void)
{
    reg_public = (reg_public_fn)kallsyms_lookup_name("osal_reg_public");
    unreg_public = (unreg_public_fn)kallsyms_lookup_name("osal_unreg_public");
    pr_info("A7M4_SND7 init reg=%px unreg=%px\n", reg_public, unreg_public);
    if (!reg_public)
        return -ENOENT;
    public_table[0] = (void *)public_cb;
    pr_info("A7M4_SND7 reg_rc=%d table=%px\n",
            reg_public(public_table), public_table);
    worker_task = kthread_run(dump_worker, 0, "a7m4_snd7");
    if (IS_ERR(worker_task)) {
        pr_err("A7M4_SND7 kthread failed\n");
        return PTR_ERR(worker_task);
    }
    return 0;
}

static void __exit a7m4_snd_exit(void)
{
    if (worker_task)
        kthread_stop(worker_task);
    if (unreg_public)
        unreg_public();
    pr_info("A7M4_SND7 exit logged=%u\n", logged);
}

module_init(a7m4_snd_init);
module_exit(a7m4_snd_exit);
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("A7M4 public sound message capture");
