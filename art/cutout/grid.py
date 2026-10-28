import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1])); from paths import *
import cv2, numpy as np, sys
S=str(WORK)+'/'
src,x0,y0,x1,y1,sc,step,out=sys.argv[1],*map(int,sys.argv[2:8]),sys.argv[8]
img=cv2.imread(S+src)[y0:y1,x0:x1]
img=cv2.resize(img,None,fx=sc,fy=sc,interpolation=cv2.INTER_CUBIC)
for x in range((x0//step+1)*step,x1,step):
    X=(x-x0)*sc; cv2.line(img,(X,0),(X,img.shape[0]),(0,255,255) if x%100==0 else (255,255,255),1)
    cv2.putText(img,str(x),(X+2,12),cv2.FONT_HERSHEY_SIMPLEX,0.4,(0,0,255),1,cv2.LINE_AA)
for y in range((y0//step+1)*step,y1,step):
    Y=(y-y0)*sc; cv2.line(img,(0,Y),(img.shape[1],Y),(0,255,255) if y%100==0 else (255,255,255),1)
    cv2.putText(img,str(y),(2,Y-2),cv2.FONT_HERSHEY_SIMPLEX,0.4,(0,0,255),1,cv2.LINE_AA)
cv2.imwrite(S+out,img)
