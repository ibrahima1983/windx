"""
Base script functionality for product definition setup.

This module provides the base class for scope-specific setup scripts.
"""

import asyncio
from abc import ABC, abstractmethod
from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.connection import get_session_maker


class BaseProductDefinitionSetup(ABC):
    """Base class for scope-specific setup scripts."""
    
    def __init__(self, scope: str):
        self.scope = scope
    
    @abstractmethod
    async def create_scope_metadata(self, db: AsyncSession) -> None:
        """Create scope metadata in database."""
        pass
    
    @abstractmethod
    async def seed_sample_data(self, db: AsyncSession) -> None:
        """Seed sample data for this scope."""
        pass
    
    async def setup_scope(self, db: AsyncSession) -> None:
        """Complete scope setup."""
        print(f"🚀 Setting up {self.scope} scope...")
        try:
            await self.create_scope_metadata(db)
            await self.seed_sample_data(db)
            print(f"✅ {self.scope} scope setup complete")
        except Exception as e:
            print(f"❌ Error setting up {self.scope} scope: {e}")
            raise
    
    async def run_setup(self) -> None:
        """Run the complete setup process."""
        session_maker = get_session_maker()
        async with session_maker() as db:
            await self.setup_scope(db)


class BaseProductDefinitionDebug(ABC):
    """Base class for scope-specific debug scripts."""
    
    def __init__(self, scope: str):
        self.scope = scope
    
    @abstractmethod
    async def debug_scope_data(self, db: AsyncSession) -> None:
        """Debug scope-specific data."""
        pass
    
    async def run_debug(self) -> None:
        """Run the debug process."""
        print(f"🔍 Debugging {self.scope} scope...")
        session_maker = get_session_maker()
        async with session_maker() as db:
            await self.debug_scope_data(db)
        print(f"✅ {self.scope} scope debug complete")


def run_async_script(coro):
    """Helper function to run async scripts."""
    try:
        asyncio.run(coro)
    except KeyboardInterrupt:
        print("\n⚠️  Script interrupted by user")
    except Exception as e:
        print(f"❌ Script failed: {e}")
        raise