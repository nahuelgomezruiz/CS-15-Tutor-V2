import base64
import hashlib
import secrets
import time
from typing import Optional, Dict, Any, Tuple
from flask import request
import logging
import os
import jwt
from datetime import datetime, timedelta

# Add LDAP import
try:
    from ldap3 import Server, Connection, ALL, SIMPLE, SYNC
    LDAP_AVAILABLE = True
except ImportError:
    LDAP_AVAILABLE = False
    print("⚠️ Warning: ldap3 not installed. LDAP authentication will not work.")

logger = logging.getLogger(__name__)

class AuthenticationService:
    """
    Authentication service for the CS 15 tutor system.
    Handles both web app (.htaccess) and VSCode extension authentication.
    """
    
    def __init__(self):
        # JWT secret for VSCode extension authentication
        self.jwt_secret = os.getenv('JWT_SECRET', 'your-secret-key-change-this-in-production')
        self.jwt_expiry_hours = 24
        
        # LDAP configuration (same as .htaccess)
        self.ldap_url = "ldap://ldap.eecs.tufts.edu"
        self.ldap_base_dn = "ou=people,dc=eecs,dc=tufts,dc=edu"
        
        logger.info("Authentication service initialized")
    
    def authenticate_ldap_credentials(self, username: str, password: str) -> bool:
        """
        Authenticate user credentials against Tufts EECS LDAP server.
        This replicates the same authentication that .htaccess performs.
        
        Args:
            username: Tufts EECS username
            password: User's password
        
        Returns:
            True if authentication successful, False otherwise
        """
        if not LDAP_AVAILABLE:
            logger.error("LDAP authentication not available - ldap3 not installed")
            return False
        
        try:
            # Create LDAP server object
            server = Server(self.ldap_url, get_info=ALL)
            
            # Construct user DN (Distinguished Name)
            user_dn = f"uid={username},{self.ldap_base_dn}"
            
            # Create connection and attempt to bind (authenticate) with provided credentials
            conn = Connection(server, user=user_dn, password=password, authentication=SIMPLE)
            
            # Attempt to bind - this performs the authentication
            if conn.bind():
                logger.info(f"LDAP authentication successful for user: {username}")
                conn.unbind()
                return True
            else:
                logger.warning(f"LDAP authentication failed - invalid credentials for user: {username}")
                return False
            
        except Exception as e:
            logger.error(f"Error during LDAP authentication for user {username}: {e}")
            return False

    def authenticate_vscode_user(self, username: str, password: str) -> Optional[str]:
        """
        Authenticate VSCode user with Tufts EECS credentials and return JWT token.
        
        Args:
            username: Tufts EECS username  
            password: User's password
        
        Returns:
            JWT token if successful, None otherwise
        """
        try:
            # Normalize username
            username = username.lower().strip()
            
            # Authorization handled by Tufts LDAP authentication
            
            # Check if development mode is enabled
            dev_mode = os.getenv('DEVELOPMENT_MODE', '').lower() == 'true'
            
            # For development users in development mode, skip LDAP authentication
            if dev_mode and username in ['dev_user', 'test_user', 'demo_user']:
                logger.info(f"Development mode: skipping LDAP authentication for {username}")
                # Just validate that a password was provided
                if not password or len(password.strip()) == 0:
                    logger.warning(f"Development user {username} provided empty password")
                    return None
            else:
                # Authenticate against LDAP for real users
                if not self.authenticate_ldap_credentials(username, password):
                    logger.warning(f"LDAP authentication failed for user: {username}")
                    return None
            
            # Create and return JWT token
            token = self.create_vscode_auth_token(username)
            logger.info(f"VSCode authentication successful for user: {username}")
            return token
            
        except Exception as e:
            logger.error(f"Error during VSCode user authentication: {e}")
            return None

    def extract_utln_from_web_request(self, request) -> Optional[str]:
        """
        Extract UTLN from web request (Apache .htaccess authentication).
        Apache sets the REMOTE_USER environment variable after LDAP authentication.
        
        Args:
            request: Flask request object
        
        Returns:
            UTLN if authenticated, None otherwise
        """
        try:
            # Try multiple ways to get the authenticated user
            utln = None
            
            # Method 1: REMOTE_USER environment variable (most common)
            utln = os.environ.get('REMOTE_USER')
            
            # Method 2: Check request headers (if forwarded by proxy)
            if not utln:
                utln = request.headers.get('X-Remote-User')
                
            # Method 3: Check CGI environment variables
            if not utln:
                utln = request.environ.get('REMOTE_USER')
                
            # Method 4: Basic Auth header (for testing/development)
            if not utln and request.authorization:
                utln = request.authorization.username
            
            # Method 5: Development mode - check for development headers
            if not utln and request.headers.get('X-Development-Mode') == 'true':
                utln = request.headers.get('X-Remote-User')
                if utln:
                    logger.info(f"Development mode authentication: {utln}")
            
            # Method 6: Tufts frontend deployment - validate requests from authorized Tufts domains
            if not utln and request.headers.get('X-Tufts-Authenticated') == 'true':
                frontend_domain = request.headers.get('X-Frontend-Domain')
                remote_user = request.headers.get('X-Remote-User')
                
                # Validate that the request is coming from a legitimate Tufts domain
                if (frontend_domain and remote_user and 
                    ('.tufts.edu' in frontend_domain or 'eecs.tufts.edu' in frontend_domain)):
                    
                    # Trust the Tufts frontend authentication
                    utln = remote_user
                    logger.info(f"Tufts frontend authentication: {utln} from {frontend_domain}")
                else:
                    logger.warning(f"Invalid Tufts frontend request: domain={frontend_domain}, user={remote_user}")
            
            if utln:
                logger.info(f"Authenticated web user: {utln}")
                return utln.lower().strip()
            
            logger.warning("No authenticated user found in web request")
            return None
            
        except Exception as e:
            logger.error(f"Error extracting UTLN from web request: {e}")
            return None
    
    def create_vscode_auth_token(self, utln: str) -> str:
        """
        Create a JWT token for VSCode extension authentication.
        
        Args:
            utln: Tufts University Login Name
        
        Returns:
            JWT token string
        """
        try:
            payload = {
                'utln': utln.lower().strip(),
                'iat': datetime.utcnow(),
                'exp': datetime.utcnow() + timedelta(hours=self.jwt_expiry_hours),
                'platform': 'vscode'
            }
            
            token = jwt.encode(payload, self.jwt_secret, algorithm='HS256')
            logger.info(f"Created VSCode auth token for user: {utln}")
            return token
            
        except Exception as e:
            logger.error(f"Error creating VSCode auth token: {e}")
            raise
    
    def verify_vscode_auth_token(self, token: str) -> Optional[str]:
        """
        Verify a VSCode extension JWT token and extract UTLN.
        
        Args:
            token: JWT token string
        
        Returns:
            UTLN if token is valid, None otherwise
        """
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=['HS256'])
            utln = payload.get('utln')
            
            if utln:
                logger.info(f"Verified VSCode auth token for user: {utln}")
                return utln.lower().strip()
            
            return None
            
        except jwt.ExpiredSignatureError:
            logger.warning("VSCode auth token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid VSCode auth token: {e}")
            return None
        except Exception as e:
            logger.error(f"Error verifying VSCode auth token: {e}")
            return None
    
    def authenticate_request(self, request) -> Tuple[Optional[str], str]:
        """
        Authenticate a request from either web app or VSCode extension.
        
        Args:
            request: Flask request object
        
        Returns:
            Tuple of (UTLN, platform) if authenticated, (None, '') otherwise
        """
        try:
            # Check for VSCode extension auth token
            auth_header = request.headers.get('Authorization')
            if auth_header and auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
                utln = self.verify_vscode_auth_token(token)
                if utln:
                    return utln, 'vscode'
            
            # Check for web app authentication
            utln = self.extract_utln_from_web_request(request)
            if utln:
                return utln, 'web'
            
            return None, ''
            
        except Exception as e:
            logger.error(f"Error authenticating request: {e}")
            return None, ''
    

    
    def generate_vscode_login_url(self, base_url: str) -> str:
        """
        Generate a login URL for VSCode extension users.
        This would redirect to a web page where they can authenticate with Tufts LDAP.
        
        Args:
            base_url: Base URL of the web application
        
        Returns:
            Login URL for VSCode users
        """
        # Create a unique session ID for this login attempt
        session_id = secrets.token_urlsafe(32)
        
        # Store session temporarily (in production, use Redis or database)
        # For now, we'll use a simple in-memory store
        if not hasattr(self, '_vscode_sessions'):
            self._vscode_sessions = {}
        
        self._vscode_sessions[session_id] = {
            'created_at': datetime.utcnow(),
            'status': 'pending'
        }
        
        # Clean up old sessions (older than 1 hour)
        cutoff = datetime.utcnow() - timedelta(hours=1)
        self._vscode_sessions = {
            k: v for k, v in self._vscode_sessions.items() 
            if v['created_at'] > cutoff
        }
        
        return f"{base_url}/vscode-auth?session_id={session_id}"
    
    def handle_vscode_login_callback(self, session_id: str, utln: str) -> Optional[str]:
        """
        Handle the callback from VSCode authentication web page.
        
        Args:
            session_id: Session ID from login URL
            utln: Authenticated UTLN
        
        Returns:
            JWT token if successful, None otherwise
        """
        try:
            if not hasattr(self, '_vscode_sessions'):
                return None
            
            session = self._vscode_sessions.get(session_id)
            if not session or session['status'] != 'pending':
                return None
            
            # Authorization handled by Tufts LDAP authentication
            
            # Create auth token
            token = self.create_vscode_auth_token(utln)
            
            # Mark session as completed
            session['status'] = 'completed'
            session['token'] = token
            session['utln'] = utln
            
            return token
            
        except Exception as e:
            logger.error(f"Error handling VSCode login callback: {e}")
            return None
    
    def get_vscode_session_status(self, session_id: str) -> Dict[str, Any]:
        """
        Get the status of a VSCode authentication session.
        
        Args:
            session_id: Session ID from login URL
        
        Returns:
            Dictionary with session status
        """
        try:
            if not hasattr(self, '_vscode_sessions'):
                return {'status': 'not_found'}
            
            session = self._vscode_sessions.get(session_id)
            if not session:
                return {'status': 'not_found'}
            
            result = {'status': session['status']}
            if session['status'] == 'completed':
                result['token'] = session.get('token')
                result['utln'] = session.get('utln')
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting VSCode session status: {e}")
            return {'status': 'error'}

# Global authentication service instance
auth_service = AuthenticationService()