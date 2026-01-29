import { productDefinitionService } from '@/services/productDefinitionService'

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
        const response = await productDefinitionService.getScopes()

        if (!response || !response.success || !response.scopes) {
            console.error('Invalid response format from getScopes', response)
            return {}
        }

        const scopes = response.scopes
        const schemas: Record<string, DefinitionSchema> = {}

        for (const [scopeKey, scopeData] of Object.entries(scopes)) {
            // Safety check
            if (!scopeData || typeof scopeData !== 'object') continue
            const data = scopeData as any

            const entityTypes: EntityTypeDefinition[] = []

            // Handle entities
            const entities = data.entities || {}
            for (const [entityKey, entityData] of Object.entries(entities)) {
                if (!entityData || typeof entityData !== 'object') continue
                const eData = entityData as any

                // robust field mapping
                const rawFields = eData.metadata_fields || []
                const fields: FieldDefinition[] = Array.isArray(rawFields)
                    ? rawFields
                        .map((field: string | any): FieldDefinition => {
                            if (typeof field === 'string') {
                                return {
                                    name: field,
                                    label: field.replace(/_/g, ' ').replace(/\b\w/g, (l: string) => l.toUpperCase()),
                                    type: 'text',
                                    hidden: false
                                }
                            }
                            return {
                                name: field.name || 'unknown',
                                label: field.label || (field.name ? field.name.replace(/_/g, ' ') : 'Unknown'),
                                type: (field.type || 'text') as FieldDefinition['type'],
                                required: !!field.required,
                                options: field.options,
                                hidden: !!field.hidden,
                                metadata_: field.placeholder ? { placeholder: field.placeholder } : undefined
                            }
                        })
                        .filter(f => !f.hidden)
                    : []

                entityTypes.push({
                    value: entityKey,
                    label: eData.label || entityKey.replace(/_/g, ' ').replace(/\b\w/g, (l: string) => l.toUpperCase()),
                    icon: eData.icon || 'pi pi-box',
                    hasImage: eData.hasImage !== false,
                    fields: fields,
                    isLinker: entityKey === 'system_series', // TODO: Make dynamic if needed
                    specialUi: eData.special_ui ? {
                        type: eData.special_ui.type,
                        config: eData.special_ui.config
                    } : undefined
                })
            }

            // Chain structure (only relevant for profile currently)
            let chainStructure: ChainNodeDefinition[] = []
            if (scopeKey === 'profile') {
                chainStructure = [
                    { key: 'company', label: 'Company', icon: 'pi pi-building', entityType: 'company' },
                    { key: 'material', label: 'Material', icon: 'pi pi-box', entityType: 'material' },
                    { key: 'opening_system', label: 'Opening', icon: 'pi pi-cog', entityType: 'opening_system' },
                    { key: 'system_series', label: 'Series', icon: 'pi pi-sitemap', entityType: 'system_series' },
                    { key: 'color', label: 'Color', icon: 'pi pi-palette', entityType: 'color' }
                ]
            }

            schemas[scopeKey] = {
                title: data.label || `${scopeKey} Definitions`,
                entityTypes: entityTypes,
                chainStructure: chainStructure
            }
        }

        return schemas
    } catch (error) {
        console.error('Failed to fetch and build schemas:', error)
        return {}
    }
}
