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
    tempo_ideal = 120
    tempo_limite = 300  # 5 min (lento)

    velocidade_normalizada = max(
        0,
        min(1, (tempo_limite - tempo_medio) / (tempo_limite - tempo_ideal))
    )


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
    tempo_ideal = 120
    tempo_limite = 300  # 5 min (lento)
    
    velocidade_normalizada = max(
        0,
        min(1, (tempo_limite - tempo_medio) / (tempo_limite - tempo_ideal))
    )

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
    meta_horas = 0
    meta_questoes = 0
    
    if periodo == "semana":
        meta_horas = 22
        meta_questoes = 350
    elif periodo == "mes":
        meta_horas = 88
        meta_questoes = 1400
    else:  # ano ou qualquer outro
        meta_horas = 1056
        meta_questoes = 16800
    
    MARGEM_HORAS = 0.0  # ±10% ainda é "DENTRO"
    
    if horas < meta_horas * (1 - MARGEM_HORAS):
        status_horas = "ABAIXO"
    elif horas > meta_horas * (1 + MARGEM_HORAS):
        status_horas = "ACIMA"
    else:
        status_horas = "DENTRO"
    
    if total_questoes < meta_questoes * (1 - MARGEM_HORAS):
        status_questoes = "ABAIXO"
    elif total_questoes > meta_questoes * (1 + MARGEM_HORAS):
        status_questoes = "ACIMA"
    else:
        status_questoes = "DENTRO"
    
    # ================= RECOMENDAÇÕES =================
    # ================= RECOMENDAÇÕES =================
    recomendacoes = []
    
    # --- 1. DESEMPENHO (IPR) ---
    if ipr_medio < 0.60:
        recomendacoes.append(
            "IPR crítico: seu cérebro está consolidando erros. Pare de aumentar volume e volte à teoria — "
            "praticar sem base só reforça padrões errados (efeito de consolidação negativa)."
        )
        recomendacoes.append(
            "Refaça questões erradas sem ver o gabarito antes: o esforço de recuperação ativa "
            "(retrieval practice) é o que gera aprendizado real, não releitura passiva."
        )
        if status_horas == "ACIMA":
            recomendacoes.append(
                f"Você está estudando acima da meta de horas ({meta_horas}h), mas o IPR está crítico — "
                "isso é um sinal claro de que volume sem qualidade está atrapalhando. Reduza a carga e foque em revisão profunda."
            )
        if periodo == "semana":
            recomendacoes.append(
                "Nessa semana, priorize entender o padrão dos seus erros antes de avançar qualquer conteúdo novo. "
                "Uma semana de consolidação vale mais do que duas semanas de avanço sem base."
            )
    
    elif ipr_medio < 0.70:
        recomendacoes.append(
            "Desempenho abaixo do limiar de aprovação. Identifique os 2-3 assuntos com mais erros e estude-os "
            "em blocos concentrados — o cérebro aprende por domínio progressivo, não por exposição distribuída sem base."
        )
        recomendacoes.append(
            "Antes de iniciar qualquer bloco novo, revise os erros do dia anterior por 10 minutos: "
            "isso ativa reconsolidação de memória e reduz reincidência de erro."
        )
        if tendencia == "DECLÍNIO":
            recomendacoes.append(
                "IPR abaixo do esperado e ainda em queda — sinal de alerta. Interrompa o avanço de conteúdo "
                "por 2-3 dias e dedique esse tempo exclusivamente a revisão dos erros recentes."
            )
        if periodo == "mes":
            recomendacoes.append(
                "No acumulado do mês, um IPR abaixo de 70% indica que a base está frágil. "
                "Reorganize o plano mensal: reserve a primeira semana do próximo mês para revisão estruturada antes de avançar."
            )
    
    elif ipr_medio < 0.75:
        recomendacoes.append(
            "Você está na zona de transição — próximo do nível competitivo, mas ainda instável. "
            "Foque em consistência antes de volume: desempenho irregular indica lacunas pontuais, não falta de esforço geral."
        )
        recomendacoes.append(
            "Use interleaving: alterne assuntos dentro do mesmo bloco em vez de estudar um só tema por sessão. "
            "Isso aumenta retenção e prepara para o formato real da prova."
        )
        if tendencia == "ASCENDENTE":
            recomendacoes.append(
                "Boa notícia: você está crescendo. Mantenha o método atual e eleve levemente a dificuldade das questões — "
                "você está pronto para sair da zona de transição."
            )
        if status_questoes == "ABAIXO":
            recomendacoes.append(
                f"Com IPR nessa faixa e volume de questões abaixo da meta ({meta_questoes}), "
                "o risco é de desenvolvimento lento. Adicione um bloco extra diário focado nos temas mais cobrados."
            )
    
    elif ipr_medio < 0.85:
        recomendacoes.append(
            "Bom desempenho. Para evitar platô cognitivo, aumente progressivamente a dificuldade das questões — "
            "o cérebro só cresce sob desafio calibrado (zona de desenvolvimento proximal)."
        )
        recomendacoes.append(
            "Introduza simulados cronometrados: a pressão do tempo muda o padrão de ativação neural "
            "e revela erros que blocos comuns não expõem."
        )
        if status_horas == "ABAIXO":
            recomendacoes.append(
                f"Seu desempenho está bom, mas as horas estão abaixo da meta ({meta_horas}h). "
                "Você tem qualidade — agora precisa de volume. Adicione sessões curtas de 45-60 min nos intervalos do dia."
            )
        if periodo == "ano":
            recomendacoes.append(
                "No acumulado anual, esse IPR coloca você em posição competitiva. "
                "O próximo passo é simular condições reais de prova com frequência — consistência no longo prazo é o diferencial."
            )
    
    else:
        recomendacoes.append(
            "Alto desempenho. Agora o diferencial é velocidade e precisão sob pressão. "
            "Treine com limite de tempo abaixo do real para criar margem de segurança na prova."
        )
        recomendacoes.append(
            "Priorize questões de provas anteriores da EsPCEx: reconhecer o estilo de elaboração "
            "reduz carga cognitiva no dia da prova."
        )
        if tendencia == "DECLÍNIO":
            recomendacoes.append(
                "Atenção: mesmo com IPR alto, a tendência está caindo. Isso pode indicar fadiga acumulada — "
                "considere 1-2 dias de carga reduzida para recuperação cognitiva antes de retomar o ritmo."
            )
        if status_horas == "ACIMA":
            recomendacoes.append(
                f"IPR alto e horas acima da meta ({meta_horas}h) — cuidado com a armadilha da quantidade. "
                "Você está bem: proteja esse desempenho reduzindo um pouco o volume e priorizando qualidade de sono."
            )
    
    # --- 2. ASSUNTOS CRÍTICOS ---
    if assuntos_criticos:
        recomendacoes.append(
            f"{len(assuntos_criticos)} assunto(s) com IPR abaixo de 70% e pelo menos 2 blocos realizados — "
            "isso indica lacuna real, não acaso. Resolva questões específicas desses tópicos diariamente "
            "até o IPR superar 75%."
        )
        if len(assuntos_criticos) >= 3:
            recomendacoes.append(
                "Múltiplos pontos críticos simultâneos indicam base teórica fragmentada. "
                "Reorganize o plano: dedique 1 semana a teoria direcionada antes de retomar volume nesses temas."
            )
        if ipr_medio >= 0.75 and assuntos_criticos:
            recomendacoes.append(
                "Seu IPR geral está bom, mas há assuntos críticos específicos puxando para baixo. "
                "Esse é o tipo de lacuna que derruba candidatos avançados na reta final — trate com prioridade."
            )
    
    # --- 3. TENDÊNCIA ---
    if tendencia == "DECLÍNIO":
        recomendacoes.append(
            "Queda de desempenho detectada. Antes de estudar mais, estude melhor: fadiga cognitiva acumulada "
            "derruba rendimento mesmo com tempo alto. Considere reduzir volume por 2-3 dias e priorizar sono e revisão."
        )
        recomendacoes.append(
            "Analise os erros recentes buscando padrões: erro recorrente no mesmo tipo de questão indica "
            "falha conceitual estrutural, não distração — e precisa de intervenção específica."
        )
    elif tendencia == "ASCENDENTE":
        recomendacoes.append(
            "Tendência positiva — seu plano atual está funcionando. Não mude o método, apenas eleve gradualmente "
            "a carga. Mudanças bruscas em fases de crescimento interrompem o ciclo de consolidação."
        )
        if periodo == "semana":
            recomendacoes.append(
                "Semana em ascensão: aproveite o momentum e mantenha a rotina que está gerando esse resultado. "
                "Consistência agora vale mais do que qualquer ajuste no método."
            )
    
    # --- 4. VOLUME ---
    if status_horas == "ABAIXO":
        if periodo == "semana":
            recomendacoes.append(
                f"Horas abaixo da meta semanal ({meta_horas}h). Distribua o estudo em blocos de 90 minutos com "
                "pausas de 15 min (ciclo ultradiano): esse ritmo respeita os picos naturais de concentração "
                "e maximiza retenção por hora estudada."
            )
        elif periodo == "mes":
            recomendacoes.append(
                f"No acumulado do mês, as horas estão abaixo da meta ({meta_horas}h). "
                "Identifique quais dias da semana estão com menor carga e adicione pelo menos uma sessão extra nesses dias."
            )
        else:
            recomendacoes.append(
                f"Horas abaixo da meta ({meta_horas}h). Revise sua rotina semanal e identifique onde há espaço "
                "para sessões adicionais — pequenos blocos diários de 45 min acumulam muito ao longo do ano."
            )
    elif status_horas == "ACIMA":
        recomendacoes.append(
            f"Carga acima da meta ({meta_horas}h). Excesso de horas sem qualidade equivalente causa fadiga de decisão "
            "e consolidação deficiente durante o sono. Reduza e monitore se o IPR sobe — qualidade supera quantidade."
        )
    
    if status_questoes == "ABAIXO":
        recomendacoes.append(
            f"Volume de questões abaixo da meta ({meta_questoes}). Quantidade mínima importa para criar familiaridade "
            "com padrões de prova. Inclua pelo menos um bloco extra diário de 20-30 questões nos assuntos mais cobrados."
        )
    elif status_questoes == "ACIMA":
        recomendacoes.append(
            "Volume acima da meta — atenção: fazer muitas questões sem analisar os erros é a principal causa de "
            "estagnação em candidatos avançados. Reserve ao menos 30% do tempo de questões para revisão e análise."
        )
    
    # --- 5. COMBINAÇÕES ESPECIAIS ---
    if ipr_medio >= 0.75 and status_horas == "DENTRO" and status_questoes == "DENTRO" and tendencia != "DECLÍNIO":
        recomendacoes.append(
            "Todos os indicadores principais estão alinhados — IPR, volume e tendência. "
            "Você está no caminho certo. Agora é proteger a consistência e elevar progressivamente a dificuldade."
        )
    
    if ipr_medio < 0.70 and status_questoes == "ACIMA":
        recomendacoes.append(
            "Combinação crítica: IPR baixo e volume alto de questões. Você está praticando muito mas aprendendo pouco. "
            "Reduza o volume pela metade e invista o tempo restante em análise profunda de cada erro."
        )
    
    if tendencia == "DECLÍNIO" and status_horas == "ACIMA":
        recomendacoes.append(
            "Queda de desempenho com horas acima da meta — esse padrão quase sempre indica fadiga cognitiva. "
            "Tire um dia de descanso completo e retome com volume reduzido. Descanso é parte do treino."
        )
    
    # --- 6. FALLBACK ---
    if not recomendacoes:
        recomendacoes.append(
            "Todos os indicadores dentro do esperado. Mantenha a consistência — "
            "na reta final, regularidade supera qualquer pico isolado de esforço."
        )
            

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

def criar_materia(db: Session, payload: schemas.MateriaCreate):
    """
    Cria uma nova matéria no banco de dados.

    Validações:
    - O nome deve ser único (case-insensitive).
    """
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