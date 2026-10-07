import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).parent

conn = sqlite3.connect(BASE_DIR / "telecom_ops.db")

with open(BASE_DIR / "sql" / "01_schema.sql") as f:
    conn.executescript(f.read())

with open(BASE_DIR / "sql" / "02_seed_data.sql") as f:
    conn.executescript(f.read())

conn.close()

print("Database created and populated successfully!") 

