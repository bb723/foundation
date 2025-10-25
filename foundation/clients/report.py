# foundation/clients/report.py
from typing import Optional
from foundation.clients.mail import MailClient
from foundation.clients.snowflake import SnowflakeClient

class ReportClient:
    """Client for handling report generation and distribution"""
    
    def __init__(self):
        self.snow_client = SnowflakeClient()
        self.mail_client = MailClient()

    def test_connections(self) -> bool:
        """Test both Snowflake and Mail connections"""
        try:
            # Test Snowflake
            snow_success = self.snow_client.test_connection()
            if not snow_success:
                print("Failed to connect to Snowflake")
                return False

            # Test Mail (just try to get access token)
            token = self.mail_client.get_access_token()
            mail_success = token is not None
            if not mail_success:
                print("Failed to connect to Mail service")
                return False

            print("✓ All connections tested successfully")
            return True

        except Exception as e:
            print(f"Error testing connections: {str(e)}")
            return False

    def send_report(
        self,
        query: str,
        recipients: str,
        subject: Optional[str] = None,
        custom_style: Optional[str] = None
    ) -> bool:
        """
        Generate and send a report via email
        
        Args:
            query: SQL query to execute
            recipients: Comma-separated list of email addresses
            subject: Optional email subject
            custom_style: Optional custom CSS styling
        """
        try:
            # Execute query
            df = self.snow_client.execute_query(query)
            
            if df is None or df.empty:
                print(f"No data returned for query")
                return False
            
            # Send report
            success = self.mail_client.send_query_report(
                query_result=df,
                to=recipients,
                subject=subject or "Report",
                custom_style=custom_style
            )
            
            return success
            
        except Exception as e:
            print(f"Error generating/sending report: {str(e)}")
            return False
