from config import CHUNK_TOKEN_OVERLAP, EMBED_ENCODING, chunk_collection, converter, CHUNK_TOKEN_CAP, embed_texts
import tiktoken
import os
import re




def process_one_file(file_path, folder):

	# Derive stable identity from the original filename
	filename = os.path.basename(file_path)  # use basename to get the file name everytime no matter the full path
	doc_id   = folder + "/" + filename                         # keep extension → unique id
	title    = os.path.splitext(filename)[0]   # drop extension → human-readable

	# Step 1: extract structure-preserving Markdown
	text = extract_text(file_path)


	# Step 2: chunk the extracted Markdown
	chunks = chunk_text_from_md(text, doc_id, title)
	
	# Step 3: embed + store the chunks in chunk_collection
	try:
		documents = [chunk["text"] for chunk in chunks]
		embeddings = embed_texts(documents)
	except Exception as e:
		print(f"Error embedding or preparing chunks for storage: {e} Please check the document content and try again.")
		return {"status": "embedding_error", "doc_id": doc_id, "title": title, "num_chunks": len(chunks)}
	ids = [f"{doc_id}_{i}" for i, chunk in enumerate(chunks)]
	metadatas = [{"folder": folder, "title": chunk["title"], "trail": trail_build(chunk["trail"]), "doc_id": chunk["doc_id"]} for chunk in chunks]
	
		

	# Step 4: delete any existing chunks for this document
	try:
		chunk_collection.delete(where={"doc_id": doc_id})
	except Exception as e:
		print(f"Error deleting existing chunks for document {doc_id}: {e} the existing version is still intact; safe to retry.")
		return {"status": "deletion_error", "doc_id": doc_id, "title": title, "num_chunks": len(chunks)}


	# Step 5: add the new chunks to the collection
	try:
		chunk_collection.add(
				ids=ids,
				embeddings=embeddings,
				documents=documents,
				metadatas=metadatas,
			)
	except Exception as e:
		print(f"Error adding chunks to the collection: {e} document file is now empty. Try again and alert Admin if the issue persists.")
		return {"status": "storage_error", "doc_id": doc_id, "title": title, "num_chunks": len(chunks)}
	
	
	return {"status": "stored", "doc_id": doc_id, "title": title, "num_chunks": len(chunks)}



# Call the appropriate function based on the file extension

def extract_text(file_path):
	allowed_extensions = ["pdf", "docx", "md", "DOC"]
	extension = file_path.split(".")[-1].lower()

	if extension in allowed_extensions:
		if extension == "md":
			return read_markdown_file(file_path)
		else:
			return extract_markdown(file_path)
	else:
		raise ValueError(f"Unsupported file type: {extension}")

def extract_markdown(file_path):
	result = converter.convert(file_path)
	return result.document.export_to_markdown()

def read_markdown_file(file_path):
	# 'r' opens the file for reading
	# encoding='utf-8' ensures special characters don't cause errors
	with open(file_path, 'r', encoding='utf-8') as file:
		return file.read()

# FIlter out chunks that are empty or contain only whitespace, TOC leader dots, or image markers.
def is_junk(text):
	stripped = text.strip()                    # 1. cleaned string
	stripped = stripped.replace("<!-- image -->", "")
	if re.search(r"\.{5,}", stripped):
		return True   
	stripped = re.sub(r"\.{5,}", "", stripped)        # remove TOC leader dots
	stripped = stripped.strip()                # tidy up whitespace left behind
	return stripped == "" 

# Build a chunked representation of the markdown text, preserving the heading hierarchy as a trail for each chunk.	
	
def chunk_text_from_md(markdown, doc_id, title):
	trail = []
	chunk_body = []
	chunks = []
	lines = markdown.split("\n")
	table_header =None

	for line in lines:
		n = len(line) - len(line.lstrip("#"))
		if line.startswith("|"):      ##------Table row detected---------
			if chunk_body:   # flush the current chunk before processing the table
				chunks.append({
					"title": title,
					"text": "\n".join(chunk_body),
					"trail": list(trail),
					"doc_id": doc_id,
					"kind": "prose"
				})
				chunk_body = []
			if table_header is None:	
				table_header = [cell.strip() for cell in line.split("|") if cell.strip()] # build the table header from the first row of the table
			elif all(c in "| -:" for c in line): 
				# This is the separator line, skip it
				continue
			else:
				cells = [cell.strip() for cell in line.split("|") if cell.strip()] # build the table row from the current line
				row_text = " | ".join(f"{header}: {cell}" for header, cell in zip(table_header, cells)) # build the row text with header: value pairs
				chunks.append({		#
					"title": title,
					"text": row_text,
					"trail": list(trail),
					"doc_id": doc_id,
					"kind": "table"
				})				##---------End of table row processing---------
		elif n > 0:			
			table_header = None
			if chunk_body:
				chunks.append({   # f
				"title": title,	
				"text": "\n".join(chunk_body),
				"trail": list(trail),
				"doc_id": doc_id,
				"kind": "prose"
				})
			trail = trail[:n-1]
			trail.append(line)
			chunk_body = []
		else:
			table_header = None
			chunk_body.append(line)  

	# Append the last chunk if any
	if chunk_body:
		chunks.append({
			"title": title,
			"text": "\n".join(chunk_body),
			"trail": list(trail),
			"doc_id": doc_id,
			"kind": "prose"
		})


	# filter chunk text
	chunks = [c for c in chunks if not is_junk(c["text"])]	


	# Expand chunks that exceed the token cap into smaller chunks, preserving the trail and title for each new chunk.
	expanded_chunks = []
	enc = tiktoken.get_encoding(EMBED_ENCODING) # Create a tiktoken encoder for the specified embedding encoding

	for chunk in chunks:  # if the chunk is prose, check its token count and split if necessary; otherwise, keep it as is.
		if chunk["kind"] == "prose":

			ids = enc.encode(chunk["text"])
			n_tokens = len(ids)

			if n_tokens > CHUNK_TOKEN_CAP:
				# Split the chunk into smaller chunks
				
				start = 0

				while start < n_tokens:
					window = ids[start:start + CHUNK_TOKEN_CAP]
					sub_text = enc.decode(window)
					expanded_chunks.append({
						"title": chunk["title"],
						"text": sub_text,
						"trail": list(chunk["trail"]),
						"doc_id": chunk["doc_id"],
						"kind": chunk["kind"]
					})
					start += CHUNK_TOKEN_CAP - CHUNK_TOKEN_OVERLAP

			else:
				expanded_chunks.append(chunk)
		else:
			expanded_chunks.append(chunk)

	for chunk in expanded_chunks:
		if chunk["kind"] == "table":
			continue
		crumb_trail = trail_build(chunk["trail"], chunk["title"])
		chunk["text"] = crumb_trail + "\n\n" + chunk["text"]
	return expanded_chunks


def trail_build(trail, title=None):
	breadcrumbs = [line.lstrip("#").strip() for line in trail]
	if title:
		breadcrumbs.insert(0, title)
	return " > ".join(breadcrumbs)




if __name__ == "__main__":
	# test_file = "Mixer_weight_replacement.docx"
	# result = process_one_file(test_file)
	# print(result)
	
	import sys
	if len(sys.argv) < 3:
		print("Usage: python ingest.py <file_path> <folder>")
		sys.exit(1)
	result = process_one_file(sys.argv[1], sys.argv[2])
	print(result)

	