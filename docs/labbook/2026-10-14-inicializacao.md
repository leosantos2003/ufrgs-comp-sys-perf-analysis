# Estado do projeto — inicialização da Etapa 2

**Data:** 2026-10-14
**Estado associado:** criação da estrutura inicial e dos controles experimentais.
**Commit de origem:** `d5fa75da2d1ac65808c8f7dbfda86446e6b3e0c1`.

## Contexto do projeto neste estado

Esta é a Etapa 2 do estudo de desempenho de um algoritmo genético (AG) sequencial. A pergunta de pesquisa é como o tamanho da população e o comprimento do cromossomo alteram o custo computacional do AG. O objetivo é medir tempo e vazão do algoritmo, não a qualidade da solução de otimização.

Neste estado, o projeto tinha somente a estrutura de diretórios e os controles em `config/experiment.yaml`. Não havia implementação C++, executável, teste automatizado, inventário da máquina ou dados de campanha.

## Significados

- **AG:** algoritmo que mantém uma população de soluções e a atualiza geração a geração por seleção, crossover e mutação.
- **OneMax:** problema em que o fitness de um cromossomo binário é a soma de seus bits iguais a um.
- **N:** número de indivíduos na população; futuro fator primário do experimento.
- **L:** número de genes binários em cada cromossomo; futuro fator primário do experimento.
- **G:** número fixo de gerações por execução. Não há parada antecipada por convergência.
- **Controle:** parâmetro mantido constante para que o efeito observado seja atribuído a `N` e `L`, como as probabilidades de crossover e mutação.

## Como testar ou reproduzir este estado

Não há implementação a executar neste estado, portanto `make test` ainda não existia. A evidência reproduzível é o commit de origem e a inspeção da configuração:

```bash
git show --stat d5fa75da2d1ac65808c8f7dbfda86446e6b3e0c1
sed -n '1,220p' config/experiment.yaml
```

O resultado esperado é a presença da estrutura inicial e dos controles do estudo, sem binários, testes ou medições.

## Mudanças e decisões

- Criada a estrutura inicial do trabalho e o repositório Git local em `etapa-2/`.
- Registrados os controles iniciais do AG em `config/experiment.yaml`.

## Evidência e impacto

- Não havia código, inventário do ambiente ou medições neste estado.
- Os controles registrados passam a ser a referência para a implementação e para futuras campanhas.

## Limitações e próximo passo

- O ambiente de medição ainda não estava inventariado.
- Próximo passo: implementar o AG e testes determinísticos de correção.
