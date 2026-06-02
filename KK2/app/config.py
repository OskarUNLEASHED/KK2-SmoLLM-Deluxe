from functools import lru_cache

from dotenv import load_dotenv
from pydantic import BaseModel


load_dotenv()


class Settings(BaseModel):
    model_name: str = "HuggingFaceTB/SmolLM2-360M-Instruct"
    max_new_tokens: int = 100
    do_sample: bool = False
    repetition_penalty: float = 1.2
    no_repeat_ngram_size: int = 3


@lru_cache
def get_settings() -> Settings:
    return Settings()
