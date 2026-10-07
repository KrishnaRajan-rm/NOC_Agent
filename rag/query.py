import os
import urllib3
from pathlib import Path

import chromadb
import requests
from dotenv import load_dotenv


# --------------------------------------------------
# 1. Configuration
# --------------------------------------------------

urllib3.disable_warnings(
    urllib3.exceptions.InsecureRequestWarning
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")
load_dotenv()

HF_TOKEN = os.getenv("HF_TOKEN")

if not HF_TOKEN:
    raise ValueError(
        "HF_TOKEN is missing from .env"
    )


# --------------------------------------------------
# 2. ChromaDB path
# --------------------------------------------------

CHROMA_DIR = (
    Path(__file__).resolve().parent
    / "chroma_db"
)


# --------------------------------------------------
# 3. Create query embedding
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

    if response.status_code != 200:
        raise RuntimeError(
            f"Hugging Face API error "
            f"{response.status_code}:\n"
            f"{response.text}"
        )

    return response.json()


# --------------------------------------------------
# 4. Connect to ChromaDB
# --------------------------------------------------

def get_collection():

    client = chromadb.PersistentClient(
        path=str(CHROMA_DIR)
    )

    collection = client.get_collection(
        name="telecom_documents"
    )

    return collection


# --------------------------------------------------
# 5. Search ChromaDB
# --------------------------------------------------

def search_documents(
    collection,
    question,
    top_k=5
):

    query_embedding = create_embedding(
        question
    )

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k
    )

    return results


# --------------------------------------------------
# 6. Display results
# --------------------------------------------------

def display_results(results):

    documents = results["documents"][0]
    distances = results["distances"][0]
    metadatas = results["metadatas"][0]

    print("\n================================")
    print("RETRIEVED DOCUMENTS")
    print("================================")

    for i, document in enumerate(
        documents,
        start=1
    ):

        print(f"\nResult {i}")
        print("------------------------")

        print(
            "Distance:",
            distances[i - 1]
        )

        print(
            "Source:",
            metadatas[i - 1].get(
                "file_name",
                "unknown"
            )
        )

        print("\nContent:")
        print(document)


# --------------------------------------------------
# 7. Main
# --------------------------------------------------

if __name__ == "__main__":

    collection = get_collection()

    print(
        "Vectors in ChromaDB:",
        collection.count()
    )

    while True:

        question = input(
            "\nCustomer question "
            "(type 'exit' to stop): "
        ).strip()

        if question.lower() == "exit":
            break

        if not question:
            continue

        results = search_documents(
            collection,
            question,
            top_k=5
        )

        display_results(results)