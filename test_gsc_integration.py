import os
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import json
from datetime import datetime, timedelta

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/webmasters']

def get_credentials():
    """Gets valid user credentials from storage.
    
    If nothing has been stored, or if the stored credentials are invalid,
    the OAuth2 flow is completed to obtain the new credentials.
    """
    creds = None
    # The file token.json stores the user's access and refresh tokens
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    
    return creds

def test_gsc_connection():
    """Test the GSC API connection and fetch a small sample of data."""
    try:
        # Get credentials
        creds = get_credentials()
        
        # Build the service
        service = build('searchconsole', 'v1', credentials=creds)
        
        # Get site list
        sites = service.sites().list().execute()
        print("\nAvailable sites:")
        for site in sites.get('siteEntry', []):
            print(f"- {site['siteUrl']}")
        
        # Select the first site for testing
        if sites.get('siteEntry'):
            site_url = sites['siteEntry'][0]['siteUrl']
            print(f"\nTesting with site: {site_url}")
            
            # Get last 7 days of data
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=7)
            
            # Prepare the request
            request = {
                'startDate': start_date.isoformat(),
                'endDate': end_date.isoformat(),
                'dimensions': ['query'],
                'rowLimit': 5  # Just get 5 rows for testing
            }
            
            # Make the API call
            response = service.searchanalytics().query(
                siteUrl=site_url,
                body=request
            ).execute()
            
            print("\nSample data retrieved:")
            if 'rows' in response:
                for row in response['rows']:
                    print(f"- Query: {row['keys'][0]}")
                    print(f"  Clicks: {row['clicks']}")
                    print(f"  Impressions: {row['impressions']}")
                    print(f"  CTR: {row['ctr']:.2%}")
                    print(f"  Position: {row['position']:.1f}")
            else:
                print("No data available for the selected period")
            
            return True
            
    except Exception as e:
        print(f"\nError testing GSC integration: {str(e)}")
        return False

if __name__ == '__main__':
    print("Testing Google Search Console API Integration...")
    success = test_gsc_connection()
    if success:
        print("\n✅ GSC API integration test completed successfully!")
    else:
        print("\n❌ GSC API integration test failed. Please check the error message above.") 