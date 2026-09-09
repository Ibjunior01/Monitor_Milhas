# PROJECT_STATE — Monitor de Milhas

## Status

**CONCLUÍDO — núcleo técnico e operacional validado.**

O projeto está funcional, testado e com automação agendada validada. As pendências restantes são apenas de apresentação final do repositório e preparação do material para portfólio.

---

## Visão geral

O **Monitor de Milhas** é uma aplicação em Python que monitora oportunidades públicas de transferência de pontos da **Esfera** para programas de fidelidade aérea.

O projeto combina:

- coleta automatizada de fontes públicas;
- filtro de recência;
- parser de promoções;
- regras de negócio;
- persistência JSON/JSONL;
- deduplicação;
- alertas via Telegram;
- dashboard em Streamlit;
- sincronização de estado remoto;
- testes automatizados;
- lint com Ruff;
- CI;
- GitHub Actions agendado.

Programas monitorados:

- LATAM Pass;
- Smiles;
- Azul Fidelidade.

---

## Arquitetura

Fluxo principal:

```text
Fontes públicas
      ↓
src/sources.py
      ↓
src/parser.py
      ↓
src/calculations.py
      ↓
src/monitor.py
      ↓
src/storage.py
      ↓
Telegram / branch state
      ↓
src/state_sync.py
      ↓
dashboard.py
```

Responsabilidades principais:

- `src/sources.py` — coleta RSS/HTTP;
- `src/parser.py` — interpretação de programa, bônus e validade;
- `src/calculations.py` — cálculos e regras de avaliação;
- `src/monitor.py` — orquestração da varredura;
- `src/storage.py` — persistência local;
- `src/state_sync.py` — sincronização do runtime state com a branch `state`;
- `src/telegram_alerts.py` — integração com Telegram;
- `dashboard.py` — camada de apresentação e operação manual.

---

## Fonte de verdade e atualização do dashboard

O problema original de atualização inconsistente do dashboard foi corrigido.

Principais causas tratadas:

1. caminhos relativos diferentes entre dashboard e storage;
2. “última varredura” inferida incorretamente a partir de oportunidades;
3. ausência de estado próprio da execução;
4. estado automático produzido pelo GitHub Actions não disponível localmente;
5. timestamps sem timezone explícito.

Fluxo atual:

```text
GitHub Actions
→ branch state
→ state_sync.py
→ storage local
→ dashboard
```

O dashboard:

- sincroniza o estado remoto ao iniciar uma sessão;
- possui atualização manual;
- preserva estado local quando ele é mais recente;
- preserva dados locais quando a sincronização remota falha;
- exibe última varredura em horário UTC-3.

---

## Persistência

### Configuração versionada

```text
data/config.json
data/cotacao_milhas.json
```

### Estado operacional

```text
data/vistos.json
data/oportunidades.jsonl
data/ultima_varredura.json
```

O estado operacional é ignorado na branch principal.

A branch dedicada:

```text
state
```

mantém o runtime state entre execuções do GitHub Actions.

Arquivos JSON críticos utilizam escrita com arquivo temporário e substituição do destino quando tecnicamente aplicável.

---

## Deduplicação e idempotência

A deduplicação foi validada em duas varreduras consecutivas.

Resultado observado no teste real:

```text
1ª varredura
Novos: 24
Vistos: 24

2ª varredura
Novos: 0
Vistos: 24
```

No GitHub Actions, em execuções reais consecutivas:

```text
1ª execução
Total coletado: 26
Novos: 26

2ª execução
Total coletado: 25
Novos: 2
```

A pequena diferença é compatível com uma fonte RSS dinâmica.

Regra de segurança:

```text
item relevante
→ processa
→ persiste
→ marca como visto
```

Se a persistência falhar, o item relevante não é marcado como visto e pode ser tentado novamente.

Itens corretamente descartados pelo filtro também são marcados como processados para evitar reprocessamento.

---

## Coleta e fontes externas

A coleta utiliza Google News RSS e outras fontes públicas previstas no projeto.

Melhorias implementadas:

