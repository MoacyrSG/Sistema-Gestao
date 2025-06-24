from collections import defaultdict
from flask import Blueprint, Response, current_app, render_template, redirect, url_for, flash, request, jsonify, make_response
from flask_login import login_user, login_required, logout_user
from app import db
from app.models import Cliente, Hospedagem, Grupo, User, PrecoTabelado, Reserva, GrupoApartamento, Hospede
from app.forms import ClienteForm, HospedagemForm, GrupoForm, LoginForm, RegistrationForm, PrecoTabeladoForm, ReservaForm, TipoApartamentoForm, ResetPasswordRequestForm, ResetPasswordForm
from flask_mail import Message
from reportlab.lib.pagesizes import landscape, letter
from reportlab.pdfgen import canvas
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.utils import simpleSplit
from reportlab.lib.styles import getSampleStyleSheet
from datetime import datetime, timedelta
from reportlab.lib import units
from wtforms import SelectField
from reportlab.lib.utils import ImageReader
from sqlalchemy import case, extract, func
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
import pytz, os
from decimal import Decimal



main = Blueprint('main', __name__)


def parse_currency_ptbr(value):
    if value is None:
        return None
    try:
        value = str(value)
        value = value.replace('R$', '').replace(' ', '').replace('.', '').replace(',', '.')
        return float(value)
    except Exception:
        return None

def parse_float(valor_str):
    """Converte string '3.400,00' para float 3400.00"""
    try:
        return float(valor_str.replace('.', '').replace(',', '.'))
    except Exception:
        return 0.0
        

@main.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):  # Certifique-se de que existe um método check_password
            login_user(user)
            flash(f'Bem-vindo, {user.username}!', 'success') 
            return redirect(url_for('main.index'))
        else:
            flash('Usuário ou senha inválidos.', 'danger')
    return render_template('login.html', form=form)


@main.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Você saiu com sucesso.', 'success')
    return redirect(url_for('main.login'))


@main.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        # Verificar se o nome de usuário ou o email já existe
        user = User.query.filter_by(username=form.username.data).first()
        if user:
            flash('Nome de usuário já existe. Tente outro.', 'danger')
            return redirect(url_for('main.register'))
        
        # Verificar se o email já existe
        email_user = User.query.filter_by(email=form.email.data).first()
        if email_user:
            flash('Email já está em uso. Tente outro.', 'danger')
            return redirect(url_for('main.register'))

        # Criar o novo usuário com o email incluído
        new_user = User(username=form.username.data, email=form.email.data)
        new_user.set_password(form.password.data)
        
        # Adicionar o usuário ao banco de dados
        db.session.add(new_user)
        db.session.commit()
        
        flash('Cadastro realizado com sucesso! Agora você pode fazer login.', 'success')
        return redirect(url_for('main.login'))  # Redireciona para a página de login após o registro

    return render_template('register.html', form=form)



# Rota para página inicial
@main.route('/')
@login_required
def index():
    total_hospedagens = Hospedagem.query.count()

    hoje = datetime.today()

    # Primeiro dia da semana (domingo)
    domingo = hoje - timedelta(days=hoje.weekday() + 1 if hoje.weekday() != 6 else 0)
    domingo = datetime.combine(domingo.date(), datetime.min.time())

    # Último dia da semana (sábado)
    sabado = domingo + timedelta(days=6)
    sabado = datetime.combine(sabado.date(), datetime.max.time())

    # Contar reservas ativas na semana atual
    reservas_ativas = Reserva.query.filter(
        Reserva.data_ida >= domingo,
        Reserva.data_ida <= sabado
    ).count()

    # Contar reservas com pagamento pendente
    reservas_pendentes = Reserva.query.filter(
        (Reserva.valor_total - Reserva.depositos_confirmados) > 0
    ).count()

    return render_template(
        'index.html',
        total_hospedagens=total_hospedagens,
        reservas_ativas=reservas_ativas,
        reservas_pendentes=reservas_pendentes
    )
    
# Rota para cadastrar cliente
@main.route('/cadastrar_cliente', methods=['GET', 'POST'])
@login_required
def cadastrar_cliente():
    form = ClienteForm()
    if form.validate_on_submit():
        cliente = Cliente(
            nome=form.nome.data,
            cpf=form.cpf.data,
            rg=form.rg.data,
            telefone=form.telefone.data,
            email=form.email.data,
            logradouro=form.logradouro.data,
            numero=form.numero.data,
            complemento=form.complemento.data,
            cep=form.cep.data,
            municipio=form.municipio.data,
            estado=form.estado.data,
            pais=form.pais.data,
            observacao=form.observacao.data
        )
        db.session.add(cliente)
        db.session.commit()
        flash('Cliente cadastrado com sucesso!', 'success')
        return redirect(url_for('main.listar_clientes'))
    return render_template('cadastrar_cliente.html', form=form)


@main.route('/cadastrar_hospedagem', methods=['GET', 'POST'])
@login_required
def cadastrar_hospedagem():
    form = HospedagemForm()
    if form.validate_on_submit():
        nova_hospedagem = Hospedagem(
            nome=form.nome.data,
            cnpj=form.cnpj.data,
            tipo=form.tipo.data,
            endereco=form.endereco.data,
            telefone=form.telefone.data,
            descricao=form.descricao.data
        )
        db.session.add(nova_hospedagem)
        db.session.commit()
        flash('Hospedagem cadastrada com sucesso!', 'success')
        return redirect(url_for('main.listar_hospedagens')) 
    return render_template('cadastrar_hospedagem.html', form=form)
    

@main.route('/cadastrar_grupo', methods=['GET', 'POST'])
@login_required
def cadastrar_grupo():
    form = GrupoForm()
    form.hospedagem_id.choices = [(h.id, h.nome) for h in Hospedagem.query.all()]

    if form.validate_on_submit():
        hospedagem = Hospedagem.query.get(form.hospedagem_id.data)

        novo_grupo = Grupo(
            nome=form.nome.data,
            data_ida=form.data_ida.data,
            data_volta=form.data_volta.data,
            horario_chegada=form.horario_chegada.data,
            horario_partida=form.horario_partida.data,
            hospedagem_id=form.hospedagem_id.data,
            nome_hospedagem=hospedagem.nome if hospedagem else None
        )

        # Processa os apartamentos
        for tipo_form in form.tipos_apartamentos:
            tipo_apartamento = GrupoApartamento(
                tipo_apart=tipo_form.tipo_apart.data,
                qtd_apart=tipo_form.qtd_apart.data,
                preco=tipo_form.preco.data
            )
            novo_grupo.tipos_apartamentos.append(tipo_apartamento)

        db.session.add(novo_grupo)
        db.session.commit()
        flash('Grupo cadastrado com sucesso!', 'success')
        return redirect(url_for('main.listar_grupo')) 
    
    else:
        print("Formulário inválido!")
        print(form.errors)

    return render_template('cadastrar_grupo.html', form=form)


@main.route('/listar_clientes', methods=['GET'])
@login_required
def listar_clientes():
    busca = request.args.get('busca', '')
    pagina = request.args.get('pagina', 1, type=int)
    
    if busca:
        clientes_query = Cliente.query.filter(Cliente.nome.ilike(f'%{busca}%'))
    else:
        clientes_query = Cliente.query
    
    clientes = clientes_query.paginate(page=pagina, per_page=5, error_out=False)
    
    return render_template('listar_clientes.html', clientes=clientes, busca=busca)



