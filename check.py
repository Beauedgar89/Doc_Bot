from config import chunk_collection
print(len(chunk_collection.get(where={"doc_id": "maintenance/ACD_v4_RA.pdf"})["ids"]))