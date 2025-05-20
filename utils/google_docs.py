#!/usr/bin/env python3

import os
import json
from typing import Dict, Optional
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

class GoogleDocsManager:
    """Manages Google Docs operations including authentication and document creation."""
    
    SCOPES = ['https://www.googleapis.com/auth/drive.file']
    
    def __init__(self, credentials_path: str = 'credentials.json', token_path: str = 'token.json'):
        """Initialize the Google Docs manager.
        
        Args:
            credentials_path: Path to the Google API credentials file
            token_path: Path to store the OAuth token
        """
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.creds = None
        self.service = None
        
    def authenticate(self) -> bool:
        """Authenticate with Google API.
        
        Returns:
            bool: True if authentication was successful, False otherwise
        """
        try:
            # Load existing token if available
            if os.path.exists(self.token_path):
                with open(self.token_path, 'r') as token:
                    self.creds = Credentials.from_authorized_user_info(
                        json.load(token), self.SCOPES)
            
            # Refresh token if expired
            if not self.creds or not self.creds.valid:
                if self.creds and self.creds.expired and self.creds.refresh_token:
                    self.creds.refresh(Request())
                else:
                    if not os.path.exists(self.credentials_path):
                        raise FileNotFoundError(
                            f"Credentials file not found at {self.credentials_path}. "
                            "Please download your credentials from Google Cloud Console."
                        )
                    
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_path, self.SCOPES)
                    self.creds = flow.run_local_server(port=0)
                
                # Save the token
                with open(self.token_path, 'w') as token:
                    token.write(self.creds.to_json())
            
            # Build the service
            self.service = build('docs', 'v1', credentials=self.creds)
            return True
            
        except Exception as e:
            print(f"Authentication failed: {str(e)}")
            return False
    
    def create_document(self, title: str, content: str) -> Optional[str]:
        """Create a new Google Doc with the given title and content.
        
        Args:
            title: The title of the document
            content: The content to add to the document
            
        Returns:
            Optional[str]: The ID of the created document if successful, None otherwise
        """
        if not self.service:
            if not self.authenticate():
                return None
        
        try:
            # Create a new document
            doc = self.service.documents().create(body={'title': title}).execute()
            doc_id = doc.get('documentId')
            
            # Prepare the content update
            requests = [
                {
                    'insertText': {
                        'location': {
                            'index': 1
                        },
                        'text': content
                    }
                }
            ]
            
            # Update the document with content
            self.service.documents().batchUpdate(
                documentId=doc_id,
                body={'requests': requests}
            ).execute()
            
            return doc_id
            
        except HttpError as error:
            print(f"An error occurred: {error}")
            return None
    
    def share_document(self, doc_id: str, email: str, role: str = 'reader') -> bool:
        """Share a Google Doc with a specific email address.
        
        Args:
            doc_id: The ID of the document to share
            email: The email address to share with
            role: The role to assign (reader, commenter, or writer)
            
        Returns:
            bool: True if sharing was successful, False otherwise
        """
        if not self.service:
            if not self.authenticate():
                return False
        
        try:
            # Create the permission
            permission = {
                'type': 'user',
                'role': role,
                'emailAddress': email
            }
            
            # Share the document
            drive_service = build('drive', 'v3', credentials=self.creds)
            drive_service.permissions().create(
                fileId=doc_id,
                body=permission,
                fields='id'
            ).execute()
            
            return True
            
        except HttpError as error:
            print(f"An error occurred while sharing: {error}")
            return False 