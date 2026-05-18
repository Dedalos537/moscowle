import os
import io
from flask import current_app

class GoogleDriveService:
    SCOPES = ['https://www.googleapis.com/auth/drive']
    
    def __init__(self):
        self.creds = None
        self.service = None
        self.root_folder_id = '1eOJfoqKA2rFriGChB5O2INPHh4UZE55j'  # Shared folder ID provided
        self._authenticate()

    def _authenticate(self):
        """Authenticate with Google Drive API using service account credentials."""
        try:
            from google.oauth2 import service_account
            from googleapiclient.discovery import build
        except ImportError:
            print("Google Drive libraries not installed. Drive upload disabled.")
            return

        # Try to find credentials in standard locations
        creds_path = os.path.join(os.getcwd(), 'google_credentials.json')
        if not os.path.exists(creds_path):
             creds_path = os.path.join(os.getcwd(), 'instance', 'google_credentials.json')
        
        if os.path.exists(creds_path):
            try:
                self.creds = service_account.Credentials.from_service_account_file(
                    creds_path, scopes=self.SCOPES)
                self.service = build('drive', 'v3', credentials=self.creds)
            except Exception as e:
                print(f"Error authenticating with Google Drive: {e}")
        else:
            print("Google Drive credentials not found. Drive upload disabled.")

    def _find_folder(self, name, parent_id):
        """Find a folder by name within a parent folder."""
        if not self.service: return None
        
        query = f"mimeType='application/vnd.google-apps.folder' and name='{name}' and '{parent_id}' in parents and trashed=false"
        results = self.service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
        files = results.get('files', [])
        if files:
            return files[0]['id']
        return None

    def _create_folder(self, name, parent_id):
        """Create a folder within a parent folder."""
        if not self.service: return None
        
        file_metadata = {
            'name': name,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [parent_id]
        }
        file = self.service.files().create(body=file_metadata, fields='id').execute()
        return file.get('id')

    def ensure_folder_structure(self, patient_name, session_date_str):
        """
        Ensures the folder structure exists: Root -> Patient Name -> Session Date
        Returns the ID of the Session Date folder.
        """
        if not self.service: return None

        # 1. Patient Folder
        patient_folder_id = self._find_folder(patient_name, self.root_folder_id)
        if not patient_folder_id:
            patient_folder_id = self._create_folder(patient_name, self.root_folder_id)
            # Permission sharing note: Service Account creates it, so it owns it. 
            # Since the Root folder is shared, the Service Account must have write access to the Root.
        
        # 2. Session Date Folder
        session_folder_id = self._find_folder(session_date_str, patient_folder_id)
        if not session_folder_id:
            session_folder_id = self._create_folder(session_date_str, patient_folder_id)
            
        return session_folder_id

    def upload_file(self, file_path_or_content, filename, mimetype, patient_name, session_date_str):
        """
        Uploads a file to the specific folder structure.
        file_path_or_content: string (path) or file-like object
        """
        if not self.service:
            print("Google Drive service not initialized.")
            return None

        try:
            folder_id = self.ensure_folder_structure(patient_name, session_date_str)
            if not folder_id:
                return None

            file_metadata = {
                'name': filename,
                'parents': [folder_id]
            }
            
            # Determine media type
            try:
                from googleapiclient.http import MediaIoBaseUpload, MediaFileUpload
            except ImportError:
                print("Google Drive libraries not installed.")
                return None

            if isinstance(file_path_or_content, str):
                # Is a file path
                media = MediaFileUpload(file_path_or_content, mimetype=mimetype, resumable=True)
            else:
                # Is a file object
                if hasattr(file_path_or_content, 'seek'):
                    file_path_or_content.seek(0)
                media = MediaIoBaseUpload(file_path_or_content, mimetype=mimetype, resumable=True)
            
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, webViewLink, owners'
            ).execute()
            
            # Verify Ownership Issue (Service Accounts have 0 quota)
            # We must transfer ownership or rely on the parent folder's quota if it's a Shared Drive (Team Drive).
            # If it's a regular shared folder in My Drive, the files owned by Service Account consume ITS quota (which is 0).
            # BUT, usually Service Accounts have 15GB. 
            # The error "Service Accounts do not have storage quota" usually means they are not GSuite accounts 
            # or the domain disabled it.
            
            return file

        except Exception as e:
            print(f"Error uploading to Google Drive: {e}")
            return None
