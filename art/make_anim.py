"""Build themes/cat/anim.bin for cat_anim_x64.efi:
   - pre-composited tile patches (blink + bird rocking), exact over bg+selection
   - selection probes, background probes, twinkling stars, firefly parameters"""
import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent)); from paths import *
import sys, json, struct, numpy as np, cv2
import animlib as A
S=str(WORK)+'/'
OUT=str(THEME/'anim.bin')
TILE_XY=(816,456); SW,SH=1920,1200; T=A.TILE
import os
VARIANT=os.environ.get('VARIANT','night')
rng=np.random.default_rng(2026)
bg=A.load_bg(); sel=A.load_sel()
def tile_img(angle,blink,selected=True):
    return A.tile_composite(bg,sel,A.to_icon(A.render_cat(angle,blink)),TILE_XY,selected)
base=tile_img(0,0)
def bbox(mask,pad):
    ys,xs=np.where(mask); return max(0,xs.min()-pad),max(0,ys.min()-pad),min(T,xs.max()+1+pad),min(T,ys.max()+1+pad)
def u32(img):                      # BGR float -> 0x00RRGGBB
    a=np.clip(np.rint(img),0,255).astype(np.uint32); return (a[...,2]<<16)|(a[...,1]<<8)|a[...,0]
patches=[]; blobs=[]
def add_patch(img,rect):
    x0,y0,x1,y1=rect; px=u32(img[y0:y1,x0:x1]); patches.append((x0,y0,x1-x0,y1-y0,len(b''.join(blobs)))); blobs.append(px.astype('<u4').tobytes()); return len(patches)-1
# ---- blink track
bl=[tile_img(0,c) for c in (0.5,1.0)]
eb=bbox((np.abs(bl[1]-base).max(2)>1.0)|(np.abs(bl[0]-base).max(2)>1.0),3)
blink_ids=[add_patch(base,eb)]+[add_patch(im,eb) for im in bl]
# ---- sway track
LEV=10; STEP=0.42
sw_imgs=[tile_img(l*STEP,0) for l in range(-LEV,LEV+1)]
m=np.zeros((T,T),bool)
for im in sw_imgs: m|=np.abs(im-base).max(2)>1.0
sb=bbox(m,3)
sway_ids=[add_patch(im,sb) for im in sw_imgs]
print('eye rect',eb,'sway rect',sb)
assert eb[2]<=sb[0] or eb[3]<=sb[1] or sb[2]<=eb[0] or sb[3]<=eb[1], 'tracks overlap'
# ---- selection probes (ring zone outside the icon rect)
unsel=tile_img(0,0,False)
diff=np.abs(base-unsel).sum(2); zone=np.zeros((T,T),bool); zone[:A.ICON_OFF,:]=1; zone[-A.ICON_OFF:,:]=1; zone[:,:A.ICON_OFF]=1; zone[:,-A.ICON_OFF:]=1
cy=cx=T/2; ang=np.arctan2(*(np.mgrid[0:T,0:T]-cy)); ring=[]
for k in range(8):
    lo=-np.pi+k*np.pi/4; sec=zone&(ang>=lo)&(ang<lo+np.pi/4)&(diff>140); 
    if not sec.any(): continue
    idx=np.argmax(np.where(sec,diff,-1)); y,x=divmod(idx,T); ring.append((x,y,diff[y,x]))
print('ring probes',[(x,y,int(d)) for x,y,d in ring])
def rgb_of(img,x,y): b,g,r=np.clip(np.rint(img[y,x]),0,255).astype(int); return (r<<16)|(g<<8)|b
ring_p=[(TILE_XY[0]+x,TILE_XY[1]+y,rgb_of(unsel,x,y),rgb_of(base,x,y)) for x,y,_ in ring]
# ---- background probes
bgi=cv2.imread(str(THEME/'bg.png'))
bgp=[(x,y,(int(bgi[y,x,2])<<16)|(int(bgi[y,x,1])<<8)|int(bgi[y,x,0])) for x,y in [(60,60),(1860,60),(60,600),(1860,600),(300,1100),(1600,1100),(500,120),(1400,120),(200,900),(1700,900)]]
# ---- stars (free zone only)
stars_all=json.load(open(S+'stars.json')) if VARIANT=='night' else []; KEEP=(500,430,1420,910)
stars=[]
for x,y,b in stars_all:
    if KEEP[0]<x<KEEP[2] and KEEP[1]<y<KEEP[3]: continue
    if any(abs(x-px)<12 and abs(y-py)<12 for px,py,_ in bgp): continue
    stars.append((x,y,int(40+215*b),int(rng.integers(0,256)),int(rng.integers(36,100))))
# ---- fireflies
zones=[(30,40,1890,420,6),(30,930,1890,1085,6),(20,450,490,900,3),(1430,450,1900,900,3)] if VARIANT=='night' else [(30,920,1890,1090,9),(20,560,470,900,3),(1440,560,1900,900,3),(20,20,700,150,2),(1180,20,1900,160,2)]
flies=[]
for (zx0,zy0,zx1,zy1,n) in zones:
    for _ in range(n):
        ax=int(rng.integers(25,95)); ay=int(rng.integers(12,45)); R_=9
        hx=int(rng.integers(zx0+ax+R_,zx1-ax-R_)); hy=int(rng.integers(zy0+ay+R_,zy1-ay-R_))
        per=lambda lo,hi:int(65536/rng.integers(lo,hi))
        col=[(235,255,120),(255,214,110),(190,255,150)][int(rng.integers(0,3))]
        flies.append((hx,hy,ax,ay,per(70,190),per(60,150),per(34,90),int(rng.integers(0,65536)),int(rng.integers(0,65536)),int(rng.integers(0,65536)),R_,int(rng.integers(170,256)),*col))
print('stars',len(stars),'flies',len(flies),'patches',len(patches),'data bytes',sum(len(b) for b in blobs))
# ---- serialise
HDR=struct.Struct('<4sHHHHHHHHHHHHHI')   # magic,ver,sw,sh,tx,ty,nring,nbg,nstar,nfly,npatch,sway_n,blink_n,pad, data_off
body=b''
body+=b''.join(struct.pack('<HHII',*p) for p in ring_p)
body+=b''.join(struct.pack('<HHI',*p) for p in bgp)
body+=b''.join(struct.pack('<HHBBH',*s) for s in stars)
body+=b''.join(struct.pack('<HHHHHHHHHHBBBBB',*f) for f in flies)
body+=b''.join(struct.pack('<HHHHI',*p) for p in patches)
body+=struct.pack('<%dH'%len(sway_ids),*sway_ids)+struct.pack('<%dH'%len(blink_ids),*blink_ids)
hdr_size=HDR.size; data_off=hdr_size+len(body)
hdr=HDR.pack(b'CATA',1,SW,SH,TILE_XY[0],TILE_XY[1],len(ring_p),len(bgp),len(stars),len(flies),len(patches),len(sway_ids),len(blink_ids),0,data_off)
open(OUT,'wb').write(hdr+body+b''.join(blobs))
print('wrote',OUT,hdr_size+len(body)+sum(len(b) for b in blobs),'bytes')
# ---- preview contact sheet
cv2.imwrite(S+'anim_prev.png',np.hstack([np.clip(base,0,255).astype(np.uint8),np.clip(bl[1],0,255).astype(np.uint8),np.clip(sw_imgs[0],0,255).astype(np.uint8),np.clip(sw_imgs[-1],0,255).astype(np.uint8)]))
