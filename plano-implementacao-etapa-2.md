# Plano de implementação - Projeto, Etapa 2

## 1. Objetivo e escopo da etapa

Esta etapa deve transformar a proposta da Etapa 1 em uma campanha **executável, auditável e parcialmente analisada**. O objeto de estudo permanece o mesmo: um algoritmo genético (AG) geracional, sequencial, com cromossomos binários, fitness OneMax, seleção por torneio, crossover de um ponto e mutação bit-flip.

A pergunta de pesquisa é:

> Como o tamanho da população (`N`) e o comprimento do cromossomo (`L`) afetam o desempenho computacional de um AG sequencial?

O foco é o custo computacional do AG, e não a qualidade das soluções. Assim, a execução sempre terá exatamente `G` gerações e **não terá término antecipado por convergência**.

Ao final da Etapa 2, o grupo deverá ser capaz de executar um único comando que: gera/lê o projeto experimental, executa o AG sob as configurações definidas, registra metadados e dados brutos, produz tabelas e gráficos preliminares, e atualiza o caderno de análise. A etapa não precisa encerrar a investigação, mas deve validar que este caminho produzirá a Etapa 3.

## 2. Critério prático de pronto

A Etapa 2 estará pronta quando houver evidência verificável de todos os itens abaixo:

- AG em C++ correto e determinístico para uma semente fornecida;
- ambiente, compilador, binário, afinidade de CPU e configurações relevantes registrados automaticamente;
- projeto fatorial `N x L`, com réplicas e ordem aleatorizada, gerado por código e salvo em CSV;
- dados brutos em CSV, uma observação por execução, sem edição manual;
- resultados preliminares para tempo, vazão, fases internas e, se disponível, contadores de hardware;
- caderno Quarto/Jupyter executável que transforma os dados brutos em figuras, tabelas e interpretação;
- README que permita a outra pessoa repetir a campanha; e
- lista honesta das dificuldades, testes feitos e limitações que ainda seguem para a Etapa 3.

## 3. Estrutura proposta para o diretório do trabalho

Manter `etapa-1/` intacto e acrescentar uma estrutura separada. Os dados brutos devem ser versionados enquanto tiverem tamanho razoável; se crescerem demais, manter no repositório ao menos um subconjunto, o esquema e instruções inequívocas de obtenção.

```text
.
├── etapa-1/                         # entrega original, preservada
├── src/
│   ├── ga.cpp                       # AG e instrumentação interna
│   └── tests.cpp                    # testes determinísticos de correção
├── scripts/
│   ├── build.sh                     # compilação com flags registradas
│   ├── generate_design.py           # gera e embaralha design.csv
│   ├── capture_environment.sh       # inventário de HW/SW e controles
│   ├── calibrate_batch.py           # escolhe lote de medição por configuração
│   ├── run_experiments.py           # lê design.csv e executa uma linha por vez
│   └── validate_data.py             # checa esquema, chaves e dados ausentes
├── config/
│   ├── experiment.yaml              # constantes do AG e configuração da campanha
│   └── design.csv                   # plano experimental congelado e aleatorizado
├── data/
│   ├── raw/                         # saída imutável do programa, perf e time
│   ├── metadata/                    # inventário da máquina e logs de controle
│   └── processed/                   # junções e sumários gerados por código
├── analysis/
│   ├── etapa2.qmd                   # texto, código, tabelas e gráficos intercalados
│   └── requirements.txt             # versões das dependências de análise
├── figures/                         # somente figuras geradas pelo caderno
├── docs/
│   ├── environment.md               # descrição legível do ambiente efetivamente usado
│   ├── labbook.md                   # decisões, tentativas e resultados por data
│   ├── difficulties.md               # problema, evidência, solução/limitação
│   └── uso-ia.md                    # declaração factual do uso de IA
├── results/                         # HTML/PDF renderizado do caderno
├── README.md
└── Makefile                         # alvos build, test, design, run, analyse e all
```

`Makefile` é uma conveniência; os scripts não devem depender de cliques, planilhas ou comandos não documentados. Os diretórios `data/processed/`, `figures/` e `results/` são produtos descartáveis: devem poder ser reconstruídos a partir de `src/`, `scripts/`, `config/` e `data/raw/`.

