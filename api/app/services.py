from typing import Optional, List
from uuid import UUID, uuid4
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException
from datetime import datetime, timedelta, timezone
import math

from . import models, schemas
from .metrics import precisao, dashboard, limites_periodo, session_seconds, block_seconds
from .clock import utcnow, local_date, month_bounds, TZ
from .planning_models import Planejamento


# ==========================================================
# UTILIDADES INTERNAS
# ==========================================================

def _normalizar(valor, minimo, maximo):
    if maximo - minimo == 0:
        return 0
    return (valor - minimo) / (maximo - minimo)

def _calcular_ipr_simulado(simulado):
    return precisao([simulado])


def _obter_data_inicio(periodo):
    return limites_periodo(periodo)[0]



def _obter_data_anterior(periodo: str, data_inicio: datetime) -> datetime:
    """Retorna o início do período anterior para comparação de tendência."""
    if periodo == "semana":
        return data_inicio - timedelta(days=7)

    if periodo == "mes":
        # primeiro dia do mês anterior
        ultimo_dia_mes_anterior = data_inicio - timedelta(days=1)
        return ultimo_dia_mes_anterior.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    if periodo == "ano":
        # primeiro dia do ano anterior
        return data_inicio.replace(year=data_inicio.year - 1)

    # "todos" ou qualquer outro: sem período anterior definido
    return data_inicio



def _calcular_ipr_bloco(bloco):
    return precisao([bloco])



def _calcular_tendencia(ipr_atual: float, ipr_anterior: float) -> str:
    if ipr_anterior == 0:
        return "ESTÁVEL"

    variacao = ((ipr_atual - ipr_anterior) / ipr_anterior) * 100

    if variacao > 5:
        return "ASCENDENTE"
    elif variacao < -5:
        return "DECLÍNIO"
    return "ESTÁVEL"

def _calcular_status_missao(
    ipr_medio: float,
    status_horas: str,
    status_questoes: str,
    tendencia: str
) -> str:
    """
    Status da missão é composto por 4 critérios independentes.
    Todos precisam estar minimamente OK para ser 'MISSÃO CUMPRIDA'.
    """
    pontos = 0

    # 1. IPR (peso maior — qualidade é o principal indicador)
    if ipr_medio >= 0.75:
        pontos += 3
    elif ipr_medio >= 0.70:
        pontos += 2
    elif ipr_medio >= 0.60:
        pontos += 1
    # abaixo de 0.60 = 0 pontos

    # 2. Horas
    if status_horas == "DENTRO" or status_horas == "ACIMA":
        pontos += 2
    elif status_horas == "ABAIXO":
        pontos += 0

    # 3. Questões
    if status_questoes == "DENTRO" or status_questoes == "ACIMA":
        pontos += 2
    elif status_questoes == "ABAIXO":
        pontos += 0

    # 4. Tendência
    if tendencia == "ASCENDENTE":
        pontos += 2
    elif tendencia == "ESTÁVEL":
        pontos += 1
    elif tendencia == "DECLÍNIO":
        pontos += 0

    # Máximo possível: 9 pontos
    # Missão Cumprida exige IPR mínimo ok (>=0.70) + pelo menos 6 pontos no total
    ipr_minimo_ok = ipr_medio >= 0.70
    if ipr_minimo_ok and pontos >= 6:
        return "MISSÃO CUMPRIDA"
    elif pontos >= 5:
        return "EXECUÇÃO PARCIAL"
    else:
        return "EXECUÇÃO INSUFICIENTE"

# ==========================================================
# SESSÃO DE ESTUDO
# ==========================================================

def registrar_sessao_estudo(db, payload):
    from .planner import validar_assunto, active_cycle_for_date
    validar_assunto(db, payload.materia_id, payload.assunto_id)
    state = db.get(Planejamento, 1, with_for_update=True)
    db_obj = models.SessaoEstudo(**payload.model_dump())
    db_obj.ciclo_id = active_cycle_for_date(db, payload.data, state)
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj



