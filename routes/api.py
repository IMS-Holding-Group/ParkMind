import secrets
import time
from functools import wraps

from flask import Blueprint, jsonify, request, session, current_app
from werkzeug.security import check_password_hash

import models

api_bp = Blueprint('api', __name__, url_prefix='/api')

_failed_login_attempts = {}
_MAX_ATTEMPTS = 5
_LOCKOUT_SECONDS = 300


def admin_required(view_function):
    @wraps(view_function)
    def wrapped(*args, **kwargs):
        if session.get('role') != 'admin':
            return jsonify({'error': 'هذا المسار محمي ويتطلب صلاحية مسؤول'}), 401
        return view_function(*args, **kwargs)
    return wrapped


def _client_ip():
    return request.headers.get('X-Forwarded-For', request.remote_addr)


def _is_locked_out(ip_address):
    record = _failed_login_attempts.get(ip_address)
    if not record:
        return False
    attempts, last_attempt = record
    if attempts >= _MAX_ATTEMPTS and (time.time() - last_attempt) < _LOCKOUT_SECONDS:
        return True
    return False


def _register_failed_attempt(ip_address):
    attempts, _ = _failed_login_attempts.get(ip_address, (0, 0))
    _failed_login_attempts[ip_address] = (attempts + 1, time.time())


def _clear_failed_attempts(ip_address):
    _failed_login_attempts.pop(ip_address, None)


@api_bp.route('/parking-lots', methods=['GET'])
def list_parking_lots():
    return jsonify(models.get_all_parking_lots())


@api_bp.route('/parking-lots/<int:lot_id>/spaces', methods=['GET'])
def list_lot_spaces(lot_id):
    lot = models.get_lot_by_id(lot_id)
    if lot is None:
        return jsonify({'error': 'الموقف المطلوب غير موجود'}), 404
    return jsonify(models.get_spaces_for_lot(lot_id))


@api_bp.route('/nearest-parking', methods=['GET'])
def nearest_parking():
    try:
        lat = float(request.args.get('lat'))
        lng = float(request.args.get('lng'))
    except (TypeError, ValueError):
        return jsonify({'error': 'إحداثيات الموقع غير صحيحة'}), 400

    if not (-90 <= lat <= 90 and -180 <= lng <= 180):
        return jsonify({'error': 'إحداثيات الموقع خارج النطاق المسموح'}), 400

    result = models.find_nearest_available_lot(lat, lng)
    if result is None:
        return jsonify({'error': 'لا يوجد حالياً أي مكان شاغر في أي موقف'}), 404
    return jsonify(result)


@api_bp.route('/login', methods=['POST'])
def login():
    ip_address = _client_ip()
    if _is_locked_out(ip_address):
        return jsonify({'error': 'تم إيقاف محاولات الدخول مؤقتاً بسبب تكرار المحاولات الفاشلة'}), 429

    payload = request.get_json(silent=True) or {}
    username = payload.get('username', '')
    password = payload.get('password', '')
    csrf_token = payload.get('csrf_token', '')

    if not csrf_token or csrf_token != session.get('csrf_token'):
        return jsonify({'error': 'جلسة النموذج غير صالحة، يرجى إعادة تحميل الصفحة'}), 400

    if not username or not password:
        return jsonify({'error': 'يرجى إدخال اسم المستخدم وكلمة المرور'}), 400

    user = models.get_user_by_username(username)
    if user is None or not check_password_hash(user['password_hash'], password):
        _register_failed_attempt(ip_address)
        return jsonify({'error': 'اسم المستخدم أو كلمة المرور غير صحيحة'}), 401

    _clear_failed_attempts(ip_address)
    session.clear()
    session.permanent = True
    session['username'] = user['username']
    session['role'] = user['role']
    session['csrf_token'] = secrets.token_hex(16)
    return jsonify({'success': True, 'username': user['username']})


@api_bp.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'success': True})


@api_bp.route('/parking-spaces/<int:space_id>/status', methods=['POST'])
def update_status(space_id):
    payload = request.get_json(silent=True) or {}
    new_status = payload.get('status')

    if new_status not in ('vacant', 'occupied'):
        return jsonify({'error': 'قيمة الحالة يجب أن تكون vacant أو occupied'}), 400

    cv_token = request.headers.get('X-CV-Token')
    is_admin_session = session.get('role') == 'admin'
    is_cv_module = cv_token is not None and cv_token == current_app.config['CV_INTERNAL_TOKEN']

    if not (is_admin_session or is_cv_module):
        return jsonify({'error': 'غير مصرح لك بتحديث حالة هذا المكان'}), 401

    changed_by = session.get('username') if is_admin_session else 'cv_module'
    updated_space = models.update_space_status(space_id, new_status, changed_by)
    if updated_space is None:
        return jsonify({'error': 'مكان الوقوف المطلوب غير موجود'}), 404

    return jsonify({'success': True, 'space': updated_space})


@api_bp.route('/admin/stats', methods=['GET'])
@admin_required
def admin_stats():
    return jsonify(models.get_admin_stats())


@api_bp.route('/admin/logs', methods=['GET'])
@admin_required
def admin_logs():
    return jsonify(models.get_status_logs())


@api_bp.route('/admin/occupancy-history', methods=['GET'])
@admin_required
def admin_occupancy_history():
    return jsonify(models.get_occupancy_history())
