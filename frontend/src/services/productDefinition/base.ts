// Base service with common functionality
import { apiClient } from '@/services/api'
import { useDebugLogger } from '@/composables/useDebugLogger'

export abstract class BaseProductDefinitionService {
    protected scope: string
    protected logger: ReturnType<typeof useDebugLogger>
    
    constructor(scope: string) {
        this.scope = scope
        this.logger = useDebugLogger(`ProductDefinitionService:${scope}`)
    }
    
    // Abstract methods that must be implemented by scope-specific services
    abstract getEntities(type: string): Promise<any>
    abstract createEntity(data: any): Promise<any>
    abstract updateEntity(id: number, data: any): Promise<any>
    abstract deleteEntity(id: number): Promise<any>
    
    // Common methods available to all scope-specific services
    protected async apiCall(method: 'get' | 'post' | 'put' | 'delete', endpoint: string, data?: any): Promise<any> {
        const url = `/api/v1/admin/product-definitions/${this.scope}${endpoint}`
        this.logger.debug(`API call: ${method.toUpperCase()} ${url}`, { data })
        
        try {
            let response
            switch (method) {
                case 'get':
                    response = await apiClient.get(url, data ? { params: data } : undefined)
                    break
                case 'post':
                    response = await apiClient.post(url, data)
                    break
                case 'put':
                    response = await apiClient.put(url, data)
                    break
                case 'delete':
                    response = await apiClient.delete(url, data ? { data } : undefined)
                    break
            }
            
            this.logger.info(`API call successful: ${method.toUpperCase()} ${url}`)
            return response.data
        } catch (error) {
            this.logger.error(`API call failed: ${method.toUpperCase()} ${url}`, { error })
            throw error
        }
    }
    
    // Common image upload functionality
    async uploadImage(file: File): Promise<any> {
        this.logger.debug('Uploading image', { fileName: file.name, fileSize: file.size })
        
        try {
            const formData = new FormData()
            formData.append('file', file)
            const response = await apiClient.post('/api/v1/admin/entry/upload-image', formData, {
                headers: { 'Content-Type': 'multipart/form-data' }
            })
            
            this.logger.info('Successfully uploaded image', { 
                fileName: file.name, 
                imageUrl: response.data?.image_url 
            })
            
            return response.data
        } catch (error) {
            this.logger.error('Failed to upload image', { fileName: file.name, error })
            throw error
        }
    }
    
    // Common scope metadata retrieval
    async getScopeMetadata(): Promise<any> {
        this.logger.debug('Getting scope metadata')
        
        try {
            const response = await this.apiCall('get', '/metadata')
            this.logger.info('Successfully retrieved scope metadata')
            return response
        } catch (error) {
            this.logger.error('Failed to get scope metadata', { error })
            throw error
        }
    }
    
    // Helper method to prepare update payload
    protected prepareUpdatePayload(data: any): any {
        const updatePayload: any = {}
        
        // Copy defined fields
        Object.keys(data).forEach(key => {
            if (data[key] !== undefined) {
                updatePayload[key] = data[key]
            }
        })
        
        // Clean up empty metadata
        if (updatePayload.metadata && Object.keys(updatePayload.metadata).length === 0) {
            delete updatePayload.metadata
        }
        
        return updatePayload
    }
}