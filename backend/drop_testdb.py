import psycopg2
conn = psycopg2.connect(dbname='postgres', user='postgres', password='postgres', host='localhost', port='5433')
conn.autocommit = True
cur = conn.cursor()
cur.execute("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='test_dementianext_db' AND pid <> pg_backend_pid()")
cur.execute("DROP DATABASE IF EXISTS test_dementianext_db")
print("Dropped test_dementianext_db")
cur.close()
conn.close()
