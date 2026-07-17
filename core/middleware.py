from rest_framework_simplejwt.tokens import AccessToken
from accounts.models import User
from urllib.parse import parse_qs
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser


class JWTAuthMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        bytes_data = scope['query_string']
        text_data = bytes_data.decode()
        query_params = parse_qs(text_data)

        try:
            token = query_params['token'][0]
            token_obj = AccessToken(token)
            user_id = token_obj['user_id']
            user = await database_sync_to_async(User.objects.get)(id=user_id)
        except Exception:
            user = AnonymousUser()

        scope['user'] = user
        return await self.app(scope, receive, send)