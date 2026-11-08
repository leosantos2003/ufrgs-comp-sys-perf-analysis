# Caderno de laboratório — índice e protocolo

Cada arquivo em `docs/labbook/` descreve um único estado do projeto. A partir da adoção deste protocolo, o arquivo deve ser incluído no mesmo commit que materializa esse estado; assim, o histórico Git preserva tanto os artefatos quanto a decisão, a evidência e o impacto associados a eles.

## Convenções obrigatórias

1. Antes de criar um commit que altere código, configuração, dados, análise ou protocolo, adicionar `docs/labbook/AAAA-MM-DD-<resumo-curto>.md`.
2. O arquivo deve registrar: objetivo da mudança, artefatos alterados, validação executada e evidência, impacto sobre dados/configuração, limitações conhecidas e próximo passo.
3. Todo arquivo deve conter também três seções autossuficientes: **Contexto do projeto neste estado** (pergunta, escopo e o que já existia), **Significados** (siglas, parâmetros e modos relevantes) e **Como testar ou reproduzir este estado** (comandos, resultado esperado e limitações da verificação).
4. Não editar nem apagar um arquivo já presente em um commit anterior. Correções, interpretações posteriores ou reversões devem constar em um novo arquivo.
5. Se o estado produzir ou invalidar dados, citar os identificadores dos arquivos/diretórios afetados e a decisão de preservação, exclusão ou novo bloco experimental.
6. O nome é cronológico e legível; a associação exata com o estado é dada pelo commit que contém o arquivo, evitando um hash autorreferente no próprio conteúdo.

Os dois primeiros registros abaixo foram reconstruídos a partir dos commits existentes durante a migração do formato. Eles preservam os hashes de origem em seus próprios metadados; os registros posteriores seguem a convenção de inclusão no mesmo commit.

## Estados registrados

- [2026-10-14 — inicialização](labbook/2026-10-14-inicializacao.md)
- [2026-10-22 — implementação inicial do AG](labbook/2026-10-22-ag-inicial.md)
- [2026-11-03 — validação independente do AG](labbook/2026-11-03-validacao-independente.md)
- [2026-11-04 — inventário de ambiente](labbook/2026-11-04-inventario-ambiente.md)
- [2026-11-04 — correção da associação da validação](labbook/2026-11-04-correcao-associacao-validacao.md)
- [2026-11-04 — DOE piloto](labbook/2026-11-04-doe-piloto.md)
- [2026-11-05 — piloto de três pontos](labbook/2026-11-05-piloto-tres-pontos.md)
- [2026-11-07 — calibração completa de lotes e DOE definitivo](labbook/2026-11-07-calibracao-completa-lotes.md)
- [2026-11-07 — campanha baseline completa](labbook/2026-11-07-campanha-baseline.md)
- [2026-11-08 — campanhas phases e perf](labbook/2026-11-08-phases-e-perf.md)
- [2026-11-08 — validação dos dados e análise renderizada](labbook/2026-11-08-analise-validacao.md)
