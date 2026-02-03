<template>
  <AppLayout>
    <div class="max-w-[1400px] mx-auto">
      <div class="mb-6 flex justify-between items-center">
        <div class="flex items-center gap-4">
          <!-- Scope Selector with Loading State -->
          <div v-if="isScopesLoading" class="w-48">
            <Skeleton height="2.5rem" class="rounded-md" />
          </div>
          <div v-else-if="scopesLoadError" class="w-48 p-2 bg-red-50 border border-red-200 rounded-md text-red-600 text-sm">
            {{ scopesLoadError }}
          </div>
          <SmartSelect 
            v-else-if="availableScopes.length > 0"
            v-model="selectedScope" 
            :options="availableScopes" 
            optionLabel="label" 
            optionValue="value"
            class="w-48"
            @change="handleScopeChange"
            @auto-selected="handleScopeChange"
            placeholder="Select Scope"
          />
          
          <!-- Title with Loading State -->
          <div v-if="isScopesLoading">
            <Skeleton height="2rem" width="15rem" class="mb-1" />
            <Skeleton height="1rem" width="20rem" />
          </div>
          <div v-else>
            <h1 class="text-3xl font-bold text-slate-800">{{ currentSchema?.title || 'Loading...' }}</h1>
            <p class="text-slate-500 mt-1">Manage definitions and valid product configurations</p>
          </div>
        </div>
        <div class="flex gap-2">
          <!-- Refresh Button -->
          <Button 
            icon="pi pi-refresh" 
            text 
            rounded 
            @click="loadData" 
            :loading="isLoading" 
            v-tooltip.bottom="'Reload Data'"
            :disabled="isScopesLoading"
          />
        </div>
      </div>

      <div class="card">
        <!-- Loading State for Entire Interface -->
        <div v-if="isScopesLoading" class="p-8">
          <div class="flex gap-4 mb-6">
            <Skeleton height="2.5rem" width="8rem" />
            <Skeleton height="2.5rem" width="10rem" />
          </div>
          <div class="grid gap-4 mb-6 grid-cols-2 md:grid-cols-5">
            <Skeleton height="100px" v-for="i in 5" :key="i" class="rounded-xl" />
          </div>
          <Skeleton height="300px" class="rounded-lg" />
        </div>

        <!-- Error State -->
        <div v-else-if="scopesLoadError" class="p-8 text-center">
          <div class="bg-red-50 border border-red-200 rounded-lg p-6">
            <i class="pi pi-exclamation-triangle text-red-500 text-3xl mb-4"></i>
            <h3 class="text-lg font-semibold text-red-800 mb-2">Failed to Load Configuration</h3>
            <p class="text-red-600 mb-4">{{ scopesLoadError }}</p>
            <Button 
              label="Retry" 
              icon="pi pi-refresh" 
              @click="loadData" 
              :loading="isLoading"
            />
          </div>
        </div>

        <!-- Main Interface -->
        <Tabs v-else value="overview">
          <TabList>
            <Tab value="overview">
              <i class="pi pi-list mr-2"></i> Overview
            </Tab>
            <Tab value="manage">
              <i class="pi pi-pencil mr-2"></i> Manage Definitions
            </Tab>
          </TabList>
          
          <TabPanels>
            <!-- OVERVIEW TAB -->
            <TabPanel value="overview">
              <div v-if="isLoading" class="grid gap-4 mb-6" :class="gridColumnsClass">
                <Skeleton height="100px" v-for="i in skeletonCount" :key="i" class="rounded-xl" />
              </div>

              <!-- Stats Cards -->
              <div v-else-if="currentSchema?.entityTypes" class="grid gap-4 mb-6" :class="gridColumnsClass">
                <button
                  v-for="type in currentSchema.entityTypes" 
                  :key="type.value"
                  class="entity-type-card bg-white border border-slate-200 rounded-xl p-4 flex flex-col items-center justify-center shadow-sm hover:shadow-lg hover:border-slate-300 transition-all duration-200 cursor-pointer focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
                  @click="navigateToDefinition(type.value)"
                  :title="`Click to manage ${type.label} definitions`"
                >
                  <i :class="[type.icon, 'text-2xl mb-2 text-blue-500']"></i>
                  <span class="text-2xl font-bold text-slate-800">{{ getEntityCount(type.value) }}</span>
                  <span class="text-xs text-slate-500 uppercase tracking-wider mt-1">{{ type.label }}</span>
                  <i class="pi pi-external-link text-xs text-slate-400 mt-2 opacity-0 group-hover:opacity-100 transition-opacity"></i>
                </button>
              </div>

              <!-- Paths / Chains Table -->
              <DataTable 
                :value="groupedPaths" 
                paginator 
                :rows="10" 
                class="p-datatable-sm border border-slate-200 rounded-lg overflow-hidden"
                :loading="isLoading"
              >
                <template #header>
                  <div class="flex justify-between items-center px-2">
                    <span class="font-semibold text-lg">Valid Configuration Chains</span>
                    <span class="text-sm text-slate-500">{{ groupedPaths.length }} grouped configurations</span>
                  </div>
                </template>

                <!-- Dynamic Columns based on Chain Structure -->
                <Column 
                  v-for="node in currentSchema?.chainStructure || []" 
                  :key="node.key"
                  :header="node.label"
                >
                  <template #body="{ data }">
                    <div class="flex items-center gap-2 flex-wrap">
                      <i :class="[node.icon, 'text-slate-400 text-xs']"></i>
                      
                      <!-- Handle multiple IDs (Aggregated Leaf) -->
                      <template v-if="Array.isArray(data[`${node.entityType}_id`])">
                         <div class="flex flex-wrap gap-1">
                           <Tag 
                            v-for="id in data[`${node.entityType}_id`]" 
                            :key="id"
                            :value="getEntityName(node.entityType, id)"
                            severity="info"
                            rounded
                            class="px-2 text-[10px] font-semibold"
                          />
                         </div>
                      </template>
                      
                      <!-- Handle single ID -->
                      <span v-else class="font-medium text-slate-700">
                        {{ getEntityName(node.entityType, data[`${node.entityType}_id`]) }}
                      </span>
                    </div>
                  </template>
                </Column>

                <Column header="Actions" style="width: 10%">
                  <template #body="{ data }">
                    <div class="flex gap-1">
                      <Button 
                        icon="pi pi-pencil" 
                        severity="info" 
                        text 
                        rounded 
                        size="small"
                        @click="editPath(data)"
                        v-tooltip.bottom="'Edit Configuration'"
                      />
                      <Button 
                        icon="pi pi-trash" 
                        severity="danger" 
                        text 
                        rounded 
                        size="small"
                        @click="confirmDeletePath(data)"
                        v-tooltip.bottom="'Delete Configuration'"
                      />
                    </div>
                  </template>
                </Column>

                <template #empty>
                  <div class="text-center py-8 text-slate-500">
                    No configuration chains defined yet. Go to "Manage Definitions" to create one.
                  </div>
                </template>
              </DataTable>
            </TabPanel>

            <!-- MANAGE TAB -->
            <TabPanel value="manage">
              <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
                <!-- Left: Form -->
                <div class="lg:col-span-2 space-y-6">
                  <!-- Type Selector -->
                  <div class="flex flex-col gap-2">
                    <label class="font-semibold text-slate-700">Definition Type</label>
                    <SmartSelect 
                      v-model="selectedEntityType" 
                      :options="currentSchema?.entityTypes || []" 
                      optionLabel="label" 
                      optionValue="value"
                      placeholder="Select what to define..."
                      class="w-full"
                      @change="resetForm"
                      @auto-selected="resetForm"
                    >
                      <template #option="slotProps">
                        <div class="flex items-center gap-2">
                          <i :class="slotProps.option.icon"></i>
                          <span>{{ slotProps.option.label }}</span>
                        </div>
                      </template>
                    </SmartSelect>
                  </div>

                  <div v-if="selectedEntityDef" class="bg-slate-50 p-6 rounded-xl border border-slate-200 animate-fade-in">
                    <div class="flex justify-between items-center mb-6 border-b border-slate-200 pb-4">
                      <h2 class="text-xl font-bold flex items-center gap-2">
                        <i :class="[selectedEntityDef.icon, 'text-blue-600']"></i>
                        New {{ selectedEntityDef.label }}
                      </h2>
                    </div>

                    <!-- Dynamic Form -->
                    <div class="space-y-4">
                      <!-- Common Fields -->
                      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <FormFieldRenderer 
                          :field="{ 
                            name: 'name', 
                            label: 'Name', 
                            type: 'text', 
                            required: true,
                            metadata_: {
                              placeholder: (selectedEntityType ? typeMetadata[selectedEntityType]?.placeholders?.name : undefined) || 'Enter name'
                            }
                          }"
                          v-model="formData.name"
                        />
                        <FormFieldRenderer 
                          :field="{ 
                            name: 'price_from', 
                            label: 'Base Price', 
                            ui_component: 'currency', 
                            required: false,
                            metadata_: {
                              placeholder: (selectedEntityType ? typeMetadata[selectedEntityType]?.placeholders?.price : undefined) || 'e.g. 25.00'
                            }
                          }"
                          v-model="formData.price_from"
                        />
                      </div>

                      <FormFieldRenderer 
                        :field="{ 
                          name: 'description', 
                          label: 'Description', 
                          type: 'textarea', 
                          required: false,
                          metadata_: {
                            placeholder: (selectedEntityType ? typeMetadata[selectedEntityType]?.placeholders?.description : undefined) || 'Optional description...'
                          }
                        }"
                        v-model="formData.description"
                      />

                      <!-- Type-Specific Fields from Schema -->
                      <FormSection 
                        v-if="selectedEntityDef.fields.length > 0" 
                        title="Properties" 
                        variant="inline"
                      >
                        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                          <div v-for="field in selectedEntityDef.fields" :key="field.name" class="flex flex-col">
                            <FormFieldRenderer 
                              :field="field"
                              v-model="formData.metadata[field.name]"
                            />
                          </div>
                        </div>
                      </FormSection>


                      <!-- Dynamic Special UI (e.g., Relation Selectors) -->
                      <FormSection 
                        v-if="selectedEntityDef.specialUi?.type === 'relation_selector'"
                        title="Required Link"
                        variant="inline"
                        class="bg-blue-50/50 -mx-6 px-6 py-4"
                      >
                        <template #default>
                          <div class="flex flex-col gap-2">
                            <label class="text-sm font-medium text-slate-700">
                              {{ selectedEntityDef.specialUi.config.label }} 
                              <span v-if="selectedEntityDef.specialUi.config.required" class="text-red-500">*</span>
                            </label>
                            <SmartSelect 
                              v-model="formData[selectedEntityDef.specialUi.config.field_name]"
                              :options="entities?.[selectedEntityDef.specialUi.config.target_entity] || []"
                              optionLabel="name"
                              optionValue="id"
                              :placeholder="`Select ${selectedEntityDef.specialUi.config.label.toLowerCase()}...`"
                              class="w-full"
                            />
                            <small v-if="selectedEntityDef.specialUi.config.help_text" class="text-slate-500">
                              {{ selectedEntityDef.specialUi.config.help_text }}
                            </small>
                          </div>
                        </template>
                      </FormSection>

                      <FormSection 
                        v-if="selectedEntityDef.isLinker"
                        title="System Dependencies"
                        variant="inline"
                        class="bg-orange-50/50 -mx-6 px-6 py-4"
                      >
                        <div class="grid grid-cols-1 gap-4">
                          <div class="flex flex-col gap-2">
                            <label class="text-sm font-medium text-slate-700">Company & Material <span class="text-red-500">*</span></label>
                            <SmartSelect 
                              v-model="formData.linked_company_material"
                              :options="companyMaterialOptions"
                              optionLabel="label"
                              optionValue="value"
                              placeholder="Select Source..."
                              class="w-full"
                            />
                          </div>

                          <div class="flex flex-col gap-2">
                            <label class="text-sm font-medium text-slate-700">Opening System <span class="text-red-500">*</span></label>
                            <SmartSelect 
                              v-model="formData.opening_system_id"
                              :options="entities?.opening_system || []"
                              optionLabel="name"
                              optionValue="id"
                              placeholder="Select Opening System..."
                              class="w-full"
                            />
                          </div>

                          <div class="flex flex-col gap-2">
                            <label class="text-sm font-medium text-slate-700">Available Colors <span class="text-red-500">*</span></label>
                            <ColorChipMultiSelect 
                              v-model="formData.color_ids"
                              :options="entities?.color || []"
                              optionLabel="name"
                              optionValue="id"
                              placeholder="Select Colors..."
                            />
                          </div>
                        </div>
                      </FormSection>

                      <!-- Action Buttons -->
                      <div class="flex justify-end gap-3 mt-8 pt-4 border-t border-slate-200">
                        <Button label="Clear" severity="secondary" text @click="resetForm" />
                        <Button label="Save Definition" icon="pi pi-save" @click="saveEntity" :loading="isSaving" />
                      </div>
                    </div>
                  </div>
                  
                  <div v-else class="flex flex-col items-center justify-center p-12 bg-slate-50 border border-dashed border-slate-300 rounded-xl text-slate-400">
                    <i class="pi pi-arrow-up text-4xl mb-4 opacity-50"></i>
                    <p class="font-medium">Select a definition type above to start</p>
                  </div>
                </div>

                <!-- Right: Image Upload (Contextual) -->
                <div class="lg:col-1">
                  <div v-if="selectedEntityDef?.hasImage" class="sticky top-6">
                    <ImageUploadCard
                      v-model="imageFile"
                      v-model:previewUrl="imagePreview"
                      title="Representation"
                    />
                  </div>
                </div>
              </div>
            </TabPanel>
          </TabPanels>
        </Tabs>
      </div>
    </div>
  </AppLayout>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useToast } from 'primevue/usetoast'
