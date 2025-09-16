# backend/embeddings.py

import os
from pinecone import Pinecone
from langchain.text_splitter import RecursiveCharacterTextSplitter
from openai import OpenAI
from dotenv import load_dotenv

# --- Initialization ---
load_dotenv() # Load environment variables from .env file

# Initialize OpenAI client
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# --- NEW PINECOME INITIALIZATION ---
# This is the updated, correct way to initialize the Pinecone client
# We create an instance of the Pinecone class
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))


# --- Configuration ---
PINECONE_INDEX_NAME = "doc-assistant" # Use the index name you created
EMBEDDING_MODEL = "text-embedding-ada-002"
PINECONE_BATCH_SIZE = 100 # Recommended batch size for upserting

# --- Core Functions ---
def get_text_chunks(documents: list) -> list:
    """Splits documents into smaller chunks for embedding."""
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len
    )
    
    chunks = []
    for doc in documents:
        split_chunks = text_splitter.create_documents(
            [doc['content']], 
            metadatas=[{"source": doc['source']}]
        )
        for chunk in split_chunks:
            chunks.append(chunk)
            
    print(f"Split {len(documents)} documents into {len(chunks)} chunks.")
    return chunks

def create_embeddings_and_upsert(chunks: list, repo_id: str):
    """
    Creates embeddings for text chunks and upserts them into the Pinecone index.
    Uses the repo_id as a Pinecone namespace to keep data separate.
    """
    if not chunks:
        print("No chunks to process.")
        return

    # <-- CHANGE: Get a handler for the index from our Pinecone instance
    index = pc.Index(PINECONE_INDEX_NAME)
    
    print(f"Preparing to upsert {len(chunks)} chunks into Pinecone namespace: {repo_id}")
    
    # Process in batches to stay within Pinecone's limits
    for i in range(0, len(chunks), PINECONE_BATCH_SIZE):
        batch_chunks = chunks[i:i + PINECONE_BATCH_SIZE]
        
        texts_to_embed = [chunk.page_content for chunk in batch_chunks]
        
        try:
            res = openai_client.embeddings.create(input=texts_to_embed, model=EMBEDDING_MODEL)
            embeddings = [record.embedding for record in res.data]
        except Exception as e:
            print(f"Error creating embeddings with OpenAI: {e}")
            continue

        vectors_to_upsert = []
        for j, chunk in enumerate(batch_chunks):
            vector = {
                "id": f"{repo_id}-{i+j}",
                "values": embeddings[j],
                "metadata": {
                    "text": chunk.page_content,
                    "source": chunk.metadata["source"]
                }
            }
            vectors_to_upsert.append(vector)
            
        try:
            index.upsert(vectors=vectors_to_upsert, namespace=repo_id)
            print(f"Successfully upserted batch {i // PINECONE_BATCH_SIZE + 1}")
        except Exception as e:
            print(f"Error upserting to Pinecone: {e}")

    print("Embedding and upsert process completed.")