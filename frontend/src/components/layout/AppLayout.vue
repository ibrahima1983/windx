<template>
  <div class="flex min-h-screen bg-slate-50">
    <Toast />
    <ConfirmDialog />
    
    <Sidebar :visible="sidebarVisible" @update:visible="sidebarVisible = $event" />
    
    <div 
      class="flex flex-1 flex-col transition-[margin] duration-300 ease-in-out pl-0 md:pl-0" 
      :class="{ 'md:ml-0': !sidebarVisible }"
    >
      <Header @toggle-sidebar="sidebarVisible = !sidebarVisible" />
      
      <main class="flex-1 w-full bg-slate-50">
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
