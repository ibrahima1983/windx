"""Quick script to check current stats."""

import asyncio

import httpx


async def check():
    async with httpx.AsyncClient() as client:
        # Login
        login = await client.post(
            "http://localhost:8000/api/v1/auth/login",
            json={"username": "johwqen_doe", "password": "SecurePaswqes123!"},
        )
        token = login.json()["access_token"]

        # Get stats
        stats = await client.get(
            "http://localhost:8000/api/v1/dashboard/stats",
            headers={"Authorization": f"Bearer {token}"},
        )

        data = stats.json()
        print(f"Total Users: {data['total_users']}")
        print(f"Active Users: {data['active_users']}")
        print(f"New Today: {data['new_users_today']}")
        print(f"Timestamp: {data['timestamp']}")


asyncio.run(check())
