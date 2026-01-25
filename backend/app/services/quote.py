"""Quote service for business logic.

This module implements business logic for quote management including
quote generation, pricing calculations, and status management.

Public Classes:
    QuoteService: Quote management business logic

Features:
    - Quote generation with price snapshot
    - Quote totals calculation (tax, discounts)
    - Quote status management
    - Quote number generation
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal

from pydantic import PositiveInt
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException, ValidationException
from app.core.rbac import Permission, Privilege, ResourceOwnership, Role, require
from app.models.configuration import Configuration
from app.models.quote import Quote
from app.repositories.configuration import ConfigurationRepository
from app.repositories.quote import QuoteRepository
from app.schemas.quote import QuoteCreate, QuoteUpdate
from app.services.base import BaseService
from app.services.rbac import RBACService

__all__ = ["QuoteService"]


# Define reusable Privilege objects for Quote Service operations
QuoteManagement = Privilege(
    roles=[Role.SALESMAN, Role.PARTNER],
    permission=Permission("quote", "create"),
    resource=ResourceOwnership("customer"),
)

QuoteReader = Privilege(
    roles=[Role.CUSTOMER, Role.SALESMAN, Role.PARTNER],
    permission=Permission("quote", "read"),
    resource=ResourceOwnership("quote"),
)

AdminQuoteAccess = Privilege(roles=Role.SUPERADMIN, permission=Permission("*", "*"))


class QuoteService(BaseService):
    """Quote service for business logic.

    Handles quote management operations including generation,
    calculations, and status management.

    Attributes:
        db: Database session
        quote_repo: Quote repository
        config_repo: Configuration repository
    """

    def __init__(self, db: AsyncSession) -> None:
        """Initialize quote service.

        Args:
            db (AsyncSession): Database session
        """
        super().__init__(db)
        self.quote_repo = QuoteRepository(db)
        self.config_repo = ConfigurationRepository(db)
        self.rbac_service = RBACService(db)

    @require(Permission("quote", "create"))
    async def generate_quote(
        self,
        configuration_id: int,
        user: Any,
        customer_id: int | None = None,
        tax_rate: Decimal = Decimal("0.00"),
        discount_amount: Decimal = Decimal("0.00"),
        valid_days: int = 30,
        technical_requirements: dict | None = None,
    ) -> Quote:
        """Generate a quote from a configuration.

        Creates a quote with calculated pricing including tax and discounts.
        Sets validity period and creates a price snapshot.

        Args:
            configuration_id (int): Configuration ID
            customer_id (int | None): Optional customer ID
            tax_rate (Decimal): Tax rate percentage (e.g., 8.50 for 8.5%)
            discount_amount (Decimal): Discount amount to apply
            valid_days (int): Number of days quote is valid (default 30)
            technical_requirements (dict | None): Customer-specific requirements

        Returns:
            Quote: Created quote instance

        Raises:
            NotFoundException: If configuration not found
            ValidationException: If configuration is invalid
        """
        # Validate configuration exists
        config = await self.config_repo.get(configuration_id)
        if not config:
            raise NotFoundException(
                resource="Configuration",
                details={"configuration_id": configuration_id},
            )

        # Calculate quote totals
        totals = self.calculate_quote_totals(
            subtotal=config.total_price,
            tax_rate=tax_rate,
            discount_amount=discount_amount,
        )

        # Generate unique quote number
        quote_number = await self._generate_quote_number()

        # Calculate validity date
        valid_until = date.today() + timedelta(days=valid_days)

        # Use customer_id from configuration to maintain relationship consistency
        quote_customer_id = customer_id or config.customer_id

        # Create quote
        quote_data = QuoteCreate(
            configuration_id=configuration_id,
            customer_id=quote_customer_id,
            quote_number=quote_number,
            subtotal=totals["subtotal"],
            tax_rate=tax_rate,
            tax_amount=totals["tax_amount"],
            discount_amount=discount_amount,
            total_amount=totals["total_amount"],
            technical_requirements=technical_requirements,
            valid_until=valid_until,
        )

        quote = await self.quote_repo.create(quote_data)
        await self.commit()
        await self.refresh(quote)

        # TODO: Create configuration snapshot for price protection
        # This will be implemented when ConfigurationSnapshot model is created
        # await self.create_configuration_snapshot(quote.id, config)

        return quote

    def calculate_quote_totals(
        self,
        subtotal: Decimal,
        tax_rate: Decimal,
        discount_amount: Decimal = Decimal("0.00"),
    ) -> dict[str, Decimal]:
        """Calculate quote totals with tax and discounts.

        Args:
            subtotal (Decimal): Price before tax and discounts
            tax_rate (Decimal): Tax rate percentage (e.g., 8.50 for 8.5%)
            discount_amount (Decimal): Discount amount to apply

        Returns:
            dict[str, Decimal]: Dictionary with subtotal, tax_amount, total_amount

        Raises:
            ValidationException: If values are invalid
        """
        if subtotal < 0:
            raise ValidationException(
                message="Subtotal cannot be negative",
                details={"subtotal": subtotal},
            )

        if tax_rate < 0 or tax_rate > 100:
            raise ValidationException(
                message="Tax rate must be between 0 and 100",
                details={"tax_rate": tax_rate},
            )

        if discount_amount < 0:
            raise ValidationException(
                message="Discount amount cannot be negative",
                details={"discount_amount": discount_amount},
            )

        if discount_amount > subtotal:
            raise ValidationException(
                message="Discount amount cannot exceed subtotal",
                details={"discount_amount": discount_amount, "subtotal": subtotal},
            )

        # Calculate tax amount
        tax_amount = (subtotal * tax_rate / Decimal("100")).quantize(Decimal("0.01"))

        # Calculate total amount
        total_amount = subtotal + tax_amount - discount_amount

        return {
            "subtotal": subtotal,
            "tax_amount": tax_amount,
            "total_amount": total_amount,
        }

    @require(QuoteReader)
    @require(AdminQuoteAccess)
    async def get_quote(self, quote_id: PositiveInt, user: Any = None) -> Quote:
        """Get quote by ID.

        Args:
            quote_id (PositiveInt): Quote ID

        Returns:
            Quote: Quote instance

        Raises:
            NotFoundException: If quote not found
        """
        quote = await self.quote_repo.get(quote_id)
        if not quote:
            raise NotFoundException(
                resource="Quote",
                details={"quote_id": quote_id},
            )
        return quote

    async def get_quote_by_number(self, quote_number: str) -> Quote:
        """Get quote by quote number.

        Args:
            quote_number (str): Quote number

        Returns:
            Quote: Quote instance

        Raises:
            NotFoundException: If quote not found
        """
        quote = await self.quote_repo.get_by_quote_number(quote_number)
        if not quote:
            raise NotFoundException(
                resource="Quote",
                details={"quote_number": quote_number},
            )
        return quote

    async def update_quote(self, quote_id: PositiveInt, quote_update: QuoteUpdate) -> Quote:
        """Update quote.

        Args:
            quote_id (PositiveInt): Quote ID
            quote_update (QuoteUpdate): Update data

        Returns:
            Quote: Updated quote instance

        Raises:
            NotFoundException: If quote not found
        """
        quote = await self.get_quote(quote_id)

        # Update quote fields
        update_data = quote_update.model_dump(exclude_unset=True)
        updated_quote = await self.quote_repo.update(quote, update_data)

        await self.commit()
        await self.refresh(updated_quote)

        return updated_quote

    async def update_quote_status(self, quote_id: PositiveInt, status: str) -> Quote:
        """Update quote status.

        Args:
            quote_id (PositiveInt): Quote ID
            status (str): New status (draft, sent, accepted, expired)

        Returns:
            Quote: Updated quote instance

        Raises:
            NotFoundException: If quote not found
            ValidationException: If status is invalid
        """
        allowed_statuses = {"draft", "sent", "accepted", "expired"}
        if status not in allowed_statuses:
            raise ValidationException(
                message=f"Invalid status: {status}",
                details={"status": status, "allowed": list(allowed_statuses)},
            )

        quote = await self.get_quote(quote_id)
        quote.status = status

        await self.commit()
        await self.refresh(quote)

        return quote

    @require(Permission("quote", "read"))
    async def list_quotes(
        self,
        user: Any,
        skip: int = 0,
        limit: int = 100,
        configuration_id: int | None = None,
        customer_id: int | None = None,
        status: str | None = None,
    ) -> list[Quote]:
        """List quotes with automatic RBAC filtering.

        Args:
            user: Current user for RBAC filtering
            skip (int): Number of records to skip
            limit (int): Maximum number of records to return
            configuration_id (int | None): Filter by configuration
            customer_id (int | None): Filter by customer
            status (str | None): Filter by status

        Returns:
            list[Quote]: List of quotes accessible to user
        """
        from sqlalchemy import select

        query = select(Quote)

        # Apply RBAC filtering using the same database session
        # Get accessible customers for user using existing session
        accessible_customers = await self.rbac_service.get_accessible_customers(user)

        if user.role != Role.SUPERADMIN.value:
            if not accessible_customers:
                # User has no accessible customers - return empty result
                query = query.where(False)
            else:
                # Filter by accessible customers
                query = query.where(Quote.customer_id.in_(accessible_customers))

        if configuration_id:
            query = query.where(Quote.configuration_id == configuration_id)

        if customer_id:
            query = query.where(Quote.customer_id == customer_id)

        if status:
            query = query.where(Quote.status == status)

        query = query.offset(skip).limit(limit).order_by(Quote.created_at.desc())

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def check_quote_validity(self, quote_id: PositiveInt) -> bool:
        """Check if a quote is still valid.

        Args:
            quote_id (PositiveInt): Quote ID

        Returns:
            bool: True if quote is valid, False otherwise

        Raises:
            NotFoundException: If quote not found
        """
        quote = await self.get_quote(quote_id)

        # Check if quote has expired
        if quote.valid_until and quote.valid_until < date.today():
            return False

        # Check if quote is in a valid status
        if quote.status in {"expired"}:
            return False

        return True

    async def expire_quote(self, quote_id: PositiveInt) -> Quote:
        """Mark a quote as expired.

        Args:
            quote_id (PositiveInt): Quote ID

        Returns:
            Quote: Updated quote instance

        Raises:
            NotFoundException: If quote not found
        """
        return await self.update_quote_status(quote_id, "expired")

    async def _generate_quote_number(self) -> str:
        """Generate a unique quote number.

        Returns:
            str: Unique quote number in format Q-YYYYMMDD-NNN
        """
        # Generate base quote number with timestamp
        timestamp = datetime.now().strftime("%Y%m%d")
        base_number = f"Q-{timestamp}"

        # Find the next available sequence number
        sequence = 1
        while True:
            quote_number = f"{base_number}-{sequence:03d}"

            # Check if this number already exists
            existing = await self.quote_repo.get_by_quote_number(quote_number)
            if not existing:
                return quote_number

            sequence += 1

            # Safety check to prevent infinite loop
            if sequence > 999:
                # Fall back to timestamp with microseconds
                timestamp_micro = datetime.now().strftime("%Y%m%d%H%M%S%f")
                return f"Q-{timestamp_micro}"

    async def create_configuration_snapshot(self, quote_id: int, config: Configuration) -> None:
        """Create a configuration snapshot for quote history.

        This method will create an immutable snapshot of the configuration
        at the time the quote was generated, preserving pricing and technical
        specifications for audit trail and price protection.

        Args:
            quote_id (int): Quote ID
            config (Configuration): Configuration to snapshot

        Note:
            This method is a placeholder and will be implemented when
            the ConfigurationSnapshot model is created.
        """
        # TODO: Implement when ConfigurationSnapshot model is created
        # This should:
        # 1. Create a snapshot record with all configuration data
        # 2. Store price breakdown (base + options)
        # 3. Store weight breakdown
        # 4. Store technical specifications
        # 5. Link to quote for price protection
        pass

    def get_user_quotes_query(self, user, status: str | None = None):
        """Build query for user's quotes with authorization.

        This method is used by the pagination system and needs to be synchronous.
        The RBAC filtering is now handled in the endpoint before pagination.

        Args:
            user: Current user
            status (str | None): Filter by status

        Returns:
            Select: SQLAlchemy select statement
        """
        from sqlalchemy import select

        query = select(Quote)

        # Apply filters
        if status:
            query = query.where(Quote.status == status)

        # Order by most recent first
        query = query.order_by(Quote.created_at.desc())

        return query

    async def get_quote_with_auth(self, quote_id: PositiveInt, user) -> Quote:
        """Get quote with authorization check.

        Users can only access their own quotes unless they are superusers.

        Args:
            quote_id (PositiveInt): Quote ID
            user: Current user

        Returns:
            Quote: Quote details

        Raises:
            NotFoundException: If quote not found
            AuthorizationException: If user lacks permission
        """
        from app.core.exceptions import AuthorizationException

        quote = await self.quote_repo.get(quote_id)
        if not quote:
            raise NotFoundException(
                resource="Quote",
                details={"quote_id": quote_id},
            )

        # Authorization check using RBAC service
        accessible_customers = await self.rbac_service.get_accessible_customers(user)
        if user.role != Role.SUPERADMIN.value and quote.customer_id not in accessible_customers:
            raise AuthorizationException("You do not have permission to access this quote")

        return quote

    async def create_quote_with_auth(self, quote_request, user) -> Quote:
        """Generate quote with authorization check.

        Args:
            quote_request: Quote creation request data
            user: Current user

        Returns:
            Quote: Created quote

        Raises:
            NotFoundException: If configuration not found
            AuthorizationException: If user lacks permission
        """
        from datetime import timedelta

        from app.core.exceptions import AuthorizationException

        # Get configuration and check authorization
        config = await self.config_repo.get(quote_request.configuration_id)
        if not config:
            raise NotFoundException(
                resource="Configuration",
                details={"configuration_id": quote_request.configuration_id},
            )

        # Authorization check using RBAC service
        accessible_customers = await self.rbac_service.get_accessible_customers(user)
        if user.role != Role.SUPERADMIN.value and config.customer_id not in accessible_customers:
            raise AuthorizationException(
                "You do not have permission to create a quote for this configuration"
            )

        # Calculate quote totals
        totals = self.calculate_quote_totals(
            subtotal=config.total_price,
            tax_rate=quote_request.tax_rate,
            discount_amount=quote_request.discount_amount,
        )

        # Generate unique quote number
        quote_number = await self._generate_quote_number()

        # Set valid_until if not provided (default 30 days)
        valid_until = quote_request.valid_until
        if valid_until is None:
            valid_until = date.today() + timedelta(days=30)

        # Create quote with calculated values
        quote_data = QuoteCreate(
            configuration_id=quote_request.configuration_id,
            customer_id=quote_request.customer_id or config.customer_id,
            quote_number=quote_number,
            subtotal=totals["subtotal"],
            tax_rate=quote_request.tax_rate,
            tax_amount=totals["tax_amount"],
            discount_amount=quote_request.discount_amount,
            total_amount=totals["total_amount"],
            technical_requirements=quote_request.technical_requirements,
            valid_until=valid_until,
        )

        quote = await self.quote_repo.create(quote_data)
        await self.commit()
        await self.refresh(quote)

        # TODO: Create configuration snapshot for price protection
        # await self.create_configuration_snapshot(quote.id, config)

        return quote
