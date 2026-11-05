# Estado do projeto — DOE piloto materializado

**Data:** 2026-11-04  
**Estado associado:** implementação do item 4 do roteiro de execução; gerador determinístico de DOE e `config/design.csv` piloto.

## Contexto do projeto neste estado

O projeto investiga como `N`, o tamanho da população, e `L`, o comprimento do cromossomo, afetam o custo computacional de um algoritmo genético (AG) sequencial para OneMax. O escopo é desempenho computacional, e cada execução deve completar exatamente `G` gerações, sem término antecipado.

Antes deste estado, o repositório já continha o AG C++ determinístico, a suíte de correção, build reproduzível, os controles congelados em `config/experiment.yaml` e o inventário de ambiente com a afinidade para o CPU lógico 0 validada. Ainda não existia o desenho fatorial materializado nem qualquer observação em `data/raw/`. A pré-condição de ambiente também registrava que a cadeia atual de eventos `perf` sofre multiplexação; isso não impede descrever as execuções planejadas, mas impede tratá-las como campanha de contadores válida.

## Significados

- **DOE (Design of Experiments):** CSV que descreve cada execução planejada, sem medições. Ele é a ligação auditável entre os controles da configuração e o futuro executor de campanha.
- **`N`, `L` e `G`:** tamanho da população, comprimento do cromossomo e gerações por execução. `N` e `L` formam os fatores do fatorial completo; `G=100` é um controle do AG.
- **`batch` (`B`):** quantidade de execuções completas do AG agregadas em uma observação. Neste DOE inicial vale `1`; será calibrada no item 5, sem alterar `G` seletivamente.
- **`replication` e `seed`:** número da repetição e semente de seu PRNG. A mesma lista de até dez sementes é reutilizada entre tratamentos; `baseline` usa as dez primeiras, `phases` e `perf`, as cinco primeiras.
- **`order`:** permutação global das 320 linhas. A sequência é determinada por `design_random_seed=20261014`, não por ordem crescente de `N` ou `L`.
- **`block`:** rótulo do conjunto inicial de planejamento (`pilot`). **`perf_group`:** `not_applicable` fora de `perf` e `requested_all` para a intenção de coletar todos os eventos solicitados juntos; não afirma que esses contadores já sejam utilizáveis.

## Como testar ou reproduzir este estado

Na raiz do repositório, execute:

```bash
make design
make check-design
make test
git diff --check
```

`make design` deve criar `config/design.csv` com cabeçalho estável e 320 execuções planejadas: 160 em `baseline`, 80 em `phases` e 80 em `perf`. `make check-design` não regrava o arquivo: ele reconstruirá o DOE em memória a partir de `config/experiment.yaml` e falhará se cabeçalho, linhas, sementes, ordem, tratamentos ou réplicas tiverem sido alterados. `make test` deve terminar com `Todos os testes do AG passaram.`. Essas verificações validam a transformação determinística do projeto e a correção funcional já coberta pelo AG; não realizam aquecimento, afinidade de campanha, medição de tempo ou coleta de `perf`.

## Mudanças e decisões

- Criado `scripts/generate_design.py`, sem dependências externas. Ele lê o subconjunto de YAML usado por `config/experiment.yaml`, valida os campos necessários — inclusive que `design.type`, `design.combinations` e os níveis de `N × L` formam o fatorial declarado — e gera o CSV com as colunas `run_id, block, order, measurement_mode, perf_group, N, L, G, batch, replication, seed, core_id` e `design_random_seed`.
- A semente de aleatorização da configuração alimenta uma implementação explícita de `SplitMix64`: ela gera a lista auditável de sementes de execução e a permutação de Fisher--Yates. Assim, a saída não depende da versão do PRNG do Python e pode ser conferida exatamente por `--check`.
- Acrescentado `design.initial_design` à fonte de verdade: `block: pilot`, `batch: 1` e `perf_group: requested_all`. São metadados de materialização do DOE; não alteram seleção, crossover, mutação, `G`, número de threads ou qualquer outro controle do AG. Como ainda não havia dados de campanha, nenhum bloco de medições foi invalidado.
- Gerado `config/design.csv` com o fatorial `4 × 4`: para cada tratamento, dez réplicas `baseline`, cinco `phases` e cinco `perf`. O `order` é uma permutação única global e cada `run_id` é único.
- Acrescentados os alvos `make design` e `make check-design`; o README passou a explicar que essa etapa somente planeja a campanha e não cria dados brutos.

## Evidência e impacto

- `make design` gerou 320 linhas planejadas, e `make check-design` confirmou que o arquivo materializado coincide exatamente com a configuração.
- Uma inspeção programática do CSV confirmou 16 tratamentos, 160 linhas `baseline`, 80 `phases`, 80 `perf`, dez sementes distintas no modo `baseline`, cinco em cada modo de perfil, ordens de 1 a 320 sem lacunas e 320 identificadores únicos.
- `make test` passou após a mudança do `Makefile`; `git diff --check` não reportou erros de espaço.
- `config/design.csv` é dado de projeto derivado e reconstruível, não dado bruto ou resultado de desempenho. Nenhum arquivo foi escrito em `data/raw/`, `data/processed/`, `figures/` ou `results/`; consequentemente, não há tempos, vazão ou contadores a interpretar neste estado.

## Limitações e próximo passo

- O desenho usa os níveis candidatos atuais e `B=1` apenas para estruturar o piloto. O item 5 deve medir três pontos sob as pré-condições de ambiente, decidir a grade final e calibrar `B`; qualquer novo CSV deve ser gerado por código, nunca editado manualmente.
- As linhas `perf` preservam a intenção de coleta, mas não autorizam utilizar os contadores. A cadeia observada no inventário ainda tem multiplexação e a máquina estava fora da alimentação AC; essas condições precisam ser resolvidas ou explicitamente mantidas como limitação antes da campanha.
- Ainda faltam o executor de linhas do DOE, a captura de saída bruta, a validação do esquema de dados e a análise. O próximo passo é o piloto de três pontos definido no item 5, não a campanha completa.
