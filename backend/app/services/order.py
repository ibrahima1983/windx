"""Order service for business logic.

This module implements business logic for order management including
order creation from quotes, status management, and item tracking.

Public Classes:
    OrderService: Order management business logic

Features:
    - Order creation from quotes
    - Order status management
    - Order item management
    - Order number generation
    - Authorization checks
"""

from __future__ import annotations

from datetime import date, datetime

from pydantic import PositiveInt
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    AuthorizationException,
    NotFoundException,
    ValidationException,
)
from app.core.rbac import Permission, Privilege, ResourceOwnership, Role, require
from app.models.order import Order
from app.repositories.order import OrderRepository
from app.repositories.quote import QuoteRepository
from app.services.base import BaseService
from app.services.rbac import RBACService

__all__ = ["OrderService"]


# Define reusable Privilege objects for Order Service operations
OrderManagement = Privilege(
    roles=[Role.SALESMAN, Role.PARTNER],
    permission=Permission("order", "create"),
    resource=ResourceOwnership("customer"),
)

OrderReader = Privilege(
    roles=[Role.CUSTOMER, Role.SALESMAN, Role.PARTNER],
    permission=Permission("order", "read"),
    resource=ResourceOwnership("order"),
)

AdminOrderAccess = Privilege(roles=Role.SUPERADMIN, permission=Permission("*", "*"))


