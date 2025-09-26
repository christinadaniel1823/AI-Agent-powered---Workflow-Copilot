# Example rag.py content

from langchain.vectorstores import Chroma
from langchain.embeddings import SentenceTransformerEmbeddings
import json
import os

def build_vectorstore(json_path="data/protocols.json"):
    with open(json_path) as f:
        docs = json.load(f)

    # prepare embeddings
    embedder = SentenceTransformerEmbeddings(model_name="all-MiniLM-L6-v2")

    # create vectorstore
    texts = [d["text"] for d in docs]
    vectordb = Chroma.from_texts(texts, embedding=embedder)
    return vectordb

def make_retriever(vectordb, k=3):
    return vectordb.as_retriever(search_kwargs={"k": k})

# Optional mock generator
def mock_generate(query, docs, industry):
    steps = "\n".join([f"{i+1}. {d}" for i, d in enumerate(docs)])
    return f"Workflow for {industry}:\nQuery: {query}\nSteps:\n{steps}\n\nHUMAN REVIEW REQUIRED."
