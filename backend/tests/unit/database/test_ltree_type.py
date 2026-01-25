"""Tests for LTREE custom database type.

This module tests the LTREE type implementation including:
- Type conversion (Python string <-> LTREE)
- Custom operators (ancestor_of, descendant_of, lquery)
- Comparator functionality
"""

from sqlalchemy import Index, select
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.database.types import LTREE, LtreeType


class TestLTREEType:
    """Test LTREE type functionality."""

    def test_ltree_get_col_spec(self):
        """Test LTREE column specification for DDL."""
        ltree_type = LTREE()
        assert ltree_type.get_col_spec() == "LTREE"

    def test_ltree_bind_processor(self):
        """Test LTREE bind processor converts strings correctly."""
        ltree_type = LTREE()
        processor = ltree_type.bind_processor(None)

        # Test string conversion
        assert processor("root.child.grandchild") == "root.child.grandchild"

        # Test None handling
        assert processor(None) is None

    def test_ltree_result_processor(self):
        """Test LTREE result processor converts values correctly."""
        ltree_type = LTREE()
        processor = ltree_type.result_processor(None, None)

        # Test string conversion
        assert processor("root.child") == "root.child"

        # Test None handling
        assert processor(None) is None

    def test_ltree_comparator_ancestor_of(self):
        """Test LTREE ancestor_of operator."""

        # Create a test model
        class TestNode(Base):
            __tablename__ = "test_nodes_ancestor"
            id: Mapped[int] = mapped_column(primary_key=True)
            path: Mapped[str] = mapped_column(LTREE, nullable=False)

        # Test that ancestor_of creates correct expression
        expr = TestNode.path.ancestor_of("root.child.grandchild")
        assert "@>" in str(expr)

    def test_ltree_comparator_descendant_of(self):
        """Test LTREE descendant_of operator."""

        # Create a test model
        class TestNode(Base):
            __tablename__ = "test_nodes_descendant"
            id: Mapped[int] = mapped_column(primary_key=True)
            path: Mapped[str] = mapped_column(LTREE, nullable=False)

        # Test that descendant_of creates correct expression
        expr = TestNode.path.descendant_of("root.child")
        assert "<@" in str(expr)

    def test_ltree_comparator_lquery(self):
        """Test LTREE lquery pattern matching operator."""

        # Create a test model
        class TestNode(Base):
            __tablename__ = "test_nodes_lquery"
            id: Mapped[int] = mapped_column(primary_key=True)
            path: Mapped[str] = mapped_column(LTREE, nullable=False)

        # Test that lquery creates correct expression
        expr = TestNode.path.lquery("*.child.*")
        assert "~" in str(expr)


class TestLtreeType:
    """Test LtreeType decorator functionality."""

    def test_ltree_type_process_bind_param(self):
        """Test LtreeType bind parameter processing."""
        ltree_type = LtreeType()

        # Test string conversion
        assert ltree_type.process_bind_param("root.child", None) == "root.child"

        # Test None handling
        assert ltree_type.process_bind_param(None, None) is None

    def test_ltree_type_process_result_value(self):
        """Test LtreeType result value processing."""
        ltree_type = LtreeType()

        # Test string conversion
        assert ltree_type.process_result_value("root.child", None) == "root.child"

        # Test None handling
        assert ltree_type.process_result_value(None, None) is None


class TestLTREEModelDefinition:
    """Test LTREE type in model definitions."""

    def test_model_with_ltree_column(self):
        """Test creating a model with LTREE column."""

        class AttributeNode(Base):
            __tablename__ = "test_attribute_nodes"

            id: Mapped[int] = mapped_column(primary_key=True)
            name: Mapped[str] = mapped_column()
            ltree_path: Mapped[str] = mapped_column(LTREE, nullable=False)

            __table_args__ = (Index("idx_test_ltree_path", "ltree_path", postgresql_using="gist"),)

        # Verify table was created
        assert AttributeNode.__tablename__ == "test_attribute_nodes"
        assert hasattr(AttributeNode, "ltree_path")

        # Verify column type
        ltree_column = AttributeNode.__table__.c.ltree_path
        assert isinstance(ltree_column.type, LTREE)

    def test_model_with_ltree_type_decorator(self):
        """Test creating a model with LtreeType decorator."""

        class Node(Base):
            __tablename__ = "test_nodes_decorator"

            id: Mapped[int] = mapped_column(primary_key=True)
            path: Mapped[str] = mapped_column(LtreeType, nullable=False)

        # Verify table was created
        assert Node.__tablename__ == "test_nodes_decorator"
        assert hasattr(Node, "path")

        # Verify column type
        path_column = Node.__table__.c.path
        assert isinstance(path_column.type, LtreeType)


class TestLTREEQueryExamples:
    """Test LTREE query patterns."""

    def test_query_descendants_example(self):
        """Test example query for finding descendants."""

        class Node(Base):
            __tablename__ = "test_query_descendants"
            id: Mapped[int] = mapped_column(primary_key=True)
            path: Mapped[str] = mapped_column(LTREE, nullable=False)

        # Create query for descendants
        query = select(Node).where(Node.path.descendant_of("root.child"))

        # Verify query structure
        query_str = str(query)
        assert "test_query_descendants" in query_str
        assert "<@" in query_str

    def test_query_ancestors_example(self):
        """Test example query for finding ancestors."""

        class Node(Base):
            __tablename__ = "test_query_ancestors"
            id: Mapped[int] = mapped_column(primary_key=True)
            path: Mapped[str] = mapped_column(LTREE, nullable=False)

        # Create query for ancestors
        query = select(Node).where(Node.path.ancestor_of("root.child.grandchild"))

        # Verify query structure
        query_str = str(query)
        assert "test_query_ancestors" in query_str
        assert "@>" in query_str

    def test_query_pattern_matching_example(self):
        """Test example query for pattern matching."""

        class Node(Base):
            __tablename__ = "test_query_pattern"
            id: Mapped[int] = mapped_column(primary_key=True)
            path: Mapped[str] = mapped_column(LTREE, nullable=False)

        # Create query with pattern matching
        query = select(Node).where(Node.path.lquery("*.material.*"))

        # Verify query structure
        query_str = str(query)
        assert "test_query_pattern" in query_str
        assert "~" in query_str
