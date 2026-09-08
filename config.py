import os
# disable torch JIT compile (docling has no C++ compiler available)
os.environ["TORCHINDUCTOR_COMPILE_THREADS"] = "1"
os.environ["TORCH_COMPILE_DISABLE"] = "1"
import truststore
truststore.inject_into_ssl()
import dataikuapi
import chromadb
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
import time

pipeline_options = PdfPipelineOptions(do_ocr=False)

converter = DocumentConverter(
    format_options={
        InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
    }
)

from dotenv import load_dotenv

load_dotenv()

DSS_INSTANCE        = os.getenv("DSS_INSTANCE")
DSS_API_KEY         = os.getenv("DSS_API_KEY")
DSS_PROJECT_KEY     = os.getenv("DSS_PROJECT_KEY")
DSS_LLM_ID          = os.getenv("DSS_LLM_ID")
DSS_LLM_ID_EMBED = os.getenv("DSS_LLM_ID_EMBED")
EMBED_ENCODING = "cl100k_base"
CHUNK_TOKEN_CAP = 500
CHUNK_TOKEN_OVERLAP = 90

client = dataikuapi.DSSClient(DSS_INSTANCE, DSS_API_KEY)
project = client.get_project(DSS_PROJECT_KEY)
llm = project.get_llm(DSS_LLM_ID)
llm_embed = project.get_llm(DSS_LLM_ID_EMBED)

DOC_STORE_PATH = "./doc_store"
chroma_client = chromadb.PersistentClient(path="./chroma_db")
chunk_collection   = chroma_client.get_or_create_collection("doc_chunks", metadata={"hnsw:space": "cosine"})








def embed_texts(texts, batch_size=20, sleep_seconds=2):
	all_embeddings = []
	start = 0
	num_batches = (len(texts) + batch_size - 1) // batch_size
	while start < len(texts):
		print(f"Embedding batch {start // batch_size + 1} of {num_batches} ({len(all_embeddings)} chunks done)")
		batch = texts[start:start + batch_size]

		new_embeddings = llm_embed.new_embeddings()
		for text in batch:
			new_embeddings.add_text(text)
		batch_vectors = new_embeddings.execute().get_embeddings()

		all_embeddings.extend(batch_vectors)

		start += batch_size
		if start < len(texts):
			time.sleep(sleep_seconds)
	return all_embeddings