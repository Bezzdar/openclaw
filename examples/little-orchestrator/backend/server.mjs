import http from "node:http";

const PORT = Number.parseInt(process.env.PORT ?? "8787", 10);
const OPENCLAW_URL = process.env.OPENCLAW_URL ?? "http://127.0.0.1:18789/rpc";
const OPENCLAW_AGENT_ID = process.env.OPENCLAW_AGENT_ID ?? "default";

function json(res, code, payload) {
  res.writeHead(code, { "content-type": "application/json; charset=utf-8" });
  res.end(JSON.stringify(payload));
}

function parseRegulationsEnv() {
  const raw = process.env.LITTLE_REGULATIONS_JSON?.trim();
  if (!raw) {
    return [];
  }
  try {
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) {
      return [];
    }
    return parsed
      .map((row) => ({
        id: typeof row?.id === "string" ? row.id.trim() : "",
        requirements: Array.isArray(row?.requirements)
          ? row.requirements.map((x) => String(x).trim()).filter(Boolean)
          : [],
        allowedTools: Array.isArray(row?.allowedTools)
          ? row.allowedTools.map((x) => String(x).trim()).filter(Boolean)
          : [],
      }))
      .filter((row) => row.id && row.requirements.length > 0)
      .toSorted((a, b) => a.id.localeCompare(b.id));
  } catch {
    return [];
  }
}

function buildSystemPrompt() {
  const regs = parseRegulationsEnv();
  if (regs.length === 0) {
    return "";
  }
  const out = [
    "## Little Regulation Runtime Policy",
    "Before any tool use, classify which regulation id applies.",
    "If ambiguous, ask minimum clarifying questions.",
    "Use only tools allowed by selected regulation when allowedTools is set.",
    "Prefer website-safe tools: web_search, web_fetch, message, canvas.",
    "",
  ];
  for (const reg of regs) {
    out.push(`### ${reg.id}`);
    out.push("Requirements:");
    for (const req of reg.requirements) {
      out.push(`- ${req}`);
    }
    if (reg.allowedTools.length > 0) {
      out.push(`Allowed tools: ${reg.allowedTools.join(", ")}`);
    }
    out.push("");
  }
  return out.join("\n");
}

async function callOpenClaw(message) {
  const body = {
    jsonrpc: "2.0",
    id: Date.now(),
    method: "agent",
    params: {
      message,
      agentId: OPENCLAW_AGENT_ID,
      channel: "webchat",
      extraSystemPrompt: buildSystemPrompt(),
      timeout: 120,
      idempotencyKey: `little-${Date.now()}-${Math.random().toString(16).slice(2)}`,
    },
  };

  const resp = await fetch(OPENCLAW_URL, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await resp.json();
  if (data?.error) {
    throw new Error(data.error?.message ?? "RPC error");
  }
  const payloads = data?.result?.result?.payloads ?? [];
  return (
    payloads
      .map((p) => p?.text)
      .filter(Boolean)
      .join("\n\n") || "(no response)"
  );
}

const server = http.createServer(async (req, res) => {
  if (req.method === "GET" && req.url === "/health") {
    return json(res, 200, { ok: true });
  }
  if (req.method === "POST" && req.url === "/api/chat") {
    let raw = "";
    req.on("data", (chunk) => (raw += chunk));
    req.on("end", async () => {
      try {
        const input = JSON.parse(raw || "{}");
        const message = String(input?.message ?? "").trim();
        if (!message) {
          return json(res, 400, { error: "message is required" });
        }
        const text = await callOpenClaw(message);
        return json(res, 200, { text });
      } catch (err) {
        return json(res, 500, { error: String(err) });
      }
    });
    return;
  }
  json(res, 404, { error: "not found" });
});

server.listen(PORT, () => {
  console.log(`Little orchestrator backend listening on :${PORT}`);
});
