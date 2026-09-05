import re

from starlette.middleware.body_limit import RequestBodyLimitMiddleware
from starlette.types import ASGIApp, Receive, Scope, Send

from services.image_analysis import MAX_IMAGE_BYTES


class ImageUploadLimitMiddleware:
    """Bound multipart parsing for images without changing other API routes."""
    def __init__(self, app: ASGIApp):
        self.app = app
        self.limited = RequestBodyLimitMiddleware(app, max_body_size=MAX_IMAGE_BYTES + 64 * 1024)

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        app = self.limited if scope["type"] == "http" and (scope["path"].rstrip("/") == "/api/analyze/image" or re.fullmatch(r"/api/campaigns/[^/]+/evidence/image/?", scope["path"])) else self.app
        await app(scope, receive, send)
