<template>
  <AppLayout>
    <div class="definition-page bg-slate-50 min-h-screen">
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
      <div class="content-container px-8 py-8 max-w-6xl mx-auto">
        <!-- Definition Selector -->
        <div class="selector-card bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden mb-8">
          <div class="selector-header px-8 py-6 border-b border-slate-200 bg-slate-50">
            <h2 class="text-2xl font-bold text-slate-900 flex items-center gap-3">
              <i :class="getEntityIcon()"></i>
              Select {{ getEntityDisplayName() }}
            </h2>
          </div>
          <div class="selector-content p-8">
            <div class="selector-field">
              <label class="block text-sm font-semibold text-slate-700 mb-3">
                Choose a {{ entityType }} definition to view or edit:
              </label>
              <DefinitionSelect
                v-model="selectedDefinitionId"
                :options="definitionOptions"
                :loading="isLoadingDefinitions"
                :placeholder="`Select ${getEntityDisplayName()}...`"
                :entity-type="entityType"
                option-label="name"
                option-value="id"
                class="w-full"
                @change="onDefinitionSelect"
              />
            </div>
          </div>
        </div>

        <!-- Definition Details -->
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
          <div v-else class="definition-form bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
            <div class="form-header px-8 py-6 border-b border-slate-200" :class="getEntityHeaderClass()">
              <h3 class="text-2xl font-bold text-slate-900 flex items-center gap-3">
                <i :class="getEntityIcon()"></i>
                {{ selectedDefinition.name }}
                <span v-if="!isEditMode" class="text-sm font-normal text-slate-600 ml-2">(Read-only)</span>
                <span v-else class="text-sm font-normal text-green-600 ml-2">(Editing)</span>
              </h3>
            </div>
            <div class="form-content p-8">
              <DynamicEntityFields 
                :entity="selectedDefinition"
                :entity-type="entityType"
                :read-only="!isEditMode"
                v-model="formData"
              />
            </div>
          </div>
        </div>

        <!-- Empty State -->
        <div v-else-if="!isLoadingDefinitions" class="empty-state text-center py-16">
          <div class="w-24 h-24 bg-slate-100 rounded-full flex items-center justify-center mx-auto mb-6">
            <i :class="getEntityIcon() + ' text-4xl text-slate-400'"></i>
          </div>
          <h3 class="text-xl font-semibold text-slate-900 mb-3">No Definition Selected</h3>
          <p class="text-slate-600 max-w-md mx-auto">
            Choose a {{ entityType }} definition from the dropdown above to view and edit its details.
          </p>
        </div>
      </div>
    </div>
  </AppLayout>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useToast } from 'primevue/usetoast'
import { productDefinitionService } from '@/services/productDefinitionService'
import { parseApiError } from '@/utils/errorHandler'
import { useDebugLogger } from '@/composables/useDebugLogger'

// Components
import AppLayout from '@/components/layout/AppLayout.vue'
import DynamicEntityFields from '@/components/common/DynamicEntityFields.vue'
import DefinitionSelect from '@/components/common/DefinitionSelect.vue'
import Button from 'primevue/button'
import Skeleton from 'primevue/skeleton'

const route = useRoute()
const router = useRouter()
const toast = useToast()
const logger = useDebugLogger('Definition')

// Props from route
const entityType = computed(() => route.params.entityType as string)

// State
const isLoadingDefinitions = ref(true)
const isLoadingDetails = ref(false)
const isSaving = ref(false)
const isEditMode = ref(false)
const selectedDefinitionId = ref<number | null>(null)
const selectedDefinition = ref<any>(null)
const definitionOptions = ref<any[]>([])
const formData = ref<Record<string, any>>({})
const originalData = ref<Record<string, any>>({})

// Computed
const hasChanges = computed(() => {
  return JSON.stringify(formData.value) !== JSON.stringify(originalData.value)
})

