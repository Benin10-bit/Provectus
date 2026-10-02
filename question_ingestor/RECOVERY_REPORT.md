# Recuperação de sobreposições e investigação de glifos

## Resultado

- Sobreposições de Q155 e Q160 resolvidas na representação extraída: quatro figuras originais isoladas da camada de texto, preservando pixels, transparência quando presente e resolução nativa. As figuras 1 e 2 seguem a ordem horizontal original. Os recortes de auditoria continuam mostrando a fonte sem alterações.
- Q160 passou a OK. Q155 continua REVIEW apenas pelo glifo ilegível.
- Resultado: 134 OK, 31 REVIEW, 0 ERROR, em 165 questões.
- 48 testes passaram. Os gabaritos foram comparados antes/depois e permaneceram idênticos, inclusive os seis ausentes.

## O que foi descoberto sobre os glifos

A inspeção dos streams originais encontrou 72 pares UTF-16 com primeiro elemento D800. Os 144 caracteres ilegíveis correspondem a 66 trechos em 24 questões. Os glifos da fonte embutida são .notdef e o subconjunto de fonte não contém os caracteres matemáticos originais.

Se substituirmos hipoteticamente D800 por D835, todos os pares podem representar símbolos do bloco Mathematical Alphanumeric Symbols: variantes de mu, omega, alpha, epsilon e letras latinas matemáticas. Exemplo: D800 DECD admite a proposta D835 DECD = U+1D6CD (𝛍). **Isso é uma reconstrução plausível, não uma decodificação inequivocamente determinada pelos bytes restantes.** Outros blocos Unicode também podem compartilhar o mesmo segundo elemento. Portanto o original não foi sobrescrito e nenhuma hipótese foi marcada OK.

O extrator agora gera `recovery_candidate` nos segmentos, com código observado, hipótese, nome Unicode, posição e `verified=false`. Todos os 66 candidatos também estão em `glyph_recovery_candidates.jsonl`. No `audit.html`, abra “Sugestões de glifos — não aplicadas, confirmação necessária”. Uma fonte legível é necessária para confirmar os símbolos. Não foram usadas respostas, unidades ou contexto físico para substituir automaticamente os quadradinhos.

## Validação visual

- [Q155: comparação](qa/recovery-q155.png): circuitos e legendas recuperados sem cabeçalho nem gabarito vizinho dentro das figuras; símbolo ilegível mantido.
- [Q160: comparação](qa/recovery-q160.png): circuito e trajetória recuperados sem fragmentos do cabeçalho; texto, alternativas e gabarito preservados.

A recuperação só isola rasters cuja identidade e posição coincidam com a camada raw e que não intersectem texto acadêmico ou desenhos necessários. Casos compostos, rotacionados ou incertos mantêm o recorte regional e REVIEW. O PDF de entrada nunca é modificado.

## Pendências

24 questões com glifos não confirmados; 6 com gabarito ausente; Q99 com possível fórmula ausente. A lista integral está no `report.md`. Os relatórios SECOND_PASS_REPORT e VISUAL_QA_SECOND_PASS são históricos; este relatório descreve a versão atual.
