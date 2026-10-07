"""sql_agent — LlamaIndex Semantic SQL module for telecom analytics.

Implements Section 6.2 of the Prodapt AI Operations Center specification.
Connects to telecom_ops.db and uses LlamaIndex ObjectIndex +
SQLTableRetrieverQueryEngine to semantically select tables and execute
natural-language SQL queries.
"""

from .semantic_search import (
    DATABASE_PATH,
    execute_query,
    get_connection,
    get_table_names,
    show_schema,
    show_tables,
)
from .semantic_search import ANALYTICS_TABLES, ask_sql, create_query_engine

__all__ = [
    "DATABASE_PATH",
    "ANALYTICS_TABLES",
    "ask_sql",
    "create_query_engine",
    "get_connection",
    "get_table_names",
    "execute_query",
    "show_tables",
    "show_schema",
]