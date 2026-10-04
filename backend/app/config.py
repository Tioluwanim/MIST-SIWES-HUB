from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./dev.db"
    firebase_project_id: str = ""
    firebase_credentials_json: str = ""
    cors_origins: str = "http://localhost:3000"
    qr_ttl_seconds: int = 45
    late_after_minutes: int = 15
    default_radius_meters: int = 100
    max_gps_accuracy_meters: int = 150
    timezone: str = "Africa/Lagos"

    storage_backend: str = "local"
    upload_dir: str = "./uploads"
    max_upload_mb: int = 10
    s3_bucket: str = ""
    s3_region: str = ""
    s3_endpoint_url: str = ""

    seed_admin_email: str = "admin@example.com"
    seed_instructor_email: str = "instructor@example.com"
    seed_supervisor_email: str = "supervisor@example.com"

    @property
    def cors_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
