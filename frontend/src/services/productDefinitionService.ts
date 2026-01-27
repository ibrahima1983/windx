import { apiClient } from '@/services/api'

// Interfaces aligned with Backend Pydantic Schemas (app.api.v1.endpoints.admin_relations)

export interface EntityCreateRequest {
    entity_type: string
    name: string
    image_url?: string | null
    price_from?: number | null
    description?: string | null
    metadata?: Record<string, any>
}

export interface EntityUpdateRequest {
    name?: string
    image_url?: string | null
    price_from?: number | null
    description?: string | null
    metadata?: Record<string, any>
}

export interface PathCreateRequest {
    company_id: number
    material_id: number
    opening_system_id: number
    system_series_id: number
    color_id: number
}

export interface PathDeleteRequest {
    ltree_path: string
}

export interface RelationEntity {
    id: number
    name: string
    node_type: string
    image_url: string | null
    price_impact_value: string | null
    description: string | null
    validation_rules: Record<string, any>
    metadata_?: Record<string, any>  // UI metadata from backend
}

export interface GetEntitiesResponse {
    success: boolean
    entities: RelationEntity[]
    type_metadata?: Record<string, any>  // Type-level UI metadata
}

export const productDefinitionService = {
    // Generic Entity Operations
    async getEntities(type: string) {
        const response = await apiClient.get(`/api/v1/admin/relations/entities/${type}`)
        return response.data
    },

    async createEntity(data: EntityCreateRequest) {
        const response = await apiClient.post('/api/v1/admin/relations/entities', data)
        return response.data
    },

    async updateEntity(id: number, data: EntityUpdateRequest) {
        // endpoint convention: params usually go before body, but here type is just for context/logging if needed or separate logic
        // The backend update endpoint is /relations/entities/{entity_id}, doesn't explicitly need type in body unless logic requires it
        const response = await apiClient.put(`/api/v1/admin/relations/entities/${id}`, data)
        return response.data
    },

    async deleteEntity(id: number) {
        const response = await apiClient.delete(`/api/v1/admin/relations/entities/${id}`)
        return response.data
    },

    // Path/Chain Operations
    async getPaths() {
        const response = await apiClient.get('/api/v1/admin/relations/paths')
        return response.data.paths || []
    },

    async createPath(data: PathCreateRequest) {
        const response = await apiClient.post('/api/v1/admin/relations/paths', data)
        return response.data
    },

    async deletePath(data: PathDeleteRequest) {
        const response = await apiClient.delete('/api/v1/admin/relations/paths', { data })
        return response.data
    },

    // Image Upload (Re-using generic endpoint from legacy code context)
    async uploadImage(file: File) {
        const formData = new FormData()
        formData.append('file', file)
        const response = await apiClient.post('/api/v1/admin/entry/upload-image', formData, {
            headers: { 'Content-Type': 'multipart/form-data' }
        })
        return response.data
    }
}
