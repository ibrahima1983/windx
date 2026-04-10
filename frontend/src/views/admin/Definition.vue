<template>
  <AppLayout>
    <div class="definition-page bg-slate-50 min-h-screen">
      <ConfirmDialog></ConfirmDialog>
      
      <!-- Header -->
      <div class="header-container bg-white border-b border-slate-200 sticky top-0 z-10">
        <div class="header-content px-8 py-6">
          <div class="header-flex flex items-center justify-between">
            <div class="header-left flex items-center gap-4">
              <Button 
                icon="pi pi-arrow-left" 
                text 
                rounded 
                size="large"
                @click="goBack"
                class="text-slate-600 hover:text-slate-800"
              />
              <div>
                <h1 class="text-3xl font-bold text-slate-900">{{ getPageTitle() }}</h1>
                <p class="text-base text-slate-600 mt-2">Manage {{ entityType }} definitions</p>
              </div>
            </div>
            <div class="header-right flex items-center gap-4">
              <Button 
                v-if="selectedDefinition && !isEditMode"
                label="Edit" 
                icon="pi pi-pencil"
                size="large"
                @click="enableEditMode"
              />
              <Button 
                v-if="isEditMode"
                label="Cancel" 
                severity="secondary" 
                outlined
                size="large"
                @click="cancelEdit"
              />
              <Button 
                v-if="isEditMode"
                label="Save Changes" 
                icon="pi pi-save" 
                size="large"
                @click="saveChanges" 
                :loading="isSaving"
                :disabled="!hasChanges"
              />
            </div>
          </div>
        </div>
      </div>

      <!-- Content -->
      <div class="content-container px-8 py-8 mx-auto w-full max-w-full">
        <!-- Definition Table Selector (Replaces Dropdown) -->
        <div class="selector-card bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden mb-8">
          <div class="selector-header px-8 py-6 border-b border-slate-200 bg-slate-50 flex justify-between items-center">
            <h2 class="text-2xl font-bold text-slate-900 flex items-center gap-3">
              <i :class="getEntityIcon()"></i>
              All {{ getEntityDisplayName() }} Configurations
            </h2>
            <Toolbar class="bg-transparent border-0 p-0 m-0">
                <template #start>
                    <Button 
                      label="Bulk Delete" 
                      icon="pi pi-trash" 
                      severity="danger" 
                      @click="confirmBulkDelete" 
                      :disabled="!selectedDefinitions || !selectedDefinitions.length" 
                      class="mr-2"
                    />
                </template>
            </Toolbar>
          </div>
          <div class="selector-content p-0">
            <DataTable 
              :value="definitionOptions" 
              v-model:selection="selectedDefinitions" 
              dataKey="id"
              :paginator="true" 
              :rows="10" 
              :loading="isLoadingDefinitions"
              responsiveLayout="scroll"
              selectionMode="multiple"
              class="w-full"
              stripedRows
              hoverableRows
              :rowHover="true"
              @row-click="onRowClick"
            >
              <Column selectionMode="multiple" headerStyle="width: 3rem"></Column>
              
              <!-- Image Column -->
              <Column v-if="selectedEntityDef?.hasImage" header="Image" style="width: 6rem">
                <template #body="{ data }">
                  <div class="relative group cursor-pointer overflow-hidden rounded-md border border-slate-200 transition-all hover:border-blue-400" @click.stop>
                    <Image v-if="data.image_url" :src="getImagePath(data.image_url)" alt="Image" width="50" preview class="w-full h-full object-cover" />
                    <div v-else class="w-12 h-12 bg-slate-50 flex items-center justify-center text-slate-300">
                      <i class="pi pi-image text-xl"></i>
                    </div>
                    <div class="absolute inset-0 bg-blue-500/0 group-hover:bg-blue-500/10 flex items-center justify-center transition-colors pointer-events-none">
                       <i class="pi pi-search-plus text-white opacity-0 group-hover:opacity-100 transition-opacity"></i>
                    </div>
                  </div>
                </template>
              </Column>
              
              <Column field="name" header="Name" sortable></Column>
              
              <!-- Dynamic columns based on entity schema -->
              <Column 
                v-for="col in entityMetadataFields" 
                :key="col.name" 
                :field="'metadata_.' + col.name" 
                :header="col.label" 
                sortable
              >
                <template #body="{ data }">
                  {{ data.metadata_ ? data.metadata_[col.name] : '' }}
                </template>
              </Column>
              
              <Column field="price_impact_value" header="Base Price" sortable>
                <template #body="{ data }">
                  {{ data.price_impact_value || '0.00' }}
                </template>
              </Column>
              
              <Column field="description" header="Description" sortable style="max-width: 200px" class="truncate"></Column>

              <!-- Actions column -->
              <Column header="Actions" :exportable="false" style="min-width: 8rem" alignFrozen="right" :frozen="true">
                <template #body="slotProps">
                    <Button icon="pi pi-pencil" outlined rounded class="mr-2" @click.stop="editDefinition(slotProps.data)" />
                    <Button icon="pi pi-trash" outlined rounded severity="danger" @click.stop="confirmDeleteDefinition(slotProps.data)" />
                </template>
              </Column>
              
              <template #empty>
                  <div class="text-center p-4">No definitions found for {{ getEntityDisplayName() }}.</div>
              </template>
            </DataTable>
          </div>
        </div>

        <!-- Definition Details Editor -->
        <div v-if="selectedDefinition" class="definition-details">
          <!-- Loading State -->
          <div v-if="isLoadingDetails" class="loading-card bg-white rounded-xl p-8 shadow-sm">
            <div class="space-y-6">
              <Skeleton height="2.5rem" width="16rem" />
              <Skeleton height="4rem" />
              <Skeleton height="4rem" />
              <Skeleton height="4rem" />
            </div>
          </div>

          <!-- Definition Form -->
          <div v-else id="editor-section" class="definition-form bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
            <div class="form-header px-8 py-6 border-b border-slate-200" :class="getEntityHeaderClass()">
              <h3 class="text-2xl font-bold text-slate-900 flex items-center gap-3">
                <i :class="getEntityIcon()"></i>
                Editing: {{ selectedDefinition.name }}
                <span v-if="!isEditMode" class="text-sm font-normal text-slate-600 ml-2">(Read-only)</span>
                <span v-else class="text-sm font-normal text-green-600 ml-2">(Editing)</span>
              </h3>
            </div>
            <div class="form-content p-8">
              <DynamicEntityFields 
                :entity="selectedDefinition"
                :entity-type="entityType"
                :definition="selectedEntityDef"
                :read-only="!isEditMode"
                v-model="formData"
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  </AppLayout>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useToast } from 'primevue/usetoast'
import { useConfirm } from 'primevue/useconfirm'
import { productDefinitionServiceFactory } from '@/services/productDefinition'
import { parseApiError } from '@/utils/errorHandler'
import { useDebugLogger } from '@/composables/useDebugLogger'
import { fetchAndBuildSchemas, type DefinitionSchema, type EntityTypeDefinition } from '@/config/definitionSchemas'

