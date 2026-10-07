import os
import urllib3
from pathlib import Path

import requests
from dotenv import load_dotenv

from llama_index.core import SimpleDirectoryReader
from llama_index.core.node_parser import SentenceSplitter


# --------------------------------------------------
# 1. Disable SSL warning
# --------------------------------------------------
# NOTE:
# verify=False is being used only for local development/testing.
# Do NOT use this approach in production.

urllib3.disable_warnings(
    urllib3.exceptions.InsecureRequestWarning
)


# --------------------------------------------------
# 2. Load environment variables
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")
load_dotenv()

HF_TOKEN = os.getenv("HF_TOKEN")

if not HF_TOKEN:
    raise ValueError(
        "HF_TOKEN is missing. "
        "Add HF_TOKEN to your .env file."
    )


# --------------------------------------------------
# 3. Find the documents folder
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DOCUMENT_DIR = (
    PROJECT_ROOT
    / "projectfiles"
    / "data"
    / "documents"
)


# --------------------------------------------------
# 4. Load documents
# --------------------------------------------------

def load_documents():

    if not DOCUMENT_DIR.is_dir():
        raise FileNotFoundError(
            f"Documents directory does not exist: "
            f"{DOCUMENT_DIR}"
        )

    documents = SimpleDirectoryReader(
        input_dir=str(DOCUMENT_DIR),
        recursive=True
    ).load_data()

    return documents


# --------------------------------------------------
# 5. Chunk documents
# --------------------------------------------------

def chunk_documents(documents):

    splitter = SentenceSplitter(
        chunk_size=512,
        chunk_overlap=50
    )

    chunks = splitter.get_nodes_from_documents(
        documents
    )

    return chunks


# --------------------------------------------------
# 6. Create BGE embedding using Hugging Face API
# --------------------------------------------------

def create_embedding(text):

    url = (
        "https://router.huggingface.co/"
        "hf-inference/models/"
        "BAAI/bge-small-en-v1.5"
        "/pipeline/feature-extraction"
    )

    headers = {
        "Authorization": f"Bearer {HF_TOKEN}",
        "Content-Type": "application/json"
    }

    payload = {
        "inputs": text,
        "options": {
            "wait_for_model": True
        }
    }

    response = requests.post(
        url,
        headers=headers,
        json=payload,
        timeout=120,
        verify=False
    )

    # --------------------------------------------------
    # Check API response
    # --------------------------------------------------

    if response.status_code != 200:

        raise RuntimeError(
            f"Hugging Face API error "
            f"{response.status_code}:\n"
            f"{response.text}"
        )

    result = response.json()

    if not result:

        raise RuntimeError(
            "Hugging Face returned an empty embedding."
        )

    return result


# --------------------------------------------------
# 7. Test
# --------------------------------------------------

if __name__ == "__main__":

    # Load documents
    documents = load_documents()

    # Create chunks
    chunks = chunk_documents(documents)

    print(f"\nDocuments: {len(documents)}")
    print(f"Chunks: {len(chunks)}")

    # --------------------------------------------------
    # Test only ONE chunk first
    # --------------------------------------------------

    first_chunk = chunks[0]

    print(
        "\nCreating embedding for first chunk..."
    )

    embedding = create_embedding(
        first_chunk.text
    )

    print(
        "\nEmbedding created successfully!"
    )

    print(
        "Embedding type:",
        type(embedding)
    )

    print(
        "Embedding dimensions:",
        len(embedding)
    )

    print(
        "First 10 values:",
        embedding[:10]
    )