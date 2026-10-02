from collections import Counter
from .extraction import dump

def inspect_pages(meta,pages,root):
    fonts=Counter((s['font'],round(s['size'],2)) for p in pages for l in p['lines'] for s in l['spans'])
    result={**meta,'fonts':[{'font':k[0],'size':k[1],'spans':v} for k,v in fonts.items()],
        'native_question_markers':sum(l['text'].startswith('Questão ') for p in pages for l in p['lines']),
        'native_answer_markers':sum(l['text'].startswith('Gabarito:') for p in pages for l in p['lines']),
        'content_image_occurrences':sum(len(p['objects']) for p in pages),
        'drawings':sum(len(p['drawings']) for p in pages),
        'pages_without_native_content':[p['page'] for p in pages if not p['text'].strip()]}
    dump(root/'inspection.json',result)
    return result
