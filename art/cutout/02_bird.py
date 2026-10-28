import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1])); from paths import *
import cv2, numpy as np
S=str(WORK)+'/'
img=cv2.imread(S+'src.png'); H,W=img.shape[:2]
head=cv2.imread(S+'m1.png',0)>0
bird_poly=np.array([(738,806),(726,801),(714,790),(702,778),(696,764),(703,752),(716,745),(735,741),(752,745),(760,732),(790,714),(830,708),(880,706),(925,708),(945,690),(960,668),(985,646),(1000,646),(1004,664),(1000,690),(988,708),(972,722),(962,736),(955,745),(930,752),(905,764),(885,778),(868,786),(845,790),(822,787),(800,779),(781,769),(773,759),(765,764),(750,766),(742,774)],np.int32)
poly=np.zeros((H,W),np.uint8); cv2.fillPoly(poly,[bird_poly],255)
k=lambda r:cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(2*r+1,2*r+1))
mask=np.full((H,W),cv2.GC_BGD,np.uint8)
mask[cv2.dilate(poly,k(12))>0]=cv2.GC_PR_BGD
mask[poly>0]=cv2.GC_PR_FGD
mask[cv2.erode(poly,k(5))>0]=cv2.GC_FGD
# the already-good head counts as sure foreground, nothing outside it is allowed to pull the model
mask[head & (cv2.erode(head.astype(np.uint8)*255,k(8))>0)]=cv2.GC_FGD
bg=np.zeros((1,65)); fg=np.zeros((1,65))
cv2.grabCut(img,mask,None,bg,fg,8,cv2.GC_INIT_WITH_MASK)
m=((mask==cv2.GC_FGD)|(mask==cv2.GC_PR_FGD))
m=m|head
cv2.imwrite(S+'m2.png',m.astype(np.uint8)*255)
ov=img.copy(); ov[~m]=(ov[~m]*0.2+np.array([255,0,255])*0.3).astype(np.uint8)
cv2.polylines(ov,[bird_poly],True,(0,255,255),1)
cv2.imwrite(S+'ov2.png',cv2.resize(ov[620:830,670:1030],None,fx=3,fy=3,interpolation=cv2.INTER_CUBIC))
