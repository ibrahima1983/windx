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
                throw new Error(`Unknown scope: ${scope}. Available scopes: ${this.getAvailableScopes().join(', ')}`)
        }
    }
    
    static getAvailableScopes(): string[] {
        return ['profile', 'glazing']
    }
    
    static clearCache(): void {
        this.services.clear()
    }
    
    static hasService(scope: string): boolean {
        return this.getAvailableScopes().includes(scope)
    }
}

// Convenience exports
export const productDefinitionServiceFactory = ProductDefinitionServiceFactory

// Direct service exports
export { BaseProductDefinitionService } from './base'
export { ProfileProductDefinitionService } from './profile'
export { GlazingProductDefinitionService } from './glazing'

// Type exports
export * from './types'

// Legacy compatibility - create a default instance that delegates to the factory
// This maintains backward compatibility during the migration period
export const productDefinitionService = {
    // Generic Entity Operations (delegates to profile service for backward compatibility)
    async getEntities(type: string, scope?: string) {
        const serviceScope = scope || 'profile'
        const service = ProductDefinitionServiceFactory.getService(serviceScope)
        return await service.getEntities(type)
    },

    async createEntity(data: any) {
        // Determine scope from entity_type or default to profile
        const scope = this.determineScopeFromEntityType(data.entity_type) || 'profile'
        const service = ProductDefinitionServiceFactory.getService(scope)
        return await service.createEntity(data)
    },

    async updateEntity(id: number, data: any) {
        // Default to profile service for backward compatibility
        const service = ProductDefinitionServiceFactory.getService('profile')
        return await service.updateEntity(id, data)
    },

    async deleteEntity(id: number) {
        // Default to profile service for backward compatibility
        const service = ProductDefinitionServiceFactory.getService('profile')
        return await service.deleteEntity(id)
    },

    // Profile-specific operations (for backward compatibility)
    async getPaths() {
        const service = ProductDefinitionServiceFactory.getService('profile') as ProfileProductDefinitionService
        return await service.getPaths()
    },

    async getPathDetails(pathId: number) {
        const service = ProductDefinitionServiceFactory.getService('profile') as ProfileProductDefinitionService
        return await service.getPathDetails(pathId)
    },

    async createPath(data: any) {
        const service = ProductDefinitionServiceFactory.getService('profile') as ProfileProductDefinitionService
        return await service.createPath(data)
    },

    async deletePath(data: any) {
        const service = ProductDefinitionServiceFactory.getService('profile') as ProfileProductDefinitionService
        return await service.deletePath(data)
    },

    // Scope Operations
    async getScopes() {
        // This could be enhanced to call a backend endpoint, for now return available scopes
        const scopes = ProductDefinitionServiceFactory.getAvailableScopes()
        return {
            success: true,
            scopes: scopes.reduce((acc, scope) => {
                acc[scope] = { label: scope.charAt(0).toUpperCase() + scope.slice(1) }
                return acc
            }, {} as Record<string, any>)
        }
    },

    // Image Upload (common functionality)
    async uploadImage(file: File) {
        const service = ProductDefinitionServiceFactory.getService('profile')
        return await service.uploadImage(file)
    },

    // Helper method to determine scope from entity type
    determineScopeFromEntityType(entityType: string): string | null {
        // Profile entity types
        const profileTypes = ['company', 'material', 'opening_system', 'system_series', 'color']
        if (profileTypes.includes(entityType)) {
            return 'profile'
        }
        
        // Glazing entity types
        const glazingTypes = ['glass_type', 'spacer', 'gas']
        if (glazingTypes.includes(entityType)) {
            return 'glazing'
        }
        
        return null
    }
}