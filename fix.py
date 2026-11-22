import sqlite3
conn = sqlite3.connect('thrift.db')
cols = ['avatar TEXT DEFAULT ""', 'email TEXT DEFAULT ""', 'bio TEXT DEFAULT ""', 'location TEXT DEFAULT ""']
for col in cols:
    try:
        conn.execute(f'ALTER TABLE users ADD COLUMN {col}')
        print(f'users.{col.split()[0]}: done')
    except:
        print(f'users.{col.split()[0]}: sudah ada')
try:
    conn.execute('ALTER TABLE products ADD COLUMN discount INTEGER DEFAULT 0')
    print('products.discount: done')
except:
    print('products.discount: sudah ada')
conn.commit()
conn.close()
print('selesai!')