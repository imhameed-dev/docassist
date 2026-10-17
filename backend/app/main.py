"""FastAPI application entry point."""

from typing import Annotated, Literal

from fastapi import Depends, FastAPI
from pydantic import BaseModel

from app import __version__
from app.config import Settings, get_settings

SettingsDep = Annotated[Settings, Depends(get_settings)]


class HealthResponse(BaseModel):
    """Response for the health check. Deliberately excludes secrets and database details."""

    status: Literal["ok"]
    app: str
    environment: str
    version: str


def create_app() -> FastAPI:
    app = FastAPI(title=get_settings().app_name, version=__version__)

    @app.get("/api/health", response_model=HealthResponse, tags=["system"])
    def health(settings: SettingsDep) -> HealthResponse:
        return HealthResponse(
            status="ok",
            app=settings.app_name,
            environment=settings.environment,
            version=__version__,
        )

    return app


app = create_app()
