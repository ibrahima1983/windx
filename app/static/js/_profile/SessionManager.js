// Session storage keys
const SESSION_KEY = 'profile_entry_form_data';
const COMMIT_STATUS_KEY = 'profile_entry_committed';

class SessionManager {
    static SESSION_KEY = SESSION_KEY;
    static COMMIT_STATUS_KEY = COMMIT_STATUS_KEY;

    static loadFromSession() {
        const savedData = sessionStorage.getItem(SESSION_KEY);
        const isCommitted = sessionStorage.getItem(COMMIT_STATUS_KEY) === 'true';

        if (savedData) {
            try {
                const parsedData = JSON.parse(savedData);
                // Only load if there's meaningful data (not just defaults)
                const hasActualData = Object.keys(parsedData).some(key => {
                    const value = parsedData[key];
                    return value !== null && value !== undefined && value !== '' &&
                        !(Array.isArray(value) && value.length === 0);
                });

                if (hasActualData) {
                    return {
                        data: parsedData,
                        hasUnsavedData: !isCommitted
                    };
                }
            } catch (err) {
                console.error('Failed to load session data:', err);
            }
        }

        return {
            data: {},
            hasUnsavedData: false
        };
    }

    static saveToSession(formData) {
        sessionStorage.setItem(SESSION_KEY, JSON.stringify(formData));
        sessionStorage.setItem(COMMIT_STATUS_KEY, 'false');
    }

    static markAsCommitted() {
        sessionStorage.setItem(COMMIT_STATUS_KEY, 'true');
    }

    static setupNavigationGuards(hasUnsavedDataCallback) {
        window.addEventListener('beforeunload', (e) => {
            if (hasUnsavedDataCallback()) {
                e.preventDefault();
                e.returnValue = 'You have unsaved data. Are you sure you want to leave?';
                return e.returnValue;
            }
        });

        document.addEventListener('click', (e) => {
            const link = e.target.closest('a');
            if (link && hasUnsavedDataCallback() && !link.getAttribute('href').startsWith('#')) {
                if (!confirm('You have unsaved data that has not been recorded to the database. Are you sure you want to leave this page?')) {
                    e.preventDefault();
                    e.stopPropagation();
                }
            }
        }, true);
    }
}