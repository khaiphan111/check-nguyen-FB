from app import db

cur = db.get_conn().conn.cursor()
cur.execute("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state = 'idle in transaction'")
print("Killed idle transactions")
