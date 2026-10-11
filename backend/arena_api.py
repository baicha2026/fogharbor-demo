from fastapi import APIRouter, Request

from backend.poster import generate_achievement_poster
from game.contracts import ArenaReward, ArenaTask, PosterResult, ReviewRequest, TaskRequest

router = APIRouter(prefix="/api/arena", tags=["AI技术策划试炼场"])


@router.post("/task", response_model=ArenaTask)
async def task(request: TaskRequest, raw: Request) -> dict:
    return await raw.app.state.arena_ai.task(request.hp_ratio, request.gold, request.mode)


@router.post("/review")
async def review(request: ReviewRequest, raw: Request) -> dict[str, str]:
    payload = request.model_dump()
    mode = payload.pop("mode")
    return {"review": await raw.app.state.arena_ai.review(payload, mode)}


@router.post("/poster", response_model=PosterResult)
async def poster(payload: ArenaReward, raw: Request) -> PosterResult:
    return await generate_achievement_poster(raw.app.state.images, payload)
