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
      <!-- Enhanced Search Bar -->
      <SearchBar
        v-model:searchQuery="searchQuery"
        v-model:columnFilters="columnFilters"
        v-model:showAdvancedSearch="showAdvancedSearch"
        :headers="headers"
        :searchStats="searchStats"
        :isSearchActive="!!isSearchActive"
        @export="handleExportResults"
        @clear-search="clearSearch"
        @clear-all="clearAll"
        class="mb-4"
      />

      <DataTable
        :value="filteredData"
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
              :class="getCellClass(data.id, String(field))"
              :data-row-id="data.id"
              :data-field="String(field)"
            >
              <!-- Image display for image fields -->
              <div v-if="isImageField(String(field)) && getFieldValue(data, String(field))" class="image-cell">
                <img 
                  :src="getImagePath(String(getFieldValue(data, String(field))))" 
                  class="w-12 h-12 object-cover rounded border cursor-pointer"
                  @click="openImagePreview(String(getFieldValue(data, String(field))))"
                  @error="(e) => (e.target as HTMLImageElement).src = 'https://placehold.co/48x48?text=Invalid'"
                  :title="String(getFieldValue(data, String(field)))"
                />
              </div>
              <!-- Regular text display -->
              <div 
                v-else
                v-html="getHighlightedCellValue(getFieldValue(data, String(field)), String(field))"
              />
            </div>
          </template>
          <template #editor="{ data, field }">
            <!-- Dynamic editor based on field type -->
            <div v-if="isImageField(String(field))" class="image-editor">
              <div v-if="data[field]" class="current-image mb-2">
                <img 
                  :src="getImagePath(data[field])" 
                  class="w-16 h-16 object-cover rounded border"
                  @error="(e) => (e.target as HTMLImageElement).src = 'https://placehold.co/64x64?text=Invalid'"
                />
              </div>
              <FileUpload
                mode="basic"
                name="file"
                accept="image/*"
                :maxFileSize="5000000"
                customUpload
                @uploader="(event) => handleImageUpload(event, data, String(field))"
                :auto="true"
                :chooseLabel="data[field] ? 'Change' : 'Upload'"
                class="p-button-sm"
                size="small"
              />
            </div>
            <InputText 
              v-else
              v-model="data[field]" 
              class="w-full" 
              @update:modelValue="(value) => onCellEdit(data, String(field), value)"
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
            <p class="text-gray-500 text-lg mb-2">
              {{ isSearchActive ? 'No matching results found' : 'No entries found' }}
            </p>
            <p class="text-gray-400 text-sm">
              {{ isSearchActive ? 'Try adjusting your search criteria' : 'Create one using the form above' }}
            </p>
            <Button
              v-if="isSearchActive"
              label="Clear Search"
              icon="pi pi-times"
              @click="clearAll"
              text
              class="mt-3"
            />
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

  <!-- Image Preview Dialog -->
  <Dialog 
    v-model:visible="showImagePreview" 
    modal 
    header="Image Preview"
    :style="{ width: '50rem' }"
    :breakpoints="{ '1199px': '75vw', '575px': '90vw' }"
  >
    <div class="flex justify-center">
      <img 
        :src="previewImageUrl" 
        class="max-w-full max-h-96 object-contain rounded"
        @error="(e) => (e.target as HTMLImageElement).src = 'https://placehold.co/400x300?text=Image+Not+Found'"
      />
    </div>
    
    <template #footer>
      <div class="flex justify-end gap-2">
        <Button 
          label="Close" 
          icon="pi pi-times" 
          @click="showImagePreview = false" 
          text 
        />
        <a 
          :href="previewImageUrl" 
          target="_blank" 
          class="p-button p-button-outlined no-underline flex items-center gap-2"
        >
          <i class="pi pi-external-link"></i>
          Open in New Tab
        </a>
      </div>
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import { ref, computed, nextTick, toRef } from 'vue'
import Card from 'primevue/card'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import InputText from 'primevue/inputtext'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import Badge from 'primevue/badge'
import FileUpload from 'primevue/fileupload'
import SearchBar from '@/components/common/SearchBar.vue'
import { useAutoCalculation } from '@/composables/useAutoCalculation'
import { useTableSearch } from '@/composables/useTableSearch'
import { useDebugLogger } from '@/composables/useDebugLogger'
import { useToast } from 'primevue/usetoast'
import { productDefinitionServiceFactory } from '@/services/productDefinition'

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

const toast = useToast()
const logger = useDebugLogger('EditableTable')

