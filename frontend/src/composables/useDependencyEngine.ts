import { ref, watch, type Ref } from 'vue'
import type { SchemaWithDependencies, DependencyAction, DependencyRule } from '@/types/dependencies'

export function useDependencyEngine(
    schema: Ref<SchemaWithDependencies | null>,
    form: Ref<Record<string, any>>,
    findField: (name: string) => any
) {
    const disabledFields = ref<Record<string, boolean>>({})

    // Process a single action
    function processAction(action: DependencyAction, triggerValue: any, sourceOption: any) {
        console.log('[DependencyEngine] Processing action:', action.type, action.target_field)

        switch (action.type) {
            case 'autofill': {
                let valueToSet = null

                if (action.source_property) {
                    // Dot notation access (e.g. metadata_.opening_system_id)
                    valueToSet = action.source_property.split('.').reduce((obj, key) => obj && obj[key], sourceOption)
                } else {
                    // Direct value from trigger if no source property specified
                    valueToSet = triggerValue
                }

                if (valueToSet !== undefined && valueToSet !== null) {
                    form.value[action.target_field] = valueToSet
                    console.log(`[DependencyEngine] Set ${action.target_field} to`, valueToSet)
                }

                if (action.disable_target) {
                    disabledFields.value[action.target_field] = true
                }

                // Chain processing
                if (action.chain) {
                    if (action.chain.lookup_source) {
                        const lookupField = findField(action.chain.lookup_source)
                        if (lookupField) {
                            const options = lookupField.options_data || lookupField.options || []
                            const lookupKey = action.chain.lookup_key || 'id'

                            // valueToSet is the ID. Find the option in lookup source.
                            const nextSourceOption = options.find((o: any) => o[lookupKey] === valueToSet)

                            if (nextSourceOption) {
                                console.log('[DependencyEngine] Chaining next lookup found:', nextSourceOption.name)
                                processAction(action.chain, valueToSet, nextSourceOption)
                            } else {
                                console.warn('[DependencyEngine] Chained lookup failed for', action.chain.lookup_source)
                            }
                        }
                    } else {
                        // Direct chain without lookup
                        processAction(action.chain, valueToSet, sourceOption)
                    }
                }
                break
            }

            case 'disable':
                disabledFields.value[action.target_field] = true
                break

            default:
                console.warn(`[DependencyEngine] Unknown action type: ${action.type}`)
        }
    }

    // Set up watchers based on schema
    watch(() => schema.value, (newSchema) => {
        if (!newSchema || !newSchema.dependencies) return

        newSchema.dependencies.forEach((rule: DependencyRule) => {
            watch(() => form.value[rule.trigger_field], (newVal) => {
                // Reset logic: if value is cleared, we should strictly re-evaluate or clear targets?
                // For simplicity, if cleared, we enable the targets.
                if (!newVal) {
                    rule.actions.forEach(action => {
                        // Basic reset: re-enable. 
                        // Ideally we should recursively enable chained targets too.
                        // This simple implementation enables direct targets.
                        disabledFields.value[action.target_field] = false
                        // TODO: Handle deep chain reset if needed
                        if (action.chain) {
                            disabledFields.value[action.chain.target_field] = false
                        }
                    })
                    return
                }

                // Find the selected option for the trigger field
                const field = findField(rule.trigger_field)
                if (!field) return

                const options = field.options_data || field.options || []
                // Try matching by name or id
                const selectedOption = options.find((o: any) => o.name === newVal || o.id === newVal)

                if (selectedOption) {
                    rule.actions.forEach(action => {
                        processAction(action, newVal, selectedOption)
                    })
                }
            })
        })
    }, { immediate: true })

    return {
        disabledFields
    }
}
