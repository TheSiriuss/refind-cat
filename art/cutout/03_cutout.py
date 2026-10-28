import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1])); from paths import *
import cv2, numpy as np
S=str(WORK)+'/'
img=cv2.imread(S+'src.png'); H,W=img.shape[:2]
hsv=cv2.cvtColor(img,cv2.COLOR_BGR2HSV); Hh,Ss,Vv=[hsv[...,i].astype(np.float32) for i in range(3)]
m=cv2.imread(S+'m2.png',0)>0
k=lambda r:cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(2*r+1,2*r+1))
# close small notches, drop islands
m8=cv2.morphologyEx(m.astype(np.uint8)*255,cv2.MORPH_CLOSE,k(7))
n,lab,st,_=cv2.connectedComponentsWithStats(m8)
big=1+np.argmax(st[1:,cv2.CC_STAT_AREA]); m8=((lab==big)*255).astype(np.uint8)
# fill holes
inv=255-m8; n,lab,st,_=cv2.connectedComponentsWithStats(inv)
for i in range(1,n):
    x,y,w,h,a=st[i]
    if a<4000 and x>0 and y>0: m8[lab==i]=255
# smooth contour
m8=cv2.morphologyEx(m8,cv2.MORPH_OPEN,k(6)); m8=cv2.morphologyEx(m8,cv2.MORPH_CLOSE,k(6))
m8=cv2.GaussianBlur(m8,(0,0),3.4); m8=((m8>127)*255).astype(np.uint8)
# whiskers over grass / dark trees: bright, unsaturated, near the face
zoneL=np.array([(560,640),(760,690),(790,800),(560,800)],np.int32)
zoneR=np.array([(940,668),(1075,668),(1075,780),(935,760)],np.int32)
z=np.zeros((H,W),np.uint8); cv2.fillPoly(z,[zoneL],255); cv2.fillPoly(z,[zoneR],255)
cand=((Vv>150)&(Ss<115)&(z>0)&(m8==0)).astype(np.uint8)
cand=cv2.morphologyEx(cand,cv2.MORPH_OPEN,np.ones((1,1),np.uint8))
# keep only whiskers that touch (come from) the cat
near=cv2.dilate(m8,k(70))>0
nc,lab2,st2,_=cv2.connectedComponentsWithStats(cand,connectivity=8)
keep=np.zeros((H,W),np.uint8)
for i in range(1,nc):
    comp=lab2==i
    if st2[i,cv2.CC_STAT_AREA]>=70 and max(st2[i,cv2.CC_STAT_WIDTH],st2[i,cv2.CC_STAT_HEIGHT])>=30 and (cv2.dilate(comp.astype(np.uint8),k(3))>0)[m8>0].any():
        keep[comp]=255
whisk_alpha=np.clip((Vv-135)/70,0,1)*(cv2.dilate(keep,k(1))>0)
# final alpha: body edge eroded 1px, soft; whiskers added
body=cv2.erode(m8,k(1)).astype(np.float32)/255
body=cv2.GaussianBlur(body,(0,0),0.9)
alpha=np.maximum(body,whisk_alpha.astype(np.float32))
# colour decontamination: replace edge-band colours with colours pulled from the interior
core=cv2.erode(m8,k(3))
band=((alpha>0.02)&(core==0)&(whisk_alpha<0.01)).astype(np.uint8)*255
rgb=cv2.inpaint(img,band,4,cv2.INPAINT_TELEA)
out=np.dstack([rgb,(alpha*255).astype(np.uint8)])
ys,xs=np.where(alpha>0.02); y0,y1,x0,x1=ys.min()-6,ys.max()+7,xs.min()-6,xs.max()+7
out=out[y0:y1,x0:x1]
cv2.imwrite(S+'cat_full.png',out)
print('bbox',x0,y0,x1,y1,'size',out.shape)
def comp(bgc,name):
    a=out[...,3:4].astype(np.float32)/255; bgi=np.zeros_like(out[...,:3],np.float32)+np.array(bgc,np.float32)
    cv2.imwrite(S+name,(out[...,:3]*a+bgi*(1-a)).astype(np.uint8))
comp((26,18,14),'chk_dark.png'); comp((235,235,235),'chk_light.png')
