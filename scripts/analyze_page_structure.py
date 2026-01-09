#!/usr/bin/env python3
"""Analyze page structure script with beautiful Rich output.

This script analyzes the current system to show:
- What pages (page types) we have
- How many columns (attributes) each page has
- Optionally display the column names

Usage:
    python analyze_page_structure.py
    python analyze_page_structure.py --show-columns
    python analyze_page_structure.py --manufacturing-type-id 546
"""

import asyncio
import argparse
import sys
from pathlib import Path
from typing import Dict, List, Optional

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns
from rich.text import Text
from rich.tree import Tree
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.layout import Layout
from rich.align import Align
from rich import box
from rich.rule import Rule

from app.database.connection import get_engine, get_session_maker
from app.models.attribute_node import AttributeNode
from app.models.manufacturing_type import ManufacturingType

# Initialize Rich console
console = Console()


async def get_manufacturing_types(session: AsyncSession) -> List[ManufacturingType]:
    """Get all active manufacturing types."""
    stmt = select(ManufacturingType).where(ManufacturingType.is_active == True)
    result = await session.execute(stmt)
    return result.scalars().all()


async def get_page_structure(
    session: AsyncSession, manufacturing_type_id: Optional[int] = None, show_columns: bool = False
) -> Dict:
    """Analyze page structure for manufacturing types."""

    # Build base query
    if manufacturing_type_id:
        # Analyze specific manufacturing type
        stmt_count = (
            select(
                ManufacturingType.id,
                ManufacturingType.name,
                AttributeNode.page_type,
                func.count(AttributeNode.id).label("column_count"),
            )
            .join(AttributeNode, ManufacturingType.id == AttributeNode.manufacturing_type_id)
            .where(
                ManufacturingType.id == manufacturing_type_id, ManufacturingType.is_active == True
            )
            .group_by(ManufacturingType.id, ManufacturingType.name, AttributeNode.page_type)
            .order_by(ManufacturingType.name, AttributeNode.page_type)
        )
    else:
        # Analyze all manufacturing types
        stmt_count = (
            select(
                ManufacturingType.id,
                ManufacturingType.name,
                AttributeNode.page_type,
                func.count(AttributeNode.id).label("column_count"),
            )
            .join(AttributeNode, ManufacturingType.id == AttributeNode.manufacturing_type_id)
            .where(ManufacturingType.is_active == True)
            .group_by(ManufacturingType.id, ManufacturingType.name, AttributeNode.page_type)
            .order_by(ManufacturingType.name, AttributeNode.page_type)
        )

    result = await session.execute(stmt_count)
    page_counts = result.fetchall()

    # Structure the data
    structure = {}

    for row in page_counts:
        mfg_type_key = f"{row.name} (ID: {row.id})"

        if mfg_type_key not in structure:
            structure[mfg_type_key] = {
                "manufacturing_type_id": row.id,
                "manufacturing_type_name": row.name,
                "pages": {},
            }

        structure[mfg_type_key]["pages"][row.page_type] = {
            "column_count": row.column_count,
            "columns": [],
        }

    # If show_columns is True, get the actual column names
    if show_columns:
        for mfg_type_key, mfg_data in structure.items():
            mfg_type_id = mfg_data["manufacturing_type_id"]

            for page_type in mfg_data["pages"].keys():
                # Get column names for this page type
                stmt_columns = (
                    select(AttributeNode.name, AttributeNode.sort_order)
                    .where(
                        AttributeNode.manufacturing_type_id == mfg_type_id,
                        AttributeNode.page_type == page_type,
                    )
                    .order_by(AttributeNode.sort_order, AttributeNode.name)
                )

                result_columns = await session.execute(stmt_columns)
                columns = [row.name for row in result_columns.fetchall()]

                structure[mfg_type_key]["pages"][page_type]["columns"] = columns

    return structure


async def get_page_type_summary(session: AsyncSession) -> Dict:
    """Get summary of all page types across the system."""
    stmt = (
        select(
            AttributeNode.page_type,
            func.count(func.distinct(AttributeNode.manufacturing_type_id)).label(
                "manufacturing_types_count"
            ),
            func.count(AttributeNode.id).label("total_attributes"),
            func.avg(func.count(AttributeNode.id))
            .over(partition_by=AttributeNode.page_type)
            .label("avg_attributes_per_type"),
        )
        .join(ManufacturingType, AttributeNode.manufacturing_type_id == ManufacturingType.id)
        .where(ManufacturingType.is_active == True)
        .group_by(AttributeNode.page_type)
        .order_by(AttributeNode.page_type)
    )

    result = await session.execute(stmt)
    summary_data = result.fetchall()

    summary = {}
    for row in summary_data:
        summary[row.page_type] = {
            "manufacturing_types_using": row.manufacturing_types_count,
            "total_attributes": row.total_attributes,
        }

    return summary


