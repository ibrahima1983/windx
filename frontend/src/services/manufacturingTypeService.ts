/**
 * Manufacturing Type Service
 * 
 * API calls for manufacturing types and schemas
 */

import { apiClient } from './api'

export const manufacturingTypeService = {
    async getAll() {
        const response = await apiClient.get('/api/v1/manufacturing-types/')
        return response.data.items || []
    },

    async getById(id: number) {
        const response = await apiClient.get(`/api/v1/manufacturing-types/${id}`)
        return response.data
    },

    async getSchema(manufacturingTypeId: number, pageType: string = 'profile') {
        const response = await apiClient.get(
            `/api/v1/admin/entry/profile/schema/${manufacturingTypeId}`,
            { params: { page_type: pageType } }
        )
        return response.data
    },

    async getHeaders(manufacturingTypeId: number, pageType: string = 'profile') {
        const response = await apiClient.get(
            `/api/v1/admin/entry/profile/headers/${manufacturingTypeId}`,
            { params: { page_type: pageType } }
        )
        return response.data
    },

    async getHeaderMapping(manufacturingTypeId: number, pageType: string = 'profile') {
        const response = await apiClient.get(
            `/api/v1/admin/entry/profile/header-mapping/${manufacturingTypeId}`,
            { params: { page_type: pageType } }
        )
        return response.data
    }
}
