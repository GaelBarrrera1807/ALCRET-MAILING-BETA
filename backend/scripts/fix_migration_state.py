"""Remove the companies 0006 migration record from django_migrations table.
Safe because 0006 had zero database impact."""
import psycopg2

conn = psycopg2.connect(
    host="localhost", port=5432, dbname="industrial_prospecting",
    user="postgres", password="alcretdbpassword22",
)
cur = conn.cursor()
cur.execute(
    "DELETE FROM django_migrations WHERE app=%s AND name=%s",
    ("companies", "0006_move_to_core"),
)
print("Deleted", cur.rowcount, "record(s)")
conn.commit()
cur.close()
conn.close()
