import os
import time
from dataclasses import dataclass

import requests


class MissingApiKeyError(RuntimeError):
    pass


@dataclass
class StudyAssistantLLM:
    provider: str = "gemini"

    def answer_question(self, question: str, context: str) -> str:
        if not context or len(context.strip()) < 80:
            return "I could not find this in the uploaded document."

        prompt = f"""
You are an AI Study Assistant using retrieval augmented generation.
Answer the student's question using only the supplied document context.
If the answer is not present in the context, say: "I could not find this in the uploaded document."
Do not use outside knowledge, assumptions, or guesses.
Do not fill missing details from memory.
Keep the explanation clear, exam-oriented, and cite source names/page numbers from the context.

Document context:
{context}

Student question:
{question}
"""
        return self._generate(prompt)

    def generate_summary(self, topic: str, context: str) -> str:
        if not context or len(context.strip()) < 80:
            return "I could not find enough relevant information in the uploaded document."

        prompt = f"""
Create an exam-focused summary from the supplied document context.
Topic or chapter request: {topic}

Strict rules:
- Use only the supplied document context.
- Do not add outside knowledge, guesses, or unsupported definitions.
- If a requested topic is not found, clearly say it is not found in the uploaded document.
- Keep the language simple, correct, and useful for exam revision.
- Mention source/page references when the context provides them.

Use exactly this structure:
## Summary
- 5 to 8 concise bullet points from the document.

## Key Concepts
- Important concepts only from the context.

## Important Definitions
- Definitions only if they appear in the context. If not available, write "Not found in the uploaded document."

## Important Formulas
- Formulas only if they appear in the context. If not available, write "Not found in the uploaded document."

## Likely Exam Points
- Short exam-oriented points from the context.

Before answering, silently verify that every point is supported by the context.

Document context:
{context}
"""
        return self._generate(prompt)

    def generate_mcqs(self, count: int, context: str) -> str:
        if not context or len(context.strip()) < 80:
            return "I could not find enough relevant information in the uploaded document."

        prompt = f"""
Generate {count} multiple choice questions from the supplied document context.

Strict rules:
- Use only facts present in the document context.
- Do not create questions from outside knowledge.
- Do not create misleading or ambiguous questions.
- Every question must have exactly four options.
- Only one option must be correct.
- The correct answer must exactly match one of A, B, C, or D.
- The explanation must be based on the document context.
- If there is not enough context to create {count} good MCQs, create fewer good MCQs instead of inventing.

Use exactly this format:

Q1. Question text?
A. Option A
B. Option B
C. Option C
D. Option D
Answer: A
Explanation: One short explanation from the document.

Q2. Question text?
A. Option A
B. Option B
C. Option C
D. Option D
Answer: B
Explanation: One short explanation from the document.

Before final output, silently check that every answer is supported by the context and that each MCQ follows the format.

Document context:
{context}
"""
        return self._generate(prompt)

    def generate_quiz_json(self, count: int, context: str) -> str:
        if not context or len(context.strip()) < 80:
            return "[]"

        prompt = f"""
Generate an interactive quiz from the supplied document context.
Return only valid JSON. Do not wrap it in markdown.

JSON schema:
[
  {{
    "question": "Question text",
    "options": {{
      "A": "Option A",
      "B": "Option B",
      "C": "Option C",
      "D": "Option D"
    }},
    "answer": "A",
    "explanation": "One-line explanation grounded in the context"
  }}
]

Rules:
- Generate exactly {count} questions.
- Use only facts present in the document context.
- Do not invent questions from outside knowledge.
- Make questions exam-oriented.
- Use four options for every question.
- The answer must be only A, B, C, or D.

Document context:
{context}
"""
        return self._generate(prompt)

    def generate_viva_questions(self, context: str) -> str:
        if not context or len(context.strip()) < 80:
            return "I could not find enough relevant information in the uploaded document."

        prompt = f"""
Generate viva questions from the supplied document context.
Group them by difficulty: Basic, Intermediate, and Advanced.
Include concise model answers for each question.
Only use the context below. Do not add outside facts.

Document context:
{context}
"""
        return self._generate(prompt)

    def generate_study_notes(self, context: str) -> str:
        if not context or len(context.strip()) < 80:
            return "I could not find enough relevant information in the uploaded document."

        prompt = f"""
Create short revision notes from the supplied document context.
Use bullet notes, exam-oriented language, important terms, and quick memory cues.
Only use the context below. Do not add outside facts.

Document context:
{context}
"""
        return self._generate(prompt)

    def _generate(self, prompt: str) -> str:
        provider = self.provider.lower().strip()
        if provider == "gemini":
            return self._generate_with_gemini(prompt)
        if provider == "openrouter":
            return self._generate_with_openai_compatible(
                prompt=prompt,
                api_key_env="OPENROUTER_API_KEY",
                model_env="OPENROUTER_MODEL",
                default_model="openai/gpt-4o-mini",
                base_url="https://openrouter.ai/api/v1",
                extra_headers={
                    "HTTP-Referer": os.getenv("APP_URL", "http://localhost:8501"),
                    "X-Title": "AI Study Assistant",
                },
            )
        if provider == "openai":
            return self._generate_with_openai_compatible(
                prompt=prompt,
                api_key_env="OPENAI_API_KEY",
                model_env="OPENAI_MODEL",
                default_model="gpt-4o-mini",
                base_url=None,
                extra_headers=None,
            )

        raise ValueError(f"Unsupported LLM provider: {self.provider}")

    def _generate_with_gemini(self, prompt: str) -> str:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise MissingApiKeyError("Set GEMINI_API_KEY in your .env file.")

        model_names = self._gemini_model_candidates(
            primary=os.getenv("GEMINI_MODEL", "gemini-3.5-flash"),
            fallbacks=os.getenv(
                "GEMINI_FALLBACK_MODELS",
                "gemini-flash-latest,gemini-3.1-flash-lite",
            ),
        )
        timeout = int(os.getenv("GEMINI_TIMEOUT", "60"))
        retries = int(os.getenv("GEMINI_RETRIES", "3"))
        response = self._generate_gemini_with_fallbacks(
            api_key=api_key,
            model_names=model_names,
            prompt=prompt,
            timeout=timeout,
            retries=retries,
        )

        payload = response.json()
        parts = (
            payload.get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [])
        )
        text = " ".join(part.get("text", "") for part in parts).strip()
        return text or "No response generated."

    def _generate_gemini_with_fallbacks(
        self,
        api_key: str,
        model_names: list[str],
        prompt: str,
        timeout: int,
        retries: int,
    ) -> requests.Response:
        errors: list[str] = []

        for model_name in model_names:
            for attempt in range(1, retries + 1):
                try:
                    response = requests.post(
                        f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent",
                        headers={"x-goog-api-key": api_key},
                        json={
                            "contents": [{"parts": [{"text": prompt}]}],
                            "generationConfig": {
                                "temperature": 0.0,
                                "maxOutputTokens": 4096,
                            },
                        },
                        timeout=timeout,
                    )
                    response.raise_for_status()
                    return response
                except requests.RequestException as exc:
                    detail = self._safe_request_error(exc)
                    errors.append(f"{model_name}: {detail}")

                    status = getattr(getattr(exc, "response", None), "status_code", None)
                    should_retry = status in {429, 500, 502, 503, 504} or status is None
                    if should_retry and attempt < retries:
                        time.sleep(min(2 ** (attempt - 1), 6))
                        continue
                    break

        raise RuntimeError(self._summarize_gemini_errors(errors))

    @staticmethod
    def _gemini_model_candidates(primary: str, fallbacks: str) -> list[str]:
        candidates: list[str] = []
        for model_name in [primary, *fallbacks.split(",")]:
            cleaned = model_name.strip()
            if cleaned and cleaned not in candidates:
                candidates.append(cleaned)
        return candidates

    @staticmethod
    def _summarize_gemini_errors(errors: list[str]) -> str:
        if any("DNS lookup failed" in error for error in errors):
            return (
                "Gemini request failed because DNS lookup failed for "
                "generativelanguage.googleapis.com. Check internet/DNS/VPN/firewall."
            )

        if any("HTTP 503" in error for error in errors):
            return (
                "Gemini request failed because all configured Gemini models are "
                "currently overloaded. Try again in 1-2 minutes, or set another "
                "provider such as OpenRouter."
            )

        return (
            "Gemini request failed after retries/fallbacks: "
            + " | ".join(errors[-3:])
            + ". Check internet, API key, Gemini model, and GEMINI_TIMEOUT."
        )

    @staticmethod
    def _safe_request_error(exc: requests.RequestException) -> str:
        response = getattr(exc, "response", None)
        if response is None:
            raw = str(exc).split("?key=")[0]
            if "NameResolutionError" in raw or "getaddrinfo failed" in raw:
                return "DNS lookup failed for generativelanguage.googleapis.com"
            return raw[:300]

        status = response.status_code
        try:
            payload = response.json()
            message = payload.get("error", {}).get("message", response.text)
        except ValueError:
            message = response.text

        return f"HTTP {status} - {message[:300]}"

    def _generate_with_openai_compatible(
        self,
        prompt: str,
        api_key_env: str,
        model_env: str,
        default_model: str,
        base_url: str | None,
        extra_headers: dict | None,
    ) -> str:
        api_key = os.getenv(api_key_env)
        if not api_key:
            raise MissingApiKeyError(f"Set {api_key_env} in your .env file.")

        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError("Install openai to use OpenAI or OpenRouter.") from exc

        client_kwargs = {"api_key": api_key}
        if base_url:
            client_kwargs["base_url"] = base_url
        if extra_headers:
            client_kwargs["default_headers"] = extra_headers

        client = OpenAI(**client_kwargs)
        response = client.chat.completions.create(
            model=os.getenv(model_env, default_model),
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a careful study assistant. Answer only from retrieved "
                        "document context. If context is insufficient, say so clearly."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.0,
        )
        return response.choices[0].message.content.strip()
