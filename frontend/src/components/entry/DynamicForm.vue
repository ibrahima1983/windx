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
                @blur="validateField(field.name)"
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
                @blur="validateField(field.name)"
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
                @blur="validateField(field.name)"
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
                <div v-if="localForm[field.name]" class="relative w-32 h-32 rounded border border-slate-200 overflow-hidden bg-white group">
                  <img :src="getImagePath(localForm[field.name])" class="w-full h-full object-contain" />
                  <button 
                    type="button"
                    @click="localForm[field.name] = null" 
                    class="absolute top-1 right-1 bg-red-500 text-white rounded-full w-6 h-6 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
                  >
                    <i class="pi pi-trash text-xs"></i>
                  </button>
                </div>
                <FileUpload
                  v-show="!isUploading"
                  mode="basic"
                  name="demo[]"
                  url="/api/v1/admin/entry/upload-image"
                  accept="image/*"
                  :maxFileSize="5000000"
                  customUpload
                  @uploader="(e) => onFileUpload(e, field.name)"
                  :auto="true"
                  :chooseLabel="localForm[field.name] ? 'Change Image' : 'Upload Image'"
                  class="p-button-sm"
                />
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
watch(() => props.modelValue, (newVal) => {
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
  const file = event.files[0]
  if (!file) return

  const result = await uploadImage(file)
  if (result.success) {
    localForm.value[fieldName] = result.url || result.filename
    validateField(fieldName)
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
</script>


