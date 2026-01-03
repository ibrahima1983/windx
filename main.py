"""Main FastAPI application module.

This module initializes the FastAPI application with CORS middleware,
API routers, and health check endpoints.

Public Functions:
    root: Root endpoint
    health_check: Health check endpoint
    configure_cors: Configure CORS middleware

Features:
    - FastAPI application initialization
    - CORS middleware configuration
    - API v1 router integration
    - Health check endpoint
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi_pagination import add_pagination
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.router import api_router
from app.core.cache import close_cache, init_cache
from app.core.config import Settings, get_settings
from app.core.exceptions import setup_exception_handlers
from app.core.limiter import close_limiter, init_limiter
from app.core.middleware import setup_middleware
from app.database import close_db, get_db, init_db

__all__ = ["app", "root", "health_check", "lifespan"]


async def check_db_setup():
    from sqlalchemy import text

    from app.database import get_db

    async for db in get_db():
        try:
            # Try to query users table
            result = await db.execute(text("SELECT COUNT(*) FROM users"))
            user_count = result.scalar()
            if user_count == 0:
                print("[!] WARNING: Database is empty. Run: python manage.py seed_data")
            else:
                print(f"[OK] Database ready with {user_count} user(s)")
        except Exception as db_error:
            if "does not exist" in str(db_error).lower():
                print("[!] WARNING: Database tables not found!")
                print("    Run: python manage.py create_tables")
                print("    Then: python manage.py seed_data")
        break


def validate_env_config():
    settings = get_settings()
    print(f"[+] Configuration loaded: {settings.app_name} v{settings.app_version}")
    print(
        f"    Database: {settings.database.provider} @ {settings.database.host}:{settings.database.port}"
    )
    print(f"    Connection mode: {settings.database.connection_mode}")


async def init_services():
    await init_db()
    await init_cache()
    await init_limiter()


async def close_servicers():
    await close_db()
    await close_cache()
    await close_limiter()


@asynccontextmanager
async def lifespan(application: FastAPI):
    """Application lifespan manager.

    Handles startup and shutdown events for the FastAPI application.
    Initializes database, cache, and rate limiter on startup.

    Args:
        application (FastAPI): FastAPI application instance

    Yields:
        None: Control back to FastAPI
    """
    # Skip lifespan during test collection to prevent pytest capture issues
    # Unkown if it can cause any issues
    import os
    if os.getenv("TESTING") == "true":
        yield
        return
    
    # Startup
    print("[*] Starting application...")

    # Validate environment configuration
    try:
        validate_env_config()
    except Exception as e:
        print(f"[-] Configuration error: {e}")
        raise

    await init_services()  # db, cache, limiter

    # Check if database is set up
    try:
        await check_db_setup()
    except Exception as e:
        print(f"[!] Could not check database status: {e}")

    print("[+] Application started successfully")

    yield

    # Shutdown
    print("[*] Shutting down application...")
    await close_servicers()  # db, cache, limiter
    print("[+] Application shutdown complete")


app = FastAPI(
    title="WindX Product Configurator API",
    summary="Automated Product Configurator for Custom Manufacturing",
    description="API for dynamic product configuration with real-time pricing, templates, quotes, and order management.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url=None,
    redoc_url="/redoc",
    contact={
        "name": "WindX Support",
        "email": "support@windx.example.com",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
    openapi_tags=[
        {
            "name": "Manufacturing Types",
            "description": "Manage product categories and base configurations",
        },
        {
            "name": "Attribute Nodes",
            "description": "Hierarchical product attributes and options",
        },
        {
            "name": "Configurations",
            "description": "Customer product designs and selections",
        },
        {
            "name": "Templates",
            "description": "Pre-configured product templates",
        },
        {
            "name": "Quotes",
            "description": "Price quotes with snapshots",
        },
        {
            "name": "Orders",
            "description": "Order management and tracking",
        },
        {
            "name": "Customers",
            "description": "Customer information management",
        },
    ],
    swagger_ui_parameters={
        "persistAuthorization": True,
        "displayOperationId": False,
        "displayRequestDuration": True,
        "filter": True,
        "tryItOutEnabled": True,
        "syntaxHighlight.theme": "monokai",
    },
)


@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html() -> FileResponse:
    """Serve custom Swagger UI documentation."""
    static_path = Path(__file__).parent / "app" / "static" / "swagger-ui.html"
    return FileResponse(static_path)


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint.

    Returns:
        dict[str, str]: Welcome message with API information
    """
    return {
        "message": "Welcome to WindX Product Configurator API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
        "version_info": "/version",
    }