// Components
import AppLayout from '@/components/layout/AppLayout.vue'
import DynamicEntityFields from '@/components/common/DynamicEntityFields.vue'
import Button from 'primevue/button'
import Skeleton from 'primevue/skeleton'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Toolbar from 'primevue/toolbar'
import Image from 'primevue/image'
import ConfirmDialog from 'primevue/confirmdialog'

const route = useRoute()
const router = useRouter()
const toast = useToast()
const confirm = useConfirm()
const logger = useDebugLogger('Definition')

// Props from route
const entityType = computed(() => route.params.entityType as string)

// State
const isLoadingDefinitions = ref(true)
const isLoadingSchemas = ref(true)
const isLoadingDetails = ref(false)
const isSaving = ref(false)
const isEditMode = ref(false)

function getImagePath(path: string | null | undefined): string {
  if (!path) return ''
  if (path.startsWith('http') || path.startsWith('data:')) return path
  const baseUrl = import.meta.env.VITE_API_BASE_URL || ''
  return `${baseUrl.replace(/\/$/, '')}/${path.replace(/^\//, '')}`
}

const definitionOptions = ref<any[]>([])
const selectedDefinitions = ref<any[]>([])
const selectedDefinition = ref<any>(null)
const formData = ref<Record<string, any>>({})
const originalData = ref<Record<string, any>>({})

// Dynamic Schemas
const schemas = ref<Record<string, DefinitionSchema>>({})