import { useConfirm } from 'primevue/useconfirm'
import camelcaseKeys from 'camelcase-keys'
import { fetchAndBuildSchemas, type DefinitionSchema } from '@/config/definitionSchemas'
import { productDefinitionServiceFactory } from '@/services/productDefinition'
import type { ProfileProductDefinitionService } from '@/services/productDefinition'
import { useDebugLogger } from '@/composables/useDebugLogger'
import { parseApiError } from '@/utils/errorHandler'

// Components
import AppLayout from '@/components/layout/AppLayout.vue'
import ColorChipMultiSelect from '@/components/common/ColorChipMultiSelect.vue'
import SmartSelect from '@/components/common/SmartSelect.vue'
import Tabs from 'primevue/tabs'
import TabList from 'primevue/tablist'
import Tab from 'primevue/tab'
import TabPanels from 'primevue/tabpanels'
import TabPanel from 'primevue/tabpanel'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Skeleton from 'primevue/skeleton'
import Button from 'primevue/button'
import ImageUploadCard from '@/components/common/ImageUploadCard.vue'
import FormFieldRenderer from '@/components/common/FormFieldRenderer.vue'
import FormSection from '@/components/common/FormSection.vue'
import Tag from 'primevue/tag'

const props = defineProps<{
  pageType: string // e.g., 'profile'
}>()

