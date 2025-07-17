import os

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'sua_chave_secreta')
    SQLALCHEMY_DATABASE_URI = "postgresql+pg8000://camila:4512@localhost:5432/coutinho_excursoes"
    SQLALCHEMY_TRACK_MODIFICATIONS = False