# Product Definitions Refactoring Plan

## Executive Summary

This document outlines a comprehensive refactoring plan to decouple the current tightly-coupled product definitions system from the profile-specific implementation. The goal is to create a flexible, scope-based architecture that supports multiple product types (profile, glazing, etc.) without code changes.

## Current Issues Analysis

### 1. Tight Coupling Problems
- **Hard-coded Profile Logic**: Service assumes profile hierarchy (company → material → opening_system → system_series → color)
- **Monolithic Service**: Single service handles all scopes with profile-specific logic
- **Inflexible API Structure**: Endpoints assume profile workflow
- **Frontend Coupling**: Service assumes profile-specific data structures

### 2. Architecture Limitations
- **Single Scope Assumption**: System designed around profile scope only
- **Hard-coded Entity Types**: Entity types are profile-specific constants
- **Inflexible Hierarchy**: Dependency logic assumes 5-level profile hierarchy
- **Mixed Concerns**: Business logic mixed with data access patterns

## Refactoring Strategy

### Core Principles
1. **Scope-Based Architecture**: Each product type (profile, glazing) has its own scope
2. **Service Factory Pattern**: Dynamic service creation based on scope
3. **Composition over Inheritance**: Compose services from reusable components
4. **Gradual Migration**: Maintain backward compatibility during transition
5. **Clear Separation**: Distinct layers for API, services, schemas, and scripts

## Phase Implementation Plan

---

## Phase 1: Create Endpoints Directory Structure

**Duration**: 1-2 days  
**Risk Level**: Low  
**Dependencies**: None

### Objectives
- Organize API endpoints by scope
- Maintain backward compatibility
- Prepare for scope-specific routing

### Files to CREATE
```
backend/app/api/v1/endpoints/product_definitions/
├── __init__.py
├── base.py                    # Base endpoint classes and common schemas
├── profile.py                 # Profile-specific endpoints
├── glazing.py                 # Glazing-specific endpoints (placeholder)
└── router.py                  # Scope-aware router factory
```

### Files to MODIFY
```
backend/app/api/v1/endpoints/admin_product_definitions.py  # Add deprecation warnings
backend/app/api/v1/router.py                               # Include new routers
```

### Implementation Details

#### `backend/app/api/v1/endpoints/product_definitions/base.py`
```python
# Base endpoint classes and common schemas
from abc import ABC, abstractmethod
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

class BaseProductDefinitionEndpoints(ABC):
    """Base class for scope-specific product definition endpoints."""
    
    def __init__(self, scope: str):
        self.scope = scope
        self.router = APIRouter(prefix=f"/product-definitions/{scope}", tags=[f"{scope}-definitions"])
        self._setup_routes()
    
    @abstractmethod
    def _setup_routes(self):
        """Setup scope-specific routes."""
        pass
    
    @abstractmethod
    async def get_entities(self, entity_type: str):
        """Get entities for this scope."""
        pass

# Common schemas
class EntityCreateRequest(BaseModel):
    entity_type: str
    name: str
    image_url: str | None = None
    # ... other common fields

class EntityUpdateRequest(BaseModel):
    name: str | None = None
    # ... other common fields
```

#### `backend/app/api/v1/endpoints/product_definitions/profile.py`
```python
# Profile-specific endpoints (migrated from current implementation)
from .base import BaseProductDefinitionEndpoints
from app.services.product_definition.profile import ProfileProductDefinitionService

class ProfileProductDefinitionEndpoints(BaseProductDefinitionEndpoints):
    def __init__(self):
        super().__init__("profile")
    
    def _setup_routes(self):
        @self.router.post("/entities")
        async def create_entity(data: EntityCreateRequest, db: AsyncSession = Depends(get_db)):
            service = ProfileProductDefinitionService(db)
            return await service.create_entity(data)
        
        @self.router.post("/paths")
        async def create_path(data: PathCreateRequest, db: AsyncSession = Depends(get_db)):
            service = ProfileProductDefinitionService(db)
            return await service.create_dependency_path(data)
        
        # ... other profile-specific endpoints
```

