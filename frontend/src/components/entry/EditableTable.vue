<template>
  <Card>
    <template #title>
      <div class="flex justify-between items-center">
        <span>{{ title }}</span>
        <Button 
          v-if="hasPendingChanges"
          label="Save All Changes"
          icon="pi pi-check"
          @click="$emit('commit')"
          :loading="loading"
          severity="success"
        />
      </div>
    </template>
    <template #content>
      <DataTable
        :value="data"
        editMode="row"
        dataKey="id"
        @row-edit-save="onRowEditSave"
        :loading="loading"
        paginator
        :rows="10"
        class="p-datatable-sm editable-table-with-calc"
        v-model:editingRows="editingRows"
      >
        <Column 
          v-for="header in headers" 
          :key="header"
          :field="header"
          :header="header"
        >
          <template #body="{ data, field }">
            <div 
              :class="getCellClass(data.id, field)"
              :data-row-id="data.id"
              :data-field="field"
            >
              {{ formatCellValue(data[field], field) }}
            </div>
          </template>
          <template #editor="{ data, field }">
            <InputText 
              v-model="data[field]" 
              class="w-full" 
              @input="onCellEdit(data, field, $event.target.value)"
            />
          </template>
        </Column>

        <Column :rowEditor="true" style="width:10%; min-width:8rem" />
        
        <Column style="width:5%">
          <template #body="slotProps">
            <Button 
              icon="pi pi-trash" 
              @click="$emit('delete', slotProps.data)"
              severity="danger"
              text
              rounded
            />
          </template>
        </Column>

        <template #empty>
          <div class="text-center py-4 text-gray-500">
            No entries found. Create one using the form above.
          </div>
        </template>
      </DataTable>
    </template>
  </Card>
</template>

<script setup lang="ts">
import { ref, computed, nextTick } from 'vue'
import Card from 'primevue/card'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import InputText from 'primevue/inputtext'
import Button from 'primevue/button'
import { useAutoCalculation } from '@/composables/useAutoCalculation'
import { useDebugLogger } from '@/composables/useDebugLogger'

const props = defineProps<{
  data: any[]
  headers: string[]
  loading: boolean
  hasPendingChanges: boolean
  title?: string
  schema?: any // Schema for auto-calculation
}>()

const emit = defineEmits<{
  (e: 'row-save', event: any): void
  (e: 'delete', data: any): void
  (e: 'commit'): void
  (e: 'cell-update', data: { rowId: any, field: string, value: any, calculatedFields?: string[] }): void
}>()

const editingRows = ref([])
const highlightedCells = ref<Set<string>>(new Set())
const logger = useDebugLogger('EditableTable')

// Setup auto-calculation
const schemaRef = computed(() => props.schema)
const dummyFormData = ref<Record<string, any>>({})
const { autoCalculateFields, parseDecimal, isFieldCalculated, clearCalculatedFields } = 
  useAutoCalculation(schemaRef, dummyFormData)

function onRowEditSave(event: any) {
  emit('row-save', event)
}

function onCellEdit(rowData: any, field: string, newValue: any) {
  const oldValue = rowData[field]
  
  logger.debug('Cell edited', { 
    rowId: rowData.id, 
    field, 
    oldValue, 
    newValue 
  })
  
  // Update the row data
  rowData[field] = newValue
  
  // If we have schema, perform auto-calculation
  if (props.schema) {
    // Set up temporary form data for calculation
    dummyFormData.value = { ...rowData }
    
    // Clear previous calculated fields tracking
    clearCalculatedFields()
    
    // Perform auto-calculation
    const calculatedFields = autoCalculateFields(field)
    
    // Update the row data with calculated values
    calculatedFields.forEach(calcField => {
      rowData[calcField] = dummyFormData.value[calcField]
    })
    
    // Emit the update with calculated fields info
    emit('cell-update', {
      rowId: rowData.id,
      field,
      value: newValue,
      calculatedFields
    })
    
    // Highlight calculated cells
    if (calculatedFields.length > 0) {
      logger.info('Highlighting calculated cells', { 
        calculatedFields,
        rowId: rowData.id 
      })
      
      nextTick(() => {
        calculatedFields.forEach(calcField => {
          highlightCalculatedCell(rowData.id, calcField)
        })
      })
    }
  } else {
    // No schema, just emit the basic update
    logger.debug('No schema provided, skipping auto-calculation')
    emit('cell-update', {
      rowId: rowData.id,
      field,
      value: newValue
    })
  }
}

function highlightCalculatedCell(rowId: any, field: string) {
  const cellKey = `${rowId}-${field}`
  highlightedCells.value.add(cellKey)
  
  logger.debug('Highlighting calculated cell', { rowId, field, cellKey })
  
  // Remove highlight after animation duration
  setTimeout(() => {
    highlightedCells.value.delete(cellKey)
    logger.debug('Removed highlight from cell', { rowId, field, cellKey })
  }, 1500)
}

function getCellClass(rowId: any, field: string): string {
  const cellKey = `${rowId}-${field}`
  const isHighlighted = highlightedCells.value.has(cellKey)
  
  return isHighlighted ? 'auto-calculated-highlight' : ''
}

function formatCellValue(value: any, field: string): string {
  if (value === null || value === undefined) return ''
  
  // Format numeric values for price fields
  if (typeof value === 'number' && (field.includes('price') || field.includes('cost'))) {
    return value.toFixed(2)
  }
  
  return String(value)
}
</script>

<style scoped>
/* Auto-calculated cell highlight animation */
@keyframes autoCalcHighlight {
  0% {
    background-color: #fef08a;
    box-shadow: inset 0 0 0 2px #eab308;
  }
  100% {
    background-color: transparent;
    box-shadow: none;
  }
}

/* Auto-calculated cell highlight class */
.auto-calculated-highlight {
  animation: autoCalcHighlight 1s ease-out forwards;
  position: relative;
  border-radius: 4px;
}

/* Optional: Add a subtle indicator icon during highlight */
.auto-calculated-highlight::after {
  content: "✓";
  position: absolute;
  top: 50%;
  right: 8px;
  transform: translateY(-50%);
  color: #16a34a;
  font-size: 0.75rem;
  font-weight: bold;
  opacity: 1;
  animation: fadeOutIcon 1s ease-out forwards;
}

@keyframes fadeOutIcon {
  0% {
    opacity: 1;
  }
  70% {
    opacity: 1;
  }
  100% {
    opacity: 0;
  }
}

/* Enhanced table styling for better visual feedback */
.editable-table-with-calc :deep(.p-datatable-tbody > tr > td) {
  transition: all 0.2s ease;
}

/* Highlight auto-calculated cells in table */
.editable-table-with-calc :deep(.auto-calculated-highlight) {
  background-color: #fef3c7 !important;
  border: 2px solid #f59e0b !important;
  animation: autoCalculatedPulse 1.5s ease-out;
}

@keyframes autoCalculatedPulse {
  0% {
    background-color: #fbbf24;
    transform: scale(1.02);
  }
  50% {
    background-color: #fef3c7;
    transform: scale(1.01);
  }
  100% {
    background-color: #fef3c7;
    transform: scale(1);
  }
}
</style>
