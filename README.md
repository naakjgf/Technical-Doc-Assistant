# Technical Documentation Assistant

An AI-powered chat application that allows developers to have a natural language conversation with a codebase. This project leverages a Retrieval-Augmented Generation (RAG) pipeline to provide context-aware answers about any public GitHub repository.

## Key Features

-   **GitHub Repository Ingestion**: Ingests and processes entire public code repositories via their URL.
-   **Vector Embeddings**: Chunks code and documentation into segments and creates vector embeddings using OpenAI's `text-embedding-ada-002` model.
-   **RAG Pipeline**: Uses Pinecone as a vector database to retrieve the most relevant code chunks and a GPT model (`gpt-3.5-turbo`) to generate context-aware answers.
-   **Redis Caching**: Implements a Redis caching layer to provide near-instant responses for repeated queries and prevent redundant API calls, reducing both latency and cost.
-   **Interactive Chat UI**: A clean, responsive chat interface built with React that provides a seamless user experience, including real-time status updates during indexing.
-   **Fully Containerized**: The entire application stack (FastAPI, React, Redis) is containerized using Docker and managed with Docker Compose for easy and consistent local development.

## Tech Stack

-   **Backend**: Python, FastAPI
-   **Frontend**: React, JavaScript, CSS, Axios
-   **AI & Data**: OpenAI API, Pinecone, LangChain (for text splitting)
-   **Infrastructure & DevOps**: Docker, Docker Compose, Redis
-   **Deployment**: Vercel (Frontend), Railway (Backend)

## Local Development Setup

To run this project on your local machine, follow these steps.

### Prerequisites

-   Git
-   Python 3.11+
-   Node.js and npm
-   Docker and Docker Compose

### 1. Clone the Repository

```bash
git clone https://github.com/naakjgf/Technical-Doc-Assistant.git
cd Technical-Doc-Assistant/technical-doc-assistant
