# Gemini provider setup

1. Create a Gemini API key through Google AI Studio.
2. Store it only in `backend/.env` as `GEMINI_API_KEY=...` and optionally configure `GEMINI_MODEL`.
3. Never commit `backend/.env`; the repository ignore rule covers `.env` files.
4. The frontend never receives the key. Gemini access is initialized only by backend provider code.
5. Ask AI accesses Gemini only through the backend after an allowlisted, authorized tool returns a bounded verified result. It never sends source files, database files, credentials, or full tables.

The official Python dependency is `google-genai`. The default model is configured centrally as `gemini-2.5-flash` and can be overridden with `GEMINI_MODEL`.
