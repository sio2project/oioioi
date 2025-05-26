import aiohttp
import logging
from cachetools import TTLCache


class Auth:
    AUTH_CACHE_EXPIRATION_SECONDS = 300
    AUTH_CACHE_MAX_SIZE = 10000
    URL_AUTHENTICATE_SUFFIX = 'notifications/authenticate/'

    def __init__(self, url: str):
        self.auth_url = url + self.URL_AUTHENTICATE_SUFFIX
        self.auth_cache = TTLCache(
            maxsize=self.AUTH_CACHE_MAX_SIZE, ttl=self.AUTH_CACHE_EXPIRATION_SECONDS)
        self.logger = logging.getLogger('auth')
        self.http_client = None

    async def connect(self) -> None:
        self.http_client = aiohttp.ClientSession()

    async def authenticate(self, session_id: str) -> str:
        "Authenticate a user with session ID."

        if session_id in self.auth_cache:
            self.logger.info(f"Cache hit for session ID: {session_id}")
            return self.auth_cache[session_id]

        async with self.http_client.post(
            self.auth_url,
            data={'nsid': session_id},
            headers={'Content-Type': 'application/x-www-form-urlencoded'}
        ) as response:
            response.raise_for_status()
            result = await response.json()

            if result.get('status') != 'OK':
                raise RuntimeError(
                    "Authentication failed - server returned non-OK status")

            user_id = result.get('user', None)
            self.auth_cache[session_id] = user_id

            self.logger.info(f"Authenticated session ID: {session_id}")
            return user_id
