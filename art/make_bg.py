"""plate.png (cat-free painting) -> bg.png 1920x1200 night meadow + stars.json (twinkle positions)."""
import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent)); from paths import *
import cv2, numpy as np, json, sys
import os
OUT=str(WORK)+'/'; S=OUT
CX,CY=960,600                                              # icon centre on screen (glow anchor)
VARIANT=os.environ.get('VARIANT','night')                  # night: graded + glow + stars;  day: the painting untouched
rng=np.random.default_rng(11)
plate=cv2.imread(str(SOURCE/'withoutcat.png')); plate=cv2.resize(plate,(1920,1200),interpolation=cv2.INTER_LANCZOS4)
if VARIANT=='day':
    cv2.imwrite(OUT+'bg.png',plate); json.dump([],open(OUT+'stars.json','w'))
    cv2.imwrite(OUT+'bg_s.png',cv2.resize(plate,None,fx=0.5,fy=0.5,interpolation=cv2.INTER_AREA)); print('day variant, no stars'); sys.exit(0)
img=plate.astype(np.float32)/255; b,g,r=cv2.split(img); lum=0.2126*r+0.7152*g+0.0722*b
stops=np.array([0.0,0.18,0.45,0.75,1.0]); cols=np.array([[0.015,0.025,0.055],[0.035,0.085,0.14],[0.09,0.23,0.30],[0.40,0.54,0.62],[0.90,0.88,0.76]])
gm=np.stack([np.interp(lum,stops,cols[:,i]) for i in range(3)],-1)
rgb=np.stack([r,g,b],-1)
night=0.64*gm+0.36*rgb*np.array([0.40,0.50,0.62])
# keep the cardinal red alive (and a bit of the bluebird)
redm=np.clip((r-np.maximum(g,b)-0.22)*6,0,1); redm=cv2.GaussianBlur(redm,(0,0),1.2)[...,None]
night=night*(1-redm)+rgb*np.array([0.78,0.36,0.30])*redm
hsv=cv2.cvtColor(plate,cv2.COLOR_BGR2HSV).astype(np.float32)
bx=np.zeros(lum.shape,np.float32); bx[95:300,1540:1880]=1; bx=cv2.GaussianBlur(bx,(0,0),6)
bm=np.clip((hsv[...,1]/255-0.30)*4,0,1)*bx; bm=cv2.GaussianBlur(bm,(0,0),1.0)[...,None]   # bluebird keeps its teal / yellow
night=night*(1-bm)+rgb*np.array([0.62,0.66,0.66])*bm
h,w=lum.shape; yy,xx=np.mgrid[0:h,0:w].astype(np.float32)
# sky mask (bright + bluish, above horizon) for stars
horizon=662*1.2106   # (painting is 1586x992; plate is scaled to 1920x1200)
sky=(lum>0.55)&(yy<horizon-8)
sky=cv2.erode(sky.astype(np.uint8),np.ones((5,5),np.uint8))
sky[20:520,230:500]=0        # cardinal
sky[80:330,1520:1900]=0      # bluebird
# moon-glow behind the icon
d=np.sqrt((xx-CX)**2+((yy-CY)*1.08)**2)
glow=np.clip(1-d/470,0,1)**2.2
night+=glow[...,None]*np.array([0.20,0.17,0.10])   # warm cream (RGB)
# vignette
vig=1-0.70*(((xx-w/2)/(w*0.60))**2+((yy-h*0.46)/(h*0.62))**2)
night*=np.clip(vig,0.12,1)[...,None]
# stars
stars=[]
cand=np.argwhere(sky>0)
tries=0
while len(stars)<70 and tries<20000:
    tries+=1; y,x=cand[rng.integers(len(cand))]
    if np.hypot(x-CX,(y-CY))<250: continue
    if y<8 or x<8 or x>w-9 or y>h-9: continue
    if min([np.hypot(x-sx,y-sy) for sx,sy,_ in stars] or [999])<40: continue
    stars.append((int(x),int(y),float(rng.uniform(0.5,1.0))))
for x,y,s_ in stars:
    night[y,x]+=0.45*s_
    night[y,x-1]+=0.12*s_;night[y,x+1]+=0.12*s_;night[y-1,x]+=0.12*s_;night[y+1,x]+=0.12*s_
night=np.clip(night,0,1)
# fine film grain so gradients dither on 8-bit panels
night+= (rng.random((h,w,1)).astype(np.float32)-0.5)*0.012
out=(np.clip(night,0,1)[...,::-1]*255).astype(np.uint8)
cv2.imwrite(OUT+'bg.png',out)
json.dump(stars,open(OUT+'stars.json','w'))
cv2.imwrite(OUT+'bg_s.png',cv2.resize(out,None,fx=0.5,fy=0.5,interpolation=cv2.INTER_AREA))
print('stars',len(stars))