#### `backend/app/api/v1/endpoints/product_definitions/glazing.py`
```python
# Glazing-specific endpoints (new implementation)
from .base import BaseProductDefinitionEndpoints
from app.services.product_definition.glazing import GlazingProductDefinitionService

class GlazingProductDefinitionEndpoints(BaseProductDefinitionEndpoints):
    def __init__(self):
        super().__init__("glazing")
    
    def _setup_routes(self):
        @self.router.post("/components")
        async def create_component(data: ComponentCreateRequest, db: AsyncSession = Depends(get_db)):
            service = GlazingProductDefinitionService(db)
            return await service.create_component(data)
        
        @self.router.post("/glazing-units")
        async def create_glazing_unit(data: GlazingUnitCreateRequest, db: AsyncSession = Depends(get_db)):
            service = GlazingProductDefinitionService(db)
            return await service.create_glazing_unit(data)
        
        # ... other glazing-specific endpoints
```

---

## Phase 2: Create Services Directory Structure

**Duration**: 2-3 days  
**Risk Level**: Medium  
**Dependencies**: Phase 1

### Objectives
- Implement service factory pattern
- Create scope-specific services
- Maintain service layer separation

### Files to CREATE
```
backend/app/services/product_definition/
├── __init__.py
├── base.py                    # Base service class and common functionality
├── factory.py                 # Service factory for dynamic service creation
├── profile.py                 # Profile-specific service (migrated logic)
├── glazing.py                 # Glazing-specific service (new)
└── types.py                   # Common types and interfaces
```

### Files to MODIFY
```
backend/app/services/product_definition.py  # Add deprecation warnings, delegate to factory
```

### Implementation Details

#### `backend/app/services/product_definition/base.py`
```python
# Base service with common functionality
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.base import BaseService

class BaseProductDefinitionService(BaseService, ABC):
    """Base service for product definitions with common functionality."""
    
    def __init__(self, db: AsyncSession, scope: str):
        super().__init__(db)
        self.scope = scope
    
    @abstractmethod
    async def get_entities(self, entity_type: str) -> List[Any]:
        """Get entities of specific type for this scope."""
        pass
    
    @abstractmethod
    async def create_entity(self, data: Any) -> Any:
        """Create entity for this scope."""
        pass
    
    # Common methods used by all scopes
    async def get_scope_metadata(self) -> Dict[str, Any]:
        """Get metadata for this scope."""
        # Implementation for loading scope metadata from database
        pass
    
    def _slugify(self, name: str) -> str:
        """Convert name to LTREE-safe slug."""
        # Common slugification logic
        pass
```

#### `backend/app/services/product_definition/profile.py`
```python
# Profile-specific service (migrated from current implementation)
from .base import BaseProductDefinitionService
from .types import ProfilePathCreate, ProfileEntity

class ProfileProductDefinitionService(BaseProductDefinitionService):
    """Service for profile product definitions with hierarchical dependencies."""
    
    def __init__(self, db: AsyncSession):
        super().__init__(db, "profile")
    
    async def create_entity(self, data: ProfileEntityCreate) -> ProfileEntity:
        """Create profile entity with hierarchy validation."""
        # Migrated logic from current ProductDefinitionService
        pass
    
    async def create_dependency_path(self, data: ProfilePathCreate) -> Any:
        """Create profile dependency path (company → material → ... → color)."""
        # Migrated path creation logic
        pass
    
    async def get_dependent_options(self, selections: Dict[str, int]) -> Dict[str, List[Any]]:
        """Get cascading options for profile hierarchy."""
        # Migrated cascading logic
        pass
```

