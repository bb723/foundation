"""
API Clients module for Foundation package.

Provides clients for QuickBooks, Snowflake, Teams, Email, and Reports.
"""

from foundation.clients.snowflake import SnowflakeClient
from foundation.clients.quickbooks import QuickBooksClient, QuickBooksAuthError
from foundation.clients.multi_tenant_quickbooks import MultiTenantQB, Companies
from foundation.clients.mail import MailClient
from foundation.clients.teams import TeamsClient
from foundation.clients.report import ReportClient

__all__ = [
    'SnowflakeClient',
    'QuickBooksClient',
    'QuickBooksAuthError',
    'MultiTenantQB',
    'Companies',
    'MailClient',
    'TeamsClient',
    'ReportClient',
]
