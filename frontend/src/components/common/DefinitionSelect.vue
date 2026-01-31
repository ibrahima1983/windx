<template>
  <div class="definition-select">
    <SmartSelect
      :model-value="modelValue"
      :options="options"
      :option-label="optionLabel"
      :option-value="optionValue"
      :placeholder="placeholder"
      :loading="loading"
      :disabled="disabled"
      :class="class"
      :show-clear="showClear"
      @update:model-value="$emit('update:modelValue', $event)"
      @change="$emit('change', $event)"
    >
      <template #value="slotProps">
        <div v-if="slotProps.value && selectedOption" class="flex items-center gap-3">
          <div class="flex-1">
            <div class="font-semibold text-slate-900">{{ selectedOption[optionLabel] }}</div>
            <div v-if="selectedOption.description" class="text-sm text-slate-600 mt-1">
              {{ selectedOption.description }}
            </div>
          </div>
        </div>
        <span v-else class="text-slate-500">{{ placeholder }}</span>
      </template>
      
      <template #option="slotProps">
        <div class="flex items-center gap-3 py-2">
          <div class="flex-1">
            <div class="font-semibold text-slate-900">{{ slotProps.option[optionLabel] }}</div>
            <div v-if="slotProps.option.description" class="text-sm text-slate-600 mt-1">
              {{ slotProps.option.description }}
            </div>
          </div>
        </div>
      </template>
      
      <template #empty>
        <div class="text-center py-4 text-slate-500">
          No {{ entityType || 'options' }} found
        </div>
      </template>
    </SmartSelect>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import SmartSelect from '@/components/common/SmartSelect.vue'

interface Props {
  modelValue?: any
  options: any[]
  optionLabel?: string
  optionValue?: string
  placeholder?: string
  loading?: boolean
  disabled?: boolean
  class?: string
  showClear?: boolean
  entityType?: string
}

const props = withDefaults(defineProps<Props>(), {
  optionLabel: 'name',
  optionValue: 'id',
  placeholder: 'Select an option...',
  loading: false,
  disabled: false,
  class: '',
  showClear: true
})

const emit = defineEmits<{
  'update:modelValue': [value: any]
  'change': [event: any]
}>()

const selectedOption = computed(() => {
  if (!props.modelValue || !props.options.length) return null
  return props.options.find(option => option[props.optionValue] === props.modelValue)
})
</script>