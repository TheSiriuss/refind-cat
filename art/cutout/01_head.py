import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1])); from paths import *
import cv2, numpy as np, sys
S=str(WORK)+'/'
img=cv2.imread(S+'src.png')
H,W=img.shape[:2]
hsv=cv2.cvtColor(img,cv2.COLOR_BGR2HSV)
mask=np.full((H,W),cv2.GC_BGD,np.uint8)
# probable region: generous box around cat + bird
x0,y0,x1,y1=490,215,1100,870
mask[y0:y1,x0:x1]=cv2.GC_PR_BGD
# probable fg: ellipse-ish core of head
cv2.ellipse(mask,(790,520),(250,260),0,0,360,cv2.GC_PR_FGD,-1)
# sure fg: smaller core
cv2.ellipse(mask,(790,520),(170,170),0,0,360,cv2.GC_FGD,-1)
bg=np.zeros((1,65),np.float64); fg=np.zeros((1,65),np.float64)
cv2.grabCut(img,mask,None,bg,fg,6,cv2.GC_INIT_WITH_MASK)
m=((mask==cv2.GC_FGD)|(mask==cv2.GC_PR_FGD)).astype(np.uint8)*255
cv2.imwrite(S+'m1.png',m)
ov=img.copy(); ov[m==0]=(ov[m==0]*0.25+np.array([255,0,255])*0.25).astype(np.uint8)
cv2.imwrite(S+'ov1.png',ov[200:880,470:1120])
