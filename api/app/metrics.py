"""Single definition of observed accuracy and time; no inferred approval score."""
from datetime import datetime, timedelta
from collections import defaultdict
from . import models
from .clock import utcnow, utc_naive, TZ, month_bounds

def valid_questions(x):
    return x.total_questoes > 0 and 0 <= x.total_acertos <= x.total_questoes

def precisao(items):
    valid = [x for x in items if valid_questions(x)]
    total = sum(x.total_questoes for x in valid)
    return sum(x.total_acertos for x in valid) / total if total else 0.0

def session_seconds(s):
    return s.segundos_exatos if s.segundos_exatos is not None else s.minutos_liquidos * 60

def block_seconds(b):
    return 0 if b.sessao_id else b.tempo_total_segundos

def limites_periodo(periodo):
    now = utcnow()
    local = now.replace(tzinfo=__import__('datetime').timezone.utc).astimezone(TZ)
    if periodo == "semana":
        start = (local - timedelta(days=local.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    elif periodo == "mes":
        start = local.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    elif periodo == "ano":
        start = local.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        return datetime(1970, 1, 1), now
    return utc_naive(start), now

def dashboard(db, periodo="semana", materia_id=None):
    start, end = limites_periodo(periodo)
    def load(model, datecol, lo, hi):
        q = db.query(model).filter(datecol >= lo, datecol < hi)
        if materia_id:
            q = q.filter(model.materia_id == materia_id)
        return q.all()
    blocks = load(models.BlocoQuestoes, models.BlocoQuestoes.data, start, end)
    sessions = load(models.SessaoEstudo, models.SessaoEstudo.data, start, end)
    def sims(lo,hi):
        return [] if materia_id else db.query(models.SimuladoSemanal).filter(models.SimuladoSemanal.criado_em >= lo, models.SimuladoSemanal.criado_em < hi).all()
    simulations = sims(start,end)
    invalid = sum(not valid_questions(x) for x in blocks + simulations)
    items = [x for x in blocks + simulations if valid_questions(x)]
    total = sum(max(b.total_questoes,0) for b in items)
    hits = sum(min(max(b.total_acertos,0),max(b.total_questoes,0)) for b in items)
    score = precisao(items)
    seconds = sum(session_seconds(s) for s in sessions) + sum(block_seconds(b) for b in blocks) + sum(s.tempo_total_segundos for s in simulations)
    trend = "SEM COMPARAÇÃO"
    trend_reason = "O período Total não possui um período anterior equivalente. Selecione Semana, Mês ou Ano."
    if periodo != "total":
        # Compare equal elapsed windows, not a partial current month with an entire past month.
        if periodo == "semana": previous = start - timedelta(days=7)
        elif periodo == "mes":
            loc = start.replace(tzinfo=__import__('datetime').timezone.utc).astimezone(TZ)
            previous = month_bounds(loc.year - (loc.month == 1), (loc.month - 2) % 12 + 1)[0]
        else:
            loc = start.replace(tzinfo=__import__('datetime').timezone.utc).astimezone(TZ)
            previous = utc_naive(loc.replace(year=loc.year-1))
        prevend = min(start, previous + (end-start))
        before = load(models.BlocoQuestoes, models.BlocoQuestoes.data, previous, prevend) + sims(previous, prevend)
        valid_before=[x for x in before if valid_questions(x)]
        previous_total=sum(x.total_questoes for x in valid_before)
        trend_reason=(f'Comparação com o mesmo trecho do período anterior: atual {total} questões em {len(items)} registros; '
                      f'anterior {previous_total} questões em {len(valid_before)} registros. São necessários 20 questões e 2 registros em cada trecho.')
        if total == 0: trend = 'SEM PRÁTICA'
        elif total < 20 or len(items) < 2: trend = 'AMOSTRA INSUFICIENTE'
        elif previous_total < 20 or len(valid_before) < 2: trend = 'HISTÓRICO INSUFICIENTE'
        if total>=20 and len(items)>=2 and sum(x.total_questoes for x in valid_before)>=20 and len(valid_before)>=2:
            diff = round(score - precisao(before), 10)
            trend = "ASCENDENTE" if diff > .05 else "DECLÍNIO" if diff < -.05 else "ESTÁVEL"
            trend_reason = f'{score*100:.1f}% agora e {precisao(before)*100:.1f}% no mesmo trecho anterior ({diff*100:+.1f} pontos percentuais). Variações de até 5 pontos são tratadas como estáveis.' 
    groups = defaultdict(list)
    for b in blocks:
        if valid_questions(b): groups[b.assunto_id].append(b)
    attention = [str(a) for a, rows in groups.items() if sum(b.total_questoes for b in rows) >= 20 and len(rows) >= 2 and precisao(rows)<.7]
    recommendation = []  # Populated by the shared study-analysis service below.
    result=dict(horas_liquidas=round(seconds/3600,2), total_questoes=total, total_acertos=hits,
        percentual_medio=round(score*100,2), ipr_geral=round(score*100,2), tendencia=trend,
        tendencia_contexto=trend_reason, status_missao="SEM PRÁTICA REGISTRADA" if not total else "ESTUDOS REGISTRADOS",
        assuntos_criticos=attention, status_horas="SEM META DE PERÍODO", status_questoes="SEM META DE PERÍODO",
        recomendacao=recommendation, tem_evidencia=bool(total), amostra_blocos=len(blocks),
        meta_horas=None, meta_questoes=None, versao_metrica="precisao_v2", registros_inconsistentes=invalid)
    if periodo=='semana':
        from .goals import week_view, status
        week=week_view(db)
        result['contexto_meta']='Metas semanais; precisão é um indicador separado de aprendizagem.'
        if week['parcial']:result['contexto_meta']+=' Primeira semana: meta reduzida aos dias restantes; registros de toda a semana contam.'
        if materia_id:
            goal=next((g for g in week['materias'] if g['materia_id']==str(materia_id)),None)
            if goal:
                target=goal['meta_minutos'];fraction=target/week['meta_minutos'] if week['meta_minutos'] else 0
                result.update(meta_horas=round(target/60,2),status_horas=status(seconds/60,target,week['esperado_minutos']*fraction),status_missao='COTA SEMANAL ATINGIDA' if target and seconds/60>=target else 'COTA SEMANAL EM ANDAMENTO')
                result['variante_missao']='success' if target and seconds/60>=target else 'default'
        else:
            result.update(meta_horas=round(week['meta_minutos']/60,2),meta_questoes=week['meta_questoes'],status_horas=week['status']['horas'],
                status_questoes=week['status']['questoes'],status_missao=week['status_missao'])
            result['variante_missao']='success' if week['status_missao']=='METAS DA SEMANA CONCLUÍDAS' else 'warning' if week['status_missao'] in ('AJUSTAR PLANO','RETOMAR O RITMO') else 'default'
    if periodo in ('mes', 'ano'):
        from .goals import week_view
        week = week_view(db)
        factor = 4 if periodo == 'mes' else 48
        def period_status(actual, target):
            return 'SEM META' if target <= 0 else 'META ATINGIDA' if actual >= target else 'EM ANDAMENTO'
        result['contexto_meta'] = f'Metas do período = {factor} × a meta semanal atual, incluindo ajustes. Precisão não é multiplicada.'
        if materia_id:
            goal = next((g for g in week['materias'] if g['materia_id'] == str(materia_id)), None)
            if goal:
                target = goal['meta_minutos'] * factor
                result.update(meta_horas=round(target/60, 2), status_horas=period_status(seconds/60, target))
            result['contexto_meta'] += ' Questões não possuem meta individual por matéria.'
        else:
            minutes = week['meta_minutos'] * factor
            questions = week['meta_questoes'] * factor
            result.update(meta_horas=round(minutes/60, 2), meta_questoes=questions,
                          status_horas=period_status(seconds/60, minutes),
                          status_questoes=period_status(total, questions))
    from .study_analysis import dashboard_guidance
    result.update(dashboard_guidance(db, blocks, materia_id))
    from .study_strategy import study_strategy
    result["recomendacoes_estudo"] = study_strategy(seconds/3600, total, round(score*100,2), len(items), sessions)
    result["recomendacao"] = result["recomendacoes_estudo"]
    return result
