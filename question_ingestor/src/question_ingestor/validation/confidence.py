"""Rule coverage, not probabilities. Failures are explicit and never averaged into OK."""
def confidence(q):
    codes={w['code'] for w in q['warnings']}
    components={
        'header':{'parsed':'HEADER_PARSE_FAILURE' not in codes,'bank_present':bool(q.get('banca_original')),'difficulty_present':bool(q.get('dificuldade_original')),'expected_typography':q['metadata']['header_typography_ok']},
        'statement':{'native_text_present':bool(q['enunciado'].strip()),'minimum_length':'VERY_SHORT_STATEMENT' not in codes,'no_suspect_formula':not any(w['code']=='POSSIBLE_MISSING_FORMULA' and w['component']=='statement' for w in q['warnings']),'no_invalid_glyph':not any(w['code'] in ('INVALID_TEXT_GLYPH','UNRESOLVED_INVALID_GLYPH') and w['component']=='statement' for w in q['warnings'])},
        'alternatives':{'no_invalid_glyph':not any(w['code'] in ('INVALID_TEXT_GLYPH','UNRESOLVED_INVALID_GLYPH') and w['component']=='alternatives' for w in q['warnings']),'present':bool(q['alternativas']),'nonempty':'EMPTY_GRAPHICAL_ALTERNATIVE' not in codes,'unique':'DUPLICATED_ALTERNATIVE' not in codes,'sequence':'BROKEN_SEQUENCE' not in codes,'count':'UNEXPECTED_ALTERNATIVE_COUNT' not in codes,'no_suspect_formula':not any(w['code']=='POSSIBLE_MISSING_FORMULA' and w['component']=='alternatives' for w in q['warnings'])},
        'answer':{'present':q['gabarito'] is not None,'membership':q['gabarito'] in [a['letra'] for a in q['alternativas']],'single':'MULTIPLE_ANSWERS' not in codes},
        'images':{'association':'POSSIBLE_UNASSOCIATED_IMAGE' not in codes,'rendered':all('asset_hash' in c for c in q['content'] if c['kind']=='visual'),'graphical_alternatives_nonempty':'EMPTY_GRAPHICAL_ALTERNATIVE' not in codes},
        'layout':{'contiguous_pages':'MULTIPAGE_INCONSISTENCY' not in codes,'no_extra_content':'CONTENT_AFTER_ANSWER' not in codes,'no_footer':'FOOTER_CONTAMINATION' not in codes,'expected_markers':'UNEXPECTED_ALTERNATIVE_LAYOUT' not in codes,'no_overlap':'SOURCE_LAYOUT_OVERLAP' not in codes,'ordered':'CONTENT_ORDER_AMBIGUOUS' not in codes}}
    q['confidence']={k:sum(bool(x) for x in v.values())/len(v) for k,v in components.items()}
    q['confidence_evidence']=components
    q['confidence_semantics']='fraction_of_passed_rules; not calibrated probability or human approval'
