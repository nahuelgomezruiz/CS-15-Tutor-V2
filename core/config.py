"""Centralized configuration for CS-15 Tutor."""

import os
from dataclasses import dataclass, field
from typing import Optional, List


@dataclass
class Settings:
    """Application settings loaded from environment variables."""
    
    # LLM Configuration
    llm_provider: str = field(default_factory=lambda: os.getenv('LLM_PROVIDER', 'natlab'))
    
    # NatLab-specific settings
    natlab_api_key: Optional[str] = field(default_factory=lambda: os.getenv('NATLAB_API_KEY'))
    natlab_endpoint: Optional[str] = field(default_factory=lambda: os.getenv('NATLAB_ENDPOINT'))
    
    # OpenAI settings
    openai_api_key: Optional[str] = field(default_factory=lambda: os.getenv('OPENAI_API_KEY'))
    
    # Anthropic settings
    anthropic_api_key: Optional[str] = field(default_factory=lambda: os.getenv('ANTHROPIC_API_KEY'))
    
    # Gemini settings
    gemini_api_key: Optional[str] = field(default_factory=lambda: os.getenv('GEMINI_API_KEY'))
    
    # Database Configuration
    database_provider: str = field(default_factory=lambda: os.getenv('DATABASE_PROVIDER', 'render'))
    database_url: Optional[str] = field(default_factory=lambda: os.getenv('DATABASE_URL', 'sqlite:///cs15_tutor_logs.db'))
    
    # Authentication
    jwt_secret: str = field(default_factory=lambda: os.getenv('JWT_SECRET', 'your-secret-key-change-this-in-production'))
    jwt_expiry_hours: int = 24
    ldap_url: str = "ldap://ldap.eecs.tufts.edu"
    ldap_base_dn: str = "ou=people,dc=eecs,dc=tufts,dc=edu"
    
    # Application settings
    development_mode: bool = field(default_factory=lambda: os.getenv('DEVELOPMENT_MODE', '').lower() == 'true')
    debug: bool = field(default_factory=lambda: os.getenv('DEBUG', '').lower() == 'true')
    
    # Health points settings
    max_health_points: int = 12
    health_regen_minutes: int = 3  # 1 point every 3 minutes
    
    # RAG settings
    rag_threshold: float = 0.4
    rag_k: int = 5
    
    # Quality check settings
    max_regeneration_attempts: int = 3
    quality_threshold: int = 7
    
    # Model settings
    default_model: str = '4o-mini'
    default_temperature: float = 0.5
    
    # CORS settings
    cors_origins: List[str] = field(default_factory=lambda: [
        'https://www.eecs.tufts.edu',
        'https://eecs.tufts.edu',
        'https://cs-15-tutor.onrender.com',
        'https://www.cs.tufts.edu',
        'https://cs.tufts.edu',
        'http://localhost:3000',
        'http://127.0.0.1:3000',
        'http://localhost:5000',
        'http://127.0.0.1:5000'
    ])
    
    # Google Sheets sync settings
    spreadsheet_id: Optional[str] = field(default_factory=lambda: os.getenv('SPREADSHEET_ID'))
    google_service_account_json: Optional[str] = field(default_factory=lambda: os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON'))
    
    def get_system_prompt_path(self) -> str:
        """Get the path to the system prompt file."""
        base_paths = [
            os.path.join(os.path.dirname(__file__), '..', 'shared', 'system_prompt.txt'),
            os.path.join(os.path.dirname(__file__), '..', 'responses-api-server', 'system_prompt.txt'),
            'system_prompt.txt',
        ]
        
        for path in base_paths:
            if os.path.exists(path):
                return path
        
        return base_paths[0]  # Default path even if doesn't exist


# Global settings instance
settings = Settings()
