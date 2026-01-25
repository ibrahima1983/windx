#!/usr/bin/env python3

import asyncio

from app.core.rbac import Role, require
from app.models.user import User


async def test_customer_decorator():
    """Test customer decorator logic."""

    # Create user with customer role
    user = User()
    user.id = 1
    user.email = "test-customer@example.com"
    user.role = "customer"

    # Create function with multiple @require decorators (OR logic)
    @require(Role.CUSTOMER)  # First requirement
    @require(Role.SALESMAN)  # Second requirement (OR logic)
    async def test_function(user: User):
        return "success"

    print(f"User role: {user.role}")
    print("Expected: Should pass because user is customer")

    try:
        result = await test_function(user)
        print(f"Result: {result}")
        print("SUCCESS: Decorator worked correctly")
        return True
    except Exception as e:
        print(f"FAILED: {e}")
        return False


if __name__ == "__main__":
    asyncio.run(test_customer_decorator())
