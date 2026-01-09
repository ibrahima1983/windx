# Relations System Implementation Plan

## Overview

Implement hierarchical option dependencies (Company → Material → Opening System → System Series → Colors) using the existing EAV pattern with `AttributeNode` and LTREE. 

**Schema Change Required:** Add `image_url` column to `AttributeNode` model.

## Implementation Status

### ✅ Phase 1: Database Schema Update - COMPLETED
- [x] Added `image_url` field to `AttributeNode` model (`app/models/attribute_node.py`)
- [x] Created and ran Alembic migration (`add_image_url_to_attribute_nodes`)

### ✅ Phase 2: Backend Relations Management - COMPLETED
- [x] Created `RelationsService` (`app/services/relations.py`)
- [x] Created API endpoints (`app/api/v1/endpoints/admin_relations.py`)
- [x] Registered router in `app/api/v1/router.py`

### ✅ Phase 3: Frontend Relations Management - COMPLETED
- [x] Created Relations page template (`app/templates/admin/relations/index.html.jinja`)
- [x] Created Jinja macros (`app/templates/admin/relations/macros.html.jinja`)
- [x] Created CSS styles (`app/static/css/relations.css`)
- [x] Created JavaScript (`app/static/js/relations.js`)

### ⏳ Phase 4: Profile Entry Integration - PENDING
- [ ] Remove add/remove option UI from profile template
- [ ] Implement cascading dropdowns in profile entry

## Access the Relations Page

Navigate to: `/api/v1/admin/relations`

---

## Problem Statement

- **Current Issue**: Profile page options are just text without relationships - data entry personnel (non-coders) can't manage hierarchical dependencies
- **Core Problem**: System doesn't enforce hierarchical relationships between Company → Material → Opening System → System Series → Colors
- **Solution Needed**: Relations page for data entry personnel to create dependency paths that update profile entry options

## Hierarchy Structure

**Fixed Hierarchy**: Company → Material → Opening System → System Series → Colors
**Dynamic Paths**: Each complete path creates a valid option combination

### Example Recorded Paths:
1. Kompen → UPVC → Casement → K700 → White
2. Kompen → UPVC → Casement → K600 → Red  
3. Kompen → Aluminum → Casement → K701 → Green
4. Kompen → Aluminum → Sliding → K800 → Blue

### Cascading Behavior in Profile Entry:
- Select **Kompen** → Material shows: **[UPVC, Aluminum]**
- Select **UPVC** → Opening System shows: **[Casement]**
- Select **Casement** → System Series shows: **[K700, K600]**
- Select **K700** → Colors shows: **[White]**

## Data Structure Using EAV Pattern

### Schema Change: Add image_url to AttributeNode
```python
# Add ONE new field to AttributeNode model:
image_url: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="Image/logo URL for the entity")
```

### AttributeNode Fields Mapping

| Data Need | AttributeNode Field |
|-----------|---------------------|
| Entity name | `name` |
| Entity type | `node_type` ('company', 'material', 'opening_system', 'system_series', 'color', 'unit_type') |
| Hierarchy level | `depth` (0=Company, 1=Material, 2=Opening System, 3=System Series, 4=Color) |
| Dependency path | `ltree_path` (e.g., "kompen.upvc.casement.k700.white") |
| Price (from €XX) | `price_impact_value` |
| Image/Logo | `image_url` (NEW FIELD) |
| Description | `description` |
| Extra metadata | `validation_rules` JSONB |

### LTREE Path Structure
```
# Company level (depth=0, node_type='company')
kompen
rehau

# Material level (depth=1, node_type='material')
kompen.upvc
kompen.aluminum

# Opening System level (depth=2, node_type='opening_system')
kompen.upvc.casement
kompen.upvc.sliding

# System Series level (depth=3, node_type='system_series')
kompen.upvc.casement.k700
kompen.upvc.casement.k600

# Color level (depth=4, node_type='color')
kompen.upvc.casement.k700.white
kompen.upvc.casement.k700.brown
```

### Metadata Storage in validation_rules JSONB
```json
// For a Material (e.g., UPVC)
{
  "density": 1.4,
  "is_relation_entity": true
}

// For a System Series (e.g., K700)
{
  "width": 70.0,
  "number_of_chambers": 5,
  "u_value": 1.1,
  "number_of_seals": 3,
  "characteristics": "Premium",
  "is_relation_entity": true
}

// For a Color (e.g., White)
{
  "code": "RAL9016",
  "has_lamination": false,
  "is_relation_entity": true
}
```

## Relations Page Design

