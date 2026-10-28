/*
 * cat_anim_x64.efi - animation driver for the rEFInd "night meadow cat" theme.
 *
 * rEFInd has no animation support of its own, but it loads every *.efi in drivers_x64 before it draws the
 * menu and the firmware keeps boot-services timers running while rEFInd waits for a key.  This boot-service
 * driver stays resident and, from a 50 ms periodic timer, paints a few things straight into the GOP
 * framebuffer (plain memory writes, so it never re-enters GOP->Blt while rEFInd is in the middle of one):
 *
 *   - the selected cat tile: eye blinks and the bird rocking, as pre-composited patches from anim.bin
 *   - fireflies and twinkling stars, only on parts of the screen rEFInd never draws on, with save-under
 *
 * It is deliberately paranoid, because it runs inside the firmware:
 *   - it only draws while a handful of probe pixels prove that the screen is exactly our theme's menu
 *     (so after rEFInd clears the screen to launch a loader, it silently stops and never restores anything)
 *   - NVRAM guard counter "CatAnimGuard": armed first thing, cleared once the menu has been animating for 2 s
 *     or at ExitBootServices; two unconfirmed starts in a row disable the driver until the variable is cleared
 *   - no floating point / SSE, no libc, everything it needs is loaded up front
 *   - at ExitBootServices it flags itself dead and never touches memory again
 * If anything is missing (data file, GOP, wrong resolution) it quietly does nothing and the static theme stays.
 */
#include <stdint.h>
#include <stddef.h>

typedef uint8_t  UINT8;  typedef uint16_t UINT16; typedef uint32_t UINT32; typedef uint64_t UINT64; typedef int64_t INT64;
typedef UINT64   UINTN;  typedef UINTN EFI_STATUS; typedef void *EFI_HANDLE, *EFI_EVENT;
typedef UINT16   CHAR16;
#define EFIAPI                         /* the PE/COFF target already uses the Microsoft x64 ABI */
#define EFI_SUCCESS 0ULL
#define EFI_ERROR(s) (((INT64)(s)) < 0)
typedef struct { UINT32 a; UINT16 b, c; UINT8 d[8]; } EFI_GUID;
typedef struct { UINT64 Signature; UINT32 Revision, HeaderSize, CRC32, Reserved; } EFI_TABLE_HEADER;

typedef struct EFI_BOOT_SERVICES {
    EFI_TABLE_HEADER Hdr;
    void *RaiseTPL, *RestoreTPL, *AllocatePages, *FreePages, *GetMemoryMap;
    EFI_STATUS (EFIAPI *AllocatePool)(UINT32 Type, UINTN Size, void **Buf);
    EFI_STATUS (EFIAPI *FreePool)(void *Buf);
    EFI_STATUS (EFIAPI *CreateEvent)(UINT32 Type, UINTN Tpl, void (EFIAPI *Notify)(EFI_EVENT, void *), void *Ctx, EFI_EVENT *Ev);
    EFI_STATUS (EFIAPI *SetTimer)(EFI_EVENT Ev, UINT32 Type, UINT64 Time);
    void *WaitForEvent, *SignalEvent;
    EFI_STATUS (EFIAPI *CloseEvent)(EFI_EVENT Ev);
    void *CheckEvent, *InstallProtocolInterface, *ReinstallProtocolInterface, *UninstallProtocolInterface;
    EFI_STATUS (EFIAPI *HandleProtocol)(EFI_HANDLE H, EFI_GUID *Proto, void **Iface);
    void *Reserved, *RegisterProtocolNotify, *LocateHandle, *LocateDevicePath, *InstallConfigurationTable;
    void *LoadImage, *StartImage, *Exit, *UnloadImage, *ExitBootServices, *GetNextMonotonicCount, *Stall, *SetWatchdogTimer;
    void *ConnectController, *DisconnectController, *OpenProtocol, *CloseProtocol, *OpenProtocolInformation;
    void *ProtocolsPerHandle, *LocateHandleBuffer;
    EFI_STATUS (EFIAPI *LocateProtocol)(EFI_GUID *Proto, void *Reg, void **Iface);
    void *InstallMultipleProtocolInterfaces, *UninstallMultipleProtocolInterfaces, *CalculateCrc32, *CopyMem, *SetMem, *CreateEventEx;
} EFI_BOOT_SERVICES;

