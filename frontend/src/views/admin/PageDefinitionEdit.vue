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
                <p class="text-base text-slate-600 mt-2">{{ pathData?.ltree_path || 'Loading...' }}</p>
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

          <!-- Configuration Components - Single Column Layout -->
          
          <!-- Company -->
          <div v-if="entityData.company" class="company-card bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
            <div class="company-header px-8 py-6 border-b border-slate-200 bg-blue-50">
              <h3 class="text-2xl font-bold text-slate-900 flex items-center gap-3">
                <i class="pi pi-building text-blue-600"></i>
                Company Information
              </h3>
            </div>
            <div class="company-content p-8 space-y-6">
              <FormFieldRenderer 
                :field="{ name: 'company_name', label: 'Company Name', type: 'text' }"
                v-model="formData.company_name"
              />
              <FormFieldRenderer 
                :field="{ name: 'company_description', label: 'Description', type: 'textarea' }"
                v-model="formData.company_description"
              />
              <FormFieldRenderer 
                :field="{ name: 'company_price', label: 'Base Price', ui_component: 'currency' }"
                v-model="formData.company_price"
              />
            </div>
          </div>

          <!-- Material -->
          <div v-if="entityData.material" class="material-card bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
            <div class="material-header px-8 py-6 border-b border-slate-200 bg-green-50">
              <h3 class="text-2xl font-bold text-slate-900 flex items-center gap-3">
                <i class="pi pi-box text-green-600"></i>
                Material Specifications
              </h3>
            </div>
            <div class="material-content p-8 space-y-6">
              <FormFieldRenderer 
                :field="{ name: 'material_name', label: 'Material Name', type: 'text' }"
                v-model="formData.material_name"
              />
              <FormFieldRenderer 
                :field="{ name: 'material_description', label: 'Description', type: 'textarea' }"
                v-model="formData.material_description"
              />
              <FormFieldRenderer 
                :field="{ name: 'material_price', label: 'Base Price', ui_component: 'currency' }"
                v-model="formData.material_price"
              />
              <FormFieldRenderer 
                v-if="entityData.material.validation_rules?.density"
                :field="{ name: 'material_density', label: 'Density (kg/m³)', type: 'number' }"
                v-model="formData.material_density"
              />
            </div>
          </div>

          <!-- Opening System -->
          <div v-if="entityData.opening_system" class="opening-card bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
            <div class="opening-header px-8 py-6 border-b border-slate-200 bg-orange-50">
              <h3 class="text-2xl font-bold text-slate-900 flex items-center gap-3">
                <i class="pi pi-cog text-orange-600"></i>
                Opening System
              </h3>
            </div>
            <div class="opening-content p-8 space-y-6">
              <FormFieldRenderer 
                :field="{ name: 'opening_system_name', label: 'System Name', type: 'text' }"
                v-model="formData.opening_system_name"
              />
              <FormFieldRenderer 
                :field="{ name: 'opening_system_description', label: 'Description', type: 'textarea' }"
                v-model="formData.opening_system_description"
              />
              <FormFieldRenderer 
                :field="{ name: 'opening_system_price', label: 'Base Price', ui_component: 'currency' }"
                v-model="formData.opening_system_price"
              />
            </div>
          </div>

          <!-- System Series -->
          <div v-if="entityData.system_series" class="series-card bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
            <div class="series-header px-8 py-6 border-b border-slate-200 bg-purple-50">
              <h3 class="text-2xl font-bold text-slate-900 flex items-center gap-3">
                <i class="pi pi-sitemap text-purple-600"></i>
                System Series
              </h3>
            </div>
            <div class="series-content p-8 space-y-6">
              <FormFieldRenderer 
                :field="{ name: 'system_series_name', label: 'Series Name', type: 'text' }"
                v-model="formData.system_series_name"
              />
              <FormFieldRenderer 
                :field="{ name: 'system_series_description', label: 'Description', type: 'textarea' }"
                v-model="formData.system_series_description"
              />
              <FormFieldRenderer 
                :field="{ name: 'system_series_price', label: 'Base Price', ui_component: 'currency' }"
                v-model="formData.system_series_price"
              />
              
              <!-- Technical Specifications -->
              <div class="tech-specs border-t border-slate-200 pt-8 mt-8">
                <h4 class="text-lg font-bold text-slate-800 mb-6">Technical Specifications</h4>
                <div class="tech-fields space-y-6">
                  <FormFieldRenderer 
                    v-if="entityData.system_series.validation_rules?.width"
                    :field="{ name: 'system_series_width', label: 'Width (mm)', type: 'number' }"
                    v-model="formData.system_series_width"
                  />
                  <FormFieldRenderer 
                    v-if="entityData.system_series.validation_rules?.number_of_chambers"
                    :field="{ name: 'system_series_chambers', label: 'Number of Chambers', type: 'number' }"
                    v-model="formData.system_series_chambers"
                  />
                  <FormFieldRenderer 
                    v-if="entityData.system_series.validation_rules?.u_value"
                    :field="{ name: 'system_series_u_value', label: 'U-Value (W/m²K)', type: 'number' }"
                    v-model="formData.system_series_u_value"
                  />
                  <FormFieldRenderer 
                    v-if="entityData.system_series.validation_rules?.number_of_seals"
                    :field="{ name: 'system_series_seals', label: 'Number of Seals', type: 'number' }"
                    v-model="formData.system_series_seals"
                  />
                  <FormFieldRenderer 
                    v-if="entityData.system_series.validation_rules?.characteristics"
                    :field="{ name: 'system_series_characteristics', label: 'Characteristics', type: 'textarea' }"
                    v-model="formData.system_series_characteristics"
                  />
                </div>
              </div>
            </div>
          </div>

          <!-- Colors Section -->
          <div v-if="entityData.colors && entityData.colors.length > 0" class="colors-card bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
            <div class="colors-header px-8 py-6 border-b border-slate-200 bg-pink-50">
              <h3 class="text-2xl font-bold text-slate-900 flex items-center gap-3">
                <i class="pi pi-palette text-pink-600"></i>
                Color Options ({{ entityData.colors.length }})
              </h3>
            </div>
            <div class="colors-content p-8">
              <div class="colors-list space-y-8">
                <div 
                  v-for="(color, index) in entityData.colors" 
                  :key="color.id"
                  class="color-item border border-slate-200 rounded-lg p-6 hover:border-slate-300 transition-colors"
                >
                  <div class="color-header flex items-center gap-4 mb-6">
                    <div 
                      class="w-8 h-8 rounded-full border-2 border-white shadow-sm"
                      :style="{ backgroundColor: getColorValue(color) }"
                    ></div>
                    <h4 class="text-xl font-bold text-slate-900">{{ color.name }}</h4>
                  </div>
                  
                  <div class="color-fields space-y-6">
                    <FormFieldRenderer 
                      :field="{ name: `color_${index}_name`, label: 'Color Name', type: 'text' }"
                      v-model="formData[`color_${index}_name`]"
                    />
                    <FormFieldRenderer 
                      :field="{ name: `color_${index}_price`, label: 'Price Impact', ui_component: 'currency' }"
                      v-model="formData[`color_${index}_price`]"
                    />
                    <FormFieldRenderer 
                      v-if="color.validation_rules?.code"
                      :field="{ name: `color_${index}_code`, label: 'Color Code', type: 'text' }"
                      v-model="formData[`color_${index}_code`]"
                    />
                    <FormFieldRenderer 
                      v-if="color.validation_rules?.has_lamination !== undefined"
                      :field="{ name: `color_${index}_lamination`, label: 'Has Lamination', type: 'boolean' }"
                      v-model="formData[`color_${index}_lamination`]"
                    />
                  </div>
                </div>
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
import { productDefinitionService } from '@/services/productDefinitionService'
import { parseApiError } from '@/utils/errorHandler'

