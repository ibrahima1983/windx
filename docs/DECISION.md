# Relations System - Design Decision Document

## Date: January 9, 2026

## The Problem

Data entry personnel need to create hierarchical option dependencies for the profile entry page:
- **Company → Material → Opening System → System Series → Colors**

Currently, profile entry fields are independent text options without relationships. When a user selects "Kompen" as company, the Material dropdown should only show materials that exist in recorded paths for Kompen.

## The Discussion

### Initial Approach Considered: Create Separate Master Data Tables

We initially considered creating separate relational tables for each entity type:
```sql
CREATE TABLE companies (name, logo_url, price_from, ...)
CREATE TABLE materials (name, image_url, price_from, density, ...)
CREATE TABLE colors (name, picture_url, code, has_lamination, ...)
CREATE TABLE system_series (name, image_url, width, u_value, chambers, ...)
CREATE TABLE opening_systems (name, description, image_url, price_from, ...)
```

**Question Raised:** Would creating separate tables violate our EAV system design?

### Analysis: What is the EAV Pattern For?

The EAV (Entity-Attribute-Value) pattern with `AttributeNode` was designed for **dynamic, flexible product configuration** where:
- You don't know ahead of time what attributes a product will have
- New attributes can be added without schema changes
- Hierarchical relationships between options need to be maintained

### Key Insight from windows24.com Reference

We examined the windows24.com window configurator (https://www.windows24.com) as a real-world reference for how professional window/door configurators handle this exact problem.

**What we observed:**

**Screenshot 1 - Wood Material Selected:**
- User selects "Wood" material (from €122)
- System shows Profile options: Classic 68mm, Rustic 68mm, Classic 78mm, Rustic 78mm
- Each profile displays: image, name, U-value badge, construction depth, features list, price modifier (+5%, +10%, +15%)
- Left sidebar shows cascading selections: Material → Profile → Type of wood → Colour → Type of window → Opening system

**Screenshot 2 - uPVC Material Selected:**
- User selects "uPVC" material (from €36)
- System shows System/Brand options: Aluplast, Kömmerling (each with logo and "from €34")
- Then Profile options appear based on system selection (IDEAL 4000 - 5-chamber-system with 2 seals)
- Different hierarchy path than Wood: Material → System → Profile → Colour and Decor → Type of window

**Key Observations:**
1. Materials have images and "from €XX" starting prices
2. Systems/Brands have logos and prices
3. Profiles have detailed specs (U-value, chambers, construction depth)
4. Colors have visual swatches
5. **The available options cascade based on previous selections** - exactly our requirement
6. **Each option is essentially a configuration choice with rich metadata** (image, price, specs)

**These ARE configuration options** - they just happen to have rich metadata (images, specs, prices). This is NOT traditional master data like company addresses or tax IDs.

The hierarchy we need (Company → Material → Opening System → System Series → Colors) is exactly what the EAV pattern with LTREE was designed to handle. The windows24.com implementation confirms this approach is industry-standard for window/door configurators.

## The Decision

### Use Existing EAV Pattern with Minimal Extension

**Extend AttributeNode with ONE new field:**
```python
image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
```

**Use existing fields for everything else:**

| Data Need | AttributeNode Field |
|-----------|---------------------|
| Entity name | `name` |
| Entity type | `node_type` ('company', 'material', 'opening_system', 'system_series', 'color') |
| Hierarchy level | `depth` (0=Company, 1=Material, 2=Opening System, 3=System Series, 4=Color) |
| Dependency path | `ltree_path` (e.g., "kompen.upvc.casement.k700.white") |
| Price (from €XX) | `price_impact_value` |
| Image | `image_url` (NEW) |
| Description | `description` |
| Extra metadata | `validation_rules` JSONB (u_value, chambers, density, code, has_lamination, etc.) |

### LTREE Path Structure

```
# Company level (depth=0, node_type='company')
kompen
rehau

# Material level (depth=1, node_type='material')
kompen.upvc
kompen.aluminum

# Opening System level (depth=2, node_type='opening_system')
kompen.upvc.casement
kompen.upvc.sliding

# System Series level (depth=3, node_type='system_series')
kompen.upvc.casement.k700
kompen.upvc.casement.k600

# Color level (depth=4, node_type='color')
kompen.upvc.casement.k700.white
kompen.upvc.casement.k700.brown
```

### Metadata Storage in validation_rules JSONB

```json
// For a Material (e.g., UPVC)
{
  "density": 1.4,
  "is_relation_entity": true
}

// For a System Series (e.g., K700)
{
  "width": 70.0,
  "number_of_chambers": 5,
  "u_value": 1.1,
  "number_of_seals": 3,
  "characteristics": "Premium",
  "is_relation_entity": true
}

// For a Color (e.g., White)
{
  "code": "RAL9016",
  "has_lamination": false,
  "is_relation_entity": true
}
```

## Why This Decision is Better

### 1. Consistency with Existing System
- Uses the same pattern already proven in the codebase
- No paradigm shift for developers
- Leverages existing LTREE indexes and query patterns

### 2. No New Tables Required
- Single schema change (add `image_url` column)
- No new migrations for multiple tables
- No new relationships to manage

### 3. Leverages Existing Infrastructure
- LTREE GiST indexes already exist for fast hierarchical queries
- JSONB indexes already exist for metadata queries
- Existing services (EntryService) can be extended, not rewritten

### 4. Flexibility
- Easy to add new entity types (just new `node_type` values)
- Easy to add new metadata fields (just add to JSONB)
- Hierarchy depth can be extended without schema changes

### 5. Matches the Domain
- windows24.com reference confirms this IS a configuration hierarchy problem
- Companies, Materials, Colors ARE configuration options with rich metadata
- They are NOT traditional master data (no addresses, tax IDs, contacts)

## What We Will NOT Do

1. ❌ Create separate tables for companies, materials, colors, etc.
2. ❌ Create a complex relationship mapping system
3. ❌ Add multiple new columns to AttributeNode for each metadata type

## What We WILL Do

1. ✅ Add `image_url` column to AttributeNode
2. ✅ Use new `node_type` values: 'company', 'material', 'opening_system', 'system_series', 'color', 'unit_type'
3. ✅ Store entity-specific metadata in `validation_rules` JSONB
4. ✅ Use `price_impact_value` for "from €XX" pricing
5. ✅ Use LTREE paths for dependency relationships
6. ✅ Create Relations page with card-based UI for data entry
7. ✅ Remove add/remove option UI from profile entry page
8. ✅ Implement cascading dropdowns in profile entry

## Summary

The EAV pattern with AttributeNode and LTREE was designed exactly for this use case. We don't need to create separate master data tables because our "entities" (Companies, Materials, Colors) are actually **configuration options with rich metadata**, not traditional master data.

By extending AttributeNode with just one field (`image_url`) and using existing fields creatively, we maintain system consistency while solving the hierarchical dependency problem.