typedef struct EFI_RUNTIME_SERVICES {
    EFI_TABLE_HEADER Hdr;
    void *GetTime, *SetTime, *GetWakeupTime, *SetWakeupTime, *SetVirtualAddressMap, *ConvertPointer;
    EFI_STATUS (EFIAPI *GetVariable)(CHAR16 *Name, EFI_GUID *Guid, UINT32 *Attr, UINTN *Size, void *Data);
    void *GetNextVariableName;
    EFI_STATUS (EFIAPI *SetVariable)(CHAR16 *Name, EFI_GUID *Guid, UINT32 Attr, UINTN Size, void *Data);
} EFI_RUNTIME_SERVICES;

typedef struct EFI_SYSTEM_TABLE {
    EFI_TABLE_HEADER Hdr; CHAR16 *FirmwareVendor; UINT32 FirmwareRevision;
    EFI_HANDLE ConsoleInHandle; void *ConIn; EFI_HANDLE ConsoleOutHandle; void *ConOut; EFI_HANDLE StdErrHandle; void *StdErr;
    EFI_RUNTIME_SERVICES *RuntimeServices; EFI_BOOT_SERVICES *BootServices;
} EFI_SYSTEM_TABLE;

typedef struct { UINT32 Version, HRes, VRes, PixelFormat; UINT32 Mask[4]; UINT32 PixelsPerScanLine; } GOP_INFO;
typedef struct { UINT32 MaxMode, Mode; GOP_INFO *Info; UINTN SizeOfInfo; UINT64 FrameBufferBase; UINTN FrameBufferSize; } GOP_MODE;
typedef struct { void *QueryMode, *SetMode, *Blt; GOP_MODE *Mode; } GOP;

typedef struct { UINT32 Revision; EFI_HANDLE Parent; EFI_SYSTEM_TABLE *SysTab; EFI_HANDLE DeviceHandle; void *FilePath, *Reserved;
                 UINT32 LoadOptionsSize; void *LoadOptions; void *ImageBase; UINT64 ImageSize; UINT32 CodeType, DataType; void *Unload; } LOADED_IMAGE;
typedef struct EFI_FILE { UINT64 Revision;
    EFI_STATUS (EFIAPI *Open)(struct EFI_FILE *, struct EFI_FILE **, CHAR16 *, UINT64, UINT64);
    EFI_STATUS (EFIAPI *Close)(struct EFI_FILE *);
    void *Delete;
    EFI_STATUS (EFIAPI *Read)(struct EFI_FILE *, UINTN *, void *);
    void *Write;
    EFI_STATUS (EFIAPI *GetPosition)(struct EFI_FILE *, UINT64 *);
    EFI_STATUS (EFIAPI *SetPosition)(struct EFI_FILE *, UINT64);
} EFI_FILE;
typedef struct { UINT64 Revision; EFI_STATUS (EFIAPI *OpenVolume)(void *, EFI_FILE **); } SIMPLE_FS;

static EFI_GUID GUID_GOP    = {0x9042a9de, 0x23dc, 0x4a38, {0x96,0xfb,0x7a,0xde,0xd0,0x80,0x51,0x6a}};
static EFI_GUID GUID_LOADED = {0x5B1B31A1, 0x9562, 0x11d2, {0x8E,0x3F,0x00,0xA0,0xC9,0x69,0x72,0x3B}};
static EFI_GUID GUID_SFS    = {0x964e5b22, 0x6459, 0x11d2, {0x8e,0x39,0x00,0xa0,0xc9,0x69,0x72,0x3b}};
static EFI_GUID GUID_GUARD  = {0x7c0a3f21, 0x5d1e, 0x4b6a, {0x9a,0x42,0xc1,0x0e,0x6f,0x2d,0x93,0x58}};
static CHAR16 GUARD_NAME[]  = {'C','a','t','A','n','i','m','G','u','a','r','d',0};
static CHAR16 DATA_PATH[]   = {'\\','E','F','I','\\','r','e','f','i','n','d','\\','t','h','e','m','e','s','\\','c','a','t','\\','a','n','i','m','.','b','i','n',0};
#define VAR_ATTR 7u   /* NON_VOLATILE | BOOTSERVICE_ACCESS | RUNTIME_ACCESS */

