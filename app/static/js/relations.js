/**
 * Relations Manager - Single Step Approach
 * 
 * Manages hierarchical option dependencies:
 * - Material, Opening System, Color: Independent entities
 * - Company: Links to Material
 * - System Series: Links to Company→Material, Opening System, Colors (creates paths)
 */

const RelationsManager = {
    // API endpoints
    API_BASE: '/api/v1/admin/relations',
    IMAGE_UPLOAD_URL: '/api/v1/admin/entry/upload-image',
    
    // Local cache of entities (loaded from server)
    entities: {
        material: [],
        opening_system: [],
        color: [],
        company: [],
        system_series: []
    },
    
    // Company-Material links (derived from paths)
    companyMaterialLinks: [],
    
    // All paths from server
    paths: [],
    
    // Selected colors for system_series (multi-select)
    selectedColors: [],
    
    // Image file for upload
    imageFile: null,

    /**
     * Initialize the Relations Manager
     */
    async init() {
        console.log('🔗 [RELATIONS] Initializing...');
        await this.loadAllData();
        this.setupDragAndDrop();
        console.log('🔗 [RELATIONS] Initialized');
    },

    /**
     * Load all entities and paths from server
     */
    async loadAllData() {
        try {
            // Load entities for each type
            for (const type of Object.keys(this.entities)) {
                const response = await fetch(`${this.API_BASE}/entities/${type}`);
                const data = await response.json();
                if (data.success) {
                    this.entities[type] = data.entities;
                }
            }
            
            // Load paths
            const pathsResponse = await fetch(`${this.API_BASE}/paths`);
            const pathsData = await pathsResponse.json();
            if (pathsData.success) {
                this.paths = pathsData.paths;
                this.deriveCompanyMaterialLinks();
            }
            
            console.log('🔗 [RELATIONS] Data loaded:', this.entities, this.paths);
        } catch (error) {
            console.error('🔗 [RELATIONS] Error loading data:', error);
        }
    },

    /**
     * Derive company-material links from paths AND company metadata
     */
    deriveCompanyMaterialLinks() {
        const linkSet = new Set();
        this.companyMaterialLinks = [];
        
        // From paths
        for (const path of this.paths) {
            const key = `${path.company_id}:${path.material_id}`;
            if (!linkSet.has(key)) {
                linkSet.add(key);
                this.companyMaterialLinks.push({
                    companyId: path.company_id,
                    materialId: path.material_id
                });
            }
        }
        
        // From company metadata (for companies not yet in paths)
        for (const company of this.entities.company) {
            const rules = company.validation_rules || {};
            if (rules.linked_material_id) {
                const key = `${company.id}:${rules.linked_material_id}`;
                if (!linkSet.has(key)) {
                    linkSet.add(key);
                    this.companyMaterialLinks.push({
                        companyId: company.id,
                        materialId: rules.linked_material_id
                    });
                }
            }
        }
    },

    /**
     * Show tab
     */
    showTab(tab) {
        // Hide all tab contents
        document.querySelectorAll('[id^="tab-content-"]').forEach(el => el.classList.add('hidden'));
        // Deactivate all tab buttons
        document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
        
        // Show selected tab
        document.getElementById(`tab-content-${tab}`).classList.remove('hidden');
        document.querySelector(`.tab-btn[data-tab="${tab}"]`).classList.add('active');
        
        if (tab === 'view') {
            this.refreshViewTab();
        }
    },

    /**
     * Update entity form based on selected type
     */
    updateEntityForm() {
        const type = document.getElementById('entityType').value;
        const form = document.getElementById('entityForm');
        
        // Hide all extra field sections
        document.getElementById('materialFields').classList.add('hidden');
        document.getElementById('seriesFields').classList.add('hidden');
        document.getElementById('colorFields').classList.add('hidden');
        document.getElementById('companyLinks').classList.add('hidden');
        document.getElementById('seriesLinks').classList.add('hidden');
        
        // Reset
        this.selectedColors = [];
        document.getElementById('colorChips').innerHTML = '';
        this.imageFile = null;
        this.resetImagePreview();
        
        if (!type) {
            form.classList.add('hidden');
            return;
        }
        
        form.classList.remove('hidden');
        this.clearForm();
        
        // Show type-specific fields
        if (type === 'material') {
            document.getElementById('materialFields').classList.remove('hidden');
        } else if (type === 'system_series') {
            document.getElementById('seriesFields').classList.remove('hidden');
            document.getElementById('seriesLinks').classList.remove('hidden');
            this.populateCompanyMaterialDropdown();
            this.populateOpeningDropdown();
            this.populateColorDropdown();
        } else if (type === 'color') {
            document.getElementById('colorFields').classList.remove('hidden');
        } else if (type === 'company') {
            document.getElementById('companyLinks').classList.remove('hidden');
            this.populateMaterialDropdown();
        }
        
        document.getElementById('entityName').focus();
    },

    /**
     * Clear form fields
     */
    clearForm() {
        document.getElementById('entityName').value = '';
        document.getElementById('entityPrice').value = '';
        document.getElementById('entityDescription').value = '';
        document.getElementById('materialDensity').value = '';
        document.getElementById('seriesWidth').value = '';
        document.getElementById('seriesChambers').value = '';
        document.getElementById('seriesUValue').value = '';
        document.getElementById('seriesSeals').value = '';
        document.getElementById('seriesCharacteristics').value = '';
        document.getElementById('colorCode').value = '';
        document.getElementById('colorLamination').value = 'false';
    },

    /**
     * Populate material dropdown for company linking
     */
    populateMaterialDropdown() {
        const select = document.getElementById('companyMaterial');
        select.innerHTML = '<option value="">Select material...</option>';
        this.entities.material.forEach(m => {
            select.innerHTML += `<option value="${m.id}">${m.name}</option>`;
        });
    },

    /**
     * Populate combined Company → Material dropdown for System Series
     */
    populateCompanyMaterialDropdown() {
        const select = document.getElementById('seriesCompanyMaterial');
        select.innerHTML = '<option value="">Select company → material...</option>';
        
        if (this.companyMaterialLinks.length === 0) {
            select.innerHTML = '<option value="">No company-material links yet</option>';
            return;
        }
        
        this.companyMaterialLinks.forEach(link => {
            const company = this.entities.company.find(c => c.id === link.companyId);
            const material = this.entities.material.find(m => m.id === link.materialId);
            if (company && material) {
                select.innerHTML += `<option value="${link.companyId}:${link.materialId}">${company.name} → ${material.name}</option>`;
            }
        });
    },

    /**
     * Populate opening system dropdown
     */
    populateOpeningDropdown() {
        const select = document.getElementById('seriesOpening');
        select.innerHTML = '<option value="">Select opening system...</option>';
        this.entities.opening_system.forEach(o => {
            select.innerHTML += `<option value="${o.id}">${o.name}</option>`;
        });
    },

    /**
     * Populate color dropdown (excluding already selected)
     */
    populateColorDropdown() {
        const select = document.getElementById('seriesColors');
        select.innerHTML = '<option value="">Select colors...</option>';
        this.entities.color.forEach(c => {
            if (!this.selectedColors.includes(c.id)) {
                select.innerHTML += `<option value="${c.id}">${c.name}</option>`;
            }
        });
    },

    /**
     * Add color chip (multi-select)
     */
    addColorChip() {
        const select = document.getElementById('seriesColors');
        const colorId = parseInt(select.value);
        if (!colorId) return;
        
        const color = this.entities.color.find(c => c.id === colorId);
        if (!color || this.selectedColors.includes(colorId)) return;
        
        this.selectedColors.push(colorId);
        this.renderColorChips();
        this.populateColorDropdown();
        select.value = '';
    },

    /**
     * Remove color chip
     */
    removeColorChip(colorId) {
        this.selectedColors = this.selectedColors.filter(id => id !== colorId);
        this.renderColorChips();
        this.populateColorDropdown();
    },

    /**
     * Render color chips
     */
    renderColorChips() {
        const container = document.getElementById('colorChips');
        container.innerHTML = this.selectedColors.map(id => {
            const color = this.entities.color.find(c => c.id === id);
            return `<span class="chip">
                <i class="fa-solid fa-palette" style="color: #db2777;"></i> ${color.name}
                <span class="remove" onclick="RelationsManager.removeColorChip(${id})">×</span>
            </span>`;
        }).join('');
    },


    /**
     * Setup drag and drop for image upload
     */
    setupDragAndDrop() {
        const box = document.querySelector('.image-upload-box');
        if (!box) return;
        
        box.addEventListener('dragover', (e) => {
            e.preventDefault();
            box.style.borderColor = '#3b82f6';
            box.style.backgroundColor = '#eff6ff';
        });
        
        box.addEventListener('dragleave', (e) => {
            e.preventDefault();
            box.style.borderColor = '';
            box.style.backgroundColor = '';
        });
        
        box.addEventListener('drop', (e) => {
            e.preventDefault();
            box.style.borderColor = '';
            box.style.backgroundColor = '';
            
            const file = e.dataTransfer.files[0];
            if (file && file.type.startsWith('image/')) {
                this.processImageFile(file);
            }
        });
    },

    /**
     * Handle image file selection
     */
    handleImageSelect(event) {
        const file = event.target.files[0];
        if (file && file.type.startsWith('image/')) {
            this.processImageFile(file);
        }
    },

    /**
     * Process image file
     */
    processImageFile(file) {
        this.imageFile = file;
        
        const reader = new FileReader();
        reader.onload = (event) => {
            const preview = document.getElementById('imagePreview');
            const placeholder = document.getElementById('imagePlaceholder');
            const overlay = document.getElementById('imageOverlay');
            const clearBtn = document.getElementById('clearImageBtn');
            
            preview.src = event.target.result;
            preview.classList.remove('hidden');
            placeholder.classList.add('hidden');
            overlay.classList.remove('hidden');
            if (clearBtn) clearBtn.classList.remove('hidden');
        };
        reader.readAsDataURL(file);
    },

    /**
     * Reset image preview
     */
    resetImagePreview() {
        const preview = document.getElementById('imagePreview');
        const placeholder = document.getElementById('imagePlaceholder');
        const overlay = document.getElementById('imageOverlay');
        const input = document.getElementById('entityImage');
        const clearBtn = document.getElementById('clearImageBtn');
        
        if (preview) {
            preview.src = '';
            preview.classList.add('hidden');
        }
        if (placeholder) placeholder.classList.remove('hidden');
        if (overlay) overlay.classList.add('hidden');
        if (input) input.value = '';
        if (clearBtn) clearBtn.classList.add('hidden');
        this.imageFile = null;
    },

    /**
     * Clear image (called from clear button)
     */
    clearImage(event) {
        event.stopPropagation();
        this.resetImagePreview();
    },

    /**
     * Upload image and get URL
     */
    async uploadImage() {
        if (!this.imageFile) return null;
        
        try {
            const formData = new FormData();
            formData.append('file', this.imageFile);
            
            const response = await fetch(this.IMAGE_UPLOAD_URL, {
                method: 'POST',
                body: formData,
                credentials: 'include'
            });
            
            const result = await response.json();
            if (result.success && result.url) {
                return result.url;
            }
            return null;
        } catch (error) {
            console.error('🔗 [RELATIONS] Image upload error:', error);
            return null;
        }
    },

    /**
     * Record entity - main save action
     */
    async recordEntity() {
        const type = document.getElementById('entityType').value;
        const name = document.getElementById('entityName').value.trim();
        const price = document.getElementById('entityPrice').value;
        const description = document.getElementById('entityDescription').value.trim();

        if (!type || !name) {
            this.showToast('Please select a type and enter a name', 'error');
            return;
        }

        // Build entity data
        const data = {
            entity_type: type,
            name: name,
            price_from: price ? parseFloat(price) : null,
            description: description || null,
            metadata: {}
        };

        // Upload image if selected
        if (this.imageFile) {
            const imageUrl = await this.uploadImage();
            if (imageUrl) {
                data.image_url = imageUrl;
            }
        }

        // Add type-specific metadata
        if (type === 'material') {
            const density = document.getElementById('materialDensity').value;
            if (density) data.metadata.density = parseFloat(density);
        } else if (type === 'system_series') {
            const width = document.getElementById('seriesWidth').value;
            const chambers = document.getElementById('seriesChambers').value;
            const uValue = document.getElementById('seriesUValue').value;
            const seals = document.getElementById('seriesSeals').value;
            const chars = document.getElementById('seriesCharacteristics').value;
            
            if (width) data.metadata.width = parseFloat(width);
            if (chambers) data.metadata.number_of_chambers = parseInt(chambers);
            if (uValue) data.metadata.u_value = parseFloat(uValue);
            if (seals) data.metadata.number_of_seals = parseInt(seals);
            if (chars) data.metadata.characteristics = chars;
        } else if (type === 'color') {
            const code = document.getElementById('colorCode').value;
            const lamination = document.getElementById('colorLamination').value;
            if (code) data.metadata.code = code;
            data.metadata.has_lamination = lamination === 'true';
        }

        try {
            // Handle Company - must link to material
            if (type === 'company') {
                const materialId = document.getElementById('companyMaterial').value;
                if (!materialId) {
                    this.showToast('Please select a material to link', 'error');
                    return;
                }
                
                // Store linked material in metadata
                data.metadata.linked_material_id = parseInt(materialId);
                
                // Create company entity
                const response = await fetch(`${this.API_BASE}/entities`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });
                const result = await response.json();
                
                if (!response.ok) {
                    this.showToast(this.extractError(result), 'error');
                    return;
                }
                
                const companyId = result.entity.id;
                // Add to local cache with validation_rules containing linked_material_id
                const newCompany = {
                    ...result.entity,
                    validation_rules: { ...result.entity.validation_rules, linked_material_id: parseInt(materialId) }
                };
                this.entities.company.push(newCompany);
                
                // Update company-material links
                this.companyMaterialLinks.push({
                    companyId: companyId,
                    materialId: parseInt(materialId)
                });
                
                const material = this.entities.material.find(m => m.id == materialId);
                this.showToast(`${name} created and linked to ${material.name}`, 'success');
            }
            // Handle System Series - creates paths
            else if (type === 'system_series') {
                const companyMaterialValue = document.getElementById('seriesCompanyMaterial').value;
                const openingId = document.getElementById('seriesOpening').value;
                
                if (!companyMaterialValue || !openingId || this.selectedColors.length === 0) {
                    this.showToast('Please fill all link fields and select at least one color', 'error');
                    return;
                }
                
                // Parse "companyId:materialId" format
                const [companyId, materialId] = companyMaterialValue.split(':').map(Number);
                
                // Create system series entity
                const response = await fetch(`${this.API_BASE}/entities`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });
                const result = await response.json();
                
                if (!response.ok) {
                    this.showToast(this.extractError(result), 'error');
                    return;
                }
                
                const seriesId = result.entity.id;
                this.entities.system_series.push(result.entity);
                
                // Create paths for each selected color
                let pathsCreated = 0;
                for (const colorId of this.selectedColors) {
                    try {
                        const pathResponse = await fetch(`${this.API_BASE}/paths`, {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({
                                company_id: companyId,
                                material_id: materialId,
                                opening_system_id: parseInt(openingId),
                                system_series_id: seriesId,
                                color_id: colorId
                            })
                        });
                        
                        if (pathResponse.ok) {
                            const pathResult = await pathResponse.json();
                            this.paths.push(pathResult.path);
                            pathsCreated++;
                        }
                    } catch (e) {
                        console.error('Error creating path:', e);
                    }
                }
                
                this.deriveCompanyMaterialLinks();
                this.showToast(`${name} created with ${pathsCreated} path(s)`, 'success');
                this.selectedColors = [];
            }
            // Handle independent entities (material, opening_system, color)
            else {
                const response = await fetch(`${this.API_BASE}/entities`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });
                const result = await response.json();
                
                if (!response.ok) {
                    this.showToast(this.extractError(result), 'error');
                    return;
                }
                
                this.entities[type].push(result.entity);
                this.showToast(`${name} added`, 'success');
            }
            
            // Reset form
            this.clearForm();
            this.resetImagePreview();
            document.getElementById('entityName').focus();
            
            // Refresh dropdowns
            if (type === 'company') {
                document.getElementById('companyMaterial').value = '';
            } else if (type === 'system_series') {
                document.getElementById('seriesCompanyMaterial').value = '';
                document.getElementById('seriesOpening').value = '';
                document.getElementById('colorChips').innerHTML = '';
                this.populateColorDropdown();
            }
            
        } catch (error) {
            console.error('🔗 [RELATIONS] Error:', error);
            this.showToast('Network error', 'error');
        }
    },

    /**
     * Extract error message from API response
     */
    extractError(result) {
        if (result.detail) {
            if (typeof result.detail === 'string') {
                return result.detail;
            } else if (result.detail.message) {
                return result.detail.message;
            } else if (Array.isArray(result.detail)) {
                return result.detail.map(e => e.msg || e.message || JSON.stringify(e)).join(', ');
            } else {
                return JSON.stringify(result.detail);
            }
        }
        return 'Unknown error';
    },

    /**
     * Refresh View All tab
     */
    async refreshViewTab() {
        // Reload data from server
        await this.loadAllData();
        
        // Update counts
        document.getElementById('countMaterial').textContent = this.entities.material.length;
        document.getElementById('countOpening').textContent = this.entities.opening_system.length;
        document.getElementById('countColor').textContent = this.entities.color.length;
        document.getElementById('countCompany').textContent = this.entities.company.length;
        document.getElementById('countSeries').textContent = this.entities.system_series.length;
        
        // Company → Material Links
        const linksView = document.getElementById('companyMaterialLinksView');
        if (this.companyMaterialLinks.length === 0) {
            linksView.innerHTML = '<div class="empty-state" style="padding: 24px;">No company-material links yet.</div>';
        } else {
            linksView.innerHTML = this.companyMaterialLinks.map(link => {
                const company = this.entities.company.find(c => c.id === link.companyId);
                const material = this.entities.material.find(m => m.id === link.materialId);
                if (!company || !material) return '';
                return `
                    <div class="link-pill">
                        <span class="company"><i class="fa-solid fa-building"></i> ${company.name}</span>
                        <span class="arrow"><i class="fa-solid fa-arrow-right"></i></span>
                        <span class="material"><i class="fa-solid fa-cubes"></i> ${material.name}</span>
                    </div>
                `;
            }).join('');
        }
        
        // Paths - group by series
        const groupedPaths = {};
        this.paths.forEach(p => {
            const key = `${p.company_id}|${p.material_id}|${p.opening_system_id}|${p.system_series_id}`;
            if (!groupedPaths[key]) {
                groupedPaths[key] = {
                    company_id: p.company_id,
                    material_id: p.material_id,
                    opening_system_id: p.opening_system_id,
                    system_series_id: p.system_series_id,
                    color_ids: [],
                    ltree_paths: []
                };
            }
            groupedPaths[key].color_ids.push(p.color_id);
            groupedPaths[key].ltree_paths.push(p.ltree_path);
        });
        
        const groupedList = Object.values(groupedPaths);
        document.getElementById('totalPaths').textContent = groupedList.length;
        
        const tbody = document.getElementById('pathsTableBody');
        const table = document.getElementById('pathsTable');
        const noPathsYet = document.getElementById('noPathsYet');
        
        if (groupedList.length === 0) {
            noPathsYet.classList.remove('hidden');
            table.classList.add('hidden');
        } else {
            noPathsYet.classList.add('hidden');
            table.classList.remove('hidden');
            
            tbody.innerHTML = groupedList.map(p => {
                const company = this.entities.company.find(c => c.id === p.company_id);
                const material = this.entities.material.find(m => m.id === p.material_id);
                const opening = this.entities.opening_system.find(o => o.id === p.opening_system_id);
                const series = this.entities.system_series.find(s => s.id === p.system_series_id);
                
                const colorBadges = p.color_ids.map(cid => {
                    const color = this.entities.color.find(c => c.id === cid);
                    return color ? `<span class="entity-badge color"><i class="fa-solid fa-palette"></i> ${color.name}</span>` : '';
                }).join(' ');
                
                return `
                    <tr>
                        <td><span class="entity-badge company"><i class="fa-solid fa-building"></i> ${company?.name || 'Unknown'}</span></td>
                        <td><span class="entity-badge material"><i class="fa-solid fa-cubes"></i> ${material?.name || 'Unknown'}</span></td>
                        <td><span class="entity-badge opening"><i class="fa-solid fa-door-open"></i> ${opening?.name || 'Unknown'}</span></td>
                        <td><span class="entity-badge series"><i class="fa-solid fa-layer-group"></i> ${series?.name || 'Unknown'}</span></td>
                        <td>${colorBadges}</td>
                        <td><button class="btn-danger" onclick="RelationsManager.deletePathGroup('${p.ltree_paths.join(',')}')"><i class="fa-solid fa-trash"></i></button></td>
                    </tr>
                `;
            }).join('');
        }
    },

    /**
     * Delete a group of paths
     */
    async deletePathGroup(ltreePathsStr) {
        const ltreePaths = ltreePathsStr.split(',');
        
        for (const ltreePath of ltreePaths) {
            try {
                await fetch(`${this.API_BASE}/paths`, {
                    method: 'DELETE',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ ltree_path: ltreePath })
                });
            } catch (e) {
                console.error('Error deleting path:', e);
            }
        }
        
        this.showToast('Path deleted', 'info');
        this.refreshViewTab();
    },

    /**
     * Show toast notification
     */
    showToast(message, type = 'info') {
        const container = document.getElementById('toastContainer');
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.textContent = message;
        container.appendChild(toast);
        setTimeout(() => {
            toast.style.opacity = '0';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }
};

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => {
    RelationsManager.init();
});
