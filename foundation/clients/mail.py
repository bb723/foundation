import os
import base64
import requests
import unicodedata
from typing import Optional, Dict, List
from datetime import datetime

import pandas as pd
class AttachmentNotFoundError(Exception):
    """Custom exception raised when no attachment is found."""
    pass

class IncorrectFileFormatError(Exception):
    """Custom exception raised when the file format is not as expected."""
    pass

class MailClient:
    def __init__(self):
        self.tenant_id = os.getenv("MS_TENANT_ID")
        self.client_id = os.getenv("MS_CLIENT_ID")
        self.client_secret = os.getenv("MS_CLIENT_SECRET")
        self._access_token = None
        self.default_style = """
            .styled-table {
                border-collapse: collapse;
                margin: 25px 0;
                font-size: 0.9em;
                font-family: sans-serif;
                min-width: 400px;
                box-shadow: 0 0 20px rgba(0, 0, 0, 0.1);
            }
            .styled-table th, .styled-table td {
                padding: 12px 15px;
                border: 1px solid #dddddd;
                text-align: left;
            }
            .styled-table thead tr {
                background-color: #009879;
                color: #ffffff;
                text-align: left;
            }
            .styled-table tbody tr {
                border-bottom: 1px solid #dddddd;
            }
            .styled-table tbody tr:nth-of-type(even) {
                background-color: #f3f3f3;
            }
            .styled-table tbody tr:last-of-type {
                border-bottom: 2px solid #009879;
            }
        """
        
    def get_access_token(self) -> Optional[str]:
        if self._access_token:
            return self._access_token
            
        token_url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "client_credentials",
            "scope": "https://graph.microsoft.com/.default"
        }
        
        response = requests.post(token_url, data=payload)
        if response.status_code == 200:
            self._access_token = response.json().get("access_token")
            return self._access_token
        return None

    def get_headers(self) -> Dict:
        token = self.get_access_token()
        if not token:
            raise Exception("Failed to get access token")
        return {"Authorization": f"Bearer {token}"}

    def list_messages(self, user_email: str, top: int = 5) -> List[Dict]:
        """List recent emails from a user's mailbox"""
        url = f"https://graph.microsoft.com/v1.0/users/{user_email}/messages"
        params = {
            "$top": top,
            "$select": "subject,receivedDateTime,from,isRead",
            "$orderby": "receivedDateTime desc"
        }
        
        response = requests.get(url, headers=self.get_headers(), params=params)
        if response.status_code == 200:
            return response.json().get('value', [])
        print(f"Error: {response.status_code}")
        print(response.text)
        return []

    def _normalize_string(self, s: str) -> str:
        """Normalize a string to handle Unicode differences"""
        return unicodedata.normalize('NFKD', s)

    def fetch_emails_with_subject(
        self, 
        user_email: str,
        subject: str, 
        download_dir: str = 'downloads', 
        expected_file_extension: str = ".csv"
    ) -> Optional[str]:
        """
        Retrieve today's emails with the specified subject and download attachments.
        """
        print(f"\nStarting email fetch for {user_email}")
        print(f"Looking for subject: {subject}")
        
        # Ensure download directory exists
        if not os.path.exists(download_dir):
            os.makedirs(download_dir)
            print(f"Created download directory: {download_dir}")

        # Format today's date for the query (Graph API format)
        today = datetime.now().strftime("%Y-%m-%dT00:00:00Z")
        print(f"Searching for emails from: {today}")
        
        # Query for emails
        url = f"https://graph.microsoft.com/v1.0/users/{user_email}/messages"
        params = {
            "$filter": f"receivedDateTime ge {today}",  # First get all today's emails
            "$select": "id,subject,hasAttachments,receivedDateTime",
            "$top": 50  # Increased to ensure we don't miss any
        }
        
        print("Fetching messages...")
        response = requests.get(url, headers=self.get_headers(), params=params)
        print(f"Response status code: {response.status_code}")
        
        if response.status_code != 200:
            print(f"Error querying messages: {response.status_code}")
            print(f"Error details: {response.text}")
            return None

        messages = response.json().get('value', [])
        print(f"Found {len(messages)} messages from today")

        if not messages:
            print("No messages found for today")
            return None

        # Filter messages by subject on our side (more reliable than Graph API subject filter)
        matching_messages = []
        for message in messages:
            print(f"\nChecking message: {message.get('subject')} ({message.get('receivedDateTime')})")
            normalized_subject = self._normalize_string(subject).strip().lower()
            normalized_msg_subject = self._normalize_string(message['subject']).strip().lower()
            
            if normalized_subject == normalized_msg_subject:
                print("√ Subject matches!")
                matching_messages.append(message)
            else:
                print(f"× Subject mismatch: '{message['subject']}' != '{subject}'")

        if not matching_messages:
            print("No matching subjects found")
            return None

        print(f"\nFound {len(matching_messages)} messages with matching subject")
        
        # Process matching messages
        for message in matching_messages:
            if not message.get('hasAttachments'):
                print(f"Message {message['id']} has no attachments")
                continue
                
            print(f"Checking attachments for message {message['id']}")
            attachments_url = f"https://graph.microsoft.com/v1.0/users/{user_email}/messages/{message['id']}/attachments"
            attachments_response = requests.get(attachments_url, headers=self.get_headers())
            
            if attachments_response.status_code != 200:
                print(f"Error getting attachments: {attachments_response.status_code}")
                print(attachments_response.text)
                continue

            attachments = attachments_response.json().get('value', [])
            print(f"Found {len(attachments)} attachments")
            
            for attachment in attachments:
                filename = attachment.get('name', '')
                print(f"Checking attachment: {filename}")
                
                if filename.endswith(expected_file_extension):
                    print(f"Found matching attachment: {filename}")
                    
                    try:
                        # Decode and save the attachment
                        file_data = base64.b64decode(attachment['contentBytes'])
                        file_path = os.path.join(download_dir, filename)
                        
                        with open(file_path, 'wb') as f:
                            f.write(file_data)
                            
                        print(f"Attachment '{filename}' downloaded successfully to {file_path}")
                        return file_path
                    except Exception as e:
                        print(f"Error saving attachment: {str(e)}")
                else:
                    print(f"Attachment {filename} doesn't match expected extension {expected_file_extension}")

        print("No matching attachments found")
        return None
    def send_html_email(
        self,
        to: str,
        subject: str,
        html_content: str,
        user_email: str = "bbrockway@standardmanagementco.com"
    ) -> bool:
        """
        Send an HTML formatted email through Microsoft Graph API.
        
        Args:
            to: Comma-separated list of recipients
            subject: Email subject
            html_content: HTML content of the email
            user_email: Email address to send from
        """
        print(f"Sending email to: {to}")
        
        # Format recipients list
        recipients = [
            {"emailAddress": {"address": email.strip()}}
            for email in to.split(',')
        ]

        message = {
            "message": {
                "subject": subject,
                "body": {
                    "contentType": "HTML",
                    "content": html_content
                },
                "toRecipients": recipients
            }
        }

        url = f"https://graph.microsoft.com/v1.0/users/{user_email}/sendMail"
        
        try:
            response = requests.post(
                url,
                headers=self.get_headers(),
                json=message
            )
            
            if response.status_code == 202:
                print("✓ Email sent successfully")
                return True
            else:
                print(f"✗ Failed to send email: {response.status_code}")
                print(response.text)
                return False
                
        except Exception as e:
            print(f"✗ Error sending email: {str(e)}")
            return False

    def create_html_table(self, df: pd.DataFrame, custom_style: Optional[str] = None) -> str:
        """Convert DataFrame to styled HTML table"""
        if df is None or df.empty:
            return "<p>No data available.</p>"
        
        style = custom_style if custom_style else self.default_style
        html_table = df.to_html(index=False, classes='styled-table', border=0)
        
        return f"""
        <html>
        <head>
            <style>
                {style}
            </style>
        </head>
        <body>
            {html_table}
        </body>
        </html>
        """
    import os
