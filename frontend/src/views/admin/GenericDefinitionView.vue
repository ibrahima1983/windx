<template>
  <AppLayout>
    <div class="max-w-[1400px] mx-auto">
      <div class="mb-6 flex justify-between items-center">
        <div>
          <h1 class="text-3xl font-bold text-slate-800">{{ currentSchema.title }}</h1>
          <p class="text-slate-500 mt-1">Manage definitions and valid product configurations</p>
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
          />
        </div>
      </div>

      <div class="card">
        <Tabs value="overview">
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
              <div v-if="isLoading" class="grid grid-cols-1 md:grid-cols-5 gap-4 mb-6">
                <Skeleton height="100px" v-for="i in 5" :key="i" class="rounded-xl" />
              </div>

              <!-- Stats Cards -->
              <div v-else class="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
                <div 
                  v-for="type in currentSchema.entityTypes" 
                  :key="type.value"
                  class="bg-white border border-slate-200 rounded-xl p-4 flex flex-col items-center justify-center shadow-sm hover:shadow-md transition-shadow"
                >
                  <i :class="[type.icon, 'text-2xl mb-2 text-blue-500']"></i>
                  <span class="text-2xl font-bold text-slate-800">{{ getEntityCount(type.value) }}</span>
                  <span class="text-xs text-slate-500 uppercase tracking-wider mt-1">{{ type.label }}</span>
                </div>
              </div>

              <!-- Paths / Chains Table -->
              <DataTable 
                :value="paths" 
                paginator 
                :rows="10" 
                class="p-datatable-sm border border-slate-200 rounded-lg overflow-hidden"
                :loading="isLoading"
              >
                <template #header>
                  <div class="flex justify-between items-center px-2">
                    <span class="font-semibold text-lg">Valid Configuration Chains</span>
                    <span class="text-sm text-slate-500">{{ paths.length }} total chains</span>
                  </div>
                </template>

                <!-- Dynamic Columns based on Chain Structure -->
                <Column 
                  v-for="node in currentSchema.chainStructure" 
                  :key="node.key"
                  :header="node.label"
                >
                  <template #body="{ data }">
                    <div class="flex items-center gap-2">
                      <i :class="[node.icon, 'text-slate-400 text-xs']"></i>
                      <span class="font-medium text-slate-700">
                        {{ getEntityName(node.entityType, data[`${node.entityType}_id`]) }}
                      </span>
                    </div>
                  </template>
                </Column>

                <Column header="Actions" style="width: 5%">
                  <template #body="{ data }">
                    <Button 
                      icon="pi pi-trash" 
                      severity="danger" 
                      text 
                      rounded 
                      size="small"
                      @click="confirmDeletePath(data)"
                    />
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
                    <Select 
                      v-model="selectedEntityType" 
                      :options="currentSchema.entityTypes" 
                      optionLabel="label" 
                      optionValue="value"
                      placeholder="Select what to define..."
                      class="w-full"
                      @change="resetForm"
                    >
                      <template #option="slotProps">
                        <div class="flex items-center gap-2">
                          <i :class="slotProps.option.icon"></i>
                          <span>{{ slotProps.option.label }}</span>
                        </div>
                      </template>
                    </Select>
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
                        <div class="flex flex-col gap-2">
                          <label class="text-sm font-medium text-slate-700">Name <span class="text-red-500">*</span></label>
                          <InputText v-model="formData.name" placeholder="e.g. Standard, Oak, Series 7000" />
                        </div>
                        <div class="flex flex-col gap-2">
                          <label class="text-sm font-medium text-slate-700">Base Price</label>
                          <InputNumber v-model="formData.price_from" mode="currency" currency="USD" locale="en-US" placeholder="0.00" />
                        </div>
                      </div>

                      <div class="flex flex-col gap-2">
                        <label class="text-sm font-medium text-slate-700">Description</label>
                        <Textarea v-model="formData.description" rows="2" placeholder="Optional description..." class="w-full" />
                      </div>

                      <!-- Type-Specific Fields from Schema -->
                      <div v-if="selectedEntityDef.fields.length > 0" class="border-t border-slate-200 pt-4 mt-4">
                        <h3 class="text-sm font-bold text-slate-500 uppercase tracking-wide mb-4">Properties</h3>
                        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                          <div v-for="field in selectedEntityDef.fields" :key="field.name" class="flex flex-col gap-2">
                            <label class="text-sm font-medium text-slate-700">{{ field.label }}</label>
                            
                            <InputText v-if="field.type === 'text'" v-model="formData.metadata[field.name]" />
                            <InputNumber v-else-if="field.type === 'number'" v-model="formData.metadata[field.name]" :maxFractionDigits="2" />
                            <Checkbox v-else-if="field.type === 'boolean'" v-model="formData.metadata[field.name]" :binary="true" />
                            <Textarea v-else-if="field.type === 'textarea'" v-model="formData.metadata[field.name]" rows="3" />
                          </div>
                        </div>
                      </div>

                      <!-- Special: Linking Logic (Harder part) -->
                      <div v-if="selectedEntityDef.value === 'company'" class="border-t border-slate-200 pt-4 mt-4 bg-blue-50/50 -mx-6 px-6 py-4">
                        <h3 class="text-sm font-bold text-blue-600 uppercase tracking-wide mb-4">Required Link</h3>
                        <div class="flex flex-col gap-2">
                          <label class="text-sm font-medium text-slate-700">Linked Material <span class="text-red-500">*</span></label>
                          <Select 
                            v-model="formData.linked_material_id"
                            :options="entities.material || []"
                            optionLabel="name"
                            optionValue="id"
                            placeholder="Select material..."
                            class="w-full"
                          />
                          <small class="text-slate-500">Companies must be linked to a specific material type.</small>
                        </div>
                      </div>

                      <div v-if="selectedEntityDef.isLinker" class="border-t border-slate-200 pt-4 mt-4 bg-orange-50/50 -mx-6 px-6 py-4">
                        <h3 class="text-sm font-bold text-orange-600 uppercase tracking-wide mb-4">System Dependencies</h3>
                        
                        <div class="grid grid-cols-1 gap-4">
                          <div class="flex flex-col gap-2">
                            <label class="text-sm font-medium text-slate-700">Company & Material <span class="text-red-500">*</span></label>
                            <Select 
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
                            <Select 
                              v-model="formData.opening_system_id"
                              :options="entities.opening_system || []"
                              optionLabel="name"
                              optionValue="id"
                              placeholder="Select Opening System..."
                              class="w-full"
                            />
                          </div>

                          <div class="flex flex-col gap-2">
                            <label class="text-sm font-medium text-slate-700">Available Colors <span class="text-red-500">*</span></label>
                            <MultiSelect 
                              v-model="formData.color_ids"
                              :options="entities.color || []"
                              optionLabel="name"
                              optionValue="id"
                              placeholder="Select Colors..."
                              class="w-full"
                              display="chip"
                            />
                          </div>
                        </div>
                      </div>

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
                    <Card class="shadow-sm border border-slate-100">
                      <template #title>
                        <span class="text-sm font-bold uppercase text-slate-500">Representation</span>
                      </template>
                      <template #content>
                        <div 
                          class="w-full aspect-square border-2 border-dashed border-slate-300 rounded-lg flex flex-col items-center justify-center cursor-pointer hover:border-blue-500 hover:bg-blue-50 transition-colors relative overflow-hidden group"
                          @click="triggerImageUpload"
                          @dragover.prevent
                          @drop.prevent="handleDrop"
                        >
                          <input type="file" ref="fileInput" class="hidden" accept="image/*" @change="handleFileSelect" />
                          
                          <div v-if="imagePreview" class="absolute inset-0">
                            <img :src="imagePreview" class="w-full h-full object-cover" />
                            <div class="absolute inset-0 bg-black/50 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
                              <span class="text-white text-sm font-medium">Change Image</span>
                            </div>
                          </div>
                          
                          <div v-else class="text-center p-4">
                            <i class="pi pi-image text-3xl text-slate-300 mb-2"></i>
                            <p class="text-xs text-slate-500">Drag image here or click to upload</p>
                          </div>
                        </div>
                        <Button v-if="imagePreview" label="Remove Image" severity="danger" text size="small" class="w-full mt-2" @click="clearImage" />
                      </template>
                    </Card>
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
import { useToast } from 'primevue/usetoast'
import { useConfirm } from 'primevue/useconfirm'
import { definitionSchemas } from '@/config/definitionSchemas'
import { productDefinitionService } from '@/services/productDefinitionService'
import { useDebugLogger } from '@/composables/useDebugLogger'

