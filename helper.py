import sqlite3
import json
import argparse
import os

DATABASE = 'database/allegro.db'

def create():
    conn = sqlite3.connect(DATABASE)
    try:
        conn.execute('DROP TABLE products')
        conn.execute('DROP TABLE checked')
    except Exception as e:
        print(e)

    conn.execute('''
        CREATE TABLE products (
            id INTEGER PRIMARY KEY,
            name TEXT, 
            maxPrice REAL
        )
        ''')
    conn.execute('''
        CREATE UNIQUE INDEX n
            ON products (name)
        ''')
    conn.execute('''
        CREATE TABLE checked (
            id TEXT PRIMARY KEY,
            price REAL,
            url TEXT
        )
        ''')
    conn.commit()

    with open('products.json') as f:
        data = f.read()

    d_prod = json.loads(data)

    query = "INSERT INTO products(name, maxPrice) VALUES('{name}', {price})"

    for l in d_prod['products']:
        conn.execute(query.format(name=l['name'], price=l['max-price']))
    conn.commit()
    conn.close()

    print('ok')


def truncate():
    conn = sqlite3.connect(DATABASE)
    conn.execute('''
        DELETE FROM checked WHERE 1=1
        ''')
    conn.commit()
    conn.close()
    print('ok')


def show():
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()
    cur.execute('SELECT name, maxPrice FROM products')
    products = cur.fetchall()
    cur.execute('SELECT * FROM checked')
    checked = cur.fetchall()
    cur.close()
    conn.close()

    for p in products:
        print(p)

    for c in checked:
        print(c)


if __name__ == "__main__":
    try:
        parser = argparse.ArgumentParser()
        parser.add_argument('-t', type=str)
        args = parser.parse_args()
        if not os.path.exists('database'):
            os.makedirs('database')
            create()
        if args.t == 'create':
            create()
        elif args.t == 'truncate':
            truncate()
        else:
            try:
                show()
            except sqlite3.OperationalError:
                create()
                show()
    except KeyboardInterrupt:
        print('Keyboard interrupt was caught.')
        exit(0)