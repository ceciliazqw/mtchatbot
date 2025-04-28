import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your_secret_key' # 強烈建議生產環境使用環境變數
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///insurance.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # 建議加入 DEBUG 設定 (例如，從環境變數讀取，預設為 True 供開發)
    DEBUG = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true' 