# Frontend connection to RAG Chat Backend

Base URL:

`http://<backend-host>:8000/api`

## Main endpoints

- `POST /api/chat` (SSE stream)
- `GET /api/health`
- `POST /api/documents/upload`
- `GET /api/documents/source/{index_name}/{doc_id}`

## SSE client template (token merge + sources)

Use this helper on frontend so token stream is merged into one readable answer.

```typescript
const API_BASE = process.env.NEXT_PUBLIC_RAG_API_URL || "http://localhost:8000/api";

export interface SourceItem {
  doc_id?: string;
  index_name?: string;
  content: string;
  title: string;
  score?: number;
  source?: string;
}

export async function sendMessageStream(
  sessionId: string,
  message: string,
  handlers: {
    onSources: (sources: SourceItem[]) => void;
    onText: (fullText: string) => void;
    onDone: () => void;
    onError: (error: string) => void;
  }
) {
  const resp = await fetch(`${API_BASE}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, message }),
  });

  if (!resp.ok || !resp.body) {
    handlers.onError(`HTTP ${resp.status}`);
    return;
  }

  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let currentEvent = "";
  let assistantText = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    for (const rawLine of lines) {
      const line = rawLine.trimEnd();
      if (!line) continue;

      if (line.startsWith("event:")) {
        currentEvent = line.slice(6).trim();
        continue;
      }

      if (!line.startsWith("data:")) continue;
      const data = line.slice(5).trimStart();

      if (currentEvent === "sources") {
        try {
          handlers.onSources(JSON.parse(data));
        } catch {
          handlers.onSources([]);
        }
        continue;
      }

      if (currentEvent === "token") {
        assistantText += data;
        handlers.onText(assistantText);
        continue;
      }

      if (currentEvent === "done") {
        handlers.onDone();
        return;
      }

      if (currentEvent === "error") {
        handlers.onError(data || "Unknown streaming error");
        return;
      }
    }
  }

  handlers.onDone();
}
```
