import sqlite3
from datetime import datetime

from flask import g, current_app
from werkzeug.security import generate_password_hash


def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(current_app.config['DATABASE_PATH'])
        g.db.row_factory = sqlite3.Row
        g.db.execute('PRAGMA foreign_keys = ON')
    return g.db


def close_db(exception=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db(app):
    with app.app_context():
        db = get_db()
        db.executescript('''
            CREATE TABLE IF NOT EXISTS parking_lot (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                address TEXT,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS parking_space (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lot_id INTEGER NOT NULL,
                space_number TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'vacant',
                updated_at DATETIME NOT NULL,
                FOREIGN KEY (lot_id) REFERENCES parking_lot (id)
            );

            CREATE TABLE IF NOT EXISTS user (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'driver'
            );

            CREATE TABLE IF NOT EXISTS status_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                space_id INTEGER NOT NULL,
                old_status TEXT NOT NULL,
                new_status TEXT NOT NULL,
                changed_by TEXT NOT NULL,
                changed_at DATETIME NOT NULL,
                FOREIGN KEY (space_id) REFERENCES parking_space (id)
            );
        ''')
        db.commit()
        _seed_data(db)


def _seed_data(db):
    lot_count = db.execute('SELECT COUNT(*) AS total FROM parking_lot').fetchone()['total']
    if lot_count > 0:
        return

    now = datetime.now().isoformat(sep=' ', timespec='seconds')

    lots = [
        ('موقف المكتبة المركزية', 'شارع الملك عبدالعزيز، بريدة', 26.3260, 43.9750),
        ('موقف مبنى الإدارة', 'طريق الملك فهد، بريدة', 26.3300, 43.9800),
    ]
    cursor = db.cursor()
    lot_ids = []
    for name, address, lat, lng in lots:
        cursor.execute(
            'INSERT INTO parking_lot (name, address, latitude, longitude) VALUES (?, ?, ?, ?)',
            (name, address, lat, lng)
        )
        lot_ids.append(cursor.lastrowid)

    lot_one_spaces = ['A1', 'A2', 'A3', 'A4', 'A5', 'A6', 'A7', 'A8']
    lot_two_spaces = ['B1', 'B2', 'B3', 'B4', 'B5', 'B6']

    for space_number in lot_one_spaces:
        cursor.execute(
            'INSERT INTO parking_space (lot_id, space_number, status, updated_at) VALUES (?, ?, ?, ?)',
            (lot_ids[0], space_number, 'vacant', now)
        )
    for space_number in lot_two_spaces:
        cursor.execute(
            'INSERT INTO parking_space (lot_id, space_number, status, updated_at) VALUES (?, ?, ?, ?)',
            (lot_ids[1], space_number, 'vacant', now)
        )

    cursor.execute(
        'INSERT INTO user (username, password_hash, role) VALUES (?, ?, ?)',
        ('admin', generate_password_hash(''), 'admin')
    )

    db.commit()
