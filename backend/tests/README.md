# Test Suite Documentation

## Overview

This test suite uses **asyncpg** with PostgreSQL (Supabase) for all database operations. The tests are designed to work with the Windx product configuration system which requires PostgreSQL-specific features.

## Database Configuration

### Why asyncpg?

The test suite uses `asyncpg` instead of `aiosqlite` or `psycopg` for several important reasons:

1. **LTREE Extension Support**: The Windx schema uses PostgreSQL's LTREE extension for efficient hierarchical attribute queries
2. **JSONB Native Support**: Better performance for JSONB operations used in flexible metadata storage
3. **Full Async/Await**: Native async support without blocking operations
4. **Supabase Compatibility**: Works seamlessly with Supabase PostgreSQL instances
5. **Performance**: Faster than psycopg for async operations

### Connection String Format

```python
postgresql+asyncpg://user:password@host:port/database
```

Example:
```python
postgresql+asyncpg://postgres:password@db.example.supabase.co:5432/postgres
```

## Test Database Setup

### Configuration Files

1. **`.env.test`**: Contains test database credentials
   - Uses Supabase PostgreSQL instance
   - Separate from production database
   - Credentials are safe for testing

2. **`tests/config.py`**: Test-specific settings
   - Overrides main application settings
   - Disables caching and rate limiting
   - Forces debug mode

3. **`tests/conftest.py`**: Pytest fixtures
   - Database engine creation
   - Session management
   - Test client setup
   - Authentication helpers

### Database Initialization

Each test gets a fresh database state:

```python
@pytest_asyncio.fixture(scope="function")
async def test_engine():
    # 1. Create engine with asyncpg
    engine = create_async_engine(
        TEST_DATABASE_URL,
        poolclass=NullPool  # No pooling for test isolation
    )
    
    # 2. Enable LTREE extension
    await conn.execute(text("CREATE EXTENSION IF NOT EXISTS ltree"))
    
    # 3. Drop and recreate all tables
    await conn.run_sync(Base.metadata.drop_all)
    await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # 4. Cleanup after test
    await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
```

## Required PostgreSQL Extensions

The test database must have these extensions enabled:

### LTREE Extension

```sql
CREATE EXTENSION IF NOT EXISTS ltree;
```

**Purpose**: Hierarchical data storage for attribute nodes

**Usage in Windx**:
- Stores attribute paths like `window.frame.material.aluminum`
- Enables fast descendant/ancestor queries
- Supports pattern matching on paths

**Example Query**:
```sql
-- Get all descendants of "frame" node
SELECT * FROM attribute_nodes 
WHERE ltree_path <@ 'window.frame'::ltree;
```

### JSONB Support

PostgreSQL's native JSONB type is used for:
- Display conditions (conditional attribute visibility)
- Validation rules (input validation logic)
- Technical specifications (product-specific data)
- Price breakdowns (detailed cost components)

**Example**:
```python
display_condition = {
    "operator": "equals",
    "field": "parent.material",
    "value": "wood"
}
```

## Running Tests

### Run All Tests

```bash
# Using pytest directly
.venv\scripts\python -m pytest

# Using uv
uv run pytest

# With coverage
.venv\scripts\python -m pytest --cov=app --cov-report=html
```

### Run Specific Test Categories

```bash
# Unit tests only
.venv\scripts\python -m pytest tests/unit -v

# Integration tests only
.venv\scripts\python -m pytest tests/integration -v

# Specific test file
.venv\scripts\python -m pytest tests/unit/test_supabase.py -v

# Tests with specific marker
.venv\scripts\python -m pytest -m auth -v
```

### Test Markers

Available markers defined in `pyproject.toml`:

- `unit`: Fast, isolated unit tests
- `integration`: Full stack integration tests
- `slow`: Tests that take longer to run
- `auth`: Authentication-related tests
- `users`: User management tests
- `services`: Service layer tests
- `repositories`: Repository layer tests

## Test Structure

```
tests/
├── conftest.py              # Shared fixtures
├── config.py                # Test settings
├── README.md                # This file
├── unit/                    # Unit tests
│   ├── test_supabase.py    # Database connection tests
│   ├── models/             # Model tests
│   ├── repositories/       # Repository tests
│   └── services/           # Service tests
└── integration/            # Integration tests
    └── api/                # API endpoint tests
```

## Common Test Patterns

### Testing with Database Session

```python
@pytest.mark.asyncio
async def test_create_user(db_session: AsyncSession):
    """Test user creation."""
    user_service = UserService(db_session)
    user_in = UserCreate(
        email="test@example.com",
        username="testuser",
        password="Password123!"
    )
    
    user = await user_service.create_user(user_in)
    
    assert user.email == "test@example.com"
    assert user.username == "testuser"
```

### Testing API Endpoints