import base64
import requests
import unicodedata
from typing import Optional, Dict, List
from datetime import datetime

class AttachmentNotFoundError(Exception):
    """Custom exception raised when no attachment is found."""
    pass

class IncorrectFileFormatError(Exception):
    """Custom exception raised when the file format is not as expected."""
    pass

class MailClient:
    def __init__(self):
        self.tenant_id = os.getenv("MS_TENANT_ID")
        self.client_id = os.getenv("MS_CLIENT_ID")
        self.client_secret = os.getenv("MS_CLIENT_SECRET")
        self._access_token = None
        self.default_style = """
            .styled-table {
                border-collapse: collapse;
                margin: 25px 0;
                font-size: 0.9em;
                font-family: sans-serif;
                min-width: 400px;
                box-shadow: 0 0 20px rgba(0, 0, 0, 0.1);
            }
            .styled-table th, .styled-table td {
                padding: 12px 15px;
                border: 1px solid #dddddd;
                text-align: left;
            }
            .styled-table thead tr {
                background-color: #009879;
                color: #ffffff;
                text-align: left;
            }
            .styled-table tbody tr {
                border-bottom: 1px solid #dddddd;
            }
            .styled-table tbody tr:nth-of-type(even) {
                background-color: #f3f3f3;
            }
            .styled-table tbody tr:last-of-type {
                border-bottom: 2px solid #009879;
            }
        """
        
    def get_access_token(self) -> Optional[str]:
        if self._access_token:
            return self._access_token
            
        token_url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "client_credentials",
            "scope": "https://graph.microsoft.com/.default"
        }
        
        response = requests.post(token_url, data=payload)
        if response.status_code == 200:
            self._access_token = response.json().get("access_token")
            return self._access_token
        return None

    def get_headers(self) -> Dict:
        token = self.get_access_token()
        if not token:
            raise Exception("Failed to get access token")
        return {"Authorization": f"Bearer {token}"}

    def list_messages(self, user_email: str, top: int = 5) -> List[Dict]:
        """List recent emails from a user's mailbox"""
        url = f"https://graph.microsoft.com/v1.0/users/{user_email}/messages"
        params = {
            "$top": top,
            "$select": "subject,receivedDateTime,from,isRead",
            "$orderby": "receivedDateTime desc"
        }
        
        response = requests.get(url, headers=self.get_headers(), params=params)
        if response.status_code == 200:
            return response.json().get('value', [])
        print(f"Error: {response.status_code}")
        print(response.text)
        return []

    def _normalize_string(self, s: str) -> str:
        """Normalize a string to handle Unicode differences"""
        return unicodedata.normalize('NFKD', s)

    def fetch_emails_with_subject(
        self, 
        user_email: str,
        subject: str, 
        download_dir: str = 'downloads', 
        expected_file_extension: str = ".csv"
    ) -> Optional[str]:
        """
        Retrieve today's emails with the specified subject and download attachments.
        """
        print(f"\nStarting email fetch for {user_email}")
        print(f"Looking for subject: {subject}")
        
        # Ensure download directory exists
        if not os.path.exists(download_dir):
            os.makedirs(download_dir)
            print(f"Created download directory: {download_dir}")

        # Format today's date for the query (Graph API format)
        today = datetime.now().strftime("%Y-%m-%dT00:00:00Z")
        print(f"Searching for emails from: {today}")
        
        # Query for emails
        url = f"https://graph.microsoft.com/v1.0/users/{user_email}/messages"
        params = {
            "$filter": f"receivedDateTime ge {today}",  # First get all today's emails
            "$select": "id,subject,hasAttachments,receivedDateTime",
            "$top": 50  # Increased to ensure we don't miss any
        }
        
        print("Fetching messages...")
        response = requests.get(url, headers=self.get_headers(), params=params)
        print(f"Response status code: {response.status_code}")
        
        if response.status_code != 200:
            print(f"Error querying messages: {response.status_code}")
            print(f"Error details: {response.text}")
            return None

        messages = response.json().get('value', [])
        print(f"Found {len(messages)} messages from today")

        if not messages:
            print("No messages found for today")
            return None

        # Filter messages by subject on our side (more reliable than Graph API subject filter)
        matching_messages = []
        for message in messages:
            print(f"\nChecking message: {message.get('subject')} ({message.get('receivedDateTime')})")
            normalized_subject = self._normalize_string(subject).strip().lower()
            normalized_msg_subject = self._normalize_string(message['subject']).strip().lower()
            
            if normalized_subject == normalized_msg_subject:
                print("√ Subject matches!")
                matching_messages.append(message)
            else:
                print(f"× Subject mismatch: '{message['subject']}' != '{subject}'")

        if not matching_messages:
            print("No matching subjects found")
            return None

        print(f"\nFound {len(matching_messages)} messages with matching subject")
        
        # Process matching messages
        for message in matching_messages:
            if not message.get('hasAttachments'):
                print(f"Message {message['id']} has no attachments")
                continue
                
            print(f"Checking attachments for message {message['id']}")
            attachments_url = f"https://graph.microsoft.com/v1.0/users/{user_email}/messages/{message['id']}/attachments"
            attachments_response = requests.get(attachments_url, headers=self.get_headers())
            
            if attachments_response.status_code != 200:
                print(f"Error getting attachments: {attachments_response.status_code}")
                print(attachments_response.text)
                continue

            attachments = attachments_response.json().get('value', [])
            print(f"Found {len(attachments)} attachments")
            
            for attachment in attachments:
                filename = attachment.get('name', '')
                print(f"Checking attachment: {filename}")
                
                if filename.endswith(expected_file_extension):
                    print(f"Found matching attachment: {filename}")
                    
                    try:
                        # Decode and save the attachment
                        file_data = base64.b64decode(attachment['contentBytes'])
                        file_path = os.path.join(download_dir, filename)
                        
                        with open(file_path, 'wb') as f:
                            f.write(file_data)
                            
                        print(f"Attachment '{filename}' downloaded successfully to {file_path}")
                        return file_path
                    except Exception as e:
                        print(f"Error saving attachment: {str(e)}")
                else:
                    print(f"Attachment {filename} doesn't match expected extension {expected_file_extension}")

        print("No matching attachments found")
        return None
    def send_html_email(
        self,
        to: str,
        subject: str,
        html_content: str,
        user_email: str = "bbrockway@standardmanagementco.com"
    ) -> bool:
        """
        Send an HTML formatted email through Microsoft Graph API.
        
        Args:
            to: Comma-separated list of recipients
            subject: Email subject
            html_content: HTML content of the email
            user_email: Email address to send from
        """
        print(f"Sending email to: {to}")
        
        # Format recipients list
        recipients = [
            {"emailAddress": {"address": email.strip()}}
            for email in to.split(',')
        ]

        message = {
            "message": {
                "subject": subject,
                "body": {
                    "contentType": "HTML",
                    "content": html_content
                },
                "toRecipients": recipients
            }
        }

        url = f"https://graph.microsoft.com/v1.0/users/{user_email}/sendMail"
        
        try:
            response = requests.post(
                url,
                headers=self.get_headers(),
                json=message
            )
            
            if response.status_code == 202:
                print("✓ Email sent successfully")
                return True
            else:
                print(f"✗ Failed to send email: {response.status_code}")
                print(response.text)
                return False
                
        except Exception as e:
            print(f"✗ Error sending email: {str(e)}")
            return False

    def create_html_table(self, df: pd.DataFrame, custom_style: Optional[str] = None) -> str:
        """Convert DataFrame to styled HTML table"""
        if df is None or df.empty:
            return "<p>No data available.</p>"
        
        style = custom_style if custom_style else self.default_style
        html_table = df.to_html(index=False, classes='styled-table', border=0)
        
        return f"""
        <html>
        <head>
            <style>
                {style}
            </style>
        </head>
        <body>
            {html_table}
        </body>
        </html>
        """
    def send_query_report(
        self,
        query_result: pd.DataFrame,
        to: str,
        subject: str,
        custom_style: Optional[str] = None,
        error_message: Optional[str] = None,
        user_email: str = "bbrockway@standardmanagementco.com"
    ) -> bool:
        """
        Format and send a query result as an HTML email report
        
        Args:
            query_result: DataFrame containing query results
            to: Comma-separated list of recipients
            subject: Email subject
            custom_style: Optional custom CSS styling
            error_message: Optional error message if query failed
            user_email: Email address to send from
        """
        try:
            if error_message:
                html_content = f"""
                <html>
                <body>
                    <h2>An error occurred while generating the report:</h2>
                    <p><strong>Error Details:</strong> {error_message}</p>
                    <p>Please check the query and permissions.</p>
                </body>
                </html>
                """
            else:
                html_content = self.create_html_table(query_result, custom_style)

            # Format recipients list
            recipients = [
                {"emailAddress": {"address": email.strip()}}
                for email in to.split(',')
            ]

            message = {
                "message": {
                    "subject": subject,
                    "body": {
                        "contentType": "HTML",
                        "content": html_content
                    },
                    "toRecipients": recipients
                }
            }

            url = f"https://graph.microsoft.com/v1.0/users/{user_email}/sendMail"
            
            response = requests.post(
                url,
                headers=self.get_headers(),
                json=message
            )
            
            if response.status_code == 202:
                print(f"✓ Report '{subject}' sent successfully")
                return True
            else:
                print(f"✗ Failed to send report: {response.status_code}")
                print(response.text)
                return False
                
        except Exception as e:
            print(f"✗ Error sending report: {str(e)}")
            return False

def test_connection(user_email: str) -> bool:
    """Test the connection to Microsoft Graph API"""
    try:
        client = MailClient()
        print("Testing connection...")
        messages = client.list_messages(user_email, top=1)
        if messages:
            print("✓ Connection successful!")
            return True
        else:
            print("✗ Connection failed - no messages retrieved")
            return False
    except Exception as e:
        print(f"✗ Connection failed with error: {str(e)}")
        return False
    
def test_connection(user_email: str) -> bool:
    """Test the connection to Microsoft Graph API"""
    try:
        client = MailClient()
        print("Testing connection...")
        messages = client.list_messages(user_email, top=1)
        if messages:
            print("✓ Connection successful!")
            return True
        else:
            print("✗ Connection failed - no messages retrieved")
            return False
    except Exception as e:
        print(f"✗ Connection failed with error: {str(e)}")
        return False