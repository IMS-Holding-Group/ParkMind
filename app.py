from flask import Flask
from werkzeug.serving import WSGIRequestHandler

from config import Config
from database import close_db, init_db
from routes.api import api_bp
from routes.admin_routes import pages_bp

WSGIRequestHandler.server_version = 'Server'
WSGIRequestHandler.sys_version = ''


def create_app():
    Config.validate()
    app = Flask(__name__)
    app.config.from_object(Config)

    app.teardown_appcontext(close_db)
    app.register_blueprint(pages_bp)
    app.register_blueprint(api_bp)

    @app.after_request
    def set_security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Content-Security-Policy'] = "default-src 'self'"
        response.headers.pop('Server', None)
        return response

    @app.errorhandler(404)
    def not_found(error):
        return {'error': 'المسار المطلوب غير موجود'}, 404

    @app.errorhandler(500)
    def server_error(error):
        app.logger.exception('حدث خطأ غير متوقع في الخادم')
        return {'error': 'حدث خطأ غير متوقع، يرجى المحاولة لاحقاً'}, 500

    init_db(app)
    return app


app = create_app()

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=Config.DEBUG)