#### `backend/app/services/product_definition/glazing.py`
```python
# Glazing-specific service (new implementation)
from .base import BaseProductDefinitionService
from .types import GlazingComponent, GlazingUnit

class GlazingProductDefinitionService(BaseProductDefinitionService):
    """Service for glazing product definitions with compositional structure."""
    
    def __init__(self, db: AsyncSession):
        super().__init__(db, "glazing")
    
    async def create_component(self, data: GlazingComponentCreate) -> GlazingComponent:
        """Create glazing component (glass_type, spacer, gas)."""
        # New implementation for glazing components
        pass
    
    async def create_glazing_unit(self, data: GlazingUnitCreate) -> GlazingUnit:
        """Create glazing unit from components (single/double/triple)."""
        # New implementation for glazing units
        pass
    
    async def calculate_glazing_properties(self, unit_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate technical properties for glazing unit."""
        # New calculation logic for U-value, thickness, price, weight
        pass
```

#### `backend/app/services/product_definition/factory.py`
```python
# Service factory for dynamic service creation
from typing import Type, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from .base import BaseProductDefinitionService
from .profile import ProfileProductDefinitionService
from .glazing import GlazingProductDefinitionService

class ProductDefinitionServiceFactory:
    """Factory for creating scope-specific product definition services."""
    
    _services: Dict[str, Type[BaseProductDefinitionService]] = {
        "profile": ProfileProductDefinitionService,
        "glazing": GlazingProductDefinitionService,
    }
    
    @classmethod
    def get_service(cls, scope: str, db: AsyncSession) -> BaseProductDefinitionService:
        """Get service instance for specified scope."""
        if scope not in cls._services:
            raise ValueError(f"Unknown scope: {scope}")
        
        service_class = cls._services[scope]
        return service_class(db)
    
    @classmethod
    def register_service(cls, scope: str, service_class: Type[BaseProductDefinitionService]):
        """Register new scope service."""
        cls._services[scope] = service_class
    
    @classmethod
    def get_available_scopes(cls) -> List[str]:
        """Get list of available scopes."""
        return list(cls._services.keys())
```

---

## Phase 3: Create Schemas Directory Structure

**Duration**: 1-2 days  
**Risk Level**: Low  
**Dependencies**: Phase 2

### Objectives
- Organize schemas by scope
- Create type-safe data structures
- Support scope-specific validation

### Files to CREATE
```
backend/app/schemas/product_definition/
├── __init__.py
├── base.py                    # Base schemas and common types
├── profile.py                 # Profile-specific schemas
├── glazing.py                 # Glazing-specific schemas
└── responses.py               # Common response schemas
```

### Files to MODIFY
```
backend/app/schemas/definition.py  # Add deprecation warnings, re-export from new location
```

### Implementation Details

#### `backend/app/schemas/product_definition/base.py`
```python
# Base schemas and common types
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field
from decimal import Decimal

class BaseEntityCreate(BaseModel):
    """Base schema for creating entities."""
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    image_url: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class BaseEntityUpdate(BaseModel):
    """Base schema for updating entities."""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    image_url: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class BaseEntityResponse(BaseModel):
    """Base schema for entity responses."""
    id: int
    name: str
    description: Optional[str]
    image_url: Optional[str]
    created_at: str
    updated_at: str
```

#### `backend/app/schemas/product_definition/profile.py`
```python
# Profile-specific schemas
from .base import BaseEntityCreate, BaseEntityUpdate, BaseEntityResponse
from typing import Optional
from decimal import Decimal

class ProfileEntityCreate(BaseEntityCreate):
    """Schema for creating profile entities."""
    entity_type: str = Field(..., regex="^(company|material|opening_system|system_series|color)$")
    price_from: Optional[Decimal] = Field(None, ge=0)

class ProfilePathCreate(BaseModel):
    """Schema for creating profile dependency paths."""
    company_id: int = Field(..., gt=0)
    material_id: int = Field(..., gt=0)
    opening_system_id: int = Field(..., gt=0)
    system_series_id: int = Field(..., gt=0)
    color_id: int = Field(..., gt=0)

class ProfileDependentOptionsRequest(BaseModel):
    """Schema for requesting dependent options in profile hierarchy."""
    company_id: Optional[int] = None
    material_id: Optional[int] = None
    opening_system_id: Optional[int] = None
    system_series_id: Optional[int] = None
```