// Methods
async function loadDefinitions() {
  isLoadingDefinitions.value = true
  logger.info('Loading definitions', { entityType: entityType.value })
  
  try {
    const response = await productDefinitionService.getEntities(entityType.value)
    
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

async function onDefinitionSelect() {
  if (!selectedDefinitionId.value) {
    selectedDefinition.value = null
    return
  }
  
  isLoadingDetails.value = true
  logger.info('Loading definition details', { 
    entityType: entityType.value, 
    definitionId: selectedDefinitionId.value 
  })
  
  try {
    // Find the selected definition from the options
    const definition = definitionOptions.value.find(opt => opt.id === selectedDefinitionId.value)
    
    if (!definition) {
      throw new Error('Definition not found')
    }
    
    selectedDefinition.value = definition
    initializeFormData(definition)
    
    // Reset edit mode when selecting a new definition
    isEditMode.value = false
    
    logger.info('Definition details loaded', { 
      entityType: entityType.value, 
      definitionId: selectedDefinitionId.value,
      definitionName: definition.name
    })
    
  } catch (error) {
    const apiError = parseApiError(error)
    logger.error('Failed to load definition details', { 
      entityType: entityType.value, 
      definitionId: selectedDefinitionId.value, 
      error: apiError 
    })
    toast.add({
      severity: 'error',
      summary: 'Load Error',
      detail: `Failed to load definition details: ${apiError.message}`,
      life: 5000
    })
  } finally {
    isLoadingDetails.value = false
  }
}

function initializeFormData(definition: any) {
  const data: Record<string, any> = {}
  
  // Core fields
  data[`${entityType.value}_name`] = definition.name || ''
  data[`${entityType.value}_description`] = definition.description || ''
  data[`${entityType.value}_image_url`] = definition.image_url || ''
  data[`${entityType.value}_price_impact_value`] = parseFloat(definition.price_impact_value || '0')
  
  // Validation rules
  if (definition.validation_rules) {
    Object.entries(definition.validation_rules).forEach(([key, value]) => {
      data[`${entityType.value}_validation_${key}`] = value
    })
  }
  
  // Metadata
  if (definition.metadata_) {
    Object.entries(definition.metadata_).forEach(([key, value]) => {
      data[`${entityType.value}_metadata_${key}`] = value
    })
  }
  
  formData.value = data
  originalData.value = { ...data }
  
  logger.debug('Form data initialized', { 
    entityType: entityType.value,
    fieldCount: Object.keys(data).length 
  })
}

function enableEditMode() {
  isEditMode.value = true
  logger.info('Edit mode enabled', { 
    entityType: entityType.value, 
    definitionId: selectedDefinitionId.value 
  })
}

function cancelEdit() {
  isEditMode.value = false
  // Reset form data to original values
  formData.value = { ...originalData.value }
  logger.info('Edit mode cancelled', { 
    entityType: entityType.value, 
    definitionId: selectedDefinitionId.value 
  })
}

async function saveChanges() {
  if (!selectedDefinition.value) return
  
  isSaving.value = true
  logger.info('Saving definition changes', { 
    entityType: entityType.value, 
    definitionId: selectedDefinition.value.id 
  })
  
  try {
    const changes = extractEntityChanges()
    
    if (!hasActualChanges(changes)) {
      toast.add({
        severity: 'info',
        summary: 'No Changes',
        detail: 'No changes detected to save',
        life: 3000
      })
      return
    }
    
    const updateData = prepareUpdatePayload(changes)
    logger.debug('Prepared update data', { 
      entityId: selectedDefinition.value.id, 
      updateData 
    })
    
    const response = await productDefinitionService.updateEntity(selectedDefinition.value.id, updateData)
    
    if (!response.success) {
      throw new Error(response.message || 'Update failed')
    }
    
    // Update the definition in our local state
    Object.assign(selectedDefinition.value, response.entity)
    originalData.value = { ...formData.value }
    isEditMode.value = false
    
    // Update the definition in the options list
    const optionIndex = definitionOptions.value.findIndex(opt => opt.id === selectedDefinition.value.id)
    if (optionIndex !== -1) {
      Object.assign(definitionOptions.value[optionIndex], response.entity)
    }
    
    toast.add({
      severity: 'success',
      summary: 'Success',
      detail: `${getEntityDisplayName()} updated successfully`,
      life: 3000
    })
    
    logger.info('Definition saved successfully', { 
      entityType: entityType.value, 
      definitionId: selectedDefinition.value.id 
    })
    
  } catch (error) {
    const apiError = parseApiError(error)
    logger.error('Failed to save definition', { 
      entityType: entityType.value, 
      definitionId: selectedDefinition.value.id, 
      error: apiError 
    })
    toast.add({
      severity: 'error',
      summary: 'Save Error',
      detail: apiError.message,
      life: 5000
    })
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
  
  if (formData.value[nameField] !== selectedDefinition.value.name) {
    changes.name = formData.value[nameField]
  }
  
  if (formData.value[descField] !== selectedDefinition.value.description) {
    changes.description = formData.value[descField]
  }
  
  if (formData.value[imageField] !== selectedDefinition.value.image_url) {
    changes.image_url = formData.value[imageField]
  }
  
  const currentPrice = formData.value[priceField]
  const originalPrice = parseFloat(selectedDefinition.value.price_impact_value || '0')
  if (Math.abs(currentPrice - originalPrice) > 0.001) {
    changes.price_impact_value = currentPrice
  }
  
  // Extract validation rule changes
  const validationRules: any = {}
  let hasValidationChanges = false
  
  if (selectedDefinition.value.validation_rules) {
    Object.keys(selectedDefinition.value.validation_rules).forEach(key => {
      const fieldName = `${entityType.value}_validation_${key}`
      const newValue = formData.value[fieldName]
      const oldValue = selectedDefinition.value.validation_rules[key]
      
      if (newValue !== oldValue) {
        validationRules[key] = newValue
        hasValidationChanges = true
      }
    })
  }
  
  if (hasValidationChanges) {
    changes.validation_rules = validationRules
  }
  
  // Extract metadata changes
  const metadata: any = {}
  let hasMetadataChanges = false
  
  if (selectedDefinition.value.metadata_) {
    Object.keys(selectedDefinition.value.metadata_).forEach(key => {
      const fieldName = `${entityType.value}_metadata_${key}`
      const newValue = formData.value[fieldName]
      const oldValue = selectedDefinition.value.metadata_[key]
      
      if (newValue !== oldValue) {
        metadata[key] = newValue
        hasMetadataChanges = true
      }
    })
  }
  
  if (hasMetadataChanges) {
    changes.metadata_ = metadata
  }
  
  return changes
}

function hasActualChanges(changes: any): boolean {
  const changeKeys = Object.keys(changes).filter(key => key !== 'id')
  return changeKeys.length > 0
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
  
  // Remove undefined fields
  Object.keys(updateData).forEach(key => {
    if (updateData[key] === undefined) {
      delete updateData[key]
    }
  })
  
  // Only include metadata if it has content
  if (Object.keys(updateData.metadata).length === 0) {
    delete updateData.metadata
  }
  
  return updateData
}

function getPageTitle(): string {
  return `${getEntityDisplayName()} Definitions`
}

function getEntityDisplayName(): string {
  const displayNames: Record<string, string> = {
    company: 'Company',
    material: 'Material',
    opening_system: 'Opening System',
    system_series: 'System Series',
    color: 'Color'
  }
  
  return displayNames[entityType.value] || entityType.value.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
}

function getEntityIcon(): string {
  const icons: Record<string, string> = {
    company: 'pi pi-building text-blue-600',
    material: 'pi pi-box text-green-600',
    opening_system: 'pi pi-cog text-orange-600',
    system_series: 'pi pi-sitemap text-purple-600',
    color: 'pi pi-palette text-pink-600'
  }
  
  return icons[entityType.value] || 'pi pi-circle text-gray-600'
}

function getEntityHeaderClass(): string {
  const classes: Record<string, string> = {
    company: 'bg-blue-50',
    material: 'bg-green-50',
    opening_system: 'bg-orange-50',
    system_series: 'bg-purple-50',
    color: 'bg-pink-50'
  }
  
  return classes[entityType.value] || 'bg-gray-50'
}

function goBack() {
  router.go(-1)
}

// Watch for entity type changes
watch(() => entityType.value, () => {
  selectedDefinitionId.value = null
  selectedDefinition.value = null
  isEditMode.value = false
  loadDefinitions()
}, { immediate: true })

// Lifecycle
onMounted(() => {
  logger.info('Definition page mounted', { entityType: entityType.value })
})
</script>

<style scoped>
.header-container {
  position: sticky;
  top: 0;
  z-index: 10;
}

.header-content {
  max-width: 72rem;
  margin-left: auto;
  margin-right: auto;
}

.header-flex {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.content-container {
  max-width: 72rem;
  margin-left: auto;
  margin-right: auto;
}

.selector-card,
.definition-form {
  overflow: hidden;
}

.selector-header,
.form-header {
  padding: 1.5rem 2rem;
}

.selector-content,
.form-content {
  padding: 2rem;
}

.empty-state {
  padding: 4rem 0;
}
</style>