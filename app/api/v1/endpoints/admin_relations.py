"""Admin Relations API endpoints.

This module provides API endpoints for managing hierarchical option
dependencies (Company → Material → Opening System → System Series → Colors).

Public Variables:
    router: FastAPI router for relations endpoints
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.api.types import CurrentSuperuser
from app.core.rbac_template_helpers import RBACTemplateMiddleware
from app.services.relations import RelationsService

__all__ = ["router"]

router = APIRouter()

# Initialize templates with RBAC middleware
templates = Jinja2Templates(directory="app/templates")
rbac_templates = RBACTemplateMiddleware(templates)


# ============================================================================
# Pydantic Schemas
# ============================================================================

class EntityCreate(BaseModel):
    """Schema for creating a relation entity."""
    
    entity_type: str = Field(..., description="Type: company, material, opening_system, system_series, color, unit_type")
    name: str = Field(..., min_length=1, max_length=200)
    image_url: str | None = Field(None, max_length=500)
    price_from: Decimal | None = Field(None, ge=0)
    description: str | None = Field(None)
    metadata: dict[str, Any] | None = Field(None, description="Extra metadata (density, u_value, etc.)")


class EntityUpdate(BaseModel):
    """Schema for updating a relation entity."""
    
    name: str | None = Field(None, min_length=1, max_length=200)
    image_url: str | None = Field(None, max_length=500)
    price_from: Decimal | None = Field(None, ge=0)
    description: str | None = Field(None)
    metadata: dict[str, Any] | None = Field(None)


class PathCreate(BaseModel):
    """Schema for creating a dependency path."""
    
    company_id: int = Field(..., gt=0)
    material_id: int = Field(..., gt=0)
    opening_system_id: int = Field(..., gt=0)
    system_series_id: int = Field(..., gt=0)
    color_id: int = Field(..., gt=0)


class PathDelete(BaseModel):
    """Schema for deleting a dependency path."""
    
    ltree_path: str = Field(..., min_length=1)


class DependentOptionsRequest(BaseModel):
    """Schema for requesting dependent options."""
    
    company_id: int | None = None
    material_id: int | None = None
    opening_system_id: int | None = None
    system_series_id: int | None = None


# ============================================================================
# HTML Page Endpoint
# ============================================================================

@router.get("/relations", response_class=HTMLResponse, name="admin_relations")
async def relations_page(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentSuperuser = None,
):
    """Render the Relations management page.
    
    Requires superuser access for full RBAC integration.
    """
    # Store user in request state for RBAC middleware
    request.state.user = current_user
    
    service = RelationsService(db)
    
    # Get all entities grouped by type
    entities = await service.get_all_entities()
    
    return await rbac_templates.render_with_rbac(
        "admin/relations/index.html.jinja",
        request,
        {
            "active_page": "relations",
            "entities": entities,
        },
    )


@router.get("/relations/test", response_class=HTMLResponse, name="test_system_series")
async def test_system_series_page(request: Request) -> HTMLResponse:
    """Test page for System Series auto-population."""
    html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>System Series Auto-Population Test</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
        }
        .form-group {
            margin-bottom: 15px;
        }
        label {
            display: block;
            margin-bottom: 5px;
            font-weight: bold;
        }
        select, input {
            width: 100%;
            padding: 8px;
            border: 1px solid #ddd;
            border-radius: 4px;
        }
        .loading {
            color: #666;
            font-style: italic;
        }
        .auto-populated {
            background-color: #f0f8ff;
            border-color: #4a90e2;
        }
        .color-chips {
            display: flex;
            flex-wrap: wrap;
            gap: 5px;
            margin-top: 5px;
        }
        .color-chip {
            background: #e3f2fd;
            border: 1px solid #2196f3;
            border-radius: 12px;
            padding: 4px 8px;
            font-size: 12px;
            color: #1976d2;
        }
        .results {
            margin-top: 20px;
            padding: 15px;
            background: #f5f5f5;
            border-radius: 4px;
        }
        .success { color: #4caf50; }
        .error { color: #f44336; }
    </style>
</head>
<body>
    <h1>System Series Auto-Population Test</h1>
    
    <div class="form-group">
        <label for="system_series">System Series:</label>
        <select id="system_series" onchange="handleSystemSeriesChange()">
            <option value="">Select System Series...</option>
            <option value="K600" data-id="81">K600</option>
            <option value="K700" data-id="80">K700</option>
            <option value="K701" data-id="82">K701</option>
            <option value="K800" data-id="83">K800</option>
        </select>
    </div>

    <div class="form-group">
        <label for="company">Company:</label>
        <select id="company" disabled>
            <option value="">Select System Series first...</option>
        </select>
    </div>

    <div class="form-group">
        <label for="material">Material:</label>
        <select id="material" disabled>
            <option value="">Select System Series first...</option>
        </select>
    </div>

    <div class="form-group">
        <label for="opening_system">Opening System:</label>
        <select id="opening_system" disabled>
            <option value="">Select System Series first...</option>
        </select>
    </div>

    <div class="form-group">
        <label for="colours">Colors:</label>
        <div id="colours_display" class="color-chips"></div>
        <select id="colours" multiple style="display: none;">
        </select>
    </div>

    <div class="results" id="results" style="display: none;">
        <h3>API Response:</h3>
        <pre id="api_response"></pre>
    </div>

    <div id="status" style="margin-top: 20px;"></div>

    <script>
        let authToken = null;

        // Login and get token
        async function login() {
            try {
                const response = await fetch('/api/v1/auth/login', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        username: 'admin',
                        password: 'AdminPassword123!'
                    })
                });
                
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                
                const data = await response.json();
                authToken = data.access_token;
                document.getElementById('status').innerHTML = '<span class="success">✅ Logged in successfully</span>';
                console.log('✅ Logged in successfully');
            } catch (error) {
                document.getElementById('status').innerHTML = `<span class="error">❌ Login failed: ${error.message}</span>`;
                console.error('❌ Login failed:', error);
            }
        }

        async function handleSystemSeriesChange() {
            const select = document.getElementById('system_series');
            const selectedOption = select.options[select.selectedIndex];
            
            if (!selectedOption.value) {
                resetFields();
                return;
            }

            const systemSeriesId = selectedOption.dataset.id;
            const systemSeriesName = selectedOption.value;
            
            console.log(`🔄 System Series changed: ${systemSeriesName} (ID: ${systemSeriesId})`);
            
            if (!authToken) {
                document.getElementById('status').innerHTML = '<span class="error">❌ Not logged in</span>';
                return;
            }
            
            // Show loading state
            setLoadingState();
            
            try {
                const response = await fetch('/api/v1/admin/relations/options', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${authToken}`
                    },
                    body: JSON.stringify({
                        system_series_id: parseInt(systemSeriesId)
                    })
                });
                
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                
                const data = await response.json();
                console.log('📦 API Response:', data);
                
                // Show raw response
                document.getElementById('results').style.display = 'block';
                document.getElementById('api_response').textContent = JSON.stringify(data, null, 2);
                
                if (data.success && data.options) {
                    populateFields(data.options);
                    document.getElementById('status').innerHTML = '<span class="success">✅ Auto-population successful</span>';
                } else {
                    console.error('❌ API returned error:', data);
                    document.getElementById('status').innerHTML = `<span class="error">❌ API error: ${JSON.stringify(data)}</span>`;
                }
                
            } catch (error) {
                console.error('❌ API call failed:', error);
                document.getElementById('status').innerHTML = `<span class="error">❌ API call failed: ${error.message}</span>`;
                resetFields();
            }
        }

        function setLoadingState() {
            const fields = ['company', 'material', 'opening_system'];
            fields.forEach(fieldName => {
                const select = document.getElementById(fieldName);
                select.innerHTML = '<option value="">Loading...</option>';
                select.disabled = true;
                select.classList.add('loading');
            });
            
            document.getElementById('colours_display').innerHTML = '<span class="loading">Loading colors...</span>';
            document.getElementById('status').innerHTML = '<span class="loading">🔄 Loading auto-population data...</span>';
        }

        function populateFields(options) {
            // Populate Company
            if (options.company && options.company.length > 0) {
                const companySelect = document.getElementById('company');
                companySelect.innerHTML = '';
                options.company.forEach(company => {
                    const option = document.createElement('option');
                    option.value = company.name;
                    option.textContent = company.name;
                    option.selected = true;
                    companySelect.appendChild(option);
                });
                companySelect.disabled = true;
                companySelect.classList.add('auto-populated');
                companySelect.classList.remove('loading');
            }

            // Populate Material
            if (options.material && options.material.length > 0) {
                const materialSelect = document.getElementById('material');
                materialSelect.innerHTML = '';
                options.material.forEach(material => {
                    const option = document.createElement('option');
                    option.value = material.name;
                    option.textContent = material.name;
                    option.selected = true;
                    materialSelect.appendChild(option);
                });
                materialSelect.disabled = true;
                materialSelect.classList.add('auto-populated');
                materialSelect.classList.remove('loading');
            }

            // Populate Opening System
            if (options.opening_system && options.opening_system.length > 0) {
                const openingSystemSelect = document.getElementById('opening_system');
                openingSystemSelect.innerHTML = '';
                options.opening_system.forEach(openingSystem => {
                    const option = document.createElement('option');
                    option.value = openingSystem.name;
                    option.textContent = openingSystem.name;
                    option.selected = true;
                    openingSystemSelect.appendChild(option);
                });
                openingSystemSelect.disabled = true;
                openingSystemSelect.classList.add('auto-populated');
                openingSystemSelect.classList.remove('loading');
            }

            // Populate Colors
            if (options.colors && options.colors.length > 0) {
                const coloursDisplay = document.getElementById('colours_display');
                coloursDisplay.innerHTML = '';
                options.colors.forEach(color => {
                    const chip = document.createElement('span');
                    chip.className = 'color-chip';
                    chip.textContent = color.name;
                    coloursDisplay.appendChild(chip);
                });
            }
        }

        function resetFields() {
            const fields = ['company', 'material', 'opening_system'];
            fields.forEach(fieldName => {
                const select = document.getElementById(fieldName);
                select.innerHTML = '<option value="">Select System Series first...</option>';
                select.disabled = true;
                select.classList.remove('auto-populated', 'loading');
            });
            
            document.getElementById('colours_display').innerHTML = '';
            document.getElementById('results').style.display = 'none';
            document.getElementById('status').innerHTML = '';
        }

        // Initialize
        window.onload = async function() {
            await login();
            resetFields();
        };
    </script>
</body>
</html>
    """
    
    return HTMLResponse(content=html_content)


