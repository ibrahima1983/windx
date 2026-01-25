<template>
  <Toolbar class="windx-header">
    <template #start>
      <Button 
        icon="pi pi-bars" 
        @click="emit('toggle-sidebar')"
        text
        rounded
      />
      <span class="ml-3 font-semibold text-lg">{{ pageTitle }}</span>
    </template>

    <template #end>
      <div class="flex items-center gap-2">
        <span v-if="authStore.user" class="text-sm text-gray-600">
          {{ authStore.user.full_name || authStore.user.username }}
        </span>
        <Avatar 
          icon="pi pi-user" 
          shape="circle" 
          class="bg-primary text-white"
        />
      </div>
    </template>
  </Toolbar>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import Toolbar from 'primevue/toolbar'
import Button from 'primevue/button'
import Avatar from 'primevue/avatar'
import { useAuthStore } from '@/stores/auth'

const emit = defineEmits<{
  (e: 'toggle-sidebar'): void
}>()

const route = useRoute()
const authStore = useAuthStore()

const pageTitle = computed(() => {
  const titles: Record<string, string> = {
    '/dashboard': 'Dashboard',
    '/profile-entry': 'Profile Entry'
  }
  return titles[route.path] || 'Windx'
})
</script>

<style scoped>
.windx-header {
  border-bottom: 1px solid #e2e8f0;
  background: white;
}
</style>
