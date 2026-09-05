"""Bound JSON before parsing, including streamed requests without Content-Length."""
from starlette.middleware.body_limit import RequestBodyLimitMiddleware
from services.limits import MAX_JSON_BYTES

class JSONBodyLimitMiddleware:
    def __init__(self,app):
        self.app=app
        self.limited=RequestBodyLimitMiddleware(app,max_body_size=MAX_JSON_BYTES)
    async def __call__(self,scope,receive,send):
        media=scope.get('path','').rstrip('/').endswith(('/image','/audio'))
        app=self.limited if scope['type']=='http' and not media else self.app
        await app(scope,receive,send)
