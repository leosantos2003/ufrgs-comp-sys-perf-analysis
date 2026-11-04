# Uso de IA no projeto

Este arquivo explica, de forma simples e factual, como a IA foi usada. IA ajuda a planejar, escrever e revisar, mas o grupo continua responsável por entender, testar e aceitar cada resultado.

## Como registrar um uso de IA

Para cada uso relevante, informe: qual ferramenta foi usada, como ela foi usada, quais dados recebeu, o que ela produziu, como o grupo escolheu aceitar, editar ou rejeitar a saída e como uma pessoa verificou o resultado. Escreva apenas fatos; não atribua à IA uma decisão que foi do grupo.

## Registro inicial — plano e estrutura

| Campo | Registro |
|---|---|
| Ferramenta | Codex, assistente de programação. |
| Como foi usada | Conversa iterativa, a pedido do grupo. O grupo decide o que será aproveitado. |
| Dados fornecidos | Enunciado, slides da Etapa 1 e materiais da disciplina disponíveis no diretório. |
| O que ajudou a produzir | Plano de implementação, README, `config/experiment.yaml` e modelos em `docs/`. |
| Como a saída foi avaliada | O grupo deve comparar as sugestões com o enunciado e com as decisões do trabalho antes de usá-las. |
| Verificação humana | Use o modelo ao final deste arquivo para registrar quem revisou, o que foi revisado e a decisão. |

## Registro de 2026-11-03 — validação e documentação

| Campo | Registro |
|---|---|
| Ferramenta | Codex, assistente de programação. |
| Como foi usada | O grupo pediu alterações passo a passo; o agente propôs e aplicou mudanças, e os resultados foram verificados com comandos locais. |
| Dados fornecidos | Código-fonte, plano de implementação, README, enunciado e documentos do repositório. |
| O que ajudou a produzir | Referência simples e testes adicionais; mudanças em `src/ga.hpp`, `src/ga.cpp`, `src/tests.cpp`, `scripts/build.sh`, `README.md`, `AGENTS.md` e `docs/`. |
| Como a saída foi avaliada | Foram aceitas apenas mudanças que compilaram, passaram em `make test`, não apresentaram erro em `git diff --check` e foram revisadas pelo grupo. Uma referência com desempate incorreto foi corrigida antes de ser aceita. |
| Verificação automática | `make test`, `make run`, comparação de checksum entre `baseline` e `phases` e `git diff --check`. |
| Verificação humana | O solicitante informou que a revisão está de acordo. Registre os detalhes no modelo abaixo antes do commit. |

## Modelo para registrar a verificação humana

Copie este bloco para cada revisão relevante e preencha os campos entre colchetes.

### 2026-11-04 — revisão humana

| Campo | Preencher |
|---|---|
| Pessoas que revisaram | Leonardo |
| O que foi revisado | Implementação do AG |
| Como foi conferido | Leitura dos códigos e execução dos testes |
| Comandos e resultado | `make test` — passou, `./build/ag_bench --population 32 --length 16 --generations 10   --seed 20261022 --crossover 0.90 --mutation 0.01 --mode baseline` — 32,16,10,20261022,0.90000000000000002,0.01,baseline,171575,0,0,0,0,0,16,2855997894351129235, `./build/ag_bench --population 32 --length 16 --generations 10   --seed 20261022 --crossover 0.90 --mutation 0.01 --mode phases` — 32,16,10,20261022,0.90000000000000002,0.01,phases,193523,6904,30353,38655,113657,513,16,2855997894351129235 |
| Decisão | aceito |
| Pendências ou limitações | nenhuma |

Uma revisão só deve ser marcada como aceita depois que as pessoas responsáveis entenderem o resultado e concordarem que ele está correto para o projeto.
