"""Generate the rEFInd theme assets (icons, selection tiles, font) into build/EFI/refind/themes/cat/."""
import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent)); from paths import *
import os, sys, math
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
T=str(THEME)+'/'; os.makedirs(T+'icons',exist_ok=True)
BIG,SMALL=256,48
TILE_BIG=BIG*9//8; TILE_SMALL=SMALL*4//3
CREAM=(240,228,196); AMBER=(255,190,82)
SS=4  # supersampling for hand-drawn shapes

def premul_resize(im,size):
    r=im.convert('RGBa').resize(size,Image.LANCZOS); return r.convert('RGBA')

# ---------- cat icon ----------
cat=Image.open(str(ART/'cat_cutout.png')).convert('RGBA')
def cat_icon(size=BIG,margin=10,shadow=True):
    s=(size-2*margin)/max(cat.size); w,h=round(cat.width*s),round(cat.height*s)
    c=premul_resize(cat,(w,h)); canvas=Image.new('RGBA',(size,size),(0,0,0,0))
    ox,oy=(size-w)//2,(size-h)//2-2
    if shadow:
        a=c.getchannel('A'); sh=Image.new('RGBA',(size,size),(0,0,0,0)); sh.paste((0,0,0,255),(ox,oy+5),a)
        sh=sh.filter(ImageFilter.GaussianBlur(5)); sa=sh.getchannel('A').point(lambda v:int(v*0.55)); sh.putalpha(sa)
        canvas=Image.alpha_composite(canvas,sh)
    layer=Image.new('RGBA',(size,size),(0,0,0,0)); layer.paste(c,(ox,oy)); return Image.alpha_composite(canvas,layer),(ox,oy)
import animlib as _A
_p=_A.to_icon(_A.render_cat(0,0)); _al=np.maximum(_p[...,3:4],1e-3)/255.0
_st=np.where(_p[...,3:4]>0,_p[...,:3]/_al,0)
icon=Image.fromarray(np.dstack([np.clip(_st[...,2::-1].copy()[...,::1],0,255),np.clip(_p[...,3:4],0,255)]).astype(np.uint8),'RGBA'); icx=icy=0
icon.save(T+'icons/os_cachyos.png')
for n in ('os_linux','os_arch','os_endeavouros','os_manjaro'): icon.save(T+f'icons/{n}.png')

# ---------- selection tiles ----------
def rounded_tile(size,radius,fill,border,bw,glow,glowr):
    S=size*SS; g=Image.new('RGBA',(S,S),(0,0,0,0)); pad=int(glowr*1.6*SS)
    box=[pad,pad,S-pad-1,S-pad-1]
    gl=Image.new('RGBA',(S,S),(0,0,0,0)); ImageDraw.Draw(gl).rounded_rectangle(box,radius*SS,outline=glow,width=bw*SS*2)
    gl=gl.filter(ImageFilter.GaussianBlur(glowr*SS)); g=Image.alpha_composite(g,gl)
    d=Image.new('RGBA',(S,S),(0,0,0,0)); dd=ImageDraw.Draw(d)
    dd.rounded_rectangle(box,radius*SS,fill=fill,outline=border,width=bw*SS)
    g=Image.alpha_composite(g,d); return g.resize((size,size),Image.LANCZOS)
selb=rounded_tile(TILE_BIG,34,(255,236,196,26),(*AMBER,230),2,(*AMBER,150),6)
selb.save(T+'selection_big.png')
sels=rounded_tile(TILE_SMALL,14,(255,236,196,26),(*AMBER,230),2,(*AMBER,140),3)
sels.save(T+'selection_small.png')

# ---------- tool icons (vector-ish, supersampled) ----------
def canvas(size): return Image.new('RGBA',(size*SS,size*SS),(0,0,0,0))
def finish(im,size): return im.resize((size,size),Image.LANCZOS)
def stroke(size): return max(2,round(size*0.075))*SS
def icon_power(size):
    im=canvas(size); d=ImageDraw.Draw(im); S=size*SS; c=S/2; r=S*0.30; w=stroke(size)
    d.arc([c-r,c-r+S*0.03,c+r,c+r+S*0.03],-60,240,fill=(*CREAM,255),width=w)
    d.line([c,S*0.16,c,S*0.46],fill=(*CREAM,255),width=w)
    for x,y in ((c,S*0.16),(c,S*0.46)): d.ellipse([x-w/2,y-w/2,x+w/2,y+w/2],fill=(*CREAM,255))
    # round the arc ends
    for a in (-60,240):
        x=c+r*math.cos(math.radians(a)); y=c+S*0.03+r*math.sin(math.radians(a)); d.ellipse([x-w/2,y-w/2,x+w/2,y+w/2],fill=(*CREAM,255))
    return finish(im,size)