const logger = useDebugLogger('GenericDefinitionView')
const toast = useToast()
const confirm = useConfirm()
const router = useRouter()

// State
const isLoading = ref(false)
const isSaving = ref(false)
const entities = ref<Record<string, any[]>>({})
const paths = ref<any[]>([])
const typeMetadata = ref<Record<string, any>>({}) 

// Scope State
const selectedScope = ref<string | null>(null)
const availableScopes = ref<any[]>([])
const schemas = ref<Record<string, DefinitionSchema>>({})
const isScopesLoading = ref(false)
const scopesLoadError = ref<string | null>(null)


// Form State
const selectedEntityType = ref<string | null>(null)
const formData = ref<Record<string, any>>({
  name: '',
  price_from: null,
  description: '',
  metadata: {} as Record<string, any>,
  // Specifics
  linked_material_id: null,
  linked_company_material: null,
  opening_system_id: null,
  color_ids: []
})

// Helper function to get the appropriate service for the current scope
const getService = () => {
  if (!selectedScope.value) {
    throw new Error('No scope selected')
  }
  return productDefinitionServiceFactory.getService(selectedScope.value)
}
const imageFile = ref<File | null>(null)
const imagePreview = ref<string | null>(null)

// Computed
const currentSchema = computed(() => {
  if (isScopesLoading.value) {
    return { title: 'Loading scopes...', entityTypes: [], chainStructure: [] }
  }
  if (!selectedScope.value || !schemas.value[selectedScope.value]) {
    return { title: 'Select a scope', entityTypes: [], chainStructure: [] }
  }
  return schemas.value[selectedScope.value]
})