```python
@pytest.mark.asyncio
async def test_login_endpoint(client: AsyncClient, test_user):
    """Test login endpoint."""
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "username": "testuser",
            "password": "Password123!"
        }
    )
    
    assert response.status_code == 200
    assert "access_token" in response.json()
```

### Testing with Authentication

```python
@pytest.mark.asyncio
async def test_protected_endpoint(
    client: AsyncClient,
    auth_headers: dict[str, str]
):
    """Test protected endpoint."""
    response = await client.get(
        "/api/v1/users/me",
        headers=auth_headers
    )
    
    assert response.status_code == 200
```

## Troubleshooting

### Connection Issues

**Problem**: `asyncpg.exceptions.InvalidCatalogNameError`

**Solution**: Ensure the database exists in your Supabase project

---

**Problem**: `asyncpg.exceptions.UndefinedObjectError: type "ltree" does not exist`

**Solution**: Enable LTREE extension:
```sql
CREATE EXTENSION IF NOT EXISTS ltree;
```

---

**Problem**: Tests hang or timeout

**Solution**: 
1. Check database connection in `.env.test`
2. Verify Supabase instance is running
3. Check firewall/network settings

### Performance Issues

**Problem**: Tests are slow

**Solutions**:
1. Use `NullPool` to avoid connection pooling overhead
2. Run unit tests separately from integration tests
3. Use test markers to run specific test categories
4. Consider using `pytest-xdist` for parallel execution

### Fixture Issues

**Problem**: `fixture 'db_session' not found`

**Solution**: Ensure `conftest.py` is in the correct location and pytest can discover it

---

**Problem**: Database state persists between tests

**Solution**: Each test should get a fresh database. Check that:
1. `test_engine` fixture has `scope="function"`
2. Tables are dropped and recreated in fixture
3. Session is properly rolled back in `db_session` fixture

## Best Practices

### Test Isolation

✅ **DO**: Use function-scoped fixtures for database tests
```python
@pytest_asyncio.fixture(scope="function")
async def db_session(test_session_maker):
    async with test_session_maker() as session:
        yield session
        await session.rollback()  # Ensure cleanup
```

❌ **DON'T**: Use session-scoped fixtures for mutable state
```python
# This will cause tests to interfere with each other
@pytest_asyncio.fixture(scope="session")
async def db_session():
    ...
```

### Async Testing

✅ **DO**: Use `@pytest.mark.asyncio` for async tests
```python
@pytest.mark.asyncio
async def test_async_operation():
    result = await some_async_function()
    assert result is not None
```

❌ **DON'T**: Mix sync and async without proper handling
```python
def test_async_operation():  # Missing @pytest.mark.asyncio
    result = await some_async_function()  # Will fail
```

### Database Cleanup

✅ **DO**: Let fixtures handle cleanup automatically
```python
@pytest_asyncio.fixture
async def test_user(db_session):
    user = await create_user(db_session)
    yield user
    # Cleanup happens automatically via session rollback
```

❌ **DON'T**: Manually delete test data
```python
@pytest_asyncio.fixture
async def test_user(db_session):
    user = await create_user(db_session)
    yield user
    await db_session.delete(user)  # Unnecessary
    await db_session.commit()
```

## Migration from aiosqlite

If you're migrating from aiosqlite to asyncpg:

### Changes Required

1. **Update connection string**:
   ```python
   # Old (aiosqlite)
   sqlite+aiosqlite:///./test.db
   
   # New (asyncpg)
   postgresql+asyncpg://user:pass@host:port/db
   ```

2. **Remove SQLite-specific code**:
   ```python
   # Old (aiosqlite)
   connect_args={"check_same_thread": False}
   
   # New (asyncpg)
   # No connect_args needed
   ```

3. **Enable PostgreSQL extensions**:
   ```python
   # New requirement for asyncpg
   await conn.execute(text("CREATE EXTENSION IF NOT EXISTS ltree"))
   ```

4. **Update dependencies**:
   ```toml
   # Remove
   dev-dependencies = ["aiosqlite"]
   
   # Already included in main dependencies
   dependencies = ["asyncpg"]
   ```

### Benefits of Migration

- ✅ Full PostgreSQL feature support (LTREE, JSONB)
- ✅ Better performance for complex queries
- ✅ Production-like test environment
- ✅ Supabase compatibility
- ✅ No SQLite limitations

## Additional Resources

- [asyncpg Documentation](https://magicstack.github.io/asyncpg/)
- [PostgreSQL LTREE](https://www.postgresql.org/docs/current/ltree.html)
- [Supabase Documentation](https://supabase.com/docs)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [SQLAlchemy Async](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)

## Support

For issues or questions:
1. Check this documentation
2. Review test examples in `tests/unit/` and `tests/integration/`
3. Check the main project README
4. Review Windx integration plan documentation
