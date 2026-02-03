// Profile-specific service (migrated logic)
import { BaseProductDefinitionService } from './base'
import { apiClient } from '@/services/api'
import type { 
    EntityCreateRequest, 
    EntityUpdateRequest, 
    ProfilePathCreate, 
    PathDeleteRequest,
    ProfileDependentOptionsRequest 
} from './types'

export class ProfileProductDefinitionService extends BaseProductDefinitionService {
    constructor() {
        super('profile')
    }
    
    // Entity operations
    async getEntities(type: string, scope?: string): Promise<any> {
        this.logger.debug('Getting profile entities', { type, scope })
        
        try {
            const params = scope ? { scope } : {}
            const response = await apiClient.get(`/api/v1/admin/product-definitions/entities/${type}`, {
                params
            })
            
            this.logger.info('Successfully retrieved profile entities', { 
                type, 
                scope, 
                count: response.data?.entities?.length 
            })
            
            return response.data
        } catch (error) {
            this.logger.error('Failed to get profile entities', { type, scope, error })
            throw error
        }
    }
    
    async createEntity(data: EntityCreateRequest): Promise<any> {
        this.logger.debug('Creating profile entity', { entityType: data.entity_type, name: data.name })
        
        try {
            const response = await apiClient.post('/api/v1/admin/product-definitions/entities', data)
            
            this.logger.info('Successfully created profile entity', { 
                entityId: response.data?.entity?.id, 
                name: data.name 
            })
            
            return response.data
        } catch (error) {
            this.logger.error('Failed to create profile entity', { data, error })
            throw error
        }
    }
    
    async updateEntity(id: number, data: EntityUpdateRequest): Promise<any> {
        this.logger.debug('Updating profile entity', { entityId: id, changes: Object.keys(data) })
        
        try {
            const updatePayload = this.prepareUpdatePayload(data)
            
            // Handle profile-specific fields
            if (data.price_from !== undefined) {
                updatePayload.price_from = data.price_from
            }
            
            this.logger.debug('Prepared profile update payload', { entityId: id, payload: updatePayload })
            
            const response = await apiClient.put(`/api/v1/admin/product-definitions/entities/${id}`, updatePayload)
            
            this.logger.info('Successfully updated profile entity', { 
                entityId: id, 
                updatedFields: Object.keys(updatePayload),
                entityName: response.data?.entity?.name 
            })
            
            return response.data
        } catch (error) {
            this.logger.error('Failed to update profile entity', { entityId: id, data, error })
            throw error
        }
    }
    
    async deleteEntity(id: number): Promise<any> {
        this.logger.debug('Deleting profile entity', { entityId: id })
        
        try {
            const response = await apiClient.delete(`/api/v1/admin/product-definitions/entities/${id}`)
            
            this.logger.info('Successfully deleted profile entity', { entityId: id })
            return response.data
        } catch (error) {
            this.logger.error('Failed to delete profile entity', { entityId: id, error })
            throw error
        }
    }
    
    // Profile-specific path operations
    async getPaths(): Promise<any> {
        this.logger.debug('Getting all profile paths')
        
        try {
            const response = await apiClient.get('/api/v1/admin/product-definitions/paths')
            const paths = response.data.paths || []
            
            this.logger.info('Successfully retrieved profile paths', { count: paths.length })
            return paths
        } catch (error) {
            this.logger.error('Failed to get profile paths', { error })
            throw error
        }
    }
    
    async getPathDetails(pathId: number): Promise<any> {
        this.logger.debug('Getting profile path details', { pathId })
        
        try {
            const response = await apiClient.get(`/api/v1/admin/product-definitions/paths/${pathId}`)
            const entityCount = response.data?.path?.entities ? Object.keys(response.data.path.entities).length : 0
            
            this.logger.info('Successfully retrieved profile path details', { 
                pathId, 
                entityCount,
                ltreePath: response.data?.path?.ltree_path 
            })
            
            return response.data
        } catch (error) {
            this.logger.error('Failed to get profile path details', { pathId, error })
            throw error
        }
    }
    
    async createPath(data: ProfilePathCreate): Promise<any> {
        this.logger.debug('Creating profile path', { data })
        
        try {
            const response = await apiClient.post('/api/v1/admin/product-definitions/paths', data)
            
            this.logger.info('Successfully created profile path', { 
                pathId: response.data?.path?.id,
                ltreePath: response.data?.path?.ltree_path 
            })
            
            return response.data
        } catch (error) {
            this.logger.error('Failed to create profile path', { data, error })
            throw error
        }
    }
    
    async deletePath(data: PathDeleteRequest): Promise<any> {
        this.logger.debug('Deleting profile path', { ltreePath: data.ltree_path })
        
        try {
            const response = await apiClient.delete('/api/v1/admin/product-definitions/paths', { data })
            
            this.logger.info('Successfully deleted profile path', { ltreePath: data.ltree_path })
            return response.data
        } catch (error) {
            this.logger.error('Failed to delete profile path', { data, error })
            throw error
        }
    }
    
    // Profile-specific dependent options
    async getDependentOptions(selections: ProfileDependentOptionsRequest): Promise<any> {
        this.logger.debug('Getting profile dependent options', { selections })
        
        try {
            const response = await this.apiCall('post', '/options', selections)
            
            this.logger.info('Successfully retrieved profile dependent options')
            return response
        } catch (error) {
            this.logger.error('Failed to get profile dependent options', { selections, error })
            throw error
        }
    }
}