#### `backend/app/schemas/product_definition/glazing.py`
```python
# Glazing-specific schemas
from .base import BaseEntityCreate, BaseEntityUpdate, BaseEntityResponse
from typing import Optional, Literal
from decimal import Decimal

class GlazingComponentCreate(BaseEntityCreate):
    """Schema for creating glazing components."""
    component_type: Literal["glass_type", "spacer", "gas"]
    price_per_sqm: Optional[Decimal] = Field(None, ge=0)
    
    # Glass-specific properties
    thickness: Optional[float] = None
    light_transmittance: Optional[float] = None
    u_value: Optional[float] = None
    
    # Spacer-specific properties
    material: Optional[str] = None
    thermal_conductivity: Optional[float] = None
    
    # Gas-specific properties
    density: Optional[float] = None

class GlazingUnitCreate(BaseModel):
    """Schema for creating glazing units."""
    name: str = Field(..., min_length=1, max_length=200)
    glazing_type: Literal["single", "double", "triple"]
    description: Optional[str] = None
    
    # Component references
    outer_glass_id: Optional[int] = None
    middle_glass_id: Optional[int] = None  # Triple only
    inner_glass_id: Optional[int] = None   # Double/Triple
    spacer1_id: Optional[int] = None       # Double/Triple
    spacer2_id: Optional[int] = None       # Triple only
    gas_id: Optional[int] = None           # Optional for Double/Triple

class GlazingUnitResponse(BaseEntityResponse):
    """Schema for glazing unit responses."""
    glazing_type: str
    total_thickness: float
    u_value: float
    price_per_sqm: Decimal
    weight_per_sqm: float
    components: Dict[str, Any]
```

---

## Phase 4: Create Scripts Directory Structure

**Duration**: 1 day  
**Risk Level**: Low  
**Dependencies**: Phase 2, 3

### Objectives
- Organize setup/debug scripts by scope
- Create reusable script components
- Support multiple scope initialization

### Files to CREATE
```
backend/scripts/product_definition/
├── __init__.py
├── base.py                    # Base script functionality
├── setup_profile.py           # Profile scope setup (migrated)
├── setup_glazing.py           # Glazing scope setup (new)
├── debug_profile.py           # Profile debug script (migrated)
├── debug_glazing.py           # Glazing debug script (new)
└── setup_all_scopes.py       # Setup all scopes
```

### Files to MODIFY
```
backend/scripts/setup_product_definitions.py  # Delegate to scope-specific scripts
backend/scripts/debug_relations.py            # Delegate to scope-specific scripts
backend/scripts/seed_relations.py             # Delegate to profile setup
```

### Implementation Details

#### `backend/scripts/product_definition/base.py`
```python
# Base script functionality
from abc import ABC, abstractmethod
from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession

class BaseProductDefinitionSetup(ABC):
    """Base class for scope-specific setup scripts."""
    
    def __init__(self, scope: str):
        self.scope = scope
    
    @abstractmethod
    async def create_scope_metadata(self, db: AsyncSession) -> None:
        """Create scope metadata in database."""
        pass
    
    @abstractmethod
    async def seed_sample_data(self, db: AsyncSession) -> None:
        """Seed sample data for this scope."""
        pass
    
    async def setup_scope(self, db: AsyncSession) -> None:
        """Complete scope setup."""
        print(f"Setting up {self.scope} scope...")
        await self.create_scope_metadata(db)
        await self.seed_sample_data(db)
        print(f"✅ {self.scope} scope setup complete")
```

