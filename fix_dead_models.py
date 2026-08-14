import sqlite3
conn = sqlite3.connect(r'C:\Users\Motunrayo\.omniroute\storage.sqlite')
cursor = conn.cursor()
cursor.execute("UPDATE provider_connections SET test_status = 'deactivated' WHERE provider IN ('nvidia', 'opencode')")
conn.commit()
print('Updated', cursor.rowcount, 'rows')
cursor.execute('SELECT id, provider, test_status FROM provider_connections')
for r in cursor.fetchall():
    print(r)
conn.close()