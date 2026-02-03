<template>
  <div class="p-6 max-w-md mx-auto bg-white rounded-lg shadow-md">
    <h2 class="text-xl font-bold mb-4">Scope Loading Demo</h2>
    
    <!-- Loading State -->
    <div v-if="isLoading" class="space-y-3">
      <Skeleton height="2rem" class="rounded-md" />
      <Skeleton height="1rem" width="80%" />
      <Skeleton height="1rem" width="60%" />
    </div>
    
    <!-- Error State -->
    <div v-else-if="error" class="p-4 bg-red-50 border border-red-200 rounded-md">
      <p class="text-red-600">{{ error }}</p>
      <Button 
        label="Retry" 
        icon="pi pi-refresh" 
        size="small"
        class="mt-2"
        @click="loadScopes" 
      />
    </div>
    
    <!-- Success State -->
    <div v-else class="space-y-2">
      <p class="text-green-600 font-medium">✓ Scopes loaded successfully!</p>
      <div v-for="(scope, key) in scopes" :key="key" class="p-2 bg-gray-50 rounded">
        <strong>{{ key }}:</strong> {{ scope.label }}
      </div>
      <Button 
        label="Reload" 
        icon="pi pi-refresh" 
        size="small"
        text
        @click="loadScopes" 
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { productDefinitionServiceFactory } from '@/services/productDefinition'
import Skeleton from 'primevue/skeleton'
import Button from 'primevue/button'

const isLoading = ref(false)
const error = ref<string | null>(null)
const scopes = ref<Record<string, any>>({})

async function loadScopes() {
  isLoading.value = true
  error.value = null
  
  try {
    // Get available scopes from factory
    const availableScopes = productDefinitionServiceFactory.getAvailableScopes()
    
    // Create scope info object
    const scopeInfo: Record<string, any> = {}
    for (const scope of availableScopes) {
      scopeInfo[scope] = {
        label: scope.charAt(0).toUpperCase() + scope.slice(1) + ' System',
        service: productDefinitionServiceFactory.getService(scope)
      }
    }
    
    scopes.value = scopeInfo
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Unknown error occurred'
  } finally {
    isLoading.value = false
  }
}

onMounted(loadScopes)
</script>