/* ---------------------------------------------------------------- data file layout (see art/make_anim.py) */
#pragma pack(push, 1)
typedef struct { char magic[4]; UINT16 ver, sw, sh, tx, ty, nring, nbg, nstar, nfly, npatch, sway_n, blink_n, pad; UINT32 data_off; } Hdr;
typedef struct { UINT16 x, y; UINT32 unsel, sel; } Ring;
typedef struct { UINT16 x, y; UINT32 rgb; } BgProbe;
typedef struct { UINT16 x, y; UINT8 bright, phase; UINT16 period; } Star;
typedef struct { UINT16 hx, hy, ax, ay, w1, w2, w3, p1, p2, p3; UINT8 R, peak, r, g, b; } Fly;
typedef struct { UINT16 x, y, w, h; UINT32 off; } Patch;
#pragma pack(pop)

#include "sin_table.h"

#define TICK_100NS   500000ULL      /* 50 ms */
#define TPL_CALLBACK 8
#define TPL_NOTIFY   16
#define FLY_R        9
#define MAXFLY       32
#define MAXSTAR      96

static struct {
    EFI_SYSTEM_TABLE *st; EFI_BOOT_SERVICES *bs; EFI_RUNTIME_SERVICES *rt; GOP *gop;
    UINT8 *data; UINTN size; const Hdr *h;
    const Ring *ring; const BgProbe *bgp; const Star *star; const Fly *fly; const Patch *patch;
    const UINT16 *sway_ids, *blink_ids; const UINT32 *pix;    /* patch pixels, 0x00RRGGBB */
    EFI_EVENT timer, ebs;
    volatile int dead; int armed, confirmed;
    UINT32 tick, ok_ticks, rnd;
    int screen_ok, tile_sel, swap, shr, shb;
    int cur_sway, cur_blink, blink_step; UINT32 next_blink;
    UINT32 *fly_save; INT64 fly_x[MAXFLY], fly_y[MAXFLY];
    UINT32 star_save[MAXSTAR][49]; INT64 star_x[MAXSTAR], star_y[MAXSTAR];
    UINT8 lut[FLY_R * FLY_R + 1];
} g;

/* ---------------------------------------------------------------- libc bits the compiler may call */
void *memcpy(void *d, const void *s, size_t n) { UINT8 *a = d; const UINT8 *b = s; while (n--) *a++ = *b++; return d; }
void *memset(void *d, int c, size_t n) { UINT8 *a = d; while (n--) *a++ = (UINT8)c; return d; }

#ifdef CATANIM_DEBUG
static inline void outb(UINT16 p, UINT8 v) { __asm__ volatile("outb %0,%1" ::"a"(v), "Nd"(p)); }
static void dbg(const char *s) { while (*s) outb(0x3F8, (UINT8)*s++); }
static __attribute__((unused)) void dbgn(const char *l, UINT64 v) { dbg(l); char b[24]; int i = 23; b[i] = 0; if (!v) b[--i] = '0'; while (v) { b[--i] = '0' + v % 10; v /= 10; } dbg(b + i); dbg("\n"); }
#else
#define dbg(s) ((void)0)
#define dbgn(l, v) ((void)0)
#endif

static UINT32 rnd32(void) { g.rnd = g.rnd * 1664525u + 1013904223u; return g.rnd >> 8; }

