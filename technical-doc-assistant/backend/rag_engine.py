# backend/rag_engine.py

import os
from pinecone import Pinecone
from openai import OpenAI

# --- Initialization ---
# Initialize clients from environment variables
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# --- Configuration ---
PINECONE_INDEX_NAME = "doc-assistant"
EMBEDDING_MODEL = "text-embedding-ada-002"
LLM_MODEL = "gpt-3.5-turbo"  # A powerful and cost-effective model for generation

def get_context(question: str, repo_id: str, top_k: int = 5) -> str:
    """
    Retrieves the most relevant document chunks from Pinecone to serve as context.
    """
    try:
        index = pc.Index(PINECONE_INDEX_NAME)
        
        # 1. Create an embedding for the user's question
        res = openai_client.embeddings.create(input=[question], model=EMBEDDING_MODEL)
        query_embedding = res.data[0].embedding
        
        # 2. Query Pinecone for similar vectors
        query_results = index.query(
            namespace=repo_id,
            vector=query_embedding,
            top_k=top_k,
            include_metadata=True
        )
        
        # 3. Format the retrieved context
        context = ""
        for match in query_results.matches:
            # Add a separator and source information for clarity
            context += f"--- Content from {match.metadata['source']} ---\n"
            context += match.metadata['text'] + "\n"
            
        return context
    except Exception as e:
        print(f"Error retrieving context from Pinecone: {e}")
        return "" # Return empty context on error

def generate_answer(question: str, context: str) -> str:
    """
    Uses the GPT model to generate an answer based on the provided context.
    """
    # This is the prompt engineering part. We instruct the model how to behave.
    system_prompt = (
        "You are a helpful assistant for software developers. "
        "Your task is to answer questions based *only* on the provided context from a codebase. "
        "Do not use any external knowledge. "
        "If the answer is not found in the context, state that clearly. "
        "Format code snippets using markdown."
    )
    
    user_prompt = f"Context:\n{context}\n\nQuestion: {question}\n\nAnswer:"
    
    try:
        response = openai_client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1 # A low temperature encourages more deterministic, factual answers
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error generating answer with OpenAI: {e}")
        return "Sorry, I encountered an error while generating the answer."