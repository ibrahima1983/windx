// Common types and interfaces for product definition services

export interface BaseEntityCreate {
    name: string
    description?: string | null
    image_url?: string | null
    metadata?: Record<string, any>
}

export interface BaseEntityUpdate {
    name?: string
    description?: string | null
    image_url?: string | null
    metadata?: Record<string, any>
}

export interface BaseEntityResponse {
    id: number
    name: string
    description?: string | null
    image_url?: string | null
    created_at: string
    updated_at: string
}

// Legacy interfaces for backward compatibility
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

export interface RelationEntity {
    id: number
    name: string
    node_type: string
    image_url: string | null
    price_impact_value: string | null
    description: string | null
    validation_rules: Record<string, any>
    metadata_?: Record<string, any>
}

export interface GetEntitiesResponse {
    success: boolean
    entities: RelationEntity[]
    type_metadata?: Record<string, any>
}

// Profile-specific types
export interface ProfilePathCreate {
    company_id: number
    material_id: number
    opening_system_id: number
    system_series_id: number
    color_id: number
}

export interface ProfileDependentOptionsRequest {
    company_id?: number
    material_id?: number
    opening_system_id?: number
    system_series_id?: number
}

export interface PathDeleteRequest {
    ltree_path: string
}

// Glazing-specific types
export interface GlazingComponentCreate extends BaseEntityCreate {
    component_type: 'glass_type' | 'spacer' | 'gas'
    price_per_sqm?: number
    
    // Glass-specific properties
    thickness?: number
    light_transmittance?: number
    u_value?: number
    
    // Spacer-specific properties
    material?: string
    thermal_conductivity?: number
    
    // Gas-specific properties
    density?: number
}

export interface GlazingUnitCreate {
    name: string
    glazing_type: 'single' | 'double' | 'triple'
    description?: string
    
    // Component references
    outer_glass_id?: number
    middle_glass_id?: number  // Triple only
    inner_glass_id?: number   // Double/Triple
    spacer1_id?: number       // Double/Triple
    spacer2_id?: number       // Triple only
    gas_id?: number           // Optional for Double/Triple
}

export interface GlazingUnitResponse extends BaseEntityResponse {
    glazing_type: string
    total_thickness: number
    u_value: number
    price_per_sqm: number
    weight_per_sqm: number
    components: Record<string, any>
}

export interface CalculationResult {
    total_thickness: number
    u_value: number
    price_per_sqm: number
    weight_per_sqm: number
    technical_properties: Record<string, any>
}