const selectedEntityDef = computed(() => {
  if (!currentSchema.value?.entityTypes) return undefined
  return currentSchema.value.entityTypes.find(t => t.value === selectedEntityType.value)
})

const gridColumnsClass = computed(() => {
  const count = currentSchema.value?.entityTypes?.length || 5
  if (count <= 1) return 'grid-cols-1'
  if (count === 2) return 'grid-cols-2'
  if (count === 3) return 'grid-cols-1 md:grid-cols-3'
  if (count === 4) return 'grid-cols-2 md:grid-cols-4'
  return 'grid-cols-2 md:grid-cols-5'
})

const skeletonCount = computed(() => currentSchema.value?.entityTypes?.length || 5)

const companyMaterialOptions = computed(() => {
  if (!entities.value.company || !entities.value.material) return []
  
  // DEBUG: Inspect first company to see structure
  if (entities.value.company.length > 0) {
    console.log('[GenericDefinitionView] Company Data:', JSON.parse(JSON.stringify(entities.value.company[0])))
    console.log('[GenericDefinitionView] Material Data:', JSON.parse(JSON.stringify(entities.value.material)))
  }

  const options = []
  for (const comp of entities.value.company) {
    // Check various possible locations for the link
    // TRY ALL: validation_rules, metadata, or just root property
    const matId = comp.validation_rules?.linked_material_id 
               || comp.metadata?.linked_material_id 
               || comp.linked_material_id
               || (comp.validation_rules && comp.validation_rules['linked_material_id'])
    
    console.log(`[GenericDefinitionView] Checking Company: ${comp.name}`, { 
      validation_rules: JSON.parse(JSON.stringify(comp.validation_rules || {})), 
      metadata: JSON.parse(JSON.stringify(comp.metadata || {})),
      extractedMatId: matId 
    })

    if (matId) {
      const mat = entities.value.material.find(m => m.id == matId)
      if (mat) {
        options.push({
          label: `${comp.name} → ${mat.name}`,
          value: `${comp.id}:${mat.id}`
        })
      } else {
        console.warn(`[GenericDefinitionView] Material ID ${matId} not found in materials list`)
      }
    }
  }
  return options
})