#### `backend/scripts/product_definition/setup_profile.py`
```python
# Profile scope setup (migrated from current scripts)
from .base import BaseProductDefinitionSetup
from app.models.attribute_node import AttributeNode

class ProfileSetup(BaseProductDefinitionSetup):
    def __init__(self):
        super().__init__("profile")
    
    async def create_scope_metadata(self, db: AsyncSession) -> None:
        """Create profile scope metadata."""
        # Migrated logic from setup_product_definitions.py
        scope_metadata = {
            "label": "Profile System",
            "hierarchy": {
                "0": "company",
                "1": "material", 
                "2": "opening_system",
                "3": "system_series",
                "4": "color"
            },
            "dependencies": [
                # Profile dependency rules
            ]
        }
        # Create scope metadata node
        pass
    
    async def seed_sample_data(self, db: AsyncSession) -> None:
        """Seed sample profile data."""
        # Migrated logic from seed_relations.py
        pass
```

#### `backend/scripts/product_definition/setup_glazing.py`
```python
# Glazing scope setup (new implementation)
from .base import BaseProductDefinitionSetup

class GlazingSetup(BaseProductDefinitionSetup):
    def __init__(self):
        super().__init__("glazing")
    
    async def create_scope_metadata(self, db: AsyncSession) -> None:
        """Create glazing scope metadata."""
        scope_metadata = {
            "label": "Glazing System",
            "entities": {
                "glass_type": {
                    "label": "Glass Type",
                    "icon": "pi pi-stop",
                    "metadata_fields": [
                        {"name": "thickness", "type": "number", "label": "Thickness (mm)"},
                        {"name": "u_value", "type": "number", "label": "U-Value"},
                        # ... other glass properties
                    ]
                },
                "spacer": {
                    "label": "Spacer",
                    "icon": "pi pi-minus",
                    "metadata_fields": [
                        {"name": "material", "type": "text", "label": "Material"},
                        {"name": "thermal_conductivity", "type": "number", "label": "Thermal Conductivity"},
                        # ... other spacer properties
                    ]
                },
                "gas": {
                    "label": "Gas Filling",
                    "icon": "pi pi-cloud",
                    "metadata_fields": [
                        {"name": "density", "type": "number", "label": "Density"},
                        # ... other gas properties
                    ]
                }
            }
        }
        # Create scope metadata node
        pass
    
    async def seed_sample_data(self, db: AsyncSession) -> None:
        """Seed sample glazing data."""
        # Create sample glass types, spacers, gases
        pass
```

---

## Phase 5: Update Frontend Structure

**Duration**: 2-3 days  
**Risk Level**: Medium  
**Dependencies**: Phase 1-4

### Objectives
- Create scope-aware frontend services
- Implement service factory pattern
- Support multiple product definition types

### Files to CREATE
```
frontend/src/services/productDefinition/
├── index.ts                   # Main exports and factory
├── base.ts                    # Base service class
├── profile.ts                 # Profile-specific service (migrated)
├── glazing.ts                 # Glazing-specific service (new)
└── types.ts                   # Common types and interfaces
```

### Files to MODIFY
```
frontend/src/services/productDefinitionService.ts  # Delegate to factory, add deprecation
frontend/src/views/admin/GenericDefinitionView.vue # Use factory pattern
```

### Implementation Details

#### `frontend/src/services/productDefinition/base.ts`
```typescript
// Base service with common functionality
import { apiClient } from '@/services/api'

export abstract class BaseProductDefinitionService {
    protected scope: string
    
    constructor(scope: string) {
        this.scope = scope
    }
    
    abstract getEntities(type: string): Promise<any>
    abstract createEntity(data: any): Promise<any>
    abstract updateEntity(id: number, data: any): Promise<any>
    abstract deleteEntity(id: number): Promise<any>
    
    // Common methods
    protected async apiCall(method: string, endpoint: string, data?: any): Promise<any> {
        const url = `/api/v1/admin/product-definitions/${this.scope}${endpoint}`
        return await apiClient[method](url, data)
    }
    
    async uploadImage(file: File): Promise<any> {
        // Common image upload logic
        const formData = new FormData()
        formData.append('file', file)
        return await apiClient.post('/api/v1/admin/entry/upload-image', formData, {
            headers: { 'Content-Type': 'multipart/form-data' }
        })
    }
}
```

