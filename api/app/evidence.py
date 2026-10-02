"""Evidence supports methods, not a scientifically prescribed weekly dose."""
SOURCES = {
    'recuperacao': {'titulo':'Dunlosky et al. (2013)', 'url':'https://www.psychologicalscience.org/publications/journals/pspi/learning-techniques.html',
        'limite':'Revisão de técnicas de aprendizagem; não define horas ou questões semanais para a EsPCEx.'},
    'espacamento': {'titulo':'Cepeda et al. (2008)', 'url':'https://www.yorku.ca/ncepeda/publications/CVRWP2008.pdf',
        'limite':'Experimento com aprendizagem de fatos; não valida os intervalos fixos usados neste aplicativo para todas as disciplinas.'},
    'feedback': {'titulo':'Metcalfe (2017)', 'url':'https://www.annualreviews.org/content/journals/10.1146/annurev-psych-010416-044022',
        'limite':'Revisão sobre aprendizagem com erros e feedback; não permite diagnosticar automaticamente a causa do seu erro.'},
    'escola': {'titulo':'Carpenter, Pashler e Cepeda (2009)', 'url':'https://www.yorku.ca/ncepeda/publications/CPC2009.pdf',
        'limite':'Estudo com fatos de História no 8º ano; resultados não são garantia individual nem previsão de aprovação.'},
}

def guidance(activity):
    if activity=='ANALISE_ERROS':
        title='Corrigir o raciocínio, não apenas copiar o gabarito';source='feedback'
        steps=['Tente novamente uma questão errada antes de ver a solução.',
            'Compare os passos e localize onde seu raciocínio divergiu.',
            'Explique a correção com suas palavras e resolva uma questão semelhante.',
            'Se ainda travar, registre um próximo passo específico para o retorno.']
    elif activity=='TEORIA':
        title='Estudar e verificar o que ficou';source='recuperacao'
        steps=['Leia um trecho específico e acompanhe um exemplo resolvido.',
            'Feche o material e explique a ideia ou reconstrua o exemplo.',
            'Confira as lacunas e tente uma aplicação sem consulta.',
            'Registre o ponto exato de continuação, se necessário.']
    else:
        title='Recuperar da memória e conferir';source='recuperacao' if activity=='QUESTOES' else 'espacamento'
        steps=['Tente as questões sem consultar a solução.',
            'Confira o gabarito e o raciocínio, inclusive nos acertos por dúvida.',
            'Reveja apenas a teoria necessária para corrigir os erros.',
            'Retorne em outro dia pela fila; não é preciso usar flashcards.']
    return dict(titulo=title,passos=steps,fonte=SOURCES[source])
