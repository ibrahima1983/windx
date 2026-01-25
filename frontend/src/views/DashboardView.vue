<template>
  <AppLayout>
    <div class="dashboard">
      <div class="mb-4">
        <h1 class="text-3xl font-bold text-gray-800">Dashboard</h1>
        <p class="text-gray-600 mt-1">Welcome to Windx Configurator</p>
      </div>

      <div v-if="isLoading" class="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Skeleton height="150px" v-for="i in 3" :key="i" />
      </div>

      <div v-else class="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card class="stat-card">
          <template #title>
            <div class="flex items-center justify-between">
              <span>Total Configurations</span>
              <i class="pi pi-file text-2xl text-blue-500"></i>
            </div>
          </template>
          <template #content>
            <div class="text-4xl font-bold text-blue-600">
              {{ stats.total_configurations || 0 }}
            </div>
          </template>
        </Card>

        <Card class="stat-card">
          <template #title>
            <div class="flex items-center justify-between">
              <span>Active Quotes</span>
              <i class="pi pi-file-edit text-2xl text-green-500"></i>
            </div>
          </template>
          <template #content>
            <div class="text-4xl font-bold text-green-600">
              {{ stats.active_quotes || 0 }}
            </div>
          </template>
        </Card>

        <Card class="stat-card">
          <template #title>
            <div class="flex items-center justify-between">
              <span>Pending Orders</span>
              <i class="pi pi-shopping-cart text-2xl text-orange-500"></i>
            </div>
          </template>
          <template #content>
            <div class="text-4xl font-bold text-orange-600">
              {{ stats.pending_orders || 0 }}
            </div>
          </template>
        </Card>
      </div>

      <Message v-if="error" severity="error" class="mt-4">
        {{ error }}
      </Message>
    </div>
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

<style scoped>
.dashboard {
  max-width: 1200px;
}

.stat-card {
  transition: transform 0.2s, box-shadow 0.2s;
}

.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}
</style>
