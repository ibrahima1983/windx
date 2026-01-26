<template>
  <AppLayout>
      <div class="mb-6">
        <h1 class="text-3xl font-bold text-slate-800">Dashboard</h1>
        <p class="text-slate-600 mt-1">Welcome to Windx Configurator</p>
      </div>

      <div v-if="isLoading" class="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Skeleton height="150px" v-for="i in 3" :key="i" class="rounded-xl" />
      </div>

      <div v-else class="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card class="transform transition-all duration-200 hover:-translate-y-1 hover:shadow-lg border border-slate-100">
          <template #title>
            <div class="flex items-center justify-between mb-2">
              <span class="text-slate-600 font-medium h4">Total Configurations</span>
              <div class="p-2 bg-blue-50 rounded-lg">
                <i class="pi pi-file text-xl text-blue-500"></i>
              </div>
            </div>
          </template>
          <template #content>
            <div class="text-4xl font-bold text-slate-800">
              {{ stats.total_configurations || 0 }}
            </div>
          </template>
        </Card>

        <Card class="transform transition-all duration-200 hover:-translate-y-1 hover:shadow-lg border border-slate-100">
          <template #title>
            <div class="flex items-center justify-between mb-2">
              <span class="text-slate-600 font-medium h4">Active Quotes</span>
              <div class="p-2 bg-green-50 rounded-lg">
                <i class="pi pi-file-edit text-xl text-green-500"></i>
              </div>
            </div>
          </template>
          <template #content>
            <div class="text-4xl font-bold text-slate-800">
              {{ stats.active_quotes || 0 }}
            </div>
          </template>
        </Card>

        <Card class="transform transition-all duration-200 hover:-translate-y-1 hover:shadow-lg border border-slate-100">
          <template #title>
            <div class="flex items-center justify-between mb-2">
              <span class="text-slate-600 font-medium h4">Pending Orders</span>
              <div class="p-2 bg-orange-50 rounded-lg">
                <i class="pi pi-shopping-cart text-xl text-orange-500"></i>
              </div>
            </div>
          </template>
          <template #content>
            <div class="text-4xl font-bold text-slate-800">
              {{ stats.pending_orders || 0 }}
            </div>
          </template>
        </Card>
      </div>

      <Message v-if="error" severity="error" class="mt-6">
        {{ error }}
      </Message>
  </AppLayout>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import Card from 'primevue/card'
import Skeleton from 'primevue/skeleton'
import Message from 'primevue/message'
import AppLayout from '@/components/layout/AppLayout.vue'
import { apiClient } from '@/services/api'
import { useDebugLogger } from '@/composables/useDebugLogger'

const logger = useDebugLogger('DashboardView')

const stats = ref({
  total_configurations: 0,
  active_quotes: 0,
  pending_orders: 0
})
const isLoading = ref(false)
const error = ref<string | null>(null)

onMounted(async () => {
  isLoading.value = true
  error.value = null

  try {
    logger.info('Loading dashboard stats')
    const response = await apiClient.get('/api/v1/dashboard/stats')
    stats.value = response.data
    logger.info('Dashboard stats loaded', stats.value)
  } catch (err: any) {
    const msg = err.response?.data?.detail || err.message || 'Failed to load stats'
    error.value = msg
    logger.error('Failed to load dashboard stats', { error: msg, err })
  } finally {
    isLoading.value = false
  }
})
</script>
