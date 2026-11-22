import sqlite3

conn = sqlite3.connect('thrift.db')
conn.row_factory = sqlite3.Row

# Reset semua data
conn.execute('DELETE FROM messages')
conn.execute('DELETE FROM orders')
conn.execute('DELETE FROM products')
conn.execute('DELETE FROM users')
conn.execute('UPDATE sqlite_sequence SET seq = 0')
conn.commit()

# ─── USERS ───────────────────────────────────────────────
users = [
    ('budi_thrift',  'budi@student.gunadarma.ac.id',  'password123'),
    ('sari_vintage', 'sari@student.gunadarma.ac.id',  'password123'),
    ('andi_buyer',   'andi@student.gunadarma.ac.id',  'password123'),
    ('rizky_seller', 'rizky@student.gunadarma.ac.id', 'password123'),
]
for u in users:
    conn.execute('INSERT INTO users (username, email, password) VALUES (?, ?, ?)', u)
conn.commit()

budi_id  = conn.execute("SELECT id FROM users WHERE username='budi_thrift'").fetchone()['id']
sari_id  = conn.execute("SELECT id FROM users WHERE username='sari_vintage'").fetchone()['id']
andi_id  = conn.execute("SELECT id FROM users WHERE username='andi_buyer'").fetchone()['id']
rizky_id = conn.execute("SELECT id FROM users WHERE username='rizky_seller'").fetchone()['id']

# Update bio & lokasi seller
conn.execute("UPDATE users SET bio='Seller thrift terpercaya, barang original semua!', location='Depok, Jawa Barat' WHERE id=?", (budi_id,))
conn.execute("UPDATE users SET bio='Vintage lover, koleksi jadul berkualitas.', location='Jakarta Selatan' WHERE id=?", (sari_id,))
conn.execute("UPDATE users SET bio='Jualan thrift sejak 2022, fast response!', location='Bekasi Utara' WHERE id=?", (rizky_id,))
conn.commit()