## 4. Pacote de trabalho A - implementação e validação do AG

### 4.1 Definir a implementação antes de medir

Implementar uma única versão sequencial do AG. Usar explicitamente `std::uint8_t` para cada gene, em vez de `std::vector<bool>`, para que `N x L` tenha interpretação direta em bytes e para evitar que a especialização compactada altere silenciosamente a carga de memória. A população corrente e a próxima população devem ser pré-alocadas antes da região medida; a troca entre elas não deve alocar memória.

Fixar no `experiment.yaml`, e registrar em cada execução:

| Item | Decisão para a campanha |
|---|---|
| Fitness | OneMax: soma dos bits do cromossomo |
| Seleção | Torneio de tamanho 2 |
| Crossover | Um ponto; probabilidade fixa `p_c` documentada |
| Mutação | Bit-flip; probabilidade fixa por gene `p_m` documentada |
| Gerações | `G` constante em todas as configurações |
| Threads | Uma única thread |
| Parada | Somente ao completar `G`; sem early stopping |
| Gerador aleatório | PRNG e semente explícitos, impressos no resultado |

Os valores de `p_c`, `p_m` e `G` devem ser escolhidos uma vez após o piloto de correção e congelados antes da campanha principal. Isso respeita a proposta da Etapa 1: `N` e `L` são os fatores estudados; taxas, método de seleção, algoritmo, compilação e número de gerações são controles.

### 4.2 Testar a correção sem misturar com desempenho

Criar testes unitários para: OneMax em vetores conhecidos; seleção por torneio com fitness conhecido; crossover em ponto conhecido; mutação com sequência aleatória controlada; tamanho da população após cada geração; e limites `0 <= fitness <= L`. Em instâncias pequenas, comparar o resultado/checksum da implementação medida com uma versão de referência simples, usando a mesma semente.

O binário de medição deve emitir, fora da região cronometrada, um checksum da população final e o melhor fitness. Eles impedem que o compilador elimine trabalho e permitem detectar mudanças acidentais de comportamento. Não imprimir por geração nem escrever arquivos dentro da região medida.

## 5. Pacote de trabalho B - ambiente, instrumentação e controle

### 5.1 Descrever o ambiente real, não apenas o planejado

A Etapa 1 antecipou Ubuntu, GCC, um Intel Core i7-1355U e execução em um núcleo. Na Etapa 2, confirmar esses dados na máquina que realmente executará a campanha e registrar automaticamente: `uname -a`, `lscpu`, topologia/cache, memória disponível, versão do GCC, versão do `perf`, versão do kernel, flags completas de compilação, commit Git, hash SHA-256 do binário e bibliotecas relevantes. Salvar a saída bruta em `data/metadata/` e resumir somente os campos relevantes em `docs/environment.md`.

Como o i7-1355U é híbrido, escolher **um núcleo de desempenho (P-core)** para toda a campanha, identificar o CPU lógico usado e usar `taskset` para afinidade. Não comparar medições de P-cores com E-cores. Registrar também o CPU efetivo reportado pela aplicação; uma configuração de afinidade que falha invalida a observação.

### 5.2 Controles experimentais

- Executar conectado à energia e sem aplicações de carga intencional; registrar carga do sistema, CPU migrations e context switches.
- Fazer uma execução de aquecimento não contabilizada para carregar executável e bibliotecas. Não confundir esse aquecimento com as réplicas.
- Verificar e registrar governor, frequências observadas e Turbo Boost. Se for permitido alterar essas configurações, registrar o estado anterior, a alteração e a restauração. Se não for permitido, **não simular controle**: reportar a limitação e usar mais réplicas.
- Usar o mesmo binário, flags, núcleo, versão de SO e configuração do AG durante toda a campanha. Alteração de qualquer um desses itens inicia novo bloco de experimentos.
- Executar as configurações na ordem aleatória de `design.csv`, não por ordem crescente de `N` ou `L`; assim, temperatura e atividades externas não ficam confundidas com um fator.
- Preservar falhas, medições interrompidas e tentativas inválidas em log. Reexecutar uma linha somente com motivo documentado.

