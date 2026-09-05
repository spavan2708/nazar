"""Reproducible local end-to-end probe. Reports misses; never edits labels/rules."""
import argparse,io,json,math,os,time
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient
from PIL import Image,ImageDraw,ImageFont
from main import app
from ml.dataset import load_split
from ml.noise import variants
from schemas.semantic import SemanticAnalysis


def run(output):
    if output.exists():raise FileExistsError('Use a fresh output file')
    cases=[];client=TestClient(app)
    # Every frozen test row, unchanged. OCR/STT noise stays paired to its parent.
    with patch('services.analysis_service.analyze_semantics',return_value=SemanticAnalysis(available=False)):
        for row in load_split('test'):
            for modality,text in [('text',row['text']),('ocr_like',variants(row['text'])['ocr_character']),('stt_like',variants(row['text'])['stt_homophone'])]:
                started=time.perf_counter();response=client.post('/api/analyze/text',json={'text':text});data=response.json()
                valid=response.status_code==200 and 0<=data.get('score',-1)<=100 and bool(data.get('explanation')) and bool(data.get('recommended_action'))
                cases.append(dict(id=row['id'],modality=modality,label=row['label'],language=row['language'],category=row['category'],status=response.status_code,
                    valid_contract=valid,score=data.get('score'),signals=data.get('signals'),grounding_topics=[t for r in (data.get('grounding') or {}).get('results',[]) for t in r['topics']],
                    warning_matches_label=(data.get('score',0)>=30)==(row['label']=='scam'),latency_ms=round((time.perf_counter()-started)*1000,2),analysis=data))
        adversarial=[]
        for row in json.loads((Path(__file__).parent/'hardening/adversarial_cases.json').read_text()):
            r=client.post('/api/analyze/text',json={'text':row['text']});data=r.json()
            adversarial.append(dict(**row,status=r.status_code,analysis=data,
                warning_matches_label=(data.get('score',0)>=30)==(row['label']=='scam')))
        urls=[]
        for value in ['http://192.0.2.1:8080/login/verify/account','https://example.org','https://xn--pple-43d.example','https://bit.ly/example','javascript:alert(1)']:
            r=client.post('/api/analyze/url',json={'url':value});urls.append(dict(input=value,status=r.status_code,result=r.json()))
        c=client.post('/api/campaigns').json();sequence=[]
        for text in ['I am a bank official. Verify your identity now.','Install AnyDesk and allow me to control your phone.','Send me your OTP immediately.','I need it really quick.']:
            r=client.post(f"/api/campaigns/{c['campaign_id']}/evidence/text",json={'text':text});sequence.append(r.json())
        image=Image.new('RGB',(900,150),'white');draw=ImageDraw.Draw(image)
        font=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf',28) if Path('/System/Library/Fonts/Supplemental/Arial.ttf').exists() else ImageFont.load_default(size=28)
        draw.text((20,40),'Send me your OTP immediately.',font=font,fill='black');blob=io.BytesIO();image.save(blob,format='PNG')
        r=client.post('/api/analyze/image',files={'file':('fixture.png',blob.getvalue(),'image/png')});screenshot=dict(status=r.status_code,result=r.json(),fixture='Locally rendered synthetic text')
        # A real encoded WAV exercises decode/temp cleanup. Stub only STT semantics,
        # whose accuracy needs human-labelled recordings, not generated waveforms.
        import wave,array
        pcm=array.array('h',(int(4000*math.sin(2*math.pi*440*i/16000)) for i in range(16000)))
        audio=io.BytesIO()
        with wave.open(audio,'wb') as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(16000);w.writeframes(pcm.tobytes())
        with patch('services.audio_analysis.transcribe_audio',return_value=('Send your password to me.','en')):
            r=client.post('/api/analyze/audio',files={'file':('fixture.wav',audio.getvalue(),'audio/wav')})
            recording=dict(status=r.status_code,result=r.json(),stt='stubbed transcript; real WAV decode; not speech accuracy')
    report=dict(cases=cases,adversarial=adversarial,urls=urls,investigation=sequence,screenshot=screenshot,audio=recording,
        summary=dict(cases=len(cases),valid_contracts=sum(x['valid_contract'] for x in cases),label_agreement=sum(x['warning_matches_label'] for x in cases)),
        limitations=['No live LLM calls','Guidance topics reported for review, not automatically certified relevant','UI rendering is checked separately','Scam stage labels describe requests, not successful attacks'])
    output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report['summary']))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);run(p.parse_args().output)
