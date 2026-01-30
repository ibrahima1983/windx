<template>
  <div class="search-bar">
    <!-- Main Search Input -->
    <div class="flex items-center gap-2 mb-3">
      <div class="flex-1 relative">
        <IconField iconPosition="left" class="w-full">
          <InputIcon class="pi pi-search" />
          <InputText
            v-model="searchQuery"
            placeholder="Search across all columns..."
            class="w-full pr-10"
            @input="onSearchInput"
            @keyup.escape="clearSearch"
          />
        </IconField>
        <Button
          v-if="searchQuery"
          icon="pi pi-times"
          class="absolute right-2 top-1/2 -translate-y-1/2 z-10"
          text
          rounded
          size="small"
          @click="clearSearch"
          v-tooltip.top="'Clear search'"
        />
      </div>
      
      <Button
        :icon="showAdvancedSearch ? 'pi pi-chevron-up' : 'pi pi-chevron-down'"
        :label="showAdvancedSearch ? 'Hide Filters' : 'Show Filters'"
        @click="toggleAdvancedSearch"
        outlined
        size="small"
      />
      
      <Button
        v-if="isSearchActive"
        icon="pi pi-download"
        label="Export"
        @click="exportResults"
        severity="secondary"
        outlined
        size="small"
        v-tooltip.top="'Export filtered results'"
      />
    </div>

    <!-- Search Stats -->
    <div v-if="isSearchActive" class="flex items-center justify-between mb-3 text-sm">
      <div class="flex items-center gap-4">
        <span class="text-gray-600">
          Showing {{ searchStats.filteredRecords }} of {{ searchStats.totalRecords }} records
        </span>
        <Badge
          v-if="searchStats.hiddenRecords > 0"
          :value="`${searchStats.hiddenRecords} hidden`"
          severity="secondary"
        />
      </div>
      
      <div class="flex items-center gap-2">
        <Button
          label="Clear All"
          icon="pi pi-times"
          @click="clearAll"
          text
          size="small"
          severity="secondary"
        />
      </div>
    </div>

    <!-- Advanced Search Panel -->
    <div v-if="showAdvancedSearch" class="advanced-search-panel">
      <Divider align="left">
        <span class="text-sm font-medium text-gray-600">Column Filters</span>
      </Divider>
      
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        <div
          v-for="header in headers"
          :key="header"
          class="flex flex-col gap-1"
        >
          <label class="text-xs font-medium text-gray-600">{{ header }}</label>
          <div class="relative">
            <InputText
              :modelValue="columnFilters[header] || ''"
              @update:modelValue="(value) => setColumnFilter(header, value)"
              :placeholder="`Filter ${header}...`"
              class="w-full text-sm"
              size="small"
            />
            <Button
              v-if="columnFilters[header]"
              icon="pi pi-times"
              class="absolute right-1 top-1/2 -translate-y-1/2"
              text
              rounded
              size="small"
              @click="setColumnFilter(header, '')"
            />
          </div>
        </div>
      </div>
      
      <div v-if="searchStats.activeFiltersCount > 0" class="mt-3 flex items-center gap-2">
        <span class="text-xs text-gray-500">Active filters:</span>
        <div class="flex flex-wrap gap-1">
          <Chip
            v-for="[header, value] in activeFilters"
            :key="header"
            :label="`${header}: ${value}`"
            removable
            @remove="setColumnFilter(header, '')"
            class="text-xs"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import InputText from 'primevue/inputtext'
import Button from 'primevue/button'
import IconField from 'primevue/iconfield'
import InputIcon from 'primevue/inputicon'
import Badge from 'primevue/badge'
import Divider from 'primevue/divider'
import Chip from 'primevue/chip'
import type { SearchStats } from '@/composables/useTableSearch'

interface Props {
  searchQuery: string
  columnFilters: Record<string, string>
  showAdvancedSearch: boolean
  headers: string[]
  searchStats: SearchStats
  isSearchActive: boolean
}

const props = defineProps<Props>()

const emit = defineEmits<{
  'update:searchQuery': [value: string]
  'update:columnFilters': [filters: Record<string, string>]
  'update:showAdvancedSearch': [show: boolean]
  'export': []
  'clear-search': []
  'clear-all': []
}>()

const searchQuery = computed({
  get: () => props.searchQuery,
  set: (value) => emit('update:searchQuery', value)
})

const columnFilters = computed({
  get: () => props.columnFilters,
  set: (value) => emit('update:columnFilters', value)
})

const showAdvancedSearch = computed({
  get: () => props.showAdvancedSearch,
  set: (value) => emit('update:showAdvancedSearch', value)
})

const activeFilters = computed(() => {
  return Object.entries(props.columnFilters).filter(([_, value]) => value && value.trim())
})

function onSearchInput(event: Event) {
  const target = event.target as HTMLInputElement
  searchQuery.value = target.value
}

function setColumnFilter(header: string, value: string) {
  const newFilters = { ...props.columnFilters }
  if (value && value.trim()) {
    newFilters[header] = value
  } else {
    delete newFilters[header]
  }
  emit('update:columnFilters', newFilters)
}

function toggleAdvancedSearch() {
  showAdvancedSearch.value = !showAdvancedSearch.value
}

function clearSearch() {
  emit('clear-search')
}

function clearAll() {
  emit('clear-all')
}

function exportResults() {
  emit('export')
}
</script>

<style scoped>
@reference "tailwindcss";

.search-bar {
  @apply bg-white border border-gray-200 rounded-lg p-4 mb-4;
}

.advanced-search-panel {
  @apply mt-4 p-4 bg-gray-50 rounded-lg border border-gray-100;
}

/* Search term highlighting */
:deep(.search-term-highlight) {
  @apply bg-amber-100 text-amber-900 px-1 rounded font-medium;
}

/* Row highlighting animation */
@keyframes searchHighlight {
  0% {
    background-color: rgb(251 191 36 / 0.3);
  }
  100% {
    background-color: transparent;
  }
}

:deep(.search-highlight) {
  background-color: rgb(254 243 199 / 0.5) !important;
  animation: searchHighlight 0.6s cubic-bezier(0.4, 0, 0.2, 1) !important;
}
</style>