class OrderService(BaseService):
    """Order service for business logic.

    Handles order management operations including creation from quotes,
    status management, and item tracking.

    Attributes:
        db: Database session
        order_repo: Order repository
        quote_repo: Quote repository
    """

    def __init__(self, db: AsyncSession) -> None:
        """Initialize order service.

        Args:
            db (AsyncSession): Database session
        """
        super().__init__(db)
        self.order_repo = OrderRepository(db)
        self.quote_repo = QuoteRepository(db)
        self.rbac_service = RBACService(db)

    @require(Permission("order", "create"))
    async def create_order_from_quote(
        self,
        quote_id: int,
        user: Any,
        order_date: date | None = None,
        required_date: date | None = None,
        special_instructions: str | None = None,
        installation_address: dict | None = None,
    ) -> Order:
        """Create an order from an accepted quote.

        Args:
            quote_id (int): Quote ID
            order_date (date | None): Order date (defaults to today)
            required_date (date | None): Requested delivery date
            special_instructions (str | None): Customer requests
            installation_address (dict | None): Delivery location

        Returns:
            Order: Created order instance

        Raises:
            NotFoundException: If quote not found
            ValidationException: If quote is not accepted or already has an order
        """
        # Validate quote exists
        quote = await self.quote_repo.get(quote_id)
        if not quote:
            raise NotFoundException(
                resource="Quote",
                details={"quote_id": quote_id},
            )

        # Check if quote is accepted
        if quote.status != "accepted":
            raise ValidationException(
                message="Quote must be accepted before creating an order",
                details={"quote_id": quote_id, "status": quote.status},
            )

        # Check if order already exists for this quote
        existing_order = await self.order_repo.get_by_quote(quote_id)
        if existing_order:
            raise ValidationException(
                message="Order already exists for this quote",
                details={"quote_id": quote_id, "order_id": existing_order.id},
            )

        # Generate unique order number
        order_number = await self._generate_order_number()

        # Use today's date if not provided
        if order_date is None:
            order_date = date.today()

        # Create order
        from app.schemas.order import OrderCreate

        order_data = OrderCreate(
            quote_id=quote_id,
            order_number=order_number,
            order_date=order_date,
            required_date=required_date,
            special_instructions=special_instructions,
            installation_address=installation_address,
        )

        order = await self.order_repo.create(order_data)
        await self.commit()
        await self.refresh(order)

        return order

    @require(OrderReader)
    @require(AdminOrderAccess)
    async def get_order(self, order_id: PositiveInt, user: Any = None) -> Order:
        """Get order by ID.

        Args:
            order_id (PositiveInt): Order ID

        Returns:
            Order: Order instance

        Raises:
            NotFoundException: If order not found
        """
        order = await self.order_repo.get(order_id)
        if not order:
            raise NotFoundException(
                resource="Order",
                details={"order_id": order_id},
            )
        return order

    async def get_order_with_items(self, order_id: PositiveInt) -> Order:
        """Get order with eager-loaded items.

        Args:
            order_id (PositiveInt): Order ID

        Returns:
            Order: Order instance with items

        Raises:
            NotFoundException: If order not found
        """
        order = await self.order_repo.get_with_items(order_id)
        if not order:
            raise NotFoundException(
                resource="Order",
                details={"order_id": order_id},
            )
        return order

    async def get_order_by_number(self, order_number: str) -> Order:
        """Get order by order number.

        Args:
            order_number (str): Order number

        Returns:
            Order: Order instance

        Raises:
            NotFoundException: If order not found
        """
        order = await self.order_repo.get_by_order_number(order_number)
        if not order:
            raise NotFoundException(
                resource="Order",
                details={"order_number": order_number},
            )
        return order

    async def update_order_status(self, order_id: PositiveInt, status: str) -> Order:
        """Update order status.

        Args:
            order_id (PositiveInt): Order ID
            status (str): New status (confirmed, production, shipped, installed)

        Returns:
            Order: Updated order instance

        Raises:
            NotFoundException: If order not found
            ValidationException: If status is invalid
        """
        allowed_statuses = {"confirmed", "production", "shipped", "installed"}
        if status not in allowed_statuses:
            raise ValidationException(
                message=f"Invalid status: {status}",
                details={"status": status, "allowed": list(allowed_statuses)},
            )

        order = await self.get_order(order_id)
        order.status = status

        await self.commit()
        await self.refresh(order)

        return order

    async def _generate_order_number(self) -> str:
        """Generate a unique order number.

        Returns:
            str: Unique order number in format O-YYYYMMDD-NNN
        """
        # Generate base order number with timestamp
        timestamp = datetime.now().strftime("%Y%m%d")
        base_number = f"O-{timestamp}"

        # Find the next available sequence number
        sequence = 1
        while True:
            order_number = f"{base_number}-{sequence:03d}"

            # Check if this number already exists
            existing = await self.order_repo.get_by_order_number(order_number)
            if not existing:
                return order_number

            sequence += 1

            # Safety check to prevent infinite loop
            if sequence > 999:
                # Fall back to timestamp with microseconds
                timestamp_micro = datetime.now().strftime("%Y%m%d%H%M%S%f")
                return f"O-{timestamp_micro}"

    @staticmethod
    def get_user_orders_query(user, status: str | None = None):
        """Build query for user's orders with authorization.

        Regular users see only their own orders (via quote ownership).
        Superusers see all orders.

        Args:
            user: Current user
            status (str | None): Filter by status

        Returns:
            Select: SQLAlchemy select statement
        """
        from sqlalchemy import select

        from app.models.quote import Quote

        query = select(Order)

        # Authorization: regular users see only their own
        if not user.is_superuser:
            # Join with quotes to filter by customer_id
            query = query.join(Quote, Order.quote_id == Quote.id).where(
                Quote.customer_id == user.id
            )

        # Apply filters
        if status:
            # noinspection PyTypeChecker
            query = query.where(Order.status == status)

        # Order by most recent first
        query = query.order_by(Order.created_at.desc())

        return query

    async def get_order_with_auth(self, order_id: PositiveInt, user) -> Order:
        """Get order with authorization check.

        Users can only access their own orders unless they are superusers.

        Args:
            order_id (PositiveInt): Order ID
            user: Current user

        Returns:
            Order: Order details

        Raises:
            NotFoundException: If order not found
            AuthorizationException: If user lacks permission
        """
        order = await self.order_repo.get(order_id)
        if not order:
            raise NotFoundException(
                resource="Order",
                details={"order_id": order_id},
            )

        # Get the quote to check ownership
        quote = await self.quote_repo.get(order.quote_id)
        if not quote:
            raise NotFoundException(
                resource="Quote",
                details={"quote_id": order.quote_id},
            )

        # Authorization check
        if not user.is_superuser and quote.customer_id != user.id:
            raise AuthorizationException("You do not have permission to access this order")

        return order

    async def get_order_with_items_auth(self, order_id: PositiveInt, user) -> Order:
        """Get order with items and authorization check.

        Args:
            order_id (PositiveInt): Order ID
            user: Current user

        Returns:
            Order: Order with items

        Raises:
            NotFoundException: If order not found
            AuthorizationException: If user lacks permission
        """
        order = await self.order_repo.get_with_items(order_id)
        if not order:
            raise NotFoundException(
                resource="Order",
                details={"order_id": order_id},
            )

        # Get the quote to check ownership
        quote = await self.quote_repo.get(order.quote_id)
        if not quote:
            raise NotFoundException(
                resource="Quote",
                details={"quote_id": order.quote_id},
            )

        # Authorization check
        if not user.is_superuser and quote.customer_id != user.id:
            raise AuthorizationException("You do not have permission to access this order")

        return order

    async def create_order_with_auth(self, order_request, user) -> Order:
        """Create order with authorization check.

        Args:
            order_request: Order creation request data
            user: Current user

        Returns:
            Order: Created order

        Raises:
            NotFoundException: If quote not found
            AuthorizationException: If user lacks permission
            ValidationException: If quote is not accepted
        """
        # Get quote and check authorization
        quote = await self.quote_repo.get(order_request.quote_id)
        if not quote:
            raise NotFoundException(
                resource="Quote",
                details={"quote_id": order_request.quote_id},
            )

        # Authorization check
        if not user.is_superuser and quote.customer_id != user.id:
            raise AuthorizationException(
                "You do not have permission to create an order for this quote"
            )

        # Create order
        return await self.create_order_from_quote(
            quote_id=order_request.quote_id,
            order_date=order_request.order_date,
            required_date=order_request.required_date,
            special_instructions=order_request.special_instructions,
            installation_address=order_request.installation_address,
        )
