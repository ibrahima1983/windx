"""Manager utility functions for sample data management.

This module provides functions to create and delete sample manufacturing data
with hierarchical attribute nodes for testing and demonstration purposes.
"""

from __future__ import annotations

import random
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from _manager_factory import (
    ATTRIBUTES,
    BOOLEAN_OPTIONS,
    CATEGORIES,
    MANUFACTURING_TYPES,
    OPTIONS,
    PRICE_FORMULAS,
    PRICE_IMPACT_TYPE_WEIGHTS,
    PRICE_IMPACT_TYPES,
    WEIGHT_FORMULAS,
)
from app.models.attribute_node import AttributeNode
from app.models.manufacturing_type import ManufacturingType


async def create_factory_manufacturing_data(
    db: AsyncSession,
    depth: int = 3,
    root_leaves: int = 3,
    mfg_type_index: int | None = None,
) -> dict[str, Any]:
    """Create manufacturing data using factory with configurable depth and breadth.

    Generates a complete product hierarchy with randomized but realistic data
    from pre-defined pools in _manager_factory.py.

    Args:
        db: Database session
        depth: Maximum depth of the hierarchy (0-based, default: 3)
               0 = categories only
               1 = categories + attributes
               2 = categories + attributes + options
               3+ = deeper nesting with sub-options
        root_leaves: Number of root categories to create (default: 3)
        mfg_type_index: Index of manufacturing type from factory (None = random)

    Returns:
        dict: Created data summary with statistics

    Example:
        # Create shallow hierarchy (2 levels, 2 root categories)
        await create_factory_manufacturing_data(db, depth=2, root_leaves=2)

        # Create deep hierarchy (4 levels, 5 root categories)
        await create_factory_manufacturing_data(db, depth=4, root_leaves=5)
    """
    # Select manufacturing type
    if mfg_type_index is None:
        mfg_template = random.choice(MANUFACTURING_TYPES)
    else:
        mfg_template = MANUFACTURING_TYPES[mfg_type_index % len(MANUFACTURING_TYPES)]

    # Create manufacturing type with randomized price/weight
    base_price_range = mfg_template["base_price"]
    base_weight_range = mfg_template["base_weight"]

    mfg_type = ManufacturingType(
        name=f"Factory {mfg_template['name']}",
        description=mfg_template["description"],
        base_category=mfg_template["base_category"],
        image_url=f"/images/factory-{mfg_template['name'].lower().replace(' ', '-')}.jpg",
        base_price=Decimal(str(random.uniform(*base_price_range))),
        base_weight=Decimal(str(random.uniform(*base_weight_range))),
        is_active=True,
    )
    db.add(mfg_type)
    await db.flush()

    created_nodes = []
    node_counter = {"count": 0}

    # Helper function to create nodes recursively
    async def create_node_recursive(
        parent_id: int | None,
        parent_path: str | None,
        current_depth: int,
        category_name: str | None = None,
    ) -> None:
        """Recursively create nodes up to specified depth."""
        if current_depth > depth:
            return

        # Depth 0: Create root categories
        if current_depth == 0:
            # Select random categories for root leaves
            selected_categories = random.sample(CATEGORIES, min(root_leaves, len(CATEGORIES)))

            for idx, cat_template in enumerate(selected_categories):
                node_path = cat_template["name"].lower().replace(" ", "_")

                category_node = AttributeNode(
                    manufacturing_type_id=mfg_type.id,
                    parent_node_id=None,
                    name=cat_template["name"],
                    node_type="category",
                    data_type="string",
                    required=False,
                    price_impact_type="fixed",
                    price_impact_value=Decimal("0.00"),
                    weight_impact=Decimal("0.00"),
                    ltree_path=node_path,
                    depth=0,
                    sort_order=idx,
                    ui_component=cat_template["ui_component"],
                    description=cat_template["description"],
                )
                db.add(category_node)
                await db.flush()
                created_nodes.append(category_node)
                node_counter["count"] += 1

                # Recurse to create children
                await create_node_recursive(
                    category_node.id,
                    node_path,
                    current_depth + 1,
                    cat_template["name"],
                )

        # Depth 1: Create attributes under categories
        elif current_depth == 1:
            if category_name not in ATTRIBUTES:
                return

            # Get attributes for this category
            attr_templates = ATTRIBUTES[category_name]
            # Randomly select 2-4 attributes
            num_attrs = random.randint(2, min(4, len(attr_templates)))
            selected_attrs = random.sample(attr_templates, num_attrs)

            for idx, attr_template in enumerate(selected_attrs):
                attr_path = f"{parent_path}.{attr_template['name'].lower().replace(' ', '_')}"

                attribute_node = AttributeNode(
                    manufacturing_type_id=mfg_type.id,
                    parent_node_id=parent_id,
                    name=attr_template["name"],
                    node_type="attribute",
                    data_type=attr_template["data_type"],
                    required=attr_template["required"],
                    price_impact_type="fixed",
                    price_impact_value=Decimal("0.00"),
                    weight_impact=Decimal("0.00"),
                    ltree_path=attr_path,
                    depth=1,
                    sort_order=idx,
                    ui_component=attr_template["ui_component"],
                    description=attr_template["description"],
                    help_text=attr_template.get("help_text"),
                )
                db.add(attribute_node)
                await db.flush()
                created_nodes.append(attribute_node)
                node_counter["count"] += 1

                # Recurse to create options
                await create_node_recursive(
                    attribute_node.id,
                    attr_path,
                    current_depth + 1,
                    attr_template["name"],
                )

        # Depth 2+: Create options under attributes
        elif current_depth >= 2:
            # For boolean attributes, create Yes/No options
            parent_node = next((n for n in created_nodes if n.id == parent_id), None)
            if not parent_node:
                return

            if parent_node.data_type == "boolean":
                option_templates = BOOLEAN_OPTIONS
            elif category_name in OPTIONS:
                option_templates = OPTIONS[category_name]
            else:
                # No options defined for this attribute
                return

            # Randomly select options (2-5 for selection types, all for boolean)
            if parent_node.data_type == "boolean":
                selected_options = option_templates
            else:
                num_options = random.randint(2, min(5, len(option_templates)))
                selected_options = random.sample(option_templates, num_options)

            for idx, opt_template in enumerate(selected_options):
                opt_path = f"{parent_path}.{opt_template['name'].lower().replace(' ', '_')}"

                # Randomize price and weight within range
                price_range = opt_template.get("price_range", (0.00, 0.00))
                weight_range = opt_template.get("weight_range", (0.00, 0.00))

                # Select price impact type
                price_impact_type = random.choices(
                    PRICE_IMPACT_TYPES, weights=PRICE_IMPACT_TYPE_WEIGHTS
                )[0]

                # Calculate price impact value or formula
                if price_impact_type == "fixed":
                    price_impact_value = Decimal(str(random.uniform(*price_range)))
                    price_formula = None
                elif price_impact_type == "percentage":
                    # Convert price to percentage (e.g., $50 on $200 base = 25%)
                    price_impact_value = Decimal(str(random.uniform(5, 25)))
                    price_formula = None
                else:  # formula
                    price_impact_value = None
                    formula_template = random.choice(PRICE_FORMULAS)
                    factor = random.uniform(0.01, 0.15)
                    price_formula = formula_template.format(factor=f"{factor:.4f}")

                # Weight formula (10% chance)
                weight_formula = None
                if random.random() < 0.1:
                    formula_template = random.choice(WEIGHT_FORMULAS)
                    factor = random.uniform(0.001, 0.05)
                    weight_formula = formula_template.format(factor=f"{factor:.4f}")
                    weight_impact = Decimal("0.00")
                else:
                    weight_impact = Decimal(str(random.uniform(*weight_range)))

                option_node = AttributeNode(
                    manufacturing_type_id=mfg_type.id,
                    parent_node_id=parent_id,
                    name=opt_template["name"],
                    node_type="option",
                    data_type=parent_node.data_type,
                    required=False,
                    price_impact_type=price_impact_type,
                    price_impact_value=price_impact_value,
                    price_formula=price_formula,
                    weight_impact=weight_impact,
                    weight_formula=weight_formula,
                    ltree_path=opt_path,
                    depth=current_depth,
                    sort_order=idx,
                    ui_component=parent_node.ui_component,
                    description=opt_template.get("description"),
                    help_text=opt_template.get("help_text"),
                )
                db.add(option_node)
                await db.flush()
                created_nodes.append(option_node)
                node_counter["count"] += 1

                # For deeper hierarchies, potentially create sub-options
                if current_depth < depth and random.random() < 0.3:
                    # 30% chance to create sub-options
                    await create_node_recursive(
                        option_node.id,
                        opt_path,
                        current_depth + 1,
                        category_name,
                    )

    # Start recursive creation
    await create_node_recursive(None, None, 0)

    await db.commit()

    # Calculate statistics
    nodes_by_depth = {}
    nodes_by_type = {}

    for node in created_nodes:
        nodes_by_depth[node.depth] = nodes_by_depth.get(node.depth, 0) + 1
        nodes_by_type[node.node_type] = nodes_by_type.get(node.node_type, 0) + 1

    return {
        "manufacturing_type_id": mfg_type.id,
        "manufacturing_type_name": mfg_type.name,
        "base_price": float(mfg_type.base_price),
        "base_weight": float(mfg_type.base_weight),
        "total_nodes": len(created_nodes),
        "max_depth": depth,
        "root_leaves": root_leaves,
        "nodes_by_depth": nodes_by_depth,
        "nodes_by_type": nodes_by_type,
        "deepest_path": max((node.ltree_path for node in created_nodes), key=lambda x: x.count("."))
        if created_nodes
        else None,
    }


