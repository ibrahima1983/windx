<template>
  <AppLayout>
    <div class="max-w-[1400px]">
      <!-- Manufacturing Type Selector -->
      <Card class="mb-4">
        <template #title>Select {{ pageTitle }} Type</template>
        <template #content>
          <Select
            v-model="selectedTypeId"
            :options="manufacturingStore.activeTypes"
            optionLabel="name"
            optionValue="id"
            placeholder="Select a type"
            class="w-full md:w-1/2"
            @change="onTypeChange"
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
          title="Saved Configurations"
          @row-save="onRowEditSave"
          @delete="confirmDelete"
          @commit="commitChanges"
        />
      </div>
    </div>
  </AppLayout>
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import { useToast } from 'primevue/usetoast'
import { useConfirm } from 'primevue/useconfirm'
import Card from 'primevue/card'
import Select from 'primevue/select'
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
const confirm = useConfirm()

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

function confirmDelete(data: any) {
  confirm.require({
    message: `Delete configuration "${data.name || data.id}"?`,
    header: 'Confirm Delete',
    icon: 'pi pi-exclamation-triangle',
    accept: async () => {
      try {
        await configStore.deleteConfiguration(data.id)
        toast.add({ severity: 'success', summary: 'Deleted', detail: 'Configuration deleted', life: 3000 })
      } catch (error) {
        toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to delete', life: 5000 })
      }
    }
  })
}
</script>


