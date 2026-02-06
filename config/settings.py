"""Centralized settings module.

This module re-exports settings from core.config for backward compatibility
and provides a single entry point for configuration.
"""

from core.config import Settings, settings

__all__ = ['Settings', 'settings']