async def delete_factory_manufacturing_data(
    db: AsyncSession, name_pattern: str = "Factory %"
) -> dict[str, Any]:
    """Delete factory-generated manufacturing data.

    Deletes all manufacturing types matching the pattern (default: "Factory %")
    and their associated attribute nodes (cascade delete).

    Args:
        db: Database session
        name_pattern: SQL LIKE pattern for matching names (default: "Factory %")

    Returns:
        dict: Deletion summary with counts
    """
    # Find all factory manufacturing types
    result = await db.execute(
        select(ManufacturingType).where(ManufacturingType.name.like(name_pattern))
    )
    mfg_types = result.scalars().all()

    if not mfg_types:
        return {
            "deleted": False,
            "message": f"No manufacturing types found matching pattern: {name_pattern}",
            "deleted_types": 0,
            "deleted_nodes": 0,
        }

    total_nodes = 0
    deleted_types = []

    for mfg_type in mfg_types:
        # Count nodes
        node_result = await db.execute(
            select(AttributeNode).where(AttributeNode.manufacturing_type_id == mfg_type.id)
        )
        nodes = node_result.scalars().all()
        total_nodes += len(nodes)
        deleted_types.append({"id": mfg_type.id, "name": mfg_type.name, "nodes": len(nodes)})

        # Delete the manufacturing type (cascade will delete nodes)
        await db.delete(mfg_type)

    await db.commit()

    return {
        "deleted": True,
        "message": f"Deleted {len(mfg_types)} factory manufacturing types",
        "deleted_types": len(mfg_types),
        "deleted_nodes": total_nodes,
        "types": deleted_types,
    }