@app.get(
    "/version",
    summary="Version Information",
    description="Get detailed version and deployment information including commit hash, deployment time, and script version.",
    response_description="Version and deployment details",
    operation_id="getVersionInfo",
)
async def version_info() -> dict[str, str | dict[str, str]]:
    """Version and deployment information endpoint.

    Returns detailed information about the current deployment including:
    - Application version
    - Deployment script version  
    - Git commit information (if available)
    - Deployment timestamp

    Returns:
        dict: Version and deployment information

    Example Response:
        {
            "app_name": "WindX Product Configurator",
            "app_version": "1.0.1",
            "script_version": "v1.0.1",
            "deployment_info": {
                "commit_hash": "abc123...",
                "short_hash": "abc123",
                "commit_message": "Fix deployment script",
                "deployment_time": "2026-01-03T14:30:00Z"
            }
        }
    """
    import json
    from pathlib import Path
    
    # Read app version from VERSION file
    app_version = "1.0.0"  # fallback
    version_file = Path("VERSION")
    if version_file.exists():
        try:
            app_version = version_file.read_text().strip()
        except Exception:
            pass
    
    # Try to read deployment info created by startup script
    deployment_info = {}
    deployment_file = Path("/tmp/deployment-info.json")
    
    if deployment_file.exists():
        try:
            with open(deployment_file, "r") as f:
                deployment_info = json.load(f)
        except Exception:
            deployment_info = {"error": "Could not read deployment info"}
    else:
        deployment_info = {"status": "No deployment info available"}
    
    return {
        "app_name": "WindX Product Configurator",
        "app_version": app_version,
        "script_version": "v1.0.1",
        "deployment_info": deployment_info,
        "endpoints": {
            "docs": "/docs",
            "health": "/health",
            "api": "/api/v1"
        }
    }


@app.get(
    "/health",
    summary="Health Check",
    description="Comprehensive health check endpoint that verifies all system dependencies including database, cache, and rate limiter connectivity.",
    response_description="Health status with dependency checks",
    operation_id="healthCheck",
)
async def health_check(
    settings: Annotated[Settings, Depends(get_settings)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, str | dict[str, str | bool | dict[str, str]]]:
    """Health check endpoint with dependency verification.

    Verifies connectivity to all critical system dependencies:
    - Database (PostgreSQL/Supabase)
    - Redis cache (if enabled)
    - Redis rate limiter (if enabled)

    Args:
        settings (Settings): Application settings
        db (AsyncSession): Database session

    Returns:
        dict: Health status with overall status and individual dependency checks

    Example Response:
        {
            "status": "healthy",
            "app_name": "Backend API",
            "version": "1.0.0",
            "checks": {
                "database": {
                    "status": "healthy",
                    "provider": "supabase"
                },
                "cache": {
                    "status": "healthy"
                },
                "rate_limiter": {
                    "status": "healthy"
                }
            }
        }
    """
    from sqlalchemy import text

    overall_status = "healthy"
    checks: dict[str, dict[str, str]] = {}

    # Check database connectivity
    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = {
            "status": "healthy",
            "provider": settings.database.provider,
        }
    except Exception as e:
        overall_status = "unhealthy"
        checks["database"] = {
            "status": "unhealthy",
            "provider": settings.database.provider,
            "error": str(e),
        }

    # Check Redis cache connectivity (if enabled)
    if settings.cache.enabled:
        redis_cache = None
        try:
            import redis.asyncio as aioredis

            # Create temporary Redis client for health check (don't use cached singleton)
            redis_cache = aioredis.from_url(
                str(settings.cache.redis_url),
                encoding="utf-8",
                decode_responses=True,
            )
            await redis_cache.ping()
            checks["cache"] = {"status": "healthy"}
        except Exception as e:
            overall_status = "unhealthy"
            checks["cache"] = {
                "status": "unhealthy",
                "error": str(e),
            }
        finally:
            if redis_cache:
                await redis_cache.close()

    # Check Redis rate limiter connectivity (if enabled)
    if settings.limiter.enabled:
        redis_limiter = None
        try:
            import redis.asyncio as aioredis

            # Create temporary Redis client for health check (don't use cached singleton)
            redis_limiter = aioredis.from_url(
                str(settings.limiter.redis_url),
                encoding="utf-8",
                decode_responses=True,
            )
            await redis_limiter.ping()
            checks["rate_limiter"] = {"status": "healthy"}
        except Exception as e:
            overall_status = "unhealthy"
            checks["rate_limiter"] = {
                "status": "unhealthy",
                "error": str(e),
            }
        finally:
            if redis_limiter:
                await redis_limiter.close()

    return {
        "status": overall_status,
        "app_name": settings.app_name,
        "version": settings.app_version,
        "checks": checks,
    }


# Get settings
settings = get_settings()

# Mount static files
static_path = Path(__file__).parent / "app" / "static"
if static_path.exists():
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

# Setup middleware (includes CORS, security headers, logging, etc.)
setup_middleware(app, settings)

# Setup exception handlers
setup_exception_handlers(app)

# Include API router
app.include_router(api_router, prefix=settings.api_v1_prefix)

# Add pagination support
add_pagination(app)
