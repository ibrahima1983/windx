<template>
  <MultiSelect 
    v-model="model"
    :options="options"
    :optionLabel="optionLabel"
    :optionValue="optionValue"
    :placeholder="placeholder"
    class="w-full professional-chip-multiselect"
    display="chip"
    v-bind="$attrs"
  >
    <template #chip="slotProps">
      <div 
        class="color-chip"
        :style="getChipStyle(slotProps.value)"
      >
        <span class="color-chip-label">{{ getColorName(slotProps.value) }}</span>
        <button 
          type="button"
          class="color-chip-remove"
          @click.stop="(e) => slotProps.removeCallback(e, slotProps.value)"
          aria-label="Remove color"
        >
          <i class="pi pi-times"></i>
        </button>
      </div>
    </template>
  </MultiSelect>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import MultiSelect from 'primevue/multiselect'


const props = defineProps<{
  modelValue: any[]
  options: any[]
  optionLabel?: string
  optionValue?: string
  placeholder?: string
}>()

const emit = defineEmits<{
  'update:modelValue': [value: any[]]
}>()

const model = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value)
})

// Helper to resolve the display label for an option
function getOptionLabel(option: any): string {
  if (option === null || option === undefined) return ''
  if (typeof option !== 'object') return String(option)
  if (props.optionLabel && option[props.optionLabel] !== undefined) return option[props.optionLabel]
  if (option.name !== undefined) return option.name
  if (option.label !== undefined) return option.label
  return String(option)
}

// Helper to resolve the value for comparison
function getOptionValue(option: any): any {
  if (option === null || option === undefined) return null
  if (typeof option !== 'object') return option
  if (props.optionValue && option[props.optionValue] !== undefined) return option[props.optionValue]
  if (option.id !== undefined) return option.id
  if (option.value !== undefined) return option.value
  return option
}

// Find the full option object from a selected value
function findOption(value: any) {
  return props.options.find(opt => getOptionValue(opt) === value)
}

function getColorName(value: any): string {
  const option = findOption(value)
  if (option) return getOptionLabel(option)
  return String(value)
}

function getChipStyle(value: any): { backgroundColor: string; color: string; borderColor: string } {
  const colorName = getColorName(value)
  const bgColor = getColorForChip(colorName)
  return {
    backgroundColor: bgColor,
    color: getContrastTextColor(bgColor),
    borderColor: getBorderColor(bgColor)
  }
}

// Professional Color Management
const COLOR_PALETTE: Record<string, string> = {
  // Whites / Off-whites
  'white': '#F8FAFC',
  'snow': '#FFFAFA',
  'ivory': '#FFFFF0',
  'cream': '#FFFDD0',
  'beige': '#F5F5DC',
  'silver': '#C0C0C0',
  
  // Grays / Blacks
  'black': '#1a1a1a',
  'gray': '#6B7280',
  'grey': '#6B7280',
  'slate': '#475569',
  'charcoal': '#36454F',
  
  // Reds / Pinks
  'red': '#EF4444',
  'rose': '#F43F5E',
  'crimson': '#DC143C',
  'maroon': '#800000',
  'pink': '#EC4899',
  'fuchsia': '#D946EF',
  
  // Oranges / Yellows
  'orange': '#F97316',
  'amber': '#F59E0B',
  'yellow': '#EAB308',
  'gold': '#FFD700',
  'bronze': '#CD7F32',
  'brown': '#92400E',
  
  // Greens
  'green': '#22C55E',
  'emerald': '#10B981',
  'lime': '#84CC16',
  'olive': '#808000',
  'teal': '#14B8A6',
  
  // Blues
  'blue': '#3B82F6',
  'navy': '#000080',
  'sky': '#0EA5E9',
  'cyan': '#06B6D4',
  'indigo': '#6366F1',
  'royal': '#4169E1',
  
  // Purples
  'purple': '#A855F7',
  'violet': '#8B5CF6',
  'magenta': '#FF00FF',
}

function getColorForChip(colorName: string): string {
  if (!colorName) return '#E2E8F0'
  const name = String(colorName).toLowerCase().trim()
  
  // 1. Exact match
  if (COLOR_PALETTE[name]) return COLOR_PALETTE[name]
  
  // 2. Fuzzy match
  const matches = Object.keys(COLOR_PALETTE).filter(key => name.includes(key))
  if (matches.length > 0) {
    const sorted = matches.sort((a, b) => b.length - a.length)
    const bestMatch = sorted[0]
    if (bestMatch && COLOR_PALETTE[bestMatch]) {
      return COLOR_PALETTE[bestMatch]
    }
  }
  
  // 3. Fallback: Hash generation
  return stringToColor(name)
}

