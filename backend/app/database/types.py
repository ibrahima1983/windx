"""Custom database types for PostgreSQL extensions.

This module provides custom SQLAlchemy types for PostgreSQL-specific
features, including LTREE for hierarchical data.

Public Classes:
    LTREE: Custom type for PostgreSQL LTREE extension
    LtreeType: SQLAlchemy type decorator for LTREE columns

Features:
    - LTREE type support for hierarchical paths
    - Custom operators (ancestor_of, descendant_of, lquery)
    - Automatic type conversion between Python strings and LTREE
    - GiST index support for efficient queries

Example:
    ```python
    from app.database.types import LTREE
    from sqlalchemy.orm import Mapped, mapped_column

    class AttributeNode(Base):
        __tablename__ = "attribute_nodes"

        id: Mapped[int] = mapped_column(primary_key=True)
        ltree_path: Mapped[str] = mapped_column(LTREE, nullable=False)

        # Define GiST index for efficient hierarchical queries
        __table_args__ = (
            Index('idx_ltree_path', 'ltree_path', postgresql_using='gist'),
        )
    ```

LTREE Operators:
    - `<@`: Is descendant of (contained by)
    - `@>`: Is ancestor of (contains)
    - `~`: Matches lquery pattern
    - `?`: Matches ltxtquery

Usage with queries:
    ```python
    # Get all descendants of a node
    descendants = await session.execute(
        select(AttributeNode).where(
            AttributeNode.ltree_path.descendant_of('root.child')
        )
    )

    # Get all ancestors of a node
    ancestors = await session.execute(
        select(AttributeNode).where(
            AttributeNode.ltree_path.ancestor_of('root.child.grandchild')
        )
    )

    # Pattern matching
    matches = await session.execute(
        select(AttributeNode).where(
            AttributeNode.ltree_path.lquery('*.material.*')
        )
    )
    ```
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import Text
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql import expression
from sqlalchemy.types import TypeDecorator, UserDefinedType

__all__ = ["LTREE", "LtreeType"]


class LTREE(UserDefinedType):
    """PostgreSQL LTREE type for hierarchical data.

    LTREE represents labels of data stored in a hierarchical tree-like structure.
    Labels are sequences of alphanumeric characters and underscores separated by dots.

    Example paths:
        - 'root'
        - 'root.child'
        - 'root.child.grandchild'
        - 'window.frame.material.aluminum'

    This type provides efficient storage and querying of hierarchical data using
    PostgreSQL's LTREE extension with GiST indexing support.

    Attributes:
        cache_ok: Enables SQLAlchemy caching for this type
    """

    cache_ok = True

    def get_col_spec(self, **kw: Any) -> str:
        """Return the column specification for DDL.

        Returns:
            str: The PostgreSQL type name 'LTREE'
        """
        return "LTREE"

    def bind_processor(self, dialect: Any) -> Any:
        """Process values before sending to database.

        Args:
            dialect: The database dialect

        Returns:
            Callable or None: Processor function for binding values
        """

        def process(value: str | None) -> str | None:
            """Convert Python string to LTREE format.

            Args:
                value: Python string representing LTREE path

            Returns:
                str or None: LTREE-formatted string
            """
            if value is not None:
                # Ensure value is a string
                return str(value)
            return None

        return process

    def result_processor(self, dialect: Any, coltype: Any) -> Any:
        """Process values received from database.

        Args:
            dialect: The database dialect
            coltype: The column type

        Returns:
            Callable or None: Processor function for result values
        """

        def process(value: str | None) -> str | None:
            """Convert LTREE value to Python string.

            Args:
                value: LTREE value from database

            Returns:
                str or None: Python string representation
            """
            if value is not None:
                return str(value)
            return None

        return process

    # noinspection PyPep8Naming
    class comparator_factory(UserDefinedType.Comparator):
        """Custom comparator for LTREE operators.

        Provides methods for LTREE-specific comparison operations:
        - ancestor_of: Check if path is ancestor of another
        - descendant_of: Check if path is descendant of another
        - lquery: Pattern matching with lquery syntax
        """

        def ancestor_of(self, other: Any) -> Any:
            """Check if this path is an ancestor of another path.

            Uses the PostgreSQL @> operator (contains).

            Args:
                other: The path to compare against

            Returns:
                BinaryExpression: SQL expression for ancestor check

            Example:
                ```python
                # Find all nodes that are ancestors of 'root.child.grandchild'
                query = select(Node).where(
                    Node.ltree_path.ancestor_of('root.child.grandchild')
                )
                # Returns: root, root.child
                ```
            """
            return self.op("@>")(other)

        def descendant_of(self, other: Any) -> Any:
            """Check if this path is a descendant of another path.

            Uses the PostgreSQL <@ operator (contained by).

            Args:
                other: The path to compare against

            Returns:
                BinaryExpression: SQL expression for descendant check

            Example:
                ```python
                # Find all nodes that are descendants of 'root.child'
                query = select(Node).where(
                    Node.ltree_path.descendant_of('root.child')
                )
                # Returns: root.child.grandchild, root.child.great_grandchild
                ```
            """
            return self.op("<@")(other)

        def lquery(self, pattern: str) -> Any:
            """Match path against lquery pattern.

            Uses the PostgreSQL ~ operator for pattern matching.

            Args:
                pattern: lquery pattern string

            Returns:
                BinaryExpression: SQL expression for pattern match

            Example:
                ```python
                # Find all nodes with 'material' anywhere in path
                query = select(Node).where(
                    Node.ltree_path.lquery('*.material.*')
                )

                # Find all nodes at specific depth
                query = select(Node).where(
                    Node.ltree_path.lquery('*{3}')  # Exactly 3 levels deep
                )
                ```
            """
            return self.op("~")(pattern)


class LtreeType(TypeDecorator):
    """Type decorator for LTREE columns with Text fallback.

    This decorator provides LTREE functionality while falling back to
    Text type for databases that don't support LTREE (e.g., SQLite for testing).

    Attributes:
        impl: The underlying type implementation (Text)
        cache_ok: Enables SQLAlchemy caching for this type

    Example:
        ```python
        from app.database.types import LtreeType

        class Node(Base):
            __tablename__ = "nodes"

            id: Mapped[int] = mapped_column(primary_key=True)
            path: Mapped[str] = mapped_column(LtreeType, nullable=False)
        ```
    """

    impl = Text
    cache_ok = True

    def load_dialect_impl(self, dialect: Any) -> Any:
        """Load the appropriate type for the dialect.

        Args:
            dialect: The database dialect

        Returns:
            TypeEngine: LTREE for PostgreSQL, Text for others
        """
        if dialect.name == "postgresql":
            return dialect.type_descriptor(LTREE())
        else:
            return dialect.type_descriptor(Text())

    def process_bind_param(self, value: str | None, dialect: Any) -> str | None:
        """Process value before binding to database.

        Args:
            value: Python string value
            dialect: The database dialect

        Returns:
            str or None: Processed value
        """
        if value is not None:
            return str(value)
        return None

    def process_result_value(self, value: str | None, dialect: Any) -> str | None:
        """Process value received from database.

        Args:
            value: Database value
            dialect: The database dialect

        Returns:
            str or None: Python string value
        """
        if value is not None:
            return str(value)
        return None


# Custom SQL expressions for LTREE functions
# noinspection PyPep8Naming
class ltree_subpath(expression.FunctionElement):
    """Extract subpath from LTREE path.

    Example:
        ```python
        # Get subpath from position 1 to 3
        subpath = select(ltree_subpath(Node.ltree_path, 1, 3))
        ```
    """

    type = LTREE()
    name = "subpath"


@compiles(ltree_subpath)
def compile_ltree_subpath(element: Any, compiler: Any, **kw: Any) -> str:
    """Compile ltree_subpath function to SQL.

    Args:
        element: The function element
        compiler: The SQL compiler
        **kw: Additional keyword arguments

    Returns:
        str: Compiled SQL string
    """
    return f"subpath({compiler.process(element.clauses, **kw)})"


# noinspection PyPep8Naming
class ltree_nlevel(expression.FunctionElement):
    """Get the depth (number of labels) in LTREE path.

    Example:
        ```python
        # Get depth of path
        depth = select(ltree_nlevel(Node.ltree_path))
        # 'root.child.grandchild' returns 3
        ```
    """

    type = Text()
    name = "nlevel"


@compiles(ltree_nlevel)
def compile_ltree_nlevel(element: Any, compiler: Any, **kw: Any) -> str:
    """Compile ltree_nlevel function to SQL.

    Args:
        element: The function element
        compiler: The SQL compiler
        **kw: Additional keyword arguments

    Returns:
        str: Compiled SQL string
    """
    return f"nlevel({compiler.process(element.clauses, **kw)})"
