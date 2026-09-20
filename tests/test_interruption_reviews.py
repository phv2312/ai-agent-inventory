from unittest.mock import MagicMock
from pathlib import Path
from collections.abc import AsyncIterator

import pytest
from sqlalchemy.exc import IntegrityError

from agent.backend.db.models import ConversationORM
from agent.backend.db.session import create_engine, create_session_factory, init_db
from agent.backend.repos.pending_run import SQLPendingAgentRunRepository
from agent.core._agent.parser.core import Interruption, StreamParser


@pytest.mark.asyncio
async def test_core_emits_resumable_interruption() -> None:
    async def events() -> AsyncIterator[None]:
        if False:
            yield

    result = MagicMock()
    result.stream_events = events
    result.run_loop_exception = None
    result.to_state.return_value.to_string.return_value = "saved-state"
    from unittest.mock import patch

    from agent.core.tools import AgentInterruption

    item = AgentInterruption(
        id="call-1", agent="global_agent", tool_name="submit_agent_plan", arguments={}
    )
    result.interruptions = [MagicMock()]
    with patch.object(AgentInterruption, "from_approval_item", return_value=item):
        parser = StreamParser()
        parsed = [event async for event in parser.parse(result)]
    assert isinstance(parsed[-1], Interruption)
    assert parsed[-1].serialized_run_state == "saved-state"
    assert parsed[-1].interruptions == [item]
    assert not parser.last_state.completed


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "decision, feedback", [("approve", ""), ("revise", "Add risks"), ("cancel", "")]
)
async def test_review_survives_pending_deletion_and_rejects_duplicate(
    tmp_path: Path, decision: str, feedback: str
) -> None:
    engine = create_engine(f"sqlite+aiosqlite:///{tmp_path}/reviews.db")
    await init_db(engine)
    sessions = create_session_factory(engine)
    async with sessions() as session:
        session.add(ConversationORM(id="conversation", title="Review"))
        await session.flush()
        repo = SQLPendingAgentRunRepository(session)
        pending = await repo.create(
            conversation_id="conversation",
            user_message_id="message",
            state_json="state",
            request_snapshot={},
            interruptions=[{"id": "call-1"}],
        )
        await session.commit()
    async with sessions() as session:
        repo = SQLPendingAgentRunRepository(session)
        restored = await repo.get("conversation")
        assert restored is not None
        assert restored.interruptions == [{"id": "call-1"}]
        await repo.record_response(pending, decision, feedback)
        await session.commit()
    async with sessions() as session:
        repo = SQLPendingAgentRunRepository(session)
        with pytest.raises(IntegrityError):
            await repo.record_response(pending, "approve", "")
        await session.rollback()
        revised = await repo.replace(
            conversation_id="conversation",
            version=1,
            state_json="new",
            interruptions=[{"id": "call-2"}],
        )
        assert revised is not None
        assert revised.version == 2
        assert not await repo.delete("conversation", 1)
        assert await repo.delete("conversation", 2)
        await session.commit()
    async with sessions() as session:
        repo = SQLPendingAgentRunRepository(session)
        assert await repo.get("conversation") is None
        history = await repo.history("conversation")
        assert len(history) == 1
        assert history[0]["feedback"] == feedback
        assert history[0]["decision"] == decision
        assert history[0]["interruptions"] == [{"id": "call-1"}]
    await engine.dispose()
