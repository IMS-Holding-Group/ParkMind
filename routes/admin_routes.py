import secrets

from flask import Blueprint, render_template, session, redirect, url_for

pages_bp = Blueprint('pages', __name__)


@pages_bp.route('/')
def driver_view():
    return render_template('index.html')


@pages_bp.route('/login')
def login_page():
    if session.get('role') == 'admin':
        return redirect(url_for('pages.admin_dashboard'))
    session['csrf_token'] = secrets.token_hex(16)
    return render_template('login.html', csrf_token=session['csrf_token'])


@pages_bp.route('/admin')
def admin_dashboard():
    if session.get('role') != 'admin':
        return redirect(url_for('pages.login_page'))
    return render_template('admin.html', username=session.get('username'))
