"""Policy management API endpoints.

This module provides API endpoints for policy management operations
including dynamic policy updates, customer assignments, and policy
backup/restore functionality. All endpoints require superadmin privileges.

Endpoints:
    POST /policies - Add new policy
    DELETE /policies - Remove policy
    POST /policies/assign-customer - Assign customer to user
    DELETE /policies/assign-customer - Remove customer assignment
    POST /policies/assign-role - Assign role to user
    GET /policies/summary - Get policy summary
    POST /policies/backup - Create policy backup
    POST /policies/restore - Restore policies from backup
    POST /policies/validate - Validate current policies
    POST /policies/seed - Seed initial policies

Requirements: 6.1, 6.2, 6.3, 9.3
"""

from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.api.types import CurrentSuperuser, DBSession
from app.core.rbac import Role
from app.services.policy_manager import PolicyManager

__all__ = ["router"]

router = APIRouter(prefix="/policies", tags=["Policy Management"])


# Request/Response Models
class PolicyRequest(BaseModel):
    """Request model for policy operations."""

    subject: str = Field(..., description="Subject (role or user) for the policy")
    resource: str = Field(..., description="Resource the policy applies to")
    action: str = Field(..., description="Action the policy allows/denies")
    effect: str = Field(default="allow", description="Effect of the policy (allow/deny)")


class CustomerAssignmentRequest(BaseModel):
    """Request model for customer assignment operations."""

    user_email: str = Field(..., description="Email of user to assign customer to")
    customer_id: int = Field(..., description="ID of customer to assign")
    assignment_type: str = Field(default="assigned", description="Type of assignment")


class RoleAssignmentRequest(BaseModel):
    """Request model for role assignment operations."""

    user_email: str = Field(..., description="Email of user to assign role to")
    role: Role = Field(..., description="Role to assign")


class PolicyBackupResponse(BaseModel):
    """Response model for policy backup operations."""

    timestamp: str
    policies: list[list[str]]
    grouping_policies: list[list[str]]
    metadata: dict[str, Any]


class PolicyValidationResponse(BaseModel):
    """Response model for policy validation."""

    valid: bool
    issues: list[dict[str, Any]]
    warnings: list[dict[str, Any]]
    statistics: dict[str, Any]


class PolicySummaryResponse(BaseModel):
    """Response model for policy summary."""

    policies_by_role: dict[str, list[dict[str, str]]]
    role_assignments: dict[str, list[str]]
    customer_assignments: dict[str, list[int]]
    statistics: dict[str, Any]


# Policy Management Endpoints
@router.post("/", status_code=status.HTTP_201_CREATED)
async def add_policy(
    policy_request: PolicyRequest, current_superuser: CurrentSuperuser, db: DBSession
) -> dict[str, Any]:
    """Add a new policy rule.

    Requires superadmin privileges. Creates a new policy rule in the Casbin
    policy engine and logs the change for audit purposes.

    Args:
        policy_request: Policy details to add
        current_superuser: Current authenticated superuser
        db: Database session

    Returns:
        Success message and policy details

    Raises:
        HTTPException: If policy addition fails or user lacks privileges
    """
    policy_manager = PolicyManager(db)

    result = await policy_manager.add_policy(
        subject=policy_request.subject,
        resource=policy_request.resource,
        action=policy_request.action,
        effect=policy_request.effect,
    )

    if not result:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Policy already exists")

    return {
        "message": "Policy added successfully",
        "policy": {
            "subject": policy_request.subject,
            "resource": policy_request.resource,
            "action": policy_request.action,
            "effect": policy_request.effect,
        },
    }


@router.delete("/")
async def remove_policy(
    policy_request: PolicyRequest, current_superuser: CurrentSuperuser, db: DBSession
) -> dict[str, Any]:
    """Remove a policy rule.

    Requires superadmin privileges. Removes an existing policy rule from the
    Casbin policy engine and logs the change for audit purposes.

    Args:
        policy_request: Policy details to remove
        db: Database session
        current_user: Current authenticated user (must be superadmin)

    Returns:
        Success message and policy details

    Raises:
        HTTPException: If policy removal fails or user lacks privileges
    """
    policy_manager = PolicyManager(db)

    result = await policy_manager.remove_policy(
        subject=policy_request.subject,
        resource=policy_request.resource,
        action=policy_request.action,
        effect=policy_request.effect,
    )

    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy not found")

    return {
        "message": "Policy removed successfully",
        "policy": {
            "subject": policy_request.subject,
            "resource": policy_request.resource,
            "action": policy_request.action,
            "effect": policy_request.effect,
        },
    }