### 5.3 Instrumentação e seu custo

Usar três modos, marcados na coluna `measurement_mode`:

1. `baseline`: relógio monotônico em volta do núcleo completo do AG; é a fonte dos resultados primários de tempo e vazão.
2. `phases`: acumuladores de tempo nas fases avaliação, seleção, crossover, mutação e substituição; é usado para a decomposição de tempo.
3. `perf`: execução sem temporizadores internos de fases e com `perf stat` para os eventos de hardware.

Comparar `baseline` e `phases` em uma amostra de configurações. Se a instrumentação interna alterar materialmente o tempo, publicar a decomposição como perfil diagnóstico, manter o modo `baseline` como medida de desempenho e declarar o viés possível. Não somar contadores de `perf` obtidos em execuções diferentes como se fossem uma única observação.

Antes da campanha, executar `perf list` e um teste curto para descobrir os eventos realmente suportados e se houve multiplexação. Priorizar `cycles`, `instructions`, `cache-references`, `cache-misses`, `context-switches` e `cpu-migrations`; registrar a cadeia de eventos literal, erros de permissão e as razões `time_running/time_enabled`. Em processadores híbridos, não chamar uma contagem genérica de cache de “falta de L1” sem validar sua semântica.

## 6. Pacote de trabalho C - projeto experimental

### 6.1 Fatores, respostas e unidades de trabalho

Os dois fatores primários são `N` e `L`. O projeto inicial recomendado é fatorial completo:

| Fator | Níveis iniciais propostos | Por que esses níveis |
|---|---:|---|
| População `N` | 128, 512, 2.048, 8.192 | Varia em potências de quatro e muda o número de indivíduos em uma geração. |
| Cromossomo `L` | 64, 256, 1.024, 4.096 | Varia em potências de quatro e altera o trabalho por indivíduo. |

Com genes de um byte, uma população ocupa aproximadamente `N x L` bytes; como há duas populações, o conjunto de trabalho principal é aproximadamente `2 x N x L`, mais fitness e metadados. A grade cobre desde quilobytes até dezenas de megabytes e pode revelar transições compatíveis com caches. As capacidades efetivas de cache da máquina devem ser anotadas no gráfico, não presumidas a partir da proposta.

Esta grade tem 16 tratamentos. Planejar inicialmente 10 réplicas independentes no modo `baseline` (160 observações). Para `phases` e cada grupo de eventos de `perf`, usar ao menos 5 réplicas por tratamento, depois de confirmar que o custo total é viável. A semente de cada réplica deve constar no projeto: usar a mesma lista de 10 sementes para todos os tratamentos facilita auditoria, mas cada repetição usa uma semente diferente.

Se o piloto mostrar que a maior configuração é longa demais, reduzir a grade antes da campanha e justificar a mudança no laboratório. Se a menor for curta demais, não alterar `G` seletivamente: medir um lote de `B` execuções completas do mesmo AG, com `G` fixo em cada uma, e registrar `B`. A duração agregada deve ficar aproximadamente entre 0,5 e 2 s. Todas as métricas normalizadas devem então usar `B x N x L x G` como trabalho total. `B` é um detalhe de medição, não um terceiro fator de estudo.

### 6.2 Projeto executável em CSV

`generate_design.py` deve criar o projeto com uma semente de aleatorização registrada. Cada linha de `config/design.csv` é uma execução planejada, contendo ao menos:

```text
run_id,block,order,measurement_mode,perf_group,N,L,G,batch,replication,seed,core_id
```

O script não deve escrever valores medidos no arquivo de projeto. `run_experiments.py` lê as linhas na ordem `order`, invoca o binário, captura a saída de `perf`/`time`, inclui o inventário do ambiente e escreve arquivos de dados brutos associados ao `run_id`. Desta forma, o código do projeto experimental é tão auditável quanto o código do AG.

## 7. Pacote de trabalho D - coleta e esquema de dados

