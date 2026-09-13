# Ask AI grounding and provenance

The database and persisted analytical outputs remain authoritative. Gemini is an explanation layer only.

`ToolResult.data` is the verified source presented to the user. Ask AI response metadata preserves the tool, validated filters, authorized scope, dataset version, generation time, and navigation links. The response also labels the distinction between source data, persisted analytical results, and Gemini prose.

Before returning Gemini prose, the backend checks that every numeric token in the prose occurs in the verified result. If the provider returns an unsupported number, is unavailable, or times out, Ask AI falls back to a deterministic explanation of the verified structure. An empty or metadata-only result is explicitly reported as no data and is never sent to Gemini as a factual success.
