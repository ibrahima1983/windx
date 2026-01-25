/**
 * Form Formatters - Utility functions for form data formatting
 * 
 * Extracted from FormHelpers.js - only the pure formatting logic
 * API calls and UI component logic have been moved to services/composables
 */

export interface FieldVisibility {
    [fieldName: string]: boolean
}

export interface HeaderMapping {
    [header: string]: string
}

/**
 * Get display value for preview tables
 */
export function getPreviewValue(
    header: string,
    formData: Record<string, any>,
    fieldVisibility: FieldVisibility,
    headerMapping: HeaderMapping
): string {
    const fieldName = headerMapping[header]
    if (!fieldName) return 'N/A'

    const value = formData[fieldName]

    if (fieldVisibility[fieldName] === false) {
        return 'N/A'
    }

    if (value === null || value === undefined || value === '') {
        return 'N/A'
    }

    if (typeof value === 'boolean') {
        return value ? 'yes' : 'no'
    }

    if (Array.isArray(value)) {
        return value.length > 0 ? value.join(', ') : 'N/A'
    }

    if (typeof value === 'number') {
        if (fieldName.includes('price')) {
            return value.toFixed(2)
        }
        if (fieldName.includes('percentage') || fieldName.includes('discount')) {
            return value + '%'
        }
    }

    return String(value)
}

/**
 * Get unit for a field (mm, kg, $, %, etc.)
 */
export function getFieldUnit(fieldName: string): string {
    const unitMap: Record<string, string> = {
        'length_of_beam': 'm',
        'width': 'mm',
        'total_width': 'mm',
        'flyscreen_track_height': 'mm',
        'front_height': 'mm',
        'rear_height': 'mm',
        'glazing_height': 'mm',
        'renovation_height': 'mm',
        'glazing_undercut_height': 'mm',
        'sash_overlap': 'mm',
        'flying_mullion_horizontal_clearance': 'mm',
        'flying_mullion_vertical_clearance': 'mm',
        'steel_material_thickness': 'mm',
        'weight_per_meter': 'kg',
        'price_per_meter': '$',
        'price_per_beam': '$',
        'upvc_profile_discount': '%'
    }

    return unitMap[fieldName] || ''
}

/**
 * Get default value for a field based on its data type
 */
export function getDefaultValue(dataType: string): any {
    switch (dataType) {
        case 'boolean':
            return false
        case 'number':
        case 'float':
            return null
        case 'array':
            return []
        default:
            return ''
    }
}

/**
 * Prepare form data for saving (remove hidden fields, convert empty to null)
 */
export function prepareSaveData(
    formData: Record<string, any>,
    manufacturingTypeId: number,
    schema: any,
    fieldVisibility: FieldVisibility
): Record<string, any> {
    const saveData: Record<string, any> = {
        ...formData,
        manufacturing_type_id: manufacturingTypeId
    }

    // Remove hidden fields
    if (schema) {
        for (const section of schema.sections) {
            for (const field of section.fields) {
                if (fieldVisibility[field.name] === false) {
                    delete saveData[field.name]
                }
            }
        }
    }

    // Convert empty strings to null
    Object.keys(saveData).forEach(key => {
        // Cast to ensure TS knows we can index by string
        const data = saveData as Record<string, any>
        if (data[key] === '') {
            data[key] = null
        }
    })

    return saveData
}

/**
 * Get count of completed fields
 */
export function getCompletedFieldsCount(
    schema: any,
    formData: Record<string, any>,
    fieldVisibility: FieldVisibility
): number {
    if (!schema) return 0

    let completed = 0
    for (const section of schema.sections) {
        for (const field of section.fields) {
            if (fieldVisibility[field.name] !== false) {
                const value = formData[field.name]
                if (value !== null && value !== undefined && value !== '' &&
                    !(Array.isArray(value) && value.length === 0)) {
                    completed++
                }
            }
        }
    }
    return completed
}

/**
 * Get total count of visible fields
 */
export function getTotalFieldsCount(
    schema: any,
    fieldVisibility: FieldVisibility
): number {
    if (!schema) return 0

    let total = 0
    for (const section of schema.sections) {
        for (const field of section.fields) {
            if (fieldVisibility[field.name] !== false) {
                total++
            }
        }
    }
    return total
}

/**
 * Check if a value has changed from last saved
 */
export function isValueChanged(
    header: string,
    formData: Record<string, any>,
    lastSavedData: Record<string, any> | null,
    headerMapping: HeaderMapping
): boolean {
    if (!lastSavedData) return false

    const fieldName = headerMapping[header]
    if (!fieldName) return false

    return formData[fieldName] !== lastSavedData[fieldName]
}
