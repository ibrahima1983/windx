import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes: RouteRecordRaw[] = [
    {
        path: '/',
        redirect: '/dashboard'
    },
    {
        path: '/login',
        name: 'Login',
        component: () => import('@/views/auth/LoginView.vue'),
        meta: { requiresAuth: false }
    },
    {
        path: '/dashboard',
        name: 'Dashboard',
        component: () => import('@/views/DashboardView.vue'),
        meta: { requiresAuth: true }
    },
    {
        path: '/profile-entry',
        name: 'ProfileEntry',
        component: () => import('@/views/entry/GenericEntryView.vue'),
        meta: { requiresAuth: true },
        props: { pageType: 'profile', pageTitle: 'Profile' }
    },
    {
        path: '/glazing-entry',
        name: 'GlazingEntry',
        component: () => import('@/views/entry/GenericEntryView.vue'),
        meta: { requiresAuth: true },
        props: { pageType: 'glazing', pageTitle: 'Glazing' }
    },
    {
        path: '/hardware-entry',
        name: 'HardwareEntry',
        component: () => import('@/views/entry/GenericEntryView.vue'),
        meta: { requiresAuth: true },
        props: { pageType: 'hardware', pageTitle: 'Hardware' }
    },
    // Admin Routes
    {
        path: '/admin/definitions',
        redirect: '/admin/definitions/profile'
    },
    {
        path: '/admin/definitions/profile',
        name: 'ProfileDefinitions',
        component: () => import('@/views/admin/GenericDefinitionView.vue'),
        meta: { requiresAuth: true },
        props: { pageType: 'profile' }
    },
    {
        path: '/:pathMatch(.*)*',
        name: 'NotFound',
        component: () => import('@/views/NotFoundView.vue')
    }
]

const router = createRouter({
    history: createWebHistory(import.meta.env.BASE_URL),
    routes
})

import NProgress from 'nprogress'

// Configure NProgress
NProgress.configure({ showSpinner: false })

// Navigation guard for authentication
router.beforeEach((to, _from, next) => {
    // Start progress bar
    NProgress.start()

    const authStore = useAuthStore()
    const requiresAuth = to.matched.some(record => record.meta.requiresAuth)
    const requiresSuperuser = to.matched.some(record => record.meta.requiresSuperuser)

    if (requiresAuth && !authStore.isAuthenticated) {
        next({ name: 'Login', query: { redirect: to.fullPath } })
    } else if (requiresSuperuser && !authStore.isSuperuser) {
        next({ name: 'Dashboard' })
    } else {
        next()
    }
})

router.afterEach(() => {
    // Finish progress bar
    NProgress.done()
})

export default router
