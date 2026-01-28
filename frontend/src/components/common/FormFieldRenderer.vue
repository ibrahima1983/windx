<template>
  <div class="flex flex-col gap-2">
    <!-- Label -->
    <label v-if="field.label" :for="field.name" class="text-sm font-medium text-slate-700 flex items-center gap-1">
      <span>{{ field.label }}</span>
      <span v-if="field.required" class="text-red-500">*</span>
      <i 
        v-if="field.description" 
        class="pi pi-info-circle text-slate-400 cursor-help text-xs"
        v-tooltip.top="{ value: field.description, escape: false }"
      ></i>
    </label>

    <!-- Text Input -->
    <InputText
      v-if="['text', 'string'].includes(field.type) || field.ui_component === 'text'"
      :id="field.name"
      :modelValue="modelValue"
      @update:modelValue="(val) => emit('update:modelValue', val)"
      :placeholder="placeholder"
      class="w-full"
      :disabled="disabled"
      @blur="emit('blur', field.name)"
    />

    <!-- Textarea -->
    <Textarea
      v-else-if="field.type === 'textarea' || field.ui_component === 'textarea'"
      :id="field.name"
      :modelValue="modelValue"
      @update:modelValue="(val) => emit('update:modelValue', val)"
      :rows="3"
      :placeholder="placeholder"
      class="w-full"
      :disabled="disabled"
      @blur="emit('blur', field.name)"
    />

    <!-- Number Input -->
    <InputNumber
      v-else-if="field.type === 'number' || field.ui_component === 'number'"
      :id="field.name"
      :modelValue="modelValue"
      @update:modelValue="(val) => emit('update:modelValue', val)"
      :placeholder="placeholder || '0'"
      class="w-full"
      :maxFractionDigits="field.precision || 2"
      :disabled="disabled"
      @blur="emit('blur', field.name)"
    />

    <!-- Currency Input -->
    <InputNumber
      v-else-if="field.ui_component === 'currency'"
      :id="field.name"
      :modelValue="modelValue"
      @update:modelValue="(val) => emit('update:modelValue', val)"
      mode="currency"
      currency="USD"
      locale="en-US"
      :placeholder="placeholder || '$0.00'"
      class="w-full"
      :disabled="disabled"
      @blur="emit('blur', field.name)"
    />

    <!-- Percentage Input -->
    <InputNumber
      v-else-if="field.ui_component === 'percentage'"
      :id="field.name"
      :modelValue="modelValue"
      @update:modelValue="(val) => emit('update:modelValue', val)"
      suffix="%"
      :min="0"
      :max="100"
      :placeholder="placeholder || '0%'"
      class="w-full"
      :disabled="disabled"
      @blur="emit('blur', field.name)"
    />

    <!-- Checkbox / Boolean -->
    <div v-else-if="field.type === 'boolean' || field.ui_component === 'checkbox'" class="flex items-center gap-2 h-[42px]">
      <Checkbox
        :id="field.name"
        :modelValue="modelValue"
        @update:modelValue="(val) => emit('update:modelValue', val)"
        :binary="true"
        :disabled="disabled"
        @change="emit('change', field.name)"
      />
      <label :for="field.name" class="cursor-pointer text-slate-600">{{ field.label || 'Enabled' }}</label>
    </div>

    <!-- Select / Dropdown -->
    <Select
      v-else-if="field.ui_component === 'dropdown' || field.ui_component === 'select'"
      :id="field.name"
      :modelValue="modelValue"
      @update:modelValue="(val) => emit('update:modelValue', val)"
      :options="resolvedOptions"
      :optionLabel="optionLabel"
      :optionValue="optionValue"
      :placeholder="placeholder || 'Select...'"
      class="w-full"
      showClear
      :disabled="disabled"
      @change="emit('change', field.name)"
    />

    <!-- MultiSelect -->
    <ColorChipMultiSelect
      v-else-if="['multi-select', 'multiselect'].includes(field.ui_component)"
      :id="field.name"
      :modelValue="modelValue"
      @update:modelValue="(val) => emit('update:modelValue', val)"
      :options="resolvedOptions"
      :optionLabel="optionLabel"
      :optionValue="optionValue"
      :placeholder="placeholder || 'Select items...'"
      class="w-full"
      :disabled="disabled"
      @change="emit('change', field.name)"
    />

    <!-- Radio -->
    <div v-else-if="field.ui_component === 'radio'" class="flex flex-wrap gap-4 mt-1">
      <div v-for="option in resolvedOptions" :key="getErrorKey(option)" class="flex items-center">
        <RadioButton 
          :inputId="`${field.name}_${getErrorKey(option)}`"
          :modelValue="modelValue" 
          @update:modelValue="(val) => emit('update:modelValue', val)"
          :name="field.name" 
          :value="optionValue ? option[optionValue] : option" 
          :disabled="disabled"
          @change="emit('change', field.name)"
        />
        <label :for="`${field.name}_${getErrorKey(option)}`" class="ml-2 cursor-pointer">
          {{ optionLabel ? option[optionLabel] : option }}
        </label>
      </div>
    </div>

    <!-- Slider -->
    <div v-else-if="field.ui_component === 'slider'" class="px-2 py-4">
      <Slider 
        :modelValue="modelValue || 0" 
        @update:modelValue="(val) => emit('update:modelValue', val)"
        class="w-full"
        :min="field.validation_rules?.min || 0"
        :max="field.validation_rules?.max || 100"
        :disabled="disabled"
        @slideend="emit('change', field.name)"
      />
      <div class="flex justify-between text-xs text-slate-500 mt-2">
        <span>{{ field.validation_rules?.min || 0 }}</span>
        <span class="font-bold text-primary">{{ modelValue || 0 }}</span>
        <span>{{ field.validation_rules?.max || 100 }}</span>
      </div>
    </div>

    <!-- Image / File Upload -->
    <div v-else-if="['picture-input', 'file', 'image', 'pic'].includes(field.ui_component)" class="flex flex-col gap-2">
      <div v-if="modelValue" class="relative w-48 h-48 rounded-lg border-2 border-dashed border-slate-200 overflow-hidden bg-slate-50 group flex items-center justify-center">
        <img 
          :src="getImagePath(modelValue)" 
          class="w-full h-full object-contain"
          @error="(e) => (e.target as HTMLImageElement).src = 'https://placehold.co/200x200?text=Invalid+Image'" 
        />
        <div class="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-2">
          <Button 
            icon="pi pi-trash" 
            severity="danger" 
            rounded 
            @click="emit('update:modelValue', null)" 
            v-tooltip.bottom="'Remove Image'"
          />
          <a :href="getImagePath(modelValue)" target="_blank" class="p-button p-button-icon-only p-button-info p-button-rounded no-underline flex items-center justify-center">
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
          @uploader="handleFileUpload"
          :auto="true"
          :chooseLabel="modelValue ? 'Change Image' : 'Upload Image'"
          class="p-button-sm"
          :disabled="disabled"
        />
        <small v-if="modelValue" class="text-slate-400 text-xs truncate max-w-[150px]">
          {{ modelValue }}
        </small>
      </div>
      <ProgressBar v-if="isUploading" mode="indeterminate" style="height: 6px" />
    </div>

    <!-- Fallback -->
    <InputText
      v-else
      :id="field.name"
      :modelValue="modelValue"
      @update:modelValue="(val) => emit('update:modelValue', val)"
      :placeholder="`Type unknown (${field.ui_component || field.type})`"
      class="w-full border-dashed border-slate-300"
      :disabled="disabled"
    />

    <!-- Error Message -->
    <small v-if="error" class="text-red-500">
      {{ error }}
    </small>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import InputText from 'primevue/inputtext'
