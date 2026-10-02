# Conferência do piloto e limites da aprovação

## O que foi efetivamente comparado

Varredura estrutural: todas as 116 páginas. Conferência visual direcionada: 16 questões (1, 2, 5, 17, 50, 66, 82, 94, 101, 106, 111, 131, 150, 155, 160 e 165). Conferência não equivale a aprovação humana da amostra completa de 75.

| Questão | Evidência observada | Resultado |
|---|---|---|
| 1 | Enunciado, circuito com 12 V/6 μF/3 μF, quatro opções e gabarito B | Campos coincidem; OK automático mantido |
| 2 | Texto inicia p1; circuito, continuação, quatro alternativas e gabarito C na p2 | Uma questão com dois recortes; OK mantido |
| 5 | Quatro opções de circuitos, sem conteúdo textual; gabarito B | Quatro imagens associadas a A–D; REVIEW conservador porque um gráfico pequeno dispara regra de possível fórmula |
| 17 | Cabeçalho no fim da p8, conteúdo na p9; glifos problemáticos na unidade | Gabarito D e cinco opções preservados; REVIEW; nenhuma substituição inferida |
| 50 | Marcador A na p31 e imagem correspondente na p32, seguido de B–D e resposta C | Continuidade de alternativa atravessa página; quatro assets; OK mantido |
| 66 | Cinco alternativas de fórmulas em imagens; não há gabarito visível no recorte da questão | REVIEW; resposta permanece nula |
| 94 | Cabeçalho longo em duas linhas, cinco alternativas visuais; sem gabarito visível | Fonte EFOMM e dificuldade Difícil preservadas; REVIEW |
| 101 | Cabeçalho isolado p66, corpo com circuito/gráfico e opções na p67; sem gabarito | REVIEW; duas páginas e figuras preservadas |
| 106 | Circuito e cinco opções numéricas negativas/zero/positiva; sem gabarito | Sinais preservados; REVIEW |
| 111 | Cabeçalho p73, figura e conteúdo p74; sem gabarito | REVIEW; questão única |
| 150 | Cabeçalho p102, circuito e cinco opções na p103; sem gabarito | REVIEW; não resolver a questão para preencher resposta |
| 82 | Três páginas: cabeçalho, página contendo figura e página com texto/opções | Figura bastante alongada já na fonte. REVIEW por página sem texto; a indicação OCR_REQUIRED pede avaliação de fallback, não implica OCR executado ou obrigatório para essa figura |
| 131 | Afirmações I–IV no enunciado; opções A–E; gabarito B | `I)` gera suspeita de layout de alternativa, mas permanece no enunciado. REVIEW conservador; não se transformou em sexta opção |
| 155 | Figuras cobrem parte do cabeçalho na p107; alternativas e gabarito E p108 | Asset atribuído provisoriamente à Q155 por geometria. REVIEW. Recorte expandido pode incluir o gabarito da questão anterior devido à sobreposição do original; não confundir com gabarito estruturado E |
| 160 | Duas figuras sobrepõem o cabeçalho no PDF; corpo e cinco opções; gabarito D | Associação provisória à Q160; REVIEW. O defeito da fonte permanece visível |
| 165 | Cabeçalho `Muito Difícil` em duas linhas p115; cinco fórmulas em imagens p116, resposta A | Instituição ITA, dificuldade, páginas e todas as opções preservadas; REVIEW por fórmulas |

A Q27 também recebeu SOURCE_LAYOUT_OVERLAP por proximidade subponto entre bbox de fórmula e cabeçalho. Não foi promovida a OK sem revisão: é um possível falso positivo conservador.

## Defeito investigado e corrigido durante a implementação

A primeira tentativa de sanitização usava o xref representativo retornado por `get_image_info`. O documento contém cópias de imagens com pixels idênticos, porém referências diferentes. Remover apenas uma referência deixava a marca em outras páginas. Operações de edição de página também causaram avisos de recursos XObject/ExtGState ausentes neste arquivo. Esses recortes foram descartados e regenerados.

A versão entregue identifica todos os recursos correspondentes às imagens recorrentes, substitui-os por um objeto transparente na cópia em memória e reabre essa cópia. A comparação automática dos digests de pixels e bboxes confirma que todas as 308 ocorrências raster de conteúdo permanecem presentes. Não há modificação dos fluxos de conteúdo acadêmico.

O PDF original já emite `invalid character in hex string` no MuPDF. O diagnóstico é registrado como SOURCE_INVALID_HEX_STRING. Esse aviso específico não é confundido com os erros de recursos que a primeira limpeza introduziu. Outros diagnósticos de renderização causam ERROR; glifos inválidos observados no texto geram REVIEW.

## Verificações adicionais executadas

- 27 testes unitários/de integração passaram, incluindo multipágina, cabeçalhos partidos, alternativas gráficas, símbolos, ausência/inconsistência de respostas, privacidade, deduplicação conservadora e retomada.
- Reexecução do PDF real retornou `resumed_without_reprocessing=true`.
- Integridade SQLite e chaves estrangeiras verificadas.
- JSONL e payloads SQLite comparados.
- 165 questões em sequência, 159 gabaritos, 44 questões com quatro opções e 121 com cinco.
- 339 objetos gráficos de conteúdo (308 raster + 31 drawings): todos associados exatamente uma vez; renderizados em 324 ocorrências de assets compostos, 320 hashes únicos.
- Recortes e assets com hashes verificáveis; todos os links locais da auditoria conferidos.
- Amostra: todas as 62 REVIEW e 13 OK. ERROR: nenhuma nesta execução.

## Limites restantes

Não foi feita transcrição/OCR de fórmulas, correção dos símbolos defeituosos da fonte nem resolução de questões sem gabarito. A associação de figuras em sobreposições continua provisória. O HTML exibe texto e assets para comparação, sem prometer reconstrução tipográfica exata do PDF.

Somente esta família de layout foi validada. Recorrência não é prova universal de decoração em outros materiais; confirme um perfil para cada nova família. O detector de fórmulas é conservador, mas não prova ausência de toda fórmula perdida. Por isso, inclusive os OK precisam da revisão humana representativa antes de escalar.

O trabalho encerra-se no staging e auditoria. Nenhuma importação, lote global, containerização ou alteração no Provectus foi executada.
