import aiohttp
import logging
from typing import Dict, Optional, Any

class Auth:
    AUTH_CACHE_EXPIRATION_SECONDS = 300
    URL_AUTHENTICATE_SUFFIX = 'notifications/authenticate/'
    
    def __init__(self):
        self.logger = logging.getLogger('auth')
        self.auth_url = 'http://localhost:8000/' + self.URL_AUTHENTICATE_SUFFIX
        self.http_session = aiohttp.ClientSession()
    
    def authenticate(self, session_id: str) -> Optional[str]:
        "Authenticate a user with session ID."
        
        try:
            async with self.http_session.post(
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