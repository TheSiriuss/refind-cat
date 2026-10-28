"""Frame renderer for the cat icon: layered head/bird, eyelids, bird rocking, drop shadow, icon scaling."""
import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent)); from paths import *
import cv2, numpy as np
X0,Y0=505,222                      # cutout origin in the painting
head=cv2.imread(str(LAYERS/'head.png'),cv2.IMREAD_UNCHANGED).astype(np.float32)
bird=cv2.imread(str(LAYERS/'bird.png'),cv2.IMREAD_UNCHANGED).astype(np.float32)
CH,CW=head.shape[:2]
BIRD_PIVOT=(850-X0,714-Y0)         # where the bird is gripped (centre of the muzzle) in cutout coords
EYES=[(756-X0,530-Y0,43,33),(920-X0,533-Y0,38,32)]   # cx,cy,rx,ry in cutout coords
SS=2  # layer supersampling for the rotated bird

def premul(a):
    o=a.copy(); o[...,:3]*=o[...,3:4]/255.0; return o
def unpremul(a):
    o=a.copy(); al=np.maximum(o[...,3:4],1e-3)/255.0; o[...,:3]=np.where(o[...,3:4]>0,o[...,:3]/al,0); return o
def over(dst,src):
    """premultiplied float images, alpha 0..255"""
    sa=src[...,3:4]/255.0; return src+dst*(1-sa)

_head_p=premul(head); _bird_p=premul(bird)
def rotate_premul(img,angle,pivot):
    M=cv2.getRotationMatrix2D(pivot,angle,1.0)
    return cv2.warpAffine(img,M,(img.shape[1],img.shape[0]),flags=cv2.INTER_CUBIC,borderMode=cv2.BORDER_CONSTANT,borderValue=(0,0,0,0))

# ---- eyelids ------------------------------------------------------------------------------------
def _lid_colour(img_bgr,alpha,cx,cy,rx,ry):
    yy,xx=np.mgrid[0:CH,0:CW].astype(np.float32)
    d=((xx-cx)/rx)**2+((yy-cy)/ry)**2
    ring=(d>1.25)&(d<2.4)&(alpha>200)
    hsv=cv2.cvtColor(np.clip(img_bgr,0,255).astype(np.uint8),cv2.COLOR_BGR2HSV)
    dark=ring&(hsv[...,2]<105)
    px=img_bgr[dark]
    return np.median(px,axis=0) if len(px)>50 else np.array([28,36,48],np.float32)
def apply_lids(img_bgra,closure,rng_seed=3):
    """img_bgra: straight-alpha float cat image; closure 0..1 (1 = shut). Lid = real fur texture cloned from just above the eye."""
    if closure<=0.001: return img_bgra
    out=img_bgra.copy(); yy,xx=np.mgrid[0:CH,0:CW].astype(np.float32)
    for ei,(cx,cy,rx,ry) in enumerate(EYES):
        d=((xx-cx)/rx)**2+((yy-cy)/ry)**2
        ytop=cy-ry-8; ybot=cy+ry+4
        yl=ytop+closure*(ybot-ytop)
        bow=(1-np.clip((xx-cx)/rx,-1,1)**2)*8*closure            # lower edge bulges down in the middle
        lidm=((d<1.12)&(yy<yl+bow)).astype(np.float32)
        lidm=cv2.GaussianBlur(lidm,(0,0),2.2)
        # fur texture: copy from 44px above (brow fur), darkened to sit in the eye socket shadow
        M=np.float32([[1,0,(8 if ei==0 else -4)],[0,1,82]]); fur=cv2.warpAffine(img_bgra[...,:3],M,(CW,CH),flags=cv2.INTER_LINEAR,borderMode=cv2.BORDER_REFLECT)
        fur=cv2.GaussianBlur(fur,(0,0),0.9)*0.78
        a=lidm[...,None]*(out[...,3:4]>0)
        out[...,:3]=out[...,:3]*(1-a)+fur*a
        # thin dark lash line along the lid edge
        edge=np.exp(-((yy-(yl+bow-1))**2)/(2*1.5**2))*((d<1.05).astype(np.float32))*np.clip(closure*3,0,1)
        edge=cv2.GaussianBlur(edge,(0,0),0.8)*0.85
        out[...,:3]=out[...,:3]*(1-edge[...,None])+np.array([12,16,22],np.float32)*edge[...,None]
    return out

# ---- full cat ------------------------------------------------------------------------------------
def render_cat(angle=0.0,blink=0.0):
    """-> straight-alpha BGRA float (CH,CW,4)"""
    # bird rotated at 2x for quality, then folded back
    if abs(angle)>1e-6:
        b2=cv2.resize(_bird_p,(CW*SS,CH*SS),interpolation=cv2.INTER_CUBIC)
        b2=rotate_premul(b2,angle,(BIRD_PIVOT[0]*SS,BIRD_PIVOT[1]*SS))
        b=cv2.resize(b2,(CW,CH),interpolation=cv2.INTER_AREA)
    else: b=_bird_p
    comp=over(_head_p,b)                       # bird in front of the head layer
    out=unpremul(comp)
    return apply_lids(out,blink)

def to_icon(cat_bgra,size=256,margin=10,shadow=True):
    """scale to the icon canvas (same geometry as the static icon), add drop shadow. -> premultiplied float RGBA-less BGRA (size,size,4)"""
    s=(size-2*margin)/max(CW,CH); w,h=round(CW*s),round(CH*s)
    p=premul(cat_bgra); p=cv2.resize(p,(w,h),interpolation=cv2.INTER_AREA)
    canvas=np.zeros((size,size,4),np.float32); ox,oy=(size-w)//2,(size-h)//2-2
    layer=np.zeros((size,size,4),np.float32); layer[oy:oy+h,ox:ox+w]=p
    out=layer
    if shadow:
        a=np.zeros((size,size),np.float32); a[oy+5:oy+5+h,ox:ox+w]=p[...,3]/255.0
        a=cv2.GaussianBlur(a,(0,0),5)*0.55
        sh=np.zeros((size,size,4),np.float32); sh[...,3]=a*255
        out=over(sh,layer)
    return out   # premultiplied BGRA, alpha 0..255

# ---- tile compositing (replicates what rEFInd draws for the selected big icon) -----------------------
TILE=288; ICON_OFF=16
BG_PATH=str(THEME/'bg.png')
SEL_PATH=str(THEME/'selection_big.png')
def load_bg(): return cv2.imread(BG_PATH).astype(np.float32)
def load_sel():
    s=cv2.imread(SEL_PATH,cv2.IMREAD_UNCHANGED).astype(np.float32); return premul(s)
def tile_composite(bg,sel_p,icon_p,tile_xy,selected=True):
    """bg: full-screen BGR float; icon_p: premultiplied BGRA icon (256x256). -> BGR float tile (TILE,TILE,3)"""
    tx,ty=tile_xy; base=bg[ty:ty+TILE,tx:tx+TILE].copy()
    if selected: base=sel_p[...,:3]+base*(1-sel_p[...,3:4]/255.0)
    ic=icon_p; y0=ICON_OFF; x0=ICON_OFF; n=ic.shape[0]
    reg=base[y0:y0+n,x0:x0+n]; base[y0:y0+n,x0:x0+n]=ic[...,:3]+reg*(1-ic[...,3:4]/255.0)
    return base
