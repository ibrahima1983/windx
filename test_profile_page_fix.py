#!/usr/bin/env python3
"""
Test script to verify the profile page data mismatch fix.

This script tests that:
1. Profile page returns profile attributes (not accessories)
2. Schema API correctly filters by page_type
3. Headers API correctly filters by page_type
"""

import asyncio
import aiohttp
import json

async def test_profile_page_fix():
    """Test the profile page data mismatch fix."""
    
    print("🧪 Testing Profile Page Data Mismatch Fix")
    print("=" * 50)
    
    base_url = "http://localhost:8000"
    manufacturing_type_id = 546
    
    # Test credentials (admin user)
    login_data = {
        "username": "admin@example.com",
        "password": "Admin123!"
    }
    
    async with aiohttp.ClientSession() as session:
        # Login first
        print("🔐 Logging in as admin...")
        async with session.post(f"{base_url}/api/v1/auth/login", json=login_data) as response:
            if response.status != 200:
                print(f"❌ Login failed: {response.status}")
                return
            print("✅ Login successful")
        
        # Test 1: Profile Schema API
        print("\n📋 Testing Profile Schema API...")
        async with session.get(f"{base_url}/api/v1/admin/entry/profile/schema/{manufacturing_type_id}?page_type=profile") as response:
            if response.status == 200:
                data = await response.json()
                total_fields = sum(len(section.get('fields', [])) for section in data.get('sections', []))
                field_names = [field['name'] for section in data.get('sections', []) for field in section.get('fields', [])]
                print(f"✅ Profile schema: {total_fields} fields")
                print(f"   First 10 fields: {field_names[:10]}")
                
                # Check if we have profile-specific fields
                profile_fields = ['name', 'type', 'company', 'material', 'opening_system']
                accessories_fields = ['accessory_name', 'accessory_type', 'size_specification']
                
                has_profile_fields = any(field in field_names for field in profile_fields)
                has_accessories_fields = any(field in field_names for field in accessories_fields)
                
                if has_profile_fields and not has_accessories_fields:
                    print("✅ Profile schema contains correct profile fields")
                elif has_accessories_fields:
                    print("❌ Profile schema still contains accessories fields!")
                else:
                    print("⚠️  Profile schema doesn't contain expected fields")
            else:
                print(f"❌ Profile schema API failed: {response.status}")
        
        # Test 2: Accessories Schema API
        print("\n🧩 Testing Accessories Schema API...")
        async with session.get(f"{base_url}/api/v1/admin/entry/profile/schema/{manufacturing_type_id}?page_type=accessories") as response:
            if response.status == 200:
                data = await response.json()
                total_fields = sum(len(section.get('fields', [])) for section in data.get('sections', []))
                field_names = [field['name'] for section in data.get('sections', []) for field in section.get('fields', [])]
                print(f"✅ Accessories schema: {total_fields} fields")
                print(f"   First 10 fields: {field_names[:10]}")
                
                # Check if we have accessories-specific fields
                accessories_fields = ['accessory_name', 'accessory_type', 'size_specification']
                has_accessories_fields = any(field in field_names for field in accessories_fields)
                
                if has_accessories_fields:
                    print("✅ Accessories schema contains correct accessories fields")
                else:
                    print("❌ Accessories schema doesn't contain expected accessories fields!")
            else:
                print(f"❌ Accessories schema API failed: {response.status}")
        
        # Test 3: Profile Headers API
        print("\n📊 Testing Profile Headers API...")
        async with session.get(f"{base_url}/api/v1/admin/entry/profile/headers/{manufacturing_type_id}?page_type=profile") as response:
            if response.status == 200:
                headers = await response.json()
                print(f"✅ Profile headers: {len(headers)} headers")
                print(f"   First 10 headers: {headers[:10]}")
                
                # Check for profile-specific headers
                profile_headers = ['Name', 'Type', 'Company', 'Material']
                accessories_headers = ['Accessory Name', 'Accessory Type']
                
                has_profile_headers = any(header in headers for header in profile_headers)
                has_accessories_headers = any(header in headers for header in accessories_headers)
                
                if has_profile_headers and not has_accessories_headers:
                    print("✅ Profile headers contain correct profile headers")
                elif has_accessories_headers:
                    print("❌ Profile headers still contain accessories headers!")
                else:
                    print("⚠️  Profile headers don't contain expected headers")
            else:
                print(f"❌ Profile headers API failed: {response.status}")
        
        # Test 4: Accessories Headers API
        print("\n🧩 Testing Accessories Headers API...")
        async with session.get(f"{base_url}/api/v1/admin/entry/profile/headers/{manufacturing_type_id}?page_type=accessories") as response:
            if response.status == 200:
                headers = await response.json()
                print(f"✅ Accessories headers: {len(headers)} headers")
                print(f"   First 10 headers: {headers[:10]}")
                
                # Check for accessories-specific headers
                accessories_headers = ['Accessory Name', 'Accessory Type']
                has_accessories_headers = any(header in headers for header in accessories_headers)
                
                if has_accessories_headers:
                    print("✅ Accessories headers contain correct accessories headers")
                else:
                    print("❌ Accessories headers don't contain expected accessories headers!")
            else:
                print(f"❌ Accessories headers API failed: {response.status}")
    
    print("\n" + "=" * 50)
    print("🎉 Profile Page Data Mismatch Fix Test Complete!")
    print("\nThe fix should ensure that:")
    print("✅ Profile page shows profile attributes (name, type, company, material, etc.)")
    print("✅ Accessories page shows accessories attributes (accessory_name, accessory_type, etc.)")
    print("✅ Each page type is properly filtered by page_type parameter")

if __name__ == "__main__":
    asyncio.run(test_profile_page_fix())