import { productDefinitionServiceFactory } from '@/services/productDefinition'
import { parseApiError } from '@/utils/errorHandler'

// Types for schema definition
export interface FieldDefinition {
    name: string
    label: string
    type: 'text' | 'number' | 'boolean' | 'textarea' | 'checkbox' // Enhanced types
    required?: boolean
    options?: { label: string; value: any }[]
    hidden?: boolean
    metadata_?: { placeholder?: string }
}

export interface EntityTypeDefinition {
    value: string
    label: string
    icon: string
    fields: FieldDefinition[]
    hasImage?: boolean
    isLinker?: boolean
    specialUi?: {
        type: string
        config: Record<string, any>
    }
}

export interface ChainNodeDefinition {
    key: string
    label: string
    icon: string
    entityType: string
}

export interface DefinitionSchema {
    title: string
    entityTypes: EntityTypeDefinition[]
    chainStructure: ChainNodeDefinition[]
}

// Dynamic Schema Builder
export async function fetchAndBuildSchemas(): Promise<Record<string, DefinitionSchema>> {
    try {
        // Get available scopes from factory
        const availableScopes = productDefinitionServiceFactory.getAvailableScopes()
        const schemas: Record<string, DefinitionSchema> = {}

        // For now, create basic schemas for each scope
        // In the future, this could be enhanced to fetch schema definitions from the backend
        for (const scope of availableScopes) {
            if (scope === 'profile') {
                schemas[scope] = {
                    title: 'Profile System',
                    entityTypes: [
                        {
                            value: 'company',
                            label: 'Company',
                            icon: 'pi pi-building',
                            fields: [
                                { name: 'name', label: 'Name', type: 'text', required: true },
                                { name: 'description', label: 'Description', type: 'textarea' },
                                { name: 'price_from', label: 'Price From', type: 'number' }
                            ],
                            hasImage: true
                        },
                        {
                            value: 'material',
                            label: 'Material',
                            icon: 'pi pi-box',
                            fields: [
                                { name: 'name', label: 'Name', type: 'text', required: true },
                                { name: 'description', label: 'Description', type: 'textarea' },
                                { name: 'price_from', label: 'Price From', type: 'number' }
                            ],
                            hasImage: true
                        },
                        {
                            value: 'opening_system',
                            label: 'Opening System',
                            icon: 'pi pi-arrows-alt',
                            fields: [
                                { name: 'name', label: 'Name', type: 'text', required: true },
                                { name: 'description', label: 'Description', type: 'textarea' },
                                { name: 'price_from', label: 'Price From', type: 'number' }
                            ],
                            hasImage: true
                        },
                        {
                            value: 'system_series',
                            label: 'System Series',
                            icon: 'pi pi-list',
                            fields: [
                                { name: 'name', label: 'Name', type: 'text', required: true },
                                { name: 'description', label: 'Description', type: 'textarea' },
                                { name: 'price_from', label: 'Price From', type: 'number' }
                            ],
                            hasImage: true
                        },
                        {
                            value: 'color',
                            label: 'Color',
                            icon: 'pi pi-palette',
                            fields: [
                                { name: 'name', label: 'Name', type: 'text', required: true },
                                { name: 'description', label: 'Description', type: 'textarea' },
                                { name: 'price_from', label: 'Price From', type: 'number' }
                            ],
                            hasImage: true
                        }
                    ],
                    chainStructure: [
                        { key: 'company', entityType: 'company', label: 'Company', icon: 'pi pi-building' },
                        { key: 'material', entityType: 'material', label: 'Material', icon: 'pi pi-box' },
                        { key: 'opening_system', entityType: 'opening_system', label: 'Opening System', icon: 'pi pi-arrows-alt' },
                        { key: 'system_series', entityType: 'system_series', label: 'System Series', icon: 'pi pi-list' },
                        { key: 'color', entityType: 'color', label: 'Color', icon: 'pi pi-palette' }
                    ]
                }
            } else if (scope === 'glazing') {
                schemas[scope] = {
                    title: 'Glazing System',
                    entityTypes: [
                        {
                            value: 'glass_type',
                            label: 'Glass Type',
                            icon: 'pi pi-stop',
                            fields: [
                                { name: 'name', label: 'Name', type: 'text', required: true },
                                { name: 'description', label: 'Description', type: 'textarea' },
                                { name: 'thickness', label: 'Thickness (mm)', type: 'number' },
                                { name: 'u_value', label: 'U-Value', type: 'number' },
                                { name: 'light_transmittance', label: 'Light Transmittance', type: 'number' },
                                { name: 'price_per_sqm', label: 'Price per m²', type: 'number' }
                            ],
                            hasImage: true
                        },
                        {
                            value: 'spacer',
                            label: 'Spacer',
                            icon: 'pi pi-minus',
                            fields: [
                                { name: 'name', label: 'Name', type: 'text', required: true },
                                { name: 'description', label: 'Description', type: 'textarea' },
                                { name: 'material', label: 'Material', type: 'text' },
                                { name: 'thickness', label: 'Thickness (mm)', type: 'number' },
                                { name: 'thermal_conductivity', label: 'Thermal Conductivity', type: 'number' },
                                { name: 'price_per_sqm', label: 'Price per m²', type: 'number' }
                            ],
                            hasImage: true
                        },
                        {
                            value: 'gas',
                            label: 'Gas Filling',
                            icon: 'pi pi-cloud',
                            fields: [
                                { name: 'name', label: 'Name', type: 'text', required: true },
                                { name: 'description', label: 'Description', type: 'textarea' },
                                { name: 'density', label: 'Density', type: 'number' },
                                { name: 'price_per_sqm', label: 'Price per m²', type: 'number' }
                            ],
                            hasImage: true
                        }
                    ],
                    chainStructure: [] // Glazing doesn't use chain structure like profile
                }
            }
        }

        return schemas
    } catch (error) {
        console.error('Error fetching schemas:', error)
        const errorMessage = parseApiError(error)
        throw new Error(`Failed to load definition schemas: ${errorMessage}`)
    }
}
