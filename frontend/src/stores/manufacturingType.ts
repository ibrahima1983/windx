/**
 * Manufacturing Type Store
 * 
 * Manages manufacturing types, schemas, and headers
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { manufacturingTypeService } from '@/services/manufacturingTypeService'
import { useDebugLogger } from '@/composables/useDebugLogger'
import type { ManufacturingType } from '@/types'

export const useManufacturingTypeStore = defineStore('manufacturingType', () => {
    const logger = useDebugLogger('ManufacturingTypeStore')

    const types = ref<ManufacturingType[]>([])
    const currentType = ref<ManufacturingType | null>(null)
    const schema = ref<any | null>(null)
    const headers = ref<string[]>([])
    const headerMapping = ref<Record<string, string>>({})
    const isLoading = ref(false)
    const error = ref<string | null>(null)

    const activeTypes = computed(() => types.value.filter(t => t.is_active))

    async function loadTypes() {
        isLoading.value = true
        error.value = null

        try {
            logger.info('Loading manufacturing types')
            types.value = await manufacturingTypeService.getAll()
            logger.info('Manufacturing types loaded', { count: types.value.length })
        } catch (err: any) {
            const msg = err.response?.data?.detail || err.message || 'Failed to load types'
            error.value = msg
            logger.error('Failed to load types', { error: msg, err })
            throw err
        } finally {
            isLoading.value = false
        }
    }

    async function loadSchema(manufacturingTypeId: number, pageType: string = 'profile') {
        isLoading.value = true
        error.value = null

        try {
            logger.info('Loading schema', { manufacturingTypeId, pageType })
            schema.value = await manufacturingTypeService.getSchema(manufacturingTypeId, pageType)
            logger.info('Schema loaded', { sections: schema.value?.sections?.length || 0 })
        } catch (err: any) {
            const msg = err.response?.data?.detail || err.message || 'Failed to load schema'
            error.value = msg
            logger.error('Failed to load schema', { error: msg, err })
            throw err
        } finally {
            isLoading.value = false
        }
    }

    async function loadHeaders(manufacturingTypeId: number, pageType: string = 'profile') {
        isLoading.value = true
        error.value = null

        try {
            logger.info('Loading headers', { manufacturingTypeId, pageType })
            headers.value = await manufacturingTypeService.getHeaders(manufacturingTypeId, pageType)
            logger.info('Headers loaded', { count: headers.value.length })
        } catch (err: any) {
            const msg = err.response?.data?.detail || err.message || 'Failed to load headers'
            error.value = msg
            logger.error('Failed to load headers', { error: msg, err })
            throw err
        } finally {
            isLoading.value = false
        }
    }

    async function loadHeaderMapping(manufacturingTypeId: number, pageType: string = 'profile') {
        isLoading.value = true
        error.value = null

        try {
            logger.info('Loading header mapping', { manufacturingTypeId, pageType })
            headerMapping.value = await manufacturingTypeService.getHeaderMapping(manufacturingTypeId, pageType)
            logger.info('Header mapping loaded', { count: Object.keys(headerMapping.value).length })
        } catch (err: any) {
            const msg = err.response?.data?.detail || err.message || 'Failed to load header mapping'
            error.value = msg
            logger.error('Failed to load header mapping', { error: msg, err })
            throw err
        } finally {
            isLoading.value = false
        }
    }

    async function loadAll(manufacturingTypeId: number, pageType: string = 'profile') {
        logger.info('Loading all data for manufacturing type', { manufacturingTypeId, pageType })

        await Promise.all([
            loadSchema(manufacturingTypeId, pageType),
            loadHeaders(manufacturingTypeId, pageType),
            loadHeaderMapping(manufacturingTypeId, pageType)
        ])

        logger.info('All data loaded successfully')
    }

    function setCurrentType(typeId: number) {
        currentType.value = types.value.find(t => t.id === typeId) || null
        logger.debug('Current type set', { typeId, name: currentType.value?.name })
    }

    return {
        types,
        currentType,
        schema,
        headers,
        headerMapping,
        isLoading,
        error,
        activeTypes,
        loadTypes,
        loadSchema,
        loadHeaders,
        loadHeaderMapping,
        loadAll,
        setCurrentType
    }
})
