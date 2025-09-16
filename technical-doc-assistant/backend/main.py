# backend/main.py

import redis
import json
import os
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from dotenv import load_dotenv

from github_loader import load_github_repo
from embeddings import get_text_chunks, create_embeddings_and_upsert
from rag_engine import get_context, generate_answer

from fastapi.middleware.cors import CORSMiddleware

# --- Configuration & Setup ---
load_dotenv()

app = FastAPI(
    title="Technical Documentation Assistant API",
    description="API for indexing and querying code repositories.",
    version="1.0.0"
)

# --- CORS MIDDLEWARE SETUP ---
origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Production-Ready Redis Connection ---
redis_client = None
try:
    # PRIORITY 1: Look for individual Railway/production variables. This is the most reliable.
    redis_host = os.getenv("REDISHOST")
    redis_port = os.getenv("REDISPORT")
    redis_password = os.getenv("REDISPASSWORD")

    if redis_host and redis_port and redis_password:
        redis_client = redis.Redis(
            host=redis_host,
            port=int(redis_port),
            password=redis_password,
            decode_responses=True,
            ssl=True
        )
        print("Successfully connected to managed Redis using component variables.")
    
    # PRIORITY 2: Fallback to the full REDIS_URL if the above aren't present.
    elif os.getenv("REDIS_URL"):
        redis_client = redis.from_url(os.getenv("REDIS_URL"), decode_responses=True)
        print("Successfully connected to managed Redis using REDIS_URL.")
    
    # PRIORITY 3: Fallback for local development using docker-compose.
    else:
        local_redis_host = os.getenv("REDIS_HOST", "localhost")
        local_redis_port = int(os.getenv("REDIS_PORT", 6379))
        redis_client = redis.Redis(host=local_redis_host, port=local_redis_port, decode_responses=True)
        print("Successfully connected to local Redis.")

    ##redis_client.ping()

except redis.exceptions.ConnectionError as e:
    print(f"FATAL: Could not connect to Redis: {e}")
    redis_client = None
except Exception as e:
    print(f"An unexpected error occurred during Redis connection: {e}")
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

# --- Caching Functions ---
def get_cached_response(repo_id: str, question: str) -> str | None:
    if not redis_client: return None
    cache_key = f"query_cache:{repo_id}:{question}"
    cached = redis_client.get(cache_key)
    return json.loads(cached) if cached else None

def set_cached_response(repo_id: str, question: str, response: dict):
    if not redis_client: return
    cache_key = f"query_cache:{repo_id}:{question}"
    redis_client.setex(cache_key, 3600, json.dumps(response))

# --- Helper Functions for Indexing Status ---
def check_if_indexed(repo_id: str) -> bool:
    if not redis_client: return False
    return redis_client.exists(f"repo_indexed:{repo_id}")

def mark_as_indexed(repo_id: str):
    if redis_client:
        redis_client.set(f"repo_indexed:{repo_id}", "true")

# --- THIS IS THE ONE AND ONLY CORRECT VERSION of the background task ---
def process_and_embed_repo(repo_url: str, repo_id: str):
    """
    The full pipeline function that will run in the background.
    It now marks the repo as indexed upon successful completion.
    """
    print(f"Starting background indexing for {repo_id}...")
    try:
        documents = load_github_repo(repo_url)
        if not documents:
            print(f"No documents found or failed to load repo: {repo_id}")
            return
            
        chunks = get_text_chunks(documents)
        create_embeddings_and_upsert(chunks, repo_id)
        
        # Mark as complete in Redis upon success
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
    """
    print("--- /index-repo endpoint START ---", flush=True)
    print(f"Received raw request to index URL: {request.repo_url}", flush=True)
    repo_id = "_".join(request.repo_url.split('/')[-2:])
    print(f"Generated repo_id: {repo_id}", flush=True)
    
    print("Checking if repo is already indexed...", flush=True)
    if check_if_indexed(repo_id):
        print(f"Repo '{repo_id}' has already been indexed. Skipping.", flush=True)
        print("--- /index-repo endpoint END (Already Indexed) ---", flush=True)
        return {"status": "success", "message": f"Repository '{repo_id}' has already been indexed.", "repo_id": repo_id}
    
    print("Repo not indexed. Adding task to background.", flush=True)
    background_tasks.add_task(process_and_embed_repo, request.repo_url, repo_id)
    
    print("--- /index-repo endpoint END (Task Added) ---", flush=True)
    return {"status": "pending", "message": f"Repository '{repo_id}' is being indexed in the background.", "repo_id": repo_id}

@app.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """
    Asks a question about an indexed repository, using a cache to store answers.
    """
    cached_answer = get_cached_response(request.repo_id, request.question)
    if cached_answer:
        print(f"Cache hit for repo '{request.repo_id}'!")
        return QueryResponse(answer=cached_answer['answer'], source="cache")

    print(f"Cache miss. Generating new response for repo '{request.repo_id}'.")
    
    context = get_context(request.question, request.repo_id)
    if not context:
        raise HTTPException(status_code=404, detail="Could not retrieve context. Please ensure the repository is indexed.")

    generated_answer = generate_answer(request.question, context)
    
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
