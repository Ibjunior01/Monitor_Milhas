# ✈️ Monitor de Milhas · Esfera

MVP local para monitorar promoções de transferência bonificada do programa Esfera para LATAM Pass, Smiles e Azul Fidelidade.

> **Importante:** Este sistema monitora apenas fontes públicas e envia alertas para análise manual. Ele **não automatiza login, não acessa contas pessoais e não realiza transferências**.

---

## 📦 Estrutura do projeto

```
monitor-milhas/
├── src/
│   ├── models.py          # Dataclasses de domínio
│   ├── config.py          # Configurações e .env
│   ├── calculations.py    # Cálculos financeiros (puro, testável)
│   ├── sources.py         # Coleta de feeds RSS públicos
│   ├── parser.py          # Extração de programa e % de bônus
│   ├── storage.py         # Persistência em JSON/JSONL
│   ├── telegram_alerts.py # Alertas via Telegram Bot
│   ├── monitor.py         # Orquestrador principal
│   └── logger.py          # Logger centralizado
├── dashboard.py           # Dashboard Streamlit
├── main.py                # Entry point CLI
├── data/
│   ├── config.json        # Metas e configurações
│   ├── cotacao_milhas.json# Valor do milheiro por programa
│   ├── oportunidades.jsonl# Histórico de oportunidades
│   └── vistos.json        # Links já processados
├── tests/
│   ├── test_calculations.py
│   └── test_parser.py
├── .env.example
├── requirements.txt
└── README.md
```

---

## 🚀 Instalação

### 1. Pré-requisitos
- Python 3.10 ou superior
- pip

### 2. Clone o repositório
```bash
git clone https://github.com/seuusuario/monitor-milhas.git
cd monitor-milhas
```

### 3. Crie e ative o ambiente virtual
```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# Linux/macOS
python -m venv .venv
source .venv/bin/activate
```

### 4. Instale as dependências
```bash
pip install -r requirements.txt
```

### 5. Configure as variáveis de ambiente
```bash
# Copie o arquivo de exemplo
copy .env.example .env      # Windows
cp .env.example .env        # Linux/macOS

# Edite o .env com seus dados reais
```

---

## 🤖 Configurar o bot do Telegram

### Criar o bot
1. Abra o Telegram e busque por **@BotFather**
2. Envie `/newbot`
3. Siga as instruções (escolha nome e username)
4. Copie o **token** gerado (ex: `123456789:ABCdef...`)
5. Cole em `TELEGRAM_BOT_TOKEN` no seu `.env`

### Obter seu Chat ID
1. Busque **@userinfobot** ou **@myidbot** no Telegram
2. Envie qualquer mensagem
3. O bot responde com seu ID (ex: `987654321`)
4. Cole em `TELEGRAM_CHAT_ID` no seu `.env`

> Alternativamente: envie uma mensagem para o seu bot e acesse:
> `https://api.telegram.org/bot{SEU_TOKEN}/getUpdates`

---

## ▶️ Como usar

### Executar varredura manual
```bash
python main.py
```

### Abrir o dashboard
```bash
streamlit run dashboard.py
```
Acesse: `http://localhost:8501`

### Rodar os testes
```bash
pytest tests/ -v
```

---

## ⏰ Agendar no Windows (Agendador de Tarefas)

1. Abra **Agendador de Tarefas** (Task Scheduler)
2. Clique em **Criar Tarefa Básica**
3. Nome: `Monitor de Milhas`
4. Gatilho: Diariamente às 08:00 (ou intervalo desejado)
5. Ação: **Iniciar um programa**
   - Programa: `C:\caminho\para\.venv\Scripts\python.exe`
   - Argumentos: `C:\caminho\para\monitor-milhas\main.py`
   - Iniciar em: `C:\caminho\para\monitor-milhas`
6. Salve e teste.

Ou crie um arquivo `.bat`:
```bat
@echo off
cd /d C:\caminho\para\monitor-milhas
.venv\Scripts\python.exe main.py
```

---

## ⚙️ Configuração

Edite `data/config.json` ou use o painel lateral do dashboard:

```json
{
  "pontos_disponiveis": 32000,
  "meta_financeira_minima": 900.0,
  "programas": {
    "LATAM":  { "bonus_minimo_pct": 20 },
    "SMILES": { "bonus_minimo_pct": 70 },
    "AZUL":   { "bonus_minimo_pct": 80 }
  }
}
```

Edite `data/cotacao_milhas.json` para ajustar o valor do milheiro:
```json
{
  "LATAM":  25.0,
  "SMILES": 16.0,
  "AZUL":   13.0
}
```

---

## 🧮 Como funciona o cálculo

```
Milhas finais = pontos × (1 + bônus% / 100)
Valor estimado = (milhas / 1.000) × valor_milheiro

Exemplo:
32.000 pontos × 1,30 (30% bônus) = 41.600 milhas
41.600 / 1.000 × R$ 25,00 = R$ 1.040,00
```

---

## 📊 Regras de decisão

| Situação | Status | Alerta Telegram |
|---|---|---|
| Bônus ≥ meta **E** valor ≥ meta financeira | ✅ Aprovada | Sim |
| Bônus ≥ meta, valor abaixo | ⚠️ Abaixo da meta | Não |
| Bônus abaixo, valor ok | ⏳ Aguardando | Não |
| Ambos abaixo | ❌ Ignorada | Não |

---

## 🗺️ Roadmap

### Fase 1 — MVP local (atual)
- [x] Monitoramento via Google News RSS
- [x] Extração de programa e % de bônus
- [x] Cálculo financeiro
- [x] Alerta Telegram
- [x] Dashboard Streamlit
- [x] Persistência em JSON/JSONL
- [x] Deduplicação de alertas

### Fase 2 — MVP online
- [ ] Publicar dashboard no Streamlit Community Cloud
- [ ] Execução agendada via GitHub Actions
- [ ] Migrar storage para Supabase (free tier)
- [ ] Cadastro simples de 2–3 usuários beta

### Fase 3 — Micro-SaaS
- [ ] Autenticação (Supabase Auth / Clerk)
- [ ] Planos pagos (Stripe)
- [ ] Painel do usuário com preferências individuais
- [ ] Múltiplos canais de notificação (WhatsApp, e-mail)
- [ ] Painel administrativo

### Fase 4 — Produto escalável
- [ ] Backend FastAPI
- [ ] PostgreSQL gerenciado
- [ ] Workers com Celery/ARQ
- [ ] Observabilidade (Sentry, logs estruturados)
- [ ] Deploy profissional (Railway, Render, VPS)
- [ ] API própria com documentação

---

## 🔒 Segurança

- Tokens nunca no código — apenas em variáveis de ambiente
- `.env` listado no `.gitignore`
- Nenhum acesso a login ou senhas de programas de pontos
- Coleta apenas de feeds RSS e páginas públicas

---

## 📄 Licença

MIT — use, modifique e distribua à vontade.
