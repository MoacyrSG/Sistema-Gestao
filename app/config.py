import os

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'sua_chave_secreta')
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
