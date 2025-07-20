import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    API_KEY: str = os.getenv("API_KEY")
    DATABASE_PATH: str = os.getenv("DATABASE_PATH", "data/words.db")
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "True").lower() == "true"
    AI_API_URL: str = os.getenv("AI_API_URL")
    AI_API_TIMEOUT: int = int(os.getenv("AI_API_TIMEOUT", "30"))
    TRANSLATION_API_URL: str = os.getenv("TRANSLATION_API_URL")
    TRANSLATION_API_TIMEOUT: int = int(os.getenv("TRANSLATION_API_TIMEOUT", "15"))
    TRANSLATION_API_KEY: str = os.getenv("TRANSLATION_API_KEY")
    
    # Dictionary file paths
    MORPHOLOGY_DICT_PATH: str = os.getenv("MORPHOLOGY_DICT_PATH", "data/DE_morph_dict.txt")
    NOUNS_CSV_PATH: str = os.getenv("NOUNS_CSV_PATH", "data/nouns.csv")  # NEW
    DICT_CACHE_DIR: str = os.getenv("DICT_CACHE_DIR", "data/cache")
    
    # Create data directory if it doesn't exist
    def __init__(self):
        os.makedirs(os.path.dirname(self.DATABASE_PATH), exist_ok=True)
        os.makedirs(self.DICT_CACHE_DIR, exist_ok=True)

settings = Settings()