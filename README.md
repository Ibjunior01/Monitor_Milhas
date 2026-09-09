# ✈️ Monitor de Milhas

Aplicação em Python para monitoramento de oportunidades de transferência de pontos da **Esfera** para programas de fidelidade aérea, com coleta automatizada de fontes públicas, análise de promoções, regras de negócio, alertas via Telegram e dashboard em Streamlit.

O projeto foi desenvolvido com foco em:

- automação;
- confiabilidade do fluxo de dados;
- deduplicação;
- persistência;
- tratamento de falhas;
- testes automatizados;
- CI;
- execução agendada;
- observabilidade;
- responsividade;
- tema claro e escuro.

---

## 📌 Problema

Promoções de transferência de pontos podem surgir em diferentes fontes e permanecer disponíveis por períodos curtos.

Acompanhar manualmente essas oportunidades exige consultar diversos sites, identificar:

- programa de destino;
- percentual de bônus;
- validade;
- valor estimado das milhas;
- aderência às metas do usuário.

Além disso, um monitor automatizado precisa evitar:

- processar repetidamente a mesma notícia;
- considerar conteúdo antigo;
- classificar promoções de outros parceiros como se fossem da Esfera;
- perder oportunidades quando integrações externas falham;
- exibir dados desatualizados no dashboard.

---

## 💡 Solução

O Monitor de Milhas automatiza esse fluxo:

```text
Fontes públicas
      ↓
Coleta RSS / HTTP
      ↓
Filtro de recência
      ↓
Parser
      ↓
Filtro Esfera
      ↓
Regras de negócio
      ↓
Persistência
      ↓
Telegram
      ↓
Dashboard
```

O sistema monitora atualmente oportunidades relacionadas a:

- LATAM Pass;
- Smiles;
- Azul Fidelidade.

A origem monitorada é a **Esfera**.

Resultados relacionados exclusivamente a outros parceiros, como Livelo, Coopera, Méliuz, Inter Loop ou programas similares, são descartados pelo filtro de relevância.

---

## 🚀 Funcionalidades

### Monitoramento

- coleta de notícias por Google News RSS;
- consultas limitadas aos últimos 7 dias;
- múltiplos termos de busca;
- timeout explícito;
- retries controlados;
- backoff entre tentativas;
- User-Agent configurado;
- isolamento de falhas HTTP.

### Parser

Identifica:

- programa de fidelidade;
- percentual de bônus;
- validade quando disponível;
- dados relevantes da promoção.

O parser não inventa valores ausentes.

Exemplo:

```text
"30 mil milhas bônus"
```

não é interpretado automaticamente como:

```text
30% de bônus
```

---

## 🎯 Regras de negócio

O sistema considera:

- quantidade de pontos Esfera disponíveis;
- bônus mínimo por programa;
- valor estimado do milheiro;
- meta financeira mínima;
- programa ativo ou inativo.

O dashboard possui um simulador comparativo para:

- LATAM;
- Smiles;
- Azul.

Cada cenário mostra:

- bônus;
- milhas finais;
- valor do milheiro;
- valor estimado;
- meta de bônus;
- status.

Estados possíveis no simulador:

```text
✅ Aprovada
⚠️ Valor abaixo da meta
❌ Bônus abaixo da meta
```

---

## 🧠 Deduplicação e idempotência

Links já processados são registrados em:

```text
data/vistos.json
```

A regra foi projetada para evitar perda de oportunidades.

Um item relevante segue o fluxo:

```text
processamento
→ cálculo
→ persistência
→ marcação como visto
```

Se a persistência da oportunidade falhar, o link não é marcado como processado e poderá ser tentado novamente.

Itens analisados e corretamente descartados como irrelevantes também são registrados como processados para evitar reprocessamento desnecessário.

A deduplicação foi validada com duas varreduras consecutivas:

```text
1ª execução
→ itens novos processados
→ links persistidos

2ª execução
→ itens já conhecidos ignorados
```

---

## 💾 Persistência

O projeto utiliza persistência simples em JSON e JSONL.

### Configuração

```text
data/config.json
data/cotacao_milhas.json
```

### Estado de execução

```text
data/vistos.json
data/oportunidades.jsonl
data/ultima_varredura.json
```

Arquivos JSON críticos utilizam escrita por arquivo temporário seguida de substituição do destino, reduzindo risco de corrupção por escrita incompleta.

---

## ☁️ Persistência no GitHub Actions

