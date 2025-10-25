# foundation/auth/microsoft.py
import os
import msal
import logging
from functools import wraps
from flask import redirect, url_for, session, request

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class MSALConfig:
    """Microsoft Authentication Library configuration"""
    def __init__(self):
        self.client_id = os.environ.get('MS_CLIENT_ID')
        self.client_secret = os.environ.get('MS_CLIENT_SECRET')
        self.tenant_id = os.environ.get('MS_TENANT_ID')
        self.authority = f"https://login.microsoftonline.com/{self.tenant_id}"
        self.scope = ['User.Read']
        self.endpoint = 'https://graph.microsoft.com/v1.0/me'


class MicrosoftAuth:
    def __init__(self, config: MSALConfig = None):
        self.config = config or MSALConfig()

    def build_auth_flow(self):
        """Create MSAL confidential client application"""
        return msal.ConfidentialClientApplication(
            self.config.client_id,
            authority=self.config.authority,
            client_credential=self.config.client_secret
        )

    def get_auth_url(self, callback_url: str) -> str:
        """Generate authorization URL"""
        logger.debug(f"Generating auth URL with callback: {callback_url}")
        # Generate and store state in session
        session['state'] = os.urandom(16).hex()
        auth_url = self.build_auth_flow().get_authorization_request_url(
            scopes=self.config.scope,
            redirect_uri=callback_url,
            state=session['state']
        )
        logger.debug(f"Generated auth URL: {auth_url}")
        return auth_url

    def get_token_from_code(self, code: str, callback_url: str) -> dict:
        """Exchange authorization code for tokens"""
        logger.debug("Attempting to get token from code")
        logger.debug(f"Callback URL: {callback_url}")
        try:
            result = self.build_auth_flow().acquire_token_by_authorization_code(
                code,
                scopes=self.config.scope,
                redirect_uri=callback_url
            )
            if 'error' in result:
                logger.error(f"Error in token response: {result.get('error')}")
                logger.error(f"Error description: {result.get('error_description')}")
            else:
                logger.debug("Successfully acquired token")
            return result
        except Exception as e:
            logger.error(f"Exception in get_token_from_code: {str(e)}", exc_info=True)
            raise

    def get_logout_url(self, post_logout_redirect_uri: str) -> str:
        """Generate logout URL"""
        return (
            f"{self.config.authority}/oauth2/v2.0/logout"
            f"?post_logout_redirect_uri={post_logout_redirect_uri}"
        )


def login_required(f):
    """Decorator to protect routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user'):
            logger.debug("User not found in session, redirecting to login")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function
