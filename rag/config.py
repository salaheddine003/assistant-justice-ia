from pathlib import Path

# Embedding
MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

# Index FAISS par défaut (Code civil)
PDF_FOLDER = Path("pdfs/Code civil")
INDEX_PATH = "faiss_index_code_civil"

# Chunking
CHUNK_SIZE = 1200   # inclut généralement un article complet
CHUNK_OVERLAP = 200 # évite de couper les articles en deux

# Requête
TOP_K = 10

# LLM local via Ollama. Peut etre remplace par OLLAMA_MODEL/GEMMA_MODEL.
GEMMA_MODEL = "gemma3:12b"

# Seuil de pertinence (distance L2 FAISS normalisée)
# < 0.8 = très pertinent | 0.8-1.5 = pertinent | 1.5-2.0 = acceptable | > 2.0 = hors-sujet
SCORE_THRESHOLD = 2.0
