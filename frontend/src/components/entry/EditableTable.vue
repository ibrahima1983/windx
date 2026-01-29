<template>
  <Card>
    <template #title>
      <div class="flex justify-between items-center">
        <div class="flex items-center gap-3">
          <span>{{ title }}</span>
          <Badge 
            v-if="selectedRows.length > 0" 
            :value="selectedRows.length" 
            severity="info"
            class="ml-2"
          />
        </div>
        <div class="flex gap-2">
          <Button 
            v-if="selectedRows.length > 0"
            :label="`Delete ${selectedRows.length} Selected`"
            icon="pi pi-trash"
            @click="showBulkDeleteDialog = true"
            severity="danger"
            outlined
            size="small"
          />
          <Button 
            v-if="hasPendingChanges"
            label="Save All Changes"
            icon="pi pi-check"
            @click="$emit('commit')"
            :loading="loading"
            severity="success"
            size="small"
          />
        </div>
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
        v-model:selection="selectedRows"
        :selectAll="selectAll"
        @select-all-change="onSelectAllChange"
        @row-select="onRowSelect"
        @row-unselect="onRowUnselect"
        stripedRows
        showGridlines
      >
        <!-- Enhanced Selection Column -->
        <Column selectionMode="multiple" headerStyle="width: 3rem" />

        <Column 
          v-for="header in headers" 
          :key="header"
          :field="header"
          :header="header"
          :sortable="true"
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
              size="small"
            />
          </template>
        </Column>

        <Column :rowEditor="true" style="width:10%; min-width:8rem" header="Edit" />
        
        <Column style="width:5%" header="Actions">
          <template #body="slotProps">
            <Button 
              icon="pi pi-trash" 
              @click="confirmSingleDelete(slotProps.data)"
              severity="danger"
              text
              rounded
              size="small"
              v-tooltip.top="'Delete this item'"
            />
          </template>
        </Column>

        <template #empty>
          <div class="text-center py-8">
            <i class="pi pi-inbox text-4xl text-gray-400 mb-4 block"></i>
            <p class="text-gray-500 text-lg mb-2">No entries found</p>
            <p class="text-gray-400 text-sm">Create one using the form above</p>
          </div>
        </template>
      </DataTable>
    </template>
  </Card>

  <!-- Enhanced Bulk Delete Confirmation Dialog -->
  <Dialog 
    v-model:visible="showBulkDeleteDialog" 
    modal 
    :header="`Delete ${selectedRows.length} Configuration${selectedRows.length > 1 ? 's' : ''}`"
    :style="{ width: '32rem' }"
    :breakpoints="{ '1199px': '75vw', '575px': '90vw' }"
  >
    <div class="flex items-start gap-4">
      <div class="flex-shrink-0">
        <div class="w-12 h-12 rounded-full bg-red-100 flex items-center justify-center">
          <i class="pi pi-exclamation-triangle text-red-600 text-xl"></i>
        </div>
      </div>
      <div class="flex-1">
        <h3 class="text-lg font-semibold text-gray-900 mb-2">
          Are you sure you want to delete these configurations?
        </h3>
        <p class="text-gray-600 mb-4">
          This action will permanently delete {{ selectedRows.length }} configuration{{ selectedRows.length > 1 ? 's' : '' }}. 
          This action cannot be undone.
        </p>
        
        <!-- Show list of items to be deleted -->
        <div class="bg-gray-50 rounded-lg p-3 max-h-32 overflow-y-auto">
          <div class="text-sm font-medium text-gray-700 mb-2">Items to delete:</div>
          <ul class="space-y-1">
            <li 
              v-for="row in selectedRows.slice(0, 5)" 
              :key="row.id"
              class="text-sm text-gray-600 flex items-center gap-2"
            >
              <i class="pi pi-file text-xs"></i>
              {{ row.name || `Configuration #${row.id}` }}
            </li>
            <li v-if="selectedRows.length > 5" class="text-sm text-gray-500 italic">
              ... and {{ selectedRows.length - 5 }} more
            </li>
          </ul>
        </div>
      </div>
    </div>
    
    <template #footer>
      <div class="flex justify-end gap-2">
        <Button 
          label="Cancel" 
          icon="pi pi-times" 
          @click="showBulkDeleteDialog = false" 
          text 
          severity="secondary"
        />
        <Button 
          label="Delete All" 
          icon="pi pi-trash" 
          @click="handleBulkDelete" 
          severity="danger"
          :loading="bulkDeleteLoading"
        />
      </div>
    </template>
  </Dialog>

  <!-- Single Delete Confirmation Dialog -->
  <Dialog 
    v-model:visible="showSingleDeleteDialog" 
    modal 
    header="Delete Configuration"
    :style="{ width: '28rem' }"
    :breakpoints="{ '1199px': '75vw', '575px': '90vw' }"
  >
    <div class="flex items-start gap-4">
      <div class="flex-shrink-0">
        <div class="w-10 h-10 rounded-full bg-red-100 flex items-center justify-center">
          <i class="pi pi-trash text-red-600"></i>
        </div>
      </div>
      <div class="flex-1">
        <p class="text-gray-700">
          Are you sure you want to delete 
          <strong>"{{ itemToDelete?.name || `Configuration #${itemToDelete?.id}` }}"</strong>?
        </p>
        <p class="text-sm text-gray-500 mt-2">This action cannot be undone.</p>
      </div>
    </div>
    
    <template #footer>
      <div class="flex justify-end gap-2">
        <Button 
          label="Cancel" 
          icon="pi pi-times" 
          @click="showSingleDeleteDialog = false" 
          text 
          severity="secondary"
        />
        <Button 
          label="Delete" 
          icon="pi pi-trash" 
          @click="handleSingleDelete" 
          severity="danger"
        />
      </div>
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import { ref, computed, nextTick } from 'vue'
import Card from 'primevue/card'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import InputText from 'primevue/inputtext'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import Badge from 'primevue/badge'
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
  (e: 'bulk-delete', data: any[]): void
  (e: 'commit'): void
  (e: 'cell-update', data: { rowId: any, field: string, value: any, calculatedFields?: string[] }): void
}>()

