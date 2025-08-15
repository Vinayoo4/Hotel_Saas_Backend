import uuid
import aiohttp
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from app.models.models import Guest, BackgroundTask
from app.utils.helpers import get_current_time
from app.config.config import settings
from app.utils.errors import UnauthorizedError, ServerError
from loguru import logger

class DigiLockerService:
    def __init__(self, session=None):
        self.session = session
        self.client_id = settings.DIGILOCKER_CLIENT_ID
        self.client_secret = settings.DIGILOCKER_CLIENT_SECRET
        self.redirect_uri = settings.DIGILOCKER_REDIRECT_URI
        self.auth_url = "https://api.digitallocker.gov.in/public/oauth2/1/authorize"
        self.token_url = "https://api.digitallocker.gov.in/public/oauth2/1/token"
        self.issued_documents_url = "https://api.digitallocker.gov.in/public/oauth2/1/files/issued"
        self.uploaded_documents_url = "https://api.digitallocker.gov.in/public/oauth2/1/files/uploaded"
    
    def get_auth_url(self, state: str) -> str:
        """Generate DigiLocker authorization URL"""
        auth_params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "state": state
        }
        
        # Build URL with query parameters
        query_string = "&".join([f"{key}={value}" for key, value in auth_params.items()])
        auth_url = f"{self.auth_url}?{query_string}"
        
        logger.info(f"Generated DigiLocker auth URL with state: {state}")
        return auth_url
    
    async def get_authorization_url(self, guest_id: int) -> str:
        """Generate DigiLocker authorization URL for a specific guest"""
        state = str(guest_id)  # Use guest_id as state for security
        return self.get_auth_url(state)
    
    async def exchange_code_for_token(self, code: str) -> Dict[str, Any]:
        """Exchange authorization code for access token"""
        token_params = {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "redirect_uri": self.redirect_uri
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.token_url, data=token_params) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"DigiLocker token exchange failed: {error_text}")
                        raise UnauthorizedError("Failed to exchange code for token")
                    
                    token_data = await response.json()
                    logger.info("Successfully exchanged code for DigiLocker token")
                    return token_data
        except aiohttp.ClientError as e:
            logger.error(f"DigiLocker API error: {str(e)}")
            raise ServerError(f"DigiLocker API error: {str(e)}")
    
    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh DigiLocker access token"""
        refresh_params = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.token_url, data=refresh_params) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"DigiLocker token refresh failed: {error_text}")
                        raise UnauthorizedError("Failed to refresh token")
                    
                    token_data = await response.json()
                    logger.info("Successfully refreshed DigiLocker token")
                    return token_data
        except aiohttp.ClientError as e:
            logger.error(f"DigiLocker API error: {str(e)}")
            raise ServerError(f"DigiLocker API error: {str(e)}")
    
    async def update_guest_tokens(self, guest_id: int, token_data: Dict[str, Any]) -> Guest:
        """Update guest's DigiLocker tokens"""
        guest = self.session.get(Guest, guest_id)
        if not guest:
            raise ValueError(f"Guest not found: {guest_id}")
        
        # Calculate token expiry time
        expires_in = token_data.get("expires_in", 3600)  # Default to 1 hour if not provided
        expiry_time = get_current_time() + timedelta(seconds=expires_in)
        
        # Update guest record
        guest.digilocker_token = token_data.get("access_token")
        guest.digilocker_refresh_token = token_data.get("refresh_token")
        guest.digilocker_token_expiry = expiry_time
        guest.updated_at = get_current_time()
        
        self.session.add(guest)
        self.session.commit()
        self.session.refresh(guest)
        
        logger.info(f"Updated DigiLocker tokens for guest: {guest_id}")
        return guest
    
    async def create_fetch_documents_task(self, guest_id: int) -> BackgroundTask:
        """Create a background task for fetching DigiLocker documents"""
        task_id = str(uuid.uuid4())
        
        task = BackgroundTask(
            task_id=task_id,
            task_type="digilocker_fetch",
            status="pending",
            result=f"{{\"guest_id\": {guest_id}}}",
            created_at=get_current_time()
        )
        
        self.session.add(task)
        self.session.commit()
        self.session.refresh(task)
        
        logger.info(f"Created DigiLocker fetch task: {task_id} for guest: {guest_id}")
        return task
    
    async def fetch_documents(self, task_id: str, guest_id: int) -> Dict[str, Any]:
        """Fetch documents from DigiLocker"""
        # Update task status
        task = self.session.get(BackgroundTask, task_id)
        if not task:
            raise ValueError(f"Task not found: {task_id}")
        
        task.status = "running"
        self.session.add(task)
        self.session.commit()
        
        # Get guest's DigiLocker token
        guest = self.session.get(Guest, guest_id)
        if not guest or not guest.digilocker_token:
            error_msg = f"Guest {guest_id} has no DigiLocker token"
            task.status = "failed"
            task.error = error_msg
            task.completed_at = get_current_time()
            self.session.add(task)
            self.session.commit()
            logger.error(error_msg)
            raise UnauthorizedError(error_msg)
        
        # Check if token is expired
        if guest.digilocker_token_expiry and guest.digilocker_token_expiry < get_current_time():
            # Try to refresh token
            if guest.digilocker_refresh_token:
                try:
                    token_data = await self.refresh_token(guest.digilocker_refresh_token)
                    guest = await self.update_guest_tokens(guest_id, token_data)
                except Exception as e:
                    error_msg = f"Failed to refresh DigiLocker token: {str(e)}"
                    task.status = "failed"
                    task.error = error_msg
                    task.completed_at = get_current_time()
                    self.session.add(task)
                    self.session.commit()
                    logger.error(error_msg)
                    raise UnauthorizedError(error_msg)
            else:
                error_msg = "DigiLocker token expired and no refresh token available"
                task.status = "failed"
                task.error = error_msg
                task.completed_at = get_current_time()
                self.session.add(task)
                self.session.commit()
                logger.error(error_msg)
                raise UnauthorizedError(error_msg)
        
        try:
            # Fetch issued documents
            issued_documents = await self._fetch_issued_documents(guest.digilocker_token)
            
            # Fetch uploaded documents
            uploaded_documents = await self._fetch_uploaded_documents(guest.digilocker_token)
            
            # Combine results
            result = {
                "issued_documents": issued_documents,
                "uploaded_documents": uploaded_documents
            }
            
            # Update task with result
            task.status = "completed"
            task.result = str(result)
            task.completed_at = get_current_time()
            self.session.add(task)
            self.session.commit()
            
            logger.info(f"DigiLocker document fetch completed for task: {task_id}")
            return result
            
        except Exception as e:
            # Update task with error
            task.status = "failed"
            task.error = str(e)
            task.completed_at = get_current_time()
            self.session.add(task)
            self.session.commit()
            
            logger.error(f"DigiLocker document fetch failed for task: {task_id}. Error: {str(e)}")
            raise
    
    async def _fetch_issued_documents(self, access_token: str) -> List[Dict[str, Any]]:
        """Fetch issued documents from DigiLocker"""
        headers = {"Authorization": f"Bearer {access_token}"}
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.issued_documents_url, headers=headers) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"DigiLocker issued documents fetch failed: {error_text}")
                        raise ServerError("Failed to fetch issued documents")
                    
                    data = await response.json()
                    documents = data.get("documents", [])
                    logger.info(f"Fetched {len(documents)} issued documents from DigiLocker")
                    return documents
        except aiohttp.ClientError as e:
            logger.error(f"DigiLocker API error: {str(e)}")
            raise ServerError(f"DigiLocker API error: {str(e)}")
    
    async def _fetch_uploaded_documents(self, access_token: str) -> List[Dict[str, Any]]:
        """Fetch uploaded documents from DigiLocker"""
        headers = {"Authorization": f"Bearer {access_token}"}
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.uploaded_documents_url, headers=headers) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"DigiLocker uploaded documents fetch failed: {error_text}")
                        raise ServerError("Failed to fetch uploaded documents")
                    
                    data = await response.json()
                    documents = data.get("documents", [])
                    logger.info(f"Fetched {len(documents)} uploaded documents from DigiLocker")
                    return documents
        except aiohttp.ClientError as e:
            logger.error(f"DigiLocker API error: {str(e)}")
            raise ServerError(f"DigiLocker API error: {str(e)}")