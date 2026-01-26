import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { apiClient } from '@/services/api'
import type { User } from '@/types'

export const useAuthStore = defineStore('auth', () => {
    const user = ref<User | null>(null)
    const token = ref<string | null>(localStorage.getItem('access_token'))

    const isAuthenticated = computed(() => !!token.value && !!user.value)
    const isSuperuser = computed(() => user.value?.is_superuser ?? false)

    async function login(username: string, password: string) {
        try {
            const response = await apiClient.post('/api/v1/auth/login', {
                username,
                password
            })

            token.value = response.data.access_token
            localStorage.setItem('access_token', token.value!)

            await fetchCurrentUser()
            return { success: true }
        } catch (error: any) {
            return {
                success: false,
                error: error.response?.data?.detail || 'Login failed'
            }
        }
    }

    async function fetchCurrentUser() {
        try {
            const response = await apiClient.get('/api/v1/auth/me')
            user.value = response.data
        } catch (error: any) {
            const is401 = error.response?.status === 401
            const isDev = import.meta.env.DEV

            // In development, we only logout on explicit 401 (expired/invalid token)
            // This prevents logging out when the backend restarts or during HMR.
            // In production, we might be stricter, but 401 remains the primary reason to clear session.
            if (is401 || (!isDev && error.response?.status === 403)) {
                logout()
            }
            throw error
        }
    }

    function logout() {
        user.value = null
        token.value = null
        localStorage.removeItem('access_token')
    }

    // Initialize user on store creation if token exists
    if (token.value) {
        fetchCurrentUser().catch(() => {
            // Token might be expired, clear it
            logout()
        })
    }

    return {
        user,
        token,
        isAuthenticated,
        isSuperuser,
        login,
        logout,
        fetchCurrentUser
    }
})
