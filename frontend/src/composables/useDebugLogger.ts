/**
 * Debug Logger Composable
 * 
 * Provides structured logging with component context
 * Automatically disabled in production
 */

export function useDebugLogger(componentName: string) {
    const isDev = import.meta.env.DEV
    const timestamp = () => new Date().toISOString().split('T')[1]?.split('.')[0] || 'unknown'

    return {
        debug: (...args: any[]) => {
            if (isDev) {
                console.log(`[${timestamp()}] [${componentName}] [DEBUG]`, ...args)
            }
        },

        info: (...args: any[]) => {
            console.info(`[${timestamp()}] [${componentName}] [INFO]`, ...args)
        },

        warn: (...args: any[]) => {
            console.warn(`[${timestamp()}] [${componentName}] [WARN]`, ...args)
        },

        error: (...args: any[]) => {
            console.error(`[${timestamp()}] [${componentName}] [ERROR]`, ...args)
        }
    }
}
