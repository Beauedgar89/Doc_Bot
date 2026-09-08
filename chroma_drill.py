import chromadb

client = chromadb.Client()                      # in-memory, ephemeral
col = client.create_collection(
    name="drill",
    metadata={"hnsw:space": "cosine"}           # force cosine so 1-distance works
)

# Add three entries by hand: id + embedding, nothing fancy
col.add(
    ids=["doc_a", "doc_b", "doc_c"],
    embeddings=[
        [1.0, 0.0, 0.0],     # doc_a points straight along x
        [0.9, 0.1, 0.0],     # doc_b almost the same as doc_a
        [0.0, 1.0, 0.0],     # doc_c points a totally different way (along y)
    ],
)

# Now query with a vector that's basically doc_a
results = col.query(
    query_embeddings=[[1.0, 0.0, 0.0]],
    n_results=3,
)

print(results)