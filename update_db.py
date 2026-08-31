import os
import sqlite3
from pathlib import Path

db_path = os.environ.get("OMNIROUTE_DB_PATH") or str(Path.home() / ".omniroute" / "storage.sqlite")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute("UPDATE provider_connections SET test_status = 'deactivated' WHERE provider IN ('nvidia', 'opencode')")
conn.commit()
print('Updated', cursor.rowcount, 'rows')
cursor.execute('SELECT id, provider, test_status FROM provider_connections')
for r in cursor.fetchall():
    print(r)
conn.close()