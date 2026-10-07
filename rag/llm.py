import os
from pathlib import Path

import httpx

from dotenv import load_dotenv
from openai import OpenAI

try:
    from .query import get_collection, search_documents
except ImportError:
    from query import get_collection, search_documents


# ============================================================
# 1. CONFIGURATION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")

OPENROUTER_API_KEY = os.getenv(
    "OPENROUTER_API_KEY"
)

if not OPENROUTER_API_KEY:
    raise ValueError(
        "OPENROUTER_API_KEY is missing from .env"
    )


# ============================================================
# 2. OPENROUTER CLIENT
# ============================================================

OPENROUTER_MODEL = os.getenv(
    "OPENROUTER_MODEL",
    "openrouter/free",
)
OPENROUTER_BASE_URL = os.getenv(
    "OPENROUTER_BASE_URL",
    "https://openrouter.ai/api/v1",
)
REQUEST_TIMEOUT = float(os.getenv("OPENROUTER_TIMEOUT", "90"))
VERIFY_SSL = os.getenv("VERIFY_SSL", "true").lower() not in {
    "0",
    "false",
    "no",
}
MAX_CONTEXT_CHARS = int(os.getenv("RAG_MAX_CONTEXT_CHARS", "12000"))

http_client = httpx.Client(
    verify=VERIFY_SSL,
    timeout=REQUEST_TIMEOUT,
)

client = OpenAI(
    base_url=OPENROUTER_BASE_URL,
    api_key=OPENROUTER_API_KEY,
    http_client=http_client,
    max_retries=2,
)


# ============================================================
# 3. SEND RETRIEVED CONTEXT TO LLM
# ============================================================

def ask_llm(question: str, results: dict) -> str:

    # Get the actual retrieved chunks
    documents = (results.get("documents") or [[]])[0]
    metadatas = (results.get("metadatas") or [[]])[0]

    if not documents:
        return (
            "I could not find relevant information in the provided policy "
            "documents."
        )

    # Combine the top-k chunks
    context_parts = []
    context_length = 0
    for index, document in enumerate(documents, start=1):
        source = metadatas[index - 1].get("file_name", "unknown") if index <= len(metadatas) else "unknown"
        chunk = f"--- Retrieved Chunk {index} ({source}) ---\n{document}"
        remaining = MAX_CONTEXT_CHARS - context_length
        if remaining <= 0:
            break
        context_parts.append(chunk[:remaining])
        context_length += len(chunk)
    context = "\n\n".join(context_parts)

    # --------------------------------------------------------
    # Prompt
    # --------------------------------------------------------

    prompt = f"""
You are Prodapt's customer support assistant.

Answer the customer's question directly and clearly using only the
retrieved policy excerpts below.

Strict response rules:
- Return only the final customer-facing answer.
- Answer exactly what the customer asked; do not provide a general policy summary.
- Do not mention retrieved chunks, context, prompts, embeddings, or models.
- Do not copy large sections of the policy.
- Include only facts needed to answer the question. Do not add adjacent details
    such as spend caps, exceptions, or country lists unless the question asks for them.
- Do not invent facts. If the documents do not answer the question, say so.
- Keep the answer concise, preferably under 120 words.
- Use short paragraphs or bullets only when they improve clarity.

POLICY EXCERPTS:
{context}

CUSTOMER QUESTION:
{question}

FINAL CUSTOMER ANSWER:
"""

    # --------------------------------------------------------
    # OpenRouter request with graceful fallback
    # --------------------------------------------------------
    try:
        response = client.chat.completions.create(
            model=OPENROUTER_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a helpful telecom "
                        "customer support assistant."
                    )
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.4,
            max_tokens=int(os.getenv("OPENROUTER_MAX_TOKENS", "1200")),
        )
        content = response.choices[0].message.content
        if content:
            if response.choices[0].finish_reason == "length":
                content += "\n\n[The model reached its response limit. Increase OPENROUTER_MAX_TOKENS to continue.]"
            return content.strip()
    except Exception as exc:
        pass

    # If OpenRouter is rate-limited (e.g. 429 daily free limit) or unreachable,
    # return the highest-scoring retrieved document chunk directly:
    return documents[0].strip()


# ============================================================
# 4. COMPLETE RAG PIPELINE
# ============================================================

def rag_query(collection, question: str, top_k: int = 5):
    if not question.strip():
        raise ValueError("question must not be empty")
    if top_k < 1:
        raise ValueError("top_k must be at least 1")

    # --------------------------------------------------------
    # STEP 1: Retrieve documents
    # --------------------------------------------------------

    results = search_documents(
        collection,
        question,
        top_k=top_k
    )

    # --------------------------------------------------------
    # STEP 2: Send retrieved documents to LLM
    # --------------------------------------------------------

    answer = ask_llm(
        question,
        results
    )

    return answer, results


# ============================================================
# 5. MAIN
# ============================================================

if __name__ == "__main__":

    # --------------------------------------------------------
    # Connect to existing ChromaDB
    # --------------------------------------------------------

    collection = get_collection()

    print("\n==========================================")
    print("          TELECOM RAG AGENT")
    print("==========================================")

    print(
        f"\nVectors in ChromaDB: "
        f"{collection.count()}"
    )

    # --------------------------------------------------------
    # Ask questions continuously
    # --------------------------------------------------------

    while True:

        question = input(
            "\nCustomer question "
            "(type 'exit' to stop): "
        ).strip()

        if question.lower() == "exit":
            print("\nExiting...")
            break

        if not question:
            print("Please enter a question.")
            continue

        try:

            # =================================================
            # RETRIEVAL + LLM
            # =================================================

            answer, _ = rag_query(
                collection,
                question,
                top_k=3
            )

            print("\n==========================================")
            print("              CUSTOMER RESPONSE")
            print("==========================================")

            print(answer)

        except Exception as e:

            print("\n==========================================")
            print("                  ERROR")
            print("==========================================")

            print(e)