/* sin of a 16-bit phase (65536 = full turn) in Q15, linearly interpolated */
static int isin(UINT32 ph) {
    ph &= 0xFFFF; UINT32 i = ph >> 8; int f = (int)(ph & 255);
    return SIN_Q15[i] + (((SIN_Q15[i + 1] - SIN_Q15[i]) * f) >> 8);
}

/* ---------------------------------------------------------------- guard */
static void guard_set(UINT8 v) { g.rt->SetVariable(GUARD_NAME, &GUID_GUARD, VAR_ATTR, 1, &v); }
static void guard_confirm(void) { if (g.armed && !g.confirmed) { g.confirmed = 1; guard_set(0); dbg("guard cleared\n"); } }

/* ---------------------------------------------------------------- framebuffer helpers */
static UINT32 *g_fb; static UINT32 g_stride;
static inline UINT32 swap_rb(UINT32 p) { return ((p & 255) << 16) | (p & 0xFF00) | ((p >> 16) & 255); }
static inline UINT32 px_in(UINT32 p)  { return g.swap ? swap_rb(p) : p; }   /* framebuffer pixel -> 0x00RRGGBB */
static inline UINT32 px_out(UINT32 p) { return g.swap ? swap_rb(p) : p; }   /* 0x00RRGGBB -> framebuffer pixel */
static inline UINT32 rd(int x, int y) { return px_in(g_fb[(UINT64)y * g_stride + x] & 0xFFFFFF); }
static inline UINT32 near_color(UINT32 a, UINT32 b) {
    int dr = (int)((a >> 16) & 255) - (int)((b >> 16) & 255), dg = (int)((a >> 8) & 255) - (int)((b >> 8) & 255), db = (int)(a & 255) - (int)(b & 255);
    return (UINT32)((dr < 0 ? -dr : dr) + (dg < 0 ? -dg : dg) + (db < 0 ? -db : db));
}

static void blit_patch(int id) {
    const Patch *p = &g.patch[id]; const UINT32 *src = g.pix + p->off / 4;
    for (int row = 0; row < p->h; row++) {
        UINT32 *dst = g_fb + (UINT64)(g.h->ty + p->y + row) * g_stride + g.h->tx + p->x;
        for (int col = 0; col < p->w; col++) dst[col] = px_out(src[col]);
        src += p->w;
    }
}

static inline UINT32 add_light(UINT32 old, int r, int gg, int b) {      /* old is a raw framebuffer pixel */
    int R = (int)((old >> g.shr) & 255) + r, G = (int)((old >> 8) & 255) + gg, B = (int)((old >> g.shb) & 255) + b;
    if (R > 255) R = 255;
    if (G > 255) G = 255;
    if (B > 255) B = 255;
    return ((UINT32)R << g.shr) | ((UINT32)G << 8) | ((UINT32)B << g.shb);
}