const groupedPaths = computed(() => {
  // Currently only applied to profile scope where we have the multi-color problem
  if (selectedScope.value !== 'profile' || paths.value.length === 0) return paths.value

  const groups: Record<string, any> = {}
  const chain = currentSchema.value?.chainStructure || []
  if (chain.length < 2) return paths.value

  // Identify the leaf entity type (last in chain)
  const leafNode = chain[chain.length - 1]
  if (!leafNode) return paths.value
  const leafKey = leafNode.entityType

  for (const path of paths.value) {
    // Generate a grouping key based on all properties EXCEPT the leaf and technical metadata (id, ltree)
    const groupingProperties = chain.slice(0, -1).map(node => path[`${node.entityType}_id`])
    const groupKey = groupingProperties.join('-')
    
    if (!groups[groupKey]) {
      groups[groupKey] = {
        ...path,
        [`${leafKey}_id`]: [path[`${leafKey}_id`]],
        _ltree_paths: [path.ltree_path],
        _ids: [path.id],
        _is_grouped: true
      }
    } else {
      const leafId = path[`${leafKey}_id`]
      if (!groups[groupKey][`${leafKey}_id`].includes(leafId)) {
        groups[groupKey][`${leafKey}_id`].push(leafId)
        groups[groupKey]._ltree_paths.push(path.ltree_path)
        groups[groupKey]._ids.push(path.id)
      }
    }
  }
  
  return Object.values(groups)
})

