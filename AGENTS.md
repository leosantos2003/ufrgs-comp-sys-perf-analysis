# Instruções para agentes e contribuidores

Estas regras valem para todo o repositório. O projeto é a Etapa 2 de INF01146 — Avaliação de Desempenho, e estuda o custo computacional de um algoritmo genético sequencial para OneMax em função de `N` (população) e `L` (comprimento do cromossomo).

## Fonte de verdade e escopo

- Ler `README.md`, `config/experiment.yaml`, `plano-implementacao-etapa-2.md` e `docs/labbook.md` antes de mudar código, protocolo experimental ou documentação relevante.
- Tratar `config/experiment.yaml` como a fonte de verdade dos controles do AG. Alterações em seus controles exigem nova validação e um novo bloco de medições.
- Não editar manualmente dados derivados, figuras ou relatórios que devam ser produzidos por código. Preservar dados brutos, falhas e medições inválidas com seu motivo.
- Não modificar, remover ou incorporar alterações preexistentes e não relacionadas no diretório de trabalho.

## Documentação por estado de projeto

Uma alteração é documentalmente relevante quando muda código, build, configuração, desenho experimental, esquema ou dados, análise, protocolo, interpretação ou limitações do projeto.

Antes de um commit que contenha uma alteração relevante, criar um único arquivo novo em `docs/labbook/` com o nome `AAAA-MM-DD-<resumo-curto>.md` e incluí-lo no mesmo commit. Se o estado ainda não foi commitado, o arquivo pendente pode ser atualizado; depois do commit, ele é imutável. Correções e revisões posteriores exigem um novo arquivo, nunca a edição do registro histórico.

Todo arquivo de estado do labbook deve conter, no mínimo:

1. **Contexto do projeto neste estado:** pergunta de pesquisa, escopo e o que já existia.
2. **Significados:** siglas, parâmetros, modos ou métricas necessários para compreender a alteração.
3. **Como testar ou reproduzir este estado:** comandos, resultado esperado e limites da verificação.
4. **Mudanças e decisões**, **evidência e impacto**, e **limitações e próximo passo**.

Atualizar `docs/labbook.md` somente para alterar o protocolo ou acrescentar o link do novo estado. O README é uma descrição estável do projeto: não acrescentar nele status corrente, diário de mudanças ou “próximo passo”.

## Registro de dificuldades e IA

- Diante de falha, anomalia, tentativa descartada, limitação ou decisão de exclusão, acrescentar uma linha factual em `docs/difficulties.md`. Nunca apagar registros anteriores.
- Quando IA tiver auxiliado uma alteração incorporada, atualizar `docs/uso-ia.md` com ferramenta, escopo da assistência, artefatos afetados, verificações automáticas realizadas e validação humana ainda necessária. Usar o modelo de revisão humana existente nesse arquivo para registrar a aceitação pelo grupo.

## Validação mínima

- Depois de mudar `src/`, `scripts/build.sh` ou `Makefile`, executar `make test` e registrar o comando e o resultado no labbook.
- Depois de alterar a interface do executável, executar também `make run` e/ou um comando direto de `./build/ag_bench`; distinguir smoke test de medição de desempenho.
- Antes do commit, executar `git diff --check`.
- Não apresentar tempos de uma execução isolada como resultado de desempenho. A campanha exige afinidade de CPU, aquecimento, réplicas, metadados de ambiente e o protocolo definido no plano.

## Commits

- Manter commits focados: código, documentação do estado e evidência de validação devem representar o mesmo estado reproduzível.
- Não criar, reescrever ou enviar commits sem solicitação explícita do usuário.
