"""
This file acts as a configuration file for the text2sql application.
- It defines the global paths for the application.
- It defines all the global variables that are going to be used from the text2sql component.
- It defines some global functions that set up some inits
"""

import os
# haystack has a poor support for langfuse. We will use the langfuse API directly.
from langfuse import Langfuse
from langfuse.api.resources.commons.errors.unauthorized_error import UnauthorizedError


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

# neo4j
NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USER")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")


def set_langfuse():
    try:
        langfuse = Langfuse() # no need to pass the host, port, public key, and secret key since they are already set in the config
        langfuse.auth_check()
    except UnauthorizedError:
        print(
            "Langfuse credentials incorrect. Please re-enter your Langfuse credentials in the pipeline settings."
        )
    except Exception as e:
        print(f"Langfuse error: {e} Please re-enter your Langfuse credentials in the pipeline settings.")
    return langfuse