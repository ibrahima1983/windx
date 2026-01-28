<template>
  <Card class="mb-4">
    <template #title>Configuration Form</template>
    <template #content>
      <div v-if="loading" class="space-y-4">
        <Skeleton height="60px" v-for="i in 5" :key="i" />
      </div>

      <div v-else-if="schema" class="space-y-6">
        <FormSection 
          v-for="section in schema.sections" 
          :key="section.name" 
          :title="section.label"
          variant="default"
        >
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div 
              v-for="field in section.fields" 
              :key="field.name"
              v-show="fieldVisibility[field.name] !== false"
              class="mb-0"
            >


              <!-- Universal Field Renderer -->
              <FormFieldRenderer 
                :field="field"
                v-model="localForm[field.name]"
                :error="fieldErrors[field.name]"
                @update:modelValue="autoCalculateFields(field.name)"
                @blur="validateField(field.name)"
                @change="validateField(field.name)"
                :disabled="fieldVisibility[field.name] === false || (disabledFields && disabledFields[field.name])"
              />
            </div>
          </div>
        </FormSection>

        <div class="flex gap-2">
          <Button 
            label="Save Configuration" 
            icon="pi pi-save"
            @click="handleSubmit"
            :loading="saving"
            :disabled="!isValid"
          />
          <Button 
            label="Clear Form" 
            icon="pi pi-times"
            @click="handleClear"
            severity="secondary"
            outlined
          />
        </div>
      </div>
    </template>
  </Card>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import type { PropType } from 'vue'
import Card from 'primevue/card'
import Button from 'primevue/button'
import Skeleton from 'primevue/skeleton'
import FormFieldRenderer from '@/components/common/FormFieldRenderer.vue'
import FormSection from '@/components/common/FormSection.vue'
import { useFormValidation } from '@/composables/useFormValidation'

const props = defineProps({
  schema: {
    type: Object as PropType<any>,
    default: null
  },
  modelValue: {
    type: Object as PropType<Record<string, any>>,
    required: true
  },
  loading: {
    type: Boolean,
    default: false
  },
  saving: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:modelValue', 'submit', 'clear'])

const localForm = ref<Record<string, any>>({})
const isCalculating = ref(false) // Prevent infinite loops during auto-calculation

// Sync local form with props
// Sync local form with props
watch(() => props.modelValue, (newVal) => {
  // Only sync if the value is actually different to avoid infinite loops or resetting local state
  if (JSON.stringify(newVal) === JSON.stringify(localForm.value)) return

  console.log('[DynamicForm] Syncing from props.modelValue')
  const processed = { ...newVal }
  if (props.schema) {
    props.schema.sections.forEach((section: any) => {
      section.fields.forEach((field: any) => {
        if (['multi-select', 'multiselect'].includes(field.ui_component)) {
          if (!Array.isArray(processed[field.name])) {
            processed[field.name] = processed[field.name] ? [processed[field.name]] : []
          }
        }
      })
    })
  }
  localForm.value = processed
}, { deep: true, immediate: true })

// Sync prop with local form
watch(localForm, (newVal) => {
  emit('update:modelValue', newVal)
}, { deep: true })

import { useDependencyEngine } from '@/composables/useDependencyEngine'

// Setup validation using the composable
const schemaRef = computed(() => props.schema)
const { fieldErrors, fieldVisibility, isValid, validateField, validateAll, clearErrors } = 
  useFormValidation(schemaRef, localForm)

// Field State & Dependencies
const { disabledFields } = useDependencyEngine(schemaRef, localForm, findField)

// Helper
function findField(name: string) {
    if (!props.schema) return null
    for (const section of props.schema.sections) {
        const f = section.fields.find((f: any) => f.name === name)
        if (f) return f
    }
    return null
}



function handleSubmit() {
  if (validateAll()) {
    emit('submit', localForm.value)
  }
}

function handleClear() {
  clearErrors()
  emit('clear')
}

/**
 * Auto-calculate fields based on metadata from backend schema
 * Reads calculated_field metadata and executes calculations generically
 */
function autoCalculateFields(fieldName: string) {
  // Prevent infinite loops - don't calculate if we're already calculating
  if (isCalculating.value) return
  if (!props.schema?.sections) return

  isCalculating.value = true
  try {
    // Find all fields that should recalculate when this field changes
    const fieldsToCalculate: Array<{field: any, calc: any}> = []
    
    props.schema.sections.forEach((section: any) => {
      section.fields.forEach((field: any) => {
        const calc = field.calculated_field
        if (calc && calc.trigger_on?.includes(fieldName)) {
          fieldsToCalculate.push({ field, calc })
        }
      })
    })

    // Execute calculations
    fieldsToCalculate.forEach(({ field, calc }) => {
      const result = executeCalculation(calc, localForm.value)
      if (result !== null) {
        localForm.value[field.name] = result
      }
    })
  } finally {
    // Always reset the flag, even if there's an error
    isCalculating.value = false
  }
}

function executeCalculation(calc: any, formData: Record<string, any>): number | null {
  const { type, operands, precision = 2 } = calc
  
  // Get operand values
  const values = operands.map((key: string) => parseDecimal(formData[key]))
  
  // Check if all values are available
  if (values.some((v: number | null) => v === null)) return null
  
  // For divide, check for zero divisor
  if (type === 'divide' && values[1] === 0) return null
  
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
      return null
  }
  
  return roundToDecimals(result, precision)
}

function parseDecimal(value: any): number | null {
  if (value === null || value === undefined || value === '') return null
  if (typeof value === 'number') return isNaN(value) ? null : value
  
  // Remove non-numeric characters except decimal point and minus sign
  const cleanValue = String(value).replace(/[^\d.-]/g, '')
  const num = parseFloat(cleanValue)
  return isNaN(num) ? null : num
}

function roundToDecimals(value: number, decimals: number): number {
  const multiplier = Math.pow(10, decimals)
  return Math.round((value + Number.EPSILON) * multiplier) / multiplier
}
</script>


