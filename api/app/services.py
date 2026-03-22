from typing import Optional, List
from uuid import UUID, uuid4
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException
from datetime import datetime, timedelta, timezone

from . import models, schemas


# ==========================================================
# UTILIDADES INTERNAS
# ==========================================================

def _normalizar(valor, minimo, maximo):
    if maximo - minimo == 0:
        return 0
    return (valor - minimo) / (maximo - minimo)

def _calcular_ipr_simulado(simulado: models.SimuladoSemanal) -> float:

    if simulado.total_questoes == 0:
        return 0.0

    # ================= PRECISÃO =================
    precisao = simulado.total_acertos / simulado.total_questoes


    # ================= VELOCIDADE =================
    tempo_medio = simulado.tempo_total_segundos / simulado.total_questoes
    velocidade = 1 / tempo_medio if tempo_medio > 0 else 0

    velocidade_normalizada = min(velocidade / 2, 1)


    # ================= PENALIDADE MENTAL =================
    penalidade = 0

    if simulado.nivel_ansiedade:
        penalidade += simulado.nivel_ansiedade * 0.01

    if simulado.nivel_fadiga:
        penalidade += simulado.nivel_fadiga * 0.01

    if simulado.qualidade_sono:
        penalidade -= simulado.qualidade_sono * 0.01


    # ================= IPR =================
    ipr = (
        (precisao * 0.7) +
        (velocidade_normalizada * 0.3)
    )

    ipr -= penalidade

    return round(max(min(ipr, 1), 0), 4)

def _obter_data_inicio(periodo: str) -> datetime:
    agora = datetime.now(timezone.utc)

    if periodo == "semana":
        # segunda-feira da semana atual
        inicio_semana = agora - timedelta(days=agora.weekday())
        return inicio_semana.replace(hour=0, minute=0, second=0, microsecond=0)

    if periodo == "mes":
        # primeiro dia do mês
        return agora.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    if periodo == "ano":
        # primeiro dia do ano
        return agora.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)

    if periodo == "todos":
        return datetime(2000, 1, 1)

    return datetime(2000, 1, 1)


def _calcular_ipr_bloco(bloco: models.BlocoQuestoes) -> float:
    if bloco.total_questoes == 0:
        return 0.0

    # Precisão
    precisao = bloco.total_acertos / bloco.total_questoes

    # Velocidade (normalização simples)
    tempo_medio = bloco.tempo_medio_por_questao
    velocidade = 1 / tempo_medio if tempo_medio > 0 else 0
    velocidade_normalizada = min(velocidade / 2, 1)  # limite arbitrário

    # Penalidade por erros críticos
    penalidade = 0
    for erro in bloco.erros:
        if erro.tipo_erro in ["DISTRACAO", "PRESSA"]:
            penalidade += erro.quantidade * 0.01

    ipr = (precisao * 0.6) + (velocidade_normalizada * 0.2) + (bloco.dificuldade / 5 * 0.2)
    ipr -= penalidade

    return round(max(min(ipr, 1), 0), 4)


def _calcular_tendencia(ipr_atual: float, ipr_anterior: float) -> str:
    if ipr_anterior == 0:
        return "ESTÁVEL"

    variacao = ((ipr_atual - ipr_anterior) / ipr_anterior) * 100

    if variacao > 5:
        return "ASCENDENTE"
    elif variacao < -5:
        return "DECLÍNIO"
    return "ESTÁVEL"


# ==========================================================
# SESSÃO DE ESTUDO
# ==========================================================

def registrar_sessao_estudo(db: Session, payload: schemas.SessaoEstudoCreate):
    db_obj = models.SessaoEstudo(**payload.model_dump())

    try:
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Erro ao registrar sessão.")


