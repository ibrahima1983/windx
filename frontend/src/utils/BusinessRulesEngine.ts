/**
 * Business Rules Engine for Profile Entry
 * 
 * Implements type-based field availability and validation rules
 * based on the CSV business rules specification.
 * 
 * Note: updateFieldVisibility() has been removed - use Vue's reactive
 * system instead (v-show/v-if based on fieldVisibility computed property)
 */

export interface FieldVisibility {
    [fieldName: string]: boolean
}

export interface FieldErrors {
    [fieldName: string]: string
}

export class BusinessRulesEngine {
    /**
     * Evaluate field availability based on current form data
     */
    static evaluateFieldAvailability(formData: Record<string, any>): FieldVisibility {
        const visibility: FieldVisibility = {}
        const productType = (formData.type || '').toLowerCase()
        const openingSystem = (formData.opening_system || '').toLowerCase()

        // Business Rule 1: "Renovation only for frame" → Only when Type = "Frame"
        visibility.renovation = productType === 'frame'

        // Business Rule 2: "builtin Flyscreen track only for sliding frame" → Only for sliding frames
        visibility.builtin_flyscreen_track = (
            productType === 'frame' && openingSystem.includes('sliding')
        )

        // Business Rule 3: "Total width only for frame with builtin flyscreen"
        visibility.total_width = (
            productType === 'frame' && formData.builtin_flyscreen_track === true
        )

        // Business Rule 4: "flyscreen track height only for frame with builtin flyscreen"
        visibility.flyscreen_track_height = (
            productType === 'frame' && formData.builtin_flyscreen_track === true
        )

        // Business Rule 5: "Sash overlap only for sashs" → Only when Type = "sash"
        visibility.sash_overlap = productType === 'sash'

        // Business Rule 6: "Flying mullion clearances" → Only when Type = "Flying mullion"
        visibility.flying_mullion_horizontal_clearance = productType === 'flying mullion'
        visibility.flying_mullion_vertical_clearance = productType === 'flying mullion'

        // Business Rule 7: "Glazing undercut height only for glazing bead" → Only when Type = "glazing bead"
        visibility.glazing_undercut_height = productType === 'glazing bead'

        // Business Rule 8: "Renovation height mm only for frame"
        visibility.renovation_height = productType === 'frame'

        // Business Rule 9: "Steel material thickness only for reinforcement"
        visibility.steel_material_thickness = productType === 'reinforcement'

        return visibility
    }

    /**
     * Check if a field is valid for the current context
     */
    static isFieldValidForCurrentContext(fieldName: string, formData: Record<string, any>): boolean {
        const fieldAvailability = this.evaluateFieldAvailability(formData)

        // If field has a specific rule, use it
        if (fieldName in fieldAvailability) {
            return fieldAvailability[fieldName] || false
        }

        // Default to true for fields without specific rules
        return true
    }

    /**
     * Get display value for preview, showing 'N/A' for fields that don't apply
     */
    static getDisplayValue(fieldName: string, value: any, formData: Record<string, any>): string {
        if (!this.isFieldValidForCurrentContext(fieldName, formData)) {
            return 'N/A'
        }

        // Format the value normally if field is applicable
        if (value === null || value === undefined || value === '') {
            return 'N/A'
        } else if (typeof value === 'boolean') {
            return value ? 'yes' : 'no'
        } else if (Array.isArray(value)) {
            return value.length > 0 ? value.join(', ') : 'N/A'
        } else {
            return String(value)
        }
    }

    /**
     * Check if a field value is meaningful (not null, empty, or default false for booleans)
     */
    private static _hasMeaningfulValue(value: any): boolean {
        if (value === null || value === undefined || value === '') {
            return false
        }
        // For boolean fields, false is not considered meaningful in this context
        // because unchecked checkboxes should not trigger validation errors
        if (typeof value === 'boolean' && value === false) {
            return false
        }
        return true
    }

    /**
     * Validate business rules and return field-specific errors
     */
    static validateBusinessRules(formData: Record<string, any>): FieldErrors {
        const errors: FieldErrors = {}
        const productType = (formData.type || '').toLowerCase()
        const openingSystem = (formData.opening_system || '').toLowerCase()

        // Rule 1: Renovation should only have values for frames
        if (this._hasMeaningfulValue(formData.renovation) && productType !== 'frame') {
            errors.renovation = 'Renovation is only applicable for frame types'
        }

        // Rule 2: Builtin flyscreen track should only be set for sliding frames
        if (this._hasMeaningfulValue(formData.builtin_flyscreen_track) &&
            !(productType === 'frame' && openingSystem.includes('sliding'))) {
            errors.builtin_flyscreen_track = 'Builtin flyscreen track is only applicable for sliding frames'
        }

        // Rule 3: Total width should only be set when builtin flyscreen is enabled
        if (this._hasMeaningfulValue(formData.total_width) &&
            !(productType === 'frame' && formData.builtin_flyscreen_track === true)) {
            errors.total_width = 'Total width is only applicable when builtin flyscreen track is enabled'
        }

        // Rule 4: Flyscreen track height should only be set when builtin flyscreen is enabled
        if (this._hasMeaningfulValue(formData.flyscreen_track_height) &&
            !(productType === 'frame' && formData.builtin_flyscreen_track === true)) {
            errors.flyscreen_track_height = 'Flyscreen track height is only applicable when builtin flyscreen track is enabled'
        }

        // Rule 5: Sash overlap should only have values for sash types
        if (this._hasMeaningfulValue(formData.sash_overlap) && productType !== 'sash') {
            errors.sash_overlap = 'Sash overlap is only applicable for sash types'
        }

        // Rule 6: Flying mullion clearances should only have values for flying mullion types
        if (this._hasMeaningfulValue(formData.flying_mullion_horizontal_clearance) &&
            productType !== 'flying mullion') {
            errors.flying_mullion_horizontal_clearance = 'Flying mullion horizontal clearance is only applicable for flying mullion types'
        }

        if (this._hasMeaningfulValue(formData.flying_mullion_vertical_clearance) &&
            productType !== 'flying mullion') {
            errors.flying_mullion_vertical_clearance = 'Flying mullion vertical clearance is only applicable for flying mullion types'
        }

        // Rule 7: Glazing undercut height should only have values for glazing bead types
        if (this._hasMeaningfulValue(formData.glazing_undercut_height) &&
            productType !== 'glazing bead') {
            errors.glazing_undercut_height = 'Glazing undercut height is only applicable for glazing bead types'
        }

        // Rule 8: Renovation height should only have values for frame types
        if (this._hasMeaningfulValue(formData.renovation_height) && productType !== 'frame') {
            errors.renovation_height = 'Renovation height is only applicable for frame types'
        }

        // Rule 9: Steel material thickness should only have values for reinforcement types
        if (this._hasMeaningfulValue(formData.steel_material_thickness) &&
            productType !== 'reinforcement') {
            errors.steel_material_thickness = 'Steel material thickness is only applicable for reinforcement types'
        }

        return errors
    }

    /**
     * Get list of fields that should be disabled based on current context
     */
    static getDisabledFields(formData: Record<string, any>): string[] {
        const fieldAvailability = this.evaluateFieldAvailability(formData)
        const disabledFields: string[] = []

        for (const [fieldName, isAvailable] of Object.entries(fieldAvailability)) {
            if (!isAvailable) {
                disabledFields.push(fieldName)
            }
        }

        return disabledFields
    }
}
