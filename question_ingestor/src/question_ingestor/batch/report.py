import json,time
from collections import Counter
from ..pdf.extraction import dump

def global_report(db,out,job,found,elapsed):
    states=Counter(r[0] for r in db.execute('SELECT state FROM batch_items WHERE job_id=?',(job,)))
    metrics=Counter();warnings=Counter();materias=Counter();paths=Counter();banks=Counter();difficulties=Counter();problems={'FAILED_DOCUMENTS':[],'UNEXPECTED_LAYOUT':[],'DOCUMENTS_WITH_REVIEW':[],'DOCUMENTS_WITH_ERROR':[],'MISSING_ANSWER':[],'SOURCE_DEFECTS':[]}
    durations=[]
    for sha,path,materia,cp,status,report,error,duration in db.execute('SELECT sha256,relative_path,materia,content_path,processing_status,report_json,error_code,processing_duration FROM documents'):
        item={'sha256':sha,'relative_path':path,'error_code':error,'report':f'documents/{sha}/report.md','audit':f'documents/{sha}/audit.html'}
        if status!='DONE':
            problems['FAILED_DOCUMENTS'].append(item)
            if error=='UnsupportedLayout':problems['UNEXPECTED_LAYOUT'].append(item)
            continue
        r=json.loads(report);durations.append(duration or 0)
        for key in ['pages','questions_found','questions_ok','questions_review','questions_error','answers_found','multipage_questions','questions_with_images']:metrics[key]+=r[key]
        warnings.update(r['warnings_by_type']);materias[materia or 'UNKNOWN']+=r['questions_found'];paths[json.dumps([materia]+json.loads(cp or '[]'),ensure_ascii=False)]+=r['questions_found'];banks.update(r['banks_found']);difficulties.update(r['difficulties'])
        if r['questions_review']:problems['DOCUMENTS_WITH_REVIEW'].append({**item,'count':r['questions_review']})
        if r['questions_error']:problems['DOCUMENTS_WITH_ERROR'].append({**item,'count':r['questions_error']})
        if r['answers_found']<r['questions_found']:problems['MISSING_ANSWER'].append({**item,'count':r['questions_found']-r['answers_found']})
        defects={k:v for k,v in r['warnings_by_type'].items() if ('SOURCE' in k or 'GLYPH' in k) and k!='SOURCE_OVERLAP_RECOVERED'}
        if defects:problems['SOURCE_DEFECTS'].append({**item,'warnings':defects})
        if any(k in r['warnings_by_type'] for k in ['UNEXPECTED_LAYOUT','UNEXPECTED_HEADER_LAYOUT','UNEXPECTED_ALTERNATIVE_LAYOUT']):problems['UNEXPECTED_LAYOUT'].append(item)
    result={'job_id':job,'documents_discovered':found,'run_states':dict(states),'documents_done':db.execute("SELECT count(*) FROM documents WHERE processing_status='DONE'").fetchone()[0],'documents_failed':len(problems['FAILED_DOCUMENTS']),'documents_skipped':states['SKIPPED'],'documents_unsupported_unexpected':len(problems['UNEXPECTED_LAYOUT']),**dict(metrics),'missing_answers':metrics['questions_found']-metrics['answers_found'],'warnings_by_type':dict(warnings),'by_materia':dict(materias),'by_content_path':dict(paths),'by_bank':dict(banks),'by_difficulty':dict(difficulties),'elapsed_seconds':round(elapsed,3),'average_successful_processing_seconds':round(sum(durations)/len(durations),3) if durations else 0,'problems':problems,'scope':'counts include all DONE documents in this staging; run_states describe this invocation'}
    dump(out/'reports/global.json',result)
    md='# Relatório global\n\nContagens abrangem documentos DONE do staging. Falhas preservam a versão anterior, mas ela não entra nestes totais.\n\n'+''.join(f'- **{k}**: {json.dumps(v,ensure_ascii=False)}\n' for k,v in result.items() if k!='problems')
    for title,items in problems.items():md+='\n## '+title+'\n\n'+('Nenhum.\n' if not items else ''.join('- '+json.dumps(i,ensure_ascii=False)+'\n' for i in items))
    (out/'reports/global.md').write_text(md,encoding='utf8');return result
