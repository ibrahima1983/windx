"""Monitor dashboard stats in real-time with live updates.

This script continuously polls the stats endpoint and shows changes.
"""

import asyncio
from datetime import datetime

import httpx


# noinspection D
async def monitor_stats():
    """Monitor stats and show when they change."""
    base_url = "http://localhost:8000"

    # Login
    print("🔐 Logging in...")
    async with httpx.AsyncClient() as client:
        login_response = await client.post(
            json={
                "username": "johwqen_doe",
                "password": "SecurePaswqes123!",
            },
            url=base_url,
        )

        if login_response.status_code != 200:
            print(f"❌ Login failed: {login_response.text}")
            return

        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("✅ Logged in!\n")

        print("📊 Monitoring dashboard stats (press Ctrl+C to stop)...")
        print("=" * 80)
        print("Create a new user in another terminal to see real-time updates!")
        print("=" * 80)
        print()

        previous_stats = None
        poll_count = 0

        try:
            while True:
                poll_count += 1

                # Get current stats
                response = await client.get(f"{base_url}/api/v1/dashboard/stats", headers=headers)

                if response.status_code != 200:
                    print(f"❌ Error: {response.text}")
                    break

                current_stats = response.json()
                current_time = datetime.now().strftime("%H:%M:%S")

                # Check if stats changed
                if previous_stats is None:
                    # First poll
                    print(f"[{current_time}] Poll #{poll_count} - Initial Stats:")
                    print(f"  📊 Total Users: {current_stats['total_users']}")
                    print(f"  ✅ Active Users: {current_stats['active_users']}")
                    print(f"  ❌ Inactive Users: {current_stats['inactive_users']}")
                    print(f"  👑 Superusers: {current_stats['superusers']}")
                    print(f"  🆕 New Today: {current_stats['new_users_today']}")
                    print(f"  📅 New This Week: {current_stats['new_users_week']}")
                    print()
                else:
                    # Check for changes
                    changes = []
                    if current_stats["total_users"] != previous_stats["total_users"]:
                        changes.append(
                            f"Total: {previous_stats['total_users']} → {current_stats['total_users']}"
                        )
                    if current_stats["active_users"] != previous_stats["active_users"]:
                        changes.append(
                            f"Active: {previous_stats['active_users']} → {current_stats['active_users']}"
                        )
                    if current_stats["inactive_users"] != previous_stats["inactive_users"]:
                        changes.append(
                            f"Inactive: {previous_stats['inactive_users']} → {current_stats['inactive_users']}"
                        )
                    if current_stats["superusers"] != previous_stats["superusers"]:
                        changes.append(
                            f"Superusers: {previous_stats['superusers']} → {current_stats['superusers']}"
                        )
                    if current_stats["new_users_today"] != previous_stats["new_users_today"]:
                        changes.append(
                            f"New Today: {previous_stats['new_users_today']} → {current_stats['new_users_today']}"
                        )
                    if current_stats["new_users_week"] != previous_stats["new_users_week"]:
                        changes.append(
                            f"New Week: {previous_stats['new_users_week']} → {current_stats['new_users_week']}"
                        )

                    if changes:
                        print(f"[{current_time}] Poll #{poll_count} - 🔥 CHANGES DETECTED!")
                        for change in changes:
                            print(f"  • {change}")
                        print()
                    else:
                        print(
                            f"[{current_time}] Poll #{poll_count} - No changes (Total: {current_stats['total_users']})"
                        )

                previous_stats = current_stats
                # Wait 2 seconds before next poll
                await asyncio.sleep(2)

        except KeyboardInterrupt:
            print("\n\n⏹️  Monitoring stopped")
            print(f"Total polls: {poll_count}")


async def create_test_user():
    """Helper function to create a test user."""
    base_url = "http://localhost:8000"

    print("\n👤 Creating a test user to demonstrate real-time updates...")

    async with httpx.AsyncClient() as client:
        test_username = f"testuser_{int(datetime.now().timestamp())}"
        response = await client.post(
            f"{base_url}/api/v1/auth/register",
            json={
                "username": test_username,
                "email": f"{test_username}@example.com",
                "password": "TestPassword123!",
                "full_name": "Test User",
            },
        )

        if response.status_code == 201:
            print(f"✅ Created user: {test_username}")
            print("   Watch the monitor above - stats should update in ~2 seconds!")
        else:
            print(f"❌ Failed: {response.text}")


if __name__ == "__main__":
    import sys

    print("=" * 80)
    print("📊 Real-Time Dashboard Stats Monitor")
    print("=" * 80)
    print()

    if len(sys.argv) > 1 and sys.argv[1] == "create":
        # Create a test user
        asyncio.run(create_test_user())
    else:
        # Monitor stats
        print("💡 TIP: Open another terminal and run:")
        print("   python test_stats_monitoring.py create")
        print("   to create a test user and see real-time updates!")
        print()
        asyncio.run(monitor_stats())
