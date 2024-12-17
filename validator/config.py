"""
This file acts as a configuration file for the text2sql application.
- It defines the global paths for the application.
- It defines all the global variables that are going to be used from the text2sql component.
"""

import os


# Global paths
DATA_PATH = "data" # the root workspace is "validator" because of the Dockerfile.
LOGGING_PATH = "logs" # the root workspace is "validator" because of the Dockerfile.
os.makedirs(LOGGING_PATH, exist_ok=True)
os.makedirs(DATA_PATH, exist_ok=True)

# haystack
SERPERDEV_API_KEY = os.getenv("SERPERDEV_API_KEY")

# haystack and langfuse
LANGFUSE_HOST= os.getenv("LANGFUSE_HOST")
LANGFUSE_PORT= os.getenv("LANGFUSE_PORT")
LANGFUSE_PUBLIC_KEY= os.getenv("LANGFUSE_PUBLIC_KEY")
LANGFUSE_SECRET_KEY= os.getenv("LANGFUSE_SECRET_KEY")
HAYSTACK_CONTENT_TRACING_ENABLED = os.getenv("HAYSTACK_CONTENT_TRACING_ENABLED")

# general paths
FOS_TAXONOMY_PATH = os.getenv("FOS_TAXONOMY_PATH")

# ollama
OLLAMA_HOST = os.getenv("OLLAMA_HOST")
OLLAMA_PORT = os.getenv("OLLAMA_PORT")
OLLAMA_STORAGE=os.getenv("OLLAMA_STORAGE")

# qdrant
QDRANT_HOST = os.getenv("QDRANT_HOST")
QDRANT_PORT = os.getenv("QDRANT_PORT")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")