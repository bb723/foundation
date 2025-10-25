"""
Authentication module for Foundation package.

Provides Microsoft SSO authentication and login decorators.
"""

from foundation.auth.microsoft import MicrosoftAuth, MSALConfig, login_required

__all__ = ['MicrosoftAuth', 'MSALConfig', 'login_required']
