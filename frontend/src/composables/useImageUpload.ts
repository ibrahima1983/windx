/**
 * Image Upload Composable
 * 
 * Handles image file validation, upload, and preview
 */

import { ref } from 'vue'
import { useToast } from 'primevue/usetoast'
import { apiClient } from '@/services/api'
import { useDebugLogger } from './useDebugLogger'

export function useImageUpload() {
    const toast = useToast()
    const logger = useDebugLogger('useImageUpload')

    const previewUrl = ref<string | null>(null)
    const isUploading = ref(false)
    const progress = ref(0)
    const error = ref<string | null>(null)

    async function uploadImage(file: File, rowId?: number, fieldName?: string) {
        logger.debug('Upload started', { fileName: file.name, size: file.size, rowId, fieldName })

        // Validation
        if (!file.type.startsWith('image/')) {
            const msg = 'Invalid file type. Please select an image.'
            logger.warn('Invalid file type', { type: file.type })
            toast.add({ severity: 'error', summary: 'Invalid File', detail: msg, life: 3000 })
            error.value = msg
            return { success: false, error: msg }
        }

        const maxSize = 5 * 1024 * 1024 // 5MB
        if (file.size > maxSize) {
            const msg = 'File too large. Maximum size is 5MB.'
            logger.warn('File too large', { size: file.size, max: maxSize })
            toast.add({ severity: 'error', summary: 'File Too Large', detail: msg, life: 3000 })
            error.value = msg
            return { success: false, error: msg }
        }

        isUploading.value = true
        error.value = null
        progress.value = 0

        try {
            const formData = new FormData()
            formData.append('file', file)
            if (rowId) formData.append('row_id', String(rowId))
            if (fieldName) formData.append('field_name', fieldName)

            logger.info('Uploading to server...')

            const response = await apiClient.post('/api/v1/entry/upload-image', formData, {
                headers: { 'Content-Type': 'multipart/form-data' },
                onUploadProgress: (progressEvent) => {
                    if (progressEvent.total) {
                        progress.value = Math.round((progressEvent.loaded * 100) / progressEvent.total)
                        logger.debug('Upload progress', { progress: progress.value })
                    }
                }
            })

            previewUrl.value = response.data.url
            logger.info('Upload successful', response.data)
            toast.add({
                severity: 'success',
                summary: 'Upload Complete',
                detail: 'Image uploaded successfully',
                life: 3000
            })

            return {
                success: true,
                url: response.data.url,
                filename: response.data.filename
            }
        } catch (err: any) {
            const errorMsg = err.response?.data?.detail || err.message || 'Upload failed'
            error.value = errorMsg
            logger.error('Upload failed', { error: errorMsg, err })
            toast.add({
                severity: 'error',
                summary: 'Upload Failed',
                detail: errorMsg,
                life: 5000
            })
            return { success: false, error: errorMsg }
        } finally {
            isUploading.value = false
            progress.value = 0
        }
    }

    function clearPreview() {
        previewUrl.value = null
        error.value = null
        progress.value = 0
        logger.debug('Preview cleared')
    }

    return {
        uploadImage,
        previewUrl,
        isUploading,
        progress,
        error,
        clearPreview
    }
}
