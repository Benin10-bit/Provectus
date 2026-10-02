def tags(q):
    return ({'status:'+q['status'],'bank:'+str(q.get('banca_normalizada')),'difficulty:'+str(q.get('dificuldade_normalizada')),'options:'+str(len(q['alternativas'])),'multipage:'+str(q['pagina_inicio']!=q['pagina_fim']),'images:'+str(bool(q['imagens'])),'graphical_options:'+str(any(not a['texto'] and a['imagens'] for a in q['alternativas']))}
        | {'warning:'+w['code'] for w in q['warnings']})

def select_sample(questions,size):
    selected=[q for q in questions if q['status']=='ERROR'];covered=set().union(*(tags(q) for q in selected)) if selected else set()
    remaining=[q for q in questions if q not in selected]
    while remaining and (len(selected)<min(size,len(questions)) or any(tags(q)-covered for q in remaining)):
        best=max(remaining,key=lambda q:(len(tags(q)-covered),q['status']=='REVIEW',-q['source_ordinal']))
        selected.append(best);remaining.remove(best);covered|=tags(best)
    return selected
