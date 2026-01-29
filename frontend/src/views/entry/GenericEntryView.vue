<template>
  <AppLayout>
    <div class="max-w-[1400px]">
      <!-- Manufacturing Type Selector -->
      <Card class="mb-4">
        <template #title>Select {{ pageTitle }} Type</template>
        <template #content>
          <SmartSelect
            v-model="selectedTypeId"
            :options="manufacturingStore.activeTypes"
            optionLabel="name"
            optionValue="id"
            placeholder="Select a type"
            class="w-full md:w-1/2"
            @change="onTypeChange"
            @auto-selected="onTypeChange"
            :loading="manufacturingStore.isLoading"
          />
        </template>
      </Card>

      <div v-if="selectedTypeId">
        <!-- Reusable Dynamic Form -->
        <DynamicForm
          v-model="formData"
          :schema="manufacturingStore.schema"
          :loading="manufacturingStore.isLoading"
          :saving="isSaving"
          @submit="saveConfiguration"
          @clear="clearForm"
        />

        <!-- Reusable Editable Table -->
        <EditableTable
          :data="configStore.configurations"
          :headers="manufacturingStore.headers"
          :loading="configStore.isLoading"
          :has-pending-changes="configStore.hasPendingChanges"
          :schema="manufacturingStore.schema"
          title="Saved Configurations"
          @row-save="onRowEditSave"
          @delete="confirmDelete"
          @bulk-delete="confirmBulkDelete"
          @commit="commitChanges"
          @cell-update="onCellUpdate"
        />
      </div>
    </div>
  </AppLayout>
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import { useToast } from 'primevue/usetoast'
import Card from 'primevue/card'
import SmartSelect from '@/components/common/SmartSelect.vue'
import AppLayout from '@/components/layout/AppLayout.vue'
import DynamicForm from '@/components/entry/DynamicForm.vue'
import EditableTable from '@/components/entry/EditableTable.vue'
import { useManufacturingTypeStore } from '@/stores/manufacturingType'
import { useConfigurationStore } from '@/stores/configuration'
import { useDebugLogger } from '@/composables/useDebugLogger'

const props = defineProps<{
  pageType: string
  pageTitle: string
}>()

const logger = useDebugLogger(`GenericEntryView:${props.pageType}`)
const toast = useToast()

const manufacturingStore = useManufacturingTypeStore()
const configStore = useConfigurationStore()

const selectedTypeId = ref<number | null>(null)
const formData = ref<Record<string, any>>({})
const isSaving = ref(false)

// Reset state when pageType changes (e.g. navigation)
watch(() => props.pageType, () => {
  selectedTypeId.value = null
  formData.value = {}
  configStore.configurations = []
  manufacturingStore.schema = null
})

onMounted(async () => {
  logger.info('Component mounted, loading manufacturing types')
  try {
    await manufacturingStore.loadTypes()
  } catch (error) {
    toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to load manufacturing types', life: 5000 })
  }
})

async function onTypeChange() {
  if (!selectedTypeId.value) return

  logger.info('Type changed', { typeId: selectedTypeId.value, pageType: props.pageType })
  clearForm()
  
  try {
    await Promise.all([
      manufacturingStore.loadAll(selectedTypeId.value, props.pageType),
      configStore.loadPreviews(selectedTypeId.value)
    ])
    logger.info('Schema and previews loaded')
  } catch (error) {
    toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to load data', life: 5000 })
  }
}

async function saveConfiguration(data: any) {
  logger.info('Saving configuration')
  isSaving.value = true

  try {
    await configStore.createConfiguration({
      ...data,
      manufacturing_type_id: selectedTypeId.value
    })
    
    toast.add({ severity: 'success', summary: 'Success', detail: 'Configuration saved', life: 3000 })
    
    // Persist data for rapid entry, only clear name if present to avoid duplicates
    if (formData.value && 'name' in formData.value) {
      formData.value.name = ''
    }
    
    // Reload previews
    if (selectedTypeId.value) {
      await configStore.loadPreviews(selectedTypeId.value)
    }
  } catch (error: any) {
    toast.add({ severity: 'error', summary: 'Error', detail: error.message, life: 5000 })
  } finally {
    isSaving.value = false
  }
}

function clearForm() {
  formData.value = {}
  logger.debug('Form cleared')
}

function onRowEditSave(event: any) {
  const { newData, index } = event
  const config = configStore.configurations[index]
  
  if (config) {
    Object.keys(newData).forEach(key => {
      if (newData[key] !== config[key]) {
        configStore.updateCell(newData.id, key, newData[key])
      }
    })
  }
}

function onCellUpdate(data: { rowId: any, field: string, value: any, calculatedFields?: string[] }) {
  const { rowId, field, value, calculatedFields } = data
  
  // Update the main field
  configStore.updateCell(rowId, field, value)
  
  // Update any calculated fields
  if (calculatedFields && calculatedFields.length > 0) {
    const config = configStore.configurations.find(c => c.id === rowId)
    if (config) {
      calculatedFields.forEach(calcField => {
        configStore.updateCell(rowId, calcField, config[calcField])
      })
    }
    
    // Log the auto-calculation for user feedback
    logger.info('Auto-calculated fields', { 
      trigger: field, 
      calculated: calculatedFields,
      rowId 
    })
  }
}

async function commitChanges() {
  try {
    const result = await configStore.commitPendingChanges()
    if (result.success) {
      toast.add({ severity: 'success', summary: 'Success', detail: 'All changes saved', life: 3000 })
    } else {
      toast.add({ severity: 'warn', summary: 'Partial Success', detail: `${result.successCount} saved, ${result.errorCount} failed`, life: 5000 })
    }
  } catch (error) {
    toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to save changes', life: 5000 })
  }
}

function confirmBulkDelete(selectedRows: any[]) {
  const count = selectedRows.length
  const configIds = selectedRows.map(row => row.id)
  
  // Handle the bulk delete directly since the table component shows the confirmation
  handleBulkDelete(configIds, count)
}

async function handleBulkDelete(configIds: number[], count: number) {
  try {
    const result = await configStore.bulkDeleteConfigurations(configIds)
    
    if (result.success) {
      toast.add({ 
        severity: 'success', 
        summary: 'Bulk Delete Completed', 
        detail: `Successfully deleted ${result.deleted_count} configuration${result.deleted_count > 1 ? 's' : ''}`, 
        life: 4000 
      })
      
      // Reload configurations to refresh the table
      if (selectedTypeId.value) {
        await configStore.loadPreviews(selectedTypeId.value)
      }
    } else {
      toast.add({ 
        severity: 'warn', 
        summary: 'Partial Success', 
        detail: `Deleted ${result.deleted_count}, failed ${result.error_count}`, 
        life: 5000 
      })
    }
  } catch (error: any) {
    toast.add({ 
      severity: 'error', 
      summary: 'Bulk Delete Failed', 
      detail: error.message || 'Failed to delete configurations', 
      life: 5000 
    })
  }
}

function confirmDelete(data: any) {
  // Handle single delete directly since the table component shows the confirmation
  handleSingleDelete(data)
}

async function handleSingleDelete(data: any) {
  try {
    await configStore.deleteConfiguration(data.id)
    toast.add({ 
      severity: 'success', 
      summary: 'Configuration Deleted', 
      detail: `"${data.name || `Configuration #${data.id}`}" has been deleted`, 
      life: 3000 
    })
  } catch (error: any) {
    toast.add({ 
      severity: 'error', 
      summary: 'Delete Failed', 
      detail: error.message || 'Failed to delete configuration', 
      life: 5000 
    })
  }
}
</script>


