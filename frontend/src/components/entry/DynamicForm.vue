<template>
  <Card class="mb-4">
    <template #title>Configuration Form</template>
    <template #content>
      <div v-if="loading" class="space-y-4">
        <Skeleton height="60px" v-for="i in 5" :key="i" />
      </div>

      <div v-else-if="schema" class="space-y-6">
        <div v-for="section in schema.sections" :key="section.name" class="p-4 bg-slate-50 rounded-lg">
          <h3 class="text-lg font-semibold mb-3">{{ section.label }}</h3>
          
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div 
              v-for="field in section.fields" 
              :key="field.name"
              v-show="fieldVisibility[field.name] !== false"
              class="mb-0"
            >
              <label :for="field.name" class="flex items-center gap-2 font-medium mb-1">
                <span>{{ field.label }}</span>
                <span v-if="field.required" class="text-red-500">*</span>
                <i 
                  v-if="field.description" 
                  class="pi pi-info-circle text-slate-400 cursor-help text-sm"
                  v-tooltip.top="{ value: field.description, escape: false }"
                ></i>
              </label>

              <!-- Text Input -->
              <InputText
                v-if="field.ui_component === 'text'"
                :id="field.name"
                v-model="localForm[field.name]"
                :placeholder="field.required ? `Enter ${field.label}` : `Optional`"
                class="w-full"
                @blur="validateField(field.name)"
              />

              <!-- Number Input -->
              <InputNumber
                v-else-if="field.ui_component === 'number'"
                :id="field.name"
                v-model="localForm[field.name]"
                :placeholder="field.required ? '0' : 'Optional'"
                class="w-full"
                updateOn="input"
                @update:modelValue="() => { validateField(field.name); autoCalculatePriceFields(field.name); }"
              />

              <!-- Currency Input -->
              <InputNumber
                v-else-if="field.ui_component === 'currency'"
                :id="field.name"
                v-model="localForm[field.name]"
                mode="currency"
                currency="USD"
                locale="en-US"
                :placeholder="field.required ? '$0.00' : '0.00'"
                class="w-full"
                updateOn="input"
                @update:modelValue="() => { validateField(field.name); autoCalculatePriceFields(field.name); }"
              />

              <!-- Percentage Input -->
              <InputNumber
                v-else-if="field.ui_component === 'percentage'"
                :id="field.name"
                v-model="localForm[field.name]"
                suffix="%"
                :min="0"
                :max="100"
                :placeholder="field.required ? '0%' : '0'"
                class="w-full"
                updateOn="input"
                @update:modelValue="() => { validateField(field.name); autoCalculatePriceFields(field.name); }"
              />

              <!-- Dropdown -->
              <Select
                v-else-if="field.ui_component === 'dropdown'"
                :id="field.name"
                v-model="localForm[field.name]"
                :options="field.options_data || field.options || []"
                :optionLabel="field.options_data ? 'name' : undefined"
                :optionValue="field.options_data ? 'name' : undefined"
                :placeholder="`Select ${field.label}`"
                class="w-full"
                @change="validateField(field.name)"
              />

              <!-- MultiSelect -->
              <MultiSelect
                v-else-if="field.ui_component === 'multi-select' || field.ui_component === 'multiselect'"
                :id="field.name"
                v-model="localForm[field.name]"
                :options="field.options_data || field.options || []"
                :optionLabel="field.options_data ? 'name' : undefined"
                :optionValue="field.options_data ? 'name' : undefined"
                :placeholder="`Select ${field.label}`"
                display="chip"
                class="w-full"
                @change="validateField(field.name)"
              />

              <!-- Checkbox -->
              <Checkbox
                v-else-if="field.ui_component === 'checkbox'"
                :id="field.name"
                v-model="localForm[field.name]"
                :binary="true"
                @change="validateField(field.name)"
              />

              <!-- Radio Buttons -->
              <div v-else-if="field.ui_component === 'radio'" class="flex flex-wrap gap-4 mt-1">
                <div v-for="option in (field.options_data || field.options || [])" :key="typeof option === 'string' ? option : option.name" class="flex items-center">
                  <RadioButton 
                    :id="`${field.name}_${typeof option === 'string' ? option : option.name}`"
                    v-model="localForm[field.name]" 
                    :name="field.name" 
                    :value="typeof option === 'string' ? option : option.name" 
                    @change="validateField(field.name)"
                  />
                  <label :for="`${field.name}_${typeof option === 'string' ? option : option.name}`" class="ml-2">
                    {{ typeof option === 'string' ? option : option.name }}
                  </label>
                </div>
              </div>

              <!-- Slider -->
              <div v-else-if="field.ui_component === 'slider'" class="px-2 py-4">
                <Slider 
                  v-model="localForm[field.name]" 
                  class="w-full"
                  :min="field.validation_rules?.min || 0"
                  :max="field.validation_rules?.max || 100"
                  @slideend="validateField(field.name)"
                />
                <div class="flex justify-between text-xs text-slate-500 mt-2">
                  <span>{{ field.validation_rules?.min || 0 }}</span>
                  <span class="font-bold text-primary">{{ localForm[field.name] || 0 }}</span>
                  <span>{{ field.validation_rules?.max || 100 }}</span>
                </div>
              </div>

              <!-- Picture Input -->
              <div v-else-if="['picture-input', 'file', 'image', 'pic'].includes(field.ui_component)" class="flex flex-col gap-2">
                <div v-if="localForm[field.name]" class="relative w-48 h-48 rounded-lg border-2 border-dashed border-slate-200 overflow-hidden bg-slate-50 group flex items-center justify-center">
                  <img 
                    :src="getImagePath(localForm[field.name])" 
                    class="w-full h-full object-contain"
                    @error="(e) => (e.target as HTMLImageElement).src = 'https://placehold.co/200x200?text=Invalid+Image'" 
                  />
                  <div class="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-2">
                    <Button 
                      icon="pi pi-trash" 
                      severity="danger" 
                      rounded 
                      @click="localForm[field.name] = null" 
                      v-tooltip.bottom="'Remove Image'"
                    />
                    <a :href="getImagePath(localForm[field.name])" target="_blank" class="p-button p-button-icon-only p-button-info p-button-rounded">
                      <i class="pi pi-external-link"></i>
                    </a>
                  </div>
                </div>
                
                <div class="flex items-center gap-2">
                  <FileUpload
                    v-show="!isUploading"
                    mode="basic"
                    name="file"
                    accept="image/*"
                    :maxFileSize="5000000"
                    customUpload
                    @uploader="(e: any) => onFileUpload(e, field.name)"
                    :auto="true"
                    :chooseLabel="localForm[field.name] ? 'Change Image' : 'Upload Image'"
                    class="p-button-sm"
                  />
                  <small v-if="localForm[field.name]" class="text-slate-400 text-xs truncate max-w-[150px]">
                    {{ localForm[field.name] }}
                  </small>
                </div>
                <ProgressBar v-if="isUploading" mode="indeterminate" style="height: 6px" />
              </div>

              <!-- Fallback for unknown components -->
              <InputText
                v-else
                :id="field.name"
                v-model="localForm[field.name]"
                :placeholder="`Type unknown (${field.ui_component})`"
                class="w-full border-dashed border-slate-300"
              />

              <!-- Error Message -->
              <small v-if="fieldErrors[field.name]" class="text-red-500">
                {{ fieldErrors[field.name] }}
              </small>
            </div>
          </div>
        </div>

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
import InputText from 'primevue/inputtext'
import InputNumber from 'primevue/inputnumber'
import Select from 'primevue/select'
import MultiSelect from 'primevue/multiselect'
import FileUpload from 'primevue/fileupload'
import Checkbox from 'primevue/checkbox'
import RadioButton from 'primevue/radiobutton'
import Slider from 'primevue/slider'
import Button from 'primevue/button'
import ProgressBar from 'primevue/progressbar'
import Skeleton from 'primevue/skeleton'
import { useFormValidation } from '@/composables/useFormValidation'
import { useImageUpload } from '@/composables/useImageUpload'

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

