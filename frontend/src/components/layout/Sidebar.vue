<template>
  <PrimeSidebar 
    v-model:visible="isVisible"
    :showCloseIcon="false"
    class="windx-sidebar"
  >
    <template #header>
      <div class="sidebar-header">
        <i class="pi pi-th-large text-2xl text-primary"></i>
        <span class="font-bold text-xl ml-2">Windx</span>
      </div>
    </template>

    <PanelMenu :model="menuItems" class="w-full border-none" />

    <template #footer>
      <div class="sidebar-footer">
        <div class="user-info" v-if="authStore.user">
          <i class="pi pi-user"></i>
          <span class="ml-2">{{ authStore.user.username }}</span>
        </div>
        <Button 
          label="Logout" 
          icon="pi pi-sign-out" 
          @click="handleLogout"
          text
          class="w-full"
        />
      </div>
    </template>
  </PrimeSidebar>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import PrimeSidebar from 'primevue/sidebar'
import PanelMenu from 'primevue/panelmenu'
import Button from 'primevue/button'
import { useAuthStore } from '@/stores/auth'
import { useDebugLogger } from '@/composables/useDebugLogger'

const props = defineProps<{
  visible: boolean
}>()

const emit = defineEmits<{
  (e: 'update:visible', value: boolean): void
}>()

const router = useRouter()
const authStore = useAuthStore()
const logger = useDebugLogger('Sidebar')

const isVisible = computed({
  get: () => props.visible,
  set: (value) => emit('update:visible', value)
})

const menuItems = ref([
  {
    label: 'Dashboard',
    icon: 'pi pi-home',
    command: () => router.push('/dashboard')
  },
  {
    label: 'Profile Entry',
    icon: 'pi pi-file-edit',
    command: () => router.push('/profile-entry')
  }
])

function handleLogout() {
  logger.info('User logging out')
  authStore.logout()
  router.push('/login')
}
</script>

<style scoped>
.windx-sidebar {
  width: 260px;
}

.sidebar-header {
  display: flex;
  align-items: center;
  padding: 1rem;
}

.sidebar-footer {
  padding: 1rem;
  border-top: 1px solid #e2e8f0;
}

.user-info {
  display: flex;
  align-items: center;
  padding: 0.75rem;
  margin-bottom: 0.5rem;
  background: #f8fafc;
  border-radius: 0.5rem;
}
</style>
