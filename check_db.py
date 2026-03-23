#!/usr/bin/env python3
"""Check database tables."""

import duckdb

conn = duckdb.connect('data/processed/o2c_graph.db')
tables = [row[0] for row in conn.execute('SHOW TABLES').fetchall()]
print('Tables:', tables)

# Check one table
if tables:
    result = conn.execute(f'SELECT COUNT(*) FROM {tables[0]}').fetchall()
    print(f'{tables[0]} count:', result[0][0])

conn.close()