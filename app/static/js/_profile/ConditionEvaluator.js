class ConditionEvaluator {
    static OPERATORS = {
        // Comparison operators
        equals: (a, b) => a == b,
        not_equals: (a, b) => a != b,
        greater_than: (a, b) => (a || 0) > (b || 0),
        less_than: (a, b) => (a || 0) < (b || 0),
        greater_equal: (a, b) => (a || 0) >= (b || 0),
        less_equal: (a, b) => (a || 0) <= (b || 0),

        // String operators
        contains: (a, b) => String(a || '').toLowerCase().includes(String(b).toLowerCase()),
        starts_with: (a, b) => String(a || '').toLowerCase().startsWith(String(b).toLowerCase()),
        ends_with: (a, b) => String(a || '').toLowerCase().endsWith(String(b).toLowerCase()),
        matches_pattern: (a, b) => new RegExp(b).test(String(a || '')),

        // Collection operators
        in: (a, b) => (Array.isArray(b) ? b : [b]).includes(a),
        not_in: (a, b) => !(Array.isArray(b) ? b : [b]).includes(a),
        any_of: (a, b) => b.some(item => (Array.isArray(a) ? a : [a]).includes(item)),
        all_of: (a, b) => b.every(item => (Array.isArray(a) ? a : [a]).includes(item)),

        // Existence operators
        exists: (a, b) => a !== null && a !== undefined && a !== '',
        not_exists: (a, b) => a === null || a === undefined || a === '',
        is_empty: (a, b) => !Boolean(a),
        is_not_empty: (a, b) => Boolean(a),
    };

    static evaluateCondition(condition, formData) {
        if (!condition) return true;

        const operator = condition.operator;
        if (!operator) return true;

        // Handle logical operators
        if (operator === 'and') {
            return (condition.conditions || []).every(c =>
                ConditionEvaluator.evaluateCondition(c, formData)
            );
        } else if (operator === 'or') {
            return (condition.conditions || []).some(c =>
                ConditionEvaluator.evaluateCondition(c, formData)
            );
        } else if (operator === 'not') {
            return !ConditionEvaluator.evaluateCondition(condition.condition, formData);
        }

        // Handle field-based operators
        const field = condition.field;
        if (!field) return true;

        const fieldValue = ConditionEvaluator.getFieldValue(field, formData);
        const expectedValue = condition.value;

        const operatorFn = ConditionEvaluator.OPERATORS[operator];
        if (!operatorFn) {
            throw new Error(`Unknown operator: ${operator}`);
        }

        return operatorFn(fieldValue, expectedValue);
    }

    static getFieldValue(fieldPath, formData) {
        if (!fieldPath.includes('.')) {
            return formData[fieldPath];
        }

        // Support nested field access
        let value = formData;
        for (const part of fieldPath.split('.')) {
            if (value && typeof value === 'object') {
                value = value[part];
            } else {
                return undefined;
            }
        }
        return value;
    }
}