# backend/main.py

import redis
import json
import os
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from dotenv import load_dotenv

# --- BEFORE (Fails in Docker) ---
# from .github_loader import load_github_repo
# from .embeddings import get_text_chunks, create_embeddings_and_upsert
# from .rag_engine import get_context, generate_answer

# --- AFTER (Works in Docker and Locally with our setup) ---
from github_loader import load_github_repo
from embeddings import get_text_chunks, create_embeddings_and_upsert
from rag_engine import get_context, generate_answer

from fastapi.middleware.cors import CORSMiddleware

# --- Configuration & Setup ---
load_dotenv() # This line loads the .env file

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

app = FastAPI(
    title="Technical Documentation Assistant API",
    description="API for indexing and querying code repositories.",
    version="1.0.0"
)

# --- NEW CORS MIDDLEWARE SETUP ---
# This is crucial, it tells the backend to accept requests from our frontend development server.
origins = [
    "https://technical-doc-assistant.vercel.app/",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"], # Allows all methods
    allow_headers=["*"], # Allows all headers
)

try:
    redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
    redis_client.ping()
    print("Successfully connected to Redis.")
except redis.exceptions.ConnectionError as e:
    print(f"Could not connect to Redis: {e}")
    redis_client = None

# --- Pydantic Models ---
class RepoIndexRequest(BaseModel):
    repo_url: str

class QueryRequest(BaseModel):
    repo_id: str
    question: str

class QueryResponse(BaseModel):
    answer: str
    source: str

# --- Caching Functions (Unchanged) ---
def get_cached_response(repo_id: str, question: str) -> str | None:
    if not redis_client: return None
    cache_key = f"query_cache:{repo_id}:{question}"
    cached = redis_client.get(cache_key)
    return json.loads(cached) if cached else None

def set_cached_response(repo_id: str, question: str, response: dict):
    if not redis_client: return
    cache_key = f"query_cache:{repo_id}:{question}"
    redis_client.setex(cache_key, 3600, json.dumps(response))

# --- Background Indexing Task ---
def process_and_embed_repo(repo_url: str, repo_id: str):
    """
    The full pipeline function that will run in the background.
    1. Clones repo
    2. Chunks documents
    3. Creates embeddings and upserts to Pinecone
    """
    print(f"Starting background indexing for {repo_id}...")
    try:
        documents = load_github_repo(repo_url)
        if not documents:
            print(f"No documents found or failed to load repo: {repo_id}")
            return
            
        chunks = get_text_chunks(documents)
        create_embeddings_and_upsert(chunks, repo_id)
        print(f"Successfully finished indexing for {repo_id}.")
    except Exception as e:
        print(f"An error occurred during background indexing for {repo_id}: {e}")
        
# --- NEW HELPER FUNCTION ---
def check_if_indexed(repo_id: str) -> bool:
    """Checks a simple flag in Redis to see if a repo is indexed."""
    if not redis_client:
        return False # If redis is down, better to re-index than to fail
    return redis_client.exists(f"repo_indexed:{repo_id}")

def mark_as_indexed(repo_id: str):
    """Sets a simple flag in Redis to mark a repo as indexed."""
    if redis_client:
        redis_client.set(f"repo_indexed:{repo_id}", "true")
        
# --- UPDATE THE BACKGROUND TASK ---
def process_and_embed_repo(repo_url: str, repo_id: str):
    """
    The full pipeline function that will run in the background.
    Now it marks the repo as indexed upon completion.
    """
    print(f"Starting background indexing for {repo_id}...")
    try:
        documents = load_github_repo(repo_url)
        if not documents:
            print(f"No documents found or failed to load repo: {repo_id}")
            return
            
        chunks = get_text_chunks(documents)
        create_embeddings_and_upsert(chunks, repo_id)
        
        # --- NEW STEP: Mark as complete in Redis ---
        mark_as_indexed(repo_id)
        print(f"Successfully finished indexing for {repo_id}. Marked as complete.")

    except Exception as e:
        print(f"An error occurred during background indexing for {repo_id}: {e}")

# --- API Endpoints ---
@app.get("/")
def read_root():
    return {"status": "API is running."}

@app.post("/index-repo")
async def index_repo(request: RepoIndexRequest, background_tasks: BackgroundTasks):
    """
    Triggers the asynchronous indexing of a GitHub repository.
    NOW CHECKS if the repo has already been indexed to save costs.
    """
    print(f"Received request to index URL: {request.repo_url}")
    repo_id = "_".join(request.repo_url.split('/')[-2:])
    
    if check_if_indexed(repo_id):
        print(f"Repo '{repo_id}' has already been indexed. Skipping.")
        return {"status": "success", "message": f"Repository '{repo_id}' has already been indexed.", "repo_id": repo_id}
    
    background_tasks.add_task(process_and_embed_repo, request.repo_url, repo_id)
    
    return {"status": "pending", "message": f"Repository '{repo_id}' is being indexed in the background.", "repo_id": repo_id}


@app.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """
    Endpoint to ask a question about an indexed repository.
    It checks the cache, then uses the RAG engine to generate a new answer.
    """
    # 1. Check cache first
    cached_answer = get_cached_response(request.repo_id, request.question)
    if cached_answer:
        print(f"Cache hit for repo '{request.repo_id}'!")
        return QueryResponse(answer=cached_answer['answer'], source="cache")

    print(f"Cache miss. Generating new response for repo '{request.repo_id}'.")
    
    # 2. Retrieve context from Pinecone
    context = get_context(request.question, request.repo_id)
    
    if not context:
        raise HTTPException(status_code=404, detail="Could not retrieve context for the given repository. Ensure it has been indexed correctly.")

    # 3. Generate an answer using the LLM
    generated_answer = generate_answer(request.question, context)
    
    # 4. Cache the new response
    response_data = {"answer": generated_answer}
    set_cached_response(request.repo_id, request.question, response_data)
    
    return QueryResponse(answer=generated_answer, source="generated")

@app.get("/index-status/{repo_id}")
async def get_index_status(repo_id: str):
    """Checks if the repository has finished indexing."""
    if check_if_indexed(repo_id):
        return {"status": "complete"}
    else:
        return {"status": "pending"}
