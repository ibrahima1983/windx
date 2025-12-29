class DataLoader {
    static async loadManufacturingTypes() {
        console.log('🦆 [MFGTYPE] Starting to load manufacturing types...');
        try {
            const url = '/api/v1/manufacturing-types/';
            console.log('🦆 [MFGTYPE] Fetching from:', url);

            const response = await fetch(url, {
                credentials: 'include'  // Include cookies for admin authentication
            });

            console.log('🦆 [MFGTYPE] Response status:', response.status);
            console.log('🦆 [MFGTYPE] Response ok:', response.ok);

            if (!response.ok) {
                const errorText = await response.text();
                console.error('🦆 [MFGTYPE ERROR] Failed response:', errorText);
                throw new Error('Failed to load manufacturing types');
            }

            const data = await response.json();
            console.log('🦆 [MFGTYPE] Response data:', data);
            const manufacturingTypes = data.items || [];
            console.log('🦆 [MFGTYPE] ✅ Success! Loaded', manufacturingTypes.length, 'types');
            return manufacturingTypes;
        } catch (err) {
            console.error('🦆 [MFGTYPE ERROR] ❌ Exception caught:', err);
            console.error('🦆 [MFGTYPE ERROR] Error stack:', err.stack);
            throw new Error('Failed to load manufacturing types');
        }
    }

    static async loadSchema(manufacturingTypeId, pageType = 'profile') {
        console.log('🦆 [SCHEMA] ========================================');
        console.log('🦆 [SCHEMA] Starting schema load process...');
        console.log('🦆 [SCHEMA] 🔥 CACHE BUSTED VERSION 2 - UPDATED WITH PAGE_TYPE SUPPORT 🔥');

        if (!manufacturingTypeId) {
            console.warn('🦆 [SCHEMA] ⚠️ No manufacturing type ID - aborting');
            return null;
        }

        console.log('🦆 [SCHEMA] Manufacturing type ID:', manufacturingTypeId);
        console.log('🦆 [SCHEMA] Page type:', pageType);

        try {
            const url = `/api/v1/admin/entry/profile/schema/${manufacturingTypeId}?page_type=${encodeURIComponent(pageType)}`;
            console.log('🦆 [SCHEMA] Constructed URL:', url);
            console.log('🦆 [SCHEMA] 🎯 NOTICE: URL INCLUDES page_type PARAMETER!');
            console.log('🦆 [SCHEMA] Initiating fetch request...');

            const response = await fetch(url, {
                credentials: 'include'  // Include cookies for admin authentication
            });

            console.log('🦆 [SCHEMA] Response received!');
            console.log('🦆 [SCHEMA] Status:', response.status);
            console.log('🦆 [SCHEMA] Status text:', response.statusText);
            console.log('🦆 [SCHEMA] Headers:', Object.fromEntries(response.headers.entries()));

            if (!response.ok) {
                const errorText = await response.text();
                console.error('🦆 [SCHEMA ERROR] ❌ Response not OK');
                console.error('🦆 [SCHEMA ERROR] Status:', response.status);
                console.error('🦆 [SCHEMA ERROR] Error body:', errorText);
                throw new Error(`Failed to load schema: ${response.status}`);
            }

            console.log('🦆 [SCHEMA] Parsing JSON response...');
            const schema = await response.json();
            console.log('🦆 [SCHEMA] ✨ LOUD DUCK DEBUG - Schema loaded:', schema);
            console.log('🦆 [SCHEMA] ✨ LOUD DUCK DEBUG - Schema type:', typeof schema);
            console.log('🦆 [SCHEMA] ✨ LOUD DUCK DEBUG - Schema keys:', Object.keys(schema || {}));
            console.log('🦆 [SCHEMA] ✨ LOUD DUCK DEBUG - Has sections?', !!schema?.sections);
            console.log('🦆 [SCHEMA] ✨ LOUD DUCK DEBUG - Sections length:', schema?.sections?.length || 0);
            console.log('🦆 [SCHEMA] ✨ LOUD DUCK DEBUG - Sections content:', schema?.sections);

            return schema;
        } catch (err) {
            console.error('🦆 [SCHEMA ERROR] ❌ Exception caught:', err);
            throw new Error('Failed to load form schema');
        }
    }

    static async loadPreviews(manufacturingTypeId) {
        console.log('🦆 [PREVIEWS] ========================================');
        console.log('🦆 [PREVIEWS] 🔥 CACHE BUSTED VERSION 3 - DEBUGGING PREVIEWS API 🔥');
        console.log('🦆 [PREVIEWS] Loading previews for manufacturing type:', manufacturingTypeId);
        
        if (!manufacturingTypeId) {
            console.warn('🦆 [PREVIEWS] ⚠️ No manufacturing type ID - returning empty array');
            return [];
        }

        try {
            const url = `/api/v1/admin/entry/profile/previews/${manufacturingTypeId}`;
            console.log('🦆 [PREVIEWS] Constructed URL:', url);
            console.log('🦆 [PREVIEWS] Making fetch request...');
            
            const response = await fetch(url, {
                credentials: 'include'  // Include cookies for admin authentication
            });
            
            console.log('🦆 [PREVIEWS] Response status:', response.status);
            console.log('🦆 [PREVIEWS] Response ok:', response.ok);
            
            if (response.ok) {
                const data = await response.json();
                console.log('🦆 [PREVIEWS] ✨ RAW API RESPONSE:', data);
                console.log('🦆 [PREVIEWS] ✨ Headers count:', data.headers?.length || 0);
                console.log('🦆 [PREVIEWS] ✨ Rows count:', data.rows?.length || 0);
                console.log('🦆 [PREVIEWS] ✨ First row:', data.rows?.[0]);
                
                const savedConfigurations = data.rows || [];
                console.log(`🦆 [PREVIEWS] ✅ Processed ${savedConfigurations.length} previews`);
                return savedConfigurations;
            } else if (response.status === 403) {
                console.warn('🦆 [PREVIEWS] 🔒 Preview access forbidden - user may not have permission');
                return [];
            } else {
                console.warn(`🦆 [PREVIEWS] ⚠️ Failed to load previews: ${response.status}`);
                const errorText = await response.text();
                console.error('🦆 [PREVIEWS] Error response:', errorText);
                return [];
            }
        } catch (err) {
            console.error('🦆 [PREVIEWS] ❌ Exception caught:', err);
            console.error('🦆 [PREVIEWS] Error stack:', err.stack);
            return [];
        }
    }

    static async loadDynamicHeaders(manufacturingTypeId, pageType = 'profile') {
        console.log('🦆 [HEADERS] ========================================');
        console.log('🦆 [HEADERS] Starting dynamic headers load process...');
        console.log('🦆 [HEADERS] 🔥 CACHE BUSTED VERSION 2 - UPDATED WITH PAGE_TYPE SUPPORT 🔥');

        if (!manufacturingTypeId) {
            console.warn('🦆 [HEADERS] ⚠️ No manufacturing type ID - aborting');
            return [];
        }

        console.log('🦆 [HEADERS] Manufacturing type ID:', manufacturingTypeId);
        console.log('🦆 [HEADERS] Page type:', pageType);

        try {
            const url = `/api/v1/admin/entry/profile/headers/${manufacturingTypeId}?page_type=${encodeURIComponent(pageType)}`;
            console.log('🦆 [HEADERS] Constructed URL:', url);
            console.log('🦆 [HEADERS] 🎯 NOTICE: URL INCLUDES page_type PARAMETER!');
            console.log('🦆 [HEADERS] Initiating fetch request...');

            const response = await fetch(url, {
                credentials: 'include'  // Include cookies for admin authentication
            });

            console.log('🦆 [HEADERS] Response received!');
            console.log('🦆 [HEADERS] Status:', response.status);
            console.log('🦆 [HEADERS] Status text:', response.statusText);

            if (!response.ok) {
                const errorText = await response.text();
                console.error('🦆 [HEADERS ERROR] ❌ Response not OK');
                console.error('🦆 [HEADERS ERROR] Status:', response.status);
                console.error('🦆 [HEADERS ERROR] Error body:', errorText);
                throw new Error(`Failed to load dynamic headers: ${response.status}`);
            }

            console.log('🦆 [HEADERS] Parsing JSON response...');
            const headers = await response.json();
            console.log('🦆 [HEADERS] ✨ LOUD DUCK DEBUG - Headers loaded:', headers);
            console.log('🦆 [HEADERS] ✨ LOUD DUCK DEBUG - Headers type:', typeof headers);
            console.log('🦆 [HEADERS] ✨ LOUD DUCK DEBUG - Headers length:', headers?.length || 0);
            console.log('🦆 [HEADERS] ✅ Success! Loaded', headers.length, 'headers');

            return headers;
        } catch (err) {
            console.error('🦆 [HEADERS ERROR] ❌ Exception caught:', err);
            console.error('🦆 [HEADERS ERROR] Error stack:', err.stack);
            throw new Error('Failed to load dynamic headers');
        }
    }
}