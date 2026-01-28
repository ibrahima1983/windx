export interface DependencyAction {
    type: 'autofill' | 'disable'
    source_property?: string
    target_field: string
    disable_target?: boolean
    lookup_source?: string
    lookup_key?: string
    chain?: DependencyAction
}

export interface DependencyRule {
    trigger_field: string
    actions: DependencyAction[]
}

export interface SchemaWithDependencies {
    sections: any[]
    dependencies?: DependencyRule[]
}
