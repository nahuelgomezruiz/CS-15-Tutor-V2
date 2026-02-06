"""Authentication Service for CS-15 Tutor."""

import os
import secrets
import logging
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timedelta

import jwt

logger = logging.getLogger(__name__)

# Try to import LDAP
try:
    from ldap3 import Server, Connection, ALL, SIMPLE
    LDAP_AVAILABLE = True
except ImportError:
    LDAP_AVAILABLE = False
    logger.warning("ldap3 not installed. LDAP authentication will not work.")


class AuthService:
    """
    Authentication service for the CS 15 tutor system.
    Handles both web app (.htaccess) and VSCode extension authentication.
    """
    
    def __init__(self, jwt_secret: Optional[str] = None):
        """
        Initialize the authentication service.
        
        Args:
            jwt_secret: Secret key for JWT tokens. If not provided,
                       uses JWT_SECRET env var.
        """
        self.jwt_secret = jwt_secret or os.getenv('JWT_SECRET', 'your-secret-key-change-this-in-production')
        self.jwt_expiry_hours = 24
        
        self.ldap_url = "ldap://ldap.eecs.tufts.edu"
        self.ldap_base_dn = "ou=people,dc=eecs,dc=tufts,dc=edu"
        
        # In-memory store for VSCode sessions
        self._vscode_sessions: Dict[str, Dict[str, Any]] = {}
        
        logger.info("Authentication service initialized")
    
    def authenticate_ldap_credentials(self, username: str, password: str) -> bool:
        """
        Authenticate user credentials against Tufts EECS LDAP server.
        
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
            server = Server(self.ldap_url, get_info=ALL)
            user_dn = f"uid={username},{self.ldap_base_dn}"
            conn = Connection(server, user=user_dn, password=password, authentication=SIMPLE)
            
            if conn.bind():
                logger.info(f"LDAP authentication successful for user: {username}")
                conn.unbind()
                return True
            else:
                logger.warning(f"LDAP authentication failed for user: {username}")
                return False
            
        except Exception as e:
            logger.error(f"LDAP authentication error for user {username}: {e}")
            return False
    
    def authenticate_vscode_user(self, username: str, password: str) -> Optional[str]:
        """
        Authenticate VSCode user with credentials and return JWT token.
        
        Args:
            username: Tufts EECS username
            password: User's password
        
        Returns:
            JWT token if successful, None otherwise
        """
        try:
            username = username.lower().strip()
            dev_mode = os.getenv('DEVELOPMENT_MODE', '').lower() == 'true'
            
            # Skip LDAP for development users in dev mode
            if dev_mode and username in ['dev_user', 'test_user', 'demo_user', 'testuser']:
                if not password or len(password.strip()) == 0:
                    return None
            else:
                if not self.authenticate_ldap_credentials(username, password):
                    return None
            
            token = self.create_vscode_auth_token(username)
            logger.info(f"VSCode authentication successful for user: {username}")
            return token
            
        except Exception as e:
            logger.error(f"VSCode authentication error: {e}")
            return None
    
    def extract_utln_from_web_request(self, request) -> Optional[str]:
        """
        Extract UTLN from web request (Apache .htaccess authentication).
        
        Args:
            request: Flask request object
        
        Returns:
            UTLN if authenticated, None otherwise
        """
        try:
            utln = None
            
            # Method 1: REMOTE_USER environment variable
            utln = os.environ.get('REMOTE_USER')
            
            # Method 2: X-Remote-User header
            if not utln:
                utln = request.headers.get('X-Remote-User')
            
            # Method 3: CGI environment
            if not utln:
                utln = request.environ.get('REMOTE_USER')
            
            # Method 4: Basic Auth header
            if not utln and request.authorization:
                utln = request.authorization.username
            
            # Method 5: Development mode header
            if not utln and request.headers.get('X-Development-Mode') == 'true':
                utln = request.headers.get('X-Remote-User')
            
            # Method 6: Tufts frontend deployment
            if not utln and request.headers.get('X-Tufts-Authenticated') == 'true':
                frontend_domain = request.headers.get('X-Frontend-Domain')
                remote_user = request.headers.get('X-Remote-User')
                
                if (frontend_domain and remote_user and 
                    ('.tufts.edu' in frontend_domain or 'eecs.tufts.edu' in frontend_domain)):
                    utln = remote_user
            
            if utln:
                return utln.lower().strip()
            
            return None
            
        except Exception as e:
            logger.error(f"Error extracting UTLN: {e}")
            return None
    
    def create_vscode_auth_token(self, utln: str) -> str:
        """
        Create a JWT token for VSCode extension authentication.
        
        Args:
            utln: Tufts University Login Name
        
        Returns:
            JWT token string
        """
        payload = {
            'utln': utln.lower().strip(),
            'iat': datetime.utcnow(),
            'exp': datetime.utcnow() + timedelta(hours=self.jwt_expiry_hours),
            'platform': 'vscode'
        }
        
        return jwt.encode(payload, self.jwt_secret, algorithm='HS256')
    
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
                return utln.lower().strip()
            return None
            
        except jwt.ExpiredSignatureError:
            logger.warning("VSCode auth token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid VSCode auth token: {e}")
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
        
        Args:
            base_url: Base URL of the web application
        
        Returns:
            Login URL with session ID
        """
        session_id = secrets.token_urlsafe(32)
        
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
        Handle the callback from VSCode authentication.
        
        Args:
            session_id: Session ID from login URL
            utln: Authenticated UTLN
        
        Returns:
            JWT token if successful, None otherwise
        """
        session = self._vscode_sessions.get(session_id)
        if not session or session['status'] != 'pending':
            return None
        
        token = self.create_vscode_auth_token(utln)
        
        session['status'] = 'completed'
        session['token'] = token
        session['utln'] = utln
        
        return token
    
    def get_vscode_session_status(self, session_id: str) -> Dict[str, Any]:
        """
        Get the status of a VSCode authentication session.
        
        Args:
            session_id: Session ID from login URL
        
        Returns:
            Session status dict
        """
        session = self._vscode_sessions.get(session_id)
        if not session:
            return {'status': 'not_found'}
        
        result = {'status': session['status']}
        if session['status'] == 'completed':
            result['token'] = session.get('token')
            result['utln'] = session.get('utln')
        
        return result


# Global authentication service instance
auth_service = AuthService()
