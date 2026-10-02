# Integração — Question Ingestor 0.2

**O ZIP contém quatro PDFs, não cinco.** Todos foram processados pelo batch. Nenhum processamento do acervo completo ou alteração no Provectus.

## Hierarquia

| PDF | Matéria | Content path | Status |
|---|---|---|---|
| fisica/hidroestatica/hidroestatica.pdf | fisica | hidroestatica | OK |
| historia/primeiro_reinado.pdf | historia | primeiro_reinado | OK |
| matematica/area.pdf | matematica | area | OK |
| portugues/interpretacao_1.pdf | portugues | interpretacao_1 | OK |

## Resultado

4 DONE; 0 FAILED. 1721 páginas; **1952 questões: 1867 OK, 85 REVIEW, 0 ERROR**.
Gabaritos presentes: 1919; ausentes: 33. Multipágina: 1226. Com imagens: 1113. Execução: 326.1 s.

## Motivos de revisão

- EMPTY_GRAPHICAL_ALTERNATIVE: 1 questões distintas.
- PARSER_MISSING_ANSWER: 33 questões distintas.
- PDF_ENGINE_WARNING: 2 questões distintas.
- SOURCE_EMPTY_CLOSEPATH: 2 questões distintas.
- UNRESOLVED_INVALID_GLYPH: 52 questões distintas.

Contagens de avisos podem se sobrepor. A lista completa, com número, documento e evidência, está em `evidence/review_error_all.json`.

`UNRESOLVED_INVALID_GLYPH`: símbolo não verificável na fonte; recorte não equivale a recuperação. `PARSER_MISSING_ANSWER`: ausência extraída ainda não atribuída definitivamente à fonte. `EMPTY_GRAPHICAL_ALTERNATIVE`: alternativa vazia. `PDF_ENGINE_WARNING` / `SOURCE_EMPTY_CLOSEPATH`: diagnóstico gráfico localizado; render e aviso preservados. Não foram inventadas respostas nem símbolos.

## Verificações

- 70 testes automatizados passaram, incluindo regressões e texto artificial acima de 100 mil caracteres.
- Um lote real com os quatro PDFs; hierarquia e relação JSONL/SQLite conferidas.
- SQLite integrity_check OK, nenhuma violação de FK.
- Segunda execução: quatro SKIPPED; contagens inalteradas.
- Force: História reprocessada, sem duplicação.
- Limit 2 em saída isolada: dois documentos; reaproveitou cache documental já verificado.
- Editor HTTP: quatro documentos, paginação, filtros, rich-content e recorte original acessível.
- Em cópia do staging: alteração, aprovação e reversão; automático preservado e três ações no histórico.
- Assets e raw permanecem por documento, com identificação por SHA-256.

Maior enunciado: portugues/interpretacao_1.pdf, Q220, 12675 caracteres, status OK. JSONL e SQLite coincidem integralmente.

Amostra de auditoria: 14 casos em `qa/`, incluindo maiores textos, REVIEW, imagens e fórmulas. Os relatórios históricos do piloto permanecem disponíveis no projeto. As comparações visuais realizadas anteriormente nesta execução cobriram Hidrostática Q3/Q26/Q370, Área Q22/Q36 e Primeiro Reinado Q65. Não se afirma aprovação visual de todas as questões.

## Correções e limites

- Preservada recuperação limitada de CIDSystemInfo ilegível em Hidrostática, com texto nativo inalterado.
- Diagnóstico gráfico de Português localizado por página; páginas comprovadamente vazias são INFO, sem penalidade por comprimento.
- Gravação JSONL temporária com flush/fsync e leitura completa antes de conclusão; separadores Unicode não dividem registros.
- Recortes já verificados podem ser reutilizados no mesmo PDF/configuração; hashes são conferidos.
- Arquivos temporários restaurados incompletos foram recuperados do ZIP original. A nova versão não trata esses bytes incompletos como conteúdo válido.
- O editor altera trechos existentes e glifos identificados; não cria segmentos novos para alternativas totalmente vazias, não edita crops e não faz classificação semântica.
- O teste de interface verifica HTTP e estrutura; não houve validação de pintura em Chromium nesta entrega.
- O quinto PDF não estava disponível. Portanto o teste cobre quatro arquivos reais, sem inventar um quinto.

## Uso

Extraia `question_ingestor_batch_v0.2.zip`, entre na pasta do projeto e siga `RUNBOOK.md`. O outro ZIP contém `integration_staging/`; abra-o com `python -m question_ingestor review /caminho/integration_staging`. Para seu acervo, use uma saída nova, confira dry-run e execute primeiro --limit 5.


## Pacotes da entrega

O programa completo está em `question_ingestor_batch_v0.2.zip`. Os resultados foram divididos em 3 ZIPs independentes por tamanho. Extraia **todos na mesma pasta**, permitindo mesclar a pasta `integration_staging`, sem substituir arquivos diferentes. Depois execute `python -m question_ingestor review /caminho/integration_staging`. Nenhuma concatenação binária é necessária.

- `question_ingestor_resultados_01.zip`
- `question_ingestor_resultados_02.zip`
- `question_ingestor_resultados_03.zip`
