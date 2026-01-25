"""Customer management endpoints.

This module provides REST API endpoints for managing customers.

Public Variables:
    router: FastAPI router for customer endpoints

Features:
    - List customers (superuser only)
    - Get customer by ID (superuser only)
    - Create customer (superuser only)
    - Update customer (superuser only)
    - OpenAPI documentation with examples
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from pydantic import PositiveInt

from app.api.types import CurrentSuperuser, DBSession
from app.core.pagination import Page, PaginationParams, create_pagination_params
from app.models.customer import Customer
from app.schemas.customer import Customer as CustomerSchema
from app.schemas.customer import CustomerCreate, CustomerUpdate
from app.schemas.responses import get_common_responses

__all__ = ["router"]

router = APIRouter(
    tags=["Customers"],
    responses=get_common_responses(401, 403, 500),
)


@router.get(
    "/",
    response_model=Page[CustomerSchema],
    summary="List Customers",
    description="List all customers with pagination (superuser only)",
    response_description="Paginated list of customers",
    operation_id="listCustomers",
    responses={
        200: {
            "description": "Successfully retrieved customers",
        },
        **get_common_responses(401, 403, 500),
    },
)
async def list_customers(
    current_superuser: CurrentSuperuser,
    params: Annotated[PaginationParams, Depends(create_pagination_params)],
    db: DBSession,
    is_active: Annotated[
        bool | None,
        Query(description="Filter by active status"),
    ] = None,
    customer_type: Annotated[
        str | None,
        Query(description="Filter by customer type"),
    ] = None,
) -> Page[Customer]:
    """List all customers with filtering (superuser only).

    Args:
        current_superuser (User): Current authenticated superuser
        params (PaginationParams): Pagination parameters
        db (AsyncSession): Database session
        is_active (bool | None): Filter by active status
        customer_type (str | None): Filter by customer type

    Returns:
        Page[Customer]: Paginated list of customers

    Example:
        GET /api/v1/customers?is_active=true&customer_type=commercial
    """
    from app.core.pagination import paginate
    from app.repositories.customer import CustomerRepository

    customer_repo = CustomerRepository(db)

    query = customer_repo.get_filtered(
        is_active=is_active,
        customer_type=customer_type,
    )

    return await paginate(db, query, params)


@router.get(
    "/{customer_id}",
    response_model=CustomerSchema,
    summary="Get Customer",
    description="Get a single customer by ID (superuser only)",
    response_description="Customer details",
    operation_id="getCustomer",
    responses={
        200: {
            "description": "Successfully retrieved customer",
        },
        404: {
            "description": "Customer not found",
        },
        **get_common_responses(401, 403, 500),
    },
)
async def get_customer(
    customer_id: PositiveInt,
    current_superuser: CurrentSuperuser,
    db: DBSession,
) -> Customer:
    """Get customer by ID (superuser only).

    Args:
        customer_id (PositiveInt): Customer ID
        current_superuser (User): Current authenticated superuser
        db (AsyncSession): Database session

    Returns:
        Customer: Customer details

    Raises:
        NotFoundException: If customer not found
    """
    from app.core.exceptions import NotFoundException
    from app.repositories.customer import CustomerRepository

    customer_repo = CustomerRepository(db)
    customer = await customer_repo.get(customer_id)

    if not customer:
        raise NotFoundException("Customer not found")

    return customer


@router.post(
    "/",
    response_model=CustomerSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create Customer",
    description="Create a new customer (superuser only)",
    response_description="Created customer",
    operation_id="createCustomer",
    responses={
        201: {
            "description": "Customer successfully created",
        },
        409: {
            "description": "Email already exists",
        },
        **get_common_responses(401, 403, 422, 500),
    },
)
async def create_customer(
    customer_in: CustomerCreate,
    current_superuser: CurrentSuperuser,
    db: DBSession,
) -> Customer:
    """Create a new customer (superuser only).

    Args:
        customer_in (CustomerCreate): Customer creation data
        current_superuser (User): Current authenticated superuser
        db (AsyncSession): Database session

    Returns:
        Customer: Created customer

    Raises:
        ConflictException: If email already exists
        AuthorizationException: If user is not superuser

    Example:
        POST /api/v1/customers
        {
            "company_name": "ABC Construction",
            "contact_person": "John Doe",
            "email": "john@abc.com",
            "phone": "555-1234",
            "customer_type": "commercial"
        }
    """
    from app.core.exceptions import ConflictException
    from app.repositories.customer import CustomerRepository

    customer_repo = CustomerRepository(db)

    # Check if email already exists
    if customer_in.email:
        existing = await customer_repo.get_by_email(customer_in.email)
        if existing:
            raise ConflictException("Customer with this email already exists")

    # Create customer
    customer = await customer_repo.create(customer_in)
    await db.commit()
    await db.refresh(customer)

    return customer


@router.patch(
    "/{customer_id}",
    response_model=CustomerSchema,
    summary="Update Customer",
    description="Update an existing customer (superuser only)",
    response_description="Updated customer",
    operation_id="updateCustomer",
    responses={
        200: {
            "description": "Customer successfully updated",
        },
        404: {
            "description": "Customer not found",
        },
        409: {
            "description": "Email already exists",
        },
        **get_common_responses(401, 403, 422, 500),
    },
)
async def update_customer(
    customer_id: PositiveInt,
    customer_update: CustomerUpdate,
    current_superuser: CurrentSuperuser,
    db: DBSession,
) -> Customer:
    """Update customer (superuser only).

    Args:
        customer_id (PositiveInt): Customer ID
        customer_update (CustomerUpdate): Update data
        current_superuser (User): Current authenticated superuser
        db (AsyncSession): Database session

    Returns:
        Customer: Updated customer

    Raises:
        NotFoundException: If customer not found
        ConflictException: If email conflicts
        AuthorizationException: If user is not superuser

    Example:
        PATCH /api/v1/customers/1
        {
            "contact_person": "Jane Doe",
            "phone": "555-5678"
        }
    """
    from app.core.exceptions import ConflictException, NotFoundException
    from app.repositories.customer import CustomerRepository

    customer_repo = CustomerRepository(db)

    # Get existing customer
    customer = await customer_repo.get(customer_id)
    if not customer:
        raise NotFoundException("Customer not found")

    # Check email uniqueness if email is being updated
    if customer_update.email and customer_update.email != customer.email:
        existing = await customer_repo.get_by_email(customer_update.email)
        if existing:
            raise ConflictException("Customer with this email already exists")

    # Update customer
    updated_customer = await customer_repo.update(customer, customer_update)
    await db.commit()
    await db.refresh(updated_customer)

    return updated_customer
