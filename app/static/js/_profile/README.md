# Profile Entry System - Modular Architecture (Browser Compatible)

## Overview

The Profile Entry system has been refactored from a single large file (`profile-entry.js`) into a modular architecture. Due to browser compatibility requirements (no ES6 module support), all modules are included inline within the main file while maintaining the logical separation and benefits of modular design.

## Architecture

### Main File
- **`profile-entry.js`** - Contains all modular classes inline and maintains the original `profileEntryApp()` function signature

### Modular Components (Inline Classes)

#### Core Logic Classes
- **`ConditionEvaluator`** - Handles conditional field visibility logic
- **`FormValidator`** - Manages form validation and error handling
- **`FormHelpers`** - Utility functions for form operations and data formatting

#### Data Management Classes
- **`DataLoader`** - Handles all API calls for loading data (schema, manufacturing types, previews)
- **`SessionManager`** - Manages browser session storage and navigation guards
- **`ConfigurationSaver`** - Handles saving configurations to the server

#### UI-Specific Classes
- **`ImageHandler`** - Manages image upload, preview, and display functionality
- **`TableEditor`** - Handles inline table editing and batch operations

### Separate Module Files (Reference Implementation)
The `_profile/` directory contains the original modular implementation as separate files:
- These serve as reference and documentation
- They demonstrate the intended modular structure
- They can be used for testing individual components
- Future browser module support can easily adopt these files

## Benefits of Refactoring

### 1. **Maintainability**
- Each class has a single responsibility
- Easier to locate and fix bugs
- Clear separation of concerns within the main file

### 2. **Testability**
- Individual classes can be unit tested
- Easier to mock dependencies
- Better test coverage possible

### 3. **Code Organization**
- Related functionality is grouped in classes
- Easier to understand the codebase
- Better developer experience

### 4. **Browser Compatibility**
- Works in all browsers without module support
- No build step required
- Immediate compatibility with existing infrastructure

### 5. **Future Migration Path**
- Easy to extract to separate modules when browser support improves
- Modular structure is already defined
- Clean interfaces between components

## Implementation Approach

### Inline Classes Strategy
Instead of ES6 modules, we use:

```javascript
// All classes defined inline in profile-entry.js
class ConditionEvaluator {
    static evaluateCondition(condition, formData) { /* ... */ }
}

class SessionManager {
    static loadFromSession() { /* ... */ }
}

// ... other classes

function profileEntryApp(options = {}) {
    return {
        // Uses all the inline classes
        async init() {
            const sessionData = SessionManager.loadFromSession();
            // ...
        }
    };
}
```

### Benefits Over Original Monolithic Approach
- **Logical Separation**: Code is organized into focused classes
- **Reusability**: Static methods can be called from anywhere
- **Maintainability**: Each class handles one concern
- **Readability**: Clear structure and organization
- **Testing**: Individual classes can be tested

## Class Details

### ConditionEvaluator
```javascript
// Handles complex conditional logic for field visibility
ConditionEvaluator.evaluateCondition(condition, formData)
```

### FormValidator
```javascript
// Validates individual fields and entire forms
FormValidator.validateField(field, value, isVisible)
FormValidator.validateAllFields(schema, formData, fieldVisibility)
FormValidator.isFormValid(schema, formData, fieldVisibility, fieldErrors)
```

### DataLoader
```javascript
// Loads data from various API endpoints
DataLoader.loadManufacturingTypes()
DataLoader.loadSchema(manufacturingTypeId)
DataLoader.loadPreviews(manufacturingTypeId)
```

### SessionManager
```javascript
// Manages browser session and navigation
SessionManager.loadFromSession()
SessionManager.saveToSession(formData)
SessionManager.setupNavigationGuards(callback)
```

### ConfigurationSaver
```javascript
// Handles server communication for saving
ConfigurationSaver.saveConfiguration(saveData)
ConfigurationSaver.handleSaveError(status, errorData)
```

### ImageHandler
```javascript
// Manages image operations
ImageHandler.isImageField(fieldName)
ImageHandler.getImageUrl(filename)
ImageHandler.handleFileChange(...)
```

### TableEditor
```javascript
// Handles table editing operations
TableEditor.saveInlineEdit(...)
TableEditor.commitTableChanges(pendingEdits)
TableEditor.deleteRow(rowId)
```

### FormHelpers
```javascript
// Utility functions for form operations
FormHelpers.getUIComponent(field)
FormHelpers.getFieldOptions(fieldName)
FormHelpers.prepareSaveData(...)
FormHelpers.getPreviewValue(...)
```

## Backward Compatibility

The refactoring maintains 100% backward compatibility:

- The main `profileEntryApp()` function signature is unchanged
- All public methods and properties remain the same
- Existing templates and calling code require no changes
- The API surface is identical to the original implementation

## Usage

The system is used exactly as before:

```javascript
// In HTML templates
x-data="profileEntryApp({ canEdit: true, canDelete: true })"
```

The modular architecture is completely transparent to consumers of the API.

## Future Migration to ES6 Modules

When browser support allows, migration is straightforward:

1. **Use existing separate files** in `_profile/` directory
2. **Add module script tags** to HTML
3. **Update imports** in main file
4. **No logic changes required** - classes are already properly separated

```html
<!-- Future ES6 module approach -->
<script type="module" src="/static/js/profile-entry.js"></script>
```

## Development Guidelines

When working with this system:

1. **Keep classes focused** - Each class should have a single responsibility
2. **Use static methods** - All methods are static for easy access
3. **Maintain pure functions** - Where possible, use pure functions for easier testing
4. **Document public APIs** - Each class's public methods should be well documented
5. **Test individual classes** - Each class can be tested independently

## Testing Strategy

With the class-based architecture, testing becomes more straightforward:

1. **Unit tests** for individual classes
2. **Integration tests** for class interactions
3. **End-to-end tests** for the complete workflow

Each class can be tested in isolation with mocked dependencies, making tests faster and more reliable.

## File Structure

```
app/static/js/
├── profile-entry.js          # Main file with all classes inline
├── _profile/                 # Reference modular implementation
│   ├── ConditionEvaluator.js # Individual class files
│   ├── SessionManager.js     # (for reference/future use)
│   ├── DataLoader.js
│   ├── FormValidator.js
│   ├── ImageHandler.js
│   ├── TableEditor.js
│   ├── FormHelpers.js
│   ├── ConfigurationSaver.js
│   ├── index.js              # Module exports
│   └── README.md             # This documentation
└── _profile/_window.js       # Window-specific functionality
```

## Summary

This approach provides the benefits of modular architecture while maintaining browser compatibility. The code is well-organized, maintainable, and ready for future migration to ES6 modules when appropriate.