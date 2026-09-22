# LLM Chain
Implements a high-availability provider chain to ensure the AI is always responsive.

## Provider Order
1. **Ollama (Gemma 4)**: Primary local provider.
2. **Groq**: High-speed fallback.
3. **GLM-5.2**: Robust alternative.
4. **Gemini**: Final fallback.

## Logic
- **Circuit Breaker**: If a provider fails (e.g., 401 Unauthorized), it is put in cooldown for 10 minutes.
- **Rate Limiting**: Implements exponential backoff for 429 errors.

Links: [[Core.Backend]]
