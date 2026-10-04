import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY')
    DATABASE_PATH = os.environ.get('DATABASE_PATH', 'parkmind.db')
    CV_INTERNAL_TOKEN = os.environ.get('CV_INTERNAL_TOKEN')
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'False') == 'True'
    PERMANENT_SESSION_LIFETIME = int(os.environ.get('SESSION_LIFETIME_SECONDS', '1800'))
    DEBUG = os.environ.get('FLASK_DEBUG', 'False') == 'True'

    @staticmethod
    def validate():
        if not Config.SECRET_KEY:
            raise RuntimeError('يجب تعيين SECRET_KEY داخل ملف .env قبل تشغيل التطبيق')
        if not Config.CV_INTERNAL_TOKEN:
            raise RuntimeError('يجب تعيين CV_INTERNAL_TOKEN داخل ملف .env قبل تشغيل التطبيق')
