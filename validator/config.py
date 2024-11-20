"""
This file acts as a configuration file for the text2sql application.
- It defines the global paths for the application.
- It defines all the global variables that are going to be used from the text2sql component.
"""

import os
import importlib.resources


# Global paths
DATA_PATH = os.path.join(importlib.resources.files(__package__.split(".")[0]), "data")
LOGGING_PATH = os.path.join(importlib.resources.files(__package__.split(".")[0]), "logs")
os.makedirs(LOGGING_PATH, exist_ok=True)
os.makedirs(DATA_PATH, exist_ok=True)

# general paths
FOS_TAXONOMY_PATH = "fos_taxonomy_v0.1.2.json"

# ollama
OLLAMA_HOST = os.getenv("OLLAMA_HOST")
OLLAMA_PORT = os.getenv("OLLAMA_PORT")
OLLAMA_STORAGE=os.getenv("OLLAMA_STORAGE")

# qdrant
QDRANT_HOST = os.getenv("QDRANT_HOST")
QDRANT_PORT = os.getenv("QDRANT_PORT")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")