// Components
import AppLayout from '@/components/layout/AppLayout.vue'
import FormFieldRenderer from '@/components/common/FormFieldRenderer.vue'
import Button from 'primevue/button'
import Skeleton from 'primevue/skeleton'

const route = useRoute()
const router = useRouter()
const toast = useToast()

// State
const isLoading = ref(true)
const isSaving = ref(false)
const loadError = ref<string | null>(null)
const pathData = ref<any>(null)
const entityData = ref<any>({})
const formData = ref<Record<string, any>>({})
const originalData = ref<Record<string, any>>({})

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
    
    if (!pathId) {
      throw new Error('Path ID is required')
    }
    
    // Load path data and related entities
    const response = await productDefinitionService.getPathDetails(parseInt(pathId))
    
    if (!response.success) {
      throw new Error('Failed to load path details')
    }
    
    pathData.value = response.path
    entityData.value = response.path.entities || {}
    
    // Initialize form data
    initializeFormData()
    
  } catch (error) {
    const apiError = parseApiError(error)
    loadError.value = apiError.message
    console.error('Failed to load path data:', error)
  } finally {
    isLoading.value = false
  }
}

function initializeFormData() {
  const data: Record<string, any> = {}
  
  // Basic information
  data.display_path = pathData.value?.display_path || ''
  
  // Entity data
  if (entityData.value.company) {
    data.company_name = entityData.value.company.name
    data.company_description = entityData.value.company.description
    data.company_price = parseFloat(entityData.value.company.price_impact_value || '0')
  }
  
  if (entityData.value.material) {
    data.material_name = entityData.value.material.name
    data.material_description = entityData.value.material.description
    data.material_price = parseFloat(entityData.value.material.price_impact_value || '0')
    data.material_density = entityData.value.material.validation_rules?.density
  }
  
  if (entityData.value.opening_system) {
    data.opening_system_name = entityData.value.opening_system.name
    data.opening_system_description = entityData.value.opening_system.description
    data.opening_system_price = parseFloat(entityData.value.opening_system.price_impact_value || '0')
  }
  
  if (entityData.value.system_series) {
    const series = entityData.value.system_series
    data.system_series_name = series.name
    data.system_series_description = series.description
    data.system_series_price = parseFloat(series.price_impact_value || '0')
    data.system_series_width = series.validation_rules?.width
    data.system_series_chambers = series.validation_rules?.number_of_chambers
    data.system_series_u_value = series.validation_rules?.u_value
    data.system_series_seals = series.validation_rules?.number_of_seals
    data.system_series_characteristics = series.validation_rules?.characteristics
  }
  
  if (entityData.value.colors) {
    entityData.value.colors.forEach((color: any, index: number) => {
      data[`color_${index}_name`] = color.name
      data[`color_${index}_price`] = parseFloat(color.price_impact_value || '0')
      data[`color_${index}_code`] = color.validation_rules?.code
      data[`color_${index}_lamination`] = color.validation_rules?.has_lamination
    })
  }
  
  formData.value = data
  originalData.value = { ...data }
}

