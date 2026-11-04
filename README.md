# Etapa 2 — avaliação de desempenho de um algoritmo genético

Este repositório contém os artefatos executáveis, dados e documentação da Etapa 2 de INF01146 — Avaliação de Desempenho. Este README descreve o projeto de forma estável; o estado de cada mudança, decisão e validação pertence ao [caderno de laboratório](docs/labbook.md).

## Pergunta e escopo

> Como o tamanho da população (`N`) e o comprimento do cromossomo (`L`) afetam o desempenho computacional de um algoritmo genético sequencial?

O objeto de estudo é um algoritmo genético geracional, sequencial, para OneMax, com genes `std::uint8_t`, seleção por torneio de tamanho 2, crossover de um ponto e mutação bit-flip. O estudo mede custo computacional — não qualidade de otimização — e toda execução completa exatamente `G` gerações, sem término antecipado.

`N` e `L` são os únicos fatores primários. As demais decisões do algoritmo são controles documentados em [config/experiment.yaml](config/experiment.yaml); uma alteração exige registro no caderno, nova validação e início de um novo bloco de medições.

## Organização e cadeia reprodutível

```text
src/             implementação do AG, executável e testes
scripts/         build e automação da campanha
config/          controles do AG e desenho experimental congelado
data/raw/         saídas originais, uma observação por execução
data/metadata/    inventário de hardware, software e controles
data/processed/   dados derivados, sempre reconstruíveis
analysis/         caderno executável que gera tabelas e figuras
figures/          figuras geradas pelo caderno
results/          relatórios renderizados
docs/             ambiente, labbook, dificuldades e uso de IA
```

A cadeia obrigatória é: código e configuração → desenho experimental → dados brutos e metadados → dados tratados → análise e figuras. Nenhuma etapa deve depender de edição manual de CSV, planilha ou interface não documentada.

## Uso local

Pré-requisitos: GNU Make e compilador compatível com C++20.

```bash
make build      # gera build/ag_bench e build/ag_tests
make test       # compila e executa a suíte determinística
make run        # executa uma configuração demonstrativa
./build/ag_bench --help
```

`ag_bench` emite uma linha CSV por execução. A região cronometrada contém somente o laço de `G` gerações; inicialização, checksum e escrita da saída ficam fora dela. Os argumentos usados numa campanha devem reproduzir os controles congelados em `config/experiment.yaml`.

## Garantias de validação

O alvo `make test` verifica as primitivas OneMax, torneio, crossover e mutação; parâmetros inválidos; mutação com sequência pseudoaleatória controlada; determinismo por semente; população e limites de fitness após cada geração; equivalência com uma referência simples em instâncias pequenas; e preservação do resultado entre os modos `baseline` e `phases`.

Os testes comprovam correção funcional nas instâncias cobertas; não constituem uma medição de desempenho. Medições só são válidas quando acompanhadas da afinidade de CPU, inventário de ambiente e metadados definidos no plano experimental.

## Protocolo de documentação

- [docs/labbook.md](docs/labbook.md) é o índice e protocolo do diário. A partir de sua adoção, cada commit que altera o estado do projeto inclui um novo arquivo imutável em `docs/labbook/`.
- [docs/difficulties.md](docs/difficulties.md) preserva problemas, evidências, tentativas e limitações, inclusive os resolvidos.
- [docs/environment.md](docs/environment.md) resume o ambiente efetivamente medido e aponta para os inventários brutos.
- [docs/uso-ia.md](docs/uso-ia.md) registra uso de IA de forma factual e a validação humana necessária.

O plano de implementação em [plano-implementacao-etapa-2.md](plano-implementacao-etapa-2.md) define entregas, critérios e protocolo experimental completos.