#### `frontend/src/services/productDefinition/profile.ts`
```typescript
// Profile-specific service (migrated logic)
import { BaseProductDefinitionService } from './base'

export class ProfileProductDefinitionService extends BaseProductDefinitionService {
    constructor() {
        super('profile')
    }
    
    async getEntities(type: string): Promise<any> {
        return await this.apiCall('get', `/entities/${type}`)
    }
    
    async createPath(data: ProfilePathCreate): Promise<any> {
        return await this.apiCall('post', '/paths', data)
    }
    
    async getDependentOptions(selections: any): Promise<any> {
        return await this.apiCall('post', '/options', selections)
    }
    
    // ... other profile-specific methods
}

export interface ProfilePathCreate {
    company_id: number
    material_id: number
    opening_system_id: number
    system_series_id: number
    color_id: number
}
```

#### `frontend/src/services/productDefinition/glazing.ts`
```typescript
// Glazing-specific service (new implementation)
import { BaseProductDefinitionService } from './base'

export class GlazingProductDefinitionService extends BaseProductDefinitionService {
    constructor() {
        super('glazing')
    }
    
    async getEntities(type: string): Promise<any> {
        return await this.apiCall('get', `/entities/${type}`)
    }
    
    async createGlazingUnit(data: GlazingUnitCreate): Promise<any> {
        return await this.apiCall('post', '/glazing-units', data)
    }
    
    async getGlazingComponents(): Promise<any> {
        return await this.apiCall('get', '/components')
    }
    
    async calculateGlazingProperties(unitData: any): Promise<any> {
        return await this.apiCall('post', '/calculate', unitData)
    }
    
    // ... other glazing-specific methods
}

export interface GlazingUnitCreate {
    name: string
    glazing_type: 'single' | 'double' | 'triple'
    outer_glass_id?: number
    inner_glass_id?: number
    middle_glass_id?: number
    spacer1_id?: number
    spacer2_id?: number
    gas_id?: number
}
```

#### `frontend/src/services/productDefinition/index.ts`
```typescript
// Service factory and main exports
import { BaseProductDefinitionService } from './base'
import { ProfileProductDefinitionService } from './profile'
import { GlazingProductDefinitionService } from './glazing'

export class ProductDefinitionServiceFactory {
    private static services: Map<string, BaseProductDefinitionService> = new Map()
    
    static getService(scope: string): BaseProductDefinitionService {
        if (!this.services.has(scope)) {
            const service = this.createService(scope)
            this.services.set(scope, service)
        }
        return this.services.get(scope)!
    }
    
    private static createService(scope: string): BaseProductDefinitionService {
        switch (scope) {
            case 'profile':
                return new ProfileProductDefinitionService()
            case 'glazing':
                return new GlazingProductDefinitionService()
            default:
                throw new Error(`Unknown scope: ${scope}`)
        }
    }
    
    static getAvailableScopes(): string[] {
        return ['profile', 'glazing']
    }
}

// Convenience exports
export const productDefinitionServiceFactory = ProductDefinitionServiceFactory
export { BaseProductDefinitionService } from './base'
export { ProfileProductDefinitionService } from './profile'
export { GlazingProductDefinitionService } from './glazing'
```

---

## Phase 6: Remove Backward Compatibility

**Duration**: 1 day  
**Risk Level**: Low  
**Dependencies**: Phase 1-5 complete and tested

### Objectives
- Remove deprecated files and endpoints
- Clean up legacy code
- Finalize new architecture

### Files to DELETE
```
backend/app/api/v1/endpoints/admin_product_definitions.py
backend/app/services/product_definition.py
backend/app/schemas/definition.py
backend/scripts/debug_relations.py
backend/scripts/seed_relations.py
frontend/src/services/productDefinitionService.ts
```

### Files to MODIFY
```
backend/app/api/v1/router.py                    # Remove old routes, keep new ones
frontend/src/views/admin/GenericDefinitionView.vue  # Remove old service imports
```

### Implementation Details

