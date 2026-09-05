"""Disposable decoder process: one bounded image, bounded output, no file writes."""
import json,sys
import cv2
import numpy as np
cv2.setNumThreads(1)
data=sys.stdin.buffer.read(8*1024*1024+1)
if len(data)>8*1024*1024:raise ValueError('Oversized image')
image=cv2.imdecode(np.frombuffer(data,dtype=np.uint8),cv2.IMREAD_COLOR)
if image is None or image.shape[0]*image.shape[1]>1600*1600:raise ValueError('Invalid dimensions')
ok,decoded,_,_=cv2.QRCodeDetector().detectAndDecodeMulti(image)
print(json.dumps(list(dict.fromkeys(x for x in decoded if x and len(x)<=4096))[:4] if ok else []))