### UI Layout (Card-Based, No Tree Visualization)
```
┌─────────────────────────────────────────────────────────────┐
│                     RELATIONS MANAGEMENT                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────────────────┐  ┌─────────────────┐   │
│  │         COMPANIES               │  │                 │   │
│  │                                 │  │     [IMAGE]     │   │
│  │ Name: [________________]        │  │                 │   │
│  │ Price From: [___________]       │  │                 │   │
│  │                                 │  │                 │   │
│  │           [Save Company]        │  │                 │   │
│  └─────────────────────────────────┘  └─────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────┐  ┌─────────────────┐   │
│  │         MATERIALS               │  │                 │   │
│  │                                 │  │     [IMAGE]     │   │
│  │ Name: [________________]        │  │                 │   │
│  │ Price From: [___________]       │  │                 │   │
│  │ Density: [______________]       │  │                 │   │
│  │                                 │  │                 │   │
│  │           [Save Material]       │  │                 │   │
│  └─────────────────────────────────┘  └─────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────┐  ┌─────────────────┐   │
│  │      OPENING SYSTEMS            │  │                 │   │
│  │                                 │  │     [IMAGE]     │   │
│  │ Name: [________________]        │  │                 │   │
│  │ Description: [__________]       │  │                 │   │
│  │ Price From: [___________]       │  │                 │   │
│  │                                 │  │                 │   │
│  │        [Save Opening System]    │  │                 │   │
│  └─────────────────────────────────┘  └─────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────┐  ┌─────────────────┐   │
│  │       SYSTEM SERIES             │  │                 │   │
│  │                                 │  │     [IMAGE]     │   │
│  │ Name: [________________]        │  │                 │   │
│  │ Width: [________________]       │  │                 │   │
│  │ Chambers: [_____________]       │  │                 │   │
│  │ U-Value: [______________]       │  │                 │   │
│  │ Seals: [________________]       │  │                 │   │
│  │ Characteristics: [______]       │  │                 │   │
│  │ Price From: [___________]       │  │                 │   │
│  │                                 │  │                 │   │
│  │        [Save System Series]     │  │                 │   │
│  └─────────────────────────────────┘  └─────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────┐  ┌─────────────────┐   │
│  │          COLORS                 │  │                 │   │
│  │                                 │  │     [IMAGE]     │   │
│  │ Name: [________________]        │  │                 │   │
│  │ Code: [________________]        │  │                 │   │
│  │ Has Lamination: [_______]       │  │                 │   │
│  │                                 │  │                 │   │
│  │           [Save Color]          │  │                 │   │
│  └─────────────────────────────────┘  └─────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────┐  ┌─────────────────┐   │
│  │        UNIT TYPES               │  │                 │   │
│  │  (Independent - No Hierarchy)   │  │     [IMAGE]     │   │
│  │                                 │  │                 │   │
│  │ Name: [________________]        │  │                 │   │
│  │ Description: [__________]       │  │                 │   │
│  │                                 │  │                 │   │
│  │         [Save Unit Type]        │  │                 │   │
│  └─────────────────────────────────┘  └─────────────────┘   │
│                                                             │
│                    PATH BUILDER                             │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ Create Complete Dependency Path:                        │ │
│  │                                                         │ │
│  │ Company: [Select Company ▼]                            │ │
│  │ Material: [Select Material ▼]                          │ │
│  │ Opening System: [Select Opening System ▼]              │ │
│  │ System Series: [Select System Series ▼]                │ │
│  │ Color: [Select Color ▼]                                │ │
│  │                                                         │ │
│  │                    [Create Path]                        │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Implementation Plan

### Phase 1: Database Schema Update

#### 1.1 Add image_url to AttributeNode Model
```python
# In app/models/attribute_node.py, add:
image_url: Mapped[str | None] = mapped_column(
    String(500),
    nullable=True,
    comment="Image/logo URL for the entity",
)
```

#### 1.2 Create Alembic Migration
```bash
alembic revision --autogenerate -m "add_image_url_to_attribute_nodes"
alembic upgrade head
```

### Phase 2: Backend Relations Management

#### 2.1 Relations Service (`app/services/relations.py`)
```python
class RelationsService(BaseService):
    # Hierarchy levels
    RELATION_LEVELS = {
        0: "company",
        1: "material",
        2: "opening_system",
        3: "system_series",
        4: "color"
    }
    
    # Entity types with their metadata fields (stored in validation_rules JSONB)
    ENTITY_METADATA = {
        'company': [],  # No extra metadata, just name, image_url, price_impact_value
        'material': ['density'],
        'opening_system': [],  # Uses description field
        'system_series': ['width', 'number_of_chambers', 'u_value', 'number_of_seals', 'characteristics'],
        'color': ['code', 'has_lamination'],
        'unit_type': []  # Independent, uses description field
    }
    
    # Key methods:
    async def create_entity(entity_type: str, data: dict) -> AttributeNode
    async def update_entity(entity_id: int, data: dict) -> AttributeNode
    async def delete_entity(entity_id: int) -> dict
    async def get_entities_by_type(entity_type: str) -> List[AttributeNode]
    async def create_dependency_path(path_data: dict) -> AttributeNode
    async def delete_dependency_path(ltree_path: str) -> dict
    async def get_dependent_options(parent_selections: dict) -> dict
    async def get_all_paths() -> List[dict]
