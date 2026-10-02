"""Shared descriptive rules, not diagnoses or scientifically calibrated cutoffs."""
from collections import defaultdict
from urllib.parse import urlencode
from .metrics import valid_questions, precisao

MIN_QUESTIONS = 20
MIN_RECORDS = 2

def sufficient(rows):
    return len(rows) >= MIN_RECORDS and sum(x.total_questoes for x in rows) >= MIN_QUESTIONS

def critical(rows):
    return sufficient(rows) and precisao(rows) < .70

def performance_change(rows):
    """Compare two pairs on one topic at the same recorded difficulty."""
    recent = sorted(rows, key=lambda b:(b.data,str(b.id)))[-4:]
    if len(recent) < 4 or any(b.dificuldade is None for b in recent) or len({b.dificuldade for b in recent}) != 1:
        return None
    before, after = recent[:2], recent[2:]
    if not sufficient(before) or not sufficient(after):return None
    delta=round(precisao(after)-precisao(before),10)
    if delta < -.10:
        return ('QUEDA RECENTE', 'REVISAO', 'A precisão caiu mais de 10 pontos entre dois pares de tentativas na mesma dificuldade registrada.',
                'Refaça os erros recentes sem consulta, compare as soluções e teste o mesmo raciocínio em questões novas.')
    if all(b.tempo_total_segundos > 0 for b in recent) and precisao(after) >= .70 and abs(delta) <= .05:
        old=sum(b.tempo_total_segundos for b in before)/sum(b.total_questoes for b in before)
        new=sum(b.tempo_total_segundos for b in after)/sum(b.total_questoes for b in after)
        if new > old * 1.25:
            return ('TEMPO EM ALTA', 'QUESTOES', 'O tempo por questão aumentou mais de 25%, com precisão estável e mesma dificuldade registrada; as questões podem ser diferentes.',
                    'Faça um pequeno bloco cronometrado do mesmo nível; identifique onde gasta tempo e confira o raciocínio antes de buscar velocidade.')
    return None

def session_url(row):
    params={k:row[v] for k,v in [('materia','materia_id'),('assunto','assunto_id'),('atividade','atividade'),('tarefa','tarefa')]}
    if row.get('acao_id'):params['acao']=row['acao_id']
    return '/estudar?'+urlencode(params)

def dashboard_guidance(db, blocks, materia_id=None):
    from . import models
    from .planner import coverage, review_items
    from uuid import UUID
    topics=coverage(UUID(str(materia_id)) if materia_id else None,db)
    topic_map={t['id']:t for t in topics}
    names={str(m.id):m.nome for m in db.query(models.Materia).filter(models.Materia.ativa.is_(True)).all()}
    grouped=defaultdict(list)
    for b in blocks:
        topic=topic_map.get(str(b.assunto_id))
        if topic and topic['materia_id']==str(b.materia_id) and valid_questions(b):grouped[str(b.assunto_id)].append(b)
    details=[]
    for id,rows in grouped.items():
        if not critical(rows):continue
        t=topic_map[id]
        task='Refaça alguns erros sem consulta, confira a solução e resolva questões semelhantes antes de avançar.'
        row=dict(assunto_id=id,assunto=t['nome'],materia_id=t['materia_id'],materia=names[t['materia_id']],
                 precisao=round(precisao(rows)*100,2),questoes=sum(b.total_questoes for b in rows),registros=len(rows),atividade='REVISAO',tarefa=task)
        row['destino']=session_url(row);details.append(row)
    details.sort(key=lambda x:(x['precisao'],-x['questoes'],x['assunto_id']))
    assessed=sum(sufficient(rows) for rows in grouped.values())
    context=(f'{assessed} assunto(s) com amostra suficiente no período; critério: menos de 70% em pelo menos 20 questões e 2 registros.'
             if assessed else 'Amostra insuficiente por assunto neste período: são necessárias 20 questões em pelo menos 2 registros. Simulados globais não identificam assuntos.')
    if assessed and not details:context='Nenhum assunto abaixo do critério entre os avaliáveis. '+context
    # Same queue, task, due dates and ordering as Estudar Agora; never generate database obligations.
    available=[r for r in review_items(db,topics) if r['disponivel']]
    cards=[];seen=set()
    for r in available:
        if r['assunto_id'] in seen:continue
        seen.add(r['assunto_id'])
        t=topic_map[r['assunto_id']]
        is_critical=t['questoes_recentes']>=MIN_QUESTIONS and t['blocos_recentes']>=MIN_RECORDS and t['precisao'] is not None and t['precisao']<70
        tone='critical' if is_critical else 'warning' if r['prioridade']<=3 else 'default'
        cards.append(dict(id=r['id'],categoria='Revisão prioritária' if r['prioridade']<=3 else 'Verificar retenção' if r['atividade']=='REVISAO' else 'Ampliar evidência',
            prioridade=r['prioridade'],variante=tone,materia=r['materia'],assunto=r['assunto'],
            motivo=r['motivo'],acao=r['tarefa'],destino=session_url(r)))
        if len(cards)==3:break
    if not cards:
        has_contacts=any(t['ultimo_contato'] for t in topics)
        cards=[dict(id='orientacao-inicial',categoria='Próximo passo',prioridade=9,variante='default',materia='',assunto='',
            motivo='Não há retomadas disponíveis agora. Isso não comprova domínio.' if has_contacts else 'Ainda não há histórico suficiente para orientar uma revisão por assunto.',
            acao='Escolha o próximo assunto do ciclo, tente uma aplicação sem consulta e registre o resultado para orientar o próximo retorno.',destino='/estudar')]
    status='ASSUNTOS EXIGEM ATENÇÃO' if details else 'REVISÃO PRIORITÁRIA' if available and available[0]['prioridade']<=3 else 'SEM ALERTAS NA AMOSTRA' if assessed else 'DADOS INSUFICIENTES'
    return dict(assuntos_criticos=[d['assunto_id'] for d in details],assuntos_criticos_detalhes=details,
                criticidade_contexto=context,status_academico=status,variante_academica='critical' if details else 'warning' if status=='REVISÃO PRIORITÁRIA' else 'default',
                orientacoes=cards,recomendacao=[f"{r['materia']} · {r['assunto']}: {r['motivo']} {r['acao']}" if r['assunto'] else r['acao'] for r in cards])
