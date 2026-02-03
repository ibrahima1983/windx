"""
Product Definition Scripts Package

This package contains scope-specific setup and debug scripts for product definitions.
Each scope (profile, glazing, etc.) has its own setup and debug scripts.
"""

from .base import BaseProductDefinitionSetup
from .setup_profile import ProfileSetup
from .setup_glazing import GlazingSetup

__all__ = [
    "BaseProductDefinitionSetup",
    "ProfileSetup", 
    "GlazingSetup",
]