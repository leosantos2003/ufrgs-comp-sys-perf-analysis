# Revisão de clareza da apresentação da Etapa 2

## Contexto do projeto neste estado

A pergunta de pesquisa permanece: como o tamanho da população (`N`) e o
comprimento do cromossomo (`L`) afetam o desempenho computacional de um
algoritmo genético sequencial para OneMax? O escopo continua sendo custo
computacional, não qualidade de otimização. Antes desta revisão, o repositório
já continha o AG testado, o DOE congelado, as campanhas `baseline`, `phases` e
`perf`, os dados validados, o caderno renderizado e um deck de 14 páginas.

O objetivo deste estado é melhorar a apresentação para uma audiência que ainda
não conhece o projeto. A revisão simplifica a linguagem, explica o AG e o
desenho experimental antes dos resultados, amplia o espaço de cada gráfico e
torna explícita a cobertura dos critérios da Etapa 2.

Commit: `docs(slides): melhorar narrativa e legibilidade da apresentação`

## Significados

- `N` é o número de indivíduos em uma população, e `L` é o número de genes em
  cada cromossomo. `G=100` é o número fixo de gerações e `B` é o lote de
  execuções completas usado para tornar configurações curtas mensuráveis.
- `T_g=T/(BG)` representa o tempo por geração. `Q=BNLG/T` representa genes
  processados por segundo. As duas métricas usam o trabalho total do lote.
- `baseline` fornece as medidas primárias de tempo e vazão. `phases` divide o
  tempo entre as cinco fases do AG. `ipc_user` e `cache_user` são grupos
  separados de contadores de hardware, válidos apenas dentro da própria linha.
- DESC, RESULTS, DIFF, REPRO, DOE, LITERAL, BOAS, DSBOX e PRES / OPIN são os
  critérios de avaliação listados na seção 11 do plano de implementação.

## Como testar ou reproduzir este estado

Na raiz do repositório:

```bash
make slides
pdfinfo slides/slides-etapa-2.pdf
pdftoppm -png -r 120 slides/slides-etapa-2.pdf /tmp/etapa2-slide
git diff --check
```

`make slides` deve gerar `slides/slides-etapa-2.pdf` sem alterar dados ou
figuras. `pdfinfo` deve informar um PDF de 23 páginas no formato 16:9. A
rasterização permite conferir visualmente que texto, diagramas e gráficos não
se sobrepõem ou são cortados. Essa verificação técnica não substitui a revisão
humana da narrativa e da adequação ao tempo de apresentação.

## Mudanças e decisões

- Reorganizamos o deck em uma jornada: pergunta e escopo, funcionamento do AG,
  desenho experimental, métricas, controles, rastreabilidade, resultados,
  dificuldades, critérios, validação e auditoria.
- Acrescentamos diagramas simples para explicar uma geração do AG e a cadeia
  reproduzível que liga código, DOE, dados brutos e análise.
- Simplificamos os termos das métricas, explicando o que cada medida significa
  e qual pergunta ela responde antes de apresentar os resultados.
- Dedicamos um slide para cada gráfico. Cada slide usa quase toda a área útil
  para a figura e termina com uma leitura curta que explica eixos, pontos,
  barras ou conclusão descritiva relevante.
- Incluímos dois slides que conectam todos os critérios da seção 11 do plano a
  evidências concretas do repositório.
- Após a revisão do grupo, reescrevemos os slides de vazão, overhead, IPC,
  cache e variabilidade. Cada um agora declara o tipo de gráfico, os eixos, a
  fórmula usada no ponto, a amostra de réplicas, o significado da barra de
  intervalo e a pergunta que a métrica ajuda a responder. O slide anterior aos
  resultados explica que a mediana é o ponto central das réplicas e como o IC
  bootstrap de 95% usa 5.000 reamostragens.
- Ajustamos a capa para apresentar Felipe e Leonardo em linhas centralizadas,
  com espaço leve entre os nomes e a afiliação `Instituto de Informática --
  UFRGS 2026/2` centralizada logo abaixo.

## Evidência e impacto

- `make slides` recompilou o PDF a partir de `slides/slides-etapa-2.tex` e das
  figuras SVG produzidas pelo caderno, sem editar dados, resultados ou figuras
  manualmente.
- A renderização técnica das 23 páginas foi inspecionada em PNG. Os gráficos de
  tempo, vazão, fases, overhead, IPC, cache e variabilidade ocupam slides
  próprios e preservam as unidades e as notas de interpretação.
- A segunda inspeção focou os slides 13, 15, 16, 17 e 18. Ela confirmou que as
  chaves de leitura e as fórmulas ficam visíveis sem cortar o gráfico nem o
  rodapé.
- O conteúdo numérico e as limitações continuam derivados de
  `data/processed/analysis-report.md`; a revisão altera apenas a comunicação
  desses resultados.

## Limitações e próximo passo

O PDF continua específico do material e da plataforma descritos no relatório.
Os contadores de hardware e o tempo seguem provenientes de campanhas distintas,
portanto a apresentação conserva a interpretação descritiva. O grupo deve abrir
o PDF em tamanho de apresentação, conferir o ritmo dos 23 slides e validar que
as explicações orais e as conclusões representam corretamente a análise antes
de criar um commit.