# ============================================================================
# Entity CRUD Endpoints
# ============================================================================

@router.post("/relations/entities", status_code=status.HTTP_201_CREATED)
async def create_entity(
    data: EntityCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentSuperuser = None,
) -> dict[str, Any]:
    """Create a new relation entity."""
    service = RelationsService(db)
    
    try:
        entity = await service.create_entity(
            entity_type=data.entity_type,
            name=data.name,
            image_url=data.image_url,
            price_from=data.price_from,
            description=data.description,
            metadata=data.metadata,
        )
        
        return {
            "success": True,
            "message": f"{data.entity_type.replace('_', ' ').title()} '{data.name}' created",
            "entity": {
                "id": entity.id,
                "name": entity.name,
                "node_type": entity.node_type,
                "image_url": entity.image_url,
                "price_impact_value": str(entity.price_impact_value) if entity.price_impact_value else None,
                "description": entity.description,
                "validation_rules": entity.validation_rules,
            },
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/relations/entities/{entity_id}")
async def update_entity(
    entity_id: int,
    data: EntityUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentSuperuser = None,
) -> dict[str, Any]:
    """Update an existing relation entity."""
    service = RelationsService(db)
    
    entity = await service.update_entity(
        entity_id=entity_id,
        name=data.name,
        image_url=data.image_url,
        price_from=data.price_from,
        description=data.description,
        metadata=data.metadata,
    )
    
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    
    return {
        "success": True,
        "message": f"Entity '{entity.name}' updated",
        "entity": {
            "id": entity.id,
            "name": entity.name,
            "node_type": entity.node_type,
            "image_url": entity.image_url,
            "price_impact_value": str(entity.price_impact_value) if entity.price_impact_value else None,
            "description": entity.description,
            "validation_rules": entity.validation_rules,
        },
    }


@router.delete("/relations/entities/{entity_id}")
async def delete_entity(
    entity_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentSuperuser = None,
) -> dict[str, Any]:
    """Delete a relation entity."""
    service = RelationsService(db)
    result = await service.delete_entity(entity_id)
    
    if not result["success"]:
        raise HTTPException(status_code=404, detail=result["message"])
    
    return result


@router.get("/relations/entities/{entity_type}")
async def get_entities_by_type(
    entity_type: str,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentSuperuser = None,
) -> dict[str, Any]:
    """Get all entities of a specific type."""
    if entity_type not in RelationsService.ENTITY_METADATA:
        raise HTTPException(status_code=400, detail=f"Invalid entity type: {entity_type}")
    
    service = RelationsService(db)
    entities = await service.get_entities_by_type(entity_type)
    
    return {
        "success": True,
        "entities": [
            {
                "id": e.id,
                "name": e.name,
                "node_type": e.node_type,
                "image_url": e.image_url,
                "price_impact_value": str(e.price_impact_value) if e.price_impact_value else None,
                "description": e.description,
                "validation_rules": e.validation_rules,
            }
            for e in entities
        ],
    }


# ============================================================================
# Path Management Endpoints
# ============================================================================

@router.post("/relations/paths", status_code=status.HTTP_201_CREATED)
async def create_path(
    data: PathCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentSuperuser = None,
) -> dict[str, Any]:
    """Create a new dependency path."""
    service = RelationsService(db)
    
    try:
        path_node = await service.create_dependency_path(
            company_id=data.company_id,
            material_id=data.material_id,
            opening_system_id=data.opening_system_id,
            system_series_id=data.system_series_id,
            color_id=data.color_id,
        )
        
        return {
            "success": True,
            "message": "Dependency path created",
            "path": {
                "id": path_node.id,
                "ltree_path": path_node.ltree_path,
                "description": path_node.description,
            },
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/relations/paths")
async def delete_path(
    data: PathDelete,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentSuperuser = None,
) -> dict[str, Any]:
    """Delete a dependency path."""
    service = RelationsService(db)
    result = await service.delete_dependency_path(data.ltree_path)
    
    if not result["success"]:
        raise HTTPException(status_code=404, detail=result["message"])
    
    return result


@router.get("/relations/paths")
async def get_all_paths(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentSuperuser = None,
) -> dict[str, Any]:
    """Get all dependency paths."""
    service = RelationsService(db)
    paths = await service.get_all_paths()
    
    return {
        "success": True,
        "paths": paths,
    }


# ============================================================================
# Cascading Options Endpoint
# ============================================================================

@router.post("/relations/options")
async def get_dependent_options(
    data: DependentOptionsRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get dependent options based on parent selections.
    
    Used for cascading dropdowns in profile entry.
    Note: This endpoint doesn't require authentication as it's used by the public profile entry.
    """
    service = RelationsService(db)
    
    parent_selections = {
        "company_id": data.company_id,
        "material_id": data.material_id,
        "opening_system_id": data.opening_system_id,
        "system_series_id": data.system_series_id,
    }
    
    options = await service.get_dependent_options(parent_selections)
    
    return {
        "success": True,
        "options": options,
    }
