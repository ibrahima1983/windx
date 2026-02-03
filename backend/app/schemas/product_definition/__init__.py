"""Product Definition Schemas package.

This package provides scope-based schemas for product definition API endpoints.
Each scope (profile, glazing, etc.) has its own schema implementation.
"""

from .base import (
    BaseEntityCreate,
    BaseEntityUpdate, 
    BaseEntityResponse,
    BaseResponse,
    ErrorResponse
)
from .profile import (
    ProfileEntityCreate,
    ProfilePathCreate,
    ProfileDependentOptionsRequest,
    ProfileEntityResponse
)
from .glazing import (
    GlazingComponentCreate,
    GlazingUnitCreate,
    GlazingUnitResponse,
    GlazingComponentResponse
)
from .responses import (
    EntityListResponse,
    PathListResponse,
    ComponentListResponse
)

__all__ = [
    # Base schemas
    "BaseEntityCreate",
    "BaseEntityUpdate", 
    "BaseEntityResponse",
    "BaseResponse",
    "ErrorResponse",
    
    # Profile schemas
    "ProfileEntityCreate",
    "ProfilePathCreate", 
    "ProfileDependentOptionsRequest",
    "ProfileEntityResponse",
    
    # Glazing schemas
    "GlazingComponentCreate",
    "GlazingUnitCreate",
    "GlazingUnitResponse",
    "GlazingComponentResponse",
    
    # Response schemas
    "EntityListResponse",
    "PathListResponse",
    "ComponentListResponse"
]