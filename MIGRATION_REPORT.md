# Frontend Migration Report: Jinja2/Alpine.js → Vue.js

**Project:** Windx Configurator System  
**Date:** 2026-01-25  
**Migration Type:** Complete frontend rewrite from server-side templates to Vue.js SPA

---

## Table of Contents

1. [What Was Deleted](#what-was-deleted)
2. [Vue.js Implementation Strategy](#vuejs-implementation-strategy)
3. [File-by-File Migration Guide](#file-by-file-migration-guide)
4. [Architecture Changes](#architecture-changes)
5. [Implementation Roadmap](#implementation-roadmap)

---

## What Was Deleted

### 1. Template Engine Infrastructure

**Deleted:**
- `app/templates/` - All Jinja2 HTML templates
- `app/static/` - Legacy static assets (partially)
- `app/core/rbac_template_helpers.py` - Template-specific RBAC helpers

**Why:** Server-side rendering is replaced by client-side Vue.js components. The backend now serves only JSON APIs.

### 2. HTML Endpoint Files

**Deleted:**
- `app/api/v1/endpoints/admin_orders.py`
- `app/api/v1/endpoints/admin_relations.py`
- `app/api/v1/endpoints/admin_entry.py`
- `app/api/v1/endpoints/admin_hierarchy.py`
- `app/api/v1/endpoints/admin_settings.py`
- `app/api/v1/endpoints/admin_documentation.py`
- `app/api/v1/endpoints/admin_customers.py`
- `app/api/v1/endpoints/admin_manufacturing.py`
- `app/api/v1/endpoints/admin_auth.py`

**Why:** These files returned `HTMLResponse` objects. The JSON API endpoints in files like `orders.py`, `customers.py`, etc. remain and will be consumed by Vue.js.

### 3. Mixed-Content Endpoints (Cleaned)

**Modified (HTML parts removed):**
- `app/api/v1/endpoints/entry.py` - Removed `profile_page`, `accessories_page`, `glazing_page`
- `app/api/v1/endpoints/dashboard.py` - Removed HTML dashboard endpoints, kept `/stats` JSON API

**Kept:** All JSON API endpoints for data operations.

### 4. Legacy JavaScript Files (Deleted)

**Files requiring major rewrite:**
- `app/static/js/_profile/_window.js` - Direct DOM manipulation for modals and image uploads
- `app/static/js/_profile/TableEditor.js` - Manual table cell editing via DOM selectors
- `app/static/js/_profile/ImageHandler.js` - Window-based image handling
- `app/static/js/_profile/ConfigurationSaver.js` - Mixed with API logic

**Why:** These files directly manipulate the DOM using vanilla JavaScript patterns that conflict with Vue's reactive system.

### 5. Monolithic CSS Files (To Be Split)

**Files requiring refactoring:**
- `app/static/css/profile-entry.css` (73KB) - Mix of global layout and component-specific styles
- `app/static/css/relations.css` - Template-specific styles
- `app/static/css/admin.css` (17KB) - Some parts reusable, others template-specific

---

## Vue.js Implementation Strategy

### Core Principles

1. **Component-Based Architecture**: Each UI element becomes a reusable Vue component
2. **Reactive State Management**: Pinia stores replace manual DOM updates
3. **API Service Layer**: Centralized API calls using Axios
4. **Vue Router**: Client-side routing replaces server redirects
5. **Scoped Styling**: Component-specific CSS using `<style scoped>`

### Technology Stack

```
Frontend Framework: Vue 3 (Composition API)
State Management: Pinia
Routing: Vue Router 4
HTTP Client: Axios
UI Framework: Tailwind CSS (or keep existing CSS variables)
Build Tool: Vite
Type Safety: TypeScript (optional but recommended)
```

---

## File-by-File Migration Guide

### 1. `_window.js` → Vue Components

**What it did:**
```javascript
// Created modal overlays manually
window.openImageModal = function(imageSrc) {
    const modal = document.createElement('div');
    modal.innerHTML = `<div>...</div>`;
    document.body.appendChild(modal);
};

// Handled inline image uploads
window.handleInlineImageChange = function(rowId, field, event) {
    const file = event.target.files[0];
    // Manual FormData upload
    // Manual Alpine.js state updates
};
```

**Vue.js Implementation:**

**File:** `frontend/src/components/ImageModal.vue`
```vue
<template>
  <Teleport to="body">
    <div v-if="isOpen" class="modal-overlay" @click.self="close">
      <div class="modal-content">
        <button @click="close" class="close-btn">×</button>
        <img :src="imageSrc" alt="Preview" />
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref } from 'vue';

const props = defineProps({
  imageSrc: String,
  isOpen: Boolean
});

const emit = defineEmits(['close']);

const close = () => emit('close');
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.75);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
}
</style>
```

**File:** `frontend/src/components/ImageUpload.vue`
```vue
<template>
  <div class="image-upload">
    <input 
      type="file" 
      @change="handleFileChange" 
      accept="image/*"
      ref="fileInput"
    />
    <img v-if="previewUrl" :src="previewUrl" @click="openModal" />
  </div>
</template>

<script setup>
import { ref } from 'vue';
import { useImageUpload } from '@/composables/useImageUpload';

const props = defineProps({
  rowId: Number,
  fieldName: String
});

const emit = defineEmits(['uploaded']);

const { uploadImage, previewUrl, isUploading } = useImageUpload();

const handleFileChange = async (event) => {
  const file = event.target.files[0];
  if (!file) return;
  
  const result = await uploadImage(file, props.rowId, props.fieldName);
  if (result.success) {
    emit('uploaded', result.url);
  }
};
</script>
```

**File:** `frontend/src/composables/useImageUpload.js`
```javascript
import { ref } from 'vue';
import { apiClient } from '@/services/api';

export function useImageUpload() {
  const previewUrl = ref(null);
  const isUploading = ref(false);

  const uploadImage = async (file, rowId, fieldName) => {
    // Validation
    if (!file.type.startsWith('image/')) {
      throw new Error('Please select an image file');
    }
    if (file.size > 5 * 1024 * 1024) {
      throw new Error('Image must be smaller than 5MB');
    }

    isUploading.value = true;
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await apiClient.post('/api/v1/entry/upload-image', formData);
      previewUrl.value = response.data.url;
      return { success: true, url: response.data.url, filename: response.data.filename };
    } catch (error) {
      console.error('Upload failed:', error);
      return { success: false, error: error.message };
    } finally {
      isUploading.value = false;
    }
  };

  return { uploadImage, previewUrl, isUploading };
}
```

---

### 2. `TableEditor.js` → Vue Data Table Component

**What it did:**
```javascript
// Manual DOM manipulation for inline editing
static saveInlineEdit(rowId, field, newValue, originalValue, pendingEdits, savedConfigurations) {
    const updatedPendingEdits = { ...pendingEdits };
    updatedPendingEdits[rowId][field] = newValue;
    
    const updatedConfigurations = [...savedConfigurations];
    const row = updatedConfigurations.find(r => r.id === rowId);
    row[field] = newValue;
}

// Manual API calls
static async commitTableChanges(pendingEdits) {
    for (const [rowId, edits] of Object.entries(pendingEdits)) {
        await fetch(`/api/v1/admin/entry/profile/preview/${rowId}/update-cell`, {...});
    }
}
```

**Vue.js Implementation:**

**File:** `frontend/src/components/ConfigurationTable.vue`
```vue
<template>
  <div class="table-container">
    <table>
      <thead>
        <tr>
          <th v-for="header in headers" :key="header">{{ header }}</th>
          <th class="sticky">Actions</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in configurations" :key="row.id">
          <td 
            v-for="header in headers" 
            :key="header"
            @dblclick="startEdit(row.id, header)"
          >
            <input 
              v-if="isEditing(row.id, header)"
              v-model="editValue"
              @blur="saveEdit(row.id, header)"
              @keyup.enter="saveEdit(row.id, header)"
              @keyup.esc="cancelEdit"
              ref="editInput"
            />
            <span v-else>{{ row[header] }}</span>
          </td>
          <td class="sticky">
            <button @click="deleteRow(row.id)">🗑️</button>
          </td>
        </tr>
      </tbody>
    </table>
    
    <div v-if="hasPendingChanges" class="save-bar">
      <button @click="commitChanges" :disabled="isSaving">
        {{ isSaving ? 'Saving...' : `Save ${pendingCount} changes` }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';
import { useConfigurationStore } from '@/stores/configuration';

const props = defineProps({
  configurations: Array,
  headers: Array
});

const store = useConfigurationStore();

const editingCell = ref(null);
const editValue = ref('');
const editInput = ref(null);

const isEditing = (rowId, header) => {
  return editingCell.value?.rowId === rowId && editingCell.value?.header === header;
};

const startEdit = (rowId, header) => {
  const row = props.configurations.find(r => r.id === rowId);
  editingCell.value = { rowId, header };
  editValue.value = row[header];
  
  // Focus input on next tick
  nextTick(() => editInput.value?.focus());
};

const saveEdit = async (rowId, header) => {
  await store.updateCell(rowId, header, editValue.value);
  editingCell.value = null;
};

const cancelEdit = () => {
  editingCell.value = null;
};

const deleteRow = async (rowId) => {
  if (confirm('Delete this configuration?')) {
    await store.deleteConfiguration(rowId);
  }
};

const commitChanges = async () => {
  await store.commitPendingChanges();
};

const hasPendingChanges = computed(() => store.pendingEdits.size > 0);
const pendingCount = computed(() => store.pendingEdits.size);
const isSaving = computed(() => store.isSaving);
</script>
```

**File:** `frontend/src/stores/configuration.js` (Pinia Store)
```javascript
import { defineStore } from 'pinia';
import { apiClient } from '@/services/api';

export const useConfigurationStore = defineStore('configuration', {
  state: () => ({
    configurations: [],
    pendingEdits: new Map(),
    isSaving: false
  }),

  actions: {
    async loadConfigurations(manufacturingTypeId) {
      const response = await apiClient.get(`/api/v1/entry/profile/previews/${manufacturingTypeId}`);
      this.configurations = response.data.rows;
    },

    updateCell(rowId, field, value) {
      // Update local state immediately
      const row = this.configurations.find(r => r.id === rowId);
      if (row) {
        row[field] = value;
      }

      // Track pending change
      if (!this.pendingEdits.has(rowId)) {
        this.pendingEdits.set(rowId, {});
      }
      this.pendingEdits.get(rowId)[field] = value;
    },

    async commitPendingChanges() {
      this.isSaving = true;
      const errors = [];

      for (const [rowId, edits] of this.pendingEdits.entries()) {
        for (const [field, value] of Object.entries(edits)) {
          try {
            await apiClient.patch(`/api/v1/entry/profile/preview/${rowId}/update-cell`, {
              field,
              value
            });
          } catch (error) {
            errors.push({ rowId, field, error: error.message });
          }
        }
      }

      if (errors.length === 0) {
        this.pendingEdits.clear();
      }

      this.isSaving = false;
      return { success: errors.length === 0, errors };
    },

    async deleteConfiguration(rowId) {
      await apiClient.delete(`/api/v1/entry/profile/configuration/${rowId}`);
      this.configurations = this.configurations.filter(r => r.id !== rowId);
    }
  }
});
```

---

### 3. `DataLoader.js` → API Service + Pinia Store

**What it did:**
```javascript
static async loadManufacturingTypes() {
    const response = await fetch('/api/v1/manufacturing-types/', {
        credentials: 'include'
    });
    const data = await response.json();
    return data.items || [];
}

static async loadSchema(manufacturingTypeId, pageType = 'profile') {
    const url = `/api/v1/entry/profile/schema/${manufacturingTypeId}?page_type=${pageType}`;
    const response = await fetch(url, { credentials: 'include' });
    return await response.json();
}
```

**Vue.js Implementation:**

**File:** `frontend/src/services/api.js`
```javascript
import axios from 'axios';

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '',
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json'
  }
});

// Request interceptor for auth token
apiClient.interceptors.request.use(config => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor for error handling
apiClient.interceptors.response.use(
  response => response,
  error => {
    if (error.response?.status === 401) {
      // Redirect to login
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);
```

**File:** `frontend/src/services/manufacturingTypeService.js`
```javascript
import { apiClient } from './api';

export const manufacturingTypeService = {
  async getAll() {
    const response = await apiClient.get('/api/v1/manufacturing-types/');
    return response.data.items || [];
  },

  async getById(id) {
    const response = await apiClient.get(`/api/v1/manufacturing-types/${id}`);
    return response.data;
  },

  async getSchema(manufacturingTypeId, pageType = 'profile') {
    const response = await apiClient.get(
      `/api/v1/entry/profile/schema/${manufacturingTypeId}`,
      { params: { page_type: pageType } }
    );
    return response.data;
  },

  async getHeaders(manufacturingTypeId, pageType = 'profile') {
    const response = await apiClient.get(
      `/api/v1/entry/profile/headers/${manufacturingTypeId}`,
      { params: { page_type: pageType } }
    );
    return response.data;
  }
};
```

**File:** `frontend/src/stores/manufacturingType.js`
```javascript
import { defineStore } from 'pinia';
import { manufacturingTypeService } from '@/services/manufacturingTypeService';

export const useManufacturingTypeStore = defineStore('manufacturingType', {
  state: () => ({
    types: [],
    currentType: null,
    schema: null,
    headers: [],
    isLoading: false,
    error: null
  }),

  getters: {
    activeTypes: (state) => state.types.filter(t => t.is_active)
  },

  actions: {
    async loadTypes() {
      this.isLoading = true;
      try {
        this.types = await manufacturingTypeService.getAll();
      } catch (error) {
        this.error = error.message;
      } finally {
        this.isLoading = false;
      }
    },

    async loadSchema(manufacturingTypeId, pageType = 'profile') {
      this.isLoading = true;
      try {
        this.schema = await manufacturingTypeService.getSchema(manufacturingTypeId, pageType);
        this.headers = await manufacturingTypeService.getHeaders(manufacturingTypeId, pageType);
      } catch (error) {
        this.error = error.message;
      } finally {
        this.isLoading = false;
      }
    },

    setCurrentType(typeId) {
      this.currentType = this.types.find(t => t.id === typeId);
    }
  }
});
```

---

### 4. `FormHelpers.js` → Vue Utilities + Composables

**What to keep:**
- `getPreviewValue()` - Formatting logic
- `prepareSaveData()` - Data transformation
- `getFieldUnit()` - Unit mapping

**What to rewrite:**
- `getUIComponent()` - Not needed (Vue uses components directly)
- `fetchHeaderMapping()` - Move to API service

**File:** `frontend/src/utils/formatters.js`
```javascript
export function getPreviewValue(header, formData, fieldVisibility, headerMapping) {
  const fieldName = headerMapping[header];
  if (!fieldName) return 'N/A';

  const value = formData[fieldName];

  if (fieldVisibility[fieldName] === false) {
    return 'N/A';
  }

  if (value === null || value === undefined || value === '') {
    return 'N/A';
  }

  if (typeof value === 'boolean') {
    return value ? 'yes' : 'no';
  }

  if (Array.isArray(value)) {
    return value.length > 0 ? value.join(', ') : 'N/A';
  }

  if (typeof value === 'number') {
    if (fieldName.includes('price')) {
      return value.toFixed(2);
    }
    if (fieldName.includes('percentage') || fieldName.includes('discount')) {
      return value + '%';
    }
  }

  return String(value);
}

export function getFieldUnit(fieldName) {
  const unitMap = {
    'length_of_beam': 'm',
    'width': 'mm',
    'total_width': 'mm',
    'flyscreen_track_height': 'mm',
    // ... rest of mapping
  };
  return unitMap[fieldName] || '';
}

export function prepareSaveData(formData, manufacturingTypeId, schema, fieldVisibility) {
  const saveData = {
    ...formData,
    manufacturing_type_id: manufacturingTypeId
  };

  // Remove hidden fields
  if (schema) {
    for (const section of schema.sections) {
      for (const field of section.fields) {
        if (fieldVisibility[field.name] === false) {
          delete saveData[field.name];
        }
      }
    }
  }

  // Convert empty strings to null
  Object.keys(saveData).forEach(key => {
    if (saveData[key] === '') {
      saveData[key] = null;
    }
  });

  return saveData;
}
```

---

### 5. CSS Migration Strategy

**`admin.css` (17KB) → Split into:**

1. **Global Variables** → `frontend/src/assets/css/variables.css`
```css
:root {
  --primary: #2563eb;
  --primary-hover: #1d4ed8;
  --secondary: #64748b;
  --background: #f8fafc;
  --surface: #ffffff;
  --text: #0f172a;
  --text-light: #64748b;
  --border: #e2e8f0;
  --success: #10b981;
  --error: #ef4444;
  --warning: #f59e0b;
  --info: #3b82f6;
}
```

2. **Layout Components** → `frontend/src/components/layout/Sidebar.vue`
```vue
<style scoped>
.sidebar {
  width: 260px;
  background-color: var(--surface);
  border-right: 1px solid var(--border);
  position: fixed;
  height: 100vh;
  transition: width 0.3s ease-in-out;
}

.sidebar.collapsed {
  width: 70px;
}
</style>
```

3. **Utility Classes** → `frontend/src/assets/css/utilities.css`
```css
.btn {
  display: inline-flex;
  align-items: center;
  padding: 0.625rem 1.25rem;
  border-radius: 0.5rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-primary {
  background-color: var(--primary);
  color: white;
}
```

**`profile-entry.css` (73KB) → Component-Scoped Styles:**

Each Vue component gets its own `<style scoped>` block:

```vue
<!-- ProfileEntryForm.vue -->
<style scoped>
.field-item {
  margin-bottom: 1.5rem;
  padding: 1rem;
  background: white;
  border-radius: 0.5rem;
}

.field-item.error {
  border-left: 4px solid var(--error);
  background-color: #fef2f2;
}
</style>
```

---

## Architecture Changes

### Before (Jinja2 + Alpine.js)

```
┌─────────────────────────────────────┐
│  FastAPI Backend                    │
│  ├─ Jinja2 Templates (HTML)         │
│  ├─ Static Files (CSS/JS)           │
│  └─ API Endpoints (JSON)            │
└─────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│  Browser                             │
│  ├─ Rendered HTML                   │
│  ├─ Alpine.js (reactive data)       │
│  └─ Vanilla JS (DOM manipulation)   │
└─────────────────────────────────────┘
```

### After (Vue.js SPA)

```
┌─────────────────────────────────────┐
│  FastAPI Backend (JSON API Only)    │
│  ├─ /api/v1/manufacturing-types/    │
│  ├─ /api/v1/configurations/         │
│  ├─ /api/v1/quotes/                 │
│  └─ /api/v1/orders/                 │
└─────────────────────────────────────┘
         │ JSON
         ▼
┌─────────────────────────────────────┐
│  Vue.js Frontend (SPA)               │
│  ├─ Components (UI)                 │
│  ├─ Pinia Stores (State)            │
│  ├─ Vue Router (Navigation)         │
│  ├─ API Services (HTTP)             │
│  └─ Composables (Logic)             │
└─────────────────────────────────────┘
```

---

## Implementation Roadmap

### Phase 1: Project Setup (Week 1)
- [ ] Initialize Vue 3 project with Vite
- [ ] Install dependencies (Pinia, Vue Router, Axios)
- [ ] Setup Tailwind CSS or port existing CSS variables
- [ ] Configure API base URL and environment variables
- [ ] Setup authentication flow (login/logout)

### Phase 2: Core Components (Week 2-3)
- [ ] Create layout components (Sidebar, Header, Footer)
- [ ] Implement routing structure
- [ ] Build authentication pages (Login, Register)
- [ ] Create dashboard page with stats

### Phase 3: Configuration System (Week 4-5)
- [ ] Port `ConditionEvaluator`, `FormValidator`, `BusinessRulesEngine` to utils
- [ ] Build dynamic form generator component
- [ ] Implement configuration table with inline editing
- [ ] Add image upload component
- [ ] Create search/filter functionality

### Phase 4: Business Features (Week 6-7)
- [ ] Manufacturing types management
- [ ] Customer management
- [ ] Quote generation
- [ ] Order management
- [ ] Template system

### Phase 5: Polish & Testing (Week 8)
- [ ] Error handling and validation
- [ ] Loading states and skeletons
- [ ] Responsive design
- [ ] E2E testing
- [ ] Performance optimization

---

## Key Takeaways

1. **No More DOM Manipulation**: Vue's reactive system handles all UI updates automatically
2. **Centralized State**: Pinia stores replace scattered state management
3. **Type Safety**: Consider TypeScript for better developer experience
4. **Reusable Logic**: Composables replace utility classes and global functions
5. **Component Isolation**: Each component is self-contained with scoped styles

---

## Next Steps

1. **Initialize Vue Project**: `npm create vite@latest frontend -- --template vue`
2. **Port Reusable JS**: Copy `ConditionEvaluator.js`, `FormValidator.js`, `BusinessRulesEngine.js` to `src/utils/`
3. **Setup API Client**: Create Axios instance with interceptors
4. **Build Layout**: Start with Sidebar and main layout components
5. **Implement Auth**: Login page and token management

---

**End of Report**