def listar_sessoes(db: Session, skip: int = 0, limit: int = 100):
    return (
        db.query(models.SessaoEstudo)
        .order_by(models.SessaoEstudo.data.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def calcular_horas_periodo(db, periodo, materia_id=None):
    return dashboard(db, periodo, materia_id)["horas_liquidas"]



# ==========================================================
# BLOCO DE QUESTÕES
# ==========================================================

def registrar_bloco_questoes(db, payload):
    from .planner import validar_assunto, active_cycle_for_date
    validar_assunto(db, payload.materia_id, payload.assunto_id)
    state = db.get(Planejamento, 1, with_for_update=True)
    db_obj = models.BlocoQuestoes(**payload.model_dump())
    db_obj.ciclo_id = active_cycle_for_date(db, payload.data, state)
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj



def listar_blocos(db: Session, skip: int = 0, limit: int = 100):
    return (
        db.query(models.BlocoQuestoes)
        .order_by(models.BlocoQuestoes.data.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


# ==========================================================
# DASHBOARD INTELIGENTE
# ==========================================================

def get_dashboard(db, periodo="semana", materia_id=None):
    return dashboard(db, periodo, materia_id)

def get_estatisticas_filtradas(db, periodo="semana", materia_id=None):
    return dashboard(db, periodo, materia_id)


def criar_materia(db: Session, payload: schemas.MateriaCreate):
    """
    Cria uma nova matéria no banco de dados.

    Validações:
    - O nome deve ser único (case-insensitive).
    """
    db.get(Planejamento, 1, with_for_update=True)
    nome_normalizado = payload.nome.strip()

    existente = (
        db.query(models.Materia)
        .filter(func.lower(models.Materia.nome) == nome_normalizado.lower())
        .first()
    )

    if existente:
        raise HTTPException(
            status_code=400,
            detail=f"Matéria '{nome_normalizado}' já existe."
        )

    db_obj = models.Materia(
        nome=nome_normalizado,
        peso_prova=payload.peso_prova
    )

    try:
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Erro ao criar matéria.")


def criar_assunto(db: Session, payload: schemas.AssuntoCreate):
    """
    Cria um novo assunto vinculado a uma matéria existente.

    Validações:
    - A matéria referenciada deve existir.
    - Não pode haver outro assunto com o mesmo nome para a mesma matéria.
    """
    materia = (
        db.query(models.Materia)
        .filter(models.Materia.id == payload.materia_id)
        .first()
    )

    if not materia:
        raise HTTPException(
            status_code=404,
            detail="Matéria não encontrada."
        )

    db.get(Planejamento, 1, with_for_update=True)
    nome_normalizado = payload.nome.strip()

    existente = (
        db.query(models.Assunto)
        .filter(
            models.Assunto.materia_id == payload.materia_id,
            func.lower(models.Assunto.nome) == nome_normalizado.lower()
        )
        .first()
    )

    if existente:
        raise HTTPException(
            status_code=400,
            detail=f"Assunto '{nome_normalizado}' já existe para esta matéria."
        )

    db_obj = models.Assunto(
        materia_id=payload.materia_id,
        nome=nome_normalizado,
        semana_do_ciclo=payload.semana_do_ciclo
    )

    try:
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Erro ao criar assunto.")


def listar_materias(db):
    return db.query(models.Materia).filter(models.Materia.ativa.is_(True)).order_by(models.Materia.nome).all()



def listar_assuntos(db, materia_id=None, skip=0, limit=None):
    query = db.query(models.Assunto).filter(models.Assunto.ativo.is_(True))
    if materia_id:
        query = query.filter(models.Assunto.materia_id == materia_id)
    query = query.order_by(models.Assunto.ordem, models.Assunto.nome, models.Assunto.id).offset(skip)
    return query.limit(limit).all() if limit is not None else query.all()



def listar_assuntos_por_materia(db, materia_id):
    return listar_assuntos(db, materia_id)



def registrar_simulado(db: Session, payload: schemas.SimuladoSemanalCreate):
    db_obj = models.SimuladoSemanal(**payload.model_dump())

    try:
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Erro ao registrar simulado.")
    

def listar_simulados(db: Session, skip: int = 0, limit: int = 100):
    return (
        db.query(models.SimuladoSemanal)
        .order_by(models.SimuladoSemanal.criado_em.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

#=========================================================
# Readação
#=========================================================

# -----------------------------------------
# CÁLCULOS
# -----------------------------------------

def calcular_nota_total(c1: int, c2: int, c3: int, c4: int, c5: int) -> int:
    return c1 + c2 + c3 + c4 + c5


def identificar_competencia_mais_fraca(c1, c2, c3, c4, c5):

    competencias = {
        1: c1,
        2: c2,
        3: c3,
        4: c4,
        5: c5
    }

    return min(competencias, key=competencias.get)


def calcular_status(nota: int) -> str:

    if nota < 400:
        return "Crítica"

    if nota < 600:
        return "Fraca"

    if nota < 700:
        return "Regular"

    if nota < 800:
        return "Boa"

    if nota < 900:
        return "Muito Boa"

    return "Excelente"


# -----------------------------------------
# DIAGNÓSTICO
# -----------------------------------------

def gerar_diagnostico(competencia: int, nota: int) -> str:

    # Competência 1 — norma culta
    if competencia == 1:

        if nota <= 80:
            return "A redação apresenta muitos desvios graves da norma culta, comprometendo a clareza e a formalidade do texto."

        if nota <= 140:
            return "Há desvios ocasionais da norma culta que prejudicam parcialmente a qualidade linguística."

        return "A norma culta está bem aplicada, com poucos desvios pontuais."


    # Competência 2 — compreensão do tema
    if competencia == 2:

        if nota <= 80:
            return "A redação demonstra compreensão insuficiente da proposta temática."

        if nota <= 140:
            return "A abordagem do tema está parcialmente adequada, mas ainda superficial."

        return "O tema foi bem compreendido, embora possa ser aprofundado."


    # Competência 3 — argumentação
    if competencia == 3:

        if nota <= 80:
            return "A argumentação é fraca ou pouco estruturada, com ideias pouco desenvolvidas."

        if nota <= 140:
            return "Os argumentos existem, mas ainda carecem de aprofundamento e exemplificação."

        return "A argumentação é consistente, mas pode ganhar maior densidade analítica."


    # Competência 4 — coesão
    if competencia == 4:

        if nota <= 80:
            return "O texto apresenta problemas significativos de coesão e organização das ideias."

        if nota <= 140:
            return "A progressão textual ocorre, mas com limitações no uso de conectivos."

        return "A coesão textual é adequada, com pequenas oportunidades de melhoria."


    # Competência 5 — intervenção
    if competencia == 5:

        if nota <= 80:
            return "A proposta de intervenção é incompleta ou pouco clara."

        if nota <= 140:
            return "A intervenção é válida, mas ainda carece de detalhamento."

        return "A proposta de intervenção é adequada, podendo apenas ganhar maior especificidade."


    return ""


# -----------------------------------------
# RECOMENDAÇÕES
# -----------------------------------------

def gerar_recomendacao(competencia: int, nota: int) -> str:

    # Competência 1 — norma culta
    if competencia == 1:

        if nota <= 80:
            return "Estude gramática básica com foco em concordância, regência e pontuação."

        if nota <= 140:
            return "Revise regras de pontuação e concordância para reduzir pequenos desvios."

        return "Faça revisões finais focando em refinamento da norma culta."


    # Competência 2 — compreensão do tema
    if competencia == 2:

        if nota <= 80:
            return "Treine interpretação de temas e pratique identificar o problema central da proposta."

        if nota <= 140:
            return "Antes de escrever, destaque palavras-chave do tema e delimite o problema da redação."

        return "Aprofunde a abordagem temática com recortes mais específicos."


    # Competência 3 — argumentação
    if competencia == 3:

        if nota <= 80:
            return "Treine construção de argumentos claros usando causa, consequência e exemplificação."

        if nota <= 140:
            return "Utilize repertório sociocultural e desenvolva melhor os exemplos nos parágrafos."

        return "Refine a densidade argumentativa com repertórios mais sofisticados."


    # Competência 4 — coesão
    if competencia == 4:

        if nota <= 80:
            return "Estude conectivos básicos e pratique a ligação entre frases e parágrafos."

        if nota <= 140:
            return "Amplie o uso de conectivos variados para melhorar a progressão textual."

        return "Aprimore a fluidez textual variando mecanismos de coesão."


    # Competência 5 — intervenção
    if competencia == 5:

        if nota <= 80:
            return "Treine a estrutura completa da intervenção: agente, ação, meio, modo e finalidade."

        if nota <= 140:
            return "Detalhe melhor os elementos da intervenção para torná-la mais concreta."

        return "Aprimore a viabilidade e detalhamento da proposta de intervenção."


    return ""


# -----------------------------------------
# CRIAR REDAÇÃO
# -----------------------------------------


def criar_redacao(db: Session, payload: schemas.RedacaoRequest) -> models.Redacao:

    # -----------------------------
    # suas variáveis originais
    # -----------------------------

    c1 = payload.competencia1
    c2 = payload.competencia2
    c3 = payload.competencia3
    c4 = payload.competencia4
    c5 = payload.competencia5

    notas = [c1, c2, c3, c4, c5]

    nota_total = sum(notas)

    competencia_mais_fraca = notas.index(min(notas)) + 1

    status = models.calcular_status(nota_total)

    empatadas = [str(i + 1) for i, nota in enumerate(notas) if nota == min(notas)]
    diagnostico = "Menor nota registrada nas competências: " + ", ".join(empatadas) + ". Avaliação ENEM; não equivale à rubrica EsPCEx."
    atividades = ["revisar os desvios de linguagem apontados na correção", "conferir atendimento ao tema e ao tipo textual", "reescrever um argumento com explicação e evidência", "revisar a ligação entre frases e parágrafos", "conferir agente, ação, meio e detalhamento da intervenção"]
    recomendacao = "Use os comentários da correção para " + atividades[competencia_mais_fraca - 1] + "."
    if min(notas) == 200:
        diagnostico = "Todas as competências têm a nota máxima registrada na rubrica ENEM."
        recomendacao = "Pratique outra proposta e confira a correção; esta nota não prova domínio permanente."

    # -----------------------------
    # criar redação
    # -----------------------------

    redacao = models.Redacao(
        id=uuid4(),
        tema=payload.tema,
        eixo_tematico=payload.eixo_tematico or "geral",
        tempo_escrita_min=payload.tempo_escrita_min,
        observacoes=payload.observacoes,
        repertorios=payload.repertorios,
        data_escrita=datetime.utcnow(),
        criado_em=datetime.utcnow()
    )

    db.add(redacao)
    db.flush()  # gera id da redação

    # -----------------------------
    # salvar competências
    # -----------------------------

    competencias = [
        (1, c1),
        (2, c2),
        (3, c3),
        (4, c4),
        (5, c5),
    ]

    for numero, nota in competencias:

        comp = models.CompetenciaRedacao(
            id=uuid4(),
            redacao_id=redacao.id,
            competencia=numero,
            nota=nota
        )

        db.add(comp)

    # -----------------------------
    # salvar análise
    # -----------------------------

    analise = models.AnaliseRedacao(
        id=uuid4(),
        redacao_id=redacao.id,
        nota_total=nota_total,
        status=status,
        competencia_mais_fraca=competencia_mais_fraca,
        diagnostico=diagnostico,
        recomendacao=recomendacao,
        criado_em=datetime.utcnow()
    )

    db.add(analise)

    # -----------------------------
    # salvar tudo
    # -----------------------------

    db.commit()
    db.refresh(redacao)

    competencias = {c.competencia: c.nota for c in redacao.competencias}

    return {
        "id": redacao.id,
        "tema": redacao.tema,
        "eixo_tematico": redacao.eixo_tematico,

        "tempo_escrita_min": redacao.tempo_escrita_min,
        "observacoes": redacao.observacoes,
        "repertorios": redacao.repertorios,

        "competencia1": competencias.get(1),
        "competencia2": competencias.get(2),
        "competencia3": competencias.get(3),
        "competencia4": competencias.get(4),
        "competencia5": competencias.get(5),

        "nota_total": redacao.analise.nota_total,
        "status": redacao.analise.status,
        "competencia_mais_fraca": redacao.analise.competencia_mais_fraca,
        "diagnostico": redacao.analise.diagnostico,
        "recomendacao": redacao.analise.recomendacao,

        "data_escrita": redacao.data_escrita,
        "criado_em": redacao.criado_em
    }


# -----------------------------------------
# BUSCAR REDAÇÃO
# -----------------------------------------

def buscar_redacao(db: Session, redacao_id: str) -> schemas.RedacaoResponse | None:

    redacao = db.query(models.Redacao).filter(
        models.Redacao.id == redacao_id
    ).first()

    if not redacao:
        return None

    competencias = {c.competencia: c.nota for c in redacao.competencias}

    data = {
        "id": redacao.id,
        "tema": redacao.tema,
        "eixo_tematico": redacao.eixo_tematico,

        "tempo_escrita_min": redacao.tempo_escrita_min,
        "observacoes": redacao.observacoes,
        "repertorios": redacao.repertorios,

        "competencia1": competencias.get(1),
        "competencia2": competencias.get(2),
        "competencia3": competencias.get(3),
        "competencia4": competencias.get(4),
        "competencia5": competencias.get(5),

        "nota_total": redacao.analise.nota_total,
        "status": redacao.analise.status,
        "competencia_mais_fraca": redacao.analise.competencia_mais_fraca,
        "diagnostico": redacao.analise.diagnostico,
        "recomendacao": redacao.analise.recomendacao,

        "data_escrita": redacao.data_escrita,
        "criado_em": redacao.criado_em
    }

    return schemas.RedacaoResponse.model_validate(data)


# -----------------------------------------
# LISTAR REDAÇÕES
# -----------------------------------------

def listar_redacoes(db: Session) -> List[schemas.RedacaoResponse]:

    redacoes = db.query(models.Redacao).order_by(
        models.Redacao.data_escrita.desc()
    ).all()

    resultado = []

    for redacao in redacoes:

        competencias = {c.competencia: c.nota for c in redacao.competencias}

        data = {
            "id": redacao.id,
            "tema": redacao.tema,
            "eixo_tematico": redacao.eixo_tematico,

            "tempo_escrita_min": redacao.tempo_escrita_min,
            "observacoes": redacao.observacoes,
            "repertorios": redacao.repertorios,

            "competencia1": competencias.get(1),
            "competencia2": competencias.get(2),
            "competencia3": competencias.get(3),
            "competencia4": competencias.get(4),
            "competencia5": competencias.get(5),

            "nota_total": redacao.analise.nota_total,
            "status": redacao.analise.status,
            "competencia_mais_fraca": redacao.analise.competencia_mais_fraca,
            "diagnostico": redacao.analise.diagnostico,
            "recomendacao": redacao.analise.recomendacao,

            "data_escrita": redacao.data_escrita,
            "criado_em": redacao.criado_em
        }

        resultado.append(
            schemas.RedacaoResponse.model_validate(data)
        )

    return resultado

###RELATORIO MENSAL

# ============================================================
# COLAR NO FINAL DE services.py
# ============================================================

import calendar as cal_module
from collections import defaultdict


# ==========================================================
# RELATÓRIO MENSAL COMPLETO
# ==========================================================

def gerar_relatorio_mensal(db: Session, mes: int, ano: int) -> dict:
    """
    Gera o relatório mensal completo de performance acadêmica.

    Agrega TODOS os dados disponíveis no sistema para o mês/ano
    informado e calcula métricas, comparativos, projeções e
    recomendações estratégicas.
    """

    # ----------------------------------------------------------
    # 0. PERÍODO DE ANÁLISE
    # ----------------------------------------------------------

    dias_no_mes = cal_module.monthrange(ano, mes)[1]

    data_inicio, fim_calendario = month_bounds(ano, mes)
    data_fim = min(fim_calendario, utcnow())
    if data_inicio > data_fim:
        raise HTTPException(422, "Selecione o mês atual ou um mês anterior.")

    # Período anterior (mês anterior)
    if mes == 1:
        mes_ant, ano_ant = 12, ano - 1
    else:
        mes_ant, ano_ant = mes - 1, ano

    dias_mes_ant = cal_module.monthrange(ano_ant, mes_ant)[1]
    data_inicio_ant, data_fim_ant = month_bounds(ano_ant, mes_ant)
    data_fim_ant = min(data_fim_ant, data_inicio_ant + (data_fim - data_inicio))

    # ----------------------------------------------------------
    # 1. CARREGAR DADOS DO MÊS ATUAL
    # ----------------------------------------------------------

    sessoes: list[models.SessaoEstudo] = (
        db.query(models.SessaoEstudo)
        .filter(models.SessaoEstudo.data >= data_inicio,
                models.SessaoEstudo.data < data_fim)
        .all()
    )

    blocos: list[models.BlocoQuestoes] = (
        db.query(models.BlocoQuestoes)
        .filter(models.BlocoQuestoes.data >= data_inicio,
                models.BlocoQuestoes.data < data_fim)
        .all()
    )

    simulados: list[models.SimuladoSemanal] = (
        db.query(models.SimuladoSemanal)
        .filter(models.SimuladoSemanal.criado_em >= data_inicio,
                models.SimuladoSemanal.criado_em < data_fim)
        .all()
    )

    redacoes: list[models.Redacao] = (
        db.query(models.Redacao)
        .filter(models.Redacao.data_escrita >= data_inicio,
                models.Redacao.data_escrita < data_fim)
        .all()
    )

    provas: list[models.ProvaOficial] = (
        db.query(models.ProvaOficial)
        .filter(models.ProvaOficial.criado_em >= data_inicio,
                models.ProvaOficial.criado_em < data_fim)
        .all()
    )

    # Carregar erros de todos os blocos do mês (1 query só)
    bloco_ids = [b.id for b in blocos]
    erros_blocos: list[models.ErroQuestao] = []
    if bloco_ids:
        erros_blocos = (
            db.query(models.ErroQuestao)
            .filter(models.ErroQuestao.bloco_id.in_(bloco_ids))
            .all()
        )

    # Carregar matérias e assuntos para lookup sem N+1
    materias_map: dict = {
        m.id: m for m in db.query(models.Materia).all()
    }
    assuntos_map: dict = {
        a.id: a for a in db.query(models.Assunto).all()
    }

    # ----------------------------------------------------------
    # 2. DADOS DO MÊS ANTERIOR (para comparativo)
    # ----------------------------------------------------------

    sessoes_ant = (
        db.query(models.SessaoEstudo)
        .filter(models.SessaoEstudo.data >= data_inicio_ant,
                models.SessaoEstudo.data < data_fim_ant)
        .all()
    )

    blocos_ant = (
        db.query(models.BlocoQuestoes)
        .filter(models.BlocoQuestoes.data >= data_inicio_ant,
                models.BlocoQuestoes.data < data_fim_ant)
        .all()
    )

    simulados_ant = (
        db.query(models.SimuladoSemanal)
        .filter(models.SimuladoSemanal.criado_em >= data_inicio_ant,
                models.SimuladoSemanal.criado_em < data_fim_ant)
        .all()
    )

    redacoes_ant = (
        db.query(models.Redacao)
        .filter(models.Redacao.data_escrita >= data_inicio_ant,
                models.Redacao.data_escrita < data_fim_ant)
        .all()
    )

    # Do not manufacture corrected values for invalid legacy records.
    from .metrics import valid_questions
    if any(not valid_questions(x) for x in blocos + simulados + blocos_ant + simulados_ant):
        raise HTTPException(422, "Há registros antigos com acertos/questões inválidos neste período ou no comparativo. Corrija-os no Histórico para gerar o relatório; nenhum dado foi alterado automaticamente.")

    # ----------------------------------------------------------
    # 3. HELPERS INTERNOS
    # ----------------------------------------------------------

    def _pct(acertos, total):
        return round((acertos / total) * 100, 2) if total > 0 else 0.0

    def _safe_avg(values):
        filtered = [v for v in values if v is not None]
        return round(sum(filtered) / len(filtered), 2) if filtered else None

    def _ipr_blocos_lista(lista):
        return precisao(lista)

    def _ipr_simulados_lista(lista):
        return precisao(lista)

    def _ipr_combinado(lista_blocos, lista_simulados):
        return precisao(lista_blocos + lista_simulados)

    # ----------------------------------------------------------
    # 4. PERÍODO — dias estudados
    # ----------------------------------------------------------

    datas_com_atividade = set()
    for s in sessoes:
        datas_com_atividade.add(local_date(s.data))
    for b in blocos:
        datas_com_atividade.add(local_date(b.data))
    for sim in simulados:
        datas_com_atividade.add(local_date(sim.criado_em))

    dias_estudados = len(datas_com_atividade)

    periodo = {
        "mes_referencia": mes,
        "ano_referencia": ano,
        "data_inicio": data_inicio.isoformat(),
        "data_fim": data_fim.isoformat(),
        "dias_no_mes": dias_no_mes,
        "dias_estudados": dias_estudados,
    }

    # ----------------------------------------------------------
    # 5. RESUMO GERAL
    # ----------------------------------------------------------

    total_min_sessoes = sum(session_seconds(s) / 60 for s in sessoes)
    total_seg_blocos = sum(block_seconds(b) for b in blocos)
    total_seg_simulados = sum(s.tempo_total_segundos for s in simulados)
    horas_totais = round(
        (total_min_sessoes + total_seg_blocos / 60 + total_seg_simulados / 60) / 60, 2
    )

    total_questoes_blocos = sum(b.total_questoes for b in blocos)
    total_acertos_blocos = sum(b.total_acertos for b in blocos)
    total_questoes_simulados = sum(s.total_questoes for s in simulados)
    total_acertos_simulados = sum(s.total_acertos for s in simulados)

    total_questoes = total_questoes_blocos + total_questoes_simulados
    total_acertos = total_acertos_blocos + total_acertos_simulados
    total_erros = total_questoes - total_acertos

    ipr_geral = _ipr_combinado(blocos, simulados)

    resumo_geral = {
        "horas_totais": horas_totais,
        "total_sessoes": len(sessoes),
        "total_blocos": len(blocos),
        "total_simulados": len(simulados),
        "total_questoes_respondidas": total_questoes,
        "total_acertos": total_acertos,
        "total_erros": total_erros,
        "percentual_acerto_geral": _pct(total_acertos, total_questoes),
        "ipr_geral": round(ipr_geral * 100, 2),
        "media_questoes_por_dia": round(total_questoes / dias_estudados, 1) if dias_estudados else 0,
        "media_minutos_estudo_por_dia": round(
            (total_min_sessoes + total_seg_blocos / 60 + total_seg_simulados / 60) / dias_estudados, 1
        ) if dias_estudados else 0,
        "dias_estudados": dias_estudados,
        "percentual_dias_estudados": round((dias_estudados / dias_no_mes) * 100, 1),
    }

    # ----------------------------------------------------------
    # 6. SESSÕES
    # ----------------------------------------------------------

    # Por tipo
    sessoes_por_tipo = defaultdict(lambda: {"quantidade": 0, "total_minutos": 0, "focos": [], "energias": []})
    for s in sessoes:
        t = s.tipo_sessao
        sessoes_por_tipo[t]["quantidade"] += 1
        sessoes_por_tipo[t]["total_minutos"] += session_seconds(s) / 60
        if s.nivel_foco:
            sessoes_por_tipo[t]["focos"].append(s.nivel_foco)
        if s.nivel_energia:
            sessoes_por_tipo[t]["energias"].append(s.nivel_energia)

    total_min_todos = sum(session_seconds(s) / 60 for s in sessoes) or 1
    sessoes_tipo_lista = []
    for tipo, dados in sessoes_por_tipo.items():
        sessoes_tipo_lista.append({
            "tipo_sessao": tipo,
            "quantidade": dados["quantidade"],
            "total_minutos": dados["total_minutos"],
            "percentual_do_total": round((dados["total_minutos"] / total_min_todos) * 100, 1),
            "media_foco": _safe_avg(dados["focos"]),
            "media_energia": _safe_avg(dados["energias"]),
        })

    # Por matéria
    sessoes_por_materia = defaultdict(lambda: {
        "total_sessoes": 0, "total_minutos": 0, "focos": [], "energias": []
    })
    for s in sessoes:
        mid = s.materia_id
        sessoes_por_materia[mid]["total_sessoes"] += 1
        sessoes_por_materia[mid]["total_minutos"] += session_seconds(s) / 60
        if s.nivel_foco:
            sessoes_por_materia[mid]["focos"].append(s.nivel_foco)
        if s.nivel_energia:
            sessoes_por_materia[mid]["energias"].append(s.nivel_energia)

    total_min_mat = sum(v["total_minutos"] for v in sessoes_por_materia.values()) or 1
    sessoes_materia_lista = []
    for mid, dados in sessoes_por_materia.items():
        mat = materias_map.get(mid)
        sessoes_materia_lista.append({
            "materia_id": str(mid),
            "materia_nome": mat.nome if mat else str(mid),
            "total_sessoes": dados["total_sessoes"],
            "total_minutos": dados["total_minutos"],
            "percentual_tempo": round((dados["total_minutos"] / total_min_mat) * 100, 1),
            "media_foco": _safe_avg(dados["focos"]),
            "media_energia": _safe_avg(dados["energias"]),
        })

    sessoes_dict = {
        "por_tipo": sessoes_tipo_lista,
        "por_materia": sessoes_materia_lista,
    }

    # ----------------------------------------------------------
    # 7. BLOCOS DE QUESTÕES
    # ----------------------------------------------------------

    # Por matéria
    blocos_por_materia = defaultdict(lambda: {
        "total_blocos": 0, "total_questoes": 0, "total_acertos": 0,
        "tempos_medios": [], "segundos": 0, "iprs": []
    })
    for b in blocos:
        mid = b.materia_id
        blocos_por_materia[mid]["total_blocos"] += 1
        blocos_por_materia[mid]["total_questoes"] += b.total_questoes
        blocos_por_materia[mid]["total_acertos"] += b.total_acertos
        blocos_por_materia[mid]["segundos"] += b.tempo_total_segundos
        blocos_por_materia[mid]["iprs"].append(_calcular_ipr_bloco(b))

    blocos_materia_lista = []
    for mid, dados in blocos_por_materia.items():
        mat = materias_map.get(mid)
        blocos_materia_lista.append({
            "materia_id": str(mid),
            "materia_nome": mat.nome if mat else str(mid),
            "total_blocos": dados["total_blocos"],
            "total_questoes": dados["total_questoes"],
            "total_acertos": dados["total_acertos"],
            "percentual_acerto": _pct(dados["total_acertos"], dados["total_questoes"]),
            "tempo_medio_por_questao": round(dados["segundos"] / dados["total_questoes"], 1) if dados["total_questoes"] else 0,
            "ipr_medio": _pct(dados["total_acertos"], dados["total_questoes"]),
        })

    # Por assunto
    blocos_por_assunto = defaultdict(lambda: {
        "total_blocos": 0, "total_questoes": 0, "total_acertos": 0, "iprs": []
    })
    for b in blocos:
        aid = b.assunto_id
        blocos_por_assunto[aid]["total_blocos"] += 1
        blocos_por_assunto[aid]["total_questoes"] += b.total_questoes
        blocos_por_assunto[aid]["total_acertos"] += b.total_acertos
        blocos_por_assunto[aid]["iprs"].append(_calcular_ipr_bloco(b))

    blocos_assunto_lista = []
    for aid, dados in blocos_por_assunto.items():
        assunto = assuntos_map.get(aid)
        mat = materias_map.get(assunto.materia_id) if assunto else None
        ipr_medio = dados["total_acertos"] / dados["total_questoes"] if dados["total_questoes"] else 0
        pct_acerto = _pct(dados["total_acertos"], dados["total_questoes"])
        status_assunto = (
            "AMOSTRA PEQUENA" if dados["total_questoes"] < 20 or dados["total_blocos"] < 2 else
            "REAVALIAR" if ipr_medio < 0.60 else
            "FRACO" if ipr_medio < 0.70 else
            "REGULAR" if ipr_medio < 0.80 else
            "BOM"
        )
        blocos_assunto_lista.append({
            "assunto_id": str(aid),
            "assunto_nome": assunto.nome if assunto else str(aid),
            "materia_id": str(assunto.materia_id) if assunto else None,
            "materia_nome": mat.nome if mat else None,
            "semana_do_ciclo": assunto.semana_do_ciclo if assunto else None,
            "total_blocos": dados["total_blocos"],
            "total_questoes": dados["total_questoes"],
            "total_acertos": dados["total_acertos"],
            "percentual_acerto": pct_acerto,
            "ipr_medio": round(ipr_medio * 100, 2),
            "status": status_assunto,
        })

    # Por dificuldade
    blocos_por_dif = defaultdict(lambda: {
        "total_blocos": 0, "total_questoes": 0, "total_acertos": 0, "iprs": []
    })
    for b in blocos:
        d = b.dificuldade
        blocos_por_dif[d]["total_blocos"] += 1
        blocos_por_dif[d]["total_questoes"] += b.total_questoes
        blocos_por_dif[d]["total_acertos"] += b.total_acertos
        blocos_por_dif[d]["iprs"].append(_calcular_ipr_bloco(b))

    blocos_dif_lista = []
    for dif in sorted(blocos_por_dif.keys()):
        dados = blocos_por_dif[dif]
        blocos_dif_lista.append({
            "dificuldade": dif,
            "total_blocos": dados["total_blocos"],
            "total_questoes": dados["total_questoes"],
            "total_acertos": dados["total_acertos"],
            "percentual_acerto": _pct(dados["total_acertos"], dados["total_questoes"]),
            "ipr_medio": _pct(dados["total_acertos"], dados["total_questoes"]),
        })

    blocos_dict = {
        "por_materia": blocos_materia_lista,
        "por_assunto": blocos_assunto_lista,
        "por_dificuldade": blocos_dif_lista,
    }

    # ----------------------------------------------------------
    # 8. ANÁLISE DE ERROS
    # ----------------------------------------------------------

    erros_por_tipo = defaultdict(lambda: {"total": 0, "blocos_ids": set()})
    for e in erros_blocos:
        erros_por_tipo[e.tipo_erro]["total"] += e.quantidade
        erros_por_tipo[e.tipo_erro]["blocos_ids"].add(e.bloco_id)

    total_erros_registrados = sum(v["total"] for v in erros_por_tipo.values()) or 1

    tipos_erro_lista = []
    for tipo, dados in sorted(erros_por_tipo.items(), key=lambda x: -x[1]["total"]):
        tipos_erro_lista.append({
            "tipo_erro": tipo,
            "total_ocorrencias": dados["total"],
            "percentual_do_total": round((dados["total"] / total_erros_registrados) * 100, 1),
            "blocos_afetados": len(dados["blocos_ids"]),
        })

    erros_distracao_pressa = sum(
        v["total"] for t, v in erros_por_tipo.items() if t in ("DISTRACAO", "PRESSA")
    )
    erros_conceito_calculo = sum(
        v["total"] for t, v in erros_por_tipo.items() if t in ("CONCEITO", "CALCULO")
    )

    # Tendência de erro: compara quantidade de erros/bloco vs mês anterior
    bloco_ids_ant = [b.id for b in blocos_ant]
    erros_blocos_ant = []
    if bloco_ids_ant:
        erros_blocos_ant = (
            db.query(models.ErroQuestao)
            .filter(models.ErroQuestao.bloco_id.in_(bloco_ids_ant))
            .all()
        )

    total_erros_ant = sum(e.quantidade for e in erros_blocos_ant)
    erros_por_bloco_atual = (
        sum(e.quantidade for e in erros_blocos) / len(blocos)
        if blocos else 0
    )
    erros_por_bloco_ant = (
        total_erros_ant / len(blocos_ant)
        if blocos_ant else 0
    )

    if erros_por_bloco_ant == 0:
        tendencia_erro = "SEM_DADOS_ANTERIORES"
    elif erros_por_bloco_atual > erros_por_bloco_ant * 1.1:
        tendencia_erro = "PIORANDO"
    elif erros_por_bloco_atual < erros_por_bloco_ant * 0.9:
        tendencia_erro = "MELHORANDO"
    else:
        tendencia_erro = "ESTÁVEL"

    erros_dict = {
        "total_erros_registrados": sum(e.quantidade for e in erros_blocos),
        "tipos_mais_comuns": tipos_erro_lista[:5],
        "todos_os_tipos": tipos_erro_lista,
        "taxa_erro_distracao_pressa": round(
            (erros_distracao_pressa / total_erros_registrados) * 100, 1
        ),
        "taxa_erro_conceito_calculo": round(
            (erros_conceito_calculo / total_erros_registrados) * 100, 1
        ),
        "tendencia_erro": tendencia_erro,
        "erros_por_bloco_atual": round(erros_por_bloco_atual, 2),
        "erros_por_bloco_mes_anterior": round(erros_por_bloco_ant, 2),
    }

    # ----------------------------------------------------------
    # 9. SIMULADOS
    # ----------------------------------------------------------

    simulados_detalhe = []
    for s in simulados:
        ipr_sim = _calcular_ipr_simulado(s)
        tempo_total = s.tempo_total_segundos
        tq = s.total_questoes

        desempenhos_sim = []
        if hasattr(s, 'desempenhos') and s.desempenhos:
            for d in s.desempenhos:
                mat = materias_map.get(d.materia_id)
                desempenhos_sim.append({
                    "materia_id": str(d.materia_id),
                    "materia_nome": mat.nome if mat else str(d.materia_id),
                    "total_questoes": d.total_questoes,
                    "total_acertos": d.total_acertos,
                    "percentual_acerto": _pct(d.total_acertos, d.total_questoes),
                    "tempo_total_segundos": d.tempo_total_segundos,
                })

        simulados_detalhe.append({
            "simulado_id": str(s.id),
            "numero_ciclo": s.numero_ciclo,
            "numero_semana": s.numero_semana,
            "total_questoes": tq,
            "total_acertos": s.total_acertos,
            "percentual_acerto": _pct(s.total_acertos, tq),
            "tempo_total_segundos": tempo_total,
            "tempo_medio_por_questao": round(tempo_total / tq, 1) if tq else 0,
            "ipr": round(ipr_sim * 100, 2),
            "nivel_ansiedade": s.nivel_ansiedade,
            "nivel_fadiga": s.nivel_fadiga,
            "qualidade_sono": s.qualidade_sono,
            "desempenhos_por_materia": desempenhos_sim,
            "criado_em": s.criado_em.isoformat(),
        })

    # ----------------------------------------------------------
    # 10. PROVAS OFICIAIS
    # ----------------------------------------------------------

    provas_detalhe = []
    for p in provas:
        desempenhos_prova = []
        if hasattr(p, 'desempenhos') and p.desempenhos:
            for d in p.desempenhos:
                mat = materias_map.get(d.materia_id)
                desempenhos_prova.append({
                    "materia_id": str(d.materia_id),
                    "materia_nome": mat.nome if mat else str(d.materia_id),
                    "percentual_acerto": d.percentual_acerto,
                    "tempo_total_segundos": d.tempo_total_segundos,
                })

        provas_detalhe.append({
            "prova_id": str(p.id),
            "ano": p.ano,
            "nota_total": p.nota_total,
            "tempo_total_segundos": p.tempo_total_segundos,
            "tempo_total_horas": round(p.tempo_total_segundos / 3600, 2),
            "nivel_ansiedade": p.nivel_ansiedade,
            "nivel_fadiga": p.nivel_fadiga,
            "qualidade_sono": p.qualidade_sono,
            "desempenhos_por_materia": desempenhos_prova,
            "criado_em": p.criado_em.isoformat(),
        })

    # ----------------------------------------------------------
    # 11. REDAÇÕES
    # ----------------------------------------------------------

    def _get_competencias(r):
        """Retorna dict {1: nota, ...} de uma Redacao."""
        if hasattr(r, 'competencias') and r.competencias:
            return {c.competencia: c.nota for c in r.competencias}
        return {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}

    redacoes_lista = []
    for r in redacoes:
        comp = _get_competencias(r)
        analise = r.analise if hasattr(r, 'analise') and r.analise else None
        redacoes_lista.append({
            "redacao_id": str(r.id),
            "tema": r.tema,
            "eixo_tematico": r.eixo_tematico or "geral",
            "data_escrita": r.data_escrita.isoformat(),
            "tempo_escrita_min": r.tempo_escrita_min,
            "nota_total": analise.nota_total if analise else sum(comp.values()),
            "status": analise.status if analise else None,
            "competencia1": comp.get(1, 0),
            "competencia2": comp.get(2, 0),
            "competencia3": comp.get(3, 0),
            "competencia4": comp.get(4, 0),
            "competencia5": comp.get(5, 0),
            "competencia_mais_fraca": analise.competencia_mais_fraca if analise else None,
        })

    # Estatísticas de redação
    if redacoes_lista:
        notas_red = [r["nota_total"] for r in redacoes_lista]
        comp_fracas = [r["competencia_mais_fraca"] for r in redacoes_lista if r["competencia_mais_fraca"]]
        comp_fraca_comum = (
            max(set(comp_fracas), key=comp_fracas.count) if comp_fracas else None
        )
        status_dist = defaultdict(int)
        for r in redacoes_lista:
            if r["status"]:
                status_dist[r["status"]] += 1

        evolucao_nota = [
            {"data": r["data_escrita"], "nota": r["nota_total"]}
            for r in sorted(redacoes_lista, key=lambda x: x["data_escrita"])
        ]

        estatisticas_redacoes = {
            "total_redacoes": len(redacoes_lista),
            "nota_media": round(sum(notas_red) / len(notas_red), 1),
            "nota_maxima": max(notas_red),
            "nota_minima": min(notas_red),
            "media_competencia1": round(_safe_avg([r["competencia1"] for r in redacoes_lista]) or 0, 1),
            "media_competencia2": round(_safe_avg([r["competencia2"] for r in redacoes_lista]) or 0, 1),
            "media_competencia3": round(_safe_avg([r["competencia3"] for r in redacoes_lista]) or 0, 1),
            "media_competencia4": round(_safe_avg([r["competencia4"] for r in redacoes_lista]) or 0, 1),
            "media_competencia5": round(_safe_avg([r["competencia5"] for r in redacoes_lista]) or 0, 1),
            "competencia_mais_fraca_mais_comum": comp_fraca_comum,
            "distribuicao_status": dict(status_dist),
            "evolucao_nota": evolucao_nota,
            "redacoes": redacoes_lista,
        }
    else:
        estatisticas_redacoes = {
            "total_redacoes": 0,
            "nota_media": 0,
            "nota_maxima": 0,
            "nota_minima": 0,
            "media_competencia1": 0,
            "media_competencia2": 0,
            "media_competencia3": 0,
            "media_competencia4": 0,
            "media_competencia5": 0,
            "competencia_mais_fraca_mais_comum": None,
            "distribuicao_status": {},
            "evolucao_nota": [],
            "redacoes": [],
        }

    # ----------------------------------------------------------
    # 12. ESTADO MENTAL
    # ----------------------------------------------------------

    estado_mental = {
        "nivel_foco_medio": _safe_avg([s.nivel_foco for s in sessoes]),
        "nivel_energia_medio": _safe_avg([s.nivel_energia for s in sessoes]),
        "nivel_confianca_medio": _safe_avg([
            b.nivel_confianca_medio for b in blocos
        ]),
        "nivel_ansiedade_medio_simulados": _safe_avg([
            s.nivel_ansiedade for s in simulados
        ]),
        "nivel_fadiga_medio_simulados": _safe_avg([
            s.nivel_fadiga for s in simulados
        ]),
        "qualidade_sono_media_simulados": _safe_avg([
            s.qualidade_sono for s in simulados
        ]),
    }

    # ----------------------------------------------------------
    # 13. COMPARATIVO MÊS ANTERIOR
    # ----------------------------------------------------------

    def _horas_lista(sess, blks, sims):
        min_s = sum(session_seconds(s) / 60 for s in sess)
        seg_b = sum(block_seconds(b) for b in blks)
        seg_sim = sum(s.tempo_total_segundos for s in sims)
        return round((min_s + seg_b / 60 + seg_sim / 60) / 60, 2)

    def _questoes_lista(blks, sims):
        return (
            sum(b.total_questoes for b in blks) +
            sum(s.total_questoes for s in sims)
        )

    def _acertos_lista(blks, sims):
        return (
            sum(b.total_acertos for b in blks) +
            sum(s.total_acertos for s in sims)
        )

    horas_ant = _horas_lista(sessoes_ant, blocos_ant, simulados_ant)
    questoes_ant = _questoes_lista(blocos_ant, simulados_ant)
    acertos_ant = _acertos_lista(blocos_ant, simulados_ant)
    pct_acerto_ant = _pct(acertos_ant, questoes_ant)
    ipr_ant = _ipr_combinado(blocos_ant, simulados_ant)

    def _var(atual, anterior):
        delta = atual - anterior
        pct = round(((atual - anterior) / anterior) * 100, 1) if anterior != 0 else None
        return round(delta, 2), pct

    var_h, var_h_pct = _var(horas_totais, horas_ant)
    var_q, var_q_pct = _var(total_questoes, questoes_ant)
    var_a, var_a_pct = _var(_pct(total_acertos, total_questoes), pct_acerto_ant)
    var_ipr, var_ipr_pct = _var(ipr_geral * 100, ipr_ant * 100)
    var_red, _ = _var(len(redacoes), len(redacoes_ant))

    def _label(delta, pct):
        if pct is None: return "SEM BASE ANTERIOR"
        if pct > 5:
            return f"↑ +{pct}%"
        if pct < -5:
            return f"↓ {pct}%"
        return f"→ {pct}%"

    nome_mes_atual = cal_module.month_name[mes]
    nome_mes_ant = cal_module.month_name[mes_ant]

    comparativo = {
        "mes_atual": f"{nome_mes_atual}/{ano}",
        "mes_anterior": f"{nome_mes_ant}/{ano_ant}",
        "horas": {
            "atual": horas_totais,
            "anterior": horas_ant,
            "variacao": var_h,
            "variacao_percentual": var_h_pct,
            "label": _label(var_h, var_h_pct),
        },
        "questoes": {
            "atual": total_questoes,
            "anterior": questoes_ant,
            "variacao": var_q,
            "variacao_percentual": var_q_pct,
            "label": _label(var_q, var_q_pct),
        },
        "percentual_acerto": {
            "atual": _pct(total_acertos, total_questoes),
            "anterior": pct_acerto_ant,
            "variacao": var_a,
            "variacao_percentual": var_a_pct,
            "label": _label(var_a, var_a_pct),
        },
        "ipr": {
            "atual": round(ipr_geral * 100, 2),
            "anterior": round(ipr_ant * 100, 2),
            "variacao": var_ipr,
            "variacao_percentual": var_ipr_pct,
            "label": _label(var_ipr, var_ipr_pct),
        },
        "redacoes": {
            "atual": len(redacoes),
            "anterior": len(redacoes_ant),
            "variacao": var_red,
        },
        "comparativo_ipr": _label(var_ipr, var_ipr_pct),
        "comparativo_volume": _label(var_q, var_q_pct),
        "comparativo_qualidade": _label(var_a, var_a_pct),
    }

    # ----------------------------------------------------------
    # 14. PROJEÇÃO DE FECHAMENTO (só faz sentido se mês atual)
    # ----------------------------------------------------------

    hoje = datetime.now(TZ)
    eh_mes_atual = (mes == hoje.month and ano == hoje.year)

    if eh_mes_atual:
        dias_passados = max(hoje.day, 1)
        dias_restantes = dias_no_mes - dias_passados
    else:
        dias_passados = dias_no_mes
        dias_restantes = 0

    meta_horas_mes = 0
    meta_questoes_mes = 0

    media_h_dia = round(horas_totais / max(dias_passados, 1), 2)
    media_q_dia = round(total_questoes / max(dias_passados, 1), 1)

    if eh_mes_atual:
        proj_horas = round(horas_totais + media_h_dia * dias_restantes, 1)
        proj_questoes = round(total_questoes + media_q_dia * dias_restantes)
        h_necessarias = round(
            max(meta_horas_mes - horas_totais, 0) / max(dias_restantes, 1), 2
        )
        q_necessarias = round(
            max(meta_questoes_mes - total_questoes, 0) / max(dias_restantes, 1), 1
        )
    else:
        proj_horas = horas_totais
        proj_questoes = total_questoes
        h_necessarias = 0
        q_necessarias = 0

    projecao = {
        "media_horas_diaria": media_h_dia,
        "media_questoes_diaria": media_q_dia,
        "projecao_horas_mes": proj_horas,
        "projecao_questoes_mes": proj_questoes,
        "projecao_percentual_dias_estudados": round(
            (dias_estudados / max(dias_passados, 1)) * 100, 1
        ),
        "on_track_meta_horas": proj_horas >= meta_horas_mes,
        "on_track_meta_questoes": proj_questoes >= meta_questoes_mes,
        "dias_passados": dias_passados,
        "dias_restantes": dias_restantes,
        "horas_necessarias_por_dia": h_necessarias,
        "questoes_necessarias_por_dia": q_necessarias,
        "meta_horas_mes": meta_horas_mes,
        "meta_questoes_mes": meta_questoes_mes,
    }

    # ----------------------------------------------------------
    # 15. SCORE DE CONSISTÊNCIA
    # ----------------------------------------------------------

    # Datas do mês em ordem
    todas_datas_mes = sorted(datas_com_atividade)
    primeiro_dia_mes = local_date(data_inicio)

    maior_streak = 0
    streak_atual = 0
    maior_falta = 0
    falta_atual = 0
    dias_falta_seguidos = 0

    dia_cursor = primeiro_dia_mes
    ultimo_dia = min(local_date(fim_calendario - timedelta(microseconds=1)), hoje.date())

    while dia_cursor <= ultimo_dia:
        if dia_cursor in todas_datas_mes:
            streak_atual += 1
            falta_atual = 0
            maior_streak = max(maior_streak, streak_atual)
        else:
            falta_atual += 1
            streak_atual = 0
            maior_falta = max(maior_falta, falta_atual)
            dias_falta_seguidos = falta_atual

        from datetime import date, timedelta as td
        dia_cursor = dia_cursor + td(days=1)

    # Variação diária de horas (desvio padrão aproximado)
    horas_por_dia: dict = defaultdict(float)
    for s in sessoes:
        d = local_date(s.data)
        horas_por_dia[d] += session_seconds(s) / 3600
    for b in blocos:
        d = local_date(b.data)
        horas_por_dia[d] += block_seconds(b) / 3600

    for sim in simulados:
        horas_por_dia[local_date(sim.criado_em)] += sim.tempo_total_segundos / 3600
    valores_h = list(horas_por_dia.values())
    if len(valores_h) > 1:
        media_h = sum(valores_h) / len(valores_h)
        variacao_h = round((sum((v - media_h) ** 2 for v in valores_h) / len(valores_h)) ** 0.5, 2)
    else:
        variacao_h = 0.0

    questoes_por_dia: dict = defaultdict(int)
    for b in blocos:
        d = local_date(b.data)
        questoes_por_dia[d] += b.total_questoes

    for sim in simulados:
        questoes_por_dia[local_date(sim.criado_em)] += sim.total_questoes
    valores_q = list(questoes_por_dia.values())
    if len(valores_q) > 1:
        media_q = sum(valores_q) / len(valores_q)
        variacao_q = round((sum((v - media_q) ** 2 for v in valores_q) / len(valores_q)) ** 0.5, 1)
    else:
        variacao_q = 0.0

    # Score de consistência: % dias estudados ponderado pela variação
    pct_dias = dias_estudados / max((ultimo_dia - primeiro_dia_mes).days + 1, 1)
    penalidade_var = 0  # Presença descritiva, sem penalizar dias com escola/descanso.
    score_consistencia = round(max(pct_dias - penalidade_var, 0) * 100, 1)

    if score_consistencia >= 85:
        class_consistencia = "EXCELENTE"
    elif score_consistencia >= 70:
        class_consistencia = "BOA"
    elif score_consistencia >= 50:
        class_consistencia = "REGULAR"
    else:
        class_consistencia = "IRREGULAR"

    consistencia = {
        "score": score_consistencia,
        "classificacao": "DIAS COM REGISTRO",
        "dias_estudados_seguidos_atual": streak_atual,
        "maior_streak_estudo": maior_streak,
        "maior_sequencia_sem_estudo": maior_falta,
        "variacao_diaria_horas": variacao_h,
        "variacao_diaria_questoes": variacao_q,
    }

    # ----------------------------------------------------------
    # 16. MELHOR E PIOR DIA
    # ----------------------------------------------------------

    dias_map = defaultdict(lambda: {
        "horas": 0.0, "questoes": 0, "acertos": 0, "iprs": []
    })

    for s in sessoes:
        d = local_date(s.data)
        dias_map[d]["horas"] += session_seconds(s) / 3600

    for b in blocos:
        d = local_date(b.data)
        dias_map[d]["horas"] += block_seconds(b) / 3600
        dias_map[d]["questoes"] += b.total_questoes
        dias_map[d]["acertos"] += b.total_acertos
        dias_map[d]["iprs"].append(_calcular_ipr_bloco(b))

    for sim in simulados:
        d = local_date(sim.criado_em)
        dias_map[d]["horas"] += sim.tempo_total_segundos / 3600
        dias_map[d]["questoes"] += sim.total_questoes
        dias_map[d]["acertos"] += sim.total_acertos
    dias_processados = []
    nomes_semana = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]
    for data_d, dados in dias_map.items():
        if not dados["questoes"]:
            continue
        ipr_dia = dados["acertos"] / dados["questoes"]
        dias_processados.append({
            "data": data_d.isoformat() if hasattr(data_d, 'isoformat') else str(data_d),
            "dia_semana": nomes_semana[data_d.weekday()] if hasattr(data_d, 'weekday') else "",
            "horas": round(dados["horas"], 2),
            "questoes": dados["questoes"],
            "percentual_acerto": _pct(dados["acertos"], dados["questoes"]),
            "ipr_dia": round(ipr_dia * 100, 2),
        })

    melhor_dia = None
    pior_dia = None
    if dias_processados:
        melhor_dia = max(dias_processados, key=lambda x: x["ipr_dia"])
        melhor_dia = {**melhor_dia, "motivo": "Maior precisão entre dias com questões; confira a amostra"}
        pior_dia = min(dias_processados, key=lambda x: x["ipr_dia"])
        pior_dia = {**pior_dia, "motivo": "Menor precisão entre dias com questões; confira a amostra"}

    # ----------------------------------------------------------
    # 17. CORRELAÇÕES (simples: pearson aproximado)
    # ----------------------------------------------------------

    def _pearson(xs, ys):
        """Pearson simplificado para listas pequenas."""
        n = len(xs)
        if n < 3:
            return None
        mx, my = sum(xs) / n, sum(ys) / n
        num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
        den = (
            (sum((x - mx) ** 2 for x in xs) * sum((y - my) ** 2 for y in ys)) ** 0.5
        )
        return round(num / den, 3) if den != 0 else None

    # Only explicitly linked sessions establish a pair; avoid a Cartesian daily join.
    session_map = {s.id: s for s in sessoes}
    pares_foco_ipr = [(session_map[b.sessao_id].nivel_foco, _calcular_ipr_bloco(b))
        for b in blocos if b.sessao_id in session_map and session_map[b.sessao_id].nivel_foco is not None]

    corr_foco_ipr = _pearson(
        [p[0] for p in pares_foco_ipr],
        [p[1] for p in pares_foco_ipr]
    ) if pares_foco_ipr else None

    # sono x acerto (via simulados)
    pares_sono_acerto = [
        (s.qualidade_sono, s.total_acertos / s.total_questoes)
        for s in simulados if s.qualidade_sono and s.total_questoes > 0
    ]
    corr_sono_acerto = _pearson(
        [p[0] for p in pares_sono_acerto],
        [p[1] for p in pares_sono_acerto]
    ) if pares_sono_acerto else None

    # ansiedade x erro
    pares_ans_erro = [
        (s.nivel_ansiedade, (s.total_questoes - s.total_acertos) / s.total_questoes)
        for s in simulados if s.nivel_ansiedade and s.total_questoes > 0
    ]
    corr_ans_erro = _pearson(
        [p[0] for p in pares_ans_erro],
        [p[1] for p in pares_ans_erro]
    ) if pares_ans_erro else None

    correlacoes = {
        "correlacao_foco_ipr": corr_foco_ipr,
        "correlacao_sono_acerto": corr_sono_acerto,
        "correlacao_ansiedade_erro": corr_ans_erro,
        "nota": (
            "Correlação calculada com base nos dados disponíveis do mês. "
            "Valores próximos de 1 indicam correlação positiva forte, "
            "-1 negativa forte, 0 ausência de correlação."
        ),
    }

    # ----------------------------------------------------------
    # 18. BALANCEAMENTO DE MATÉRIAS
    # ----------------------------------------------------------

    total_min_todas = (
        sum(session_seconds(s) / 60 for s in sessoes) +
        sum(block_seconds(b) / 60 for b in blocos)
    ) or 1

    total_q_todas = total_questoes_blocos or 1

    balanceamento = []
    for mat_id, mat in materias_map.items():
        min_mat = (
            sum(session_seconds(s) / 60 for s in sessoes if s.materia_id == mat_id) +
            sum(block_seconds(b) / 60 for b in blocos if b.materia_id == mat_id)
        )
        q_mat = (
            sum(b.total_questoes for b in blocos if b.materia_id == mat_id)
        )
        blocos_mat = [b for b in blocos if b.materia_id == mat_id]
        ipr_mat = _ipr_blocos_lista(blocos_mat)

        pct_tempo = round((min_mat / total_min_todas) * 100, 1)
        pct_q = round((q_mat / total_q_todas) * 100, 1)

        peso = float(mat.peso_prova)
        # "peso_vs_tempo": se estuda proporcionalmente ao peso
        if peso > 0:
            ratio = pct_tempo / (peso / sum(float(m.peso_prova) for m in materias_map.values()) * 100)
            if ratio < 0.7:
                peso_vs_tempo = "SUBINVESTIDA"
            elif ratio > 1.4:
                peso_vs_tempo = "SUPERINVESTIDA"
            else:
                peso_vs_tempo = "EQUILIBRADA"
        else:
            peso_vs_tempo = "SEM_PESO_DEFINIDO"

        status_mat = (
            "SEM PRÁTICA" if not blocos_mat else
            "AMOSTRA PEQUENA" if q_mat < 20 or len(blocos_mat) < 2 else
            "REAVALIAR" if ipr_mat < 0.60 else
            "FRACA" if ipr_mat < 0.70 else
            "REGULAR" if ipr_mat < 0.80 else
            "BOA"
        )

        balanceamento.append({
            "materia_id": str(mat_id),
            "materia_nome": mat.nome,
            "peso_prova": peso,
            "tempo_dedicado_minutos": round(min_mat, 1),
            "tempo_dedicado_percentual": pct_tempo,
            "questoes_respondidas": q_mat,
            "questoes_respondidas_percentual": pct_q,
            "ipr": round(ipr_mat * 100, 2),
            "peso_vs_tempo": peso_vs_tempo,
            "status": status_mat,
        })

    balanceamento.sort(key=lambda x: -x["peso_prova"])

    # ----------------------------------------------------------
    # 19. RECOMENDAÇÕES ESTRATÉGICAS MENSAIS
    # ----------------------------------------------------------

    recomendacoes_mensais = [{
        "categoria": "PRÓXIMA SESSÃO", "prioridade": "NORMAL",
        "mensagem": f"{total_questoes} questões registradas neste período." if total_questoes else "Sem questões registradas: não há evidência de precisão.",
        "acao_sugerida": "Abra Estudar agora para retomar o saldo do ciclo e escolher uma atividade. Horas não medem domínio; ausência não vira dívida."
    }]
    if total_questoes and total_questoes < 20:
        recomendacoes_mensais.append({"categoria": "AMOSTRA", "prioridade": "NORMAL", "mensagem": "Poucas questões para avaliar desempenho.", "acao_sugerida": "Faça um pequeno diagnóstico no assunto atual antes de atribuir uma causa aos erros."})
    # No invented monthly goals. Projections remain descriptive, never a debt.
    for key in ("meta_horas_mes", "meta_questoes_mes", "on_track_meta_horas", "on_track_meta_questoes"):
        projecao[key] = None
    projecao["horas_necessarias_por_dia"] = None
    projecao["questoes_necessarias_por_dia"] = None
    resumo_geral["tem_evidencia"] = total_questoes > 0
    resumo_geral["versao_metrica"] = "precisao_v2"

    # ----------------------------------------------------------
    # 20. MONTAGEM FINAL
    # ----------------------------------------------------------

    return {
        "gerado_em": datetime.now(timezone.utc).isoformat(),
        "versao_metrica": "precisao_v2",
        "periodo": periodo,
        "resumo_geral": resumo_geral,
        "sessoes": sessoes_dict,
        "blocos": blocos_dict,
        "erros": erros_dict,
        "simulados": simulados_detalhe,
        "provas_oficiais": provas_detalhe,
        "redacoes": estatisticas_redacoes,
        "estado_mental": estado_mental,
        "comparativo_mes_anterior": comparativo,
        "projecao_fechamento": projecao,
        "consistencia": consistencia,
        "melhor_dia": melhor_dia,
        "pior_dia": pior_dia,
        "correlacoes": correlacoes,
        "balanceamento_materias": balanceamento,
        "recomendacoes_estrategicas": recomendacoes_mensais,
    }