const selectedEntityDef = computed<EntityTypeDefinition | undefined>(() => {
  for (const scope in schemas.value) {
    const found = schemas.value[scope]?.entityTypes?.find(t => t.value === entityType.value)
    if (found) return found
  }
  return undefined
})

const loadedScope = computed<string>(() => {
  for (const scope in schemas.value) {
    if (schemas.value[scope]?.entityTypes?.some(t => t.value === entityType.value)) {
      return scope
    }
  }
  return 'profile' // fallback
})

const entityMetadataFields = computed(() => {
  const def = selectedEntityDef.value
  return def ? def.fields : []
})

// Helper function to get service
const getService = (): any => {
  return productDefinitionServiceFactory.getService(loadedScope.value)
}

// Computed
const hasChanges = computed(() => {
  return JSON.stringify(formData.value) !== JSON.stringify(originalData.value)
})

// Methods
async function loadSchemas() {
  isLoadingSchemas.value = true
  try {
    schemas.value = await fetchAndBuildSchemas()
  } catch (err) {
    logger.error('Failed to load schemas', { error: err })
  } finally {
    isLoadingSchemas.value = false
  }
}

async function loadDefinitions() {
  isLoadingDefinitions.value = true
  logger.info('Loading definitions', { entityType: entityType.value })
  
  try {
    const service = getService()
    const response = await service.getEntities(entityType.value)
    
    if (response.success && response.entities) {
      definitionOptions.value = response.entities.map((entity: any) => ({
        id: entity.id,
        name: entity.name,
        description: entity.description,
        ...entity
      }))
      
      logger.info('Definitions loaded successfully', { 
        entityType: entityType.value, 
        count: definitionOptions.value.length 
      })
    } else {
      throw new Error('Failed to load definitions')
    }
  } catch (error) {
    const apiError = parseApiError(error)
    logger.error('Failed to load definitions', { entityType: entityType.value, error: apiError })
    toast.add({
      severity: 'error',
      summary: 'Load Error',
      detail: `Failed to load ${entityType.value} definitions: ${apiError.message}`,
      life: 5000
    })
  } finally {
    isLoadingDefinitions.value = false
  }
}

// Edit action when a table row is clicked
function onRowClick(event: any) {
  editDefinition(event.data)
}

function editDefinition(definition: any) {
  selectedDefinition.value = definition
  initializeFormData(definition)
  
  // Reset purely to view mode initially, or allow editing immediately if you prefer
  isEditMode.value = true
  
  // Scroll to editor
  setTimeout(() => {
    document.getElementById('editor-section')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }, 100)
}

// Bulk delete functionality matching user request
function confirmBulkDelete() {
  confirm.require({
    message: `Are you sure you want to delete the selected ${selectedDefinitions.value.length} items?`,
    header: 'Confirm Bulk Deletion',
    icon: 'pi pi-exclamation-triangle',
    acceptClass: 'p-button-danger',
    accept: () => {
      executeBulkDelete()
    }
  })
}

async function executeBulkDelete() {
  const service = getService()
  const allResults = []
  let errorCount = 0

  for (const def of selectedDefinitions.value) {
    try {
      const res = await service.deleteEntity(def.id)
      if (res.success) allResults.push(def.id)
      else errorCount++
    } catch (e) {
      errorCount++
    }
  }

  if (allResults.length > 0) {
    const deletedIds = new Set(allResults)
    definitionOptions.value = definitionOptions.value.filter(d => !deletedIds.has(d.id))
    
    // Clear editor if currently edited item was in the bulk delete
    if (selectedDefinition.value && deletedIds.has(selectedDefinition.value.id)) {
      cancelEdit()
      selectedDefinition.value = null
    }
    
    selectedDefinitions.value = []
    toast.add({ severity: 'success', summary: 'Bulk Delete', detail: `Successfully deleted ${allResults.length} items`, life: 3000 })
  }
  
  if (errorCount > 0) {
    toast.add({ severity: 'warn', summary: 'Partial Success', detail: `${allResults.length} deleted, ${errorCount} failed`, life: 5000 })
  }
}