```

#### 2.2 Relations API Endpoints (`app/api/v1/endpoints/admin_relations.py`)
- `GET /api/v1/admin/relations`: Relations management page (HTML)
- `POST /api/v1/admin/relations/entities`: Create entity
- `PUT /api/v1/admin/relations/entities/{id}`: Update entity
- `DELETE /api/v1/admin/relations/entities/{id}`: Delete entity
- `GET /api/v1/admin/relations/entities/{type}`: Get entities by type
- `POST /api/v1/admin/relations/paths`: Create dependency path
- `DELETE /api/v1/admin/relations/paths`: Delete dependency path
- `GET /api/v1/admin/relations/paths`: Get all paths
- `GET /api/v1/admin/relations/options`: Get dependent options (for cascading)

### Phase 3: Frontend Relations Management

#### 3.1 Relations Management Page (`app/templates/admin/relations/index.html.jinja`)
- Card-based layout for each entity type
- Form fields for entity data + image upload
- Path builder section for creating dependency chains
- List of existing paths with delete option

#### 3.2 Relations JavaScript (`app/static/js/relations.js`)
```javascript
class RelationsManager {
    // Entity CRUD
    async createEntity(entityType, formData)
    async updateEntity(entityId, formData)
    async deleteEntity(entityId)
    async getEntitiesByType(entityType)
    
    // Path management
    async createDependencyPath(pathData)
    async deleteDependencyPath(ltreePath)
    async getAllPaths()
    
    // Cascading options
    async getDependentOptions(parentSelections)
}
```

### Phase 4: Profile Entry Integration

#### 4.1 Remove Add/Remove Option UI from Profile Template
- Remove `__ADD_NEW__` and `__REMOVE__` option elements from dropdowns
- Remove add/remove option input containers
- Remove related Alpine.js state variables and methods
- Keep Python backend methods for backward compatibility

#### 4.2 Implement Cascading Dropdowns
- Update `FormHelpers.getFieldOptions()` to call relations API
- Add event listeners for parent field changes
- Clear and reload dependent field options on parent change
- Show only options that exist in recorded dependency paths

## Implementation Order

### Step 1: Schema Update
1. Add `image_url` field to AttributeNode model
2. Create and run Alembic migration

### Step 2: Backend
1. Create RelationsService with entity and path management
2. Create API endpoints for relations management
3. Add endpoint for cascading options

### Step 3: Relations Page UI
1. Create relations page template with card-based layout
2. Create JavaScript for entity CRUD and path management
3. Implement image upload functionality

### Step 4: Profile Entry Integration
1. Remove add/remove option UI from profile template
2. Update FormHelpers for cascading dropdown behavior
3. Test complete flow

## Example Usage Flow

### 1. Data Entry Personnel Creates Entities
```
Relations Page:
1. Create Company: "Kompen" (image, price_from: 100)
2. Create Material: "UPVC" (image, price_from: 50, density: 1.4)
3. Create Opening System: "Casement" (image, description, price_from: 30)
4. Create System Series: "K700" (image, width: 70, chambers: 5, u_value: 1.1, seals: 3, price_from: 80)
5. Create Color: "White" (image, code: RAL9016, has_lamination: false)
```

### 2. Data Entry Personnel Creates Dependency Path
```
Path Builder:
Company: Kompen → Material: UPVC → Opening System: Casement → System Series: K700 → Color: White
Result: Creates LTREE path "kompen.upvc.casement.k700.white"
```

### 3. User Uses Profile Entry
```
Profile Entry Form:
1. Select Company: "Kompen" → Material dropdown shows only: ["UPVC"]
2. Select Material: "UPVC" → Opening System shows: ["Casement"]
3. Select Opening System: "Casement" → System Series shows: ["K700"]
4. Select System Series: "K700" → Colors shows: ["White"]
5. Complete path validated and saved
```

## Benefits

1. **Minimal Schema Change**: Only adds `image_url` column to existing AttributeNode
2. **Uses Existing EAV Pattern**: Leverages LTREE, JSONB, and existing indexes
3. **User-Friendly**: Card-based interface for non-technical data entry personnel
4. **Data Integrity**: Only valid combinations available in profile entry
5. **Performance**: Uses existing LTREE GiST indexes for fast hierarchical queries
6. **Clean Separation**: Relations management separate from profile entry usage

## Reference

See `DECISION.md` for the full discussion and rationale behind these design decisions, including analysis of the windows24.com configurator as industry reference.
