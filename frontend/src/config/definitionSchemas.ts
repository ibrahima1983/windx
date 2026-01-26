// Configuration for Product Definition Views

export interface FieldDefinition {
    name: string
    label: string
    type: 'text' | 'number' | 'boolean' | 'textarea'
    required?: boolean
    placeholder?: string
    options?: { label: string; value: any }[]
}

export interface EntityTypeDefinition {
    value: string
    label: string
    icon: string
    fields: FieldDefinition[]
    hasImage?: boolean
    isLinker?: boolean // If true, this entity links other entities together (like System Series)
}

export interface ChainNodeDefinition {
    key: string
    label: string
    icon: string
    entityType: string // The entity type value this node corresponds to
}

export interface DefinitionSchema {
    title: string
    entityTypes: EntityTypeDefinition[]
    chainStructure: ChainNodeDefinition[] // Visualization of the "Path"
}

export const definitionSchemas: Record<string, DefinitionSchema> = {
    profile: {
        title: 'Profile Definitions',
        entityTypes: [
            {
                value: 'material',
                label: 'Material',
                icon: 'pi pi-box',
                hasImage: true,
                fields: [
                    { name: 'density', label: 'Density (kg/m³)', type: 'number' }
                ]
            },
            {
                value: 'opening_system',
                label: 'Opening System',
                icon: 'pi pi-cog',
                hasImage: true,
                fields: []
            },
            {
                value: 'color',
                label: 'Color',
                icon: 'pi pi-palette',
                hasImage: true,
                fields: [
                    { name: 'code', label: 'Color Code', type: 'text' },
                    { name: 'has_lamination', label: 'Has Lamination', type: 'boolean' }
                ]
            },
            {
                value: 'company',
                label: 'Company',
                icon: 'pi pi-building',
                hasImage: true,
                fields: [],
                // Special handling logic will be needed for Company->Material link in the View
            },
            {
                value: 'system_series',
                label: 'System Series',
                icon: 'pi pi-sitemap',
                hasImage: true,
                isLinker: true, // This is the core "Linker" entity
                fields: [
                    { name: 'width', label: 'Width (mm)', type: 'number' },
                    { name: 'number_of_chambers', label: 'Chambers', type: 'number' },
                    { name: 'u_value', label: 'U-Value', type: 'number' },
                    { name: 'number_of_seals', label: 'Seals', type: 'number' },
                    { name: 'characteristics', label: 'Characteristics', type: 'textarea' }
                ]
            }
        ],
        chainStructure: [
            { key: 'company', label: 'Company', icon: 'pi pi-building', entityType: 'company' },
            { key: 'material', label: 'Material', icon: 'pi pi-box', entityType: 'material' },
            { key: 'opening_system', label: 'Opening', icon: 'pi pi-cog', entityType: 'opening_system' },
            { key: 'system_series', label: 'Series', icon: 'pi pi-sitemap', entityType: 'system_series' },
            { key: 'color', label: 'Color', icon: 'pi pi-palette', entityType: 'color' }
        ]
    }
    // Future: glazing: { ... }
}
