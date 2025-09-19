from pydantic_settings import BaseSettings
from pydantic import field_validator

class Settings(BaseSettings):
    MYSQL_HOST: str
    MYSQL_PORT: str
    MYSQL_USER: str
    MYSQL_PASSWORD: str
    MYSQL_DB: str

    @property
    def DATABASE_URL(self) -> str:
        return f"mysql+aiomysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DB}"

    class Config: 
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "allow"

settings = Settings()