Guardar a saída original de cada ferramenta em `data/raw/` e produzir uma tabela tratada, em formato longo e legível por máquina, em `data/processed/measurements.csv`. Uma observação deverá sempre poder ser rastreada de volta ao comando, à versão do binário e à saída bruta que a originaram.

Campos mínimos da tabela tratada:

```text
run_id, status, timestamp, block, order, measurement_mode, perf_group,
git_commit, binary_sha256, compiler, compiler_flags, core_id,
N, L, G, batch, replication, seed, p_c, p_m,
wall_time_ns, phase_eval_ns, phase_selection_ns, phase_crossover_ns,
phase_mutation_ns, phase_replacement_ns,
cycles, instructions, cache_references, cache_misses,
context_switches, cpu_migrations, max_rss_kib, stderr_path
```

Definir as respostas derivadas somente no caderno de análise:

\[
T_g = \frac{T}{B G}, \qquad
Q = \frac{B N L G}{T}, \qquad
IPC = \frac{\text{instructions}}{\text{cycles}}
\]

em que `T` é `wall_time_ns` convertido para segundos e `B` é `batch`. Para as fases, calcular `P_f = 100 T_f / T` apenas nos dados `phases`, conservando também a diferença entre a soma das fases e o tempo total. Para cache, usar a taxa `cache_misses / cache_references` somente quando ambos os eventos foram coletados juntos, suportados e sem multiplexação inaceitável.

`validate_data.py` deve falhar se houver chave duplicada, coluna ausente, `status` diferente de sucesso no conjunto analisado, tempo não positivo, parâmetros diferentes dos congelados, `core_id` inesperado ou dados de `perf` malformados. Dados inválidos não devem desaparecer: ficam marcados com `status` e `exclusion_reason`.

## 8. Pacote de trabalho E - análise preliminar e programação literal

Usar `analysis/etapa2.qmd` como fonte única da análise e renderizá-lo para HTML/PDF. O arquivo deve conter, em sequência, texto explicativo, código Python ou R, resultados de execução, tabelas, figuras e interpretação humana. Recomenda-se Python com `pandas`, `seaborn`/`matplotlib` e `scipy`/`statsmodels`; todas as versões devem estar em `analysis/requirements.txt`. Quarto pode ser substituído por Jupyter somente se o notebook e seu ambiente também forem executáveis sem passos manuais.

O caderno deve produzir, no mínimo:

1. tabela do ambiente e tabela do desenho (`N`, `L`, `G`, `B`, réplicas e total de observações);
2. tabela por tratamento com `n`, mediana, média, desvio-padrão e coeficiente de variação de `T_g` e `Q`;
3. mapa de calor de `T_g` por `N` e `L`;
4. gráfico de `Q` versus conjunto de trabalho `N x L` (escala logarítmica quando apropriado), com linhas por `L` ou painéis por fator e intervalo de confiança;
5. gráficos de IPC e taxa de cache miss versus `N x L`, se `perf` estiver disponível;
6. gráfico de composição do tempo por fase, acompanhado da verificação do overhead de instrumentação; e
7. gráfico ou tabela de variabilidade entre réplicas (por exemplo, CV) e anomalias documentadas.

Os eixos devem ter nome, unidade e escala explícitos. Marcar capacidades de cache como referências visuais apenas depois de confirmá-las no inventário da plataforma. Usar intervalos de confiança por bootstrap ou barras de dispersão; não tratar uma única execução como evidência. A análise precisa separar fato medido de hipótese: por exemplo, queda de vazão acompanhada de mais cache misses é **evidência compatível** com pressão de memória, não prova isolada de causalidade.

Estabelecer antes de olhar os resultados as regras de qualidade: excluir apenas execuções incompletas, sem afinidade, com erro de ferramenta ou com violação documentada do protocolo. Um ponto estatisticamente extremo deve ser sinalizado e investigado, mas não removido automaticamente. Registrar a decisão e, se necessário, a repetição no `labbook.md`.

## 9. Pacote de trabalho F - dificuldades, validação e apresentação

