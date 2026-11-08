# 2026-11-08 — validação dos dados e análise renderizada

## Contexto do projeto neste estado

A pergunta do projeto é como o tamanho da população (`N`) e o comprimento do
cromossomo (`L`) afetam o custo computacional de um algoritmo genético (AG)
sequencial para OneMax. O escopo continua sendo desempenho computacional: cada
AG executa `G=100` gerações, sem parada antecipada, e a qualidade da solução
não é uma resposta do experimento.

Já existiam o AG testado, o DOE congelado, as 90 observações `baseline`, as 45
observações `phases`, as 90 observações `perf` divididas nos grupos válidos e
seus inventários/artefatos brutos. Faltavam a validação centralizada dos três
blocos, a tabela tratada rastreável, um caderno literal e o relatório
renderizado do item 8 do roteiro.

Commit: `feat: valida dados e renderiza análise da etapa 2`

## Significados

- `N` é o número de indivíduos; `L`, o número de genes por indivíduo; `G`, o
  número de gerações; e `B`, o número de AGs completos agregados em uma
  observação.
- `T_g = T/(B G)` é o tempo em nanossegundos por geração; `Q = B N L G/T` é a
  vazão em genes por segundo.
- `baseline` é a medida primária de tempo; `phases` registra os cinco
  temporizadores internos; `ipc_user` mede `instructions/cycles`; e
  `cache_user` mede `cache_misses/cache_references`. IPC e cache não são
  combinados entre grupos ou linhas diferentes.
- DOE é o projeto experimental. As campanhas `baseline` e `phases` usaram a
  ordem de um DOE anterior à separação dos grupos de `perf`; seus manifestos
  preservam hashes do YAML e CSV efetivamente usados.

## Mudanças e decisões

- Foi criado `scripts/validate_data.py`. Ele valida o esquema, chaves, status,
  parâmetros, afinidade, fases, contadores e artefatos de cada observação. A
  versão histórica do DOE/configuração é localizada pelos hashes do manifesto
  no histórico Git; portanto, uma ordem posterior não reclassifica dados já
  coletados.
- O validador gera `data/processed/measurements.csv` (225 observações
  rastreáveis), `environment.csv` e `validation-report.md`, sem modificar os
  dados brutos.
- Foi criado `analysis/etapa2.qmd` como fonte única da análise e
  `scripts/render_analysis.py` como executor das células Python e renderizador
  Quarto. A análise usa a biblioteca padrão do Python, produz os sumários CSV,
  sete figuras SVG e o HTML `results/etapa2.html`.
- Foram acrescentados `make check-data`, `make validate-data`, `make analyse`
  e `make all`. O alvo `analyse` recria, nessa ordem, a consolidação tratada,
  tabelas, figuras e relatório; não mede novamente o AG.
- Após revisão do material didático em `graphics-material/`, as sete figuras
  foram aprimoradas na fonte `analysis/etapa2.qmd`, sem alterar dados ou
  protocolo. Os títulos passaram a declarar a observação principal; os
  gráficos de vazão, IPC e cache usam painéis por `L` e pontos somente nos
  níveis medidos de `N`, com ICs e sem linhas de interpolação; o mapa de calor
  usa escala logarítmica com valores escritos; e a composição de fases usa
  médias que somam exatamente 100%. A paleta categórica é distinguível sem o
  par vermelho--verde, e os diagnósticos de overhead/variabilidade são
  dotplots com a referência de zero explícita quando aplicável.

## Como testar ou reproduzir este estado

Em um clone com o histórico Git que contém os DOE/configurações preservados:

```bash
make test
make check-design
make check-data
make analyse
```

O último comando requer Python 3.12 e Quarto 1.x. O executor prioriza `quarto`
no `PATH` e, em Linux, reconhece também a instalação empacotada pelo RStudio;
neste ambiente foi encontrado Quarto 1.10.18 nessa segunda localização.
O resultado esperado é a mensagem de 90 observações `baseline`, 45 `phases` e
90 `perf` válidas, seguida de `Caderno renderizado: results/etapa2.html`.
Abra o HTML no navegador para uma leitura humana; a inspeção local deve
confirmar títulos, unidades, pontos, barras de intervalo, eixo de referência
e ausência de sobreposição de rótulos.

Também foi executado `make all`: testes do AG, DOE atual, checagens secas das campanhas, validação de dados e renderização passaram. Essa auditoria foi feita no diretório de trabalho atual; uma entrega final ainda deve repetir o mesmo alvo em clone novo.

A verificação cobre coerência dos dados e geração automática dos artefatos; ela
não transforma as campanhas em uma nova medição nem substitui a interpretação
humana de variações de ambiente.

## Evidência e impacto

`make check-data` e o `make all` posterior validaram as 225 observações: 90
`baseline`, 45 `phases` e 90 `perf`. O HTML contém tabela de ambiente e desenho, sumário por tratamento de
`T_g` e `Q`, heatmap, vazão com IC bootstrap, IPC, cache miss, composição de
fases, overhead e variabilidade. As figuras e tabelas são geradas de
`data/processed/measurements.csv` e `data/processed/environment.csv`; não há
edição manual de valores derivados.

A revisão visual dos SVGs rasterizados pelo navegador confirmou que os títulos
e subtítulos cabem, os rótulos de eixos e valores são legíveis, os intervalos
não se confundem com curvas e a marca de 0% do overhead está visível. A mudança
melhora a comunicação, não a evidência: continuam os mesmos 225 registros e as
mesmas estatísticas tratadas.

Os achados apresentados são deliberadamente descritivos. Por exemplo, o
caderno relata a maior e a menor mediana de vazão e a taxa de cache observada,
mas trata associação com cache como evidência compatível, não prova isolada de
causalidade. O modo `phases` é mantido como diagnóstico, pois a comparação
pareada com `baseline` vem de instantes diferentes.

## Limitações e próximo passo

- O resolvedor de proveniência requer o histórico Git completo para recuperar
  o par de arquivos indicado pelos hashes de campanhas antigas. Um clone
  superficial que não contenha esses commits não pode validar esses blocos.
- O artefato padrão é HTML. Não havia motor PDF (LaTeX, WeasyPrint ou
  equivalente) instalado; uma exportação PDF fica condicionada à configuração
  explícita desse motor no ambiente de Quarto.
- O limiar de 10% usado para sinalizar anomalias é apenas descritivo e não
  remove observações. A revisão humana deve conferir o relatório, a
  interpretação e a decisão de apresentação antes de um commit.
- Os gráficos declaram tendências observadas e intervalos das réplicas, mas
  não estabelecem causalidade microarquitetural. Em especial, o cache continua
  em campanha distinta da medida de tempo e o overhead de `phases` continua
  diagnóstico entre campanhas feitas em instantes diferentes.