Runners do GitHub Actions possuem filesystem efêmero.

Por isso, o estado operacional não depende do disco do runner.

O projeto utiliza uma branch dedicada:

```text
state
```

Ela armazena exclusivamente o runtime state:

```text
data/vistos.json
data/oportunidades.jsonl
data/ultima_varredura.json
```

Fluxo:

```text
GitHub Actions
      ↓
restaura branch state
      ↓
executa monitor
      ↓
atualiza estado
      ↓
commit automático
      ↓
branch state
```

Isso mantém código e estado separados:

```text
main  → aplicação
state → runtime state
```

---

## 🔄 Sincronização do dashboard

O dashboard local consegue sincronizar o estado produzido pelo monitor automático.

Fluxo:

```text
GitHub Actions
      ↓
branch state
      ↓
state_sync.py
      ↓
storage local
      ↓
dashboard
```

A sincronização compara timestamps.

### Estado remoto mais recente

```text
→ atualiza estado local
```

### Estado local igual ou mais recente

```text
→ mantém estado local
```

### GitHub indisponível

```text
→ preserva dados locais
```

O usuário também pode executar manualmente:

```text
🔄 Atualizar dados remotos
```

---

## 🕒 Datas e timezone

Timestamps novos são armazenados em UTC com timezone explícito:

```text
2026-09-08T18:03:24+00:00
```

O dashboard converte a apresentação para horário UTC-3.

Estados antigos gravados sem timezone possuem tratamento de compatibilidade.

---

## 📲 Telegram

O sistema pode enviar oportunidades aprovadas para um bot do Telegram.

Credenciais são obtidas exclusivamente por variáveis de ambiente:

```text
TELEGRAM_BOT_TOKEN
TELEGRAM_CHAT_ID
```

O monitor trata:

- ausência de credenciais;
- timeout;
- falha HTTP;
- falha de rede;
- resposta inválida;
- indisponibilidade do Telegram.

Uma falha no Telegram não remove uma oportunidade já persistida.

O campo:

```text
alertado
```

só é atualizado para `true` após confirmação de envio.

O tratamento de erros evita registrar o token do bot nos logs.

---

## 📊 Dashboard

Interface desenvolvida com Streamlit.

Principais elementos:

- pontos Esfera disponíveis;
- oportunidades encontradas;
- meta financeira;
- última varredura;
- simulador comparativo;
- gráfico de valor estimado;
- histórico de oportunidades;
- configuração por programa;
- sincronização remota;
- execução manual do monitor.

### Responsividade

Os KPIs se adaptam conforme a largura:

```text
Desktop → 4 colunas
Tablet  → 2 colunas
Mobile  → 1 coluna
```

A sidebar utiliza seções recolhíveis para reduzir o espaço vertical.

### Tema

O dashboard suporta:

- Dark;
- Light.

O tema padrão do projeto é Dark.

Componentes customizados utilizam variáveis do tema do Streamlit para preservar contraste nos dois modos.

---

## 📈 Gráfico

O comparativo financeiro utiliza Altair.

O eixo Y possui base fixa em:

```text
R$ 0
```

evitando escalas negativas para valores financeiros que não podem ser negativos.

---

## 🧪 Testes automatizados

Framework:

```text
Pytest
```

Estado atual:

```text
50 testes passando
```

A suíte cobre áreas como:

- cálculos;
- parser;
- configuração;
- storage;
- monitor;
- fontes externas;
- Telegram;
- persistência;
- deduplicação;
- última varredura;
- sincronização remota;
- tratamento de falhas.

Os testes não dependem de:

- Google News real;
- Telegram real;
- conexão com internet.

São utilizados:

- mocks;
- monkeypatch;
- tmp_path;
- fixtures.

Executar:

```bash
python -m pytest
```

---

## 🧹 Qualidade de código

O projeto utiliza Ruff.

Configuração:

```text
pyproject.toml
```

Executar:

```bash
python -m ruff check .
```

Fluxo de validação recomendado:

```bash
python -m ruff check .
python -m pytest
```

---

## ⚙️ CI

Workflow:

```text
.github/workflows/ci.yml
```

Executado em:

```text
push
pull_request
```

Pipeline:

```text
Checkout
→ Python 3.12
→ dependências
→ Ruff
→ Pytest
```

A CI não depende de:

- Telegram;
- Google News;
- secrets.

---

## ⏰ Monitor agendado

Workflow:

```text
.github/workflows/monitor.yml
```

