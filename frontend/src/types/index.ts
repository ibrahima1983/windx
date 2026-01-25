// User types
export interface User {
    id: number
    email: string
    username: string
    full_name: string | null
    is_active: boolean
    is_superuser: boolean
    created_at: string
    updated_at: string
}

// Manufacturing Type
export interface ManufacturingType {
    id: number
    name: string
    description: string | null
    base_category: string
    base_price: number
    base_weight: number
    is_active: boolean
}

// Attribute Node
export interface AttributeNode {
    id: number
    manufacturing_type_id: number
    parent_node_id: number | null
    name: string
    label: string
    description: string | null
    node_type: 'category' | 'attribute' | 'option'
    data_type: string | null
    ui_component: string | null
    required: boolean
    sort_order: number
    options?: string[]
    validation_rules?: Record<string, any>
    display_condition?: Record<string, any>
}

// Configuration
export interface Configuration {
    id: number
    manufacturing_type_id: number
    customer_id: number | null
    name: string
    status: string
    base_price: number
    total_price: number
    calculated_weight: number | null
    calculated_technical_data: Record<string, any> | null
    created_at: string
    updated_at: string
    [key: string]: any
}

// Form Schema
export interface FormSection {
    name: string
    label: string
    fields: AttributeNode[]
}

export interface FormSchema {
    sections: FormSection[]
}

// API Response types
export interface PaginatedResponse<T> {
    items: T[]
    total: number
    skip: number
    limit: number
}

export interface ApiError {
    detail: string | { message: string }
}
