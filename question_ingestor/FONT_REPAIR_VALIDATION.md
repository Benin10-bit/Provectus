# Validação da correção 0.2.3

## Escopo

Dois PDFs Fênix reais, recebidos como exemplos de `UNRECOVERABLE_SOURCE_OBJECT`:

| PDF | SHA-256 | Páginas | Questões | OK | REVIEW | ERROR |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| plano_inclinado.pdf | `7715369f2e5c4c81f776090dfd4b84d9768700e9399b9f167ce7b417adbe4284` | 82 | 109 | 97 | 12 | 0 |
| polaridade.pdf | `33b94ed4886cb76f4cffffbd691e2dfe48e67282b96c378ebeb4e6f53cb478ad` | 57 | 71 | 71 | 0 | 0 |

O reparo alterou apenas o dicionário auxiliar de fonte xref 21 no primeiro PDF e xref 16 no segundo. Texto nativo de todas as 139 páginas permaneceu idêntico (SHA-256 por página antes/depois). O pipeline completo verificou a integridade dos objetos gráficos, produziu 180 questões e 179 gabaritos. A primeira questão de cada arquivo foi conferida com o recorte original: cabeçalho, dificuldade, enunciado, alternativas e gabarito coincidiram. Também foram conferidas as fórmulas `√3/6` e `v²` no primeiro.

Os 12 REVIEW são do primeiro PDF: questões 7, 45, 59, 65, 67, 70, 71, 84, 89, 91, 93 e 100. Nas 7, 45, 59, 65, 67, 84, 89, 91 e 100 há glifos inválidos da fonte; nas 70 e 71 há diagnósticos `SOURCE_EMPTY_CLOSEPATH`/`PDF_ENGINE_WARNING`. A 93 está sem gabarito extraído (`PARSER_MISSING_ANSWER`). Avisos de captura visual também aparecem em algumas dessas questões; os recortes originais permanecem disponíveis para revisão. Nenhuma dessas incertezas foi promovida a OK.

## Staging e retomada

Uma execução com os dois PDFs resultou em `integrity_check = ok`, dois documentos e 180 questões no SQLite global. Uma execução subsequente pulou os dois (`SKIPPED=2`) e manteve a contagem. Os testes automatizados passaram: 73 testes. O banco global passou a usar journal tradicional; em teste com WAL, observou-se truncamento após o fechamento de um lote real, razão pela qual a checagem de integridade agora ocorre também depois de reabrir o arquivo.

## Limite

Os dois arquivos recebidos reproduzem a falha de fonte. Nenhum reproduz `SANITIZATION_GRAPHIC_INTEGRITY_FAILURE`. Essa segunda falha não foi corrigida sem o PDF correspondente. Não foram processados outros PDFs do acervo e os arquivos originais não são distribuídos neste pacote.
