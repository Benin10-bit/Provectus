"""Evidence-informed methods; numerical cutoffs are product heuristics."""
from .clock import local_date
from .metrics import session_seconds


def study_strategy_details(hours, questions, accuracy, records, sessions=()):
    rows = []
    def add(title, reason, steps, source):
        rows.append(dict(titulo=title, motivo=reason, passos=steps, source=source))

    if questions <= 0:
        add('Verifique o que consegue aplicar',
            f'Há {hours:.1f}h registradas, mas nenhuma questão válida neste período.' if hours else 'Ainda não há tempo nem questões registrados neste período; não é possível avaliar seu estudo.',
            ['Escolha o assunto atual do ciclo, estude um trecho e feche o material.',
             'Explique a ideia de memória e tente uma pequena seleção de questões. Confira as soluções e registre tempo, total e acertos.',
             'Se não souber começar, consulte um exemplo resolvido, explique cada passo e tente outra questão sem olhar.'], 'recuperacao')
    elif questions < 20 or records < 2:
        add('Confirme o resultado em novas tentativas',
            f'Você acertou {accuracy:.0f}% em {questions} questões, distribuídas em {records} registro(s). A amostra ainda é limitada para uma avaliação consistente.',
            ['Corrija os erros desta tentativa e resolva questões do mesmo assunto em outra sessão, sem consultar respostas.',
             'Compare tentativas de dificuldade semelhante. Não reduza revisões nem recomece toda a teoria por causa de um único resultado.'], 'recuperacao')
    elif accuracy < 70:
        add('Corrija antes de aumentar o volume',
            f'Nos {questions} exercícios registrados, a precisão foi {accuracy:.0f}%. Há erros suficientes para priorizar a correção, mas a média não identifica quais assuntos causaram dificuldade.',
            ['Neste ciclo, dê mais espaço à correção e à consolidação dentro da carga atual, antes de buscar mais questões ou mais horas.',
             'Use os resultados por assunto para direcionar esse tempo: uma média baixa não justifica refazer toda a teoria de todas as matérias.',
             'Reavalie essa prioridade quando novas tentativas comparáveis mostrarem que os erros deixaram de se repetir; um aumento isolado na média não comprova evolução.'], 'feedback')
    else:
        add('Verifique se os acertos se mantêm',
            f'Sua precisão foi {accuracy:.0f}% em {questions} questões. '+('Ainda há lacunas a investigar.' if accuracy < 80 else 'É um resultado favorável nesta amostra, não uma confirmação de domínio.'),
            ['Revise os erros e também os acertos por chute ou dúvida; explique por que a alternativa correta funciona.',
             'Em outro dia, resolva uma seleção sem consulta e de dificuldade semelhante. Se os mesmos erros voltarem, retome o conceito específico.',
             'Se conseguir explicar e repetir o acerto, avance no ciclo mantendo retornos espaçados. Não aumente a velocidade sacrificando a precisão.'], 'feedback')

    if questions > 0:
        add('Dê finalidade ao volume e ao tempo',
            f'Foram {questions} questões e {hours:.1f}h de estudo registradas. O tempo geral inclui outras atividades e não permite concluir se você está rápido ou lento.',
            ['Não aumente a carga apenas para melhorar o contador. Primeiro verifique se a rotina atual comporta prática, correção e retornos sem acumular dúvidas.',
             'Se os erros continuarem recorrentes, redistribua parte do tempo de conteúdo novo para consolidação, em vez de acrescentar horas.' if accuracy < 80 else 'Se os acertos se mantiverem em dias diferentes e as correções couberem na rotina, experimente um aumento pequeno de prática dentro das janelas disponíveis; compare os resultados antes de manter a mudança.',
             'A quantidade ideal não pode ser deduzida desses totais. Use capacidade de resolver sem ajuda e constância dos registros para decidir se o volume está servindo à aprendizagem.'], 'feedback')

    total = sum(session_seconds(s) for s in sessions)
    theory = sum(session_seconds(s) for s in sessions if (s.atividade or s.tipo_sessao) == 'TEORIA')
    if total and theory / total >= .7:
        add('Intercale teoria com recuperação',
            f'{theory / total:.0%} do tempo das sessões registradas foi classificado como teoria. Isso descreve seus registros, não uma proporção ideal de estudo.',
            ['Após um trecho curto, feche o material e explique o conceito ou resolva uma aplicação.',
             'Use a dificuldade encontrada para escolher o que reler. Se não consegue começar, examine um exemplo e tente reconstruí-lo sem consulta.'], 'recuperacao')
    dates = {local_date(s.data) for s in sessions if session_seconds(s) > 0}
    if questions or total:
        add('Teste a retenção em outro dia',
            'As sessões registradas neste período estão concentradas em um único dia.' if len(dates) == 1 else f'Há sessões registradas em {len(dates)} dias neste período; isso não mostra se cada assunto foi retomado.' if dates else 'Há questões, mas não há sessões com duração positiva para avaliar a distribuição do estudo.',
            ['Escolha um erro ou conceito trabalhado e retome em outro dia, começando por uma tentativa sem consulta.',
             'Se lembrar e aplicar, aumente gradualmente o intervalo. Se falhar, confira o raciocínio e faça um retorno mais próximo.',
             'Use a lista de revisão para organizar esses retornos. Conseguir reler uma solução não substitui conseguir resolvê-la sozinho.'], 'espacamento')
    return rows


def study_strategy(*args, **kwargs):
    return [' '.join([r['motivo'], *r['passos']]) for r in study_strategy_details(*args, **kwargs)]
