import psycopg2
import os
from keys import *
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

env = os.getenv('APP_ENV')

if env != 'production':
    conn = psycopg2.connect(
        dbname="postgres",
        user=db_username,
        password=db_password,
        host=db_host,
    )

    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)

    cur = conn.cursor()
    dbnames = []
    cur.execute("SELECT datname FROM pg_database;")
    for dbn in cur.fetchall():
        dbnames.append(dbn[0])

    if db_name not in dbnames:
        cur.execute("CREATE DATABASE {};".format(db_name))
        conn.commit()
        cur.close()
        conn.close()
        conn = psycopg2.connect(
            dbname=db_name,
            user=db_username,
            password=db_password,
            host=db_host,
        )
        cur = conn.cursor()
        cur.execute("CREATE SCHEMA reopt_api;")
        cur.execute("ALTER SCHEMA reopt_api OWNER TO {};".format(db_username))
        conn.commit()

    cur.close()
    conn.close()
