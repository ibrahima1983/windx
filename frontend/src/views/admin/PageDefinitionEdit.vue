<template>
  <AppLayout>
    <div class="page-wrapper bg-slate-50">
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
                <h1 class="text-3xl font-bold text-slate-900">Edit Configuration</h1>
                <p class="text-base text-slate-600 mt-2">{{ pathData?.display_path || 'Loading...' }}</p>
              </div>
            </div>
            <div class="header-right flex items-center gap-4">
              <Button 
                label="Cancel" 
                severity="secondary" 
                outlined
                size="large"
                @click="goBack" 
              />
              <Button 
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
      <div class="content-container px-8 py-8">
        <!-- Loading State -->
        <div v-if="isLoading" class="loading-container space-y-8">
          <div class="bg-white rounded-xl p-8 shadow-sm">
            <Skeleton height="2.5rem" width="16rem" class="mb-6" />
            <div class="space-y-6">
              <Skeleton height="4rem" />
              <Skeleton height="4rem" />
              <Skeleton height="4rem" />
              <Skeleton height="4rem" />
            </div>
          </div>
        </div>

        <!-- Error State -->
        <div v-else-if="loadError" class="error-container flex items-center justify-center min-h-[400px]">
          <div class="error-content text-center max-w-md">
            <div class="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <i class="pi pi-exclamation-triangle text-red-500 text-2xl"></i>
            </div>
            <h3 class="text-xl font-semibold text-slate-900 mb-3">Failed to Load Configuration</h3>
            <p class="text-slate-600 mb-6">{{ loadError }}</p>
            <div class="error-buttons flex gap-4 justify-center">
              <Button 
                label="Try Again" 
                icon="pi pi-refresh" 
                size="large"
                @click="loadData" 
                :loading="isLoading"
              />
              <Button 
                label="Go Back" 
                severity="secondary" 
                outlined
                size="large"
                @click="goBack" 
              />
            </div>
          </div>
        </div>

        <!-- Edit Form -->
        <div v-else-if="pathData" class="form-container space-y-8">
          <!-- Overview Card -->
          <div class="overview-card bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
            <div class="overview-header px-8 py-6 border-b border-slate-200 bg-slate-50">
              <h2 class="text-2xl font-bold text-slate-900 flex items-center gap-3">
                <i class="pi pi-info-circle text-blue-500"></i>
                Configuration Overview
              </h2>
            </div>
            <div class="overview-content p-8">
              <div class="overview-grid grid grid-cols-1 md:grid-cols-2 gap-8">
                <div class="space-y-3">
                  <label class="block text-sm font-semibold text-slate-700 uppercase tracking-wide">Configuration ID</label>
                  <div class="px-4 py-3 bg-slate-100 rounded-lg text-slate-700 font-mono text-lg">
                    #{{ pathData.id }}
                  </div>
                </div>
                <div class="space-y-3">
                  <label class="block text-sm font-semibold text-slate-700 uppercase tracking-wide">Path</label>
                  <div class="px-4 py-3 bg-slate-100 rounded-lg text-slate-700 text-base">
                    {{ pathData.ltree_path }}
                  </div>
                </div>
                <div class="space-y-3">
                  <label class="block text-sm font-semibold text-slate-700 uppercase tracking-wide">Created</label>
                  <div class="px-4 py-3 bg-slate-100 rounded-lg text-slate-700 text-base">
                    {{ formatDate(pathData.created_at) }}
                  </div>
                </div>
                <div class="space-y-3">
                  <label class="block text-sm font-semibold text-slate-700 uppercase tracking-wide">Total Price</label>
                  <div class="px-4 py-3 bg-green-50 rounded-lg text-green-700 font-bold text-lg">
                    ${{ calculateTotalPrice().toFixed(2) }}
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Dynamic Entity Cards -->
          <div 
            v-for="(entity, entityType) in entityData" 
            :key="entityType"
            class="entity-card bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden"
          >
            <div 
              class="entity-header px-8 py-6 border-b border-slate-200"
              :class="getEntityHeaderClass(String(entityType))"
            >
              <h3 class="text-2xl font-bold text-slate-900 flex items-center gap-3">
                <i :class="getEntityIcon(String(entityType))"></i>
                {{ getEntityTitle(String(entityType)) }}
              </h3>
            </div>
            <div class="entity-content p-8">
              <!-- Render fields dynamically based on entity data -->
              <div class="entity-fields space-y-6">
                <DynamicEntityFields 
                  :entity="entity"
                  :entity-type="String(entityType)"
                  v-model="formData"
                />
              </div>
            </div>
          </div>

          <!-- Summary Card -->
          <div class="summary-card bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
            <div class="summary-header px-8 py-6 border-b border-slate-200 bg-slate-50">
              <h3 class="text-2xl font-bold text-slate-900 flex items-center gap-3">
                <i class="pi pi-calculator text-slate-600"></i>
                Configuration Summary
              </h3>
            </div>
            <div class="summary-content p-8">
              <div class="summary-grid grid grid-cols-1 md:grid-cols-3 gap-8">
                <div class="text-center p-6 bg-green-50 rounded-lg">
                  <div class="text-3xl font-bold text-green-700">${{ calculateTotalPrice().toFixed(2) }}</div>
                  <div class="text-base text-green-600 mt-2">Total Price</div>
                </div>
                <div class="text-center p-6 bg-blue-50 rounded-lg">
                  <div class="text-3xl font-bold text-blue-700">{{ calculateTotalWeight().toFixed(1) }} kg</div>
                  <div class="text-base text-blue-600 mt-2">Total Weight</div>
                  <!-- TODO: Weight calculation is currently using density values directly -->
                  <!-- Future: Calculate actual weight using volume × density formulas -->
                </div>
                <div class="text-center p-6 bg-purple-50 rounded-lg">
                  <div class="text-3xl font-bold text-purple-700">{{ Object.keys(entityData).length }}</div>
                  <div class="text-base text-purple-600 mt-2">Components</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </AppLayout>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useToast } from 'primevue/usetoast'
