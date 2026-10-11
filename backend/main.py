from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from backend.arena_ai import ArenaAI
from backend.arena_api import router as arena_router
from backend.comfyui import ComfyUIClient
from backend.config import Settings
from backend.errors import ServiceError
from backend.models import ChooseRequest, GenerateRequest, ImageResult, QuestSession
from backend.sessions import SessionService


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    application = FastAPI(
        title="AI技术策划试炼场",
        version="2.0.0",
        description="异步 DeepSeek 动态任务与复盘、ComfyUI 海报；保留任务分支 API。",
    )
    sessions = SessionService(settings)
    images = ComfyUIClient(settings)
    application.state.sessions = sessions
    application.state.images = images
    application.state.settings = settings
    application.state.arena_ai = ArenaAI(settings)
    application.include_router(arena_router)

    @application.exception_handler(ServiceError)
    async def service_error_handler(request: Request, exc: ServiceError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": str(exc)})

    @application.get("/health")
    async def health() -> dict:
        return {
            "status": "ok",
            "deepseek_configured": bool(settings.deepseek_api_key.get_secret_value()),
            "deepseek_model": settings.deepseek_model,
            "deepseek_timeout": settings.deepseek_timeout,
            "comfyui_timeout": settings.comfyui_timeout,
            "comfyui_workflow_configured": settings.workflow_path.is_file(),
            "max_depth": settings.max_depth,
            "max_nodes": settings.max_nodes,
        }

    @application.post("/api/quests/generate", response_model=QuestSession)
    async def generate(request: GenerateRequest) -> QuestSession:
        return await sessions.create(request)

    @application.get("/api/sessions/{session_id}", response_model=QuestSession)
    async def get_session(session_id: str) -> QuestSession:
        return sessions.get(session_id)

    @application.post("/api/sessions/{session_id}/choose", response_model=QuestSession)
    async def choose(session_id: str, request: ChooseRequest) -> QuestSession:
        return await sessions.choose(session_id, request)

    @application.post(
        "/api/sessions/{session_id}/nodes/{node_id}/reward-image", response_model=ImageResult
    )
    async def reward_image(session_id: str, node_id: str) -> ImageResult:
        node = sessions.node(session_id, node_id)
        return await images.generate(node.quest.rewards)

    return application


app = create_app()
