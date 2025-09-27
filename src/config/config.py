from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Database credentials env
    MYSQL_HOST: str
    MYSQL_PORT: str
    MYSQL_USER: str
    MYSQL_PASSWORD: str
    MYSQL_DB: str
    ADMIN_GMAIL: str

    # JWT secrets env
    JWT_ACCESS_SECRET_KEY: str
    JWT_REFRESH_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE: int = 45
    REFRESH_TOKEN_EXPIRE: int = 60 * 3

    # Redis credentials env
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379


    @property
    def DATABASE_URL(self) -> str:
        return f"mysql+aiomysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DB}"

    class Config: 
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "allow"

settings = Settings()
