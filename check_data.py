#!/usr/bin/env python3
"""Check data loading."""

import duckdb

conn = duckdb.connect('data/processed/o2c_graph.db')
result = conn.execute('SELECT COUNT(*) FROM sales_order_headers').fetchall()
print('Sales order headers count:', result[0][0])

result = conn.execute('SELECT COUNT(*) FROM sales_order_items').fetchall()
print('Sales order items count:', result[0][0])

conn.close()