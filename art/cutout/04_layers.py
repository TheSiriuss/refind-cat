"""Split the cat cutout into head / bird layers (same canvas as cat_cutout.png) and locate the eyes.
   bird = polygon-seeded GrabCut region minus fur-coloured pixels;  head = cutout minus bird, with the hidden fur
   under the bird/tail inpainted so a swinging bird never exposes holes."""
import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1])); from paths import *
import cv2, numpy as np, json
S=str(WORK)+'/'
R=str(ART)+'/'
src=cv2.imread(S+'src.png'); cat=cv2.imread(R+'cat_cutout.png',cv2.IMREAD_UNCHANGED)
X0,Y0=505,222; h,w=cat.shape[:2]
H,W=src.shape[:2]
hsv=cv2.cvtColor(src,cv2.COLOR_BGR2HSV).astype(np.float32); Hh,Ss,Vv=hsv[...,0],hsv[...,1],hsv[...,2]
mb_union=cv2.imread(S+'m2.png',0)>0
poly=np.array([(738,806),(726,801),(714,790),(702,778),(696,764),(703,752),(716,745),(735,741),(752,745),(760,732),(790,714),(830,708),(880,706),(925,708),(945,690),(960,668),(985,646),(1000,646),(1004,664),(1000,690),(988,708),(972,722),(962,736),(955,745),(930,752),(905,764),(885,778),(868,786),(845,790),(822,787),(800,779),(781,769),(773,759),(765,764),(750,766),(742,774)],np.int32)
pm=np.zeros((H,W),np.uint8); cv2.fillPoly(pm,[poly],255)
k=lambda r:cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(2*r+1,2*r+1))
# fur-like: warm hue, moderate saturation (bird yellow is much more saturated; teal/navy are cold)
fur=((Hh<=21)|(Hh>=170))&(Ss>45)&(Vv>60)&~((Hh>=17)&(Ss>185)&(Vv>140))
fur|=((Hh>=14)&(Hh<=24)&(Ss<110)&(Vv>120))                      # pale tan highlights
bird=(pm>0)&mb_union&~fur
bird=cv2.morphologyEx(bird.astype(np.uint8)*255,cv2.MORPH_OPEN,k(1))
bird=cv2.morphologyEx(bird,cv2.MORPH_CLOSE,k(4))
n,lab,st,_=cv2.connectedComponentsWithStats(bird)
keep=np.zeros_like(bird)
for i in range(1,n):
    if st[i,cv2.CC_STAT_AREA]>350: keep[lab==i]=255
bird=keep
# fill holes inside the bird
inv=255-bird; n,lab,st,_=cv2.connectedComponentsWithStats(inv)
for i in range(1,n):
    if st[i,cv2.CC_STAT_AREA]<1500 and st[i,cv2.CC_STAT_LEFT]>0: bird[lab==i]=255
bird=cv2.GaussianBlur(bird,(0,0),1.6); bird=((bird>110)*255).astype(np.uint8)
# take in the thin yellow rim of the tail feather and similar saturated edge pixels
cut_a=np.zeros((H,W),np.uint8); cut_a[Y0:Y0+h,X0:X0+w]=(cat[...,3]>40)*255
fur_strict=((Hh<=21)|(Hh>=170))&(Ss>60)&(Ss<=185)&(Vv>80)
ext=(cv2.dilate(bird,k(6))>0)&(cut_a>0)&(pm>0)&~fur_strict
cold=((Hh>=70)&(Hh<=135)&(Ss>35)&(Vv>45))|((Hh>=15)&(Hh<=34)&(Ss>185)&(Vv>130))
near=(cv2.dilate(pm,k(18))>0)&(cut_a>0)
ext2=near&cold
bird=((bird>0)|ext|ext2).astype(np.uint8)*255
bird=cv2.morphologyEx(bird,cv2.MORPH_CLOSE,k(3))
n,lab,st,_=cv2.connectedComponentsWithStats(bird)
bird=np.where(np.isin(lab,[i for i in range(1,n) if st[i,cv2.CC_STAT_AREA]>200]),255,0).astype(np.uint8)
bird=cv2.GaussianBlur(bird,(0,0),1.2); bird=((bird>110)*255).astype(np.uint8)
bird_c=bird[Y0:Y0+h,X0:X0+w]
cv2.imwrite(S+'bird_mask_c.png',bird_c)
# overlay for review
vis=cat.copy(); a=vis[...,3:4].astype(np.float32)/255
bg=np.full((h,w,3),(30,22,18),np.float32); comp=vis[...,:3]*a+bg*(1-a)
comp[bird_c>0]=comp[bird_c>0]*0.55+np.array([255,0,255])*0.45
cv2.imwrite(S+'bird_review.png',comp.astype(np.uint8)[h-230:,:])
print('bird px',int((bird_c>0).sum()))

# ---------- layers ----------
rgb=cat[...,:3]; alpha=cat[...,3]
b_soft=cv2.GaussianBlur(bird_c,(0,0),0.9).astype(np.float32)/255
bird_rgba=np.dstack([rgb,(alpha.astype(np.float32)*b_soft).astype(np.uint8)])
# head: remove bird, but keep an inpainted fur band under the bird edge where it touches visible fur
head_vis=((alpha>40)&(bird_c==0)).astype(np.uint8)*255
band=(cv2.dilate(head_vis,k(20))>0)&(bird_c>0)&(alpha>0)
mask_inp=((cv2.dilate((bird_c>0).astype(np.uint8)*255,k(3))>0)|(alpha<200)).astype(np.uint8)*255
fill=cv2.inpaint(rgb,mask_inp,9,cv2.INPAINT_TELEA)
fill=(fill.astype(np.float32)*0.62).astype(np.uint8)                      # in the shadow under the chin / tail
hv=cv2.GaussianBlur(head_vis,(0,0),0.9).astype(np.float32)/255
ba=cv2.GaussianBlur(band.astype(np.float32),(0,0),2.0)*(alpha.astype(np.float32)/255)
head_a=np.maximum(hv,ba)
head_rgb=np.where((bird_c>0)[...,None],fill,rgb)
head_rgba=np.dstack([head_rgb,(np.clip(head_a,0,1)*255).astype(np.uint8)])
import os; os.makedirs(R+'layers',exist_ok=True)
cv2.imwrite(R+'layers/head.png',head_rgba); cv2.imwrite(R+'layers/bird.png',bird_rgba)
cv2.imwrite(S+'bird_mask_c.png',bird_c)
print('layers written; bird px',int((bird_c>0).sum()))
