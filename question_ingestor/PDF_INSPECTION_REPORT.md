# Inspeção técnica do PDF piloto

Documento: lista-questoes-610750.pdf. Contexto fornecido: Física / Eletrodinâmica / Capacitores.
Inspeção realizada com PyMuPDF 1.26.6 antes da implementação do parser principal.

## Estrutura observada

- 116 páginas A4, aproximadamente 595,28 × 841,89 pontos. Uma coluna predominante.
- 165 inícios de questão, numerados de 1 a 165. 159 linhas nativas de gabarito.
- Cabeçalhos em DejaVuSans-Bold 12 pt, x=22,5 pt. Corpo principalmente DejaVuSans 9 pt, alternativas x=30 pt. Há estilos bold/oblique, tamanhos 8 e 10,5 e fontes Helvetica/Times em regiões específicas.
- Texto de conteúdo inicia próximo de y=88,5 e pode ultrapassar y=790. Cortar arbitrariamente em y=790 perderia cabeçalhos e conteúdo legítimo.
- Cabeçalhos: `Questão N - fonte - Dificuldade: classificação`. Fonte pode conter hífens, instituição por extenso, sigla e `(Simulados)`.
- Cabeçalhos longos quebram em duas linhas, inclusive `Dificuldade:` e `Muito Difícil`. A tipografia e a proximidade devem unir essas linhas.
- Alternativas: letra seguida de `)`, com conteúdo na mesma linha, na seguinte, em imagem, ou em combinação.
- Gabarito nativo: `Gabarito: A` a `Gabarito: E`. Não encontrado na camada textual das questões 66, 94, 101, 106, 111 e 150. Isso não autoriza inventar respostas.
- Classificações observadas incluem Fácil, Média, Difícil e Muito Difícil. Preservar original e normalizar sem enum fechado.

## Elementos gráficos e privacidade

540 ocorrências raster: 232 são dois objetos repetidos nas 116 páginas (marca sobreposta e logotipo de cabeçalho); 308 ocorrências restantes são candidatas a conteúdo. Existem 31 drawings em 5 páginas (12, 13, 92, 105 e 106). Ocorrência não equivale a asset único.

A marca diagonal identificadora é um objeto raster sobre o corpo. Exclusão somente de texto ou corte das margens é insuficiente. O mesmo objeto aparece na mesma posição em todas as páginas. Remover sua referência na cópia de renderização, sem modificar o PDF original. Não registrar texto, digest do objeto identificador ou dados pessoais em relatórios, raw, IDs ou logs. Identificadores do documento são SHA-256 do arquivo completo.

Dois textos fixos de cabeçalho são recorrentes em 116 páginas, nas faixas aproximadas y=16,8–27,9 e y=73,8–86,1. A detecção deve usar posição + recorrência de conteúdo. Não houve evidência de um rodapé textual recorrente inferior nesta amostra.

A camada raw será sanitizada: preservar conteúdo acadêmico, layout e contagens de exclusões, nunca copiar metadados PDF arbitrários, texto identificador ou bytes dos objetos excluídos. O original permanece no arquivo de entrada, sem alteração.

## Casos difíceis

- Q2 começa na página 1 e prossegue na 2; imagem, texto e opções precisam manter uma única identidade.
- Q5 (p3) possui quatro alternativas de circuitos: texto vazio não significa alternativa vazia.
- Q50 atravessa páginas 31–32, com alternativas gráficas.
- Q165 termina na página 116 com cinco alternativas de fórmulas rasterizadas.
- Diversas imagens são expressões matemáticas, não ilustrações independentes. Texto simples não representa fielmente essas regiões. Preservar posição, imagem e ordem; exigir REVIEW quando a fórmula puder estar ausente da representação textual.
- Há cabeçalhos quase no fim de página, sem corpo na mesma página (por exemplo Q17). Não confundir com questão interrompida se houver continuação.
- A ordem dos objetos internos não é a ordem de leitura: cabeçalhos repetidos aparecem depois do corpo na extração. Ordenar geometricamente após sanitização.
- Símbolos μ, subscritos, superscritos e sinais devem permanecer intactos. Não usar NFKC para deduplicação matemática.

## Decisões de arquitetura

Pipeline isolado: inspeção → raw sanitizado → detecção de eventos → parser → assets regionais → validadores → JSONL/SQLite → relatório/auditoria. Inspeção e raw independem da persistência de questões. Estratégia OCR abstrata sem implementação obrigatória; página sem texto nativo deve bloquear OK e preservar imagem para revisão.

Perfil inicial é a família de layout realmente observada. Validações de tipografia, indentação, sequência, gabarito e geometria complementam regex de marcadores. PDFs fora desse perfil devem gerar diagnóstico, não ser aceitos silenciosamente.

Cada componente recebe evidências binárias e score = verificações satisfeitas / verificações aplicáveis. Não são probabilidades estatísticas. Warnings relevantes impedem OK independentemente da média.

Assets: renderização de regiões na cópia limpa, incluindo texto e desenhos que intersectam a região; hash SHA-256 do WebP lossless. Recortes completos por página, em lista ordenada, evitam imagens verticalmente gigantes. Referências possuem documento, página, bbox e proprietário. Questões conservam spans de origem e conteúdo ordenado para rastrear fórmulas.

SQLite normalizado para documentos, jobs, questões, alternativas, assets, associações, warnings, validações e candidatos a duplicidade. JSONL é o intercâmbio canônico. Nenhuma resposta de usuário pertence ao registro da questão. Nenhuma migração PostgreSQL nesta fase.

## Limites da inspeção inicial

As contagens acima provêm de varredura das 116 páginas. Inspeção visual inicial: páginas 3 e 116. A validação final deverá ampliar a amostra e registrar exatamente os casos comparados. A ausência de warnings não é uma certificação humana de fidelidade. Deduplicação global, novos formatos, lote, Docker e integração seguem as fases posteriores.

## Complemento após execução do parser

Confirmados: 110 questões multipágina, 146 alternativas exclusivamente gráficas, 44 questões com quatro alternativas e 121 com cinco. Fontes normalizadas: 11 categorias. Dificuldades: 17 FACIL, 62 MEDIA, 61 DIFICIL e 25 MUITO_DIFICIL.

A inspeção visual posterior revelou sobreposição real de figuras/cabeçalhos nas questões 155 e 160. A imagem pode começar antes do marcador textual: usar apenas o topo de sua bbox atribuiria figuras à questão anterior. A atribuição por centro com warning explícito evita esse falso OK, mantendo a decisão aberta à revisão humana.

O documento também contém glifos inválidos e aviso nativo do MuPDF de string hexadecimal inválida. Nada foi reconstruído por inferência. Detalhes de conferência e defeitos do extrator corrigidos estão em `VISUAL_QA.md`.
