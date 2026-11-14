# API notes (checked 2026-11-14)

Every model call goes through OpenRouter with one key, `OPENROUTER_API_KEY`, sent as `Authorization: Bearer <key>`.

## Jev (TypeSafe System One)
- `POST https://openrouter.ai/api/alpha/decisions`
- Body: `{"model": "typesafe/jev-1.14", "state": <string|object>, "questions": {<id>: <question>}}`
- Question types ([docs](https://docs.typesafe.ai/primitives.md)):
  - `noul`: `{"type":"noul","instructions":str,"criteria":{"true":str,"false":str}}` (criteria optional) → `{"type":"noul","noul":p_yes}`
  - `choice`: `{"type":"choice","instructions":str,"criteria":{option: description}}` → `{"choice", "probabilities":{option:p}, "confidence"}`
  - `score`: `{"type":"score","instructions":str,"criteria":[level0, level1, ...]}` (low → high, 2–10 levels, numbered from 0) → `{"score": float position, "legend", "probabilities":[p per level], "confidence"}`
- Question ids are not sent to the model; write the full question in `instructions`.
- All questions in one request share the state and run in parallel.
- Response: `{"model", "answers": {...}, "usage": {"input_tokens", "output_tokens", "cost"}, "id", "provider"}`. `usage.cost` is in USD.
- Limits: 64k tokens per request, 32k per question. Price $0.042 per million input tokens; output is free.
- Probe: 1 Noul on the Rami state → 200 OK, 305 ms, 433 input tokens, $0.000018.

## LLM (Claude Sonnet 5.5)
- `POST https://openrouter.ai/api/v1/chat/completions`, model `anthropic/claude-sonnet-5.5`
- OpenAI-style body: `messages`, `max_tokens`, and `response_format: {"type":"json_schema", ...}` for structured output.
- Response `usage` has `prompt_tokens`, `completion_tokens` and `cost` (USD).
- Price $2 / $10 per million input / output tokens.
- Probe: 200 OK, 1181 ms.

## Cost metric
Both APIs return the real cost of each call in `usage.cost`, so the metrics use **measured cost**, not a price table.