/* ---------------------------------------------------------------- ambient layer (fireflies, stars) */
static int hits_probe(int x, int y, int r) {
    for (int i = 0; i < g.h->nbg; i++) { int dx = (int)g.bgp[i].x - x, dy = (int)g.bgp[i].y - y; if (dx >= -r && dx <= r && dy >= -r && dy <= r) return 1; }
    return 0;
}
static void ambient_restore(void) {
    int W = 2 * FLY_R + 1;
    for (int i = g.h->nfly - 1; i >= 0; i--) if (g.fly_x[i] >= 0) {
        UINT32 *sv = g.fly_save + (UINT64)i * W * W;
        for (int dy = 0; dy < W; dy++) for (int dx = 0; dx < W; dx++) g_fb[(UINT64)(g.fly_y[i] - FLY_R + dy) * g_stride + g.fly_x[i] - FLY_R + dx] = sv[dy * W + dx];
        g.fly_x[i] = -1;
    }
    for (int i = g.h->nstar - 1; i >= 0; i--) if (g.star_x[i] >= 0) {
        for (int dy = 0; dy < 7; dy++) for (int dx = 0; dx < 7; dx++) g_fb[(UINT64)(g.star_y[i] - 3 + dy) * g_stride + g.star_x[i] - 3 + dx] = g.star_save[i][dy * 7 + dx];
        g.star_x[i] = -1;
    }
}
static void ambient_draw(void) {
    UINT32 t = g.tick; int W = 2 * FLY_R + 1;
    static const int arm[4][2] = {{1, 0}, {-1, 0}, {0, 1}, {0, -1}};
    for (int i = 0; i < g.h->nstar; i++) {                                    /* stars: extra twinkle on top of the baked dim star */
        const Star *s = &g.star[i]; int sn = isin(((t * 65536u) / (s->period ? s->period : 60)) + ((UINT32)s->phase << 8));
        if (sn <= 0) continue;
        int amt = (int)((((INT64)sn * sn) >> 15) * s->bright >> 15);
        if (amt < 24) continue;
        int cx = s->x, cy = s->y; if (cx < 4 || cy < 4 || hits_probe(cx, cy, 5)) continue;
        for (int dy = 0; dy < 7; dy++) for (int dx = 0; dx < 7; dx++) g.star_save[i][dy * 7 + dx] = g_fb[(UINT64)(cy - 3 + dy) * g_stride + cx - 3 + dx];
        g.star_x[i] = cx; g.star_y[i] = cy;
        UINT32 *c = &g_fb[(UINT64)cy * g_stride + cx]; *c = add_light(*c, amt, amt * 15 / 16, amt * 3 / 4);
        for (int k = 0; k < 4; k++) { UINT32 *a = &g_fb[(UINT64)(cy + arm[k][1]) * g_stride + cx + arm[k][0]]; *a = add_light(*a, amt / 3, amt / 3, amt / 4); }
        if (amt > 150) for (int k = 0; k < 4; k++) { UINT32 *a = &g_fb[(UINT64)(cy + 2 * arm[k][1]) * g_stride + cx + 2 * arm[k][0]]; *a = add_light(*a, amt / 8, amt / 8, amt / 10); }
    }
    for (int i = 0; i < g.h->nfly; i++) {
        const Fly *f = &g.fly[i];
        int x = f->hx + (int)(((INT64)f->ax * isin(f->p1 + f->w1 * t)) >> 15);
        int y = f->hy + (int)(((INT64)f->ay * isin(f->p2 + f->w2 * t)) >> 15);
        int s3 = isin(f->p3 + f->w3 * t); if (s3 <= 0) continue;
        int inten = (int)((((INT64)s3 * s3) >> 15) * f->peak >> 15); if (inten < 10) continue;
        if (x < FLY_R || y < FLY_R || hits_probe(x, y, FLY_R + 1)) continue;
        UINT32 *sv = g.fly_save + (UINT64)i * W * W;
        for (int dy = 0; dy < W; dy++) for (int dx = 0; dx < W; dx++) sv[dy * W + dx] = g_fb[(UINT64)(y - FLY_R + dy) * g_stride + x - FLY_R + dx];
        g.fly_x[i] = x; g.fly_y[i] = y;
        for (int dy = -FLY_R; dy <= FLY_R; dy++) for (int dx = -FLY_R; dx <= FLY_R; dx++) {
            int d2 = dx * dx + dy * dy; if (d2 > FLY_R * FLY_R) continue;
            int a = (g.lut[d2] * inten) >> 8; if (a < 2) continue;
            UINT32 *p = &g_fb[(UINT64)(y + dy) * g_stride + x + dx]; *p = add_light(*p, (f->r * a) >> 8, (f->g * a) >> 8, (f->b * a) >> 8);
        }
    }
}