async def delete_all_sample_data(db: AsyncSession) -> dict[str, Any]:
    """Delete ALL sample and factory-generated manufacturing data.

    This is a convenience function that removes all test data created by:
    - create_sample_manufacturing_data()
    - create_factory_manufacturing_data()

    Useful for cleaning up the database before production or after testing.

    Args:
        db: Database session

    Returns:
        dict: Comprehensive deletion summary
    """
    result = await delete_factory_manufacturing_data(db, name_pattern="Factory %")

    if result["deleted"]:
        return {
            "deleted": True,
            "message": "All sample/factory data deleted successfully",
            "total_types_deleted": result["deleted_types"],
            "total_nodes_deleted": result["deleted_nodes"],
            "details": result["types"],
        }
    else:
        return {
            "deleted": False,
            "message": "No sample/factory data found to delete",
            "total_types_deleted": 0,
            "total_nodes_deleted": 0,
        }


async def create_factory_customers(
    db: AsyncSession,
    count: int = 10,
) -> dict[str, Any]:
    """Create factory-generated customer data.

    Generates realistic customer records with randomized data including:
    - Company names and contact persons
    - Email addresses and phone numbers
    - Addresses (JSONB format)
    - Customer types (residential, commercial, contractor)
    - Tax IDs and payment terms

    Args:
        db: Database session
        count: Number of customers to create (default: 10)

    Returns:
        dict: Created data summary with customer IDs

    Example:
        # Create 20 customers
        await create_factory_customers(db, count=20)
    """
    from app.models.customer import Customer

    # Sample data pools
    company_prefixes = ["ABC", "XYZ", "Premier", "Elite", "Global", "Metro", "Urban", "Coastal"]
    company_suffixes = [
        "Construction",
        "Builders",
        "Contractors",
        "Homes",
        "Properties",
        "Development",
    ]
    first_names = [
        "John",
        "Jane",
        "Michael",
        "Sarah",
        "David",
        "Emily",
        "Robert",
        "Lisa",
        "James",
        "Maria",
    ]
    last_names = [
        "Smith",
        "Johnson",
        "Williams",
        "Brown",
        "Jones",
        "Garcia",
        "Miller",
        "Davis",
        "Rodriguez",
        "Martinez",
    ]
    streets = [
        "Main St",
        "Oak Ave",
        "Maple Dr",
        "Pine Rd",
        "Cedar Ln",
        "Elm St",
        "Park Ave",
        "Lake Dr",
    ]
    cities = [
        "Springfield",
        "Riverside",
        "Fairview",
        "Georgetown",
        "Madison",
        "Franklin",
        "Clinton",
        "Salem",
    ]
    states = ["CA", "TX", "FL", "NY", "IL", "PA", "OH", "GA", "NC", "MI"]
    customer_types = ["residential", "commercial", "contractor"]
    payment_terms = ["net_30", "net_15", "net_45", "cod", "net_60"]

    created_customers = []

    for i in range(count):
        # Determine customer type
        customer_type = random.choice(customer_types)

        # Generate name based on type
        if customer_type == "residential":
            first_name = random.choice(first_names)
            last_name = random.choice(last_names)
            company_name = None
            contact_person = f"{first_name} {last_name}"
            email = f"{first_name.lower()}.{last_name.lower()}{i}@email.com"
        else:
            company_prefix = random.choice(company_prefixes)
            company_suffix = random.choice(company_suffixes)
            company_name = f"Factory {company_prefix} {company_suffix}"
            first_name = random.choice(first_names)
            last_name = random.choice(last_names)
            contact_person = f"{first_name} {last_name}"
            email = f"{first_name.lower()}.{last_name.lower()}@{company_prefix.lower()}{company_suffix.lower()}.com"

        # Generate address
        address = {
            "street": f"{random.randint(100, 9999)} {random.choice(streets)}",
            "city": random.choice(cities),
            "state": random.choice(states),
            "zip": f"{random.randint(10000, 99999)}",
            "country": "USA",
        }

        # Generate phone
        phone = (
            f"+1-{random.randint(200, 999)}-{random.randint(200, 999)}-{random.randint(1000, 9999)}"
        )

        # Generate tax ID for business customers
        tax_id = None
        if customer_type in ["commercial", "contractor"]:
            tax_id = f"{random.randint(10, 99)}-{random.randint(1000000, 9999999)}"

        # Create customer
        customer = Customer(
            company_name=company_name,
            contact_person=contact_person,
            email=email,
            phone=phone,
            address=address,
            customer_type=customer_type,
            tax_id=tax_id,
            payment_terms=random.choice(payment_terms) if customer_type != "residential" else None,
            is_active=True,
            notes=f"Factory-generated {customer_type} customer for testing",
        )

        db.add(customer)
        created_customers.append(customer)

    await db.commit()

    # Refresh to get IDs
    for customer in created_customers:
        await db.refresh(customer)

    # Calculate statistics
    customers_by_type = {}
    for customer in created_customers:
        customers_by_type[customer.customer_type] = (
            customers_by_type.get(customer.customer_type, 0) + 1
        )

    return {
        "total_customers": len(created_customers),
        "customers_by_type": customers_by_type,
        "customer_ids": [c.id for c in created_customers],
        "sample_emails": [c.email for c in created_customers[:5]],
    }


async def delete_factory_customers(db: AsyncSession, email_pattern: str = "%@%") -> dict[str, Any]:
    """Delete factory-generated customer data.

    Deletes all customers matching the email pattern (default: all customers).
    Use with caution in production environments.

    Args:
        db: Database session
        email_pattern: SQL LIKE pattern for matching emails (default: "%@%")

    Returns:
        dict: Deletion summary with counts
    """
    from app.models.customer import Customer

    # Find all matching customers
    result = await db.execute(select(Customer).where(Customer.email.like(email_pattern)))
    customers = result.scalars().all()

    if not customers:
        return {
            "deleted": False,
            "message": f"No customers found matching pattern: {email_pattern}",
            "deleted_customers": 0,
        }

    deleted_count = len(customers)
    deleted_types = {}

    for customer in customers:
        deleted_types[customer.customer_type] = deleted_types.get(customer.customer_type, 0) + 1
        await db.delete(customer)

    await db.commit()

    return {
        "deleted": True,
        "message": f"Deleted {deleted_count} factory customers",
        "deleted_customers": deleted_count,
        "deleted_by_type": deleted_types,
    }
