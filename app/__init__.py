from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from dotenv import load_dotenv
import os

# Carregar as variáveis de ambiente do arquivo .env
load_dotenv()

# Instanciando as extensões
db = SQLAlchemy()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)

    # Configurações do app
    app.config.from_object('app.config.Config')

    # Inicializando o banco de dados e o LoginManager
    db.init_app(app)
    login_manager.init_app(app)

    # Configurando a página de login
    login_manager.login_view = 'main.login'  # Define qual a rota que os usuários não autenticados serão redirecionados

    with app.app_context():
        # Registrando o blueprint
        from .routes import main as main_blueprint
        app.register_blueprint(main_blueprint)

        # Criando as tabelas no banco de dados, caso ainda não existam
        db.create_all()

    return app

# Função para carregar o usuário
@login_manager.user_loader
def load_user(user_id):
    from .models import User  # Certifique-se de que o modelo User está correto
    return User.query.get(int(user_id))