import InputNumber from 'primevue/inputnumber'
import Textarea from 'primevue/textarea'
import Checkbox from 'primevue/checkbox'
import Select from 'primevue/select'
import RadioButton from 'primevue/radiobutton'
import Slider from 'primevue/slider'
import FileUpload from 'primevue/fileupload'
import Button from 'primevue/button'
import ProgressBar from 'primevue/progressbar'
import ColorChipMultiSelect from '@/components/common/ColorChipMultiSelect.vue'
import { useImageUpload } from '@/composables/useImageUpload'

const props = defineProps<{
  field: any
  modelValue: any
  options?: any[]
  error?: string
  disabled?: boolean
}>()

const emit = defineEmits(['update:modelValue', 'change', 'blur'])

// Resolving options: either from props (external) or field definition (internal)
const resolvedOptions = computed(() => props.options || props.field.options_data || props.field.options || [])
const optionLabel = computed(() => props.field.optionLabel || (props.field.options_data ? 'name' : undefined))
const optionValue = computed(() => props.field.optionValue || (props.field.options_data ? 'name' : undefined))

const placeholder = computed(() => {
  // Explicitly check if placeholder exists in field (even if empty string)
  if (props.field.placeholder !== undefined && props.field.placeholder !== null) {
    return props.field.placeholder
  }
  if (props.field.required) return `Enter ${props.field.label}`
  return 'Optional'
})

// Helper for Radio keys
function getErrorKey(option: any) {
  return typeof option === 'string' ? option : (option.value || option.name || JSON.stringify(option))
}

// Image Handling
const { uploadImage, isUploading } = useImageUpload()

function getImagePath(path: string) {
  if (!path) return ''
  if (path.startsWith('http') || path.startsWith('data:')) return path
  
  const baseUrl = import.meta.env.VITE_API_BASE_URL || ''
  return `${baseUrl.replace(/\/$/, '')}/${path.replace(/^\//, '')}`
}

async function handleFileUpload(event: any) {
  const file = event.files[0]
  if (!file) return

  const result = await uploadImage(file)
  if (result.success) {
    emit('update:modelValue', result.url || result.filename)
    emit('change', props.field.name)
  } else {
    console.error('Upload failed', result.error)
  }
}
</script>
