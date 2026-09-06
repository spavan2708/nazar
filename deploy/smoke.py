"""Live HTTP checks with harmless synthetic evidence. Run with backend's venv."""
import argparse
import io
import json
import re
from pathlib import Path

import httpx
from PIL import Image, ImageDraw, ImageFont


def run(url, output, audio=None):
    results = {}
    with httpx.Client(base_url=url.rstrip('/'), timeout=300, follow_redirects=True) as client:
        def check(name, action):
            try:
                results[name] = {"pass": True, "result": action()}
            except Exception as error:
                results[name] = {"pass": False, "error": str(error)}
            print(name, 'PASS' if results[name]['pass'] else 'FAIL', flush=True)
            output.write_text(json.dumps(results, indent=2, ensure_ascii=False))

        def request(path, payload=None, files=None):
            response = client.post(path, json=payload, files=files) if payload is not None or files else client.get(path)
            response.raise_for_status()
            return response.json()

        def homepage():
            response = client.get('/')
            response.raise_for_status()
            assert 'Nazar' in response.text
            assets = set(re.findall(r'(?:src|href)="([^\"]+/_next/[^\"]+|/_next/[^\"]+)"', response.text))
            assert assets, 'No Next.js assets found'
            for asset in assets:
                r = client.get(asset.replace('&amp;', '&'))
                r.raise_for_status()
                if '.js' in asset:
                    assert 'http://localhost:8000' not in r.text, 'Production client targets localhost'
            return {"status": response.status_code, "assets": len(assets)}

        check('frontend', homepage)
        check('health', lambda: request('/health'))

        def exposure():
            paths = ['/.env', '/backend/.env', '/backend/main.py', '/docs', '/openapi.json', '/backend/ml/artifacts/metadata.json']
            statuses = {path: client.get(path).status_code for path in paths}
            assert all(status == 404 for status in statuses.values()), statuses
            return statuses

        check('source_exposure', exposure)

        def message():
            data = request('/api/analyze/text', {'text': 'Send me your OTP immediately.'})
            assert data['score'] > 0
            assert data['ml']['available'], 'ML unavailable'
            assert data['grounding']['available'] and data['grounding']['results'], 'RAG unavailable'
            return data

        check('message_ml_rag', message)
        check('url', lambda: request('/api/analyze/url', {'url': 'https://example.org'}))

        def screenshot(qr=False, language='eng'):
            image = Image.new('RGB', (1000, 600), 'white')
            draw = ImageDraw.Draw(image)
            samples = {
                'eng': ('Arial.ttf', 'Send me your OTP immediately.', 'otp'),
                'hin': ('Devanagari Sangam MN.ttc', 'मुझे अपना ओटीपी भेजें', 'ओटीपी'),
                'tam': ('Tamil Sangam MN.ttc', 'உங்கள் கடவுச்சொல்லை அனுப்புங்கள்', 'கடவுச்சொல்'),
            }
            fontname, text, expected = samples[language]
            fontpath = Path('/System/Library/Fonts/Supplemental') / fontname
            font = ImageFont.truetype(str(fontpath), 32) if fontpath.exists() else ImageFont.load_default(size=32)
            draw.text((30, 30), text, fill='black', font=font)
            if qr:
                import cv2
                code = cv2.QRCodeEncoder_create().encode('https://example.org')
                code = cv2.copyMakeBorder(code, 4, 4, 4, 4, cv2.BORDER_CONSTANT, value=255)
                image.paste(Image.fromarray(code).resize((360, 360), Image.Resampling.NEAREST), (30, 150))
            stream = io.BytesIO()
            image.save(stream, format='PNG')
            data = request('/api/analyze/image', files={'file': ('synthetic.png', stream.getvalue(), 'image/png')})
            assert expected in data['extracted_text'].lower(), data['extracted_text']
            assert not data['ocr']['missing_languages'], data['ocr']
            if qr:
                assert data['visual']['available'] and data['visual']['qr_codes'], 'QR decode failed'
            return data

        check('ocr', screenshot)
        check('ocr_hindi', lambda: screenshot(language='hin'))
        check('ocr_tamil', lambda: screenshot(language='tam'))
        check('qr', lambda: screenshot(True))

        def investigation():
            response = client.post('/api/campaigns')
            response.raise_for_status()
            campaign = response.json()
            route = f"/api/campaigns/{campaign['campaign_id']}"
            data = request(route + '/evidence/text', {'text': 'Send me your OTP immediately.'})
            assert data['interactions']
            assert request(route)['campaign_id'] == campaign['campaign_id']
            return data

        check('investigations', investigation)
        # Invalid image bytes avoid expensive processing while probing platform ingress.
        boundary = client.post('/api/analyze/image', files={'file': ('boundary.png', b'x' * 4_900_000, 'image/png')})
        results['upload_boundary'] = {'pass': boundary.status_code in (413, 422),
                                      'result': {'bytes': 4_900_000, 'status': boundary.status_code}}
        output.write_text(json.dumps(results, indent=2, ensure_ascii=False))
        if audio:
            def recording():
                data = request('/api/analyze/audio', files={'file': ('synthetic.wav', audio.read_bytes(), 'audio/wav')})
                assert 'password' in data['transcript'].lower(), data['transcript']
                return data
            check('audio', recording)
    return all(item['pass'] for item in results.values())


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('url')
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--audio', type=Path)
    args = parser.parse_args()
    raise SystemExit(0 if run(args.url, args.output, args.audio) else 1)