// Helper function to get a service (defaults to profile for image upload)
const getService = () => {
  return productDefinitionServiceFactory.getService('profile')
}

const editingRows = ref([])
const selectedRows = ref<any[]>([])
const selectAll = ref(false)
const highlightedCells = ref<Set<string>>(new Set())
const showBulkDeleteDialog = ref(false)
const showSingleDeleteDialog = ref(false)
const showImagePreview = ref(false)
const previewImageUrl = ref('')
const itemToDelete = ref<any>(null)
const bulkDeleteLoading = ref(false)

// Helper function to safely get field values
function getFieldValue(data: any, field: string | number): any {
  const fieldKey = String(field)
  return data[fieldKey]
}

// Setup search functionality
const {
  searchQuery,
  columnFilters,
  showAdvancedSearch,
  filteredData,
  searchStats,
  isSearchActive,
  clearSearch,
  clearAll,
  highlightSearchTerm,
  exportSearchResults
} = useTableSearch(toRef(props, 'data'), toRef(props, 'headers'))

// Setup auto-calculation
const schemaRef = computed(() => props.schema)
const dummyFormData = ref<Record<string, any>>({})
const { autoCalculateFields, clearCalculatedFields } = 
  useAutoCalculation(schemaRef, dummyFormData)

function onRowEditSave(event: any) {
  emit('row-save', event)
}

function onSelectAllChange(event: any) {
  selectAll.value = event.checked
  if (event.checked) {
    selectedRows.value = [...filteredData.value]
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
  } else if (selectedRows.value.length === filteredData.value.length) {
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

function getHighlightedCellValue(value: any, field: string): string {
  const formattedValue = formatCellValue(value, field)
  return highlightSearchTerm(formattedValue, field)
}

// Export search results with toast notification
function handleExportResults() {
  try {
    exportSearchResults(`${props.title || 'table'}_search_results`)
    toast.add({
      severity: 'success',
      summary: 'Export Successful',
      detail: `Exported ${searchStats.value.filteredRecords} records`,
      life: 3000
    })
  } catch (error: any) {
    toast.add({
      severity: 'error',
      summary: 'Export Failed',
      detail: error.message,
      life: 5000
    })
  }
}

// Image handling functions
function isImageField(field: string): boolean {
  return field.toLowerCase().includes('image') || 
         field.toLowerCase().includes('picture') || 
         field.toLowerCase().includes('photo') ||
         field.toLowerCase().includes('pic')
}

function getImagePath(path: string): string {
  if (!path) return ''
  if (path.startsWith('http') || path.startsWith('data:')) return path
  
  const baseUrl = import.meta.env.VITE_API_BASE_URL || ''
  return `${baseUrl.replace(/\/$/, '')}/${path.replace(/^\//, '')}`
}

async function handleImageUpload(event: any, rowData: any, field: string) {
  const file = event.files[0]
  if (!file) return

  try {
    logger.debug('Uploading image for table cell', { 
      rowId: rowData.id, 
      field, 
      fileName: file.name 
    })

    const result = await getService().uploadImage(file)
    
    if (result.success) {
      const imageUrl = result.image_url || result.url || result.filename
      
      // Update the row data
      onCellEdit(rowData, field, imageUrl)
      
      toast.add({
        severity: 'success',
        summary: 'Image Uploaded',
        detail: 'Image uploaded successfully',
        life: 3000
      })
      
      logger.info('Image uploaded successfully', { 
        rowId: rowData.id, 
        field, 
        imageUrl 
      })
    } else {
      throw new Error(result.error || 'Upload failed')
    }
  } catch (error: any) {
    logger.error('Image upload failed', { 
      rowId: rowData.id, 
      field, 
      error: error.message 
    })
    
    toast.add({
      severity: 'error',
      summary: 'Upload Failed',
      detail: error.message || 'Failed to upload image',
      life: 5000
    })
  }
}

function openImagePreview(imageUrl: string) {
  previewImageUrl.value = getImagePath(imageUrl)
  showImagePreview.value = true
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

/* Image cell styling */
.image-cell {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0.25rem;
}

.image-cell img {
  transition: transform 0.2s ease;
}

.image-cell img:hover {
  transform: scale(1.1);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
}

/* Image editor styling */
.image-editor {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  align-items: center;
}

.current-image {
  display: flex;
  justify-content: center;
}

.current-image img {
  border: 2px solid #e2e8f0;
  transition: border-color 0.2s ease;
}

.current-image img:hover {
  border-color: #3b82f6;
}
</style>
