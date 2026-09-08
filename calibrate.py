from ingest import extract_text, summarize, embed_summary

def cosine_similarity(a, b):
    dot = sum(x*y for x, y in zip(a, b))
    mag_a = sum(x*x for x in a) ** 0.5
    mag_b = sum(x*x for x in b) ** 0.5
    return dot / (mag_a * mag_b)


doc_paths = {
    "original": "original.docx",
    "version2": "version2.docx",
    "different": "different.docx",
}

vectors = {}
for name, path in doc_paths.items():
    text = extract_text(path)
    summary = summarize(text)
    vectors[name] = embed_summary(summary)


print("original ↔ version2 :", cosine_similarity(vectors["original"], vectors["version2"]))
print("original ↔ different:", cosine_similarity(vectors["original"], vectors["different"]))
print("version2 ↔ different:", cosine_similarity(vectors["version2"], vectors["different"]))