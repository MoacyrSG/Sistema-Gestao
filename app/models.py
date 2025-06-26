from app import db
from sqlalchemy import ARRAY, ForeignKey
from sqlalchemy.orm import relationship
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from datetime import datetime, timedelta
import pytz
    

class User(db.Model, UserMixin):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(512), nullable=False)
    roles = db.Column(db.String(50), nullable=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'
    

class Cliente(db.Model):
    __tablename__ = 'clientes'
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    cpf = db.Column(db.String(11), unique=True, nullable=False)
    rg = db.Column(db.String(9), nullable=False)
    telefone = db.Column(db.String(15), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    data_nasc = db.Column(db.Date, nullable=True)
    logradouro = db.Column(db.String(150), nullable=False)
    numero = db.Column(db.String(10), nullable=False)
    complemento = db.Column(db.String(50))
    cep = db.Column(db.String(8), nullable=False)
    municipio = db.Column(db.String(50), nullable=False)
    estado = db.Column(db.String(2), nullable=False)
    pais = db.Column(db.String(20), nullable=False)
    observacao = db.Column(db.String(300), nullable=True)

class Hospedagem(db.Model):
    __tablename__ = 'hospedagens'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    tipo = db.Column(db.String(50), nullable=False)  # Ex: hotel, resort, pousada
    cnpj = db.Column(db.String(20), nullable=False)
    endereco = db.Column(db.String(150), nullable=False)
    telefone = db.Column(db.String(15), nullable=False)
    descricao = db.Column(db.Text)  # Uma descrição detalhada da hospedagem
    

class Grupo(db.Model):
    __tablename__ = 'grupos'    
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    data_ida = db.Column(db.Date, nullable=False)
    data_volta = db.Column(db.Date, nullable=False)
    horario_chegada = db.Column(db.Time, nullable=True)
    horario_partida = db.Column(db.Time, nullable=True)
    hospedagem_id = db.Column(db.Integer, db.ForeignKey('hospedagens.id'), nullable=False)
    nome_hospedagem = db.Column(db.String(100), nullable=False)
    hospedagem = db.relationship('Hospedagem', backref='grupos')
    tipos_apartamentos = db.relationship('GrupoApartamento', back_populates='grupo', cascade="all, delete-orphan")

class GrupoApartamento(db.Model):
    __tablename__ = 'grupo_apartamentos'

    id = db.Column(db.Integer, primary_key=True)
    grupo_id = db.Column(db.Integer, db.ForeignKey('grupos.id'), nullable=False)
    id_grupo = db.Column(db.String(10), nullable=True)  # Adicionando o id_grupo
    tipo_apart = db.Column(db.String(30), nullable=False)
    qtd_apart = db.Column(db.Integer, nullable=False)
    preco = db.Column(db.Float, nullable=False, default=0.0)
    grupo = db.relationship('Grupo', back_populates='tipos_apartamentos')
    
    
class PrecoTabelado(db.Model):
    __tablename__ = 'preco_tabelado'    
    
    id = db.Column(db.Integer, primary_key=True)
    single = db.Column(db.Float, nullable=False)
    duplo = db.Column(db.Float, nullable=False)
    triplo = db.Column(db.Float, nullable=False)
    quadruplo = db.Column(db.Float, nullable=False)
    chd = db.Column(db.Float, nullable=False)
    data = db.Column(db.Date, nullable=False)
    hospedagem_id = db.Column(db.Integer, ForeignKey('hospedagens.id'), nullable=False)
    hospedagem = relationship('Hospedagem', backref='preco_tabelado')
    
    
class Reserva(db.Model):
    __tablename__ = 'reservas'
    
    id = db.Column(db.Integer, primary_key=True)
    id_reserva = db.Column(db.String(10), nullable=False)
    tipo_reserva = db.Column(db.String(20), nullable=False)  # 'Grupo' ou 'Pacote'
    
    cliente_id = db.Column(db.Integer, db.ForeignKey('clientes.id', ondelete="SET NULL"), nullable=False)
    nome_cliente = db.Column(db.String(100), nullable=True)
    cliente = db.relationship('Cliente', backref='reservas')
    
    opcoes_pacote = db.Column(ARRAY(db.String))
    
    num_adultos = db.Column(db.Integer, nullable=False, default=1)
    num_criancas = db.Column(db.Integer, nullable=False, default=0)
    num_criancas_free = db.Column(db.Integer, nullable=False, default=0)
    confirmada_por = db.Column(db.String(100), nullable=True)

    status = db.Column(db.String(20), nullable=True)  # Confirmada, Pendente, Não Confirmada
    pensao = db.Column(db.String(20), nullable=True)  # Inteira, Meia
    garante_no_show = db.Column(db.Boolean, nullable=False, default=False)
    evento = db.Column(db.Boolean, nullable=False, default=False)
    descricao = db.Column(db.Text, nullable=True)

    # Relacionamento com Hóspedes
    hospedes = db.relationship('Hospede', back_populates='reserva', cascade="all, delete-orphan")
    
    # Relacionamento com Grupo (opcional para reserva de grupo)
    grupo_id = db.Column(db.Integer, db.ForeignKey('grupos.id', ondelete="SET NULL"), nullable=True)
    nome_grupo = db.Column(db.String(100), nullable=True)
    nome_hospedagem_grupo = db.Column(db.String(100), nullable=True)
    hospedagem_id_grupo = db.Column(db.Integer, nullable=True)
    tipo_apart_grupo = db.Column(db.String(100), nullable=True)
    grupo = db.relationship('Grupo', backref='reservas')
    
    # Referente ao pacote aereo
    companhia = db.Column(db.String(100), nullable=True)
    numero_voo = db.Column(db.String(20), nullable=True)
    data_ida = db.Column(db.Date, nullable=True)
    data_volta = db.Column(db.Date, nullable=True)
    horario_ida = db.Column(db.Time, nullable=True)
    horario_chegada = db.Column(db.Time, nullable=True)
    origem = db.Column(db.String(100), nullable=True)
    destino = db.Column(db.String(100), nullable=True)
    escala = db.Column(db.String(100), nullable=True)
    inclui_bagagem = db.Column(db.Boolean, nullable=True)
    
    # Referente ao pacote hospedagem
    hospedagem_id = db.Column(db.Integer, db.ForeignKey('hospedagens.id', ondelete="SET NULL"), nullable=True)
    nome_hospedagem = db.Column(db.String(100), nullable=True)
    tipo_apart = db.Column(db.String(100), nullable=True)
    hospedagem = db.relationship('Hospedagem', backref='reservas')
    
    # Referente ao pacote transporte
    transporte_info = db.Column(db.Text, nullable=True)
    
    # Referente ao pacote seguro
    seguro_info = db.Column(db.Text, nullable=True)
    
    # Referente ao pacote servico
    servico_info = db.Column(db.Text, nullable=True)
    
    diaria = db.Column(db.Float, nullable=True)
    diaria_crianca = db.Column(db.Float, nullable=True)
    diaria_pessoa = db.Column(db.Float, nullable=True)
    valor_total = db.Column(db.Float, nullable=True)
    depositos_confirmados = db.Column(db.Float, nullable=True)
    lucro = db.Column(db.Float, nullable=True)
    
    data_reserva = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(pytz.timezone("America/Sao_Paulo")))
    
    
    
    
    
    
    
class Hospede(db.Model):
    __tablename__ = 'hospedes'
    
    id = db.Column(db.Integer, primary_key=True)
    reserva_id = db.Column(db.Integer, db.ForeignKey('reservas.id'), nullable=False)
    nome = db.Column(db.String(100), nullable=False)

    reserva = db.relationship('Reserva', back_populates='hospedes')
    

class RelatorioReserva(db.Model):
    __tablename__ = 'relatorio_reserva'

    id = db.Column(db.Integer, primary_key=True)  # Identificador único
    mes = db.Column(db.Integer, nullable=False)  # Mês do relatório
    ano = db.Column(db.Integer, nullable=False)  # Ano do relatório
    total_mes = db.Column(db.Numeric(10, 2), default=0, nullable=False)  # Total do mês
    total_ano = db.Column(db.Numeric(10, 2), default=0, nullable=False)  # Total acumulado no ano
    reservas_mes = db.Column(db.Integer, default=0)  # Número de reservas no mês
    reservas_ano = db.Column(db.Integer, default=0)  # Número de reservas acumulado no ano
    total_adultos = db.Column(db.Integer, default=0)  # Total de adultos
    total_criancas = db.Column(db.Integer, default=0)  # Total de crianças
    data_atualizacao = db.Column(db.DateTime, default=datetime.utcnow)  # Data de atualização
    notas = db.Column(db.String(255))  # Notas ou observações
    
    
