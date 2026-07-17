from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    # App
    APP_ENV: str = "development"
    SECRET_KEY: str = "dev-secret-change-me"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080  # 7 days
    ALGORITHM: str = "HS256"

    # Database
    MONGODB_URL: str = "mongodb://localhost:27017"
    DATABASE_NAME: str = "legallens"

    # Storage
    STORAGE_PATH: str = "./storage/pdfs"

    # Azure OpenAI
    AZURE_OPENAI_API_KEY: str = ""
    AZURE_OPENAI_ENDPOINT: str = ""  # Base URL only: https://<resource>.cognitiveservices.azure.com/
    AZURE_OPENAI_API_VERSION: str = "2024-12-01-preview"
    AZURE_OPENAI_DEPLOYMENT_NAME: str = "gpt-4.1"
    AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME: str = "text-embedding-ada-002"

    # Retrieval
    DEFAULT_TOP_K: int = 5
    MAX_TOP_K: int = 20

    # CORS
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000,https://ai-legal-lens-1.onrender.com"

    @property
    def allowed_origins_list(self) -> List[str]:
        origins = [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]
        always_allowed = [
            "https://ai-legal-lens-1.onrender.com",
            "https://ai-legal-lens.onrender.com",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:3001",
            "http://127.0.0.1:3001"
        ]
        for url in always_allowed:
            if url not in origins:
                origins.append(url)
        return origins

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()

# Ensure storage directory exists
os.makedirs(settings.STORAGE_PATH, exist_ok=True)