/* ---------------------------------------------------------------- tile (selected cat) */
static void tile_update(void) {
    const Hdr *h = g.h; int lev = h->sway_n / 2;
    /* bird rocking: one sine over 2.8 s mapped onto the pre-rendered levels */
    int s = isin((g.tick * 1170u) & 0xFFFF);
    int l = (s * lev + (s >= 0 ? 16384 : -16384)) / 32768;
    int id = g.sway_ids[l + lev];
    if (id != g.cur_sway) { blit_patch(id); g.cur_sway = id; }
    /* blink: 2.5-5.5 s apart, now and then twice in a row; sequence half, shut, shut, half, open (50 ms each) */
    static const UINT8 seq[5] = {1, 2, 2, 1, 0};
    if (g.blink_step < 0 && g.tick >= g.next_blink) g.blink_step = 0;
    if (g.blink_step >= 0) {
        int bid = g.blink_ids[seq[g.blink_step]];
        if (bid != g.cur_blink) { blit_patch(bid); g.cur_blink = bid; }
        if (++g.blink_step >= 5) { g.blink_step = -1; g.next_blink = g.tick + ((rnd32() % 4 == 0) ? 5 : 50 + rnd32() % 60); }
    }
}

/* ---------------------------------------------------------------- timer */
static int probes_ok(void) {
    int good = 0;
    for (int i = 0; i < g.h->nbg; i++) if (near_color(rd(g.bgp[i].x, g.bgp[i].y), g.bgp[i].rgb) <= 24) good++;
#ifdef CATANIM_DEBUG
    if (g.tick % 60 == 0) { dbgn(" probes good ", good); dbgn(" of ", g.h->nbg); for (int i = 0; i < 3; i++) { dbgn("  got ", rd(g.bgp[i].x, g.bgp[i].y)); dbgn("  exp ", g.bgp[i].rgb); } }
#endif
    return good >= g.h->nbg - 1;
}
static int selected(void) {
    int good = 0;
    for (int i = 0; i < g.h->nring; i++) { UINT32 p = rd(g.ring[i].x, g.ring[i].y); if (near_color(p, g.ring[i].sel) + 24 < near_color(p, g.ring[i].unsel)) good++; }
    return g.h->nring >= 4 && good >= g.h->nring - 1;
}
static void invalidate(void) {
    for (int i = 0; i < g.h->nfly; i++) g.fly_x[i] = -1;
    for (int i = 0; i < g.h->nstar; i++) g.star_x[i] = -1;
    g.cur_sway = -1; g.cur_blink = -1; g.blink_step = -1; g.tile_sel = 0;
}

static void EFIAPI on_tick(EFI_EVENT ev, void *ctx) {
    (void)ev; (void)ctx;
    if (g.dead) return;
    g.tick++;
#ifdef CATANIM_CRASHTEST
    if (g.tick == 20) *(volatile UINT32 *)0x0000800000000000ULL = 1;     /* test hook: deliberate fault to exercise the NVRAM guard */
#endif
    GOP_MODE *m = g.gop->Mode; GOP_INFO *in = m ? m->Info : 0;
#ifdef CATANIM_DEBUG
    if (g.tick < 400 && (g.tick % 5) == 0) dbgn("t", g.tick);
    if (g.tick == 1 || g.tick % 60 == 0) { dbgn("tick ", g.tick); if (in) { dbgn(" hres ", in->HRes); dbgn(" vres ", in->VRes); dbgn(" fmt ", in->PixelFormat); dbgn(" stride ", in->PixelsPerScanLine); dbgn(" fb ", m->FrameBufferBase); } }
#endif
    if (!in || in->HRes != g.h->sw || in->VRes != g.h->sh || !m->FrameBufferBase || (in->PixelFormat != 0 && in->PixelFormat != 1) ||
        in->PixelsPerScanLine < in->HRes) { if (g.screen_ok) { g.screen_ok = 0; invalidate(); } return; }
    g_fb = (UINT32 *)(UINTN)m->FrameBufferBase; g_stride = in->PixelsPerScanLine;
#ifdef CATANIM_DEBUG
    { UINT32 c = ((g.tick * 5) & 255) << 16 | ((g.tick * 3) & 255) << 8 | 0xFF; for (int yy = 0; yy < 6; yy++) for (int xx = 0; xx < 40; xx++) g_fb[(UINT64)yy * g_stride + xx] = c; }
#endif
    g.swap = (in->PixelFormat == 0); g.shr = g.swap ? 0 : 16; g.shb = g.swap ? 16 : 0;
    if (!probes_ok()) { if (g.screen_ok) { g.screen_ok = 0; invalidate(); dbg("screen lost\n"); } return; }   /* not our menu: cleared, other mode, text... */
    if (!g.screen_ok) { g.screen_ok = 1; g.ok_ticks = 0; invalidate(); dbg("screen ok\n"); }
    if (++g.ok_ticks == 40) guard_confirm();
    ambient_restore();
    ambient_draw();
    int sel = selected();
    if (sel && !g.tile_sel) { g.cur_sway = -1; g.cur_blink = -1; g.blink_step = -1; g.next_blink = g.tick + 20 + rnd32() % 30; dbg("tile selected\n"); }
    g.tile_sel = sel;
    if (sel) tile_update(); else { g.cur_sway = -1; g.cur_blink = -1; g.blink_step = -1; }
}

