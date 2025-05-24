import aiohttp
import logging
from typing import Dict, Optional, Any

class Auth:
    AUTH_CACHE_EXPIRATION_SECONDS = 300
    URL_AUTHENTICATE_SUFFIX = 'notifications/authenticate/'
    
    def __init__(self, url: str):
        self.auth_url = url + self.URL_AUTHENTICATE_SUFFIX
        self.logger = logging.getLogger('auth')
        
    async def connect(self) -> None:
        self.http_client = aiohttp.ClientSession()
    
    async def authenticate(self, session_id: str) -> Optional[str]:
        "Authenticate a user with session ID."
        
        try:
            async with self.http_client.post(
                self.auth_url,
                data={'nsid': session_id},
                headers={'Content-Type': 'application/x-www-form-urlencoded'}
            ) as response:
                if response.status != 200:
                    self.logger.error(f"Authentication request failed with status {response.status}")
                    return None
                    
                result = await response.json()
                
                if result.get('status') != 'OK':
                    self.logger.info("Authentication failed - server returned non-OK status")
                    return None
                    
                username = result.get('user')
                self.logger.debug(f"Authenticated user: {username}")
                
                return username
            
        except Exception as e:
            self.logger.error(f"Authentication error: {str(e)}")
            return None