Execuções configuradas:

```text
11:00 UTC
21:00 UTC
```

Equivalentes atualmente a aproximadamente:

```text
08:00 UTC-3
18:00 UTC-3
```

Também é possível executar manualmente pelo:

```text
workflow_dispatch
```

O workflow foi validado manualmente com sucesso.

---

## 🪵 Logging

O projeto utiliza logging para registrar operações como:

- início da execução;
- fontes consultadas;
- quantidade de itens;
- processamento;
- oportunidades;
- Telegram;
- persistência;
- falhas.

Arquivo local:

```text
data/monitor.log
```

Tokens e credenciais não devem ser registrados.

---

## 🔐 Segurança

Práticas aplicadas:

- tokens fora do código;
- `.env` ignorado pelo Git;
- `.env.example` sem segredos;
- timeout em integrações externas;
- tratamento controlado de exceções;
- logs sem exposição do token Telegram;
- escrita segura de JSON;
- workflow com responsabilidades separadas;
- estado operacional separado da branch principal.

O dashboard executado localmente não exige autenticação.

Caso seja publicado com ações operacionais habilitadas, autenticação deverá ser considerada antes de disponibilização pública.

---

## 🗂️ Estrutura

```text
Monitor_Milhas/
├── .github/
│   └── workflows/
│       ├── ci.yml
│       └── monitor.yml
│
├── .streamlit/
│   └── config.toml
│
├── data/
│   ├── config.json
│   └── cotacao_milhas.json
│
├── src/
│   ├── __init__.py
│   ├── calculations.py
│   ├── config.py
│   ├── logger.py
│   ├── models.py
│   ├── monitor.py
│   ├── parser.py
│   ├── sources.py
│   ├── state_sync.py
│   ├── storage.py
│   └── telegram_alerts.py
│
├── tests/
├── dashboard.py
├── main.py
├── pyproject.toml
├── requirements.txt
├── requirements-dev.txt
└── README.md
```

---

## 🛠️ Instalação

Recomendado:

```text
Python 3.12
```

Clone:

```bash
git clone https://github.com/Ibjunior01/Monitor_Milhas.git
cd Monitor_Milhas
```

Crie o ambiente virtual.

### Windows

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Instale:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

---

## 🔑 Variáveis de ambiente

Crie:

```text
.env
```

baseado em:

```text
.env.example
```

Exemplo:

```env
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
```

Nunca publique valores reais.

---

## ▶️ Executar o monitor

```bash
python main.py
```

---

## 📊 Executar o dashboard

```bash
python -m streamlit run dashboard.py
```

Normalmente:

```text
http://localhost:8501
```

---

## 🧪 Ambiente de desenvolvimento

Instale:

```bash
python -m pip install -r requirements-dev.txt
```

Valide:

```bash
python -m ruff check .
python -m pytest
```

---

## 📦 Stack

- Python 3.12
- Streamlit
- Pandas
- Altair
- Feedparser
- Requests
- Python Dotenv
- Pytest
- Ruff
- GitHub Actions
- Telegram Bot API
- JSON / JSONL

---

## ⚠️ Limitações

O sistema:

- depende de fontes públicas;
- depende da disponibilidade e do conteúdo publicado pelo Google News;
- não garante que toda promoção existente será encontrada;
- não executa transferência de pontos;
- não compra ou vende milhas;
- não realiza operações financeiras;
- não substitui validação manual dos termos oficiais de uma promoção;
- pode exigir revisão manual quando informações não estiverem claras no título ou resumo.

O projeto tem finalidade de monitoramento e apoio à análise.

---

## 🗺️ Roadmap

Possíveis evoluções futuras:

- novas fontes públicas;
- filtros adicionais;
- histórico analítico;
- métricas de efetividade das fontes;
- deploy autenticado do dashboard;
- armazenamento externo caso o volume de dados justifique;
- novas regras de oportunidade.

Essas evoluções não são requisitos para o estado atual do projeto.

---

## 📌 Status

```text
NÚCLEO OPERACIONAL VALIDADO
```

Principais validações concluídas:

- fluxo de dados;
- atualização do dashboard;
- persistência;
- sincronização;
- idempotência;
- deduplicação;
- coleta recente;
- filtro Esfera;
- Telegram;
- testes;
- Ruff;
- CI;
- GitHub Actions;
- responsividade;
- tema claro/escuro.

A documentação e a preparação final para portfólio completam o fechamento do projeto.
