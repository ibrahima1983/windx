"""
Database SQL Scripts Package

This package contains PostgreSQL SQL scripts for database triggers and functions.
"""

from pathlib import Path

SQL_DIR = Path(__file__).parent

__all__ = ["SQL_DIR"]
