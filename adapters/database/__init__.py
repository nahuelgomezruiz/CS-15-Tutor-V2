"""Database Adapters package."""

from adapters.database.base import BaseDatabaseAdapter
from adapters.database.render_postgres import RenderPostgresAdapter


def get_database_adapter(provider: str = None) -> BaseDatabaseAdapter:
    """
    Factory function to get the appropriate database adapter.
    
    Args:
        provider: Database provider name ('render')
                 If None, uses DATABASE_PROVIDER environment variable, defaults to 'render'
    
    Returns:
        An instance of the appropriate database adapter
    """
    import os
    
    if provider is None:
        provider = os.getenv('DATABASE_PROVIDER', 'render').lower()
    
    adapters = {
        'render': RenderPostgresAdapter,
        'postgres': RenderPostgresAdapter,
        'sqlite': RenderPostgresAdapter,  # Same adapter handles both
    }
    
    adapter_class = adapters.get(provider)
    if adapter_class is None:
        raise ValueError(f"Unknown database provider: {provider}. Available: {list(adapters.keys())}")
    
    return adapter_class()


__all__ = [
    'BaseDatabaseAdapter',
    'RenderPostgresAdapter',
    'get_database_adapter',
]