const editingRows = ref([])
const selectedRows = ref([])
const selectAll = ref(false)
const highlightedCells = ref<Set<string>>(new Set())
const showBulkDeleteDialog = ref(false)
const showSingleDeleteDialog = ref(false)
const itemToDelete = ref<any>(null)
const bulkDeleteLoading = ref(false)
const logger = useDebugLogger('EditableTable')

// Setup auto-calculation
const schemaRef = computed(() => props.schema)
const dummyFormData = ref<Record<string, any>>({})
const { autoCalculateFields, parseDecimal, isFieldCalculated, clearCalculatedFields } = 
  useAutoCalculation(schemaRef, dummyFormData)

function onRowEditSave(event: any) {
  emit('row-save', event)
}

function onSelectAllChange(event: any) {
  selectAll.value = event.checked
  if (event.checked) {
    selectedRows.value = [...props.data]
  } else {
    selectedRows.value = []
  }
}

function toggleSelectAll(checked: boolean) {
  selectAll.value = checked
  if (checked) {
    selectedRows.value = [...props.data]
  } else {
    selectedRows.value = []
  }
}

function onRowSelect(event: any) {
  logger.debug('Row selected', { rowId: event.data.id })
  updateSelectAllState()
}

function onRowUnselect(event: any) {
  logger.debug('Row unselected', { rowId: event.data.id })
  updateSelectAllState()
}

function updateSelectAllState() {
  if (selectedRows.value.length === 0) {
    selectAll.value = false
  } else if (selectedRows.value.length === props.data.length) {
    selectAll.value = true
  }
}

function confirmSingleDelete(data: any) {
  itemToDelete.value = data
  showSingleDeleteDialog.value = true
}

function handleSingleDelete() {
  if (itemToDelete.value) {
    emit('delete', itemToDelete.value)
    showSingleDeleteDialog.value = false
    itemToDelete.value = null
  }
}

async function handleBulkDelete() {
  bulkDeleteLoading.value = true
  try {
    emit('bulk-delete', selectedRows.value)
    showBulkDeleteDialog.value = false
    selectedRows.value = []
    selectAll.value = false
  } finally {
    bulkDeleteLoading.value = false
  }
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

/* Enhanced selection styling */
.editable-table-with-calc :deep(.p-datatable-tbody > tr.p-datatable-row-selected) {
  background-color: #eff6ff !important;
  border-left: 3px solid #3b82f6;
}

.editable-table-with-calc :deep(.p-datatable-tbody > tr.p-datatable-row-selected:hover) {
  background-color: #dbeafe !important;
}

/* Better checkbox styling */
.editable-table-with-calc :deep(.p-checkbox) {
  width: 18px;
  height: 18px;
}

.editable-table-with-calc :deep(.p-checkbox .p-checkbox-box) {
  border-radius: 4px;
  border: 2px solid #d1d5db;
  transition: all 0.2s ease;
}

.editable-table-with-calc :deep(.p-checkbox .p-checkbox-box:hover) {
  border-color: #3b82f6;
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.1);
}

.editable-table-with-calc :deep(.p-checkbox .p-checkbox-box.p-highlight) {
  background-color: #3b82f6;
  border-color: #3b82f6;
}

/* Enhanced empty state */
.editable-table-with-calc :deep(.p-datatable-emptymessage) {
  padding: 3rem 1rem;
}

/* Better button spacing in header */
.editable-table-with-calc :deep(.p-datatable-header) {
  padding: 1rem;
  background: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
}

/* Improved dialog styling */
:deep(.p-dialog .p-dialog-header) {
  background: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
}

:deep(.p-dialog .p-dialog-content) {
  padding: 1.5rem;
}

:deep(.p-dialog .p-dialog-footer) {
  background: #f8fafc;
  border-top: 1px solid #e2e8f0;
  padding: 1rem 1.5rem;
}

/* Badge styling */
:deep(.p-badge) {
  font-size: 0.75rem;
  min-width: 1.5rem;
  height: 1.5rem;
  line-height: 1.5rem;
}
</style>
