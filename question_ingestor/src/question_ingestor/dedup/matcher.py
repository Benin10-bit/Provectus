"""Local candidate detector. No deletions and no automatic confirmation."""
import hashlib,json
from difflib import SequenceMatcher
from .normalization import normalize

def signature(q):
    return {'text':normalize(q['enunciado']), 'bank':q.get('banca_normalizada'),
        'alternatives':[(a['letra'],normalize(a['texto'] or '')) for a in q['alternativas']],
        'images':[a['hash'] for a in q['imagens']]+[i['hash'] for a in q['alternativas'] for i in a['imagens']]}

def candidates(questions,threshold=.94):
    # Quadratic comparison is intentionally restricted to this small pilot. Global phase needs blocking/indexing.
    out=[];sigs=[signature(q) for q in questions]
    for i,a in enumerate(sigs):
        for j in range(i+1,len(sigs)):
            b=sigs[j];score=SequenceMatcher(None,a['text'],b['text'],autojunk=False).ratio()
            exact=a==b
            if (a['text'] and a['text']==b['text']) or (a['bank']==b['bank'] and score>=threshold):
                out.append({'question_a':questions[i]['extraction_id'],'question_b':questions[j]['extraction_id'],'status':'POSSIBLE_DUPLICATE','score':score,'evidence':{'text_hash_equal':hashlib.sha256(a['text'].encode()).digest()==hashlib.sha256(b['text'].encode()).digest(),'bank_equal':a['bank']==b['bank'],'alternatives_equal':a['alternatives']==b['alternatives'],'asset_hashes_equal':a['images']==b['images'],'full_signature_equal':exact}})
    return out
