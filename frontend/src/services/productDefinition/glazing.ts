// Glazing-specific service (new implementation)
import { BaseProductDefinitionService } from './base'
import type { 
    GlazingComponentCreate, 
    GlazingUnitCreate, 
    GlazingUnitResponse,
    CalculationResult 
} from './types'

export class GlazingProductDefinitionService extends BaseProductDefinitionService {
    constructor() {
        super('glazing')
    }
    
    // Entity operations for glazing components
    async getEntities(type: string): Promise<any> {
        this.logger.debug('Getting glazing entities', { type })
        
        try {
            const response = await this.apiCall('get', `/entities/${type}`)
            
            this.logger.info('Successfully retrieved glazing entities', { 
                type, 
                count: response?.entities?.length 
            })
            
            return response
        } catch (error) {
            this.logger.error('Failed to get glazing entities', { type, error })
            throw error
        }
    }
    
    async createEntity(data: GlazingComponentCreate): Promise<any> {
        this.logger.debug('Creating glazing component', { componentType: data.component_type, name: data.name })
        
        try {
            const response = await this.apiCall('post', '/components', data)
            
            this.logger.info('Successfully created glazing component', { 
                componentId: response?.component?.id, 
                name: data.name 
            })
            
            return response
        } catch (error) {
            this.logger.error('Failed to create glazing component', { data, error })
            throw error
        }
    }
    
    async updateEntity(id: number, data: Partial<GlazingComponentCreate>): Promise<any> {
        this.logger.debug('Updating glazing component', { componentId: id, changes: Object.keys(data) })
        
        try {
            const updatePayload = this.prepareUpdatePayload(data)
            const response = await this.apiCall('put', `/components/${id}`, updatePayload)
            
            this.logger.info('Successfully updated glazing component', { 
                componentId: id, 
                updatedFields: Object.keys(updatePayload)
            })
            
            return response
        } catch (error) {
            this.logger.error('Failed to update glazing component', { componentId: id, data, error })
            throw error
        }
    }
    
    async deleteEntity(id: number): Promise<any> {
        this.logger.debug('Deleting glazing component', { componentId: id })
        
        try {
            const response = await this.apiCall('delete', `/components/${id}`)
            
            this.logger.info('Successfully deleted glazing component', { componentId: id })
            return response
        } catch (error) {
            this.logger.error('Failed to delete glazing component', { componentId: id, error })
            throw error
        }
    }
    
    // Glazing-specific operations
    async getAllComponents(): Promise<any> {
        this.logger.debug('Getting all glazing components')
        
        try {
            const response = await this.apiCall('get', '/components')
            
            this.logger.info('Successfully retrieved all glazing components', {
                glassTypes: response?.glass_types?.length || 0,
                spacers: response?.spacers?.length || 0,
                gases: response?.gases?.length || 0
            })
            
            return response
        } catch (error) {
            this.logger.error('Failed to get all glazing components', { error })
            throw error
        }
    }
    
    async createGlazingUnit(data: GlazingUnitCreate): Promise<GlazingUnitResponse> {
        this.logger.debug('Creating glazing unit', { 
            name: data.name, 
            glazingType: data.glazing_type 
        })
        
        try {
            const response = await this.apiCall('post', '/glazing-units', data)
            
            this.logger.info('Successfully created glazing unit', { 
                name: data.name,
                glazingType: data.glazing_type,
                totalThickness: response?.calculated_properties?.total_thickness,
                uValue: response?.calculated_properties?.u_value
            })
            
            return response
        } catch (error) {
            this.logger.error('Failed to create glazing unit', { data, error })
            throw error
        }
    }
    
    async calculateGlazingProperties(unitData: Partial<GlazingUnitCreate>): Promise<CalculationResult> {
        this.logger.debug('Calculating glazing properties', { 
            glazingType: unitData.glazing_type 
        })
        
        try {
            const response = await this.apiCall('post', '/calculate', unitData)
            
            this.logger.info('Successfully calculated glazing properties', {
                glazingType: unitData.glazing_type,
                totalThickness: response?.total_thickness,
                uValue: response?.u_value,
                pricePerSqm: response?.price_per_sqm
            })
            
            return response
        } catch (error) {
            this.logger.error('Failed to calculate glazing properties', { unitData, error })
            throw error
        }
    }
    
    // Glazing component type helpers
    async getGlassTypes(): Promise<any> {
        return await this.getEntities('glass_type')
    }
    
    async getSpacers(): Promise<any> {
        return await this.getEntities('spacer')
    }
    
    async getGases(): Promise<any> {
        return await this.getEntities('gas')
    }
    
    // Create specific component types
    async createGlassType(data: Omit<GlazingComponentCreate, 'component_type'>): Promise<any> {
        return await this.createEntity({ ...data, component_type: 'glass_type' })
    }
    
    async createSpacer(data: Omit<GlazingComponentCreate, 'component_type'>): Promise<any> {
        return await this.createEntity({ ...data, component_type: 'spacer' })
    }
    
    async createGas(data: Omit<GlazingComponentCreate, 'component_type'>): Promise<any> {
        return await this.createEntity({ ...data, component_type: 'gas' })
    }
}