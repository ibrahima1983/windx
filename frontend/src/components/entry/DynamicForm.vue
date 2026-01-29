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
import { useDependencyEngine } from '@/composables/useDependencyEngine'
import { useAutoCalculation } from '@/composables/useAutoCalculation'

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

// Setup auto-calculation using the composable
const schemaRef = computed(() => props.schema)
const { autoCalculateFields } = useAutoCalculation(schemaRef, localForm)

// Sync local form with props
watch(() => props.modelValue, (newVal) => {
  // Only sync if the value is actually different to avoid infinite loops or resetting local state
  if (JSON.stringify(newVal) === JSON.stringify(localForm.value)) return

  const processed = { ...newVal }
  if (props.schema) {
    props.schema.sections.forEach((section: any) => {
      section.fields.forEach((field: any) => {
        if (['multi-select', 'multiselect', 'color-multi-select'].includes(field.ui_component)) {
          if (!Array.isArray(processed[field.name])) {
            processed[field.name] = processed[field.name] ? [processed[field.name]] : []
          }
        }
      })
    })
  }
  localForm.value = processed
}, { deep: true, immediate: true })

// Initialize form when schema loads (important for multi-select defaults)
watch(() => props.schema, (newSchema) => {
  if (!newSchema) return
  
  newSchema.sections.forEach((section: any) => {
    section.fields.forEach((field: any) => {
      if (['multi-select', 'multiselect', 'color-multi-select'].includes(field.ui_component)) {
        if (!Array.isArray(localForm.value[field.name])) {
          localForm.value[field.name] = []
        }
      }
    })
  })
}, { immediate: true })

// Sync prop with local form
watch(localForm, (newVal) => {
  emit('update:modelValue', newVal)
}, { deep: true })

// Setup validation using the composable
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
</script>