import { productDefinitionServiceFactory } from '@/services/productDefinition'
import type { ProfileProductDefinitionService } from '@/services/productDefinition'
import { parseApiError } from '@/utils/errorHandler'
import { useDebugLogger } from '@/composables/useDebugLogger'

// Components
import AppLayout from '@/components/layout/AppLayout.vue'
import DynamicEntityFields from '@/components/common/DynamicEntityFields.vue'
import Button from 'primevue/button'
import Skeleton from 'primevue/skeleton'

const route = useRoute()
const router = useRouter()
const toast = useToast()
const logger = useDebugLogger('PageDefinitionEdit')

// State
const isLoading = ref(true)
const isSaving = ref(false)
const loadError = ref<string | null>(null)
const pathData = ref<any>(null)
const entityData = ref<any>({})
const formData = ref<Record<string, any>>({})
const originalData = ref<Record<string, any>>({})

// Helper function to get profile service (this view is profile-specific)
const getProfileService = (): ProfileProductDefinitionService => {
  return productDefinitionServiceFactory.getService('profile') as ProfileProductDefinitionService
}

// Computed
const hasChanges = computed(() => {
  return JSON.stringify(formData.value) !== JSON.stringify(originalData.value)
})

// Methods
async function loadData() {
  isLoading.value = true
  loadError.value = null
  
  try {
    const pathId = route.params.pathId as string
    logger.info('Loading path details', { pathId })
    
    if (!pathId) {
      throw new Error('Path ID is required')
    }
    
    // Load path data and related entities from backend
    const profileService = getProfileService()
    const response = await profileService.getPathDetails(parseInt(pathId))
    
    if (!response.success) {
      throw new Error('Failed to load path details')
    }
    
    pathData.value = response.path
    entityData.value = response.path.entities || {}
    
    logger.debug('Loaded path data', { 
      pathId, 
      entityCount: Object.keys(entityData.value).length,
      entities: Object.keys(entityData.value)
    })
    
    // Initialize form data dynamically from entity data
    initializeFormData()
    
    logger.info('Path data loaded successfully', { pathId })
    
  } catch (error) {
    const apiError = parseApiError(error)
    loadError.value = apiError.message
    logger.error('Failed to load path data', { pathId: route.params.pathId, error: apiError })
  } finally {
    isLoading.value = false
  }
}

function initializeFormData() {
  const data: Record<string, any> = {}
  logger.debug('Initializing form data from entity data')
  
  // Initialize form data dynamically from entity data
  Object.entries(entityData.value).forEach(([entityType, entity]: [string, any]) => {
    if (Array.isArray(entity)) {
      // Handle arrays (like colors)
      logger.debug(`Processing array entity type: ${entityType}`, { count: entity.length })
      entity.forEach((item: any, index: number) => {
        initializeEntityFields(data, `${entityType}_${index}`, item)
      })
    } else {
      // Handle single entities
      logger.debug(`Processing single entity type: ${entityType}`, { entityId: entity.id })
      initializeEntityFields(data, entityType, entity)
    }
  })
  
  formData.value = data
  originalData.value = { ...data }
  
  logger.info('Form data initialized', { 
    fieldCount: Object.keys(data).length,
    entityTypes: Object.keys(entityData.value)
  })
}

