# Little backend orchestration with OpenClaw patterns

This guide describes a web-first orchestration pattern for integrating a corporate portal backend (Little) with OpenClaw-style agent behavior.

## Goals

- Accept structured regulation requirements from a configurable system prompt block.
- Let the assistant automatically choose the right toolchain by policy and context.
- Keep runtime capabilities compatible with website deployment (browser-safe + server API tools).

## 1) Structured regulations in system prompt

Use a dedicated prompt block in your backend template instead of freeform hardcoding.

Example template:

```txt
[REGULATION_CATALOG]
- id: hr_internal_policy
  summary: Internal HR policy handling
  required_fields: employeeId, policyVersion, effectiveDate
  output_constraints: cite_policy, include_approval_path
- id: legal_contract_flow
  summary: Contract review process
  required_fields: contractType, jurisdiction, signerRole
  output_constraints: risk_matrix, escalation_required
- id: infosec_change_control
  summary: Infrastructure or access change requests
  required_fields: systemId, changeWindow, impactLevel
  output_constraints: rollback_plan, owner_signoff

[REGULATION_SELECTION_POLICY]
- Identify the closest regulation type before any action.
- If input is ambiguous, ask only the minimum clarifying questions.
- Never execute tools that violate output_constraints.
```

Recommended runtime behavior:

- Inject this block in the final system prompt (or prepend as a policy section).
- Keep the regulation catalog as editable config (DB/env/admin UI), not source-only text.
- Version the catalog and log the active version per run for auditability.

## 2) Automatic tool orchestration (OpenClaw-style)

Use capability-based tool routing:

1. Intent + regulation classification.
2. Policy evaluation (what tools are allowed under the selected regulation).
3. Tool scoring and selection (prefer least-privileged tool).
4. Execute and validate outputs against regulation constraints.

Minimal tool routing contract:

```ts
export type RegulationToolPolicy = {
  regulationId: string;
  allowedTools: string[];
  blockedTools?: string[];
  requiredChecks?: string[];
};
```

Key design rules:

- Avoid hardcoding vendor/tool names in core orchestration logic.
- Resolve tools by declared capabilities (read/search/retrieve/approve/notify).
- Keep deterministic ordering in tool candidate lists for prompt-cache stability.

## 3) Website-compatible plugin profile

For web deployment, prioritize plugins/tools that are safe for browser-initiated flows and server-side execution:

- HTTP/API tools (internal Little APIs, document services, approval workflows).
- Search/retrieval tools for regulation knowledge base.
- Messaging/notification adapters used by your portal UI.
- Disable terminal-local or host-specific tools unless required in server runtime.

Suggested split:

- Client (web app): chat UI, auth context, file upload metadata.
- Server (orchestration): model calls, policy enforcement, plugin execution, audit logs.

## 4) Regulation-aware execution checklist

- Determine regulation type first.
- Validate required fields.
- Select only policy-allowed tools.
- Enforce output constraints before user-visible response.
- Save audit record: user, regulationId, tools used, constraint checks, timestamp.

## 5) Rollout plan

1. Start with 2-3 regulation types and strict schemas.
2. Add tool policy maps for each type.
3. Enable shadow-mode validation logs.
4. Turn on hard enforcement after acceptance tests.
5. Expand regulation catalog incrementally.
