import asyncio
import time
from dataclasses import dataclass, field
from uuid import uuid4

from backend.config import Settings
from backend.errors import ServiceError
from backend.generator import DeepSeekGenerator, DemoGenerator, History, QuestGenerator
from backend.models import (
    ChooseRequest,
    GenerateRequest,
    QuestNode,
    QuestSession,
    apply_effects,
    validate_for_player,
)


@dataclass
class SessionEntry:
    session: QuestSession
    touched: float = field(default_factory=time.monotonic)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)


class SessionService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.generators: dict[str, QuestGenerator] = {
            "demo": DemoGenerator(),
            "deepseek": DeepSeekGenerator(settings),
        }
        self.entries: dict[str, SessionEntry] = {}
        self.pending = 0

    def _prune(self) -> None:
        now = time.monotonic()
        expired = [
            key
            for key, entry in self.entries.items()
            if now - entry.touched > self.settings.session_ttl_seconds and not entry.lock.locked()
        ]
        for key in expired:
            del self.entries[key]

    def _entry(self, session_id: str) -> SessionEntry:
        self._prune()
        entry = self.entries.get(session_id)
        if entry is None:
            raise ServiceError("推演会话不存在或已过期，请重新生成任务。", 404)
        entry.touched = time.monotonic()
        return entry

    def get(self, session_id: str) -> QuestSession:
        return self._entry(session_id).session.model_copy(deep=True)

    def node(self, session_id: str, node_id: str) -> QuestNode:
        session = self._entry(session_id).session
        node = next((node for node in session.nodes if node.id == node_id), None)
        if node is None:
            raise ServiceError("任务节点不存在，请重新选择节点。", 404)
        return node.model_copy(deep=True)

    async def create(self, request: GenerateRequest) -> QuestSession:
        self._prune()
        if len(self.entries) + self.pending >= self.settings.max_sessions:
            raise ServiceError("演示会话数量已达上限，请等待闲置会话回收或重启后端。", 429)
        self.pending += 1
        try:
            started = time.monotonic()
            quest = await self.generators[request.mode].generate(
                request.player_state, request.theme, []
            )
            validate_for_player(quest, request.player_state)
            root = QuestNode(
                id=uuid4().hex, depth=0, quest=quest, player_state=request.player_state
            )
            session = QuestSession(
                id=uuid4().hex,
                root_id=root.id,
                current_id=root.id,
                source=request.mode,
                theme=request.theme,
                nodes=[root],
                generation_ms=int((time.monotonic() - started) * 1000),
            )
            self.entries[session.id] = SessionEntry(session)
            return session.model_copy(deep=True)
        finally:
            self.pending -= 1

    @staticmethod
    def _history(session: QuestSession, parent: QuestNode) -> History:
        by_id = {node.id: node for node in session.nodes}
        history: History = []
        node = parent
        while node.parent_id:
            ancestor = by_id[node.parent_id]
            history.append(
                {
                    "quest": ancestor.quest.name,
                    "action": node.parent_action or "accept",
                    "outcome": node.incoming_outcome,
                }
            )
            node = ancestor
        return list(reversed(history))

    async def choose(self, session_id: str, request: ChooseRequest) -> QuestSession:
        entry = self._entry(session_id)
        async with entry.lock:
            session = entry.session
            parent = next((node for node in session.nodes if node.id == request.node_id), None)
            if parent is None:
                raise ServiceError("任务节点不存在，请重新选择节点。", 404)
            existing = next(
                (
                    node
                    for node in session.nodes
                    if node.parent_id == parent.id and node.parent_action == request.action
                ),
                None,
            )
            if existing:
                session.current_id = existing.id
                entry.touched = time.monotonic()
                return session.model_copy(deep=True)
            if (
                parent.depth >= self.settings.max_depth
                or len(session.nodes) >= self.settings.max_nodes
            ):
                raise ServiceError("此推演已达到深度或节点上限，请回溯已有节点或生成新任务。", 409)
            branch = next(
                branch for branch in parent.quest.branches if branch.action == request.action
            )
            state = apply_effects(parent.player_state, branch.effects)
            history = self._history(session, parent)
            history.append(
                {"quest": parent.quest.name, "action": request.action, "outcome": branch.outcome}
            )
            started = time.monotonic()
            quest = await self.generators[session.source].generate(state, session.theme, history)
            validate_for_player(quest, state)
            # No mutation until the new task has been generated and validated successfully.
            items = list(parent.earned_items)
            if request.action == "accept":
                items.append(parent.quest.rewards.item_name)
            child = QuestNode(
                id=uuid4().hex,
                parent_id=parent.id,
                parent_action=request.action,
                depth=parent.depth + 1,
                quest=quest,
                player_state=state,
                incoming_outcome=branch.outcome,
                earned_items=items,
            )
            session.nodes.append(child)
            session.current_id = child.id
            session.generation_ms = int((time.monotonic() - started) * 1000)
            entry.touched = time.monotonic()
            return session.model_copy(deep=True)