@router.post("/assign-customer", status_code=status.HTTP_201_CREATED)
async def assign_customer_to_user(
    assignment_request: CustomerAssignmentRequest,
    current_superuser: CurrentSuperuser,
    db: DBSession,
) -> dict[str, Any]:
    """Assign customer access to a user.

    Requires superadmin privileges. Assigns customer access to a user
    (typically for salesmen or partners) and logs the assignment.

    Args:
        assignment_request: Customer assignment details
        db: Database session
        current_user: Current authenticated user (must be superadmin)

    Returns:
        Success message and assignment details

    Raises:
        HTTPException: If assignment fails or user lacks privileges
    """
    policy_manager = PolicyManager(db)

    result = await policy_manager.assign_customer_to_user(
        user_email=assignment_request.user_email,
        customer_id=assignment_request.customer_id,
        assignment_type=assignment_request.assignment_type,
    )

    if not result:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Customer assignment already exists"
        )

    return {
        "message": "Customer assigned successfully",
        "assignment": {
            "user_email": assignment_request.user_email,
            "customer_id": assignment_request.customer_id,
            "assignment_type": assignment_request.assignment_type,
        },
    }


@router.delete("/assign-customer")
async def remove_customer_assignment(
    assignment_request: CustomerAssignmentRequest,
    current_superuser: CurrentSuperuser,
    db: DBSession,
) -> dict[str, Any]:
    """Remove customer assignment from a user.

    Requires superadmin privileges. Removes customer access from a user
    and logs the change for audit purposes.

    Args:
        assignment_request: Customer assignment details to remove
        db: Database session
        current_user: Current authenticated user (must be superadmin)

    Returns:
        Success message and assignment details

    Raises:
        HTTPException: If removal fails or user lacks privileges
    """
    policy_manager = PolicyManager(db)

    result = await policy_manager.remove_customer_assignment(
        user_email=assignment_request.user_email, customer_id=assignment_request.customer_id
    )

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Customer assignment not found"
        )

    return {
        "message": "Customer assignment removed successfully",
        "assignment": {
            "user_email": assignment_request.user_email,
            "customer_id": assignment_request.customer_id,
        },
    }


@router.post("/assign-role", status_code=status.HTTP_201_CREATED)
async def assign_role_to_user(
    role_request: RoleAssignmentRequest, current_superuser: CurrentSuperuser, db: DBSession
) -> dict[str, Any]:
    """Assign role to a user.

    Requires superadmin privileges. Assigns a role to a user and updates
    both the Casbin policies and the user record in the database.

    Args:
        role_request: Role assignment details
        db: Database session
        current_user: Current authenticated user (must be superadmin)

    Returns:
        Success message and role assignment details

    Raises:
        HTTPException: If role assignment fails or user lacks privileges
    """
    policy_manager = PolicyManager(db)

    result = await policy_manager.assign_role_to_user(
        user_email=role_request.user_email, role=role_request.role
    )

    if not result:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to assign role"
        )

    return {
        "message": "Role assigned successfully",
        "assignment": {"user_email": role_request.user_email, "role": role_request.role.value},
    }


@router.get("/summary", response_model=PolicySummaryResponse)
async def get_policy_summary(
    current_superuser: CurrentSuperuser, db: DBSession
) -> PolicySummaryResponse:
    """Get a summary of current policies and assignments.

    Requires superadmin privileges. Returns a comprehensive summary of
    all policies, role assignments, and customer assignments.

    Args:
        db: Database session
        current_user: Current authenticated user (must be superadmin)

    Returns:
        Policy summary with statistics

    Raises:
        HTTPException: If summary generation fails or user lacks privileges
    """
    policy_manager = PolicyManager(db)

    summary = await policy_manager.get_policy_summary()

    return PolicySummaryResponse(**summary)