static void EFIAPI on_exit_boot(EFI_EVENT ev, void *ctx) { (void)ev; (void)ctx; g.dead = 1; guard_confirm(); }

/* ---------------------------------------------------------------- entry */
static int load_data(EFI_HANDLE image) {
    LOADED_IMAGE *li; SIMPLE_FS *fs; EFI_FILE *root, *f; UINT64 size = 0;
    EFI_STATUS rc;
    if (EFI_ERROR(rc = g.bs->HandleProtocol(image, &GUID_LOADED, (void **)&li))) { dbgn("loaded-image proto failed ", rc); return 0; }
    if (EFI_ERROR(rc = g.bs->HandleProtocol(li->DeviceHandle, &GUID_SFS, (void **)&fs))) { dbgn("simple-fs proto failed ", rc); return 0; }
    if (EFI_ERROR(rc = fs->OpenVolume(fs, &root))) { dbgn("open volume failed ", rc); return 0; }
    if (EFI_ERROR(rc = root->Open(root, &f, DATA_PATH, 1 /* EFI_FILE_MODE_READ */, 0))) { dbgn("open data failed ", rc); root->Close(root); return 0; }
    int ok = 0;
    if (!EFI_ERROR(f->SetPosition(f, ~0ULL)) && !EFI_ERROR(f->GetPosition(f, &size)) && !EFI_ERROR(f->SetPosition(f, 0)) &&
        size > sizeof(Hdr) && size < (32u << 20) && !EFI_ERROR(g.bs->AllocatePool(4 /* BootServicesData */, size, (void **)&g.data))) {
        UINT64 done = 0; ok = 1;
        while (done < size) {
            UINTN n = size - done > 262144 ? 262144 : (UINTN)(size - done);
            EFI_STATUS rr = f->Read(f, &n, g.data + done);
            if (EFI_ERROR(rr) || n == 0) { dbgn("read failed ", rr); dbgn(" at ", done); ok = 0; break; }
            done += n;
        }
        g.size = size;
    }
    if (!ok) dbgn("load size ", size);
    f->Close(f); root->Close(root);
    return ok;
}

static int parse_data(void) {
    const Hdr *h = (const Hdr *)g.data;
    if (h->magic[0] != 'C' || h->magic[1] != 'A' || h->magic[2] != 'T' || h->magic[3] != 'A' || h->ver != 1) { dbg("bad magic\n"); return 0; }
    if (h->nfly > MAXFLY || h->nstar > MAXSTAR || h->nring > 16 || h->nbg > 32 || h->sway_n < 3 || (h->sway_n & 1) == 0 || h->blink_n < 3) { dbg("bad counts\n"); return 0; }
    const UINT8 *p = g.data + sizeof(Hdr);
    g.ring = (const Ring *)p;       p += h->nring * sizeof(Ring);
    g.bgp = (const BgProbe *)p;     p += h->nbg * sizeof(BgProbe);
    g.star = (const Star *)p;       p += h->nstar * sizeof(Star);
    g.fly = (const Fly *)p;         p += h->nfly * sizeof(Fly);
    g.patch = (const Patch *)p;     p += h->npatch * sizeof(Patch);
    g.sway_ids = (const UINT16 *)p; p += h->sway_n * 2;
    g.blink_ids = (const UINT16 *)p; p += h->blink_n * 2;
    if ((UINTN)(p - g.data) != h->data_off || h->data_off > g.size) { dbgn("bad data_off ", h->data_off); return 0; }
    for (int i = 0; i < h->sway_n; i++) if (g.sway_ids[i] >= h->npatch) return 0;
    for (int i = 0; i < h->blink_n; i++) if (g.blink_ids[i] >= h->npatch) return 0;
    for (int i = 0; i < h->npatch; i++) {
        const Patch *q = &g.patch[i];
        if (q->off % 4 || (UINT64)q->off + (UINT64)q->w * q->h * 4 > g.size - h->data_off) return 0;
    }
    g.h = h; g.pix = (const UINT32 *)(g.data + h->data_off);
    return 1;
}

