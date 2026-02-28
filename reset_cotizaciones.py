import sqlite3
conn = sqlite3.connect('web/data/aroluz.db')
conn.execute('DELETE FROM cotizaciones')
conn.execute("UPDATE sqlite_sequence SET seq = 0 WHERE name = 'cotizaciones'")
conn.execute("UPDATE sqlite_sequence SET seq = 0 WHERE name = 'cotizacion_items'")
conn.commit()
conn.close()
print('Listo.')
print('Listo.')