@router.post("/backup", response_model=PolicyBackupResponse)
async def backup_policies(
    current_superuser: CurrentSuperuser, db: DBSession
) -> PolicyBackupResponse:
    """Create a backup of all current policies.

    Requires superadmin privileges. Creates a complete backup of all
    policies and grouping policies for disaster recovery purposes.

    Args:
        db: Database session
        current_user: Current authenticated user (must be superadmin)

    Returns:
        Policy backup data with metadata

    Raises:
        HTTPException: If backup creation fails or user lacks privileges
    """
    policy_manager = PolicyManager(db)

    backup_data = await policy_manager.backup_policies()

    return PolicyBackupResponse(**backup_data)


@router.post("/restore")
async def restore_policies(
    backup_data: PolicyBackupResponse, current_superuser: CurrentSuperuser, db: DBSession
) -> dict[str, Any]:
    """Restore policies from a backup.

    Requires superadmin privileges. Restores all policies from a backup,
    replacing the current policy set. This operation is irreversible.

    Args:
        backup_data: Policy backup data to restore
        db: Database session
        current_user: Current authenticated user (must be superadmin)

    Returns:
        Success message and restore statistics

    Raises:
        HTTPException: If restore fails or user lacks privileges
    """
    policy_manager = PolicyManager(db)

    # Convert Pydantic model to dict for the service
    backup_dict = backup_data.model_dump()

    result = await policy_manager.restore_policies(backup_dict)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to restore policies"
        )

    return {
        "message": "Policies restored successfully",
        "statistics": {
            "restored_policies": len(backup_data.policies),
            "restored_groupings": len(backup_data.grouping_policies),
            "backup_timestamp": backup_data.timestamp,
        },
    }


@router.post("/validate", response_model=PolicyValidationResponse)
async def validate_policies(
    current_superuser: CurrentSuperuser, db: DBSession
) -> PolicyValidationResponse:
    """Validate current policies for conflicts and issues.

    Requires superadmin privileges. Performs comprehensive validation
    of the current policy set to identify conflicts, orphaned policies,
    and other potential issues.

    Args:
        db: Database session
        current_user: Current authenticated user (must be superadmin)

    Returns:
        Validation results with issues and statistics

    Raises:
        HTTPException: If validation fails or user lacks privileges
    """
    policy_manager = PolicyManager(db)

    validation_results = await policy_manager.validate_policies()

    return PolicyValidationResponse(**validation_results)


@router.post("/seed")
async def seed_initial_policies(
    current_superuser: CurrentSuperuser, db: DBSession
) -> dict[str, Any]:
    """Seed initial policies for default roles.

    Requires superadmin privileges. Creates the initial policy set with
    full privileges for salesman, data_entry, and partner roles as
    specified in the requirements. This will clear existing policies.

    Args:
        db: Database session
        current_user: Current authenticated user (must be superadmin)

    Returns:
        Success message and seeding statistics

    Raises:
        HTTPException: If seeding fails or user lacks privileges
    """
    policy_manager = PolicyManager(db)

    await policy_manager.seed_initial_policies()

    return {
        "message": "Initial policies seeded successfully",
        "note": "All roles now have appropriate initial privileges",
    }


@router.get("/user-assignments/{user_email}")
async def get_user_assignments(
    user_email: str, current_superuser: CurrentSuperuser, db: DBSession
) -> dict[str, Any]:
    """Get all assignments for a specific user.

    Requires superadmin privileges. Returns all customer assignments
    and role assignments for the specified user.

    Args:
        user_email: Email of user to get assignments for
        db: Database session
        current_user: Current authenticated user (must be superadmin)

    Returns:
        User assignments including customers and roles

    Raises:
        HTTPException: If retrieval fails or user lacks privileges
    """
    policy_manager = PolicyManager(db)

    customer_assignments = await policy_manager.get_user_customer_assignments(user_email)

    # Get policy summary to extract role assignments
    summary = await policy_manager.get_policy_summary()
    role_assignments = summary.get("role_assignments", {}).get(user_email, [])

    return {
        "user_email": user_email,
        "customer_assignments": customer_assignments,
        "role_assignments": role_assignments,
        "statistics": {
            "total_customers": len(customer_assignments),
            "total_roles": len(role_assignments),
        },
    }
