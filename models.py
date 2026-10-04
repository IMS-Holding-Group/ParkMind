import math
from datetime import datetime

from database import get_db


def get_all_parking_lots():
    db = get_db()
    rows = db.execute('SELECT id, name, address, latitude, longitude FROM parking_lot').fetchall()
    return [dict(row) for row in rows]


def get_lot_by_id(lot_id):
    db = get_db()
    row = db.execute(
        'SELECT id, name, address, latitude, longitude FROM parking_lot WHERE id = ?',
        (lot_id,)
    ).fetchone()
    return dict(row) if row else None


def get_spaces_for_lot(lot_id):
    db = get_db()
    rows = db.execute(
        'SELECT id, lot_id, space_number, status, updated_at FROM parking_space WHERE lot_id = ? ORDER BY space_number',
        (lot_id,)
    ).fetchall()
    return [dict(row) for row in rows]


def get_space_by_id(space_id):
    db = get_db()
    row = db.execute(
        'SELECT id, lot_id, space_number, status, updated_at FROM parking_space WHERE id = ?',
        (space_id,)
    ).fetchone()
    return dict(row) if row else None


def update_space_status(space_id, new_status, changed_by):
    db = get_db()
    space = get_space_by_id(space_id)
    if space is None:
        return None
    old_status = space['status']
    now = datetime.now().isoformat(sep=' ', timespec='seconds')
    db.execute(
        'UPDATE parking_space SET status = ?, updated_at = ? WHERE id = ?',
        (new_status, now, space_id)
    )
    db.execute(
        'INSERT INTO status_log (space_id, old_status, new_status, changed_by, changed_at) VALUES (?, ?, ?, ?, ?)',
        (space_id, old_status, new_status, changed_by, now)
    )
    db.commit()
    return get_space_by_id(space_id)


def get_admin_stats():
    db = get_db()
    total = db.execute('SELECT COUNT(*) AS total FROM parking_space').fetchone()['total']
    occupied = db.execute(
        "SELECT COUNT(*) AS total FROM parking_space WHERE status = 'occupied'"
    ).fetchone()['total']
    vacant = total - occupied
    occupancy_rate = round((occupied / total) * 100, 1) if total > 0 else 0
    return {
        'total_spaces': total,
        'occupied_spaces': occupied,
        'vacant_spaces': vacant,
        'occupancy_rate': occupancy_rate
    }


def get_status_logs(limit=50):
    db = get_db()
    rows = db.execute(
        '''
        SELECT status_log.id, status_log.old_status, status_log.new_status,
               status_log.changed_by, status_log.changed_at, parking_space.space_number
        FROM status_log
        JOIN parking_space ON parking_space.id = status_log.space_id
        ORDER BY status_log.changed_at DESC
        LIMIT ?
        ''',
        (limit,)
    ).fetchall()
    return [dict(row) for row in rows]


def get_occupancy_history():
    db = get_db()
    rows = db.execute(
        '''
        SELECT strftime('%Y-%m-%d %H:00', changed_at) AS hour_bucket,
               SUM(CASE WHEN new_status = 'occupied' THEN 1 ELSE -1 END) AS delta
        FROM status_log
        GROUP BY hour_bucket
        ORDER BY hour_bucket ASC
        LIMIT 24
        '''
    ).fetchall()
    return [dict(row) for row in rows]


def get_user_by_username(username):
    db = get_db()
    row = db.execute(
        'SELECT id, username, password_hash, role FROM user WHERE username = ?',
        (username,)
    ).fetchone()
    return dict(row) if row else None


def _haversine_distance_km(lat1, lng1, lat2, lng2):
    earth_radius_km = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lng2 - lng1)
    a = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return earth_radius_km * c


def find_nearest_available_lot(driver_lat, driver_lng):
    db = get_db()
    lots = get_all_parking_lots()
    candidates = []
    for lot in lots:
        vacant_count = db.execute(
            "SELECT COUNT(*) AS total FROM parking_space WHERE lot_id = ? AND status = 'vacant'",
            (lot['id'],)
        ).fetchone()['total']
        if vacant_count > 0:
            distance = _haversine_distance_km(driver_lat, driver_lng, lot['latitude'], lot['longitude'])
            candidates.append({
                'lot_id': lot['id'],
                'name': lot['name'],
                'address': lot['address'],
                'latitude': lot['latitude'],
                'longitude': lot['longitude'],
                'vacant_spaces': vacant_count,
                'distance_km': round(distance, 2)
            })
    candidates.sort(key=lambda item: item['distance_km'])
    return candidates[0] if candidates else None
