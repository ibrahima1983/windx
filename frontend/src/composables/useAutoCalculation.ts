import { ref, type Ref } from 'vue'
import { useDebugLogger } from '@/composables/useDebugLogger'

/**
 * Composable for handling auto-calculation of fields based on schema metadata
 * Extracted from DynamicForm.vue to be reusable in tables and other components
 */
export function useAutoCalculation(
  schema: Ref<any>,
  formData: Ref<Record<string, any>>
) {
  const logger = useDebugLogger('useAutoCalculation')
  const isCalculating = ref(false)
  const calculatedFields = ref<Set<string>>(new Set())

  /**
   * Auto-calculate fields based on metadata from backend schema
   * Reads calculated_field metadata and executes calculations generically
   */
  function autoCalculateFields(fieldName: string): string[] {
    // Prevent infinite loops - don't calculate if we're already calculating
    if (isCalculating.value) return []
    if (!schema.value?.sections) return []

    logger.info('Starting calculation', { fieldName })
    isCalculating.value = true
    const updatedFields: string[] = []

    try {
      // Find all fields that should recalculate when this field changes
      const fieldsToCalculate: Array<{field: any, calc: any}> = []
      
      schema.value.sections.forEach((section: any) => {
        section.fields.forEach((field: any) => {
          const calc = field.calculated_field
          if (calc && calc.trigger_on?.includes(fieldName)) {
            fieldsToCalculate.push({ field, calc })
            logger.debug('Found field to calculate', { 
              fieldName: field.name, 
              calculation: calc 
            })
          }
        })
      })

      if (fieldsToCalculate.length === 0) {
        logger.debug('No fields to calculate', { fieldName })
      }

      // Execute calculations
      fieldsToCalculate.forEach(({ field, calc }) => {
        const result = executeCalculation(calc, formData.value)
        if (result !== null) {
          const oldValue = formData.value[field.name]
          formData.value[field.name] = result
          
          // Track that this field was calculated
          calculatedFields.value.add(field.name)
          updatedFields.push(field.name)
          
          // Log the calculation
          logger.info('Field calculated', {
            fieldName: field.name,
            oldValue,
            newValue: result,
            calculation: calc
          })
        } else {
          logger.warn('Calculation returned null', { 
            fieldName: field.name, 
            calculation: calc 
          })
        }
      })
    } finally {
      // Always reset the flag, even if there's an error
      isCalculating.value = false
    }

    logger.info('Calculation completed', { 
      triggerField: fieldName,
      updatedFields 
    })
    return updatedFields
  }

  /**
   * Execute a calculation based on the calculation configuration
   */
  function executeCalculation(calc: any, data: Record<string, any>): number | null {
    const { type, operands, precision = 2 } = calc
    
    logger.debug('Executing calculation', { type, operands, precision })
    
    // Get operand values
    const values = operands.map((key: string) => parseDecimal(data[key]))
    
    logger.debug('Operand values', { operands, values })
    
    // Check if all values are available
    if (values.some((v: number | null) => v === null)) {
      logger.debug('Some operand values are null, skipping calculation')
      return null
    }
    
    // For divide, check for zero divisor
    if (type === 'divide' && values[1] === 0) {
      logger.warn('Division by zero attempted')
      return null
    }
    
    let result: number
    switch (type) {
      case 'multiply':
        result = values[0]! * values[1]!
        break
      case 'divide':
        result = values[0]! / values[1]!
        break
      case 'add':
        result = values.reduce((a: number, b: number) => a + b, 0)
        break
      case 'subtract':
        result = values[0]! - values[1]!
        break
      default:
        logger.error('Unknown calculation type', { type })
        return null
    }
    
    const finalResult = roundToDecimals(result, precision)
    logger.debug('Calculation result', { result, finalResult, precision })
    
    return finalResult
  }

  /**
   * Parse a value to decimal, handling various input types
   */
  function parseDecimal(value: any): number | null {
    if (value === null || value === undefined || value === '') return null
    if (typeof value === 'number') return isNaN(value) ? null : value
    
    // Remove non-numeric characters except decimal point and minus sign
    const cleanValue = String(value).replace(/[^\d.-]/g, '')
    const num = parseFloat(cleanValue)
    return isNaN(num) ? null : num
  }

  /**
   * Round a number to specified decimal places
   */
  function roundToDecimals(value: number, decimals: number): number {
    const multiplier = Math.pow(10, decimals)
    return Math.round((value + Number.EPSILON) * multiplier) / multiplier
  }

  /**
   * Check if a field was recently calculated (for highlighting purposes)
   */
  function isFieldCalculated(fieldName: string): boolean {
    return calculatedFields.value.has(fieldName)
  }

  /**
   * Clear the calculated fields tracking
   */
  function clearCalculatedFields(): void {
    calculatedFields.value.clear()
  }

  /**
   * Mark a field as calculated (for external use)
   */
  function markFieldAsCalculated(fieldName: string): void {
    calculatedFields.value.add(fieldName)
  }

  /**
   * Get all fields that would be affected by changing a specific field
   */
  function getAffectedFields(fieldName: string): string[] {
    if (!schema.value?.sections) return []

    const affectedFields: string[] = []
    
    schema.value.sections.forEach((section: any) => {
      section.fields.forEach((field: any) => {
        const calc = field.calculated_field
        if (calc && calc.trigger_on?.includes(fieldName)) {
          affectedFields.push(field.name)
        }
      })
    })

    return affectedFields
  }

  return {
    isCalculating,
    calculatedFields,
    autoCalculateFields,
    executeCalculation,
    parseDecimal,
    roundToDecimals,
    isFieldCalculated,
    clearCalculatedFields,
    markFieldAsCalculated,
    getAffectedFields
  }
}