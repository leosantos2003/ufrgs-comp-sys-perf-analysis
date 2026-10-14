# Projeto - Etapa 2: avaliação de desempenho de um algoritmo genético

Este diretório concentra todos os artefatos da Etapa 2 do trabalho de INF01146 - Avaliação de Desempenho. A pergunta de pesquisa, herdada da Etapa 1, é:

> Como o tamanho da população (`N`) e o comprimento do cromossomo (`L`) afetam o desempenho computacional de um algoritmo genético sequencial?

O objetivo é medir e explicar o custo computacional do algoritmo. A qualidade da solução de otimização não é uma variável de resposta do estudo.

## Estado atual

Foi concluído o primeiro item do roteiro: estrutura do projeto, versionamento local e configuração explícita dos controles do AG. Ainda não há implementação, medições ou resultados neste diretório.

## Escopo experimental

O objeto sob teste será um AG geracional sequencial em C++ para o problema OneMax. Os fatores estudados são:

- `N`: tamanho da população;
- `L`: comprimento do cromossomo em genes binários.

Os controles iniciais - fitness, seleção, crossover, mutação, número de gerações, PRNG, número de threads e representação do gene - estão em [config/experiment.yaml](config/experiment.yaml). Eles só podem mudar mediante uma decisão registrada em `docs/labbook.md`, seguida de nova validação e de um novo bloco de medições. Nenhuma configuração pode encerrar antes de completar `G` gerações.

## Estrutura

```text
etapa-2/
├── analysis/          # caderno Quarto/Jupyter e dependências da análise
├── config/            # controles do AG e desenho experimental gerado por código
├── data/
│   ├── metadata/      # inventário de HW/SW e logs de ambiente
│   ├── processed/     # tabelas derivadas; sempre reconstruíveis
│   └── raw/           # saídas imutáveis de cada execução
├── docs/              # ambiente, caderno de laboratório, dificuldades e uso de IA
├── figures/           # figuras exclusivamente geradas pela análise
├── results/           # HTML/PDF renderizado do caderno
├── scripts/           # automação de build, DOE, coleta e validação
├── src/               # AG, testes e código auxiliar
├── .gitignore
└── README.md
```

Os diretórios inicialmente vazios têm um `.gitkeep` apenas para preservar o esqueleto. Dados processados, figuras e relatórios não serão editados manualmente: deverão ser produzidos a partir de dados brutos, código e configuração versionados.

## Fluxo previsto

1. Implementar o AG e testes determinísticos em `src/`.
2. Registrar o ambiente efetivo de medição em `data/metadata/` e `docs/environment.md`.
3. Gerar o projeto fatorial e aleatorizado em `config/design.csv` por um script em `scripts/`.
4. Executar o projeto, com afinidade de CPU e coleta automatizada, gravando uma observação por execução em `data/raw/`.
5. Validar e transformar os dados em `data/processed/`.
6. Renderizar a análise literal de `analysis/etapa2.qmd` em `results/` e gerar as figuras em `figures/`.

Os comandos para as etapas acima serão acrescentados ao README apenas quando existirem e puderem ser executados do zero. Não usar planilhas, edições manuais de CSV ou passos de interface não documentados.

## Reprodutibilidade e rastreabilidade

- O repositório Git local foi inicializado nesta pasta; não há commit inicial ainda.
- Cada campanha deverá registrar commit Git, hash do binário, flags de compilação, núcleo de CPU, seed, ordem aleatorizada, versão das ferramentas e horário.
- Arquivos em `data/raw/` serão preservados; transformações acontecerão por scripts e permanecerão auditáveis.
- `docs/labbook.md` registra decisões, ensaios e anomalias; `docs/difficulties.md` registra problemas e suas soluções ou limitações.
- O uso de IA deve ser declarado de forma factual em `docs/uso-ia.md`, com validação humana das saídas incorporadas.

## Relação com a Etapa 1

A entrega anterior está em `../etapa-1/`. Ela definiu a medição em sistema Linux, execução de uma thread, instrumentação de tempo e fases, e possível uso de `perf stat` e `/usr/bin/time -v`. A Etapa 2 confirmará a máquina e ferramentas realmente usadas antes da campanha; os dados da proposta não substituem esse inventário.

## Próximo passo

O próximo item do roteiro é implementar o AG e seus testes de correção, mantendo os parâmetros de [config/experiment.yaml](config/experiment.yaml) como a única fonte de configuração experimental.