function confirmDeleteDefinition(definition: any) {
    confirm.require({
        message: `Are you sure you want to delete ${definition.name}?`,
        header: 'Confirm',
        icon: 'pi pi-exclamation-triangle',
        acceptClass: 'p-button-danger',
        accept: async () => {
            try {
                const service = getService()
                const response = await service.deleteEntity(definition.id)
                if (response.success) {
                    definitionOptions.value = definitionOptions.value.filter(d => d.id !== definition.id)
                    selectedDefinitions.value = selectedDefinitions.value.filter(d => d.id !== definition.id)
                    
                    // Clear editor if deleted item was open
                    if (selectedDefinition.value?.id === definition.id) {
                        cancelEdit()
                        selectedDefinition.value = null
                    }
                    
                    toast.add({ severity: 'success', summary: 'Deleted', detail: 'Definition removed', life: 3000 })
                } else {
                    toast.add({ severity: 'error', summary: 'Error', detail: response.message, life: 3000 })
                }
            } catch(e) {
                toast.add({ severity: 'error', summary: 'Error', detail: parseApiError(e).message, life: 3000 })
            }
        }
    })
}

function initializeFormData(definition: any) {
  const data: Record<string, any> = {}
  
  // Core fields
  data[`${entityType.value}_name`] = definition.name || ''
  data[`${entityType.value}_description`] = definition.description || ''
  data[`${entityType.value}_image_url`] = definition.image_url || ''
  data[`${entityType.value}_price_impact_value`] = parseFloat(definition.price_impact_value || '0')
  
  // Validation rules (stored in metadata but often mapped specifically)
  if (definition.validation_rules) {
    Object.entries(definition.validation_rules).forEach(([key, value]) => {
      data[`${entityType.value}_validation_${key}`] = value
    })
  }
  
  // Metadata Properties
  if (definition.metadata_) {
    Object.entries(definition.metadata_).forEach(([key, value]) => {
      data[`${entityType.value}_metadata_${key}`] = value
    })
  }
  
  formData.value = data
  originalData.value = { ...data }
}

function enableEditMode() {
  isEditMode.value = true
}

function cancelEdit() {
  isEditMode.value = false
  formData.value = { ...originalData.value }
}

async function saveChanges() {
  if (!selectedDefinition.value) return
  
  isSaving.value = true
  
  try {
    const changes = extractEntityChanges()
    if (!hasActualChanges(changes)) {
      toast.add({ severity: 'info', summary: 'No Changes', detail: 'No changes detected to save', life: 3000 })
      return
    }
    
    const updateData = prepareUpdatePayload(changes)
    const service = getService()
    const response = await service.updateEntity(selectedDefinition.value.id, updateData)
    
    if (!response.success) {
      throw new Error(response.message || 'Update failed')
    }
    
    // Update local data
    const idx = definitionOptions.value.findIndex(d => d.id === selectedDefinition.value.id)
    if (idx !== -1) {
      // Merge changes locally since backend only returns message/success
      const updatedItem = { 
        ...definitionOptions.value[idx],
        ...changes
      }
      
      if (changes.metadata_) {
        updatedItem.metadata_ = { ...(definitionOptions.value[idx].metadata_ || {}), ...changes.metadata_ }
      }
      if (changes.validation_rules) {
        updatedItem.validation_rules = { ...(definitionOptions.value[idx].validation_rules || {}), ...changes.validation_rules }
      }
      
      // Replace object for reactivity
      definitionOptions.value[idx] = updatedItem
      selectedDefinition.value = updatedItem
    }
    
    originalData.value = { ...formData.value }
    isEditMode.value = false
    
    toast.add({ severity: 'success', summary: 'Success', detail: `${getEntityDisplayName()} updated successfully`, life: 3000 })
  } catch (error) {
    toast.add({ severity: 'error', summary: 'Save Error', detail: parseApiError(error).message, life: 5000 })
  } finally {
    isSaving.value = false
  }
}

