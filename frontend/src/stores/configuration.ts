/**
 * Configuration Store
 * 
 * Manages configuration state and operations
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { configurationService } from '@/services/configurationService'
import { useDebugLogger } from '@/composables/useDebugLogger'
import type { Configuration } from '@/types'

export const useConfigurationStore = defineStore('configuration', () => {
    const logger = useDebugLogger('ConfigurationStore')

    const configurations = ref<Configuration[]>([])
    const currentConfiguration = ref<Configuration | null>(null)
    const pendingEdits = ref<Map<number, Record<string, any>>>(new Map())
    const isLoading = ref(false)
    const error = ref<string | null>(null)

    const hasPendingChanges = computed(() => pendingEdits.value.size > 0)

    async function loadConfigurations(manufacturingTypeId?: number) {
        isLoading.value = true
        error.value = null

        try {
            logger.info('Loading configurations', { manufacturingTypeId })
            const data = await configurationService.getAll({ manufacturing_type_id: manufacturingTypeId })
            configurations.value = data.items || []
            logger.info('Configurations loaded', { count: configurations.value.length })
        } catch (err: any) {
            const msg = err.response?.data?.detail || err.message || 'Failed to load configurations'
            error.value = msg
            logger.error('Failed to load configurations', { error: msg, err })
            throw err
        } finally {
            isLoading.value = false
        }
    }

    async function loadPreviews(manufacturingTypeId: number) {
        isLoading.value = true
        error.value = null

        try {
            logger.info('Loading previews', { manufacturingTypeId })
            const data = await configurationService.getPreviews(manufacturingTypeId)
            configurations.value = data.rows || []
            logger.info('Previews loaded', { count: configurations.value.length })
            return data
        } catch (err: any) {
            const msg = err.response?.data?.detail || err.message || 'Failed to load previews'
            error.value = msg
            logger.error('Failed to load previews', { error: msg, err })
            throw err
        } finally {
            isLoading.value = false
        }
    }

    async function createConfiguration(data: Record<string, any>) {
        isLoading.value = true
        error.value = null

        try {
            logger.info('Creating configuration', { data })
            const result = await configurationService.create(data)
            configurations.value.push(result)
            logger.info('Configuration created', { id: result.id })
            return result
        } catch (err: any) {
            const msg = err.response?.data?.detail || err.message || 'Failed to create configuration'
            error.value = msg
            logger.error('Failed to create configuration', { error: msg, err })
            throw err
        } finally {
            isLoading.value = false
        }
    }

    function updateCell(rowId: number, field: string, value: any) {
        logger.debug('Updating cell locally', { rowId, field, value })

        // Update local state immediately
        const row = configurations.value.find(r => r.id === rowId)
        if (row) {
            (row as any)[field] = value
        }

        // Track pending change
        if (!pendingEdits.value.has(rowId)) {
            pendingEdits.value.set(rowId, {})
        }
        pendingEdits.value.get(rowId)![field] = value

        logger.debug('Cell updated', { pendingCount: pendingEdits.value.size })
    }

    async function commitPendingChanges() {
        if (pendingEdits.value.size === 0) {
            logger.warn('No pending changes to commit')
            return { success: true, successCount: 0, errorCount: 0 }
        }

        isLoading.value = true
        let successCount = 0
        let errorCount = 0
        const errors: Record<string, string> = {}

        try {
            logger.info('Committing pending changes', { count: pendingEdits.value.size })

            for (const [rowId, edits] of pendingEdits.value.entries()) {
                for (const [field, value] of Object.entries(edits)) {
                    try {
                        await configurationService.updateCell(rowId, field, value)
                        successCount++
                        logger.debug('Cell saved', { rowId, field })
                    } catch (err: any) {
                        errorCount++
                        const msg = err.response?.data?.detail || err.message
                        errors[`${rowId}_${field}`] = msg
                        logger.error('Cell save failed', { rowId, field, error: msg })
                    }
                }
            }

            if (errorCount === 0) {
                pendingEdits.value.clear()
                logger.info('All changes committed successfully')
            } else {
                logger.warn('Some changes failed', { successCount, errorCount })
            }

            return { success: errorCount === 0, successCount, errorCount, errors }
        } finally {
            isLoading.value = false
        }
    }

    async function deleteConfiguration(id: number) {
        isLoading.value = true
        error.value = null

        try {
            logger.info('Deleting configuration', { id })
            await configurationService.delete(id)
            configurations.value = configurations.value.filter(c => c.id !== id)
            pendingEdits.value.delete(id)
            logger.info('Configuration deleted', { id })
        } catch (err: any) {
            const msg = err.response?.data?.detail || err.message || 'Failed to delete configuration'
            error.value = msg
            logger.error('Failed to delete configuration', { error: msg, err })
            throw err
        } finally {
            isLoading.value = false
        }
    }

    function clearPendingEdits() {
        pendingEdits.value.clear()
        logger.debug('Pending edits cleared')
    }

    return {
        configurations,
        currentConfiguration,
        pendingEdits,
        isLoading,
        error,
        hasPendingChanges,
        loadConfigurations,
        loadPreviews,
        createConfiguration,
        updateCell,
        commitPendingChanges,
        deleteConfiguration,
        clearPendingEdits
    }
})