// Setup validation using the composable
const schemaRef = computed(() => props.schema)
const { fieldErrors, fieldVisibility, isValid, validateField, validateAll, clearErrors } = 
  useFormValidation(schemaRef, localForm)

// Image path resolution
function getImagePath(path: string) {
  if (!path) return ''
  if (path.startsWith('http') || path.startsWith('data:')) return path
  
  const baseUrl = import.meta.env.VITE_API_BASE_URL || ''
  // Remove trailing slashes from base and leading from path
  return `${baseUrl.replace(/\/$/, '')}/${path.replace(/^\//, '')}`
}

// Image upload logic
const { uploadImage, isUploading } = useImageUpload()

async function onFileUpload(event: any, fieldName: string) {
  console.log('[DynamicForm] Starting upload for field:', fieldName)
  const file = event.files[0]
  if (!file) {
    console.warn('[DynamicForm] No file selected')
    return
  }

  const result = await uploadImage(file)
  console.log('[DynamicForm] Upload result:', result)
  
  if (result.success) {
    const finalPath = result.url || result.filename
    console.log('[DynamicForm] Setting field', fieldName, 'to path:', finalPath)
    localForm.value[fieldName] = finalPath
    validateField(fieldName)
    // Force reactivity for the property addition
    localForm.value = { ...localForm.value }
  } else {
    console.error('[DynamicForm] Upload failed:', result.error)
  }
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
 * Auto-calculate price fields based on length_of_beam
 * Formula: price_per_beam = price_per_meter * length_of_beam
 */
function autoCalculatePriceFields(fieldName: string) {
  console.log('[DynamicForm] autoCalculatePriceFields triggered for:', fieldName)
  
  // Use schema to find actual field names for calculation
  let lengthKey = 'length_of_beam'
  let priceMKey = 'price_per_meter'
  let priceBKey = 'price_per_beam'
  
  if (props.schema?.sections) {
    props.schema.sections.forEach((s: any) => {
      s.fields.forEach((f: any) => {
        const label = f.label?.toLowerCase() || ''
        if (label.includes('length of beam')) lengthKey = f.name
        else if (label === 'price/m') priceMKey = f.name
        else if (label.includes('price per beam')) priceBKey = f.name
      })
    })
  }

  const priceFields = [priceMKey, priceBKey, lengthKey]
  if (!priceFields.includes(fieldName)) return

  const currentData = localForm.value
  const length = parseDecimal(currentData[lengthKey])
  const priceM = parseDecimal(currentData[priceMKey])
  const priceB = parseDecimal(currentData[priceBKey])

  console.log('[DynamicForm] Calc context:', { 
    fieldName,
    keys: { lengthKey, priceMKey, priceBKey },
    values: { length, priceM, priceB }
  })

  if (length === null || length === 0) {
    console.log('[DynamicForm] Calc skipped: length is null or 0')
    return
  }

  if (fieldName === priceMKey && priceM !== null) {
    localForm.value[priceBKey] = roundToDecimals(priceM * length, 2)
  } else if (fieldName === priceBKey && priceB !== null) {
    localForm.value[priceMKey] = roundToDecimals(priceB / length, 2)
  } else if (fieldName === lengthKey && priceM !== null) {
    localForm.value[priceBKey] = roundToDecimals(priceM * length, 2)
  }
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