// Initialization
onMounted(loadData)

watch(() => props.pageType, loadData)

async function loadData() {
  isLoading.value = true
  try {
    // 0. Fetch and build schemas if not already done (or force refresh)
    if (Object.keys(schemas.value).length === 0) {
        isScopesLoading.value = true
        scopesLoadError.value = null
        
        try {
          schemas.value = await fetchAndBuildSchemas()
          
          // Populate available scopes
          availableScopes.value = Object.keys(schemas.value).map(key => {
              const schema = schemas.value[key]
              return {
                  label: schema ? schema.title : key,  // Guard access
                  value: key
              }
          })

          // Set default scope
          if (!selectedScope.value && availableScopes.value.length > 0) {
              selectedScope.value = props.pageType && schemas.value[props.pageType] ? props.pageType : availableScopes.value[0].value
          }
        } catch (error) {
          const apiError = parseApiError(error)
          scopesLoadError.value = apiError.message
          logger.error('Failed to load scopes', { error: apiError, originalError: error })
          toast.add({ 
            severity: 'error', 
            summary: 'Configuration Error', 
            detail: apiError.message, 
            life: 5000 
          })
          return
        } finally {
          isScopesLoading.value = false
        }
    }

    if (!selectedScope.value) return 

    // 1. Load entities
    if (currentSchema.value && currentSchema.value.entityTypes) {
        for (const typeDef of currentSchema.value.entityTypes) {
            const service = getService()
            const response = await service.getEntities(typeDef.value)
            
            if (response.success) {
                entities.value[typeDef.value] = response.entities
                // Store type-level UI metadata
                if (response.type_metadata) {
                    typeMetadata.value[typeDef.value] = camelcaseKeys(response.type_metadata, { deep: true })
                    logger.debug('Type metadata for', typeDef.value, ':', typeMetadata.value[typeDef.value])
                }
            }
        }
    }

    // 2. Load paths (Only relevant for profile scope currently)
    if (selectedScope.value === 'profile') {
        const profileService = getService() as ProfileProductDefinitionService
        const pathsData = await profileService.getPaths()
        paths.value = pathsData
    } else {
        paths.value = [] // Clear paths for non-profile scopes
    }

    logger.info('Data loaded', { scope: selectedScope.value, entityTypes: Object.keys(entities.value) })
  } catch (error) {
    const apiError = parseApiError(error)
    logger.error('Failed to load definition data', { error: apiError, originalError: error })
    toast.add({ 
      severity: 'error', 
      summary: apiError.type === 'server' ? 'Server Error' : 'Load Error', 
      detail: apiError.message, 
      life: 5000 
    })
  } finally {
    isLoading.value = false
  }
}

async function handleScopeChange() {
    // Reset selection when scope changes
    selectedEntityType.value = null
    resetForm()
    // Clear previous data
    entities.value = {}
    paths.value = []
    // Reload data for new scope
    await loadData()
}