function initializeEntityFields(data: Record<string, any>, prefix: string, entity: any) {
  // Core fields
  data[`${prefix}_name`] = entity.name || ''
  data[`${prefix}_description`] = entity.description || ''
  data[`${prefix}_image_url`] = entity.image_url || ''
  data[`${prefix}_price_impact_value`] = parseFloat(entity.price_impact_value || '0')
  
  // Validation rules
  if (entity.validation_rules) {
    Object.entries(entity.validation_rules).forEach(([key, value]) => {
      data[`${prefix}_validation_${key}`] = value
    })
  }
  
  // Metadata
  if (entity.metadata_) {
    Object.entries(entity.metadata_).forEach(([key, value]) => {
      data[`${prefix}_metadata_${key}`] = value
    })
  }
}

function calculateTotalPrice(): number {
  let total = 0
  
  // Calculate total from all entity price impacts
  Object.entries(entityData.value).forEach(([entityType, entity]: [string, any]) => {
    if (Array.isArray(entity)) {
      entity.forEach((_, index: number) => {
        const priceField = `${entityType}_${index}_price_impact_value`
        total += formData.value[priceField] || 0
      })
    } else {
      const priceField = `${entityType}_price_impact_value`
      total += formData.value[priceField] || 0
    }
  })
  
  return total
}

function calculateTotalWeight(): number {
  // TODO: This is a simplified weight calculation using density values
  // In the future, this should be updated to use proper weight formulas
  // that consider dimensions, material properties, and manufacturing specifications
  
  let totalWeight = 0
  
  // Calculate weight from all entity density values
  Object.entries(entityData.value).forEach(([entityType, entity]: [string, any]) => {
    if (Array.isArray(entity)) {
      entity.forEach((item: any, index: number) => {
        const densityWeight = extractDensityWeight(item, `${entityType}_${index}`)
        totalWeight += densityWeight
      })
    } else {
      const densityWeight = extractDensityWeight(entity, entityType)
      totalWeight += densityWeight
    }
  })
  
  return totalWeight
}

function extractDensityWeight(entity: any, prefix: string): number {
  // TODO: This is a temporary implementation that treats density as weight
  // Future implementation should:
  // 1. Calculate volume from dimensions (width × height × depth)
  // 2. Multiply volume by material density to get actual weight
  // 3. Consider manufacturing processes that affect weight
  // 4. Account for hollow sections, reinforcements, etc.
  
  // Check for density in validation rules (common for materials)
  if (entity.validation_rules?.density) {
    const density = parseFloat(entity.validation_rules.density)
    if (!isNaN(density)) {
      logger.debug(`Using density as weight for ${prefix}`, { density })
      return density
    }
  }
  
  // Check for density in form data (user-modified values)
  const densityField = `${prefix}_validation_density`
  if (formData.value[densityField]) {
    const density = parseFloat(formData.value[densityField])
    if (!isNaN(density)) {
      logger.debug(`Using form density as weight for ${prefix}`, { density })
      return density
    }
  }
  
  // Check for other weight-related properties in metadata
  if (entity.metadata_?.weight) {
    const weight = parseFloat(entity.metadata_.weight)
    if (!isNaN(weight)) {
      logger.debug(`Using metadata weight for ${prefix}`, { weight })
      return weight
    }
  }
  
  // Check for weight in validation rules
  if (entity.validation_rules?.weight) {
    const weight = parseFloat(entity.validation_rules.weight)
    if (!isNaN(weight)) {
      logger.debug(`Using validation weight for ${prefix}`, { weight })
      return weight
    }
  }
  
  logger.debug(`No weight/density found for ${prefix}, using 0`)
  return 0
}

function getEntityTitle(entityType: string): string {
  const titles: Record<string, string> = {
    company: 'Company Information',
    material: 'Material Specifications',
    opening_system: 'Opening System',
    system_series: 'System Series',
    colors: 'Color Options'
  }
  
  return titles[entityType] || entityType.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
}

function getEntityIcon(entityType: string): string {
  const icons: Record<string, string> = {
    company: 'pi pi-building text-blue-600',
    material: 'pi pi-box text-green-600',
    opening_system: 'pi pi-cog text-orange-600',
    system_series: 'pi pi-sitemap text-purple-600',
    colors: 'pi pi-palette text-pink-600'
  }
  
  return icons[entityType] || 'pi pi-circle text-gray-600'
}

