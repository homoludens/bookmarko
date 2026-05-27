import pymysql
import psycopg2
from psycopg2.extras import execute_batch

# Connect to MySQL using pymysql
mysql_conn = pymysql.connect(
    host='localhost',
    user='root',
    database='flaskmarks'
)

# Rest of the script stays the same
pg_conn = psycopg2.connect('postgresql://bookm_user:digestpass@localhost:5432/bookmarko')

mysql_cur = mysql_conn.cursor(pymysql.cursors.DictCursor)
pg_cur = pg_conn.cursor()

# Get all tables
mysql_cur.execute("SHOW TABLES")
tables = [list(table.values())[0] for table in mysql_cur]

tables = [ 'users', 'marks', 'tags', 'marks_tags']
print(tables)

for table in tables:
    print(f"Migrating {table}...")

    # Get column names
    mysql_cur.execute(f"SHOW COLUMNS FROM {table}")
    columns = [col['Field'] for col in mysql_cur]

    # Fetch data in batches
    mysql_cur.execute(f"SELECT * FROM {table}")
    batch_size = 1000

    while True:
        rows = mysql_cur.fetchmany(batch_size)
        if not rows:
            break

        # Insert into PostgreSQL
        placeholders = ','.join(['%s'] * len(columns))
        insert_query = f"INSERT INTO {table} ({','.join(columns)}) VALUES ({placeholders})"

        execute_batch(pg_cur, insert_query, [tuple(row.values()) for row in rows])
        pg_conn.commit()
        print(f"  Migrated {len(rows)} rows")

print("Migration complete!")
pg_conn.close()
mysql_conn.close()
