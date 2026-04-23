from __future__ import annotations

import argparse
import base64
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from packages.data_store.connect import sqlite_db
from packages.data_store.migrations import apply_pending_migrations
from packages.data_store.llm_agent_runtime import queries as runtime_queries
from packages.llm.shared.agent_runtime.hosted_tools import (
    openai_image_generation,
    openai_web_search_preview,
)
from packages.llm.shared.agent_runtime.litellm_executor import LiteLLMAgentExecutor
from packages.llm.shared.agent_runtime.loop import AgentRuntimeLoop
from packages.llm.shared.agent_runtime.models import AgentSpec
from packages.llm.shared.agent_runtime.registry import AgentRegistry
from packages.llm.shared.agent_runtime.tools import ToolRegistry
from packages.pipeline.logging_utils import configure_logging


DEFAULT_OPENAI_MODEL = "openai/gpt-5"


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for the interactive agent runtime REPL."""
    parser = argparse.ArgumentParser(
        description="Interactive REPL over the durable agent runtime.",
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        default=REPO_ROOT / "data" / "app" / "app.db",
        help="SQLite database path.",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_OPENAI_MODEL,
        help="OpenAI Responses model to use for the REPL.",
    )
    parser.add_argument(
        "--thread-id",
        default=None,
        help="Optional existing thread id to resume immediately.",
    )
    return parser.parse_args()


def build_agent_spec(model: str) -> AgentSpec:
    """Return the REPL assistant spec."""
    return AgentSpec(
        agent_id="agent_runtime_repl.v1",
        instructions=(
            "You are a useful assistant in an interactive REPL. "
            "Use hosted tools when needed. If you generate an image, also describe briefly what you made."
        ),
        default_provider="openai",
        default_model=model,
        local_tools=[],
        hosted_tools=[
            openai_web_search_preview(search_context_size="medium"),
            openai_image_generation(size="1024x1024", quality="medium"),
        ],
    )


def print_help() -> None:
    """Print the available REPL commands."""
    print("/help                    show commands")
    print("/threads                 list conversation and task threads")
    print("/new [title]             start a new conversation thread")
    print("/task <text>             create a one-shot task thread and run it")
    print("/resume <thread_id>      switch to an existing thread")
    print("/show                    show current thread")
    print("/quit                    exit")
    print("Anything else sends a user message on the current thread.")


def artifact_dir_for_thread(thread_id: str) -> Path:
    """Return the artifact directory for one REPL thread."""
    return REPO_ROOT / ".logs" / "agent_runtime_repl" / thread_id


def save_generated_images(
    *,
    items: list[object],
    artifacts_dir: Path,
) -> list[Path]:
    """Persist any hosted image-generation outputs from the thread items."""
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    saved: list[Path] = []
    for item in items:
        provider_payload = getattr(item, "provider_payload", None)
        provider_item_type = getattr(item, "provider_item_type", None)
        item_id = getattr(item, "item_id", None)
        if provider_item_type != "image_generation_call" or not isinstance(provider_payload, dict):
            continue
        image_b64 = provider_payload.get("result")
        if not isinstance(image_b64, str) or not image_b64.strip():
            continue
        format_name = provider_payload.get("format")
        suffix = f".{format_name}" if isinstance(format_name, str) and format_name else ".png"
        output_path = artifacts_dir / f"{item_id or 'image'}{suffix}"
        if output_path.exists():
            saved.append(output_path)
            continue
        output_path.write_bytes(base64.b64decode(image_b64))
        saved.append(output_path)
    return saved


def list_thread_rows(connection) -> None:
    """Print thread summaries."""
    rows = runtime_queries.list_threads(connection)
    if not rows:
        print("no threads")
        return
    for row in rows:
        print(
            f"{row.thread_id}  kind={row.thread_kind}  status={row.status}  "
            f"updated={row.updated_at.isoformat()}  title={row.title or '-'}"
        )


def print_current_thread(connection, thread_id: str | None) -> None:
    """Print the current thread summary."""
    if not thread_id:
        print("current_thread=-")
        return
    thread = runtime_queries.get_thread(connection, thread_id)
    if thread is None:
        print(f"current_thread={thread_id} (missing)")
        return
    print(
        f"current_thread={thread.thread_id} kind={thread.thread_kind} "
        f"status={thread.status} phase={thread.phase} title={thread.title or '-'}"
    )


def max_seen_seq(connection, thread_id: str) -> int:
    """Return the current maximum item sequence for one thread."""
    items = runtime_queries.list_items(connection, thread_id)
    return max((item.seq or 0) for item in items) if items else 0


def print_thread_history(
    *,
    connection,
    thread_id: str,
    max_messages: int = 12,
) -> int:
    """Print recent user/assistant transcript for one thread and return latest seq."""
    items = runtime_queries.list_items(connection, thread_id)
    latest_seq = max((item.seq or 0) for item in items) if items else 0
    transcript_items = [
        item
        for item in items
        if item.item_type == "message" and item.role in {"user", "assistant"} and item.content_text
    ]
    if not transcript_items:
        print("history: no user/assistant messages")
    else:
        print("history:")
        for item in transcript_items[-max_messages:]:
            role = "user" if item.role == "user" else "assistant"
            print(f"{role}> {item.content_text}")
    artifact_dir = artifact_dir_for_thread(thread_id)
    if artifact_dir.exists():
        artifacts = sorted(path for path in artifact_dir.iterdir() if path.is_file())
        for artifact in artifacts[-6:]:
            print(f"image_artifact={artifact}")
    return latest_seq


def print_new_assistant_output(
    *,
    connection,
    thread_id: str,
    seen_seq: int,
) -> int:
    """Print assistant messages and save any newly generated images."""
    items = runtime_queries.list_items(connection, thread_id)
    new_items = [item for item in items if (item.seq or 0) > seen_seq]
    for item in new_items:
        if item.item_type == "message" and item.role == "assistant" and item.content_text:
            print(f"\nassistant> {item.content_text}\n")
    for path in save_generated_images(
        items=new_items,
        artifacts_dir=artifact_dir_for_thread(thread_id),
    ):
        print(f"image_artifact={path}")
    return max((item.seq or 0) for item in items) if items else seen_seq


def main() -> int:
    """Run the interactive durable-runtime REPL."""
    configure_logging()
    args = parse_args()
    agent_spec = build_agent_spec(args.model)
    current_thread_id = args.thread_id
    seen_seq_by_thread: dict[str, int] = {}
    db = sqlite_db(args.db_path)

    with db.connect() as connection:
        apply_pending_migrations(connection)
        loop = AgentRuntimeLoop(
            agent_registry=AgentRegistry([agent_spec]),
            tools=ToolRegistry(),
            executor=LiteLLMAgentExecutor(),
        )

        print(f"db_path={args.db_path}")
        print(f"model={agent_spec.default_model}")
        print("agent_spec=" + agent_spec.model_dump_json(indent=2))
        print_help()
        print_current_thread(connection, current_thread_id)
        if current_thread_id and runtime_queries.get_thread(connection, current_thread_id) is not None:
            seen_seq_by_thread[current_thread_id] = print_thread_history(
                connection=connection,
                thread_id=current_thread_id,
            )

        while True:
            try:
                raw = input("repl> ").strip()
            except EOFError:
                print()
                break
            if not raw:
                continue
            if raw == "/quit":
                break
            if raw == "/help":
                print_help()
                continue
            if raw == "/threads":
                list_thread_rows(connection)
                continue
            if raw.startswith("/new"):
                title = raw[len("/new") :].strip() or "REPL Thread"
                thread, _turn = loop.start_thread(db, agent_id=agent_spec.agent_id, title=title)
                current_thread_id = thread.thread_id
                seen_seq_by_thread[current_thread_id] = 0
                print(f"thread_started={thread.thread_id}")
                print_current_thread(connection, current_thread_id)
                continue
            if raw.startswith("/resume "):
                thread_id = raw.split(maxsplit=1)[1].strip()
                if runtime_queries.get_thread(connection, thread_id) is None:
                    print(f"unknown_thread={thread_id}")
                    continue
                current_thread_id = thread_id
                print_current_thread(connection, current_thread_id)
                seen_seq_by_thread[current_thread_id] = print_thread_history(
                    connection=connection,
                    thread_id=current_thread_id,
                )
                continue
            if raw.startswith("/task "):
                task_text = raw.split(maxsplit=1)[1].strip()
                thread, _turn = loop.start_task(db, agent_id=agent_spec.agent_id, task_text=task_text, title="REPL Task")
                current_thread_id = thread.thread_id
                result = loop.run_pending_turns(
                    db,
                    max_turns=10,
                    max_steps=100,
                    thread_id=current_thread_id,
                )
                seen_seq_by_thread[current_thread_id] = print_new_assistant_output(
                    connection=connection,
                    thread_id=current_thread_id,
                    seen_seq=seen_seq_by_thread.get(current_thread_id, 0),
                )
                print(
                    f"task_thread={current_thread_id} turns_completed={result.turns_completed} "
                    f"turns_failed={result.turns_failed}"
                )
                continue
            if raw == "/show":
                print_current_thread(connection, current_thread_id)
                continue

            if not current_thread_id:
                thread, _turn = loop.start_thread(db, agent_id=agent_spec.agent_id, title="REPL Thread")
                current_thread_id = thread.thread_id
                seen_seq_by_thread.setdefault(current_thread_id, 0)
                print(f"thread_started={thread.thread_id}")

            loop.send_input(db, current_thread_id, raw)
            result = loop.run_pending_turns(
                db,
                max_turns=10,
                max_steps=100,
                thread_id=current_thread_id,
            )
            seen_seq_by_thread[current_thread_id] = print_new_assistant_output(
                connection=connection,
                thread_id=current_thread_id,
                seen_seq=seen_seq_by_thread.get(current_thread_id, 0),
            )
            print(
                f"turns_completed={result.turns_completed} "
                f"turns_failed={result.turns_failed} steps_executed={result.steps_executed}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