# ─── PRODUCTS ────────────────────────────────────────────
# (user_id, title, price, discount, category, location, description, size, condition, defect, stock, image, status, wa_number)
products = [
    (
        budi_id,
        'Jaket Denim Levis Vintage 90s',
        185000, 0,
        'Jaket', 'Depok',
        'Jaket denim Levis original vintage era 90an. Warna biru faded yang khas, kondisi masih sangat bagus. Beli di pasar thrift Bandung, dipakai hanya 2-3x. Cocok buat yang suka gaya retro.',
        'L', 'Baik', 'Fading ringan di bagian siku kiri, wajar untuk barang vintage',
        2, 'jaket_denim.jpg', 'available', '6281234567890'
    ),
    (
        budi_id,
        'Sepatu Converse Chuck 70 Hi Black',
        220000, 10,
        'Sepatu', 'Depok',
        'Converse Chuck 70 High warna hitam. Sole masih tebal, canvas masih bersih. Dijual karena upgrade ke ukuran yang lebih besar. Original bukan KW.',
        '42 EU', 'Cukup Baik', 'Yellowing ringan di bagian sol, wajar untuk pemakaian',
        1, 'converse_chuck.jpg', 'available', '6281234567890'
    ),
    (
        budi_id,
        'Kemeja Flannel Uniqlo Kotak Merah',
        75000, 0,
        'Baju', 'Depok',
        'Kemeja flannel Uniqlo motif kotak merah-hitam. Bahan tebal dan hangat, perfect buat cuaca dingin atau gaya kasual. Size M pas untuk badan 60-70kg tinggi 165-175cm.',
        'M', 'Sangat Baik', '-',
        3, 'flannel_uniqlo.jpg', 'available', '6281234567890'
    ),
    (
        budi_id,
        'Tas Ransel Outdoor REI 30L',
        150000, 0,
        'Tas', 'Jakarta',
        'Tas ransel REI original kapasitas 30 liter. Warna hitam, bahan cordura anti air. Semua zipper masih berfungsi normal. Cocok buat hiking, camping, atau aktivitas outdoor.',
        '-', 'Baik', 'Tali bahu kanan ada jahitan yang sedikit terlepas di ujung, tidak mengganggu fungsi',
        1, 'ransel_rei.jpg', 'available', '6281234567890'
    ),
    (
        sari_id,
        'Dress Vintage Floral Sundress',
        95000, 0,
        'Baju', 'Jakarta',
        'Sundress motif bunga-bunga vintage yang estetik banget. Bahan cotton adem, cocok buat OOTD casual atau hangout. Size S-M, ada tali adjustable di bagian pinggang.',
        'S', 'Sangat Baik', '-',
        2, 'dress_floral.jpg', 'available', '6289876543210'
    ),
    (
        sari_id,
        'Celana Mom Jeans High Waist',
        110000, 15,
        'Baju', 'Bekasi',
        'Mom jeans high waist warna light blue yang lagi trend. Potongan yang flattering untuk semua bentuk tubuh. Ukuran 28, bisa stretch sedikit untuk ukuran 29.',
        'M', 'Baik', 'Sedikit pudar di bagian lutut, masih terlihat estetik',
        1, 'mom_jeans.jpg', 'available', '6289876543210'
    ),
    (
        sari_id,
        'Bucket Hat Polos Cream Aesthetic',
        45000, 0,
        'Aksesoris', 'Bekasi',
        'Bucket hat warna cream polos yang timeless. Bahan cotton adem, tidak mudah kusut. One size fits all dengan tali pengencang di dalam. Perfect untuk beach day atau hangout.',
        'One Size', 'Sangat Baik', '-',
        5, 'bucket_hat.jpg', 'available', '6289876543210'
    ),
    (
        sari_id,
        'Kaos Oversize Thrasher Original',
        85000, 0,
        'Baju', 'Tangerang',
        'Kaos Thrasher original bukan KW. Warna hitam, logo Thrasher di depan masih jelas dan tidak crack. Bahan cotton tebal 100%. Fit oversize untuk gaya streetwear.',
        'XL', 'Baik', '-',
        2, 'thrasher_xl.jpg', 'locked', '6289876543210'
    ),
    (
        rizky_id,
        'Jam Tangan Casio MQ24 Vintage',
        175000, 0,
        'Aksesoris', 'Depok',
        'Casio MQ24 classic vintage, jam tangan yang tidak lekang oleh waktu. Baterai baru baru diganti bulan ini. Tali original masih bagus, tidak ada goresan di kaca.',
        '-', 'Sangat Baik', '-',
        1, 'casio_vintage.jpg', 'available', '6285678901234'
    ),
    (
        rizky_id,
        'Blazer Thrift Korea Navy Slim Fit',
        130000, 20,
        'Jaket', 'Bogor',
        'Blazer import thrift dari Korea. Warna navy gelap, potongan slim fit yang rapi. Perfect untuk smart casual atau acara formal semi-formal. Bahan polyester premium tidak panas.',
        'M', 'Sangat Baik', '-',
        3, 'blazer_korea.jpg', 'available', '6285678901234'
    ),
    (
        rizky_id,
        'Kalung Perak 925 Vintage Charm',
        65000, 0,
        'Aksesoris', 'Jakarta',
        'Kalung perak 925 dengan charm vintage. Panjang 45cm, ada pengait lobster. Sudah dicuci bersih. Bisa untuk pria atau wanita. Cocok dipadu dengan outfit casual maupun formal.',
        '-', 'Baik', 'Ada sedikit oksidasi di bagian charm, bisa dibersihkan dengan silver polish',
        2, 'kalung_perak.jpg', 'available', '6285678901234'
    ),
    (
        budi_id,
        'Sneakers Putih Pria Clean Look',
        155000, 0,
        'Sepatu', 'Depok',
        'Sneakers putih pria kondisi bersih. Sudah dicuci dan direpair bagian sol yang mulai lepas. Sekarang kondisi bagus dan siap pakai. Gaya minimalis cocok untuk outfit apapun.',
        '41 EU', 'Baik', 'Sol pernah sedikit lepas di ujung depan, sudah di-repair dengan lem sepatu kuat',
        1, 'sneakers_putih.jpg', 'available', '6281234567890'
    ),
]

