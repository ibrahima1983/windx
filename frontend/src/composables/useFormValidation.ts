/**
 * Form Validation Composable
 * 
 * Handles dynamic form validation with business rules
 */

import { ref, computed, watch } from 'vue'
import type { Ref, ComputedRef } from 'vue'
import { FormValidator } from '@/utils/FormValidator'
import { BusinessRulesEngine } from '@/utils/BusinessRulesEngine'
import { useDebugLogger } from './useDebugLogger'

export function useFormValidation(
    schema: Ref<any | null>,
    formData: Ref<Record<string, any>>
) {
    const logger = useDebugLogger('useFormValidation')
    const fieldErrors = ref<Record<string, string>>({})

    // Calculate field visibility based on business rules
    const fieldVisibility = computed(() => {
        if (!schema.value) return {}
        return BusinessRulesEngine.evaluateFieldAvailability(formData.value)
    })

    // Check if form is valid
    const isValid = computed(() => {
        if (!schema.value) return false
        return FormValidator.isFormValid(schema.value, formData.value, fieldVisibility.value, fieldErrors.value)
    })

    // Validate a single field
    function validateField(fieldName: string) {
        if (!schema.value) return

        logger.debug('Validating field', { fieldName })

        // Find field definition
        let fieldDef = null
        for (const section of schema.value.sections) {
            const found = section.fields.find((f: any) => f.name === fieldName)
            if (found) {
                fieldDef = found
                break
            }
        }

        if (!fieldDef) {
            logger.warn('Field definition not found', { fieldName })
            return
        }

        const isVisible = fieldVisibility.value[fieldName] !== false
        const errors = FormValidator.validateField(fieldDef, formData.value[fieldName], isVisible)

        if (Object.keys(errors).length > 0) {
            fieldErrors.value = { ...fieldErrors.value, ...errors }
            logger.debug('Field validation failed', { fieldName, errors })
        } else {
            // Clear error for this field
            const updated = { ...fieldErrors.value }
            delete updated[fieldName]
            fieldErrors.value = updated
            logger.debug('Field validation passed', { fieldName })
        }
    }

    // Validate all fields
    function validateAll() {
        if (!schema.value) {
            logger.warn('Cannot validate: schema is null')
            return false
        }

        logger.info('Validating all fields')

        // Standard validation
        const standardErrors = FormValidator.validateAllFields(
            schema.value,
            formData.value,
            fieldVisibility.value
        )

        // Business rules validation
        const businessErrors = BusinessRulesEngine.validateBusinessRules(formData.value)

        // Merge errors
        fieldErrors.value = { ...standardErrors, ...businessErrors }

        const hasErrors = Object.keys(fieldErrors.value).length > 0
        if (hasErrors) {
            logger.warn('Validation failed', { errors: fieldErrors.value })
        } else {
            logger.info('Validation passed')
        }

        return !hasErrors
    }

    // Clear all errors
    function clearErrors() {
        fieldErrors.value = {}
        logger.debug('Errors cleared')
    }

    // Clear error for specific field
    function clearFieldError(fieldName: string) {
        fieldErrors.value = FormValidator.clearFieldError(fieldErrors.value, fieldName)
        logger.debug('Field error cleared', { fieldName })
    }

    // Watch for form data changes and re-evaluate visibility
    watch(
        () => formData.value,
        () => {
            // Re-validate visible fields when data changes
            const visibleFields = Object.keys(fieldVisibility.value).filter(
                key => fieldVisibility.value[key] !== false
            )

            // Clear errors for hidden fields
            const updated = { ...fieldErrors.value }
            let changed = false
            Object.keys(updated).forEach(key => {
                if (fieldVisibility.value[key] === false) {
                    delete updated[key]
                    changed = true
                }
            })
            if (changed) {
                fieldErrors.value = updated
                logger.debug('Cleared errors for hidden fields')
            }
        },
        { deep: true }
    )

    return {
        fieldErrors,
        fieldVisibility,
        isValid,
        validateField,
        validateAll,
        clearErrors,
        clearFieldError
    }
}
