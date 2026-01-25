/**
 * Configuration Service
 * 
 * API calls for configuration management
 */

import { apiClient } from './api'

export const configurationService = {
    async getAll(params?: { manufacturing_type_id?: number; skip?: number; limit?: number }) {
        const response = await apiClient.get('/api/v1/configurations/', { params })
        return response.data
    },

    async getById(id: number) {
        const response = await apiClient.get(`/api/v1/configurations/${id}`)
        return response.data
    },

    async create(data: Record<string, any>) {
        const response = await apiClient.post('/api/v1/configurations/', data)
        return response.data
    },

    async update(id: number, data: Record<string, any>) {
        const response = await apiClient.put(`/api/v1/configurations/${id}`, data)
        return response.data
    },

    async delete(id: number) {
        const response = await apiClient.delete(`/api/v1/configurations/${id}`)
        return response.data
    },

    async updateCell(id: number, field: string, value: any) {
        const response = await apiClient.patch(`/api/v1/admin/entry/profile/preview/${id}/update-cell`, {
            field,
            value
        })
        return response.data
    },

    async getPreviews(manufacturingTypeId: number) {
        const response = await apiClient.get(`/api/v1/admin/entry/profile/previews/${manufacturingTypeId}`)
        return response.data
    }
}
