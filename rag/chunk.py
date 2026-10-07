from pathlib import Path

from llama_index.core import SimpleDirectoryReader
from llama_index.core.node_parser import SentenceSplitter


# --------------------------------------------------
# 1. Find the documents folder
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DOCUMENT_DIR = PROJECT_ROOT / "projectfiles" / "data" / "documents"


# --------------------------------------------------
# 2. Load documents
# --------------------------------------------------

def load_documents():

    if not DOCUMENT_DIR.is_dir():
        raise FileNotFoundError(
            f"Documents directory does not exist: {DOCUMENT_DIR}"
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
# 4. Test
# --------------------------------------------------

if __name__ == "__main__":

    documents = load_documents()

    chunks = chunk_documents(documents)

    print(f"\nLoaded {len(documents)} documents.")
    print(f"Created {len(chunks)} chunks.\n")

    for i, chunk in enumerate(chunks[:5], start=1):

        print(f"Chunk {i}")
        print("------------------------")

        print(
            "Chunk ID:",
            chunk.node_id
        )

        print(
            "Source:",
            chunk.metadata.get("file_name")
        )

        print(
            "Characters:",
            len(chunk.text)
        )

        print(
            "Content:",
            chunk.text[:500]
        )

        print()