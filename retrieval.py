import re

from config import chunk_collection, embed_texts, llm



def router(user_input):
	match = re.search(r"\d{5,}", user_input)  # Search for a sequence of 5 or more digits in the user input
	if match:
		found_number = match.group()
		got = chunk_collection.get(where_document={"$contains": found_number})
		return got["documents"]
	return retrieve(user_input, k=5)

def retrieve(user_input, k=5):
	# Embed the user input
	user_input_vector = embed_texts([user_input])[0] # only one input, so take the first embedding

	# query the chunk_collection for the top k most similar documents
	results = chunk_collection.query(
		query_embeddings=[user_input_vector],
		n_results=k,
		include=["documents"],
	)

	# return the top k documents
	return results["documents"][0]


def answer_question(user_input):
	retrieved_value = router(user_input)
	if not retrieved_value:
		return "No such code, double-check or clarify your question."
	dedup_list = list(dict.fromkeys(retrieved_value))
	context = "\n\n".join(dedup_list)
	answer_prompt = f"""You are a helpful answer retrieval assistant. 
	You are to answer the user's question according to these instructions: 
	Answer only from the retrieved context, not your training knowledge.
	If the user gives a situational context with specific facts, lead with reasoning and apply the retrieved rules to those facts. If you can only answer part of the question with the retrieved context, state what you can and acknowledge the missing information;
	If it's a direct lookup, lead with the answer and just state what the document says; never invent rules or specs that aren't grounded. 
	Do not fabricate an answer. No plausible sounding answer that you think the user wants to hear. If it's not in the context, say so. Tell the user that you are unable to answer the question with the available information.
	 When answering, be concise and precise. Write in connected prose, not bullet points unless necessary for the matter. Answer the user question between the below markers based on the context provided between the markers below.

<document>
{context}
</document>
	
<question>
{user_input}
</question>"""

	completion = llm.new_completion()
	completion.with_message(answer_prompt)
	response = completion.execute()
	return response.text


if __name__ == "__main__":
	q1 = "when doing a mixer weight replacement, what is the torque spec for the 24mm bolts?"
	
	
	print("=== EIP answer ===")
	print(answer_question(q1))
	


	