function extractEntityChanges(): any {
  const changes: any = { id: selectedDefinition.value.id }
  
  const nameField = `${entityType.value}_name`
  const descField = `${entityType.value}_description`
  const imageField = `${entityType.value}_image_url`
  const priceField = `${entityType.value}_price_impact_value`
  
  if (formData.value[nameField] !== selectedDefinition.value.name) changes.name = formData.value[nameField]
  if (formData.value[descField] !== selectedDefinition.value.description) changes.description = formData.value[descField]
  if (formData.value[imageField] !== selectedDefinition.value.image_url) changes.image_url = formData.value[imageField]
  
  const currentPrice = formData.value[priceField]
  const originalPrice = parseFloat(selectedDefinition.value.price_impact_value || '0')
  if (Math.abs(currentPrice - originalPrice) > 0.001) changes.price_impact_value = currentPrice
  
  const validationRules: any = {}
  let hasValidationChanges = false
  if (selectedDefinition.value.validation_rules) {
    Object.keys(selectedDefinition.value.validation_rules).forEach(key => {
      const fieldName = `${entityType.value}_validation_${key}`
      if (formData.value[fieldName] !== selectedDefinition.value.validation_rules[key]) {
        validationRules[key] = formData.value[fieldName]
        hasValidationChanges = true
      }
    })
  }
  if (hasValidationChanges) changes.validation_rules = validationRules
  
  const metadata: any = {}
  let hasMetadataChanges = false
  
  // Iterate over fields defined in schema to pick up all potential changes (including new ones)
  if (selectedEntityDef.value?.fields) {
    selectedEntityDef.value.fields.forEach(field => {
      const fieldName = `${entityType.value}_metadata_${field.name}`
      const currentVal = formData.value[fieldName]
      const originalVal = selectedDefinition.value.metadata_ ? selectedDefinition.value.metadata_[field.name] : undefined
      
      if (currentVal !== originalVal) {
        metadata[field.name] = currentVal
        hasMetadataChanges = true
      }
    })
  }
  
  if (hasMetadataChanges) changes.metadata_ = metadata
  
  return changes
}

function hasActualChanges(changes: any): boolean {
  return Object.keys(changes).filter(k => k !== 'id').length > 0
}

function prepareUpdatePayload(changes: any): any {
  const updateData: any = {
    name: changes.name,
    description: changes.description,
    image_url: changes.image_url,
    price_from: changes.price_impact_value,
    metadata: {
      ...changes.validation_rules && { validation_rules: changes.validation_rules },
      ...changes.metadata_ && { ...changes.metadata_ }
    }
  }
  Object.keys(updateData).forEach(k => { if (updateData[k] === undefined) delete updateData[k] })
  if (Object.keys(updateData.metadata).length === 0) delete updateData.metadata
  return updateData
}

function getPageTitle(): string {
  return `${getEntityDisplayName()} Definitions`
}

function getEntityDisplayName(): string {
  const displayNames: Record<string, string> = { company: 'Company', material: 'Material', opening_system: 'Opening System', system_series: 'System Series', color: 'Color' }
  return displayNames[entityType.value] || entityType.value.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
}

function getEntityIcon(): string {
  const icons: Record<string, string> = { company: 'pi pi-building text-blue-600', material: 'pi pi-box text-green-600', opening_system: 'pi pi-cog text-orange-600', system_series: 'pi pi-sitemap text-purple-600', color: 'pi pi-palette text-pink-600' }
  return icons[entityType.value] || 'pi pi-circle text-gray-600'
}

function getEntityHeaderClass(): string {
  const classes: Record<string, string> = { company: 'bg-blue-50', material: 'bg-green-50', opening_system: 'bg-orange-50', system_series: 'bg-purple-50', color: 'bg-pink-50' }
  return classes[entityType.value] || 'bg-gray-50'
}

function goBack() {
  router.go(-1)
}

watch(() => entityType.value, async () => {
  selectedDefinitions.value = []
  selectedDefinition.value = null
  isEditMode.value = false
  if (Object.keys(schemas.value).length === 0) {
    await loadSchemas()
  }
  await loadDefinitions()
}, { immediate: true })

onMounted(() => {
  logger.info('Definition page mounted', { entityType: entityType.value })
})
</script>

<style scoped>
.header-container { position: sticky; top: 0; z-index: 10; }
.header-content { max-width: 100%; margin-left: auto; margin-right: auto; }
.header-flex { display: flex; align-items: center; justify-content: space-between; }
.header-left { display: flex; align-items: center; gap: 1rem; }
.header-right { display: flex; align-items: center; gap: 1rem; }
.content-container { width: 100%; padding-left: 2rem; padding-right: 2rem; }
.selector-card, .definition-form { overflow: hidden; }
.selector-header, .form-header { padding: 1.5rem 2rem; }
.selector-content { padding: 0; }
.form-content { padding: 2rem; }
</style>