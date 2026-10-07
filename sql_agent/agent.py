"""Standalone Telecom SQL Agent CLI.

Allows staff, evaluators, and developers to interactively query
the telecom operations database in natural language using LlamaIndex
Semantic SQL.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure prodapt-project is on path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sql_agent.semantic_search import (
    DATABASE_PATH,
    ask_sql,
    create_query_engine,
    get_table_names,
)


def run_interactive_cli() -> None:
    """Run an interactive natural language SQL query session."""
    print("\n" + "=" * 50)
    print("       PRODAPT TELECOM SQL AGENT")
    print("=" * 50)
    print(f"Database: {DATABASE_PATH}")

    try:
        tables = get_table_names()
        print(f"Available tables ({len(tables)}): {', '.join(tables)}")
    except Exception as e:
        print(f"Warning: Could not list tables ({e})")

    print("\nWarm up semantic SQL engine...")
    try:
        create_query_engine()
        print("Engine ready.")
    except Exception as e:
        print(f"Engine initialization note: {e}")

    print("\nEnter a question in plain English (or 'exit' to quit).")
    print("Example queries:")
    print("  - Which region had the most CRITICAL network outages?")
    print("  - Which towers have the highest packet loss right now?")
    print("  - How long was the Midwest outage on 12 September 2026, and how many customers?")
    print("  - How many towers are in the Southwest region?")
    print("-" * 50)

    while True:
        try:
            query = input("\nSQL Question: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nSession ended.")
            break

        if not query:
            continue

        if query.lower() in {"exit", "quit", "q"}:
            print("Exiting SQL Agent.")
            break

        print("\nThinking and querying database...")
        try:
            answer = ask_sql(query)
            print("\n" + "=" * 50)
            print("RESPONSE:")
            print("=" * 50)
            print(answer)
        except Exception as err:
            print("\n" + "=" * 50)
            print("ERROR:")
            print("=" * 50)
            print(err)


if __name__ == "__main__":
    run_interactive_cli()
