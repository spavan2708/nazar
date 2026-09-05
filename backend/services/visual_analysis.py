"""Optional local QR extraction. No browsing, payment actions or identity claims."""
import io,json,os,re,subprocess,sys
from pathlib import Path
from urllib.parse import urlsplit,parse_qsl
from decimal import Decimal,InvalidOperation
from pydantic import BaseModel,Field
from typing import Literal
from services.url_intelligence import analyze_url,InvalidURL
from schemas.url import URLAnalysis

class QRContent(BaseModel):
    kind: Literal['url','payment','unsupported','invalid']
    url: URLAnalysis | None = None
    payee: str | None = None
    amount: str | None = None
    explanation: str

class VisualEvidence(BaseModel):
    available: bool = False
    engine: str = 'opencv-qr'
    qr_codes: list[QRContent] = Field(default_factory=list,max_length=4)
    limitation: str = 'QR extraction only. No visual brand, sender identity or scam classification.'


def parse_payload(raw):
    if not isinstance(raw,str) or len(raw)>4096 or any(ord(c)<32 for c in raw):
        return QRContent(kind='invalid',explanation='QR payload exceeds supported limits.')
    try:
        parts=urlsplit(raw)
        if parts.scheme.lower() in ('http','https'):
            return QRContent(kind='url',url=analyze_url(raw),explanation='QR destination inspected offline; it was not opened.')
        if parts.scheme.lower()=='upi' and parts.netloc=='pay' and parts.path in ('','/') and not parts.fragment:
            pairs=parse_qsl(parts.query,keep_blank_values=True,max_num_fields=20)
            if len({k for k,v in pairs})!=len(pairs):raise ValueError()
            values=dict(pairs);payee=values.get('pa','')
            if not re.fullmatch(r'[A-Za-z0-9._-]{1,128}@[A-Za-z0-9.-]{1,64}',payee):raise ValueError()
            amount=values.get('am')
            if amount is not None:
                if not re.fullmatch(r'\d{1,9}(?:\.\d{1,2})?',amount) or Decimal(amount)<=0:raise ValueError()
            if values.get('cu','INR')!='INR':raise ValueError()
            return QRContent(kind='payment',payee=payee,amount=amount,explanation='Payment instruction, not proof of fraud. Confirm recipient and amount independently. Receiving money does not require an outgoing payment.')
    except (ValueError,InvalidOperation,InvalidURL):
        return QRContent(kind='invalid',explanation='QR content could not be safely interpreted.')
    return QRContent(kind='unsupported',explanation='Unsupported QR content; no action was taken.')


def analyze_visual(image):
    if os.getenv('QR_ENABLED','false').lower()!='true':return VisualEvidence()
    import importlib.util
    if importlib.util.find_spec('cv2') is None:return VisualEvidence()
    try:
        image=image.copy();image.thumbnail((1600,1600));data=io.BytesIO();image.save(data,format='PNG');image.close()
        worker=Path(__file__).with_name('qr_worker.py')
        result=subprocess.run([sys.executable,str(worker)],input=data.getvalue(),stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,timeout=8,check=True)
        if len(result.stdout)>20000:raise ValueError()
        payloads=json.loads(result.stdout)
        if not isinstance(payloads,list) or len(payloads)>4:raise ValueError()
        return VisualEvidence(available=True,qr_codes=[parse_payload(x) for x in payloads])
    except (ValueError,OSError,subprocess.SubprocessError):return VisualEvidence()
