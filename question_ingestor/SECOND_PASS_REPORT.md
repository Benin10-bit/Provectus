# Segunda passagem — fórmulas inline e conteúdo estruturado

Somente o PDF piloto. Sem importação em produção. Aprovação humana pendente.

| Métrica | Antes | Agora |
|---|---:|---:|
| questions_found | 165 | 165 |
| questions_ok | 103 | 133 |
| questions_review | 62 | 32 |
| questions_error | 0 | 0 |
| answers_found | 159 | 159 |
| images_found | 324 | 382 |
| graphical_alternatives | 146 | 146 |
| possible_missing_formulas | 35 | 1 |

## O que mudou

- `statement.segments` e `alternativas[].segments` são a representação canônica: texto, visual inline e visual de bloco, com página, bbox, ordem e vínculo ao asset. Plain text é derivado e usa marcadores explícitos de conteúdo visual.
- A ordenação usa faixas de linha, baseline, vizinhança horizontal e posição X. Q13 mantém texto → fórmula → texto. Imagens raster independentes não são fundidas por mera proximidade: o teste e a conferência de Q65 detectaram e corrigiram esse erro.
- Linhas vetoriais de altura zero foram agrupadas nas tabelas de Q21, preservando texto e desenhos num recorte regional por página. Textos nativos internos continuam nos metadados da tabela e na camada raw.
- INFO registra conteúdo visual efetivamente capturado. INFO não bloqueia OK. Overlap real, símbolo ilegível ou gabarito ausente continuam em REVIEW.
- Raw v2 mantém caracteres, origens, bboxes, fonte e evidência de glyph ID. Raw anterior permanece disponível; configuração de layout/parsing não força reextração raw. A última execução reutilizou raw.
- SQLite inclui `content_segments`, com roundtrip verificado contra JSONL. Resume valida também esses registros. HTML inclui filtros por alterações para OK, glifos, inline, gabarito, overlap e OCR.

## Glifos: investigação concluída, conteúdo não inventado

Os 144 caracteres problemáticos examinados correspondem ao glyph ID 0 (.notdef), em 66 trechos. A prancha `qa/glyph-evidence.png` mostra caixas no próprio PDF renderizado. Portanto não há símbolo visual recuperado nesses casos. Um recorte de caixa vazia não autoriza OK. Mantivemos `UNRESOLVED_INVALID_GLYPH`, localização e recorte. Nenhuma substituição por μ ou outro símbolo foi feita. A interface aceita preservação visual de glifo válido; nenhum desses 144 caracteres pôde ser confirmado como válido.

## Pendências reais

- Gabaritos ausentes na fonte: Q66, Q94, Q101, Q106, Q111 e Q150. Foram comparados enunciados, alternativas e limite da próxima questão, incluindo a página seguinte de Q106. Permanecem nulos e REVIEW.
- Sobreposição real: Q155 e Q160. O recorte pode incluir fragmentos de cabeçalho ou conteúdo vizinho já sobreposto na origem; não houve reconstrução ou apagamento especulativo.
- Q99: lacuna textual suspeita em “distância de.”. A renderização também é suspeita; não inferimos a expressão.
- Glifos .notdef: conforme lista completa de REVIEW em `report.md`.

## Verificações e limites

43 testes automatizados passaram, incluindo geometria inline, agrupamento raster, tabelas, severidades, glifos, cache e roundtrip SQLite. A auditoria visual desta passagem cobre os 21 casos de `VISUAL_QA_SECOND_PASS.md`, incluindo casos recém-OK. Os demais OK refletem as regras automáticas, não aprovação visual individual. A apresentação HTML foi renderizada para comparação com WeasyPrint; o navegador Chromium disponível não pôde ser iniciado. Nenhum OCR global foi executado. Não foram processados outros PDFs, nem alterado o Provectus.

## Todas as alterações de status

| Questão | Antes | Agora | Justificativa |
|---|---|---|---|
| 5 | REVIEW | OK | visual capturado com vínculo e ordenação; sobrescrito nativo preservado quando presente |
| 13 | REVIEW | OK | visual capturado com vínculo e ordenação; sobrescrito nativo preservado quando presente |
| 18 | REVIEW | OK | visual capturado com vínculo e ordenação; sobrescrito nativo preservado quando presente |
| 21 | REVIEW | OK | visual capturado com vínculo e ordenação; sobrescrito nativo preservado quando presente |
| 27 | REVIEW | OK | visual capturado com vínculo e ordenação; sobrescrito nativo preservado quando presente; interseção abaixo da tolerância geométrica |
| 31 | REVIEW | OK | visual capturado com vínculo e ordenação; sobrescrito nativo preservado quando presente |
| 42 | REVIEW | OK | visual capturado com vínculo e ordenação; sobrescrito nativo preservado quando presente |
| 65 | REVIEW | OK | visual capturado com vínculo e ordenação; sobrescrito nativo preservado quando presente |
| 67 | REVIEW | OK | visual capturado com vínculo e ordenação; sobrescrito nativo preservado quando presente |
| 69 | REVIEW | OK | visual capturado com vínculo e ordenação; sobrescrito nativo preservado quando presente |
| 72 | REVIEW | OK | visual capturado com vínculo e ordenação; sobrescrito nativo preservado quando presente |
| 78 | REVIEW | OK | visual capturado com vínculo e ordenação; sobrescrito nativo preservado quando presente |
| 82 | REVIEW | OK | continuação gráfica preservada; demais componentes presentes |
| 83 | REVIEW | OK | visual capturado com vínculo e ordenação; sobrescrito nativo preservado quando presente |
| 89 | REVIEW | OK | visual capturado com vínculo e ordenação; sobrescrito nativo preservado quando presente |
| 91 | REVIEW | OK | visual capturado com vínculo e ordenação; sobrescrito nativo preservado quando presente |
| 92 | REVIEW | OK | visual capturado com vínculo e ordenação; sobrescrito nativo preservado quando presente |
| 96 | REVIEW | OK | visual capturado com vínculo e ordenação; sobrescrito nativo preservado quando presente |
| 105 | REVIEW | OK | visual capturado com vínculo e ordenação; sobrescrito nativo preservado quando presente |
| 112 | REVIEW | OK | visual capturado com vínculo e ordenação; sobrescrito nativo preservado quando presente |
| 119 | REVIEW | OK | visual capturado com vínculo e ordenação; sobrescrito nativo preservado quando presente |
| 127 | REVIEW | OK | visual capturado com vínculo e ordenação; sobrescrito nativo preservado quando presente |
| 131 | REVIEW | OK | enumeração romana mantida no enunciado |
| 138 | REVIEW | OK | visual capturado com vínculo e ordenação; sobrescrito nativo preservado quando presente |
| 143 | REVIEW | OK | visual capturado com vínculo e ordenação; sobrescrito nativo preservado quando presente |
| 146 | REVIEW | OK | visual capturado com vínculo e ordenação; sobrescrito nativo preservado quando presente |
| 147 | REVIEW | OK | visual capturado com vínculo e ordenação; sobrescrito nativo preservado quando presente |
| 148 | REVIEW | OK | visual capturado com vínculo e ordenação; sobrescrito nativo preservado quando presente |
| 153 | REVIEW | OK | visual capturado com vínculo e ordenação; sobrescrito nativo preservado quando presente |
| 165 | REVIEW | OK | visual capturado com vínculo e ordenação; sobrescrito nativo preservado quando presente |

A lista integral de REVIEW/ERROR está em `report.md` e `report.json`. O diretório baseline permite comparar os registros anteriores.
