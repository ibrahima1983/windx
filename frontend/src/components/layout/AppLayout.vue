<template>
  <div class="app-layout">
    <Toast />
    <ConfirmDialog />

    <Sidebar
      :visible="sidebarVisible"
      @update:visible="sidebarVisible = $event"
    />

    <div
      class="app-content"
      :class="{ 'sidebar-hidden': !sidebarVisible }"
    >
      <Header @toggle-sidebar="sidebarVisible = !sidebarVisible" />

      <main class="app-main">
        <PageContainer>
          <slot />
        </PageContainer>
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
import PageContainer from './PageContainer.vue'

const sidebarVisible = ref(true)
</script>

<style scoped>
/* Root layout */
.app-layout {
  display: flex;
  min-height: 100vh;
  background-color: #f8fafc; /* slate-50 */
}

/* Right side (header + content) */
.app-content {
  display: flex;
  flex-direction: column;
  flex: 1;

  transition: margin 0.3s ease-in-out;
}

/* When sidebar is hidden on desktop */
@media (min-width: 768px) {
  .app-content.sidebar-hidden {
    margin-left: 0;
  }
}

/* Main scrollable area */
.app-main {
  flex: 1;
  width: 100%;
  background-color: #f8fafc;
}
</style>
