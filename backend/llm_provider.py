"""
Single shared llama.cpp model for the whole process.

Chat replies, event reactions and memory extraction all use this one
instance, so the 3B model is loaded once. A RAM prompt cache keeps the KV
state of recent prompts, so switching between the chat prompt and the
extraction prompt does not force the long chat system prompt to be
re-evaluated on every turn.
"""
import logging
import threading

import config

log = logging.getLogger(__name__)

_llm = None
_lock = threading.RLock()


def _compact_ram_cache(capacity_bytes):
    from llama_cpp import LlamaRAMCache

    class CompactRAMCache(LlamaRAMCache):
        """
        llama-cpp-python's RAM cache stores a copy of the logits for every
        prompt token (~0.6 GB for a 1000-token prompt with Qwen's 152k vocab)
        but only counts the KV state against its capacity, so it grows without
        bound. Only the last row is needed to continue generating (load_state
        broadcasts it), so keep just that row and count it.
        """

        def __setitem__(self, key, value):
            if value.scores is not None and len(value.scores) > 1:
                value.scores = value.scores[-1:].copy()
            super().__setitem__(key, value)

        @property
        def cache_size(self):
            return sum(s.llama_state_size + (s.scores.nbytes if s.scores is not None else 0)
                       for s in self.cache_state.values())

    return CompactRAMCache(capacity_bytes=capacity_bytes)


def get_llm():
    global _llm
    with _lock:
        if _llm is None:
            from llama_cpp import Llama

            path = config.LLM_MODEL_PATH
            if not path.is_file():
                raise FileNotFoundError(
                    f"LLM model not found at {path}. Run `python download_models.py` "
                    "or set TOM_LLM_MODEL."
                )
            log.info("Loading LLM %s (n_ctx=%d, gpu_layers=%d)",
                     path.name, config.LLM_CONTEXT, config.LLM_GPU_LAYERS)
            _llm = Llama(
                str(path),
                n_ctx=config.LLM_CONTEXT,
                n_gpu_layers=config.LLM_GPU_LAYERS,
                verbose=False,
            )
            if config.LLM_PROMPT_CACHE_MB > 0:
                _llm.set_cache(_compact_ram_cache(config.LLM_PROMPT_CACHE_MB << 20))
        return _llm


def chat(**kwargs):
    """Thread-safe create_chat_completion on the shared model."""
    with _lock:
        return get_llm().create_chat_completion(**kwargs)


def set_llm(llm):
    """Inject a model (tests)."""
    global _llm
    with _lock:
        _llm = llm


def close():
    """Free the model before interpreter shutdown (avoids a noisy __del__ traceback)."""
    global _llm
    with _lock:
        if _llm is not None and hasattr(_llm, "close"):
            _llm.close()
        _llm = None