def icon_reboot(size):
    im=canvas(size); d=ImageDraw.Draw(im); S=size*SS; c=S/2; r=S*0.30; w=stroke(size)
    d.arc([c-r,c-r,c+r,c+r],-40,270,fill=(*CREAM,255),width=w)
    a=math.radians(-40); x=c+r*math.cos(a); y=c+r*math.sin(a)
    h=S*0.17; d.polygon([(x-h*0.1,y-h*1.0),(x+h*1.25,y+h*0.25),(x-h*0.85,y+h*0.45)],fill=(*CREAM,255))
    return finish(im,size)
def icon_firmware(size):
    im=canvas(size); d=ImageDraw.Draw(im); S=size*SS; c=S/2; w=stroke(size); b=S*0.23
    d.rounded_rectangle([c-b,c-b,c+b,c+b],S*0.05,outline=(*CREAM,255),width=w)
    q=S*0.10; d.rectangle([c-q,c-q,c+q,c+q],fill=(*CREAM,255))
    for k in (-0.11,0.11):
        for sgn in (-1,1):
            d.line([c+k*S,c+sgn*b,c+k*S,c+sgn*(b+S*0.12)],fill=(*CREAM,255),width=w)
            d.line([c+sgn*b,c+k*S,c+sgn*(b+S*0.12),c+k*S],fill=(*CREAM,255),width=w)
    return finish(im,size)
def icon_about(size):
    im=canvas(size); d=ImageDraw.Draw(im); S=size*SS; c=S/2; r=S*0.34; w=stroke(size)
    d.ellipse([c-r,c-r,c+r,c+r],outline=(*CREAM,255),width=w)
    d.line([c,c-S*0.02,c,c+S*0.16],fill=(*CREAM,255),width=w); d.ellipse([c-w*0.6,c-S*0.16-w*0.6,c+w*0.6,c-S*0.16+w*0.6],fill=(*CREAM,255))
    return finish(im,size)
def icon_arrow(size,left):
    im=canvas(size); d=ImageDraw.Draw(im); S=size*SS; w=stroke(size)
    x0,x1=(S*0.62,S*0.36) if left else (S*0.38,S*0.64)
    d.line([x0,S*0.26,x1,S*0.5,x0,S*0.74],fill=(*CREAM,255),width=w,joint='curve')
    return finish(im,size)
icon_power(SMALL).save(T+'icons/func_shutdown.png'); icon_reboot(SMALL).save(T+'icons/func_reset.png')
icon_firmware(SMALL).save(T+'icons/func_firmware.png'); icon_about(SMALL).save(T+'icons/func_about.png')
icon_arrow(48,True).save(T+'icons/arrow_left.png'); icon_arrow(48,False).save(T+'icons/arrow_right.png')

# ---------- font: 96 fixed cells (ASCII 32..126 + fallback box), gray+alpha, black glyphs ----------
FH=36; FW=21; size=34
font=ImageFont.truetype('/usr/share/fonts/noto/NotoSansMono-Regular.ttf',size)
strip=Image.new('L',(FW*96,FH),0); d=ImageDraw.Draw(strip)
asc,desc=font.getmetrics()
for i in range(95):
    ch=chr(32+i); w=font.getlength(ch); d.text((i*FW+(FW-w)/2,(FH-asc-desc)/2+1),ch,font=font,fill=255)
d.rectangle([95*FW+3,6,95*FW+FW-4,FH-8],outline=255,width=2)
la=Image.merge('LA',(Image.new('L',strip.size,0),strip)); la.save(T+'font.png')
print('tiles',TILE_BIG,TILE_SMALL,'icon offset',icx,icy)
