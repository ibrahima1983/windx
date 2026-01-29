/**
 * Configuration Service
 * 
 * API calls for configuration management
 */

import { apiClient } from './api'

const BASE_ROUTE = '/api/v1/'
const BASE_CONFIG = `${BASE_ROUTE}configurations`
const BASE_ADMIN = `${BASE_ROUTE}admin/entry/profile`

export const configurationService = {
  async getAll(params?: {
    manufacturing_type_id?: number
    skip?: number
    limit?: number
  }) {
    const res = await apiClient.get(BASE_CONFIG, { params })
    return res.data
  },

  async getById(id: number) {
    const res = await apiClient.get(`${BASE_CONFIG}/${id}`)
    return res.data
  },

  async create(data: Record<string, any>) {
    const res = await apiClient.post(`${BASE_ADMIN}/save`, data)
    return res.data
  },

  async update(id: number, data: Record<string, any>) {
    const res = await apiClient.put(`${BASE_CONFIG}/${id}`, data)
    return res.data
  },

  async delete(id: number) {
    const res = await apiClient.delete(`${BASE_CONFIG}/${id}`)
    return res.data
  },

  async bulkDelete(ids: number[]) {
    const res = await apiClient.delete(
      `${BASE_ADMIN}/configurations/bulk`,
      { data: ids }
    )
    return res.data
  },

  async updateCell(id: number, field: string, value: any) {
    const res = await apiClient.patch(
      `${BASE_ADMIN}/preview/${id}/update-cell`,
      { field, value }
    )
    return res.data
  },

  async getPreviews(manufacturingTypeId: number) {
    const res = await apiClient.get(
      `${BASE_ADMIN}/previews/${manufacturingTypeId}`
    )
    return res.data
  },
}
