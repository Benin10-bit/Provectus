"""Operational coaching for recorded blocks, separate from strategic overview."""
from collections import defaultdict
from . import models
from .clock import local_date
from .metrics import valid_questions, precisao, session_seconds, limites_periodo
from .study_analysis import performance_change, session_url
from .evidence import SOURCES


def block_guidance(db):
    lo, hi = limites_periodo('semana')
    blocks = db.query(models.BlocoQuestoes).filter(models.BlocoQuestoes.data >= lo, models.BlocoQuestoes.data < hi).all()
    grouped = defaultdict(list)
    for b in blocks:
        if valid_questions(b) and b.assunto and b.materia and b.materia.ativa and b.assunto.materia_id == b.materia_id:
            grouped[(b.materia_id, b.assunto_id)].append(b)
    out = []
    for (mid, aid), rows in sorted(grouped.items(), key=lambda item: precisao(item[1]))[:3]:
        recent = sorted(rows, key=lambda b: (b.data, str(b.id)))
        last = recent[-1]
        score = precisao(rows) * 100
        errors = last.total_questoes - last.total_acertos
        reason = f'{last.materia.nome} · {last.assunto.nome}: último bloco em {local_date(last.data):%d/%m}, {last.total_acertos}/{last.total_questoes} acertos'
        reason += f' em {last.tempo_total_segundos / 60:.0f} minutos.' if last.tempo_total_segundos > 0 else '; duração não registrada.'
        reason += f' Na semana: {score:.0f}% em {len(rows)} bloco(s).'
        change = performance_change(rows)
        if change:
            title, activity, evidence, task = change
            reason += ' ' + evidence
            steps = [task, 'Mantenha assunto e dificuldade semelhantes no próximo registro e compare precisão e tempo por questão. Essa comparação não demonstra a causa da mudança.']
        elif errors:
            title, activity = 'Ajuste o próximo bloco', 'REVISAO'
            size = max(1, last.total_questoes // 2)
            steps = [f'No último bloco houve {errors} erro(s); os registros não dizem quais já foram corrigidos. Comece pelos ainda não resolvidos e identifique o passo em que travou.']
            if last.total_acertos / last.total_questoes < .7:
                steps.append(f'Experimente {size} questões novas do mesmo assunto no próximo bloco, em vez de {last.total_questoes}, usando o restante da janela para trabalhar esses erros. É um ajuste inicial, não uma quantidade ideal científica.')
            else:
                steps.append(f'Mantenha inicialmente até {last.total_questoes} questões, mas pare antes se a correção não couber na janela. Não amplie o bloco com erros ainda sem explicação.')
            steps.append('Se o erro for conceitual, consulte um exemplo; se for procedimento, reconstitua os passos. Encerre tentando uma questão equivalente sem ajuda e registre o resultado.')
        else:
            title, activity = 'Teste além deste bloco', 'QUESTOES'
            steps = [f'O último bloco teve {last.total_questoes} acertos e nenhum erro registrado. Faça uma nova seleção do mesmo tamanho e nível, em outro dia, para verificar se o resultado se repete.', 'Se acertou por dúvida, inclua esse raciocínio no retorno. Se o resultado se mantiver sem ajuda, varie os exercícios antes de aumentar quantidade ou dificuldade.']
        if len(rows) < 2 or sum(b.total_questoes for b in rows) < 20:
            reason += ' Pouca evidência por assunto: o ajuste é provisório.'
        out.append(dict(titulo=title+' · '+last.assunto.nome, motivo=reason, passos=steps,
                        destino=session_url(dict(materia_id=str(mid), assunto_id=str(aid), atividade=activity, tarefa=steps[0])), fonte=SOURCES['feedback']))

    sessions = db.query(models.SessaoEstudo).filter(models.SessaoEstudo.data >= lo, models.SessaoEstudo.data < hi).all()
    long = sorted([s for s in sessions if session_seconds(s) >= 90*60], key=session_seconds, reverse=True)
    if long:
        s = long[0]; minutes = session_seconds(s)/60
        out.append(dict(titulo='Experimente dividir a sessão mais longa', motivo=f'A sessão de {local_date(s.data):%d/%m} registrou {minutes:.0f} minutos líquidos. Isso não prova cansaço nem baixa qualidade.',
            passos=[f'Se foi difícil manter a atenção, teste duas partes de aproximadamente {minutes/2:.0f} minutos, com uma pausa entre elas, sem aumentar o tempo líquido planejado.', 'Defina um resultado para cada parte: uma aplicação resolvida ou um erro explicado. Compare foco registrado e capacidade de resolver ao final antes de manter a mudança. A divisão é uma experiência, não um intervalo ideal universal.'], destino='/estudar', fonte=SOURCES['recuperacao']))
    if not out:
        out.append(dict(titulo='Prepare um bloco que possa ser avaliado', motivo='Não há blocos válidos por assunto nesta semana para sugerir uma mudança de tamanho ou de ritmo.',
            passos=['No assunto atual, escolha uma pequena seleção da mesma dificuldade e registre o tempo efetivo das tentativas, quantidade e acertos.', 'Registre a correção na sessão correspondente. Quando houver outra tentativa comparável, será possível examinar alterações de precisão e tempo sem confundir matérias diferentes.'], destino='/estudar', fonte=SOURCES['recuperacao']))
    return out