for p in products:
    conn.execute('''
        INSERT INTO products
        (user_id, title, price, discount, category, location, description, size, condition, defect, stock, image, status, wa_number)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', p)
conn.commit()

# Ambil semua product id
prod_ids = [r['id'] for r in conn.execute('SELECT id FROM products ORDER BY id').fetchall()]

# ─── ORDERS ──────────────────────────────────────────────
conn.execute('''
    INSERT INTO orders (product_id, buyer_id, payment_method, pickup_method, schedule, status)
    VALUES (?, ?, 'Transfer', 'meetup', '2026-04-22 14:00', 'Dibayar')
''', (prod_ids[7], andi_id))  # Kaos Thrasher locked

conn.execute('''
    INSERT INTO orders (product_id, buyer_id, payment_method, pickup_method, schedule, status)
    VALUES (?, ?, 'COD', 'meetup', '2026-04-20 10:00', 'Selesai')
''', (prod_ids[2], andi_id))  # Kemeja Flannel selesai

conn.execute('''
    INSERT INTO orders (product_id, buyer_id, payment_method, pickup_method, schedule, status)
    VALUES (?, ?, 'E-Wallet', 'pickup', '2026-04-23 16:00', 'Menunggu Pembayaran')
''', (prod_ids[4], andi_id))  # Dress Floral menunggu bayar

conn.commit()

# ─── MESSAGES ────────────────────────────────────────────
messages = [
    (prod_ids[0], 'andi_buyer',   'Halo kak, jaket denim masih available?'),
    (prod_ids[0], 'budi_thrift',  'Masih available kak! Kondisi bagus, mau liat foto detail?'),
    (prod_ids[0], 'andi_buyer',   'Boleh kak, kirim ke sini aja. Btw bisa nego gak?'),
    (prod_ids[0], 'budi_thrift',  'Bisa nego dikit kak, harga segitu udah pas sih. Tapi kalo ambil 2 item bisa dapet diskon 😊'),
    (prod_ids[0], 'andi_buyer',   'Oke deh kak, deal! Bisa meetup dimana?'),
    (prod_ids[0], 'budi_thrift',  'Bisa di Margonda kak, atau di kampus UG juga bisa'),

    (prod_ids[4], 'andi_buyer',   'Kak dress floralnya ukuran S muat untuk badan 52kg tinggi 158cm?'),
    (prod_ids[4], 'sari_vintage', 'Harusnya muat banget kak, bahannya ada stretch dikit. Pinggang bisa diatur lewat tali 😊'),
    (prod_ids[4], 'andi_buyer',   'Oke siap, saya checkout sekarang ya kak!'),

    (prod_ids[8], 'andi_buyer',   'Casio vintage masih ada kak? Baterainya masih bagus?'),
    (prod_ids[8], 'rizky_seller', 'Masih ada kak! Baterai baru diganti minggu lalu, dijamin masih lama'),
]

for m in messages:
    conn.execute('INSERT INTO messages (product_id, username, message) VALUES (?, ?, ?)', m)
conn.commit()

# ─── REVIEWS ─────────────────────────────────────────────
conn.execute('''
    INSERT INTO reviews (reviewer_id, seller_id, product_id, rating, comment)
    VALUES (?, ?, ?, 5, 'Seller ramah dan fast response! Barang sesuai deskripsi, kondisi bagus. Recommended banget!')
''', (andi_id, budi_id, prod_ids[2]))

conn.execute('''
    INSERT INTO reviews (reviewer_id, seller_id, product_id, rating, comment)
    VALUES (?, ?, ?, 4, 'Barang sesuai foto, cuma agak telat balesnya. Overall oke lah!')
''', (andi_id, sari_id, prod_ids[4]))

conn.execute('''
    INSERT INTO reviews (reviewer_id, seller_id, product_id, rating, comment)
    VALUES (?, ?, ?, 5, 'Top seller! Barang rapih dikemas, meetup on time, honest seller 👍')
''', (andi_id, rizky_id, prod_ids[8]))

conn.commit()
conn.close()

print('✅ Seed berhasil!')
print()
print('Akun yang tersedia:')
print('  budi_thrift  / password123  (seller)')
print('  sari_vintage / password123  (seller)')
print('  rizky_seller / password123  (seller)')
print('  andi_buyer   / password123  (buyer)')
print()
print('Foto yang perlu kamu siapkan di static/uploads/:')
photos = [
    'jaket_denim.jpg', 'converse_chuck.jpg', 'flannel_uniqlo.jpg',
    'ransel_rei.jpg', 'dress_floral.jpg', 'mom_jeans.jpg',
    'bucket_hat.jpg', 'thrasher_xl.jpg', 'casio_vintage.jpg',
    'blazer_korea.jpg', 'kalung_perak.jpg', 'sneakers_putih.jpg'
]
for p in photos:
    print(f'  - {p}')