<template>
  <div class="app-layout">
    <Toast />
    <ConfirmDialog />
    
    <Sidebar :visible="sidebarVisible" @update:visible="sidebarVisible = $event" />
    
    <div class="main-content" :class="{ 'sidebar-open': sidebarVisible }">
      <Header @toggle-sidebar="sidebarVisible = !sidebarVisible" />
      
      <main class="content-area">
        <slot />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import Toast from 'primevue/toast'
import ConfirmDialog from 'primevue/confirmdialog'
import Sidebar from './Sidebar.vue'
import Header from './Header.vue'

const sidebarVisible = ref(true)
</script>

<style scoped>
.app-layout {
  display: flex;
  min-height: 100vh;
  background-color: #f8fafc;
}

.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  transition: margin-left 0.3s ease;
}

.content-area {
  flex: 1;
  padding: 1.5rem;
}

@media (max-width: 768px) {
  .main-content {
    margin-left: 0 !important;
  }
}
</style>
