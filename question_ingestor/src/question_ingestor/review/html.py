import html,json
from .sample import select_sample

def render_segments(segments):
    out=[];line=None
    for s in segments:
        if s.get('line_id')!=line:
            if line is not None:out.append('</div>')
            out.append('<div class="content-line">');line=s.get('line_id','line')
        if s['kind']=='text':
            tag='sup' if s.get('script')=='sup' else 'span'
            value=html.escape(s['text'])
            if s.get('bold'):value=f'<strong>{value}</strong>'
            out.append(f'<{tag}>'+value+f'</{tag}>')
        else:
            inline=s.get('display')=='inline';box=s['bbox'];font=s.get('font_size',9)
            height=max(.1,(box[3]-box[1])/font)
            css=f'height:{height:.4f}em;width:auto;max-width:none;vertical-align:baseline' if inline else 'display:block;max-width:100%;height:auto'
            out.append(f'<img class="{"inline-visual" if inline else "block-visual"}" src="{html.escape(s.get("asset_path",""))}" style="{css}" alt="{html.escape(s.get("role","visual"))}">')
    if line is not None:out.append('</div>')
    return ''.join(out)

def generate(questions,root,cfg):
    chosen=select_sample(questions,cfg.review_sample_size);ids={q['extraction_id'] for q in chosen}
    def esc(t):return html.escape(str(t or ''))
    def imgs(items):return ''.join(f'<figure><img loading="lazy" src="{esc(a["path"])}"><figcaption>p{a["page"]} · {esc(a["type"])} · {a["hash"][:12]}</figcaption></figure>' for a in items)
    rows=[]
    for q in questions:
        options=''.join(f'<div class="option"><b>{a["letra"]})</b>{render_segments(a.get("segments",[]))}</div>' for a in q['alternativas'])
        statement=render_segments(q.get('statement',{}).get('segments',[]))
        candidates=[{'page':seg['page'],'bbox':seg['bbox'],**seg['recovery_candidate']} for seg in q['content'] if 'recovery_candidate' in seg]
        candidate_html=('<details><summary>Sugestões de glifos — não aplicadas, confirmação necessária</summary><pre>'+esc(json.dumps(candidates,ensure_ascii=False,indent=2))+'</pre></details>') if candidates else ''
        sample=q['extraction_id'] in ids
        flags=[]
        if q['status']=='OK' and q['metadata'].get('previous_status')=='REVIEW':flags.append('CHANGED_TO_OK')
        if q['gabarito'] is None:flags.append('MISSING_ANSWER')
        if any(s.get('display')=='inline' for s in q['content']):flags.append('INLINE_MATH')
        if any('GLYPH' in w['code'] for w in q['warnings']):flags.append('INVALID_GLYPH')
        if any('OVERLAP' in w['code'] for w in q['warnings']):flags.append('OVERLAP')
        if any('OCR' in w['code'] for w in q['warnings']):flags.append('OCR')
        rows.append(f'''<article id="q{q['source_ordinal']}" data-flags="{' '.join(flags)}" data-status="{q['status']}" data-sample="{str(sample).lower()}"><h2>Questão {q.get('numero_original')} · {q['status']} {'· AMOSTRA' if sample else ''}</h2><p>{esc(q.get('banca_original'))} · {esc(q.get('dificuldade_original'))} · p{q['pagina_inicio']}–{q['pagina_fim']}</p><div class="compare"><section><h3>Estrutura extraída</h3><div>{statement}</div>{options}<p><b>Gabarito: {esc(q['gabarito']) or 'AUSENTE'}</b></p>{candidate_html}<details><summary>Warnings e regras</summary><pre>{esc(json.dumps({'warnings':q['warnings'],'confidence':q['confidence'],'evidence':q['confidence_evidence']},ensure_ascii=False,indent=2))}</pre></details></section><section><h3>Recortes da fonte · marcas repetidas removidas</h3>{imgs(q['originals'])}</section></div></article>''')
    page='''<!doctype html><html lang="pt-BR"><meta charset="utf-8"><title>Auditoria do piloto</title><style>body{font:16px system-ui;background:#f3f5f4;color:#18221d;max-width:1500px;margin:auto;padding:24px}header{position:sticky;top:0;background:#f3f5f4;padding:12px;z-index:1}article{background:white;padding:22px;margin:24px 0;border:1px solid #ccd5cf}.compare{display:grid;grid-template-columns:1fr 1fr;gap:28px}section{min-width:0}img{max-width:100%;height:auto}figure{margin:12px 0}figcaption{font-size:12px;color:#58665d}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:inherit}.content-line{white-space:pre-wrap;line-height:1.7}.inline-visual{display:inline!important}.block-visual{margin:8px 0}.option{padding:12px;border-bottom:1px solid #ddd}button,select,input{padding:8px}article[hidden]{display:none}@media(max-width:800px){.compare{grid-template-columns:1fr}}</style><header><h1>Auditoria do documento</h1><p>OK significa aprovação pelas regras automáticas, não aprovação humana. Fonte visual sanitizada, sem correção de conteúdo.</p><label>Status <select id="status"><option>Todos</option><option>OK</option><option>REVIEW</option><option>ERROR</option></select></label> <label><input id="sample" type="checkbox" checked>Somente amostra</label> <label>Categoria <select id="category"><option>Todos</option><option>CHANGED_TO_OK</option><option>MISSING_ANSWER</option><option>INLINE_MATH</option><option>INVALID_GLYPH</option><option>OVERLAP</option><option>OCR</option></select></label> <label>Questão <input id="number" type="number" min="1" style="width:80px"></label><p id="count"></p></header>'''+''.join(rows)+'''<script>function filter(){let n=0;document.querySelectorAll('article').forEach(a=>{a.hidden=(category.value!=='Todos'&&!a.dataset.flags.split(' ').includes(category.value))||(statusSelect.value!=='Todos'&&a.dataset.status!==statusSelect.value)||(sample.checked&&a.dataset.sample!=='true')||(number.value&&a.id!=='q'+number.value);if(!a.hidden)n++});count.textContent=n+' questões exibidas'}const category=document.querySelector('#category');const statusSelect=document.querySelector('#status'),sample=document.querySelector('#sample'),number=document.querySelector('#number'),count=document.querySelector('#count');[statusSelect,sample,number,category].forEach(e=>e.addEventListener('input',filter));filter()</script></html>'''
    (root/'audit.html').write_text(page,encoding='utf8')
    (root/'review_sample.json').write_text(json.dumps([{'numero_original':q.get('numero_original'),'extraction_id':q['extraction_id'],'status':q['status'],'tags':sorted(__import__('question_ingestor.review.sample',fromlist=['tags']).tags(q))} for q in chosen],ensure_ascii=False,indent=2))
    return len(chosen)