Manter `docs/difficulties.md` durante o trabalho, em vez de reconstruí-lo ao final. Para cada item, registrar: data, sintoma/evidência, impacto nos dados, hipótese, tentativa de solução, resultado, decisão e efeito remanescente. Exemplos esperados: permissão negada pelo `perf`, eventos indisponíveis em CPU híbrida, migração de CPU, variação por frequência/temperatura, execução curta demais, overhead dos temporizadores e divergência em teste de correção.

Preparar uma apresentação curta que conte uma história verificável:

1. pergunta de pesquisa e recorte herdado da Etapa 1;
2. ambiente efetivamente usado e controles aplicados;
3. desenho fatorial e como o CSV/código executa a campanha;
4. cadeia de reprodutibilidade: código -> design -> dados brutos -> caderno -> figuras;
5. resultados preliminares de tempo e vazão;
6. evidências de fases e de hardware, quando disponíveis;
7. dificuldades, soluções e limitações; e
8. decisão de validação: o que já funciona e o que será ampliado na Etapa 3.

Cada gráfico deve responder uma pergunta concreta. Evitar gráficos decorativos ou a conclusão trivial de que cargas maiores levam mais tempo; o interesse é saber se o custo normalizado muda e em que condições.

## 10. Roteiro de execução

| Ordem | Entrega verificável | Condição para avançar |
|---:|---|---|
| 1 | Esqueleto do repositório, README inicial e `experiment.yaml` | As escolhas fixas do AG estão explícitas. |
| 2 | AG, testes e build reproduzível | Testes passam; checksum é igual ao da referência em instâncias pequenas. |
| 3 | Inventário de ambiente e teste de `taskset`/`perf` | CPU alvo, ferramenta disponível e limitações documentadas. |
| 4 | Gerador de DOE e `design.csv` piloto | Há uma linha por execução, réplicas, sementes e ordem aleatória. |
| 5 | Piloto de três pontos (pequeno, médio, grande) | Define `G`, a grade final e `B` sem alterar fatores seletivamente. |
| 6 | Campanha `baseline` completa | 16 tratamentos x 10 réplicas ou desenho revisado e justificado. |
| 7 | Campanhas `phases` e `perf` | Overhead quantificado; eventos válidos ou limitação evidenciada. |
| 8 | Caderno renderizado e validação de dados | Todas as figuras/tabelas são geradas a partir do CSV. |
| 9 | Slides, dificuldades e auditoria final | Outra pessoa consegue seguir o README do zero. |

Antes da entrega, executar `make all` em um diretório limpo ou em clone novo. Conferir que a execução não depende de dados processados pré-existentes, caminhos absolutos, variáveis de ambiente implícitas ou intervenção manual. Gerar o `.tgz` somente depois dessa auditoria e incluir nele os fontes, scripts, projeto CSV, resultados brutos/metadata, análise, slides e README.

## 11. Cobertura explícita dos critérios da Etapa 2

| Critério | Evidência planejada |
|---|---|
| DESC | `docs/environment.md`, metadata bruta e slide de plataforma. |
| RESULTS | Tabelas de sumário e gráficos do caderno renderizado. |
| DIFF | `docs/difficulties.md` com evidência e decisão. |
| REPRO | Git, README, seeds, hashes, dados CSV e comando `make all`. |
| DOE | `generate_design.py`, `experiment.yaml` e `config/design.csv`. |
| LITERAL | `analysis/etapa2.qmd` com prosa, código, saída e interpretação. |
| BOAS | Afinidade, aleatorização, réplicas, aquecimento, controle/registro de frequência e validação de dados. |
| DSBOX | Quarto + Python/R, dados tidy, geração automática de figuras e ambiente versionado. |
| PRES / OPIN | Apresentação focada em progresso demonstrável, validação e próximos passos. |

## 12. Transparência sobre IA

Como o enunciado exige declaração do uso de IA, preencher `docs/uso-ia.md` somente com fatos: ferramenta/agente usado, autonomia (passo a passo ou outra), dados fornecidos, fluxo de prompts -> validação humana -> integração, critérios de aceitação/rejeição, verificações humanas e quais trechos foram assistidos. A criação deste plano deve ser incluída caso o grupo o aproveite ou adapte. A declaração não substitui a revisão humana dos experimentos, código, resultados e interpretações.
