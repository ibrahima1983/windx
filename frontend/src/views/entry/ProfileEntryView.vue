<template>
  <AppLayout>
    <div class="profile-entry">
      <!-- Manufacturing Type Selector -->
      <Card class="mb-4">
        <template #title>Select Manufacturing Type</template>
        <template #content>
          <Dropdown
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
        <!-- Dynamic Form -->
        <Card class="mb-4">
          <template #title>Configuration Form</template>
          <template #content>
            <div v-if="manufacturingStore.isLoading" class="space-y-4">
              <Skeleton height="60px" v-for="i in 5" :key="i" />
            </div>

            <div v-else-if="manufacturingStore.schema" class="space-y-6">
              <div v-for="section in manufacturingStore.schema.sections" :key="section.name" class="form-section">
                <h3 class="text-lg font-semibold mb-3">{{ section.label }}</h3>
                
                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div 
                    v-for="field in section.fields" 
                    :key="field.name"
                    v-show="fieldVisibility[field.name] !== false"
                    class="field-item"
                  >
                    <label :for="field.name" class="block font-medium mb-2">
                      {{ field.label }}
                      <span v-if="field.required" class="text-red-500">*</span>
                    </label>

                    <!-- Text Input -->
                    <InputText
                      v-if="field.ui_component === 'text'"
                      :id="field.name"
                      v-model="formData[field.name]"
                      :placeholder="field.description"
                      class="w-full"
                      @blur="validateField(field.name)"
                    />

                    <!-- Number Input -->
                    <InputNumber
                      v-else-if="field.ui_component === 'number'"
                      :id="field.name"
                      v-model="formData[field.name]"
                      class="w-full"
                      @blur="validateField(field.name)"
                    />

                    <!-- Dropdown -->
                    <Dropdown
                      v-else-if="field.ui_component === 'dropdown'"
                      :id="field.name"
                      v-model="formData[field.name]"
                      :options="field.options || []"
                      :placeholder="`Select ${field.label}`"
                      class="w-full"
                      @change="validateField(field.name)"
                    />

                    <!-- Checkbox -->
                    <Checkbox
                      v-else-if="field.ui_component === 'checkbox'"
                      :id="field.name"
                      v-model="formData[field.name]"
                      :binary="true"
                      @change="validateField(field.name)"
                    />

                    <!-- Error Message -->
                    <small v-if="fieldErrors[field.name]" class="text-red-500">
                      {{ fieldErrors[field.name] }}
                    </small>
                  </div>
                </div>
              </div>

              <div class="flex gap-2">
                <Button 
                  label="Save Configuration" 
                  icon="pi pi-save"
                  @click="saveConfiguration"
                  :loading="isSaving"
                  :disabled="!isValid"
                />
                <Button 
                  label="Clear Form" 
                  icon="pi pi-times"
                  @click="clearForm"
                  severity="secondary"
                  outlined
                />
              </div>
            </div>
          </template>
        </Card>

        <!-- Preview Table -->
        <Card>
          <template #title>
            <div class="flex justify-between items-center">
              <span>Saved Configurations</span>
              <Button 
                v-if="configStore.hasPendingChanges"
                label="Save All Changes"
                icon="pi pi-check"
                @click="commitChanges"
                :loading="configStore.isLoading"
                severity="success"
              />
            </div>
          </template>
          <template #content>
            <DataTable
              v-model:editingRows="editingRows"
              :value="configStore.configurations"
              editMode="row"
              dataKey="id"
              @row-edit-save="onRowEditSave"
              :loading="configStore.isLoading"
              paginator
              :rows="10"
              class="p-datatable-sm"
            >
              <Column 
                v-for="header in manufacturingStore.headers" 
                :key="header"
                :field="header"
                :header="header"
              >
                <template #editor="{ data, field }">
                  <InputText v-model="data[field]" class="w-full" />
                </template>
              </Column>

              <Column :rowEditor="true" style="width:10%; min-width:8rem" />
              
              <Column style="width:5%">
                <template #body="slotProps">
                  <Button 
                    icon="pi pi-trash" 
                    @click="confirmDelete(slotProps.data)"
                    severity="danger"
                    text
                    rounded
                  />
                </template>
              </Column>

              <template #empty>
                <div class="text-center py-4 text-gray-500">
                  No configurations found. Create one using the form above.
                </div>
              </template>
            </DataTable>
          </template>
        </Card>
      </div>
    </div>
  </AppLayout>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useToast } from 'primevue/usetoast'
import { useConfirm } from 'primevue/useconfirm'
import Card from 'primevue/card'
import Dropdown from 'primevue/dropdown'
import InputText from 'primevue/inputtext'
import InputNumber from 'primevue/inputnumber'
import Checkbox from 'primevue/checkbox'
import Button from 'primevue/button'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Skeleton from 'primevue/skeleton'
import AppLayout from '@/components/layout/AppLayout.vue'
import { useManufacturingTypeStore } from '@/stores/manufacturingType'
import { useConfigurationStore } from '@/stores/configuration'
import { useFormValidation } from '@/composables/useFormValidation'
import { useDebugLogger } from '@/composables/useDebugLogger'

const logger = useDebugLogger('ProfileEntryView')
const toast = useToast()
const confirm = useConfirm()

const manufacturingStore = useManufacturingTypeStore()
const configStore = useConfigurationStore()

const selectedTypeId = ref<number | null>(null)
const formData = ref<Record<string, any>>({})
const isSaving = ref(false)
const editingRows = ref([])

const schema = computed(() => manufacturingStore.schema)

const { fieldErrors, fieldVisibility, isValid, validateField, validateAll, clearErrors } = 
  useFormValidation(schema, formData)

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

  logger.info('Type changed', { typeId: selectedTypeId.value })
  clearForm()
  
  try {
    await Promise.all([
      manufacturingStore.loadAll(selectedTypeId.value),
      configStore.loadPreviews(selectedTypeId.value)
    ])
    logger.info('Schema and previews loaded')
  } catch (error) {
    toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to load data', life: 5000 })
  }
}

async function saveConfiguration() {
  logger.info('Saving configuration')
  
  if (!validateAll()) {
    toast.add({ severity: 'warn', summary: 'Validation Failed', detail: 'Please fix errors before saving', life: 3000 })
    return
  }

  isSaving.value = true

  try {
    await configStore.createConfiguration({
      ...formData.value,
      manufacturing_type_id: selectedTypeId.value
    })
    
    toast.add({ severity: 'success', summary: 'Success', detail: 'Configuration saved', life: 3000 })
    clearForm()
    
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
  clearErrors()
  logger.debug('Form cleared')
}

function onRowEditSave(event: any) {
  const { newData, index } = event
  logger.info('Row edit saved', { index, data: newData })
  
  // Update is handled by DataTable automatically
  // We track it as pending edit
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
  logger.info('Committing all pending changes')
  
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

<style scoped>
.profile-entry {
  max-width: 1400px;
}

.form-section {
  padding: 1rem;
  background: #f8fafc;
  border-radius: 0.5rem;
}

.field-item {
  margin-bottom: 0;
}
</style>
