# Resultado do piloto

Extração automática; ainda não aprovada para importação.

- **file**: "lista-questoes-610750.pdf"
- **sha256**: "5c4b0a1e7c5cac9d88da8a80897e836be629c4e82f1e03416a23ebc497247909"
- **pages**: 116
- **processing_time_seconds**: 20.791
- **questions_found**: 165
- **questions_ok**: 134
- **questions_review**: 31
- **questions_error**: 0
- **answers_found**: 159
- **images_found**: 382
- **unique_content_assets**: 330
- **graphical_alternatives**: 146
- **multipage_questions**: 110
- **questions_with_images**: 136
- **possible_missing_formulas**: 1
- **banks_found**: {"EEAr": 3, "UECE": 7, "CFS - Demais especialidades": 8, "EAM": 1, "EsPCEx": 4, "EFOMM": 31, "ITA": 38, "EN": 34, "CBMERJ": 2, "AFA": 23, "IME": 14}
- **difficulties**: {"FACIL": 17, "MEDIA": 62, "DIFICIL": 61, "MUITO_DIFICIL": 25}
- **alternative_counts**: {"4": 44, "5": 121}
- **review_sample_size**: 75
- **orphan_elements**: 0
- **raw_cache_reused**: true
- **warning_severities**: {"INFO": 466, "REVIEW": 73}
- **changed_to_ok**: [5, 13, 18, 21, 27, 31, 42, 65, 67, 69, 72, 78, 82, 83, 89, 91, 92, 96, 105, 112, 119, 127, 131, 138, 143, 146, 147, 148, 153, 160, 165]
- **deduplication_executed**: false
- **human_approved**: false
- **source_engine_warnings**: ["SOURCE_INVALID_HEX_STRING"]
- **sanitization_raster_integrity_verified**: true

## Warnings

- VISUAL_BLOCK_CAPTURED: 285 ocorrências
- GRAPHICAL_ALTERNATIVE: 146 ocorrências
- INLINE_VISUAL_CAPTURED: 30 ocorrências
- UNRESOLVED_INVALID_GLYPH: 66 ocorrências
- SOURCE_MISSING_ANSWER: 6 ocorrências
- VISUAL_CONTINUATION_PAGE: 1 ocorrências
- POSSIBLE_MISSING_FORMULA: 1 ocorrências
- SOURCE_OVERLAP_RECOVERED: 4 ocorrências

## Todas as questões REVIEW e ERROR

| Questão | Status | Páginas | Warnings |
|---|---|---|---|
| 17 | REVIEW | 8–9 | UNRESOLVED_INVALID_GLYPH |
| 26 | REVIEW | 17–18 | GRAPHICAL_ALTERNATIVE, UNRESOLVED_INVALID_GLYPH, VISUAL_BLOCK_CAPTURED |
| 37 | REVIEW | 24–24 | UNRESOLVED_INVALID_GLYPH, VISUAL_BLOCK_CAPTURED |
| 39 | REVIEW | 25–26 | UNRESOLVED_INVALID_GLYPH, VISUAL_BLOCK_CAPTURED |
| 46 | REVIEW | 29–30 | UNRESOLVED_INVALID_GLYPH, VISUAL_BLOCK_CAPTURED |
| 51 | REVIEW | 32–33 | UNRESOLVED_INVALID_GLYPH, VISUAL_BLOCK_CAPTURED |
| 55 | REVIEW | 34–34 | UNRESOLVED_INVALID_GLYPH, VISUAL_BLOCK_CAPTURED |
| 57 | REVIEW | 35–36 | UNRESOLVED_INVALID_GLYPH, VISUAL_BLOCK_CAPTURED |
| 58 | REVIEW | 36–36 | UNRESOLVED_INVALID_GLYPH |
| 59 | REVIEW | 36–36 | UNRESOLVED_INVALID_GLYPH |
| 60 | REVIEW | 36–37 | INLINE_VISUAL_CAPTURED, UNRESOLVED_INVALID_GLYPH |
| 62 | REVIEW | 38–38 | UNRESOLVED_INVALID_GLYPH |
| 63 | REVIEW | 38–39 | UNRESOLVED_INVALID_GLYPH, VISUAL_BLOCK_CAPTURED |
| 64 | REVIEW | 39–39 | UNRESOLVED_INVALID_GLYPH |
| 66 | REVIEW | 40–40 | GRAPHICAL_ALTERNATIVE, SOURCE_MISSING_ANSWER, VISUAL_BLOCK_CAPTURED |
| 68 | REVIEW | 41–42 | UNRESOLVED_INVALID_GLYPH, VISUAL_BLOCK_CAPTURED |
| 90 | REVIEW | 58–58 | UNRESOLVED_INVALID_GLYPH, VISUAL_BLOCK_CAPTURED |
| 94 | REVIEW | 61–61 | GRAPHICAL_ALTERNATIVE, SOURCE_MISSING_ANSWER, VISUAL_BLOCK_CAPTURED |
| 99 | REVIEW | 65–66 | GRAPHICAL_ALTERNATIVE, POSSIBLE_MISSING_FORMULA, VISUAL_BLOCK_CAPTURED |
| 101 | REVIEW | 66–67 | SOURCE_MISSING_ANSWER, VISUAL_BLOCK_CAPTURED |
| 106 | REVIEW | 70–70 | SOURCE_MISSING_ANSWER, VISUAL_BLOCK_CAPTURED |
| 111 | REVIEW | 73–74 | SOURCE_MISSING_ANSWER, VISUAL_BLOCK_CAPTURED |
| 120 | REVIEW | 80–81 | UNRESOLVED_INVALID_GLYPH, VISUAL_BLOCK_CAPTURED |
| 122 | REVIEW | 82–83 | UNRESOLVED_INVALID_GLYPH, VISUAL_BLOCK_CAPTURED |
| 125 | REVIEW | 84–85 | GRAPHICAL_ALTERNATIVE, UNRESOLVED_INVALID_GLYPH, VISUAL_BLOCK_CAPTURED |
| 130 | REVIEW | 88–88 | UNRESOLVED_INVALID_GLYPH |
| 137 | REVIEW | 92–93 | UNRESOLVED_INVALID_GLYPH, VISUAL_BLOCK_CAPTURED |
| 150 | REVIEW | 102–103 | SOURCE_MISSING_ANSWER, VISUAL_BLOCK_CAPTURED |
| 151 | REVIEW | 103–104 | UNRESOLVED_INVALID_GLYPH, VISUAL_BLOCK_CAPTURED |
| 155 | REVIEW | 107–108 | SOURCE_OVERLAP_RECOVERED, UNRESOLVED_INVALID_GLYPH, VISUAL_BLOCK_CAPTURED |
| 156 | REVIEW | 108–109 | GRAPHICAL_ALTERNATIVE, UNRESOLVED_INVALID_GLYPH, VISUAL_BLOCK_CAPTURED |

## Interpretação

Visuais capturados e ordenados geram INFO e não bloqueiam OK. UNRESOLVED_INVALID_GLYPH mantém REVIEW mesmo com recorte: imagem não recupera um glifo ausente na fonte. SOURCE_MISSING_ANSWER registra ausência conferida visualmente; PARSER_MISSING_ANSWER exige investigação. Nenhuma resposta é inferida. Os scores são proporções de verificações, não probabilidades. Veja VISUAL_QA_SECOND_PASS.md para os casos efetivamente comparados.