def listar_sessoes(db: Session, skip: int = 0, limit: int = 100):
    return (
        db.query(models.SessaoEstudo)
        .order_by(models.SessaoEstudo.data.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def calcular_horas_periodo(
    db: Session,
    periodo: str,
    materia_id: Optional[UUID]
) -> float:

    data_inicio = _obter_data_inicio(periodo)

    # ================= SESSÕES =================
    query_sessoes = db.query(func.sum(models.SessaoEstudo.minutos_liquidos)).filter(
        models.SessaoEstudo.data >= data_inicio
    )

    if materia_id:
        query_sessoes = query_sessoes.filter(
            models.SessaoEstudo.materia_id == materia_id
        )

    total_min_sessoes = query_sessoes.scalar() or 0


    # ================= BLOCOS =================
    query_blocos = db.query(func.sum(models.BlocoQuestoes.tempo_total_segundos)).filter(
        models.BlocoQuestoes.data >= data_inicio
    )

    if materia_id:
        query_blocos = query_blocos.filter(
            models.BlocoQuestoes.materia_id == materia_id
        )

    total_seg_blocos = query_blocos.scalar() or 0


    # ================= SIMULADOS =================
    query_simulados = db.query(func.sum(models.SimuladoSemanal.tempo_total_segundos)).filter(
        models.SimuladoSemanal.criado_em >= data_inicio
    )

    total_seg_simulados = query_simulados.scalar() or 0


    # ================= CONSOLIDAÇÃO =================
    total_min_blocos = total_seg_blocos / 60
    total_min_simulados = total_seg_simulados / 60

    total_minutos = total_min_sessoes + total_min_blocos + total_min_simulados

    return round(total_minutos / 60, 2)


# ==========================================================
# BLOCO DE QUESTÕES
# ==========================================================

def registrar_bloco_questoes(db: Session, payload: schemas.BlocoQuestoesCreate):
    if payload.total_acertos > payload.total_questoes:
        raise HTTPException(status_code=400, detail="Acertos não podem ser maiores que total.")

    db_obj = models.BlocoQuestoes(**payload.model_dump())

    try:
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Erro ao registrar bloco.")


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

def get_dashboard(
    db: Session,
    periodo: str = "semana",
    materia_id: Optional[UUID] = None
):

    data_inicio = _obter_data_inicio(periodo)

    # ================= HORAS =================
    horas = calcular_horas_periodo(db, periodo, materia_id)

    # ================= BLOCOS =================
    query_blocos = db.query(models.BlocoQuestoes).filter(
        models.BlocoQuestoes.data >= data_inicio
    )

    query_simulados = db.query(models.SimuladoSemanal).filter(
        models.SimuladoSemanal.criado_em >= data_inicio
    )

    if materia_id:
        query_blocos = query_blocos.filter(
            models.BlocoQuestoes.materia_id == materia_id
        )

    blocos = query_blocos.all()
    simulados = query_simulados.all()
    
    # ================= TOTAIS =================
    if (materia_id):
        total_questoes = (
        sum(b.total_questoes for b in blocos) +
        round((sum(s.total_questoes for s in simulados)/7))  # simulado semanal dividido por 7 para média diária
    )
    else:
        total_questoes = (
            sum(b.total_questoes for b in blocos) +
            sum(s.total_questoes for s in simulados)
        )
    
    total_acertos = (
        sum(b.total_acertos for b in blocos) +
        sum(s.total_acertos for s in simulados)
    )
    
    percentual_medio = round(
        (total_acertos / total_questoes) * 100, 2
    ) if total_questoes > 0 else 0
    
    
    # ================= IPR ATUAL =================
    
    iprs_blocos = [_calcular_ipr_bloco(b) for b in blocos]
    iprs_simulados = [_calcular_ipr_simulado(s) for s in simulados]
    
    ipr_blocos = (
        sum(iprs_blocos) / len(iprs_blocos)
    ) if iprs_blocos else 0
    
    ipr_simulados = (
        sum(iprs_simulados) / len(iprs_simulados)
    ) if iprs_simulados else 0
    
    ipr_medio = None

    if ipr_simulados > 0:
        ipr_medio = round(
            (ipr_blocos * 0.7) + (ipr_simulados * 0.3),
            4
        )
    else:
        ipr_medio = round(ipr_blocos, 4)    
    
    # ================= TENDÊNCIA =================
    
    if periodo == "semana":
        data_anterior = data_inicio - timedelta(days=7)
    
    elif periodo == "mes":
        data_anterior = (data_inicio - timedelta(days=1)).replace(day=1)
    
    else:
        data_anterior = datetime(2000,1,1)
    
    blocos_anteriores = db.query(models.BlocoQuestoes).filter(
        models.BlocoQuestoes.data >= data_anterior,
        models.BlocoQuestoes.data < data_inicio
    ).all()
    
    simulados_anteriores = db.query(models.SimuladoSemanal).filter(
        models.SimuladoSemanal.criado_em >= data_anterior,
        models.SimuladoSemanal.criado_em < data_inicio
    ).all()
    
    
    iprs_blocos_ant = [_calcular_ipr_bloco(b) for b in blocos_anteriores]
    iprs_simulados_ant = [_calcular_ipr_simulado(s) for s in simulados_anteriores]
    
    ipr_blocos_ant = (
        sum(iprs_blocos_ant) / len(iprs_blocos_ant)
    ) if iprs_blocos_ant else 0
    
    ipr_simulados_ant = (
        sum(iprs_simulados_ant) / len(iprs_simulados_ant)
    ) if iprs_simulados_ant else 0
    
    ipr_anterior = round(
        (ipr_blocos_ant * 0.7) + (ipr_simulados_ant * 0.3),
        4
    )
    
    tendencia = _calcular_tendencia(ipr_medio, ipr_anterior)

    # ================= ASSUNTOS CRÍTICOS =================
    assuntos_criticos = []

    assuntos_ids = list(set(b.assunto_id for b in blocos))

    for assunto_id in assuntos_ids:
        blocos_assunto = [b for b in blocos if b.assunto_id == assunto_id]
        iprs_assunto = [_calcular_ipr_bloco(b) for b in blocos_assunto]

        if len(iprs_assunto) >= 2 and sum(iprs_assunto) / len(iprs_assunto) < 0.70:
            assuntos_criticos.append(str(assunto_id))

    # ================= STATUS DE META =================
    status_horas = "ABAIXO"
    if 22 <= horas <= 24:
        status_horas = "DENTRO"
    elif horas > 24:
        status_horas = "ACIMA"

    status_questoes = "ABAIXO"
    if 350 <= total_questoes <= 450:
        status_questoes = "DENTRO"
    elif total_questoes > 450:
        status_questoes = "ACIMA"

    # ================= RECOMENDAÇÕES =================

    recomendacoes = []

    if ipr_medio < 0.60:
        recomendacoes.append("Desempenho crítico: revise a teoria base imediatamente antes de continuar com exercícios")
        recomendacoes.append("Refaça questões erradas sem consultar resposta até acertar sozinho")
        recomendacoes.append("Diminua volume e aumente qualidade do estudo")

    if 0.60 <= ipr_medio < 0.70:
        recomendacoes.append("Foque nos assuntos críticos identificados")
        recomendacoes.append("Revise erros recentes antes de iniciar novos blocos")
        recomendacoes.append("Aumente repetição espaçada dos conteúdos com baixo desempenho")

    if ipr_medio >= 0.75:
        recomendacoes.append("Bom desempenho: mantenha consistência")
        recomendacoes.append("Aumente levemente a dificuldade das questões")
        recomendacoes.append("Introduza simulados mais desafiadores")

    if ipr_medio >= 0.85:
        recomendacoes.append("Alto desempenho: foco em refinamento e velocidade")
        recomendacoes.append("Treine resolução sob tempo")
        recomendacoes.append("Priorize questões de alto nível e provas anteriores")

    # Tendência
    if tendencia == "DECLÍNIO":
        recomendacoes.append("Queda de desempenho: revise estratégia de estudo")
        recomendacoes.append("Reduza carga temporariamente para recuperar qualidade")
        recomendacoes.append("Analise erros recorrentes e padrões de falha")

    elif tendencia == "SUBIDA":
        recomendacoes.append("Evolução positiva: mantenha o plano atual")
        recomendacoes.append("Aproveite para consolidar conteúdos fortes")

    # Horas
    if status_horas == "ABAIXO":
        recomendacoes.append("Aumente o tempo de estudo semanal")
        recomendacoes.append("Distribua melhor os horários ao longo da semana")

    elif status_horas == "ACIMA":
        recomendacoes.append("Carga alta: cuidado com fadiga e queda de rendimento")
        recomendacoes.append("Considere pausas estratégicas para manter desempenho")

    # Questões
    if status_questoes == "ABAIXO":
        recomendacoes.append("Aumente o volume de questões praticadas")
        recomendacoes.append("Inclua mais blocos diários")

    elif status_questoes == "ACIMA":
        recomendacoes.append("Volume alto: priorize análise de erros em vez de quantidade")
        recomendacoes.append("Evite fazer questões de forma automática sem aprendizado")

    # Assuntos críticos
    if assuntos_criticos:
        recomendacoes.append("Priorize revisão dos assuntos críticos identificados")
        recomendacoes.append("Resolva questões específicas desses tópicos diariamente")
        recomendacoes.append("Estude teoria direcionada para corrigir lacunas")

        if len(assuntos_criticos) >= 3:
            recomendacoes.append("Muitos pontos fracos: reorganize o plano de estudos")
            recomendacoes.append("Considere voltar etapas no conteúdo para reforço base")

    # Consistência geral
    if not recomendacoes:
        recomendacoes.append("Plano equilibrado: continue com a mesma estratégia")


    return {
        "horas_liquidas": horas,
        "total_questoes": total_questoes,
        "percentual_medio": percentual_medio,
        "ipr_geral": round(ipr_medio * 100, 2),
        "tendencia": tendencia,
        "status_missao": "MISSÃO CUMPRIDA" if ipr_medio >= 0.70 else "EXECUÇÃO INSUFICIENTE",
        "assuntos_criticos": assuntos_criticos,
        "status_horas": status_horas,
        "status_questoes": status_questoes,
        "recomendacao": recomendacoes
    }

def listar_materias(db: Session):
    return db.query(models.Materia).order_by(models.Materia.nome).all()


def listar_assuntos(db: Session, materia_id: Optional[UUID] = None):
    query = db.query(models.Assunto)

    if materia_id:
        query = query.filter(models.Assunto.materia_id == materia_id)

    return query.order_by(models.Assunto.nome).all()


def listar_assuntos_por_materia(db: Session, materia_id: UUID):
    return (
        db.query(models.Assunto)
        .filter(models.Assunto.materia_id == materia_id)
        .order_by(models.Assunto.nome)
        .all()
    )


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
        return "critica"

    if nota < 600:
        return "fraca"

    if nota < 700:
        return "regular"

    if nota < 800:
        return "boa"

    if nota < 900:
        return "muito_boa"

    return "excelente"


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

    diagnostico = f"A competência {competencia_mais_fraca} foi a mais fraca."
    recomendacao = f"Treinar mais a competência {competencia_mais_fraca}."

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