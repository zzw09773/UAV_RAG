import sys
import warnings
from typing import List
import httpx

# Global flag to control logging output
_QUIET_MODE = False

def set_quiet_mode(quiet: bool = True):
    """Enable or disable quiet mode globally."""
    global _QUIET_MODE
    _QUIET_MODE = quiet

def log(msg: str):
    """Simple, unified logging function. Respects global quiet mode."""
    if not _QUIET_MODE:
        print(f"[LOG] {msg}", file=sys.stderr, flush=True)

class LocalApiEmbeddings:
    """
    A wrapper for a local embedding API that mimics LangChain's Embeddings interface.
    It includes batching and retry logic.
    """
    def __init__(self, api_base: str, api_key: str, model_name: str = "nvidia/nv-embed-v2", batch_size: int = 8, verify_ssl: bool = False):
        self.api_base = api_base.rstrip('/')
        self.api_key = api_key
        self.model_name = model_name
        self.batch_size = batch_size
        
        if verify_ssl:
            verify_context = True
        else:
            warnings.warn(
                "SSL verification is disabled. This is insecure and should only be used for development.",
                UserWarning
            )
            verify_context = False

        # Configure a client with built-in retries for robustness.
        if verify_ssl:
            transport = httpx.HTTPTransport(retries=3)
        else:
            transport = httpx.HTTPTransport(retries=3, verify=False)
        timeout_config = httpx.Timeout(600.0, connect=30.0)
        self.client = httpx.Client(verify=verify_context, transport=transport, timeout=timeout_config, follow_redirects=True)

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embeds a list of documents, handling batching automatically."""
        all_embeddings = []
        num_texts = len(texts)
        log(f"Embedding {num_texts} documents in batches of {self.batch_size}...")
        
        for i in range(0, num_texts, self.batch_size):
            batch = texts[i:i + self.batch_size]
            num_batches = (num_texts + self.batch_size - 1) // self.batch_size
            log(f"Processing batch {i//self.batch_size + 1}/{num_batches}")
            try:
                batch_embeddings = self._embed_batch(batch)
                all_embeddings.extend(batch_embeddings)
            except httpx.HTTPStatusError as e:
                print(f"[ERROR] Batch failed with status {e.response.status_code}: {e.response.text}", file=sys.stderr)
                raise  # Re-raise the exception after logging
            except httpx.RequestError as e:
                print(f"[ERROR] Batch failed due to request error: {e}", file=sys.stderr)
                raise

        return all_embeddings

    def _embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Embeds a single batch of documents."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model_name,
            "input": texts,
            "encoding_format": "float"
        }
        
        log(f"Sending {len(texts)} texts to {self.api_base}/embeddings")
        response = self.client.post(f"{self.api_base}/embeddings", headers=headers, json=payload)
        response.raise_for_status()  # Will raise an exception for 4xx/5xx responses
        
        data = response.json()
        embeddings = [item["embedding"] for item in data["data"]]
        log(f"Successfully received {len(embeddings)} vectors.")
        return embeddings

    def embed_query(self, text: str) -> List[float]:
        """Embeds a single query."""
        return self.embed_documents([text])[0]