#### Update `backend/app/api/v1/router.py`
```python
# Remove old imports and routes
# from app.api.v1.endpoints import admin_product_definitions

# Add new scope-based routes
from app.api.v1.endpoints.product_definitions.profile import ProfileProductDefinitionEndpoints
from app.api.v1.endpoints.product_definitions.glazing import GlazingProductDefinitionEndpoints

# Register new routers
profile_endpoints = ProfileProductDefinitionEndpoints()
glazing_endpoints = GlazingProductDefinitionEndpoints()

api_router.include_router(profile_endpoints.router, prefix="/admin")
api_router.include_router(glazing_endpoints.router, prefix="/admin")
```

#### Update Frontend Views
```typescript
// Remove old imports
// import { productDefinitionService } from '@/services/productDefinitionService'

// Use new factory
import { productDefinitionServiceFactory } from '@/services/productDefinition'

// In component
const profileService = productDefinitionServiceFactory.getService('profile')
const glazingService = productDefinitionServiceFactory.getService('glazing')
```

---

## Migration Strategy

### Gradual Migration Approach

1. **Phase 1-3**: Create new structure alongside existing code
2. **Phase 4-5**: Update consumers to use new structure
3. **Phase 6**: Remove old code after thorough testing

### Backward Compatibility During Transition

- Keep existing endpoints with deprecation warnings
- Delegate old service calls to new factory
- Maintain existing API contracts
- Add feature flags for new functionality

### Testing Strategy

- **Unit Tests**: Test each service independently
- **Integration Tests**: Test API endpoints with database
- **E2E Tests**: Test complete workflows in frontend
- **Migration Tests**: Verify data integrity during migration

### Rollback Plan

- Keep old code until new system is proven stable
- Feature flags to switch between old/new implementations
- Database migrations are reversible
- Frontend can fall back to old service

## Benefits After Refactoring

### 1. Flexibility
- Easy to add new product types (furniture, doors, etc.)
- Scope-specific business logic
- Independent development of different product types

### 2. Maintainability
- Clear separation of concerns
- Smaller, focused service classes
- Easier to test and debug

### 3. Scalability
- Services can be optimized per scope
- Independent deployment of scope-specific features
- Better performance through targeted optimizations

### 4. Developer Experience
- Clear code organization
- Type-safe interfaces
- Easier onboarding for new developers

## Risk Mitigation

### Technical Risks
- **Database Migration**: Use careful migration scripts with rollback capability
- **API Breaking Changes**: Maintain backward compatibility during transition
- **Frontend Integration**: Gradual migration with feature flags

### Business Risks
- **Downtime**: Zero-downtime deployment strategy
- **Data Loss**: Comprehensive backup and testing strategy
- **User Impact**: Maintain existing functionality during migration

## Success Metrics

### Technical Metrics
- Code coverage > 90% for new services
- API response times < 100ms
- Zero breaking changes during migration

### Business Metrics
- No user-reported issues during migration
- Successful creation of glazing system
- Reduced development time for new product types

## Timeline Summary

| Phase | Duration | Dependencies | Risk Level |
|-------|----------|--------------|------------|
| Phase 1: Endpoints | 1-2 days | None | Low |
| Phase 2: Services | 2-3 days | Phase 1 | Medium |
| Phase 3: Schemas | 1-2 days | Phase 2 | Low |
| Phase 4: Scripts | 1 day | Phase 2,3 | Low |
| Phase 5: Frontend | 2-3 days | Phase 1-4 | Medium |
| Phase 6: Cleanup | 1 day | Phase 1-5 | Low |

**Total Duration**: 8-12 days  
**Total Risk Level**: Medium (manageable with proper testing)

## Conclusion

This refactoring plan transforms the tightly-coupled product definitions system into a flexible, scope-based architecture. The gradual migration approach ensures minimal risk while providing maximum benefit for future development.

The new architecture will support:
- **Profile System**: Existing hierarchical dependencies
- **Glazing System**: New compositional structure
- **Future Systems**: Easy addition of new product types

By following this plan, the Windx system will be well-positioned for growth and adaptation to new business requirements.