- timeout explícito;
- retries controlados;
- backoff;
- User-Agent configurado;
- validação de status HTTP;
- isolamento de falha por chamada;
- testes sem internet;
- consultas do Google News limitadas a 7 dias.

Diagnóstico anterior:

```text
390 coletados
386 antigos
4 recentes
```

Após a correção:

```text
25 coletados
25 recentes
0 antigos
```

O excesso de conteúdo histórico foi eliminado.

---

## Parser e relevância

O parser reconhece:

- LATAM;
- Smiles;
- Azul;
- percentuais de bônus;
- validade quando disponível.

Validação real:

```text
390 itens analisados
304 com programa identificado
```

Foi identificado que a regra de relevância aceitava promoções de parceiros diferentes da Esfera.

Exemplos descartados corretamente após a correção:

- Livelo → Azul;
- Coopera → Smiles;
- Uau CAIXA → Azul;
- Inter Loop → Azul;
- Méliuz → Azul;
- Clube Smiles sem origem Esfera.

Regra atual:

```text
programa reconhecido
+
menção explícita à Esfera
=
candidato relevante
```

O parser não converte automaticamente expressões como:

```text
30 mil milhas bônus
```

em:

```text
30% de bônus
```

---

## Regras de negócio

As regras consideram:

- pontos Esfera disponíveis;
- meta financeira mínima;
- bônus mínimo por programa;
- valor do milheiro;
- programa ativo/inativo.

O dashboard consome as funções oficiais de domínio e não mantém uma segunda implementação dos principais cálculos.

Estados do simulador:

```text
✅ Aprovada
⚠️ Valor abaixo da meta
❌ Bônus abaixo da meta
```

Quando nenhuma opção atende simultaneamente às metas, o dashboard informa isso explicitamente e apresenta apenas o maior valor estimado, sem classificá-lo incorretamente como aprovado.

---

## Telegram

Credenciais:

```text
TELEGRAM_BOT_TOKEN
TELEGRAM_CHAT_ID
```

São obtidas por variáveis de ambiente.

Tratamentos implementados:

- credencial ausente;
- timeout;
- erro HTTP;
- falha de rede;
- resposta inválida;
- indisponibilidade do Telegram.

Fluxo:

```text
oportunidade persistida
→ tentativa de envio
→ sucesso: alertado=True
→ falha: alertado=False
```

Uma falha no Telegram não remove uma oportunidade já persistida.

Logs de erro não expõem o token do bot.

---

## Logging

O projeto utiliza `logging` em vez de depender de `print` para operações relevantes.

Contextos registrados incluem:

- início da varredura;
- fontes consultadas;
- quantidade de itens;
- parsing;
- oportunidades;
- persistência;
- Telegram;
- falhas.

Arquivo local:

```text
data/monitor.log
```

---

## Dashboard

Tecnologia:

```text
Streamlit
```

Elementos principais:

- pontos Esfera;
- oportunidades encontradas;
- meta financeira;
- última varredura;
- simulador comparativo;
- tabela de cenários;
- gráfico Altair;
- histórico de oportunidades;
- configurações;
- sincronização remota;
- varredura manual.

### Responsividade

KPIs:

```text
Desktop → 4 colunas
Tablet  → 2 colunas
Mobile  → 1 coluna
```

A sidebar utiliza expanders para reduzir altura e melhorar uso em telas menores.

### Tema

Suporta:

- Dark;
- Light.

Configuração padrão:

```text
.streamlit/config.toml
```

Tema padrão: Dark.

Os componentes customizados usam variáveis de tema do Streamlit para manter contraste nos dois modos.

### Gráfico

Tecnologia:

```text
Altair 5.5.0
```

O eixo Y inicia em:

```text
R$ 0
```

evitando escala negativa para valores financeiros.

---

## Testes

Framework:

```text
Pytest
```

Estado atual:

```text
50 passed
```

Cobertura funcional da suíte inclui:

- cálculos;
- parser;
- configuração;
- storage;
- monitor;
- fontes;
- Telegram;
- persistência;
- última varredura;
- idempotência;
- deduplicação;
- sincronização remota;
- tratamento de falhas.