def print_structure(structure: Dict, show_columns: bool = False):
    """Print the page structure in a beautiful Rich format."""

    # Create main title
    title = Text("WindX Page Structure Analysis", style="bold magenta")
    console.print(Panel(title, box=box.DOUBLE, padding=(1, 2)))

    if not structure:
        console.print(
            Panel(
                "❌ No manufacturing types with attributes found.",
                style="bold red",
                box=box.ROUNDED,
            )
        )
        return

    total_pages = 0
    total_columns = 0

    # Create a tree for the structure
    tree = Tree("🏭 [bold blue]Manufacturing Types[/bold blue]")

    for mfg_type_key, mfg_data in structure.items():
        # Add manufacturing type branch
        mfg_branch = tree.add(f"[bold green]{mfg_type_key}[/bold green]")

        pages = mfg_data["pages"]
        if not pages:
            mfg_branch.add("[yellow]⚠️ No pages found[/yellow]")
            continue

        for page_type, page_data in pages.items():
            column_count = page_data["column_count"]
            total_pages += 1
            total_columns += column_count

            # Color code page types
            page_colors = {"profile": "cyan", "accessories": "yellow", "glazing": "green"}
            color = page_colors.get(page_type.lower(), "white")

            # Add page branch
            page_branch = mfg_branch.add(
                f"[{color}]📄 {page_type.upper()}[/{color}] "
                f"[bold white]({column_count} columns)[/bold white]"
            )

            if show_columns and page_data["columns"]:
                # Create columns table for this page
                columns_table = Table(
                    title=f"{page_type.title()} Columns",
                    box=box.MINIMAL,
                    show_header=True,
                    header_style="bold magenta",
                )
                columns_table.add_column("#", style="dim", width=3)
                columns_table.add_column("Column Name", style="cyan")

                for i, column_name in enumerate(page_data["columns"], 1):
                    columns_table.add_row(str(i), column_name)

                # Add table to tree (this will be displayed separately)
                page_branch.add(f"[dim]→ See detailed table below[/dim]")

    console.print(tree)

    # Show detailed column tables if requested
    if show_columns:
        console.print(Rule("[bold blue]Detailed Column Information[/bold blue]"))

        for mfg_type_key, mfg_data in structure.items():
            pages = mfg_data["pages"]

            for page_type, page_data in pages.items():
                if page_data["columns"]:
                    # Create a beautiful table for columns
                    columns_table = Table(
                        title=f"[bold]{mfg_type_key} - {page_type.title()} Page[/bold]",
                        box=box.ROUNDED,
                        show_header=True,
                        header_style="bold magenta",
                        title_style="bold blue",
                    )
                    columns_table.add_column("#", style="dim", width=4, justify="right")
                    columns_table.add_column("Column Name", style="cyan", min_width=20)
                    columns_table.add_column("Type", style="yellow", width=12)

                    for i, column_name in enumerate(page_data["columns"], 1):
                        # Add some visual variety
                        row_style = "dim" if i % 2 == 0 else None
                        columns_table.add_row(str(i), column_name, "Attribute", style=row_style)

                    console.print(columns_table)
                    console.print()

    # Create summary panel
    summary_table = Table(box=box.MINIMAL, show_header=False)
    summary_table.add_column("Metric", style="bold cyan")
    summary_table.add_column("Value", style="bold green")

    summary_table.add_row("Manufacturing Types", str(len(structure)))
    summary_table.add_row("Total Pages", str(total_pages))
    summary_table.add_row("Total Columns", str(total_columns))
    if total_pages > 0:
        summary_table.add_row("Avg Columns/Page", f"{total_columns / total_pages:.1f}")

    console.print(
        Panel(
            summary_table,
            title="[bold blue]📈 Summary Statistics[/bold blue]",
            box=box.DOUBLE,
            padding=(1, 2),
        )
    )


def print_page_type_summary(summary: Dict):
    """Print summary of page types in a beautiful Rich format."""

    if not summary:
        console.print(Panel("❌ No page types found.", style="bold red", box=box.ROUNDED))
        return

    # Create page type summary table
    summary_table = Table(
        title="[bold blue]📋 Page Type Summary[/bold blue]",
        box=box.HEAVY,
        show_header=True,
        header_style="bold magenta",
    )

    summary_table.add_column("Page Type", style="bold cyan", width=15)
    summary_table.add_column("Manufacturing Types", justify="center", style="yellow", width=18)
    summary_table.add_column("Total Attributes", justify="center", style="green", width=16)
    summary_table.add_column("Visual", width=20)

    # Add visual bars for attributes
    max_attributes = max(data["total_attributes"] for data in summary.values())

    for page_type, data in summary.items():
        # Create a simple bar visualization
        bar_length = int((data["total_attributes"] / max_attributes) * 15)
        bar = "█" * bar_length + "░" * (15 - bar_length)

        # Color code the page types
        page_colors = {"profile": "cyan", "accessories": "yellow", "glazing": "green"}
        color = page_colors.get(page_type.lower(), "white")

        summary_table.add_row(
            f"[{color}]{page_type.upper()}[/{color}]",
            str(data["manufacturing_types_using"]),
            str(data["total_attributes"]),
            f"[{color}]{bar}[/{color}]",
        )

    console.print(summary_table)


