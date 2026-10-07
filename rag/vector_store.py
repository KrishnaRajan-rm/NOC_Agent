import chromadb
from pathlib import Path

from llama_index.core import SimpleDirectoryReader
from llama_index.core.node_parser import SentenceSplitter


# --------------------------------------------------
# 1. Project paths
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DOCUMENT_DIR = (
    PROJECT_ROOT
    / "projectfiles"
    / "data"
    / "documents"
)

CHROMA_DIR = (
    Path(__file__).resolve().parent
    / "chroma_db"
)


# --------------------------------------------------
# 2. Load documents
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
# 3. Chunk documents
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
# 4. Create BGE embedding
# --------------------------------------------------

def create_embedding(text):

    import os
    import requests
    from dotenv import load_dotenv

    load_dotenv()

    HF_TOKEN = os.getenv("HF_TOKEN")

    if not HF_TOKEN:
        raise ValueError(
            "HF_TOKEN is missing from .env"
        )

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
# 5. Create ChromaDB
# --------------------------------------------------

def create_vector_store():

    client = chromadb.PersistentClient(
        path=str(CHROMA_DIR)
    )

    collection = client.get_or_create_collection(
        name="telecom_documents"
    )

    return collection


# --------------------------------------------------
# 6. Store chunks and embeddings
# --------------------------------------------------

def store_documents(collection, chunks):

    for i, chunk in enumerate(chunks):

        print(
            f"Embedding and storing "
            f"chunk {i + 1}/{len(chunks)}..."
        )

        embedding = create_embedding(
            chunk.text
        )

        collection.add(
            ids=[chunk.node_id],
            embeddings=[embedding],
            documents=[chunk.text],
            metadatas=[
                {
                    "file_name": chunk.metadata.get(
                        "file_name",
                        "unknown"
                    )
                }
            ]
        )

    print("\nAll chunks stored successfully.")


# --------------------------------------------------
# 7. Test
# --------------------------------------------------

if __name__ == "__main__":

    # Load
    documents = load_documents()

    print(
        f"\nDocuments loaded: {len(documents)}"
    )

    # Chunk
    chunks = chunk_documents(documents)

    print(
        f"Chunks created: {len(chunks)}"
    )

    # ChromaDB
    collection = create_vector_store()

    print(
        f"ChromaDB collection: "
        f"{collection.name}"
    )

    # Store
    store_documents(
        collection,
        chunks
    )

    # Verify
    print(
        "\nTotal vectors in ChromaDB:",
        collection.count()
    )