function calculateTotalPrice(): number {
  let total = 0
  total += formData.value.company_price || 0
  total += formData.value.material_price || 0
  total += formData.value.opening_system_price || 0
  total += formData.value.system_series_price || 0
  
  // Add color prices
  if (entityData.value.colors) {
    entityData.value.colors.forEach((_: any, index: number) => {
      total += formData.value[`color_${index}_price`] || 0
    })
  }
  
  return total
}

function calculateTotalWeight(): number {
  // This would be calculated based on actual weight formulas
  return 45.2 // Placeholder
}

function getColorValue(color: any): string {
  // Simple color mapping - in real app, you'd have proper color values
  const colorMap: Record<string, string> = {
    'White': '#FFFFFF',
    'Black': '#000000',
    'Brown': '#8B4513',
    'Grey': '#808080',
    'Blue': '#0000FF'
  }
  return colorMap[color.name] || '#CCCCCC'
}

function formatDate(dateString: string): string {
  if (!dateString) return ''
  return new Date(dateString).toLocaleDateString()
}

async function saveChanges() {
  isSaving.value = true
  
  try {
    // Here you would implement the actual save logic
    // This would involve updating multiple entities through the API
    
    // Simulate save delay
    await new Promise(resolve => setTimeout(resolve, 1000))
    
    toast.add({
      severity: 'success',
      summary: 'Success',
      detail: 'Configuration updated successfully',
      life: 3000
    })
    
    // Update original data to reflect saved state
    originalData.value = { ...formData.value }
    
  } catch (error) {
    const apiError = parseApiError(error)
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