def print_manufacturing_types(manufacturing_types: List[ManufacturingType]):
    """Print available manufacturing types in a beautiful format."""

    if not manufacturing_types:
        console.print(
            Panel("❌ No active manufacturing types found.", style="bold red", box=box.ROUNDED)
        )
        return

    # Create manufacturing types table
    mfg_table = Table(
        title="[bold blue]🏭 Available Manufacturing Types[/bold blue]",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold magenta",
    )

    mfg_table.add_column("ID", style="dim", width=5, justify="right")
    mfg_table.add_column("Name", style="bold cyan", min_width=25)
    mfg_table.add_column("Description", style="yellow", min_width=30)
    mfg_table.add_column("Category", style="green", width=10)

    for mfg_type in manufacturing_types:
        # Truncate long descriptions
        description = mfg_type.description or "No description"
        if len(description) > 50:
            description = description[:47] + "..."

        mfg_table.add_row(
            str(mfg_type.id), mfg_type.name, description, mfg_type.base_category or "N/A"
        )

    console.print(mfg_table)

    # Add helpful tips
    tips_panel = Panel(
        "[bold cyan]💡 Tips:[/bold cyan]\n"
        "• Use [bold]--manufacturing-type-id <ID>[/bold] to analyze a specific type\n"
        "• Use [bold]--show-columns[/bold] to see column names\n"
        "• Use [bold]--summary-only[/bold] for a quick overview",
        title="[bold green]Usage Tips[/bold green]",
        box=box.ROUNDED,
        padding=(1, 2),
    )
    console.print(tips_panel)


async def main():
    """Main analysis function with beautiful Rich output."""
    parser = argparse.ArgumentParser(
        description="Analyze WindX page structure with beautiful output"
    )
    parser.add_argument(
        "--show-columns", action="store_true", help="Show column names for each page"
    )
    parser.add_argument(
        "--manufacturing-type-id", type=int, help="Analyze specific manufacturing type ID only"
    )
    parser.add_argument("--summary-only", action="store_true", help="Show only page type summary")

    args = parser.parse_args()

    # Create a beautiful header
    console.print()
    header = Text("WindX Page Structure Analyzer", style="bold magenta")
    console.print(
        Panel(Align.center(header), box=box.DOUBLE_EDGE, padding=(1, 2), style="bold blue")
    )

    engine = get_engine()
    session_maker = get_session_maker()

    try:
        # Show progress spinner
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
        ) as progress:
            task = progress.add_task("🔍 Analyzing database structure...", total=None)

            async with session_maker() as session:
                if args.summary_only:
                    # Show only page type summary
                    progress.update(task, description="📊 Generating page type summary...")
                    summary = await get_page_type_summary(session)
                    progress.stop()

                    console.print()
                    print_page_type_summary(summary)
                else:
                    # Show detailed structure
                    progress.update(task, description="🏗️ Building page structure...")
                    structure = await get_page_structure(
                        session,
                        manufacturing_type_id=args.manufacturing_type_id,
                        show_columns=args.show_columns,
                    )

                    progress.update(task, description="📈 Calculating summary statistics...")
                    summary = await get_page_type_summary(session)

                    progress.stop()

                    console.print()
                    print_structure(structure, show_columns=args.show_columns)
                    console.print()
                    print_page_type_summary(summary)

                # Show available manufacturing types for reference
                if not args.manufacturing_type_id:
                    console.print()
                    console.print(Rule("[bold blue]Available Manufacturing Types[/bold blue]"))

                    manufacturing_types = await get_manufacturing_types(session)
                    print_manufacturing_types(manufacturing_types)

    except Exception as e:
        console.print()
        error_panel = Panel(
            f"[bold red]❌ Error during analysis:[/bold red]\n[red]{str(e)}[/red]",
            title="[bold red]Error[/bold red]",
            box=box.HEAVY,
            padding=(1, 2),
        )
        console.print(error_panel)

        # Show traceback in debug mode
        import traceback

        console.print("\n[dim]Traceback:[/dim]")
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        sys.exit(1)
    finally:
        await engine.dispose()

        # Show completion message
        console.print()
        completion_panel = Panel(
            "[bold green]✅ Analysis completed successfully![/bold green]",
            box=box.ROUNDED,
            padding=(0, 2),
            style="green",
        )
        console.print(completion_panel)


if __name__ == "__main__":
    asyncio.run(main())
