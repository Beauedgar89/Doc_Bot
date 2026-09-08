from config import chunk_collection
result = chunk_collection.get(where={"doc_id": "maintenance/My_test_doc.docx"})
print(len(result["ids"]), "chunks")
print(result["ids"])