// Components
import AppLayout from '@/components/layout/AppLayout.vue'
import Tabs from 'primevue/tabs'
import TabList from 'primevue/tablist'
import Tab from 'primevue/tab'
import TabPanels from 'primevue/tabpanels'
import TabPanel from 'primevue/tabpanel'
import Button from 'primevue/button'
import Select from 'primevue/select'
import MultiSelect from 'primevue/multiselect'
import InputText from 'primevue/inputtext'
import InputNumber from 'primevue/inputnumber'
import Textarea from 'primevue/textarea'
import Checkbox from 'primevue/checkbox'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Skeleton from 'primevue/skeleton'
import Card from 'primevue/card'

const props = defineProps<{
  pageType: string // e.g., 'profile'
}>()

const logger = useDebugLogger('GenericDefinitionView')
const toast = useToast()
const confirm = useConfirm()

// State
const isLoading = ref(false)
const isSaving = ref(false)
const entities = ref<Record<string, any[]>>({})
const paths = ref<any[]>([])

// Form State
const selectedEntityType = ref<string | null>(null)
const formData = ref({
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
const imageFile = ref<File | null>(null)
const imagePreview = ref<string | null>(null)
const fileInput = ref<HTMLInputElement | null>(null)

// Computed
const currentSchema = computed(() => definitionSchemas[props.pageType] || definitionSchemas.profile || {
  title: 'Unknown Definition',
  entityTypes: [],
  chainStructure: []
})

const selectedEntityDef = computed(() => 
  currentSchema.value.entityTypes.find(t => t.value === selectedEntityType.value)
)

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

// Initialization
onMounted(loadData)

watch(() => props.pageType, loadData)

async function loadData() {
  isLoading.value = true
  try {
    // 1. Load entities for all defined types in schema
    for (const typeDef of currentSchema.value.entityTypes) {
      const response = await productDefinitionService.getEntities(typeDef.value)
      if (response.success) {
        entities.value[typeDef.value] = response.entities
      }
    }

    // 2. Load paths
    const pathsData = await productDefinitionService.getPaths()
    paths.value = pathsData

    logger.info('Data loaded', { entityTypes: Object.keys(entities.value), paths: paths.value.length })
  } catch (error) {
    logger.error('Failed to load definition data', error)
    toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to load definitions', life: 5000 })
  } finally {
    isLoading.value = false
  }
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

// Image Actions
function triggerImageUpload() {
  fileInput.value?.click()
}

function handleFileSelect(event: Event) {
  const file = (event.target as HTMLInputElement).files?.[0]
  if (file) processFile(file)
}

function handleDrop(event: DragEvent) {
  const file = event.dataTransfer?.files[0]
  if (file) processFile(file)
}

function processFile(file: File) {
  if (!file.type.startsWith('image/')) {
    toast.add({ severity: 'warn', summary: 'Invalid File', detail: 'Please upload an image', life: 3000 })
    return
  }
  imageFile.value = file
  const reader = new FileReader()
  reader.onload = (e) => imagePreview.value = e.target?.result as string
  reader.readAsDataURL(file)
}

function clearImage() {
  imageFile.value = null
  imagePreview.value = null
  if (fileInput.value) fileInput.value.value = ''
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
      const uploadRes = await productDefinitionService.uploadImage(imageFile.value)
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

    // Special Case: Company Linking
    if (type === 'company') {
      if (!formData.value.linked_material_id) throw new Error('Company must be linked to a material')
      basePayload.metadata['linked_material_id'] = formData.value.linked_material_id
    }

    // Special Case: System Series (Linker)
    if (selectedEntityDef.value?.isLinker) {
      if (!formData.value.linked_company_material || !formData.value.opening_system_id || formData.value.color_ids.length === 0) {
        throw new Error('Please fill all link fields and select at least one color')
      }
      
      // Create Series Entity first
      const createRes = await productDefinitionService.createEntity(basePayload)
      if (!createRes.success) throw new Error('Failed to create series entity')
      
      const seriesId = createRes.entity.id
      if (!entities.value[type]) entities.value[type] = []
      entities.value[type].push(createRes.entity) // Optimistic update

      // Create Paths
      const [compId, matId] = (formData.value.linked_company_material as string).split(':').map(Number)
      
      if (!compId || !matId) {
        throw new Error('Invalid company/material configuration')
      }

      let pathsCreated = 0
      for (const colorId of formData.value.color_ids) {
        await productDefinitionService.createPath({
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
      const createRes = await productDefinitionService.createEntity(basePayload)
      if (createRes.success) {
        if (!entities.value[type]) entities.value[type] = []
        entities.value[type].push(createRes.entity)
        toast.add({ severity: 'success', summary: 'Success', detail: `${selectedEntityDef.value?.label} created`, life: 3000 })
      }
    }

    resetForm()
  } catch (error: any) {
    logger.error('Save failed', error)
    toast.add({ severity: 'error', summary: 'Error', detail: error.message || 'Failed to save', life: 3000 })
  } finally {
    isSaving.value = false
  }
}

// Delete Logic
function confirmDeletePath(pathData: any) {
  // Logic to delete path (or group of paths if they share an ltree)
  confirm.require({
    message: 'Delete this configuration chain?',
    header: 'Confirm Delete',
    icon: 'pi pi-exclamation-triangle',
    accept: async () => {
      try {
        await productDefinitionService.deletePath({ ltree_path: pathData.ltree_path })
        toast.add({ severity: 'success', summary: 'Deleted', detail: 'Configuration chain removed', life: 3000 })
        // Optimistic remove
        paths.value = paths.value.filter(p => p.ltree_path !== pathData.ltree_path)
      } catch (error) {
        toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to delete', life: 3000 })
      }
    }
  })
}
</script>

<style>
/* Animation Utility */
.animate-fade-in {
  animation: fadeIn 0.3s ease-out;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(5px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