function getEntityHeaderClass(entityType: string): string {
  const classes: Record<string, string> = {
    company: 'bg-blue-50',
    material: 'bg-green-50',
    opening_system: 'bg-orange-50',
    system_series: 'bg-purple-50',
    colors: 'bg-pink-50'
  }
  
  return classes[entityType] || 'bg-gray-50'
}

function formatDate(dateString: string): string {
  if (!dateString) return ''
  return new Date(dateString).toLocaleDateString()
}

async function saveChanges() {
  isSaving.value = true
  logger.info('Starting save operation')
  
  try {
    // Prepare update data by extracting changes for each entity
    const updates: Array<{ entityId: number, entityType: string, changes: any }> = []
    
    Object.entries(entityData.value).forEach(([entityType, entity]: [string, any]) => {
      if (Array.isArray(entity)) {
        // Handle arrays (like colors)
        entity.forEach((item: any, index: number) => {
          const changes = extractEntityChanges(`${entityType}_${index}`, item)
          if (hasActualChanges(changes)) {
            updates.push({ 
              entityId: item.id, 
              entityType: `${entityType}[${index}]`,
              changes 
            })
          }
        })
      } else {
        // Handle single entities
        const changes = extractEntityChanges(entityType, entity)
        if (hasActualChanges(changes)) {
          updates.push({ 
            entityId: entity.id, 
            entityType,
            changes 
          })
        }
      }
    })
    
    logger.debug('Detected changes', { 
      totalEntities: Object.keys(entityData.value).length,
      changedEntities: updates.length,
      changes: updates.map(u => ({ entityId: u.entityId, entityType: u.entityType, changeKeys: Object.keys(u.changes).filter(k => k !== 'id') }))
    })
    
    // Only proceed if there are actual changes
    if (updates.length === 0) {
      logger.info('No changes detected, skipping save')
      toast.add({
        severity: 'info',
        summary: 'No Changes',
        detail: 'No changes detected to save',
        life: 3000
      })
      return
    }
    
    logger.info(`Saving ${updates.length} changed entities`)
    
    // Send updates to backend for each changed entity
    const savePromises = updates.map(async ({ entityId, entityType, changes }) => {
      try {
        const updateData = prepareUpdatePayload(changes)
        
        logger.debug(`Updating entity ${entityId} (${entityType})`, { updateData })
        
        const profileService = getProfileService()
        const response = await profileService.updateEntity(entityId, updateData)
        
        if (!response.success) {
          throw new Error(`Failed to update entity ${entityId}: ${response.message || 'Unknown error'}`)
        }
        
        logger.debug(`Successfully updated entity ${entityId}`, { response: response.entity })
        return { entityId, entityType, success: true, response }
      } catch (error) {
        const errorMessage = parseApiError(error).message
        logger.error(`Failed to update entity ${entityId} (${entityType})`, { error: errorMessage })
        return { entityId, entityType, success: false, error: errorMessage }
      }
    })
    
    // Wait for all updates to complete
    const results = await Promise.all(savePromises)
    
    // Check results
    const successful = results.filter(r => r.success)
    const failed = results.filter(r => !r.success)
    
    logger.info('Save operation completed', {
      total: results.length,
      successful: successful.length,
      failed: failed.length,
      failedEntities: failed.map(f => ({ entityId: f.entityId, entityType: f.entityType, error: f.error }))
    })
    
    if (failed.length > 0) {
      // Some updates failed
      const failedDetails = failed.map(f => `${f.entityType} (ID: ${f.entityId})`).join(', ')
      toast.add({
        severity: 'warn',
        summary: 'Partial Save',
        detail: `${successful.length} entities updated successfully, ${failed.length} failed: ${failedDetails}`,
        life: 7000
      })
    } else {
      // All updates successful
      toast.add({
        severity: 'success',
        summary: 'Success',
        detail: `Successfully updated ${successful.length} ${successful.length === 1 ? 'entity' : 'entities'}`,
        life: 3000
      })
      
      // Update original data to reflect saved state
      originalData.value = { ...formData.value }
      logger.info('Original data updated to reflect saved state')
    }
    
  } catch (error) {
    const apiError = parseApiError(error)
    logger.error('Save operation failed', { error: apiError })
    toast.add({
      severity: 'error',
      summary: 'Save Error',
      detail: apiError.message,
      life: 5000
    })
  } finally {
    isSaving.value = false
    logger.debug('Save operation finished')
  }
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

function hasActualChanges(changes: any): boolean {
  // Check if there are any actual changes beyond the ID
  const changeKeys = Object.keys(changes).filter(key => key !== 'id')
  return changeKeys.length > 0
}

function extractEntityChanges(prefix: string, originalEntity: any): any {
  const changes: any = {
    id: originalEntity.id
  }
  
  // Extract core field changes
  const nameField = `${prefix}_name`
  const descField = `${prefix}_description`
  const imageField = `${prefix}_image_url`
  const priceField = `${prefix}_price_impact_value`
  
  // Check for actual changes (not just different types)
  const currentName = formData.value[nameField]
  const currentDesc = formData.value[descField]
  const currentImage = formData.value[imageField]
  const currentPrice = formData.value[priceField]
  
  const originalName = originalEntity.name || ''
  const originalDesc = originalEntity.description || ''
  const originalImage = originalEntity.image_url || ''
  const originalPrice = parseFloat(originalEntity.price_impact_value || '0')
  
  if (currentName !== originalName) {
    changes.name = currentName
  }
  
  if (currentDesc !== originalDesc) {
    changes.description = currentDesc
  }
  
  if (currentImage !== originalImage) {
    changes.image_url = currentImage
  }
  
  if (Math.abs(currentPrice - originalPrice) > 0.001) { // Handle floating point precision
    changes.price_impact_value = currentPrice
  }
  
  // Extract validation rule changes
  const validationRules: any = {}
  let hasValidationChanges = false
  
  if (originalEntity.validation_rules) {
    Object.keys(originalEntity.validation_rules).forEach(key => {
      const fieldName = `${prefix}_validation_${key}`
      const newValue = formData.value[fieldName]
      const oldValue = originalEntity.validation_rules[key]
      
      // More precise comparison for different types
      if (!isEqual(newValue, oldValue)) {
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
  
  if (originalEntity.metadata_) {
    Object.keys(originalEntity.metadata_).forEach(key => {
      const fieldName = `${prefix}_metadata_${key}`
      const newValue = formData.value[fieldName]
      const oldValue = originalEntity.metadata_[key]
      
      if (!isEqual(newValue, oldValue)) {
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

// Helper function for deep equality comparison
function isEqual(a: any, b: any): boolean {
  if (a === b) return true
  
  // Handle null/undefined
  if (a == null || b == null) return a === b
  
  // Handle arrays
  if (Array.isArray(a) && Array.isArray(b)) {
    if (a.length !== b.length) return false
    return a.every((item, index) => isEqual(item, b[index]))
  }
  
  // Handle objects
  if (typeof a === 'object' && typeof b === 'object') {
    const keysA = Object.keys(a)
    const keysB = Object.keys(b)
    
    if (keysA.length !== keysB.length) return false
    
    return keysA.every(key => isEqual(a[key], b[key]))
  }
  
  // Handle numbers with precision tolerance
  if (typeof a === 'number' && typeof b === 'number') {
    return Math.abs(a - b) < 0.001
  }
  
  return false
}

function goBack() {
  const scope = route.params.scope as string
  router.push({
    name: 'ProfileDefinitions',
    params: { scope }
  })
}

// Lifecycle
onMounted(loadData)
</script>

<style scoped>
/* Layout CSS - converted from Tailwind */
.page-wrapper {
  min-height: 100vh;
}

.header-container {
  position: sticky;
  top: 0;
  z-index: 10;
}

.header-content {
  max-width: 64rem; /* max-w-4xl */
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
  max-width: 64rem; /* max-w-4xl */
  margin-left: auto;
  margin-right: auto;
}

.loading-container {
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.error-container {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 400px;
}

.error-content {
  text-align: center;
  max-width: 28rem;
}

.error-buttons {
  display: flex;
  gap: 1rem;
  justify-content: center;
}

.form-container {
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.overview-card {
  overflow: hidden;
}

.overview-header {
  padding: 1.5rem 2rem;
}

.overview-content {
  padding: 2rem;
}

.overview-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 2rem;
}

@media (min-width: 768px) {
  .overview-grid {
    grid-template-columns: 1fr 1fr;
  }
}

.company-card,
.material-card,
.opening-card,
.series-card,
.colors-card,
.summary-card {
  overflow: hidden;
}

.company-header,
.material-header,
.opening-header,
.series-header,
.colors-header,
.summary-header {
  padding: 1.5rem 2rem;
}

.company-content,
.material-content,
.opening-content,
.series-content,
.colors-content,
.summary-content {
  padding: 2rem;
}

.tech-specs {
  padding-top: 2rem;
  margin-top: 2rem;
}

.tech-fields {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.colors-list {
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.color-item {
  padding: 1.5rem;
}

.color-header {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.color-fields {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.summary-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 2rem;
}

@media (min-width: 768px) {
  .summary-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}
</style>