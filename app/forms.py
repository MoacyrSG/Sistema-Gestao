from flask_wtf import FlaskForm
from wtforms import StringField, DecimalField, SubmitField, SelectField, TextAreaField, FloatField, DateField, PasswordField, IntegerField, RadioField, BooleanField, TimeField, SelectMultipleField, widgets, FieldList, FormField
from wtforms.validators import DataRequired, Length, Email, EqualTo, NumberRange, Optional
from wtforms_sqlalchemy.fields import QuerySelectField
from app.models import Grupo
import re

class LoginForm(FlaskForm):
    username = StringField('Usuário', validators=[DataRequired()])
    password = PasswordField('Senha', validators=[DataRequired()])
    submit = SubmitField('Login')
    

class RegistrationForm(FlaskForm):
    username = StringField('Nome de Usuário', validators=[DataRequired(), Length(min=3, max=100)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField('Senha', validators=[DataRequired()])
    confirm_password = PasswordField('Confirmar Senha', validators=[DataRequired(), EqualTo('password', message='As senhas devem ser iguais')])
    submit = SubmitField('Cadastrar')

def only_digits(value):
    return re.sub(r'\D', '', value or '')

class ClienteForm(FlaskForm):
    nome = StringField('Nome', validators=[Length(max=100), Optional()])
    cpf = StringField('CPF', filters=[only_digits], validators=[Length(max=11), Optional()])
    rg = StringField('RG', filters=[only_digits], validators=[Length(max=9), Optional()])
    telefone = StringField('Telefone', validators=[Length(max=15), Optional()])
    email = StringField('Email', validators=[Length(max=100), Optional()])
    data_nasc = DateField('Data de Nascimento', format='%Y-%m-%d', validators=[Optional()])
    logradouro = StringField('Logradouro', validators=[Length(max=150), Optional()])
    bairro = StringField('Bairro', validators=[Length(max=150), Optional()])
    numero = StringField('Número', validators=[Length(max=10), Optional()])
    complemento = StringField('Complemento', validators=[Length(max=50), Optional()])
    cep = StringField('CEP', filters=[only_digits], validators=[Length(max=8), Optional()])
    municipio = StringField('Município', validators=[Length(max=50),Optional()])
    estado = StringField('Estado', validators=[Length(max=2), Optional()])
    pais = StringField('País', validators=[Length(max=50), Optional()])
    observacao = StringField('Observação', validators=[Length(max=300), Optional()])
    submit = SubmitField('Cadastrar')
    
class HospedagemForm(FlaskForm):
    nome = StringField('Nome', validators=[DataRequired(), Length(max=100)])
    tipo = SelectField('Tipo', choices=[('hotel', 'Hotel'), ('resort', 'Resort'), ('pousada', 'Pousada')], validators=[DataRequired()])
    cnpj = StringField('CNPJ', validators=[Optional(), Length(max=50)])
    endereco = StringField('Endereço', validators=[Optional(), Length(max=150)])
    telefone = StringField('Telefone', validators=[Optional(), Length(max=15)])
    descricao = TextAreaField('Descrição', validators=[Optional()])
    submit = SubmitField('Cadastrar')
    
class TipoApartamentoForm(FlaskForm):
    tipo_apart = StringField('Tipo do Apartamento')
    qtd_apart = IntegerField('Quantidade de Apartamentos', validators=[NumberRange(min=1)])
    preco = StringField('Preço', validators=[Optional()])

class GrupoForm(FlaskForm):
    nome = StringField('Nome do Grupo', validators=[DataRequired()])
    data_ida = DateField('Data de Ida', format='%Y-%m-%d', validators=[DataRequired()])
    data_volta = DateField('Data de Volta', format='%Y-%m-%d', validators=[DataRequired()])
    horario_chegada = TimeField('Horário de Chegada', format='%H:%M', validators=[Optional()])
    horario_partida = TimeField('Horário de Partida', format='%H:%M', validators=[Optional()])
    hospedagem_id = SelectField('Hospedagem', coerce=int, validators=[DataRequired()])
    tipos_apartamentos = FieldList(FormField(TipoApartamentoForm), min_entries=1)
    submit = SubmitField('Cadastrar Grupo')

class PrecoTabeladoForm(FlaskForm):
    single = StringField('Single', validators=[Optional()])
    duplo = StringField('Duplo', validators=[Optional()])
    triplo = StringField('Triplo', validators=[Optional()])
    quadruplo = StringField('Quádruplo', validators=[Optional()])
    chd = StringField('CHD', validators=[Optional()])
    data_inicio = DateField('Data Início', format='%Y-%m-%d', validators=[Optional()])
    data_fim = DateField('Data Fim', format='%Y-%m-%d', validators=[Optional()])
    hospedagem = StringField('Endereço', validators=[DataRequired(), Length(max=150)])
    submit = SubmitField('Cadastrar Preço')

    
class HospedeForm(FlaskForm):
    nome = StringField('Nome', validators=[DataRequired()])
        
    
class ReservaForm(FlaskForm):
    tipo_reserva = RadioField(
        'Tipo de Reserva',
        choices=[('Grupo', 'Grupo'), ('Pacote', 'Pacote')],
        validators=[DataRequired()]
    )
    
    opcoes_pacote = SelectMultipleField(
        'Opções do Pacote',
        choices=[
            ('aereo', 'Aéreo'),
            ('hospedagem', 'Hospedagem'),
            ('transporte', 'Transporte'),
            ('seguro', 'Seguro'),
            ('servico', 'Serviço')
        ],
        validators=[Optional()]
    )

    # Informações gerais
    cliente_id = SelectField('Cliente', coerce=int, validators=[DataRequired()])
    num_adultos = IntegerField('Número de Adultos', validators=[DataRequired(), NumberRange(min=1)], default=1)
    num_criancas = IntegerField('Número de Crianças', validators=[NumberRange(min=0)], default=0)
    num_criancas_free = IntegerField('Número de Crianças Free', validators=[NumberRange(min=0)], default=0)
    confirmada_por = StringField('Confirmada por', validators=[Optional()])

    status = SelectField(
        'Status da Reserva',
        choices=[('confirmada', 'Confirmada'), ('pendente', 'Pendente'), ('nao_confirmada', 'Não Confirmada')],
        validators=[Optional()]
    )
    pensao = SelectField(
        'Pensão',
        choices=[('inteira', 'Inteira'), ('meia', 'Meia'), ('café da manhã', 'Café da Manhã')],
        validators=[Optional()]
    )
    garante_no_show = SelectField(
        'Garante No-Show',
        choices=[('sim', 'Sim'), ('nao', 'Não')],
        validators=[Optional()]
    )
    
    evento = SelectField(
        'Evento',
        choices=[('sim', 'Sim'), ('nao', 'Não')],
        validators=[Optional()]
    )
    
    id_reserva = StringField('Id da Reserva', validators=[DataRequired()])
    
    descricao = TextAreaField('Informações Adicionais', validators=[Optional()])

    # Campo para múltiplos hóspedes
    hospedes = FieldList(FormField(HospedeForm), min_entries=1)
    
    grupo_id = SelectField('Grupo', choices=[], coerce=int, validators=[Optional()])
    tipo_apart_grupo = StringField("Tipo de Apartamento", validators=[Optional()])
    
    # Campos adicionais para Pacote (exibidos quando o tipo for 'Pacote')
    companhia = StringField('Companhia Aérea', validators=[Optional()])
    numero_voo = StringField('Número do Voo', validators=[Optional()])
    data_ida = DateField('Data de Ida', format='%Y-%m-%d', validators=[Optional()])
    data_volta = DateField('Data de Volta', format='%Y-%m-%d', validators=[Optional()])
    horario_ida = TimeField('Horário de Ida', format='%H:%M', validators=[Optional()])
    horario_chegada = TimeField('Horário de Chegada', format='%H:%M', validators=[Optional()])
    origem = StringField('Origem', validators=[Optional()])
    destino = StringField('Destino', validators=[Optional()])
    escala = StringField('Escala', validators=[Optional()])
    inclui_bagagem = BooleanField('Inclui Bagagem', default=False)
    
    hospedagem_id = SelectField('Hospedagem', coerce=int, choices=[], validators=[Optional()])
    tipo_apart = StringField('Tipo de Apartamento', validators=[Optional()])
    
    transporte_info = TextAreaField('Informações sobre Transporte', validators=[Optional()])
    seguro_info = TextAreaField('Informações sobre Seguro', validators=[Optional()])
    servico_info = TextAreaField('Informações sobre Serviço', validators=[Optional()])
    
    diaria = StringField('Diária', validators=[Optional()])
    diaria_pessoa = StringField('Diária por Pessoa', validators=[Optional()])
    valor_total = StringField('Depósitos Negociados', validators=[Optional()])
    depositos_confirmados = StringField('Depósitos Confirmados', validators=[Optional()])
    lucro = StringField('Lucro', validators=[Optional()])
    
    submit = SubmitField('Reservar')
    


    
class ResetPasswordRequestForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Enviar Solicitação')

class ResetPasswordForm(FlaskForm):
    password = PasswordField('Nova Senha', validators=[DataRequired()])
    confirm_password = PasswordField('Confirmar Senha', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Redefinir Senha')