Os testes utilizam:

- mocks;
- monkeypatch;
- tmp_path;
- fixtures.

Não dependem de:

- Google News real;
- Telegram real;
- internet real.

---

## Ruff

Configuração:

```text
pyproject.toml
```

Comando:

```bash
python -m ruff check .
```

Estado atual:

```text
All checks passed!
```

---

## CI

Workflow:

```text
.github/workflows/ci.yml
```

Executado em:

- `push`;
- `pull_request`.

Pipeline:

```text
Checkout
→ Python 3.12
→ dependências
→ Ruff
→ Pytest
```

A CI foi validada com sucesso no GitHub Actions.

---

## Monitor agendado

Workflow:

```text
.github/workflows/monitor.yml
```

Horários:

```text
11:00 UTC
21:00 UTC
```

Correspondentes atualmente a aproximadamente:

```text
08:00 UTC-3
18:00 UTC-3
```

Também suporta execução manual via:

```text
workflow_dispatch
```

O workflow foi validado manualmente de ponta a ponta.

Fluxo:

```text
checkout
→ Python 3.12
→ dependências
→ restaura branch state
→ executa monitor
→ persiste estado
→ commit automático em state
```

Possui:

- `timeout-minutes`;
- `concurrency`;
- `contents: write`;
- separação entre CI e automação agendada.

---

## Segurança

Práticas aplicadas:

- segredos fora do código;
- `.env` ignorado;
- `.env.example` sem valores reais;
- logs sem token Telegram;
- timeout em integrações externas;
- validação de respostas;
- escrita segura de estado;
- separação entre código e runtime state;
- CI independente de secrets;
- dashboard local sem autenticação obrigatória.

Limitação de segurança:

Se o dashboard for publicado com ações operacionais habilitadas, autenticação deverá ser implementada antes de exposição pública.

---

## Dependências

Arquivos:

```text
requirements.txt
requirements-dev.txt
```

Dependências principais incluem:

- Python 3.12;
- Streamlit;
- Pandas;
- Altair 5.5.0;
- Feedparser;
- Requests;
- Python Dotenv.

Desenvolvimento:

- Pytest;
- Ruff.

---

## Limitações atuais

O sistema:

- depende de fontes públicas;
- depende da indexação e disponibilidade do Google News;
- não garante cobertura de todas as promoções existentes;
- não executa transferências;
- não compra nem vende milhas;
- não realiza operações financeiras;
- não substitui validação dos termos oficiais;
- pode exigir análise manual quando dados estiverem ausentes ou ambíguos;
- não possui autenticação porque o dashboard atual é tratado como aplicação local.

Persistência JSON/JSONL continua adequada ao escopo atual.

Não foi adotado PostgreSQL, Redis, microservices ou outra infraestrutura sem necessidade real.

---

## Docker

Docker não foi considerado requisito obrigatório para o estado atual.

A aplicação já possui:

- ambiente virtual reproduzível;
- dependências declaradas;
- CI;
- execução agendada;
- dashboard local.

Docker poderá ser adicionado futuramente se houver necessidade concreta de deploy ou padronização adicional de ambiente.

---

## Próximos passos opcionais

Possíveis evoluções, sem caráter obrigatório para conclusão:

- novas fontes públicas;
- métricas de efetividade das fontes;
- histórico analítico;
- deploy autenticado;
- armazenamento externo caso o volume cresça;
- novas regras de oportunidade;
- cobertura adicional de testes de interface.

---

## Estado final

```text
CONCLUÍDO
```

Critérios técnicos validados:

- arquitetura;
- fluxo de dados;
- dashboard atualizado;
- persistência;
- branch `state`;
- sincronização remota;
- timezone;
- deduplicação;
- idempotência;
- recência;
- filtro Esfera;
- parser;
- regras de negócio;
- Telegram;
- logging;
- Ruff;
- 50 testes;
- CI;
- GitHub Actions agendado;
- responsividade;
- tema claro/escuro;
- segurança compatível com o escopo.

Pendências restantes são de apresentação final do repositório e material de portfólio, não de funcionamento do núcleo da aplicação.
