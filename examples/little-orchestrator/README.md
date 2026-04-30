# Little orchestrator starter (frontend + backend)

Готовый минимальный проект, который можно разложить на фронт и бэк.

## Что делает

- Backend проксирует запросы в OpenClaw Gateway RPC (`agent` method).
- Регламентные требования задаются через `LITTLE_REGULATIONS_JSON`.
- Эти требования автоматически превращаются в `extraSystemPrompt`.
- Канал принудительно web (`channel: "webchat"`) для website-сценария.

## Запуск backend

```bash
cd examples/little-orchestrator/backend
PORT=8787 \
OPENCLAW_URL=http://127.0.0.1:18789/rpc \
OPENCLAW_AGENT_ID=default \
LITTLE_REGULATIONS_JSON='[
  {"id":"hr_policy","requirements":["employeeId required","cite policy version"],"allowedTools":["web_search","web_fetch","message"]},
  {"id":"legal_contract","requirements":["jurisdiction required","include risk summary"],"allowedTools":["web_fetch","message"]}
]' \
node server.mjs
```

## Раздача frontend

```bash
cd examples/little-orchestrator/frontend
python3 -m http.server 8788
```

Если фронт и бэк на разных доменах — добавьте reverse proxy или CORS-обработку.
