# foundation/clients/teams.py
import os
import requests
from datetime import datetime
from typing import Optional, Dict, List

class TeamsClient:
    def __init__(self):
        self.tenant_id = os.getenv("MS_TENANT_ID")
        self.client_id = os.getenv("MS_CLIENT_ID")
        self.client_secret = os.getenv("MS_CLIENT_SECRET")
        self._access_token = None
        
    def get_access_token(self) -> Optional[str]:
        """Get Microsoft Graph API access token"""
        if self._access_token:  # Add token caching/refresh logic here later
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
        """Get headers with access token"""
        token = self.get_access_token()
        if not token:
            raise Exception("Failed to get access token")
        return {"Authorization": f"Bearer {token}"}

    def get_channel_id(self, team_id: str, channel_name: str) -> Optional[str]:
        """Get channel ID by name"""
        url = f"https://graph.microsoft.com/v1.0/teams/{team_id}/channels"
        response = requests.get(url, headers=self.get_headers())
        
        if response.status_code == 200:
            channels = response.json().get('value', [])
            for channel in channels:
                if channel['displayName'].lower() == channel_name.lower():
                    return channel['id']
        return None

    def post_message(self, team_id: str, channel_name: str, message: str) -> bool:
        """Post message to Teams channel"""
        channel_id = self.get_channel_id(team_id, channel_name)
        if not channel_id:
            raise Exception(f"Channel '{channel_name}' not found")
            
        url = f"https://graph.microsoft.com/v1.0/teams/{team_id}/channels/{channel_id}/messages"
        payload = {
            "body": {
                "content": message
            }
        }
        
        response = requests.post(url, headers=self.get_headers(), json=payload)
        return response.status_code == 201
