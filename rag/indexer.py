from pathlib import Path

from .config import CHUNK_OVERLAP, CHUNK_SIZE, INDEX_PATH, PDF_FOLDER
from .embeddings import get_embeddings


def build_index(pdf_folder=None, index_path=None, code_name: str | None = None):
    """
    Charge les PDFs, découpe en chunks article-aware,
    construit et sauvegarde l'index FAISS.
    code_name : nom du code juridique, stocké dans la metadata de chaque chunk.
    """
    from langchain_community.document_loaders import PyPDFLoader
    from langchain_community.vectorstores import FAISS
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    folder    = Path(pdf_folder) if pdf_folder else PDF_FOLDER
    idx_path  = index_path or INDEX_PATH
    pdf_files = sorted(folder.glob("*.pdf"))

    if not pdf_files:
        raise FileNotFoundError(f"Aucun PDF trouvé dans {folder}")

    print(f"[1/4] {len(pdf_files)} PDFs trouvés dans {folder}")

    docs = []
    for i, pdf in enumerate(pdf_files, 1):
        if i % 200 == 0:
            print(f"      Chargement … {i}/{len(pdf_files)}")
        try:
            loader = PyPDFLoader(str(pdf))
            pages  = loader.load()
            for page in pages:
                page.metadata["source_file"] = pdf.name
                if code_name:
                    page.metadata["code_name"] = code_name
            docs.extend(pages)
        except Exception as e:
            print(f"      ERREUR {pdf.name}: {e}")

    print(f"[2/4] {len(docs)} pages chargées")

    # Séparateurs respectant les frontières naturelles des articles
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\nArticle ", "\nArticle ", "\n\n", "\n", ". ", " ", ""],
        length_function=len,
    )
    chunks = splitter.split_documents(docs)
    print(f"[3/4] {len(chunks)} chunks créés (taille={CHUNK_SIZE}, overlap={CHUNK_OVERLAP})")

    embeddings  = get_embeddings()
    vectorstore = FAISS.from_documents(chunks, embeddings)
    vectorstore.save_local(idx_path)
    print(f"[4/4] Index FAISS sauvegardé → {idx_path}/")
    print("      Construction terminée ✓")
