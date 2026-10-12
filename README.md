# Edith — Assistente Pessoal IA

Assistente pessoal tipo Jarvis: agenda, saúde, estudos ENEM, produtividade e chat IA. Dashboard web + API Flask.

## Funcionalidades

- **Dashboard web** com dados em tempo real
- **Agenda** — compromissos, próximos 7 dias
- **Saúde** — peso, treinos, sono, alimentação
- **Estudos ENEM** — horas por matéria, simulados, meta semanal 35h
- **Produtividade** — checklist diário de 9 tarefas
- **Chat IA** — via OpenRouter (gratuito) ou respostas locais (fallback)

## Quickstart

```bash
pip install -r requirements.txt
cp .env.example .env   # opcional: OPENROUTER_API_KEY, TELEGRAM_BOT_TOKEN
python server.py
# abre http://localhost:5000
```

CLI:

```bash
python -m edith.core dashboard
python -m edith.core chat "Qual minha agenda?"
```

## Deploy gratuito (Render)

1. Suba este repo no GitHub
2. Em [render.com](https://render.com) → New → Web Service → conecte o repo
3. Build: `pip install -r requirements.txt` · Start: `gunicorn server:app --bind 0.0.0.0:$PORT`
4. O `render.yaml` já deixa isso pronto (Blueprint)

Também funciona em Railway, Fly.io ou qualquer host Python (Procfile incluído).

## Variáveis de ambiente

| Var | Uso |
|-----|-----|
| `OPENROUTER_API_KEY` | Chat IA avançado (opcional; sem ela, usa respostas locais) |
| `TELEGRAM_BOT_TOKEN` | Envio de notificações Telegram (opcional) |
| `EDITH_DATA_DIR` | Diretório de dados (padrão: `~/Evolution/...`) |
| `PORT` | Porta do servidor (padrão: 5000) |

## Estrutura

```
edith/          # núcleo portátil (importa modules direto)
modules/        # jarvis_agenda, jarvis_saude, jarvis_enem, jarvis_produtividade
templates/      # dashboard web
server.py       # Flask API
```

## API

- `GET /` — dashboard web
- `GET /api/dashboard` — JSON completo
- `POST /api/chat` — `{"message": "..."}` → `{"response": "..."}`
