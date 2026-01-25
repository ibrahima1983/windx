"""Backend API application package.

This is the main application package for the backend API built with FastAPI,
PostgreSQL/Supabase, and following repository pattern architecture.

Public Modules:
    core: Core functionality (config, database, security)
    models: SQLAlchemy ORM models
    schemas: Pydantic validation schemas
    repositories: Repository pattern implementations
    api: API endpoints and routers
    main: FastAPI application entry point

Features:
    - RESTful API with FastAPI
    - PostgreSQL database with Supabase
    - Repository pattern for data access
    - JWT authentication
    - Type-safe with full type hints
    - Async/await support
"""

__all__ = ["core", "models", "schemas", "repositories", "api"]