EFI_STATUS EFIAPI efi_main(EFI_HANDLE image, EFI_SYSTEM_TABLE *st) {
    g.st = st; g.bs = st->BootServices; g.rt = st->RuntimeServices; g.rnd = (UINT32)(UINTN)image ^ 0x9E3779B9u;
    dbg("cat_anim: start\n");

    UINT8 n = 0; UINTN sz = 1; UINT32 attr = 0;
    if (!EFI_ERROR(g.rt->GetVariable(GUARD_NAME, &GUID_GUARD, &attr, &sz, &n)) && n >= 2) { dbg("cat_anim: disabled by guard\n"); return EFI_SUCCESS; }
    g.armed = 1; guard_set((UINT8)(n + 1));                      /* armed before anything that could possibly fault */

    if (!load_data(image) || !parse_data()) { dbg("cat_anim: no data\n"); guard_confirm(); return EFI_SUCCESS; }
    /* rEFInd draws through LocateProtocol(GOP) = the first instance, i.e. the device's own GOP rather than the console
       splitter's virtual one (whose Mode->Info is not updated by SetMode); use exactly the same instance */
    if (EFI_ERROR(g.bs->LocateProtocol(&GUID_GOP, 0, (void **)&g.gop)) &&
        EFI_ERROR(g.bs->HandleProtocol(st->ConsoleOutHandle, &GUID_GOP, (void **)&g.gop))) { dbg("cat_anim: no gop\n"); guard_confirm(); return EFI_SUCCESS; }
    if (EFI_ERROR(g.bs->AllocatePool(4, (UINTN)g.h->nfly * (2 * FLY_R + 1) * (2 * FLY_R + 1) * 4 + 16, (void **)&g.fly_save))) { guard_confirm(); return EFI_SUCCESS; }

    for (int d2 = 0; d2 <= FLY_R * FLY_R; d2++) { int v = FLY_R * FLY_R - d2; g.lut[d2] = (UINT8)((v * v * 255) / (FLY_R * FLY_R * FLY_R * FLY_R)); }
    for (int i = 0; i < MAXFLY; i++) g.fly_x[i] = -1;
    for (int i = 0; i < MAXSTAR; i++) g.star_x[i] = -1;
    g.cur_sway = g.cur_blink = -1; g.blink_step = -1;

    if (EFI_ERROR(g.bs->CreateEvent(0x00000201 /* EVT_SIGNAL_EXIT_BOOT_SERVICES */, TPL_NOTIFY, on_exit_boot, 0, &g.ebs)) ||
        EFI_ERROR(g.bs->CreateEvent(0x80000200 /* EVT_TIMER | EVT_NOTIFY_SIGNAL */, TPL_CALLBACK, on_tick, 0, &g.timer)) ||
        EFI_ERROR(g.bs->SetTimer(g.timer, 1 /* TimerPeriodic */, TICK_100NS))) { dbg("cat_anim: event setup failed\n"); g.dead = 1; guard_confirm(); return EFI_SUCCESS; }
    dbg("cat_anim: running\n");
    return EFI_SUCCESS;
}