// Helpers
function getEntityCount(type: string) {
  return entities.value[type]?.length || 0
}

function getEntityName(type: string, id: number) {
  const list = entities.value[type]
  if (!list) return 'Unknown'
  const found = list.find((e: any) => e.id === id)
  return found ? found.name : 'Unknown'
}

// Form Actions
function resetForm() {
  formData.value = {
    name: '',
    price_from: null,
    description: '',
    metadata: {},
    linked_material_id: null,
    linked_company_material: null,
    opening_system_id: null,
    color_ids: []
  }
  clearImage()
}

// Debug
watch(typeMetadata, (newVal) => {
  logger.info('Type Metadata Updated:', newVal)
}, { deep: true })

// Image Actions
function clearImage() {
  imageFile.value = null
  imagePreview.value = null
}

// Save Logic
async function saveEntity() {
  if (!formData.value.name || !selectedEntityType.value) {
    toast.add({ severity: 'warn', summary: 'Validation', detail: 'Name is required', life: 3000 })
    return
  }

  isSaving.value = true
  try {
    // 1. Upload Image if present
    let imageUrl = null
    if (imageFile.value) {
      const service = getService()
      const uploadRes = await service.uploadImage(imageFile.value)
      if (uploadRes.success) imageUrl = uploadRes.url
    }

    const type = selectedEntityType.value
    const basePayload = {
      entity_type: type,
      name: formData.value.name,
      price_from: formData.value.price_from,
      description: formData.value.description,
      image_url: imageUrl,
      metadata: { ...formData.value.metadata }
    }


    // Handle Special UI Fields (e.g., relation_selector)
    if (selectedEntityDef.value?.specialUi?.type === 'relation_selector') {
      const config = selectedEntityDef.value.specialUi.config
      const fieldValue = (formData.value as any)[config.field_name]
      
      if (config.required && !fieldValue) {
        throw new Error(`${config.label} is required`)
      }
      
      if (fieldValue) {
        basePayload.metadata[config.field_name] = fieldValue
      }
    }


    // Special Case: System Series (Linker)
    if (selectedEntityDef.value?.isLinker) {
      if (!formData.value.linked_company_material || !formData.value.opening_system_id || formData.value.color_ids.length === 0) {
        throw new Error('Please fill all link fields and select at least one color')
      }
      
      // Parse company and material IDs from the combined value
      const [compId, matId] = (formData.value.linked_company_material as string).split(':').map(Number)
      
      if (!compId || !matId) {
        throw new Error('Invalid company/material configuration')
      }
      
      // Lookup Names for Metadata (Dependency Engine requires Names)
      const company = entities.value.company?.find((c: any) => c.id === compId)
      const material = entities.value.material?.find((m: any) => m.id === matId)
      const openingSystem = entities.value.opening_system?.find((os: any) => os.id === formData.value.opening_system_id)
      
      if (company) basePayload.metadata.linked_company_material = company.name
      if (material) basePayload.metadata.linked_material_id = material.name
      if (openingSystem) basePayload.metadata.opening_system_id = openingSystem.name
      
      console.log('[SystemSeries] Creating Series with Metadata:', {
          company: basePayload.metadata.linked_company_material,
          material: basePayload.metadata.linked_material_id,
          opening: basePayload.metadata.opening_system_id
      })
      
      // Create Series Entity
      const service = getService()
      const createRes = await service.createEntity(basePayload)
      if (!createRes.success) throw new Error('Failed to create series entity')
      
      const seriesId = createRes.entity.id
      if (!entities.value[type]) entities.value[type] = []
      entities.value[type].push(createRes.entity) // Optimistic update

      // Create Paths
      let pathsCreated = 0
      for (const colorId of formData.value.color_ids) {
        const profileService = service as ProfileProductDefinitionService
        await profileService.createPath({
          company_id: compId,
          material_id: matId,
          opening_system_id: formData.value.opening_system_id,
          system_series_id: seriesId,
          color_id: colorId
        })
        pathsCreated++
      }
      
      toast.add({ severity: 'success', summary: 'Success', detail: `Series created with ${pathsCreated} valid configurations`, life: 3000 })
      await loadData() // Refresh full state
    } else {
      // Normal Entity
      const service = getService()
      const createRes = await service.createEntity(basePayload)
      if (createRes.success) {
        if (!entities.value[type]) entities.value[type] = []
        entities.value[type].push(createRes.entity)
        toast.add({ severity: 'success', summary: 'Success', detail: `${selectedEntityDef.value?.label} created`, life: 3000 })
      }
    }

    // Clear only primary identity fields to allow rapid repeated entry
    formData.value.name = ''
    formData.value.price_from = null
    clearImage()
  } catch (error: any) {
    const apiError = parseApiError(error)
    logger.error('Save failed', { error: apiError, originalError: error })
    
    // Provide specific error messages based on error type
    let summary = 'Save Error'
    if (apiError.type === 'validation') {
      summary = 'Validation Error'
    } else if (apiError.type === 'server') {
      summary = 'Server Error'
    } else if (apiError.type === 'network') {
      summary = 'Connection Error'
    }
    
    toast.add({ 
      severity: 'error', 
      summary, 
      detail: apiError.message, 
      life: 5000 
    })
  } finally {
    isSaving.value = false
  }
}

