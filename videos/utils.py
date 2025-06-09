from transformers import GPT2Tokenizer
from functools import lru_cache

@lru_cache(maxsize=1)
def get_tokenizer():
    return GPT2Tokenizer.from_pretrained("gpt2")