function stringToColor(str: string): string {
  let hash = 0
  for (let i = 0; i < str.length; i++) {
    hash = str.charCodeAt(i) + ((hash << 5) - hash)
  }
  const c = (hash & 0x00ffffff).toString(16).toUpperCase()
  return '#' + '00000'.substring(0, 6 - c.length) + c
}

function getContrastTextColor(hexColor: string): string {
  const hex = hexColor.replace('#', '')
  const r = parseInt(hex.substring(0, 2), 16)
  const g = parseInt(hex.substring(2, 4), 16)
  const b = parseInt(hex.substring(4, 6), 16)
  
  const uicolors = [r / 255, g / 255, b / 255]
  const c = uicolors.map((col) => {
    if (col <= 0.03928) {
      return col / 12.92
    }
    return Math.pow((col + 0.055) / 1.055, 2.4)
  })
  
  const rL = c[0] ?? 0
  const gL = c[1] ?? 0
  const bL = c[2] ?? 0
  
  const L = 0.2126 * rL + 0.7152 * gL + 0.0722 * bL
  
  return L > 0.4 ? '#1F2937' : '#FFFFFF'
}

function getBorderColor(hexColor: string): string {
  return getContrastTextColor(hexColor) === '#1F2937' ? '#E2E8F0' : 'transparent'
}


</script>

<style scoped>
/* Keep default PrimeVue input padding - don't override */
:deep(.professional-chip-multiselect .p-chip) {
  margin: 0;
  padding: 0;
  background: transparent !important;
  border: none !important;
}

/* Main Color Chip Container - Modern Minimal Design */
.color-chip {
  /* Layout */
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  
  /* Spacing - Compact modern look */
  padding: 0.375rem 0.625rem;
  padding-right: 0.5rem;
  
  /* Visual - Clean minimal border */
  border-radius: 0.375rem;
  border-width: 1px;
  border-style: solid;
  
  /* No shadow - flat modern design */
  box-shadow: none;
  
  /* Typography */
  font-size: 0.875rem;
  font-weight: 500;
  line-height: 1.25rem;
  
  /* Smooth transition */
  transition: all 0.2s ease;
  
  /* Interaction */
  cursor: default;
  user-select: none;
}

.color-chip:hover {
  /* Subtle opacity change on hover */
  opacity: 0.9;
}

/* Chip Label */
.color-chip-label {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 120px;
  
  /* Smooth text */
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

/* Remove Button - Minimal Circle with × */
.color-chip-remove {
  /* Layout */
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  
  /* Size - small and minimal */
  width: 1rem;
  height: 1rem;
  
  /* Visual - transparent background */
  border-radius: 50%;
  background: transparent;
  border: none;
  padding: 0;
  
  /* Interaction */
  cursor: pointer;
  transition: all 0.2s ease;
  
  /* Icon */
  font-size: 0.75rem;
  opacity: 0.6;
}

.color-chip-remove:hover {
  opacity: 1;
  background: rgba(0, 0, 0, 0.1);
}

.color-chip-remove:active {
  transform: scale(0.9);
}

.color-chip-remove i {
  pointer-events: none;
  line-height: 1;
}

/* Light background adjustment for remove button */
.color-chip[style*="color: rgb(31, 41, 55)"] .color-chip-remove:hover,
.color-chip[style*="color: #1F2937"] .color-chip-remove:hover {
  background: rgba(0, 0, 0, 0.08);
}

/* Dark background adjustment for remove button */
.color-chip[style*="color: rgb(255, 255, 255)"] .color-chip-remove:hover,
.color-chip[style*="color: #FFFFFF"] .color-chip-remove:hover {
  background: rgba(255, 255, 255, 0.2);
}

/* Ensure proper spacing in the multiselect */
:deep(.professional-chip-multiselect .p-multiselect-chip-item) {
  margin: 0.125rem;
}

/* Focus states for accessibility */
.color-chip-remove:focus-visible {
  outline: 2px solid currentColor;
  outline-offset: 2px;
  border-radius: 50%;
}
</style>
