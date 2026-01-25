"""Policy management service for dynamic RBAC policy updates.

This module provides comprehensive policy management capabilities including
dynamic policy updates, customer assignments, policy backup/restore, and
audit logging for policy changes.

Public Classes:
    PolicyManager: Service for managing Casbin policies dynamically

Features:
    - Dynamic policy addition and removal
    - Customer assignment management for salesmen/partners
    - Policy backup and restore functionality
    - Audit logging for all policy changes
    - Batch policy operations for efficiency
    - Policy validation and conflict detection
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

import casbin
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import PolicyEvaluationException
from app.core.rbac import Role
from app.models.customer import Customer
from app.models.user import User
from app.services.base import BaseService

__all__ = ["PolicyManager"]

logger = logging.getLogger(__name__)


class PolicyManager(BaseService):
    """Service for managing Casbin policies dynamically.

    Provides comprehensive policy management including:
    - Dynamic policy updates without system restart
    - Customer assignment workflows for salesmen/partners
    - Policy backup and restore for disaster recovery
    - Audit logging for compliance and security
    - Batch operations for efficiency
    - Policy validation and conflict detection
    """

    def __init__(self, db: AsyncSession):
        """Initialize policy manager.

        Args:
            db: Database session for operations
        """
        super().__init__(db)
        self.enforcer = casbin.Enforcer("config/rbac_model.conf", "config/rbac_policy.csv")

        # Enable auto-save for policy changes
        self.enforcer.enable_auto_save(True)

    async def add_policy(
        self, subject: str, resource: str, action: str, effect: str = "allow"
    ) -> bool:
        """Add a new policy rule.

        Args:
            subject: Subject (role or user) for the policy
            resource: Resource the policy applies to
            action: Action the policy allows/denies
            effect: Effect of the policy (allow/deny)

        Returns:
            True if policy was added, False if it already exists

        Raises:
            PolicyEvaluationException: If policy addition fails
        """
        try:
            # Add policy to Casbin
            result = self.enforcer.add_policy(subject, resource, action, effect)

            if result:
                # Log policy addition for audit
                await self._log_policy_change(
                    action_type="add_policy",
                    policy_data={
                        "subject": subject,
                        "resource": resource,
                        "action": action,
                        "effect": effect,
                    },
                )

                logger.info(f"Added policy: {subject} -> {resource}:{action} ({effect})")

            return result

        except Exception as e:
            logger.error(f"Failed to add policy: {e}")
            raise PolicyEvaluationException(
                f"Failed to add policy for {subject}",
                {"subject": subject, "resource": resource, "action": action},
            )

    async def remove_policy(
        self, subject: str, resource: str, action: str, effect: str = "allow"
    ) -> bool:
        """Remove a policy rule.

        Args:
            subject: Subject (role or user) for the policy
            resource: Resource the policy applies to
            action: Action the policy allows/denies
            effect: Effect of the policy (allow/deny)

        Returns:
            True if policy was removed, False if it didn't exist

        Raises:
            PolicyEvaluationException: If policy removal fails
        """
        try:
            # Remove policy from Casbin
            result = self.enforcer.remove_policy(subject, resource, action, effect)

            if result:
                # Log policy removal for audit
                await self._log_policy_change(
                    action_type="remove_policy",
                    policy_data={
                        "subject": subject,
                        "resource": resource,
                        "action": action,
                        "effect": effect,
                    },
                )

                logger.info(f"Removed policy: {subject} -> {resource}:{action} ({effect})")

            return result

        except Exception as e:
            logger.error(f"Failed to remove policy: {e}")
            raise PolicyEvaluationException(
                f"Failed to remove policy for {subject}",
                {"subject": subject, "resource": resource, "action": action},
            )

    async def assign_customer_to_user(
        self, user_email: str, customer_id: int, assignment_type: str = "assigned"
    ) -> bool:
        """Assign customer access to a user (for salesmen/partners).

        Args:
            user_email: Email of user to assign customer to
            customer_id: ID of customer to assign
            assignment_type: Type of assignment (assigned, managed, etc.)

        Returns:
            True if assignment was successful

        Raises:
            PolicyEvaluationException: If assignment fails
        """
        try:
            # Verify customer exists
            stmt = select(Customer).where(Customer.id == customer_id)
            result = await self.db.execute(stmt)
            customer = result.scalar_one_or_none()

            if not customer:
                raise PolicyEvaluationException(
                    f"Customer {customer_id} not found", {"customer_id": customer_id}
                )

            # Add customer assignment using g2 grouping
            result = self.enforcer.add_grouping_policy(user_email, "customer", str(customer_id))

            if result:
                # Log customer assignment for audit
                await self._log_policy_change(
                    action_type="assign_customer",
                    policy_data={
                        "user_email": user_email,
                        "customer_id": customer_id,
                        "assignment_type": assignment_type,
                        "customer_name": customer.company_name or customer.contact_person,
                    },
                )

                logger.info(f"Assigned customer {customer_id} to user {user_email}")

            return result

        except PolicyEvaluationException:
            # Re-raise PolicyEvaluationException without wrapping
            raise
        except Exception as e:
            logger.error(f"Failed to assign customer: {e}")
            raise PolicyEvaluationException(
                f"Failed to assign customer {customer_id} to {user_email}",
                {"user_email": user_email, "customer_id": customer_id},
            )

    async def remove_customer_assignment(self, user_email: str, customer_id: int) -> bool:
        """Remove customer assignment from a user.

        Args:
            user_email: Email of user to remove assignment from
            customer_id: ID of customer to remove

        Returns:
            True if assignment was removed

        Raises:
            PolicyEvaluationException: If removal fails
        """
        try:
            # Remove customer assignment using g2 grouping
            result = self.enforcer.remove_grouping_policy(user_email, "customer", str(customer_id))

            if result:
                # Log customer assignment removal for audit
                await self._log_policy_change(
                    action_type="remove_customer_assignment",
                    policy_data={"user_email": user_email, "customer_id": customer_id},
                )

                logger.info(f"Removed customer {customer_id} assignment from user {user_email}")

            return result

        except Exception as e:
            logger.error(f"Failed to remove customer assignment: {e}")
            raise PolicyEvaluationException(
                f"Failed to remove customer {customer_id} from {user_email}",
                {"user_email": user_email, "customer_id": customer_id},
            )

    async def get_user_customer_assignments(self, user_email: str) -> list[int]:
        """Get all customer assignments for a user.

        Args:
            user_email: Email of user to get assignments for

        Returns:
            List of customer IDs assigned to the user
        """
        try:
            # Get all grouping policies for the user
            groupings = self.enforcer.get_grouping_policy()

            customer_ids = []
            for grouping in groupings:
                if len(grouping) >= 3 and grouping[0] == user_email and grouping[1] == "customer":
                    try:
                        customer_ids.append(int(grouping[2]))
                    except ValueError:
                        logger.warning(f"Invalid customer ID in grouping: {grouping[2]}")

            return customer_ids

        except Exception as e:
            logger.error(f"Failed to get customer assignments: {e}")
            return []

    async def assign_role_to_user(self, user_email: str, role: Role) -> bool:
        """Assign role to user and update policies.

        Args:
            user_email: Email of user to assign role to
            role: Role to assign

        Returns:
            True if role was assigned successfully

        Raises:
            PolicyEvaluationException: If role assignment fails
        """
        try:
            # Remove existing role assignments
            self.enforcer.remove_grouping_policy(user_email)

            # Add new role assignment
            result = self.enforcer.add_grouping_policy(user_email, role.value)

            if result:
                # Update user role in database
                stmt = select(User).where(User.email == user_email)
                db_result = await self.db.execute(stmt)
                user = db_result.scalar_one_or_none()

                if user:
                    user.role = role.value
                    await self.commit()

                # Log role assignment for audit
                await self._log_policy_change(
                    action_type="assign_role",
                    policy_data={"user_email": user_email, "role": role.value},
                )

                logger.info(f"Assigned role {role.value} to user {user_email}")

            return result

        except Exception as e:
            logger.error(f"Failed to assign role: {e}")
            raise PolicyEvaluationException(
                f"Failed to assign role {role.value} to {user_email}",
                {"user_email": user_email, "role": role.value},
            )

    async def backup_policies(self) -> dict[str, Any]:
        """Create a backup of all current policies.

        Returns:
            Dictionary containing all policies and metadata
        """
        try:
            backup_data = {
                "timestamp": datetime.utcnow().isoformat(),
                "policies": self.enforcer.get_policy(),
                "grouping_policies": self.enforcer.get_grouping_policy(),
                "metadata": {
                    "total_policies": len(self.enforcer.get_policy()),
                    "total_groupings": len(self.enforcer.get_grouping_policy()),
                },
            }

            # Log backup creation for audit
            await self._log_policy_change(
                action_type="backup_policies",
                policy_data={
                    "policy_count": backup_data["metadata"]["total_policies"],
                    "grouping_count": backup_data["metadata"]["total_groupings"],
                },
            )

            logger.info(
                f"Created policy backup with {backup_data['metadata']['total_policies']} "
                f"policies and {backup_data['metadata']['total_groupings']} groupings"
            )

            return backup_data

        except Exception as e:
            logger.error(f"Failed to backup policies: {e}")
            raise PolicyEvaluationException("Failed to create policy backup", {"error": str(e)})

    async def restore_policies(self, backup_data: dict[str, Any]) -> bool:
        """Restore policies from a backup.

        Args:
            backup_data: Backup data containing policies to restore

        Returns:
            True if restore was successful

        Raises:
            PolicyEvaluationException: If restore fails
        """
        try:
            # Validate backup data structure
            if not all(key in backup_data for key in ["policies", "grouping_policies"]):
                raise PolicyEvaluationException(
                    "Invalid backup data structure",
                    {"required_keys": ["policies", "grouping_policies"]},
                )

            # Clear existing policies
            self.enforcer.clear_policy()

            # Restore policies
            for policy in backup_data["policies"]:
                self.enforcer.add_policy(*policy)

            # Restore grouping policies
            for grouping in backup_data["grouping_policies"]:
                self.enforcer.add_grouping_policy(*grouping)

            # Save policies
            self.enforcer.save_policy()

            # Log restore for audit
            await self._log_policy_change(
                action_type="restore_policies",
                policy_data={
                    "restored_policies": len(backup_data["policies"]),
                    "restored_groupings": len(backup_data["grouping_policies"]),
                    "backup_timestamp": backup_data.get("timestamp"),
                },
            )

            logger.info(
                f"Restored {len(backup_data['policies'])} policies and "
                f"{len(backup_data['grouping_policies'])} groupings from backup"
            )

            return True

        except PolicyEvaluationException:
            # Re-raise PolicyEvaluationException without wrapping
            raise
        except Exception as e:
            logger.error(f"Failed to restore policies: {e}")
            raise PolicyEvaluationException(
                "Failed to restore policies from backup", {"error": str(e)}
            )

    async def validate_policies(self) -> dict[str, Any]:
        """Validate current policies for conflicts and issues.

        Returns:
            Dictionary containing validation results
        """
        try:
            validation_results = {"valid": True, "issues": [], "warnings": [], "statistics": {}}

            # Get all policies
            policies = self.enforcer.get_policy()
            groupings = self.enforcer.get_grouping_policy()

            # Check for conflicting policies (same subject/resource/action with different effects)
            policy_map = {}
            for policy in policies:
                if len(policy) >= 4:
                    key = f"{policy[0]}:{policy[1]}:{policy[2]}"
                    if key in policy_map and policy_map[key] != policy[3]:
                        validation_results["issues"].append(
                            {
                                "type": "conflicting_policy",
                                "description": f"Conflicting effects for {key}",
                                "policies": [policy_map[key], policy[3]],
                            }
                        )
                        validation_results["valid"] = False
                    policy_map[key] = policy[3]

            # Check for orphaned groupings (users with roles but no policies)
            role_users = set()
            for grouping in groupings:
                if len(grouping) >= 2:
                    role_users.add(grouping[0])

            # Statistics
            validation_results["statistics"] = {
                "total_policies": len(policies),
                "total_groupings": len(groupings),
                "unique_subjects": len(set(p[0] for p in policies if len(p) >= 1)),
                "unique_resources": len(set(p[1] for p in policies if len(p) >= 2)),
                "role_assignments": len(
                    [g for g in groupings if len(g) >= 2 and g[1] in [r.value for r in Role]]
                ),
            }

            logger.info(f"Policy validation completed: {validation_results['statistics']}")

            return validation_results

        except Exception as e:
            logger.error(f"Failed to validate policies: {e}")
            raise PolicyEvaluationException("Failed to validate policies", {"error": str(e)})

    async def get_policy_summary(self) -> dict[str, Any]:
        """Get a summary of current policies and assignments.

        Returns:
            Dictionary containing policy summary
        """
        try:
            policies = self.enforcer.get_policy()
            groupings = self.enforcer.get_grouping_policy()

            # Organize policies by role
            policies_by_role = {}
            for policy in policies:
                if len(policy) >= 4:
                    role = policy[0]
                    if role not in policies_by_role:
                        policies_by_role[role] = []
                    policies_by_role[role].append(
                        {"resource": policy[1], "action": policy[2], "effect": policy[3]}
                    )

            # Organize role assignments
            role_assignments = {}
            customer_assignments = {}

            for grouping in groupings:
                if len(grouping) >= 2:
                    user = grouping[0]
                    group_type = grouping[1]

                    if group_type == "customer" and len(grouping) >= 3:
                        # Customer assignment (3 elements: user, "customer", customer_id)
                        if user not in customer_assignments:
                            customer_assignments[user] = []
                        customer_assignments[user].append(int(grouping[2]))
                    elif group_type in [r.value for r in Role]:
                        # Role assignment (2 elements: user, role)
                        if user not in role_assignments:
                            role_assignments[user] = []
                        role_assignments[user].append(group_type)

            summary = {
                "policies_by_role": policies_by_role,
                "role_assignments": role_assignments,
                "customer_assignments": customer_assignments,
                "statistics": {
                    "total_policies": len(policies),
                    "total_role_assignments": len(role_assignments),
                    "total_customer_assignments": sum(
                        len(customers) for customers in customer_assignments.values()
                    ),
                    "roles_with_policies": len(policies_by_role),
                },
            }

            return summary

        except Exception as e:
            logger.error(f"Failed to get policy summary: {e}")
            raise PolicyEvaluationException("Failed to get policy summary", {"error": str(e)})

    async def _log_policy_change(self, action_type: str, policy_data: dict[str, Any]) -> None:
        """Log policy change for audit purposes.

        Args:
            action_type: Type of policy change (add_policy, remove_policy, etc.)
            policy_data: Data about the policy change
        """
        try:
            # Create audit log entry
            audit_entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "action_type": action_type,
                "policy_data": policy_data,
                "system": "rbac_policy_manager",
            }

            # Log to application logger
            logger.info(f"Policy change audit: {json.dumps(audit_entry)}")

            # TODO: Store in dedicated audit table if needed
            # This could be implemented to store audit logs in database
            # for compliance and long-term retention

        except Exception as e:
            logger.error(f"Failed to log policy change: {e}")
            # Don't raise exception for logging failures

    async def seed_initial_policies(self) -> None:
        """Seed initial policies for default roles.

        Creates the initial policy set with full privileges for salesman,
        data_entry, and partner roles as specified in requirements.
        """
        try:
            logger.info("Seeding initial RBAC policies...")

            # Clear existing policies
            self.enforcer.clear_policy()

            # Initial policies with full privileges
            initial_policies = [
                # Superadmin - unrestricted access
                ("superadmin", "*", "*", "allow"),
                # Salesman - initially full privileges (to be restricted later)
                ("salesman", "*", "*", "allow"),
                # Data entry - initially full privileges (to be restricted later)
                ("data_entry", "*", "*", "allow"),
                # Partner - initially full privileges (to be restricted later)
                ("partner", "*", "*", "allow"),
                # Customer - limited privileges
                ("customer", "configuration", "read", "allow"),
                ("customer", "configuration", "create", "allow"),
                ("customer", "quote", "read", "allow"),
                ("customer", "quote", "create", "allow"),
            ]

            # Add all initial policies
            for policy in initial_policies:
                self.enforcer.add_policy(*policy)

            # Save policies
            self.enforcer.save_policy()

            # Log policy seeding for audit
            await self._log_policy_change(
                action_type="seed_initial_policies",
                policy_data={
                    "policies_created": len(initial_policies),
                    "policy_list": initial_policies,
                },
            )

            logger.info(f"Seeded {len(initial_policies)} initial policies")

        except Exception as e:
            logger.error(f"Failed to seed initial policies: {e}")
            raise PolicyEvaluationException("Failed to seed initial policies", {"error": str(e)})