@main.route('/listar_hospedagens', methods=['GET'])
@login_required
def listar_hospedagens():
    busca = request.args.get('busca', '')
    pagina = request.args.get('pagina', 1, type=int)
    
    if busca:
        hospedagens = Hospedagem.query.filter(Hospedagem.nome.ilike(f'%{busca}%'))
    else:
        hospedagens = Hospedagem.query
    
    hospedagens = hospedagens.paginate(page=pagina, per_page=5, error_out=False)
        
    return render_template('listar_hospedagens.html', hospedagens=hospedagens, busca=busca)


@main.route('/listar_grupo', methods=['GET'])
@login_required
def listar_grupo():
    busca = request.args.get('busca', '')
    pagina = request.args.get('pagina', 1, type=int)
    
    if busca:
        grupos = Grupo.query.filter(Grupo.nome.ilike(f'%{busca}%'))
    else:
        grupos = Grupo.query
        
    grupos = grupos.paginate(page=pagina, per_page=5, error_out=False)
        
    return render_template('listar_grupo.html', grupos=grupos, busca=busca)



@main.route('/editar_cliente/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_cliente(id):
    cliente = Cliente.query.get_or_404(id)  # Carrega o cliente com o ID específico ou retorna 404 se não for encontrado
    form = ClienteForm(obj=cliente)

    if form.validate_on_submit():
        # Atualiza os campos do cliente com os dados do formulário
        form.populate_obj(cliente)
        db.session.commit()
        flash('Cliente atualizado com sucesso!', 'success')
        return redirect(url_for('main.listar_clientes'))
    
    return render_template('editar_cliente.html', form=form, cliente=cliente)



@main.route('/excluir_cliente/<int:id>', methods=['POST'])
@login_required
def excluir_cliente(id):
    cliente = Cliente.query.get_or_404(id)
    db.session.delete(cliente)
    db.session.commit()
    flash('Cliente excluído com sucesso!', 'success')
    return redirect(url_for('main.listar_clientes'))


@main.route('/editar_hospedagem/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_hospedagem(id):
    hospedagem = Hospedagem.query.get_or_404(id)  # Carrega a hospedagem ou retorna 404
    form = HospedagemForm(obj=hospedagem)

    if form.validate_on_submit():
        # Atualiza os campos da hospedagem com os dados do formulário
        form.populate_obj(hospedagem)
        db.session.commit()
        flash('Hospedagem atualizada com sucesso!', 'success')
        return redirect(url_for('main.listar_hospedagens'))
    
    return render_template('editar_hospedagem.html', form=form, hospedagem=hospedagem)


@main.route('/excluir_hospedagem/<int:id>', methods=['POST'])
@login_required
def excluir_hospedagem(id):
    hospedagem = Hospedagem.query.get_or_404(id)
    
    # Excluir grupos relacionados
    grupos = Grupo.query.filter_by(hospedagem_id=id).all()
    for grupo in grupos:
        db.session.delete(grupo)
    
    try:
        # Excluir a hospedagem
        db.session.delete(hospedagem)
        db.session.commit()
        flash('Hospedagem excluída com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Ocorreu um erro ao excluir a hospedagem: {e}', 'danger')
    
    return redirect(url_for('main.listar_hospedagens'))



@main.route('/editar_grupo/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_grupo(id):
    grupo = Grupo.query.get_or_404(id)
    
    # Preenche automaticamente os campos com obj=grupo
    form = GrupoForm(obj=grupo)
    
    # Preenche as opções de hospedagem no SelectField
    form.hospedagem_id.choices = [(h.id, h.nome) for h in Hospedagem.query.all()]

    if form.validate_on_submit():
        # Atualiza os campos principais do grupo
        grupo.nome = form.nome.data
        grupo.data_ida = form.data_ida.data
        grupo.data_volta = form.data_volta.data
        grupo.horario_chegada = form.horario_chegada.data
        grupo.horario_partida = form.horario_partida.data
        grupo.hospedagem_id = form.hospedagem_id.data

        # Remove apartamentos antigos
        GrupoApartamento.query.filter_by(grupo_id=grupo.id).delete()

        # Adiciona os novos apartamentos
        for subform in form.tipos_apartamentos.entries:
            if subform.data['tipo_apart'] and subform.data['qtd_apart'] and subform.data['preco']:
                novo_apartamento = GrupoApartamento(
                    grupo_id=grupo.id,
                    tipo_apart=subform.data['tipo_apart'],
                    qtd_apart=subform.data['qtd_apart'],
                    preco=subform.data['preco']
                )
                db.session.add(novo_apartamento)

        try:
            db.session.commit()
            flash('Grupo atualizado com sucesso!', 'success')
            return redirect(url_for('main.listar_grupo'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao atualizar o grupo: {e}', 'danger')

    return render_template('editar_grupo.html', form=form, grupo=grupo)



@main.route('/excluir_grupo/<int:id>', methods=['POST'])
@login_required
def excluir_grupo(id):
    grupo = Grupo.query.get_or_404(id)

    try:
        db.session.delete(grupo)
        db.session.commit()
        flash('Grupo excluído com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao excluir o grupo: {e}', 'danger')

    return redirect(url_for('main.listar_grupo'))


@main.route('/cadastrar_precos', methods=['GET', 'POST'])
@login_required
def cadastrar_precos():
    form = PrecoTabeladoForm()
    
    form.hospedagem_id.choices = [(h.id, h.nome) for h in Hospedagem.query.all()]
    
    if form.validate_on_submit():        
        preco_tabelado = PrecoTabelado(
            single=form.single.data,
            duplo=form.duplo.data,
            triplo=form.triplo.data,
            quadruplo=form.quadruplo.data,
            chd=form.chd.data,
            hospedagem_id=form.hospedagem_id.data
        )
        
        db.session.add(preco_tabelado)
        db.session.commit()
        
        flash('Preço tabelado cadastrado com sucesso!', 'success')
        return redirect(url_for('main.listar_precos'))  # Redireciona para a listagem dos preços

    return render_template('cadastrar_precos.html', form=form)


@main.route('/listar_precos', methods=['GET'])
@login_required
def listar_precos():
    busca = request.args.get('busca', '')
    pagina = request.args.get('pagina', 1, type=int)

    if busca:
        precos_query = PrecoTabelado.query.join(Hospedagem).filter(Hospedagem.nome.ilike(f'%{busca}%'))
    else:
        precos_query = PrecoTabelado.query

    precos = precos_query.order_by(PrecoTabelado.id.asc()).paginate(page=pagina, per_page=5, error_out=False)

    return render_template('listar_precos.html', precos=precos, busca=busca)


@main.route('/editar_precos/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_precos(id):
    preco = PrecoTabelado.query.get_or_404(id)
    form = PrecoTabeladoForm(obj=preco)
    
    form.hospedagem_id.choices = [(h.id, h.nome) for h in Hospedagem.query.all()]
    
    if form.validate_on_submit():
        form.populate_obj(preco)
        db.session.commit()
        flash('Preço atualizado com sucesso!', 'success')
        return redirect(url_for('main.listar_precos'))
    
    return render_template('editar_precos.html', form=form, preco=preco)



@main.route('/excluir_precos/<int:id>', methods=['POST'])
@login_required
def excluir_precos(id):
    preco = PrecoTabelado.query.get_or_404(id)
    db.session.delete(preco)
    db.session.commit()
    flash('Preço excluído com sucesso!', 'success')
    return redirect(url_for('main.listar_precos'))


@main.route('/calcular_valor_hospedagem', methods=['POST'])
@login_required
def calcular_valor_hospedagem():
    data = request.get_json()
    hospedagem_id = data.get('hospedagem_id')
    adultos = data.get('adultos', 0)
    criancas_pagantes = data.get('criancas_pagantes', 0)
    
    if not hospedagem_id:
        return jsonify({'error': 'Hospedagem não selecionada'}), 400

    hospedagem = Hospedagem.query.get(hospedagem_id)
    preco_tabelado = PrecoTabelado.query.filter_by(hospedagem_id=str(hospedagem_id)).first()
    
    if not hospedagem or not preco_tabelado:
        return jsonify({'error': 'Dados de hospedagem não encontrados'}), 404

    # Calcular o valor da hospedagem
    valor_hospedagem = 0
    if adultos == 1:
        valor_hospedagem = preco_tabelado.single
    elif adultos == 2:
        valor_hospedagem = preco_tabelado.duplo
    elif adultos == 3:
        valor_hospedagem = preco_tabelado.triplo
    elif adultos >= 4:
        valor_hospedagem = preco_tabelado.quadruplo

    # Adicionar o valor por criança pagante
    valor_hospedagem += criancas_pagantes * preco_tabelado.chd

    return jsonify({'valor_hospedagem': valor_hospedagem})




@main.route('/cadastrar_reserva', methods=['GET', 'POST'])
@login_required
def cadastrar_reserva():
    form = ReservaForm()
    
    grupos = Grupo.query.all()
    hospedagens = Hospedagem.query.all()
    clientes = Cliente.query.all()
    
    form.grupo_id.choices = [(grupo.id, grupo.nome) for grupo in Grupo.query.all()]
    form.hospedagem_id.choices = [(hospedagem.id, hospedagem.nome) for hospedagem in Hospedagem.query.all()]
    form.cliente_id.choices = [(cliente.id, cliente.nome) for cliente in Cliente.query.all()]
    
    if form.validate_on_submit():
        opcoes_pacote = form.opcoes_pacote.data if form.opcoes_pacote.data else []
        
        # Atribuição de nome da hospedagem
        nome_hospedagem = None
        if 'hospedagem' in form.opcoes_pacote.data:
            hospedagem = Hospedagem.query.get(form.hospedagem_id.data)
            nome_hospedagem = hospedagem.nome if hospedagem else None
            
        nome_grupo = None
        nome_hospedagem_grupo = None
        hospedagem_id_grupo = None
        tipo_apart_grupo = None

        if form.tipo_reserva.data == 'Grupo':
            grupo = Grupo.query.get(form.grupo_id.data)
            nome_grupo = grupo.nome if grupo else None
            nome_hospedagem_grupo = grupo.nome_hospedagem if grupo else None
            hospedagem_id_grupo = grupo.hospedagem_id if grupo else None
            
            if grupo.tipos_apartamentos:
                tipo_apart_grupo = ', '.join([ap.tipo_apart for ap in grupo.tipos_apartamentos])
          
          
        cliente = Cliente.query.get(form.cliente_id.data)  
        nome_cliente = cliente.nome if cliente else None
    

        reserva = Reserva(
            id_reserva=form.id_reserva.data,
            tipo_reserva=form.tipo_reserva.data,
            cliente_id = form.cliente_id.data,
            nome_cliente = nome_cliente,
            num_adultos=form.num_adultos.data or None,
            num_criancas=form.num_criancas.data or None,
            num_criancas_free=form.num_criancas_free.data or None,
            confirmada_por=form.confirmada_por.data or None,
            status=form.status.data or None,
            pensao=form.pensao.data or None,
            garante_no_show=True if form.garante_no_show.data == 'sim' else False,
            evento=True if form.evento.data == 'sim' else False,
            descricao=form.descricao.data or None,
            data_ida=form.data_ida.data or None,
            data_volta=form.data_volta.data or None,
            horario_ida=form.horario_ida.data or None,
            horario_chegada=form.horario_chegada.data or None,
            
            grupo_id=form.grupo_id.data if form.tipo_reserva.data == 'Grupo' else None,
            nome_grupo=nome_grupo,
            nome_hospedagem_grupo=nome_hospedagem_grupo,
            hospedagem_id_grupo=hospedagem_id_grupo,
            tipo_apart_grupo=tipo_apart_grupo,
            
            opcoes_pacote=opcoes_pacote,

            companhia=form.companhia.data if 'aereo' in form.opcoes_pacote.data else None,
            numero_voo=form.numero_voo.data if 'aereo' in form.opcoes_pacote.data else None,
            origem=form.origem.data if 'aereo' in form.opcoes_pacote.data else None,
            destino=form.destino.data if 'aereo' in form.opcoes_pacote.data else None,
            escala=form.escala.data if 'aereo' in form.opcoes_pacote.data else None,
            inclui_bagagem=form.inclui_bagagem.data if 'aereo' in form.opcoes_pacote.data else None,

            # Dados de Hospedagem (somente se 'hospedagem' estiver selecionado)
            hospedagem_id=form.hospedagem_id.data if 'hospedagem' in form.opcoes_pacote.data else None,
            nome_hospedagem=nome_hospedagem,
            tipo_apart=form.tipo_apart.data if 'hospedagem' in form.opcoes_pacote.data else None,

            # Outras informações do Pacote
            transporte_info=form.transporte_info.data if 'transporte' in form.opcoes_pacote.data else None,
            seguro_info=form.seguro_info.data if 'seguro' in form.opcoes_pacote.data else None,
            servico_info=form.servico_info.data if 'servico' in form.opcoes_pacote.data else None,
            
            diaria=parse_currency_ptbr(form.diaria.data),
            diaria_pessoa=parse_currency_ptbr(form.diaria_pessoa.data),
            valor_total=parse_currency_ptbr(form.valor_total.data),
            depositos_confirmados=parse_currency_ptbr(form.depositos_confirmados.data),
            lucro=parse_currency_ptbr(form.lucro.data),
        )


        # Adiciona os hóspedes relacionados à reserva
        for hospede_form in form.hospedes.entries:
            if hospede_form.data['nome']:
                hospede = Hospede(nome=hospede_form.data['nome'])
                reserva.hospedes.append(hospede)

        # Adiciona a reserva ao banco de dados
        db.session.add(reserva)
        db.session.commit()

        flash(f'Reserva para {reserva.tipo_reserva} "{reserva.cliente_id}" cadastrada com sucesso!', 'success')
        return redirect(url_for('main.listar_reserva'))

    # Em caso de erros de validação
    if form.errors:
        print("Erros de validação:")
        for field, errors in form.errors.items():
            for error in errors:
                print(f"{field}: {error}")

    return render_template('cadastrar_reserva.html', form=form, grupos=grupos, hospedagens=hospedagens, clientes=clientes)






@main.route('/grupo/<int:grupo_id>', methods=['GET'])
@login_required
def get_grupo(grupo_id):
    grupo = Grupo.query.get_or_404(grupo_id)
    return jsonify({
        'data_ida': grupo.data_ida.strftime('%Y-%m-%d') if grupo.data_ida else '',
        'data_volta': grupo.data_volta.strftime('%Y-%m-%d') if grupo.data_volta else '',
        'horario_chegada': grupo.horario_chegada.strftime('%H:%M') if grupo.horario_chegada else '',
        'horario_partida': grupo.horario_partida.strftime('%H:%M') if grupo.horario_partida else '',
        'nome_hospedagem': grupo.nome_hospedagem
    })


@main.route('/listar_reserva', methods=['GET'])
@login_required
def listar_reserva():
    nome_cliente = request.args.get('nome_cliente', type=int)
    pagina = request.args.get('pagina', 1, type=int)

    if nome_cliente:
        reservas_query = Reserva.query.filter_by(nome_cliente=nome_cliente)
    else:
        reservas_query = Reserva.query

    reservas = reservas_query.order_by(Reserva.id.asc()).paginate(page=pagina, per_page=5, error_out=False)

    return render_template('listar_reserva.html', reservas=reservas, nome_cliente=nome_cliente)



@main.route('/reservas_ativas', methods=['GET'])
@login_required
def reservas_ativas():
    nome_cliente = request.args.get('nome_cliente', type=int)
    hoje = datetime.today()

    # Primeiro dia da semana (domingo)
    domingo = hoje - timedelta(days=hoje.weekday() + 1 if hoje.weekday() != 6 else 0)
    domingo = datetime.combine(domingo.date(), datetime.min.time())

    # Último dia da semana (sábado)
    sabado = domingo + timedelta(days=6)
    sabado = datetime.combine(sabado.date(), datetime.max.time())

    # Consulta com ou sem filtro de nome_cliente
    reservas_query = Reserva.query.filter(
        Reserva.data_ida >= domingo,
        Reserva.data_ida <= sabado
    )

    if nome_cliente:
        reservas_query = reservas_query.filter(Reserva.nome_cliente == nome_cliente)

    reservas = reservas_query.order_by(Reserva.data_ida.asc()).all()

    return render_template('reservas_ativas.html', reservas=reservas, nome_cliente=nome_cliente)



@main.route('/reservas_pendentes', methods=['GET'])
@login_required
def reservas_pendentes():
    nome_cliente = request.args.get('nome_cliente', type=int)

    # Consulta base: todas as reservas com valor pendente
    reservas_query = Reserva.query.filter(
        (Reserva.valor_total - Reserva.depositos_confirmados) > 0
    )

    # Filtro opcional por nome_cliente
    if nome_cliente:
        reservas_query = reservas_query.filter(Reserva.nome_cliente == nome_cliente)

    # Ordenar por data de ida (opcional, mas ajuda na visualização)
    reservas = reservas_query.order_by(Reserva.data_ida.asc()).all()

    return render_template('reservas_pendentes.html', reservas=reservas, nome_cliente=nome_cliente)




@main.route('/editar_reserva/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_reserva(id):
    reserva = Reserva.query.get_or_404(id)
    
    # Carrega choices ANTES de criar o form
    cliente_choices = [(c.id, c.nome) for c in Cliente.query.order_by(Cliente.nome).all()]
    grupo_choices = [(g.id, g.nome) for g in Grupo.query.order_by(Grupo.nome).all()]
    hospedagem_choices = [(h.id, h.nome) for h in Hospedagem.query.order_by(Hospedagem.nome).all()]

    form = ReservaForm(obj=reserva)
    form.cliente_id.choices = cliente_choices
    form.grupo_id.choices = grupo_choices
    form.hospedagem_id.choices = hospedagem_choices
    
    # Identificar se a reserva é Grupo ou Pacote
    tipo_reserva = 'grupo' if reserva.grupo_id else 'pacote'
    
    if isinstance(reserva.opcoes_pacote, str):  # Garante que seja string antes de processar
        opcoes_pacote = reserva.opcoes_pacote.strip('{}').split(',') if reserva.opcoes_pacote else []
    else:
        opcoes_pacote = []
        
    if reserva.companhia or reserva.numero_voo or reserva.origem or reserva.destino or reserva.escala or reserva.inclui_bagagem:
        opcoes_pacote.append('aereo')
    if reserva.hospedagem_id or reserva.tipo_apart:
        opcoes_pacote.append('hospedagem')
    if reserva.transporte_info:
        opcoes_pacote.append('transporte')
    if reserva.seguro_info:
        opcoes_pacote.append('seguro')
    if reserva.servico_info:
        opcoes_pacote.append('servico')

    
    if form.validate_on_submit():
        form.populate_obj(reserva)
        
        reserva.evento = True if form.evento.data == 'sim' else False
        reserva.garante_no_show = True if form.garante_no_show.data == 'sim' else False

        reserva.diaria = parse_float(form.diaria.data)
        reserva.diaria_pessoa = parse_float(form.diaria_pessoa.data)
        reserva.valor_total = parse_float(form.valor_total.data)
        reserva.depositos_confirmados = parse_float(form.depositos_confirmados.data)
        reserva.lucro = parse_float(form.lucro.data)
        
        db.session.commit()
        flash('Reserva atualizada com sucesso!', 'success')
        return redirect(url_for('main.listar_reserva'))
    else:
        print("❌ Erros no formulário:")
        print(form.errors)

    return render_template('editar_reserva.html', form=form, reserva=reserva, tipo_reserva=tipo_reserva, opcoes_pacote=opcoes_pacote)


@main.route('/excluir_reserva/<int:id>', methods=['POST'])
@login_required
def excluir_reserva(id):
    reserva = Reserva.query.get_or_404(id)
    db.session.delete(reserva)
    db.session.commit()
    flash('Reserva excluída com sucesso!', 'success')
    return redirect(url_for('main.listar_reserva'))


@main.route('/relatorios/relatorios_reservas')
@login_required
def relatorios_reservas():
    # Obtém o ano selecionado
    ano_selecionado = request.args.get('ano', default=2025, type=int)

    # Query para buscar total de reservas e valor total por mês/ano
    query = db.session.query(
        extract('month', Reserva.data_ida).label('mes'),
        func.count(Reserva.id).label('quantidade_reservas'),
        func.sum(Reserva.valor_total).label('total_vendas'),
        func.sum(Reserva.lucro).label('lucro')
    ).filter(
        extract('year', Reserva.data_ida) == ano_selecionado
    )

    # Execute a consulta para obter os dados agrupados por mês
    resultados = query.group_by('mes').order_by('mes').all()

    # Formata os dados para exibição no template
    dados_relatorio = {mes: {'quantidade': 0, 'total': 0.0, 'reservas': [], 'lucro': 0.0} for mes in range(1, 13)}

    for resultado in resultados:
        mes = int(resultado.mes)
        dados_relatorio[mes]['quantidade'] = resultado.quantidade_reservas
        dados_relatorio[mes]['total'] = resultado.total_vendas or 0.0
        dados_relatorio[mes]['lucro'] = resultado.lucro or 0.0

        # Consulta para buscar as reservas detalhadas para aquele mês
        reservas_mes = db.session.query(Reserva).filter(
            extract('month', Reserva.data_ida) == mes,
            extract('year', Reserva.data_ida) == ano_selecionado
        ).all()

        dados_relatorio[mes]['reservas'] = reservas_mes

    # Lista de anos disponíveis para o filtro
    anos_disponiveis = [
        row[0] for row in db.session.query(extract('year', Reserva.data_ida)).distinct().all()
    ]

    return render_template(
        'relatorios_reservas.html',
        dados_relatorio=dados_relatorio,
        ano_selecionado=ano_selecionado,
        anos_disponiveis=anos_disponiveis
    )


@main.route('/relatorios/relatorios_hospedagens')
@login_required
def relatorios_hospedagens():
    # Capturar o ano selecionado no filtro
    ano_selecionado = request.args.get('ano', None, type=int)

    # Buscar todas as hospedagens cadastradas
    hospedagens = Hospedagem.query.all()

    # Buscar todas as reservas do banco de dados
    reservas = Reserva.query.all()

    # Criar dicionário para armazenar os dados do relatório
    dados_relatorio = defaultdict(lambda: {
        "nome": "",
        "dados_mensais": {mes: {"grupo": 0, "pacote": 0} for mes in range(1, 13)}
    })

    # Inicializar todas as hospedagens no relatório
    for hospedagem in hospedagens:
        dados_relatorio[hospedagem.id]["nome"] = hospedagem.nome

    # Processar as reservas e somar o faturamento de cada hospedagem
    for reserva in reservas:
        # Determinar se a reserva é Grupo ou Pacote
        if reserva.tipo_reserva == "Grupo":
            hospedagem_id = reserva.hospedagem_id_grupo
            nome_hospedagem = reserva.nome_hospedagem_grupo
            tipo = "grupo"
        else:  # Pacote
            hospedagem_id = reserva.hospedagem_id
            nome_hospedagem = reserva.nome_hospedagem
            tipo = "pacote"

        # Se a hospedagem estiver associada à reserva, garantir que ela está no relatório
        if hospedagem_id:
            dados_relatorio[hospedagem_id]["nome"] = nome_hospedagem
            mes_reserva = reserva.data_ida.month
            dados_relatorio[hospedagem_id]["dados_mensais"][mes_reserva][tipo] += reserva.valor_total

    # Obter os anos disponíveis para filtro
    anos_disponiveis = db.session.query(db.func.extract('year', Reserva.data_ida)).distinct().order_by(db.func.extract('year', Reserva.data_ida)).all()
    anos_disponiveis = [int(ano[0]) for ano in anos_disponiveis]

    return render_template(
        "relatorios_hospedagens.html",
        dados_relatorio=dados_relatorio,
        anos_disponiveis=anos_disponiveis,
        ano_selecionado=ano_selecionado
    )

MESES = {
    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
    5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
    9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
}



@main.route('/gerar_relatorio_reservas')
@login_required
def gerar_relatorio_reservas():
    ano_selecionado = request.args.get('ano', default=2025, type=int)
    
    caminho_logo = os.path.join(current_app.root_path, 'static', 'assets', 'imagens', 'logo_coutinho.png')

    # Faturamento por mês
    query = db.session.query(
        extract('month', Reserva.data_ida).label('mes'),
        func.count(Reserva.id).label('quantidade_reservas'),
        func.sum(Reserva.valor_total).label('total_vendas')
    ).filter(
        extract('year', Reserva.data_ida) == ano_selecionado
    ).group_by('mes').order_by('mes').all()

    faturamento = {i: {'quantidade_reservas': 0, 'total_vendas': 0} for i in range(1, 13)}
    for resultado in query:
        faturamento[resultado.mes]['quantidade_reservas'] = resultado.quantidade_reservas
        faturamento[resultado.mes]['total_vendas'] = resultado.total_vendas

    # Detalhes das reservas por mês
    detalhes_reservas = {i: [] for i in range(1, 13)}
    reservas = db.session.query(
        extract('month', Reserva.data_ida).label('mes'),
        Reserva.nome_cliente.label("nome_cliente"),
        Reserva.tipo_reserva.label("tipo_reserva"),
        Reserva.data_ida,
        Reserva.data_volta,
        Reserva.valor_total
    ).filter(
        extract('year', Reserva.data_ida) == ano_selecionado
    ).order_by(Reserva.data_ida).all()

    for reserva in reservas:
        detalhes_reservas[reserva.mes].append(reserva)

    # Criar PDF
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=landscape(letter))

    # Página inicial com resumo
    if os.path.exists(caminho_logo):
        logo = ImageReader(caminho_logo)
        pdf.drawImage(logo, 30, 500, width=100, height=80, mask='auto')

    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(180, 540, f"Relatório de Reservas - {ano_selecionado}")
    pdf.setFont("Helvetica", 12)
    pdf.drawString(180, 520, f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}")

    # Faturamento por mês
    y = 480
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(30, y, "Faturamento por Mês")
    y -= 20

    pdf.setFillColor("#0066ff")
    pdf.rect(30, y - 10, 180, 25, fill=1)
    pdf.setFillColor("#33ccff")
    pdf.rect(210, y - 10, 150, 25, fill=1)
    pdf.setFillColor("#0066ff")
    pdf.rect(370, y - 10, 200, 25, fill=1)

    pdf.setFillColor(colors.white)
    pdf.drawString(40, y, "Mês")
    pdf.drawString(220, y, "Reservas")
    pdf.drawString(380, y, "Total Vendido (R$)")
    y -= 25

    pdf.setFont("Helvetica", 12)
    for mes, data in faturamento.items():
        nome_mes = MESES[mes]
        pdf.setFillColor("#e6f2ff" if mes % 2 == 0 else colors.white)
        pdf.rect(30, y - 10, 180, 20, fill=1)
        pdf.rect(210, y - 10, 150, 20, fill=1)
        pdf.rect(370, y - 10, 200, 20, fill=1)

        pdf.setFillColor(colors.black)
        pdf.drawString(40, y, nome_mes)
        pdf.drawString(220, y, str(data['quantidade_reservas']))
        pdf.drawString(380, y, f"R$ {data['total_vendas']:,.2f}")
        y -= 20

    pdf.showPage()

    # Uma página por mês com os detalhes
    for mes in range(1, 13):
        nome_mes = MESES[mes]

        # Logo e cabeçalho em cada nova página
        if os.path.exists(caminho_logo):
            logo = ImageReader(caminho_logo)
            pdf.drawImage(logo, 30, 500, width=100, height=80, mask='auto')

        pdf.setFont("Helvetica-Bold", 16)
        pdf.drawString(180, 540, f"Reservas - {nome_mes} / {ano_selecionado}")
        pdf.setFont("Helvetica", 12)
        pdf.drawString(180, 520, f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}")

        y = 480
        pdf.setFont("Helvetica-Bold", 14)
        pdf.drawString(30, y, f"Reservas para o mês de {nome_mes}")
        y -= 20

        if not detalhes_reservas[mes]:
            pdf.setFont("Helvetica", 12)
            pdf.drawString(30, y, "Não foram feitas reservas neste mês")
            pdf.showPage()
            continue

        # Cabeçalho da tabela
        pdf.setFillColor("#0066ff")
        pdf.rect(30, y - 10, 180, 25, fill=1)
        pdf.setFillColor("#33ccff")
        pdf.rect(210, y - 10, 120, 25, fill=1)
        pdf.setFillColor("#0066ff")
        pdf.rect(330, y - 10, 120, 25, fill=1)
        pdf.setFillColor("#33ccff")
        pdf.rect(450, y - 10, 120, 25, fill=1)
        pdf.setFillColor("#0066ff")
        pdf.rect(570, y - 10, 120, 25, fill=1)

        pdf.setFillColor(colors.white)
        pdf.drawString(35, y, "Nome da Reserva")
        pdf.drawString(215, y, "Tipo")
        pdf.drawString(335, y, "Data de Ida")
        pdf.drawString(455, y, "Data de Volta")
        pdf.drawString(575, y, "Valor (R$)")
        y -= 25

        pdf.setFont("Helvetica", 12)
        for i, reserva in enumerate(detalhes_reservas[mes]):
            if y < 70:
                pdf.showPage()
                y = 520
                # Reescreve cabeçalho da tabela
                pdf.setFont("Helvetica-Bold", 14)
                pdf.drawString(30, y, f"Reservas para o mês de {nome_mes} (continuação)")
                y -= 20

                pdf.setFillColor("#0066ff")
                pdf.rect(30, y - 10, 180, 25, fill=1)
                pdf.setFillColor("#33ccff")
                pdf.rect(210, y - 10, 120, 25, fill=1)
                pdf.setFillColor("#0066ff")
                pdf.rect(330, y - 10, 120, 25, fill=1)
                pdf.setFillColor("#33ccff")
                pdf.rect(450, y - 10, 120, 25, fill=1)
                pdf.setFillColor("#0066ff")
                pdf.rect(570, y - 10, 120, 25, fill=1)

                pdf.setFillColor(colors.white)
                pdf.drawString(35, y, "Nome da Reserva")
                pdf.drawString(215, y, "Tipo")
                pdf.drawString(335, y, "Data de Ida")
                pdf.drawString(455, y, "Data de Volta")
                pdf.drawString(575, y, "Valor (R$)")
                y -= 25

            pdf.setFillColor("#e6f2ff" if i % 2 == 0 else colors.white)
            pdf.rect(30, y - 10, 180, 20, fill=1)
            pdf.rect(210, y - 10, 120, 20, fill=1)
            pdf.rect(330, y - 10, 120, 20, fill=1)
            pdf.rect(450, y - 10, 120, 20, fill=1)
            pdf.rect(570, y - 10, 120, 20, fill=1)

            pdf.setFillColor(colors.black)
            pdf.drawString(35, y, reserva.nome_cliente)
            pdf.drawString(215, y, reserva.tipo_reserva)
            pdf.drawString(335, y, reserva.data_ida.strftime('%d/%m/%Y'))
            pdf.drawString(455, y, reserva.data_volta.strftime('%d/%m/%Y'))
            pdf.drawString(575, y, f"R$ {reserva.valor_total:,.2f}")
            y -= 20

        pdf.showPage()

    pdf.save()
    buffer.seek(0)

    return Response(buffer, mimetype='application/pdf',
                    headers={'Content-Disposition': f'attachment;filename=relatorio_reservas_{ano_selecionado}.pdf'})

    

@main.route('/gerar_relatorio_hospedagens')
@login_required
def gerar_relatorio_hospedagens():
    ano_selecionado = request.args.get('ano', default=2025, type=int)

    caminho_logo = os.path.join(current_app.root_path, 'static', 'assets', 'imagens', 'logo_coutinho.png')

    hospedagens = Hospedagem.query.all()
    reservas = Reserva.query.filter(extract('year', Reserva.data_ida) == ano_selecionado).all()

    dados_relatorio = defaultdict(lambda: {
        "nome": "",
        "dados_mensais": {mes: {"grupo": 0, "pacote": 0} for mes in range(1, 13)}
    })

    for hospedagem in hospedagens:
        dados_relatorio[hospedagem.id]["nome"] = hospedagem.nome

    for reserva in reservas:
        if reserva.tipo_reserva == "Grupo":
            hospedagem_id = reserva.hospedagem_id_grupo
            tipo = "grupo"
        else:
            hospedagem_id = reserva.hospedagem_id
            tipo = "pacote"

        if hospedagem_id:
            mes = reserva.data_ida.month
            dados_relatorio[hospedagem_id]["dados_mensais"][mes][tipo] += reserva.valor_total

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=landscape(letter))

    def desenhar_cabecalho():
        if os.path.exists(caminho_logo):
            logo = ImageReader(caminho_logo)
            pdf.drawImage(logo, 30, 500, width=100, height=80, mask='auto')

        pdf.setFont("Helvetica-Bold", 18)
        pdf.drawString(180, 540, f"Relatório de Hospedagens - {ano_selecionado}")
        pdf.setFont("Helvetica", 12)
        pdf.drawString(180, 520, f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}")

    first = True
    
    for hospedagem_id, info in dados_relatorio.items():
        if not first:
            pdf.showPage()
        first = False
        
        desenhar_cabecalho()

        y = 480
        nome_hospedagem = info["nome"]
        dados_mensais = info["dados_mensais"]

        pdf.setFont("Helvetica-Bold", 16)
        pdf.drawString(30, y, f"{nome_hospedagem}")
        y -= 20

        # Cabeçalho da tabela
        pdf.setFillColor("#0066ff")
        pdf.rect(30, y - 10, 150, 25, fill=1)
        pdf.setFillColor("#33ccff")
        pdf.rect(180, y - 10, 180, 25, fill=1)
        pdf.setFillColor("#0066ff")
        pdf.rect(360, y - 10, 180, 25, fill=1)

        pdf.setFillColor(colors.white)
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(40, y, "Mês")
        pdf.drawString(190, y, "Faturamento Grupo (R$)")
        pdf.drawString(370, y, "Faturamento Pacote (R$)")
        y -= 25

        pdf.setFont("Helvetica", 12)
        for mes in range(1, 13):
            grupo = dados_mensais[mes]['grupo']
            pacote = dados_mensais[mes]['pacote']

            cor_fundo = "#e6f2ff" if mes % 2 == 0 else colors.white
            pdf.setFillColor(cor_fundo)
            pdf.rect(30, y - 10, 150, 20, fill=1)
            pdf.rect(180, y - 10, 180, 20, fill=1)
            pdf.rect(360, y - 10, 180, 20, fill=1)

            pdf.setFillColor(colors.black)
            pdf.drawString(40, y, MESES[mes])
            pdf.drawString(190, y, f"R$ {grupo:,.2f}")
            pdf.drawString(370, y, f"R$ {pacote:,.2f}")
            y -= 20

    pdf.save()
    buffer.seek(0)

    return Response(buffer, mimetype='application/pdf',
                    headers={'Content-Disposition': f'attachment;filename=relatorio_hospedagens_{ano_selecionado}.pdf'})



@main.route('/gerar_voucher/<int:id>')
@login_required
def gerar_voucher(id):
    reserva = Reserva.query.get_or_404(id)

    buffer = BytesIO()
    response = make_response()

    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    # Cores principais
    azul_escuro = colors.HexColor("#0A2540")
    cinza_claro = colors.HexColor("#000000")

    # Caminhos das logos
    logo_jardins_jurema_path = 'app/static/assets/imagens/logo_jardins_jurema.jpeg'
    logo_coutinho_path = 'app/static/assets/imagens/logo_coutinho.png'
    
    nome_hospedagem = reserva.nome_hospedagem or ''
    nome_grupo = reserva.nome_hospedagem_grupo or ''

    if 'jardins de jurema' in nome_hospedagem.lower() or 'jardins de jurema' in nome_grupo.lower():
        logo_hospedagem_path = 'app/static/assets/imagens/logo_jardins_jurema.jpeg'
    elif 'lagos de jurema' in nome_hospedagem.lower() or 'lagos de jurema' in nome_grupo.lower():
        logo_hospedagem_path = 'app/static/assets/imagens/logo_lagos_jurema.jpeg'
    else:
        logo_hospedagem_path = None  # Pode colocar uma logo padrão se quiser

    # Tamanhos das logos
    logo_width = 160
    logo_height = 60
    margin_top = height - 90  # margem superior para as logos

    # Logo da hospedagem (à esquerda)
    if logo_hospedagem_path:
        c.drawImage(logo_hospedagem_path, 50, margin_top, width=logo_width, height=logo_height, preserveAspectRatio=True, mask='auto')

    # Logo Coutinho (à direita)
    c.drawImage(logo_coutinho_path, width - logo_width - 50, margin_top, width=logo_width, height=logo_height, preserveAspectRatio=True, mask='auto')

    # Cabeçalho centralizado entre as logos
    fuso_brasilia = pytz.timezone("America/Sao_Paulo")
    agora = datetime.now(fuso_brasilia)
    data_geracao = agora.strftime("%d/%m/%Y")
    hora_geracao = agora.strftime("%H:%M")

    data = reserva.data_ida  # datetime com fuso de Brasília
    ano = str(data.year)[-2:]    # ex: 2025 -> '25'
    mes = str(data.month).zfill(2)  # ex: 4 -> '04'
    
    # Contar quantas reservas existem no mesmo mês/ano da data_ida
    qtde_reservas_mes = Reserva.query.filter(
        db.extract('year', Reserva.data_ida) == data.year,
        db.extract('month', Reserva.data_ida) == data.month,
        Reserva.data_ida <= data  # apenas anteriores ou no mesmo dia
    ).order_by(Reserva.data_ida).all()
    
    # Posição dessa reserva na lista
    ordem_no_mes = qtde_reservas_mes.index(reserva) + 1
    numero = str(ordem_no_mes).zfill(2)

    # Monta o número da reserva
    numero_reserva = f"{ano}{mes}{numero}"

    title_x = 220  # Posição horizontal do texto centralizado
    title_y = margin_top + 35  # vertical no meio das logos

    c.setFont("Helvetica-Bold", 18)
    c.setFillColor(azul_escuro)
    c.drawString(title_x, title_y, f"VOUCHER {numero_reserva}")

    c.setFont("Helvetica", 10)
    c.setFillColor(colors.black)
    c.drawString(title_x, title_y - 15, f"Emitido em {data_geracao} às {hora_geracao}")

    # Linha separadora abaixo da logo e texto
    linha_y = margin_top - 10
    c.setStrokeColor(cinza_claro)
    c.setLineWidth(1)
    c.line(50, linha_y, width - 50, linha_y)

    # Começa o conteúdo depois da logo e linha
    y = linha_y - 30


    # Saudação
    y = height - 130
    c.setFont("Helvetica", 12)
    
    partes_nome = reserva.nome_cliente.strip().split()
    if len(partes_nome) > 1:
        sobrenome = partes_nome[-1]
        nome = " ".join(partes_nome[:-1])
        nome_formatado = f"{sobrenome}, {nome}"
    else:
        nome_formatado = reserva.nome_cliente
        
    # Define o nome da hospedagem de acordo com o tipo da reserva
    if reserva.tipo_reserva == 'Grupo':
        nome_hospedagem = reserva.nome_hospedagem_grupo
    elif reserva.tipo_reserva == 'Pacote':
        nome_hospedagem = reserva.nome_hospedagem
    else:
        nome_hospedagem = "hospedagem não identificada"

        
    c.drawString(50, y, f"Prezado Sr.(a): {nome_formatado}")
    y -= 20
    c.drawString(50, y, f"Anexo segue voucher referente à sua reserva para {nome_hospedagem}.")
    y -= 10
    c.line(50, y, width - 50, y)
    y -= 30

    # Títulos
    c.setFont("Helvetica-Bold", 11)
    x_nome = 50
    x_chegada = 300
    x_partida = 450

    c.drawString(x_nome, y, "Nome do Hóspede")
    c.drawString(x_chegada, y, "Data de Chegada")
    c.drawString(x_partida, y, "Data de Partida")

    y -= 18

    # Valores
    hospedes = Hospede.query.filter_by(reserva_id=reserva.id).all()
    nome_hospede = hospedes[0].nome if hospedes else "Nenhum hóspede informado"
    
    partes_nome = nome_hospede.strip().split()
    if len(partes_nome) > 1:
        sobrenome = partes_nome[-1]
        nome = " ".join(partes_nome[:-1])
        nome_formatado_hospede = f"{sobrenome}, {nome}"
    else:
        nome_formatado_hospede = nome_hospede

    c.setFont("Helvetica", 11)
    c.drawString(x_nome, y, nome_formatado_hospede)
    c.drawString(x_chegada, y, reserva.data_ida.strftime('%d/%m/%Y'))
    c.drawString(x_partida, y, reserva.data_volta.strftime('%d/%m/%Y'))

    y -= 20

    # Linha separadora depois
    c.line(50, y, width - 50, y)
    y -= 30

    # Primeira linha de dados (Chegada, horário, Tipo, Pensão)
    c.setFont("Helvetica", 11)
    c.drawString(50, y, "Chegada:")
    c.setFont("Helvetica-Bold", 11)
    c.drawString(100, y, reserva.data_ida.strftime('%d/%m/%Y'))

    c.setFont("Helvetica-Bold", 11)
    c.drawString(180, y, reserva.horario_ida.strftime('%H:%M'))

    c.setFont("Helvetica", 11)
    c.drawString(250, y, "Tipo de Apartamento:")

    # Definindo o valor a ser exibido
    if reserva.tipo_reserva == 'Grupo':
        tipo_apartamento = reserva.tipo_apart_grupo.capitalize()
    elif reserva.tipo_reserva == 'Pacote':
        tipo_apartamento = reserva.tipo_apart.capitalize()
    else:
        tipo_apartamento = ""

    c.setFont("Helvetica-Bold", 11)
    c.drawString(360, y, tipo_apartamento if tipo_apartamento else "Não informado")

    c.setFont("Helvetica", 11)
    c.drawString(420, y, "Pensão:")
    c.setFont("Helvetica-Bold", 11)
    c.drawString(465, y, reserva.pensao.capitalize() if reserva.pensao else "")

    y -= 20

    # Segunda linha de dados (Partida, horário, Status, Garante No-Show)
    c.setFont("Helvetica", 11)
    c.drawString(50, y, "Partida:")
    c.setFont("Helvetica-Bold", 11)
    c.drawString(90, y, reserva.data_volta.strftime('%d/%m/%Y'))

    c.setFont("Helvetica-Bold", 11)
    c.drawString(180, y, reserva.horario_chegada.strftime('%H:%M'))

    c.setFont("Helvetica", 11)
    c.drawString(250, y, "Status:")
    c.setFont("Helvetica-Bold", 11)
    c.drawString(290, y, reserva.status.capitalize() if reserva.status else "")

    c.setFont("Helvetica", 11)
    c.drawString(420, y, "Garante No-Show:")
    c.setFont("Helvetica-Bold", 11)
    c.drawString(515, y, "Sim" if reserva.garante_no_show else "Não")
    
    y -= 30
    
    c.setFont("Helvetica", 11)
    c.drawString(50, y, "Adultos:")
    c.setFont("Helvetica-Bold", 11)
    c.drawString(95, y, str(reserva.num_adultos) if reserva.num_adultos else "0")
    
    c.setFont("Helvetica", 11)
    c.drawString(180, y, "Crianças:")
    c.setFont("Helvetica-Bold", 11)
    c.drawString(230, y, str(reserva.num_criancas) if reserva.num_criancas else "0")

    c.setFont("Helvetica", 11)
    c.drawString(310, y, "Criança Free:")
    c.setFont("Helvetica-Bold", 11)
    c.drawString(390, y, str(reserva.num_criancas_free) if reserva.num_criancas_free else "0")

    y -= 20

    # Linha separadora após esse bloco
    c.setStrokeColor(cinza_claro)
    c.setLineWidth(1)
    c.line(50, y, width - 50, y)
    y -= 30
    
    c.setFont("Helvetica", 11)
    c.drawString(50, y, "Diária:")
    c.setFont("Helvetica-Bold", 11)
    c.drawString(85, y, "R$")
    c.drawString(100, y, str(reserva.diaria) if reserva.diaria else "")
    
    y -= 30
    
    c.setFont("Helvetica", 11)
    c.drawString(50, y, "Total de Diárias por pessoa:")
    c.setFont("Helvetica-Bold", 11)
    c.drawString(190, y, "R$")
    c.drawString(205, y, str(reserva.diaria_pessoa) if reserva.diaria_pessoa else "")
    
    y -= 30
    
    c.setFont("Helvetica", 11)
    c.drawString(50, y, "Depósitos Negociados:")
    c.setFont("Helvetica-Bold", 11)
    c.drawString(165, y, "R$")
    c.drawString(180, y, str(reserva.valor_total) if reserva.valor_total else "")
    
    c.setFont("Helvetica", 11)
    c.drawString(320, y, "Depósitos Confirmados:")
    c.setFont("Helvetica-Bold", 11)
    c.drawString(440, y, "R$")
    c.drawString(455, y, str(reserva.depositos_confirmados) if reserva.depositos_confirmados else "")
    
    y -= 30
    
    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, y, "*Despesas extras poderão ser parceladas em até 3 vezes via cartão.")
    

    y -= 20
    
    # Linha separadora após esse bloco
    c.setStrokeColor(cinza_claro)
    c.setLineWidth(1)
    c.line(50, y, width - 50, y)
    y -= 30
    
    
    c.setFont("Helvetica", 11)
    c.drawString(50, y, f"Número do {reserva.tipo_reserva}:")
    c.setFont("Helvetica-Bold", 11)
    c.drawString(150, y, reserva.id_reserva if reserva.id_reserva else "")
    
    c.setFont("Helvetica", 11)
    c.drawString(210, y, "Confirmado por:")
    c.setFont("Helvetica-Bold", 11)
    c.drawString(295, y, reserva.confirmada_por if reserva.confirmada_por else "")
    
    c.setFont("Helvetica", 11)
    c.drawString(420, y, "Data da Reserva:")
    c.setFont("Helvetica-Bold", 11)
    data_formatada = reserva.data_reserva.strftime("%d/%m/%Y")
    c.drawString(510, y, data_formatada)

    
    
    y -= 20
    
    # Linha separadora após esse bloco
    c.setStrokeColor(cinza_claro)
    c.setLineWidth(1)
    c.line(50, y, width - 50, y)
    y -= 30

    # Separador
    y -= 10
    c.line(50, y, width - 50, y)
    y -= 40

    # Mensagem final
    c.setFont("Helvetica-Oblique", 11)
    c.setFillColor(colors.black)
    c.drawString(50, y, "Agradecemos por escolher a Coutinho Excursões!")
    y -= 20
    c.drawString(50, y, "Desejamos uma ótima experiência e uma excelente viagem.")

    # Rodapé
    logo_rodape_path = 'app/static/assets/imagens/logo_reserva_segura.png'

    # Posicionando a imagem no rodapé
    c.drawImage(logo_rodape_path, width - 200, 20, width=250, height=80, preserveAspectRatio=True, mask='auto')


    # Finalização
    c.showPage()

    # --- Segunda página ---
    # Logo da hospedagem (à esquerda)
    if logo_hospedagem_path:
        c.drawImage(logo_hospedagem_path, 50, margin_top, width=logo_width, height=logo_height, preserveAspectRatio=True, mask='auto')

    # Logo Coutinho (à direita)
    c.drawImage(logo_coutinho_path, width - logo_width - 50, margin_top, width=logo_width, height=logo_height, preserveAspectRatio=True, mask='auto')

    # Cabeçalho centralizado entre as logos
    data_geracao = datetime.now().strftime("%d/%m/%Y")
    hora_geracao = datetime.now().strftime("%H:%M")

    title_x = 220  # Posição horizontal do texto centralizado
    title_y = margin_top + 35  # vertical no meio das logos

    c.setFont("Helvetica-Bold", 18)
    c.setFillColor(azul_escuro)
    c.drawString(title_x, title_y, f"VOUCHER {numero_reserva}")

    c.setFont("Helvetica", 10)
    c.setFillColor(colors.black)
    c.drawString(title_x, title_y - 15, f"Emitido em {data_geracao} às {hora_geracao}")
    
    # Linha separadora abaixo da logo e texto
    linha_y = margin_top - 10
    c.setStrokeColor(cinza_claro)
    c.setLineWidth(1)
    c.line(50, linha_y, width - 50, linha_y)

    # Começa o conteúdo depois da logo e linha
    y = linha_y - 30

    # --- Conteúdo formatado ---
    texto = """
    Serviços Prestados

    Inclusos na diária: café da manhã, almoço, jantar, conjunto de piscinas, piscinas cobertas, banho de lama negra, ofurô ao ar livre, circuito de relaxamento, quadras para prática de esportes, espaços temáticos (empório do chá, chimarródromo, casa da mamadeira, casa da Turma da Jureminha), recreações monitoradas com passeios ecológicos, jogos esportivos, caminhadas orientadas, trilhas e programação noturna.

    Não inclusos na diária: Procedimentos do SPA e os demais serviços extras, como: bebidas, porções, jogos e passeios para os quais são exigidas fichas (cavalo, charretes, pedalinho, carrinho de passeio, bicicletas, jogos eletrônicos, arborismo e tirolesa).

    Política de cancelamento:

    A devolução de valores somente ocorrerá quando comprovado questões de caso fortuito ou força maior, no restante somente através de carta de crédito utilizados junto ao Jurema Águas Quentes.

    Considerando o início do pacote ou diária, o valor pago será restituído através de uma carta de crédito para uso em 180 dias, condicionada aos seguintes prazos:

    1 - Desistência e cancelamento efetivados até 15 dias antecedentes à entrada, ficará com crédito do valor integral.

    2 - Desistência e cancelamento efetivados entre 14 e 7 dias antecedentes à entrada, ficará com crédito de 70% do valor pago.

    3 - Desistência e cancelamento efetivados 06 dias antecedentes à entrada, NÃO HAVERÁ DIREITO A QUALQUER TIPO DE RESTITUIÇÃO DO VALOR PAGO.

    4 - Quando ocorrer devolução de valores pagos através de cartão, deverão ser observadas as taxas financeiras cobradas pelas operadoras, mais os impostos decorrentes da transação.

    5 - A devolução de valores somente ocorrerá quando comprovado questões de caso fortuito ou força maior, no restante somente através de carta de crédito utilizados junto ao Jurema Águas Quentes.

    Informações Adicionais:

    A reserva estará garantida até a data e horários combinados acima, quando não houver a garantia de NO-SHOW, após este horário o apartamento estará disponível para a venda.

    É imprescindível a apresentação dos documentos de identificação originais com foto no ato do check-in.

    É obrigatório para menores de 18 anos a apresentação do RG ou Certidão de Nascimento no momento do check-in, quando na presença dos pais. Caso esteja desacompanhado ou na companhia de terceiros é obrigatória autorização do Juizado da Infância e Adolescência. Lei 8.069/90 Arts. 82 e 250.
    """

    y = height - 120
    left_margin = 50
    right_margin = width - 50

    linhas = texto.strip().split("\n")
    titulos = ["Serviços Prestados", "Política de cancelamento:", "Informações Adicionais:"]

    for linha in linhas:
        linha = linha.strip()
        if not linha:
            y -= 6
            continue

        # Verifica se é um título
        if linha in titulos:
            if y < 100:
                c.showPage()
                y = height - 100

            # Título
            c.setFont("Helvetica-Bold", 10)
            c.setFillColor(colors.black)
            c.drawString(left_margin, y, linha)
            y -= 20

            # Retorna à fonte normal
            c.setFont("Helvetica", 8)
            continue

        # Texto comum
        sublinhas = simpleSplit(linha, "Helvetica", 8, right_margin - left_margin)
        for sublinha in sublinhas:
            if y < 80:
                c.showPage()
                y = height - 100
                c.setFont("Helvetica", 8)
            c.drawString(left_margin, y, sublinha)
            y -= 14
        

    # Linha separadora
    c.setStrokeColor(colors.black)
    c.setLineWidth(0.5)
    y -= 10
    c.line(left_margin, y, right_margin, y)
    y -= 15
    
    # Linha separadora
    c.setStrokeColor(colors.black)
    c.setLineWidth(0.5)
    y -= 10
    c.line(left_margin, y, right_margin, y)
    y -= 15

    # Mensagem final
    c.setFont("Helvetica-Oblique", 11)
    c.setFillColor(colors.black)
    c.drawString(50, y, "Agradecemos por escolher a Coutinho Excursões!")
    y -= 20
    c.drawString(50, y, "Desejamos uma ótima experiência e uma excelente viagem.")

    # Rodapé
    logo_rodape_path = 'app/static/assets/imagens/logo_reserva_segura.png'

    # Posicionando a imagem no rodapé
    c.drawImage(logo_rodape_path, width - 200, 20, width=250, height=80, preserveAspectRatio=True, mask='auto')

    # Finalização
    c.showPage()
    c.save()



    buffer.seek(0)
    response.data = buffer.getvalue()
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=voucher_{reserva.id}.pdf'
    return response
