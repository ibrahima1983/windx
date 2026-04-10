/**
 * Form Validation Utilities
 * 
 * Pure validation logic extracted from FormValidator.js
 * DOM manipulation methods removed - use Vue's reactive error display instead
 */

export interface ValidationRule {
    rule_type?: string
    min?: number
    max?: number
    min_length?: number
    max_length?: number
    pattern?: string
    message?: string
}

import type { AttributeNode } from '@/types'

// Re-export or alias for local usage
export type Field = AttributeNode

export interface FieldErrors {
    [fieldName: string]: string
}

export class FormValidator {
    /**
     * Validate a single field
     */
    static validateField(field: Field, value: any, isVisible: boolean): FieldErrors {
        const errors: FieldErrors = {}

        // Skip validation for hidden fields
        if (!isVisible) {
            return errors
        }

        // Required validation
        if (field.required && (!value || value === '' || (Array.isArray(value) && value.length === 0))) {
            errors[field.name] = `${field.label} is required`
            return errors
        }

        // Skip further validation if field is empty and not required
        if (!value || value === '') {
            return errors
        }

        // Data type validation
        if (['number', 'float', 'dimension'].includes(field.data_type || '')) {
            if (value !== undefined && value !== null && value !== '') {
                const numValue = typeof value === 'string' ? parseFloat(value.replace(/[^\d.-]/g, '')) : Number(value)
                if (isNaN(numValue)) {
                    errors[field.name] = `${field.label} must be a valid number`
                    return errors
                }
            }
        }

        // Validation rules
        if (field.validation_rules) {
            const rules = field.validation_rules as any

            // Range validation for numbers
            if (rules.min !== undefined || rules.max !== undefined) {
                const numValue = typeof value === 'string' ? parseFloat(value.replace(/[^\d.-]/g, '')) : Number(value)
                if (!isNaN(numValue)) {
                    if (rules.min !== undefined && numValue < rules.min) {
                        errors[field.name] = `${field.label} must be at least ${rules.min}`
                        return errors
                    }
                    if (rules.max !== undefined && numValue > rules.max) {
                        errors[field.name] = `${field.label} must be at most ${rules.max}`
                        return errors
                    }
                }
            }

            // Pattern validation for strings
            if (rules.pattern && typeof value === 'string') {
                try {
                    if (!new RegExp(rules.pattern).test(value)) {
                        errors[field.name] = rules.message || `${field.label} format is invalid`
                        return errors
                    }
                } catch (e) {
                    console.warn(`Invalid regex pattern for ${field.name}:`, rules.pattern)
                }
            }

            // Length validation for strings
            if (typeof value === 'string') {
                if (rules.min_length && value.length < rules.min_length) {
                    errors[field.name] = `${field.label} must be at least ${rules.min_length} characters`
                    return errors
                }
                if (rules.max_length && value.length > rules.max_length) {
                    errors[field.name] = `${field.label} must be at most ${rules.max_length} characters`
                    return errors
                }
            }

            // Custom validation rules
            if (rules.rule_type) {
                switch (rules.rule_type) {
                    case 'email':
                        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
                        if (!emailRegex.test(value)) {
                            errors[field.name] = `${field.label} must be a valid email address`
                            return errors
                        }
                        break
                    case 'positive_number':
                        if (isNaN(value) || parseFloat(value) <= 0) {
                            errors[field.name] = `${field.label} must be a positive number`
                            return errors
                        }
                        break
                }
            }
        }

        return errors
    }

    /**
     * Validate all fields in a schema
     */
    static validateAllFields(
        schema: any,
        formData: Record<string, any>,
        fieldVisibility: Record<string, boolean>
    ): FieldErrors {
        if (!schema) return {}

        let allErrors: FieldErrors = {}

        // Validate all visible fields
        for (const section of schema.sections) {
            for (const field of section.fields) {
                const isVisible = fieldVisibility[field.name] !== false
                if (isVisible) {
                    const fieldErrors = FormValidator.validateField(field, formData[field.name], isVisible)
                    allErrors = { ...allErrors, ...fieldErrors }
                }
            }
        }

        return allErrors
    }

    /**
     * Check if form is valid (all required fields filled, no errors)
     */
    static isFormValid(
        schema: any,
        formData: Record<string, any>,
        fieldVisibility: Record<string, boolean>,
        fieldErrors: FieldErrors
    ): boolean {
        if (!schema) return false

        // Check required fields
        for (const section of schema.sections) {
            for (const field of section.fields) {
                const isVisible = fieldVisibility[field.name] !== false
                if (field.required && isVisible) {
                    const value = formData[field.name]
                    if (!value || value === '') {
                        return false
                    }
                }
            }
        }

        // Check for validation errors
        return Object.keys(fieldErrors).length === 0
    }

    /**
     * Clear error for a specific field
     */
    static clearFieldError(fieldErrors: FieldErrors, fieldName: string): FieldErrors {
        const updatedErrors = { ...fieldErrors }
        delete updatedErrors[fieldName]
        return updatedErrors
    }
}
