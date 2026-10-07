from pathlib import Path

from llama_index.core import SimpleDirectoryReader


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
# 3. Test
# --------------------------------------------------

if __name__ == "__main__":

    documents = load_documents()

    print(f"\nLoaded {len(documents)} documents.\n")

    for i, document in enumerate(documents, start=1):

        print(f"Document {i}")
        print("------------------------")

        print(
            "File:",
            document.metadata.get("file_name")
        )

        print(
            "Characters:",
            len(document.text)
        )

        print(
            "Preview:",
            document.text[:200]
        )

        print()