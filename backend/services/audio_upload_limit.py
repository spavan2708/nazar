import re

from starlette.middleware.body_limit import RequestBodyLimitMiddleware
from starlette.types import ASGIApp, Receive, Scope, Send

from services.audio_analysis import MAX_AUDIO_BYTES


class AudioUploadLimitMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app
        self.limited = RequestBodyLimitMiddleware(app, max_body_size=MAX_AUDIO_BYTES + 64 * 1024)

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        app = self.limited if scope["type"] == "http" and (scope["path"].rstrip("/") == "/api/analyze/audio" or re.fullmatch(r"/api/campaigns/[^/]+/evidence/audio/?", scope["path"])) else self.app
        await app(scope, receive, send)