// Delete Logic
function editPath(pathData: any) {
  // Navigate to edit page with path data
  router.push({
    name: 'PageDefinitionEdit',
    params: {
      scope: selectedScope.value || 'profile',
      pathId: pathData.id.toString()
    },
    query: {
      // Pass additional data as query params for immediate access
      ltreePath: pathData.ltree_path,
      isGrouped: pathData._is_grouped ? 'true' : 'false'
    }
  })
}

function navigateToDefinition(entityType: string) {
  logger.info('Navigating to definition page', { entityType })
  router.push({
    name: 'Definition',
    params: { entityType }
  })
}

function confirmDeletePath(pathData: any) {
  confirm.require({
    message: pathData._is_grouped && pathData._ltree_paths?.length > 1
      ? `Delete this configuration and all ${pathData._ltree_paths.length} associated colors?`
      : 'Delete this configuration chain?',
    header: 'Confirm Delete',
    icon: 'pi pi-exclamation-triangle',
    accept: async () => {
      try {
        const profileService = getService() as ProfileProductDefinitionService
        if (pathData._is_grouped && pathData._ltree_paths) {
          // Delete all paths in the group
          for (const ltree of pathData._ltree_paths) {
            await profileService.deletePath({ ltree_path: ltree })
          }
        } else {
          await profileService.deletePath({ ltree_path: pathData.ltree_path })
        }
        
        toast.add({ severity: 'success', summary: 'Deleted', detail: 'Configuration removed', life: 3000 })
        await loadData() // Refresh state
      } catch (error) {
        const apiError = parseApiError(error)
        toast.add({ 
          severity: 'error', 
          summary: 'Delete Error', 
          detail: apiError.message, 
          life: 5000 
        })
      }
    }
  })
}
</script>

<style scoped>
/* Animation Utility */
.animate-fade-in {
  animation: fadeIn 0.3s ease-out;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(5px); }
  to { opacity: 1; transform: translateY(0); }
}

/* Entity Type Cards */
.entity-type-card {
  /* Reset button styles */
  background: none;
  border: none;
  padding: 0;
  margin: 0;
  font: inherit;
  color: inherit;
  text-decoration: none;
  cursor: pointer;
  outline: none;
  
  /* Card styles */
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  width: 100%;
  text-align: center;
}

.entity-type-card:hover {
  transform: translateY(-2px);
}

.entity-type-card:focus {
  outline: 2px solid #3b82f6;
  outline-offset: 2px;
}

.entity-type-card:active {
  transform: translateY(0);
}


</style>