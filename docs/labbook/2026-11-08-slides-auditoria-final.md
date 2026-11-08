# Slides e auditoria final da Etapa 2

## Contexto do projeto neste estado

A pergunta de pesquisa permanece: como o tamanho da população (`N`) e o
comprimento do cromossomo (`L`) afetam o desempenho computacional de um
algoritmo genético sequencial para OneMax? O escopo continua sendo custo
computacional, não qualidade de otimização. Antes deste estado, o repositório
já continha o AG testado, o DOE revisado, campanhas `baseline`, `phases` e
`perf`, dados validados, análise renderizada e figuras reproduzíveis.

O objetivo deste estado é cumprir o item 9 do roteiro: criar slides que
apresentem o progresso verificável, preservar dificuldades e confirmar que a
cadeia pode ser executada fora do diretório original.

## Significados

- `N` é o número de indivíduos; `L`, o número de genes por cromossomo; `G=100`
  é o número fixo de gerações; `B` é o lote de execuções completas do AG.
- `baseline` mede o laço geracional sem temporizadores de fases; `phases`
  registra as cinco fases internas; `ipc_user` e `cache_user` são grupos de
  eventos de `perf` válidos somente dentro da própria linha.
- `T_g=T/(BG)` é o tempo por geração e `Q=BNLG/T` é a vazão normalizada.
- Um snapshot congelado é a cópia literal de `experiment.yaml` e `design.csv`
  identificada pelos hashes registrados no manifesto de uma campanha. Ele não
  é uma medição e não substitui os dados brutos.

## Como testar ou reproduzir este estado

Na raiz do repositório:

```bash
make test
make check-archive-inputs
make check-data
make all
make slides
git diff --check
```

`make all` deve concluir testes, validação do DOE e das campanhas, validação
dos snapshots e renderização de `results/etapa2.html`. A auditoria deste
estado também copiou o diretório para um novo local em `/tmp`, excluiu `.git`
e `build/`, e executou `make all` nessa cópia. O comando passou após a
permissão necessária para o cache do Quarto. `make slides` verifica
explicitamente `pdflatex`, Inkscape, `svg.sty` e `brazil.ldf` antes de compilar.
Com `texlive-latex-extra`, `texlive-lang-portuguese` e Inkscape instalados,
ele gerou o PDF de 14 páginas. As páginas foram rasterizadas e revisadas
visualmente; a aceitação humana do grupo ainda é necessária.

## Mudanças e decisões

- Adicionamos `slides/slides-etapa-2.tex`, no estilo do template e dos slides
  da Etapa 1. O deck apresenta pergunta, DOE, ambiente, rastreabilidade,
  resultados, fases, contadores, variabilidade, dificuldades, decisão de
  validação, uso de IA e auditoria.
- Adicionamos `scripts/build_slides.sh` e o alvo `make slides`. O script usa
  somente as figuras SVG que o caderno já gera e não altera dados nem figuras.
- A exportação padrão do Inkscape tentava interpretar rótulos dos SVGs como
  LaTeX e falhou em `T_g`. O deck agora preserva o texto vetorial já gerado
  pelo caderno, com `inkscapelatex=false`.
- A auditoria revelou que o validador dependia de `.git` para recuperar
  controles históricos e de caminhos absolutos preservados nos inventários.
  Adicionamos `scripts/archive_frozen_inputs.py`, os alvos de arquivamento e
  dois snapshots verificados em `data/metadata/frozen-inputs/`.
- O validador agora confere primeiro esses snapshots e, em uma cópia relocada,
  localiza o inventário histórico pelo diretório correspondente em
  `data/metadata/`. O texto absoluto continua preservado no dado bruto.

## Evidência e impacto

- `make archive-inputs` materializou dois pares de controles, um para
  `baseline`/`phases` e outro para `perf`; `make check-archive-inputs` confirmou
  seus hashes.
- `make check-data` aceitou 90 observações `baseline`, 45 `phases` e 90
  observações `perf` sem gerar dados derivados.
- `make test` passou após a alteração do Makefile e do validador.
- Em uma cópia limpa sem `.git`, `make all` recompilou os binários, confirmou
  225 linhas planejadas no DOE, validou as campanhas e snapshots e renderizou
  o HTML. Os dados brutos permaneceram imutáveis.
- Após instalar as dependências de slides, `make slides` concluiu sem erro e
  gerou `slides/slides-etapa-2.pdf` com 14 páginas. `pdfinfo` confirmou o
  formato 16:9, e a rasterização das páginas confirmou que não há texto
  cortado nem sobreposição.

## Limitações e próximo passo

Uma instalação parcial de LaTeX pode não conter `brazil.ldf`, que o template
fornecido usa; o script diagnostica essa ausência antes de iniciar o Beamer.
O PDF da Etapa 2 já foi compilado e inspecionado visualmente de modo técnico,
mas o grupo ainda deve fazer sua revisão humana da narrativa antes da entrega.
A interpretação dos resultados segue descritiva: campanhas de tempo e de
contadores ocorreram em instantes distintos, e correlação com cache não
demonstra causalidade isoladamente.
