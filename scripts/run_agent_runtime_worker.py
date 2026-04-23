from __future__ import annotations

import argparse
import signal
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from packages.data_store.connect import default_db_path, sqlite_db
from packages.data_store.migrations import apply_pending_migrations
from packages.llm.agents.app.corpus_assistant.agent_spec import build_corpus_assistant_agent_spec
from packages.llm.agents.app.corpus_assistant.tool_registry import build_corpus_tool_registry
from packages.llm.shared.agent_runtime.emitter import CompositeRuntimeEventEmitter, RuntimeEventEmitter
from packages.llm.shared.agent_runtime.event_sinks import (
    JsonlRuntimeEventSink,
    PrettyPrintRuntimeEventSink,
)
from packages.llm.shared.agent_runtime.loop import AgentRuntimeLoop
from packages.llm.shared.agent_runtime.registry import AgentRegistry
from packages.llm.shared.agent_runtime.worker import AgentRuntimeWorker, WorkerPassResult
from packages.pipeline.logging_utils import configure_logging


@dataclass
class WorkerPrinterState:
    """Track pretty-print state for the worker CLI."""

    idle_streak: int = 0


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for the background agent worker."""
    parser = argparse.ArgumentParser(
        description="Run the corpus-assistant background worker over queued assistant turns.",
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        default=default_db_path(REPO_ROOT),
        help="SQLite database path. Defaults to data/app/app.db.",
    )
    parser.add_argument(
        "--provider",
        default=None,
        help="Optional provider override for the corpus assistant.",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Optional model override for the corpus assistant.",
    )
    parser.add_argument(
        "--max-turns",
        type=int,
        default=25,
        help="Maximum queued/active turns to inspect per worker pass.",
    )
    parser.add_argument(
        "--max-steps",
        type=int,
        default=200,
        help="Maximum phase steps to execute per worker pass.",
    )
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=0.5,
        help="Idle sleep interval in seconds between passes.",
    )
    parser.add_argument(
        "--thread-id",
        default=None,
        help="Optional thread filter for debugging a single thread.",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run one worker pass and exit.",
    )
    parser.add_argument(
        "--verbose-logs",
        action="store_true",
        help="Enable runtime logger output in addition to the worker summaries.",
    )
    parser.add_argument(
        "--event-pretty",
        action="store_true",
        default=True,
        help="Print fine-grained runtime events through the pretty event sink (default: on).",
    )
    parser.add_argument(
        "--no-event-pretty",
        action="store_false",
        dest="event_pretty",
        help="Disable fine-grained pretty event output.",
    )
    parser.add_argument(
        "--event-jsonl",
        type=Path,
        default=None,
        help="Optional JSONL file path for structured runtime events. Defaults to a timestamped file under .logs/agent_runtime_worker/.",
    )
    return parser.parse_args()


def build_runtime_loop(
    *,
    default_provider: str,
    default_model: str,
    emitter: RuntimeEventEmitter | None = None,
) -> AgentRuntimeLoop:
    """Return the immutable runtime loop for the corpus-assistant worker."""
    tools = build_corpus_tool_registry()
    agent_spec = build_corpus_assistant_agent_spec().model_copy(
        update={
            "default_provider": default_provider,
            "default_model": default_model,
        }
    )
    registry = AgentRegistry(
        [lambda: agent_spec]
    )
    return AgentRuntimeLoop(agent_registry=registry, tools=tools, emitter=emitter)


def default_event_jsonl_path() -> Path:
    """Return the default JSONL event log path for the worker script."""
    timestamp = datetime.now().astimezone().strftime("%Y%m%d_%H%M%S")
    return REPO_ROOT / ".logs" / "agent_runtime_worker" / f"events_{timestamp}.jsonl"


def format_header(args: argparse.Namespace, *, default_provider: str, default_model: str) -> str:
    """Return the startup banner for the worker script."""
    lines = [
        "agent-runtime worker",
        f"  db_path: {args.db_path}",
        f"  provider: {default_provider}",
        f"  model: {default_model}",
        f"  max_turns: {args.max_turns}",
        f"  max_steps: {args.max_steps}",
        f"  poll_interval: {args.poll_interval:.2f}s",
        f"  thread_filter: {args.thread_id or '-'}",
        f"  mode: {'once' if args.once else 'forever'}",
        f"  event_pretty: {args.event_pretty}",
        f"  event_jsonl: {args.event_jsonl or '-'}",
    ]
    return "\n".join(lines)


def format_pass_result(
    result: WorkerPassResult,
    *,
    idle_streak: int,
    poll_interval_seconds: float,
    once: bool,
) -> str:
    """Return one compact human-readable line for a worker pass."""
    pending = result.pending_turns
    timestamp = result.finished_at.astimezone().strftime("%H:%M:%S")
    duration = f"{result.duration_seconds:.2f}s"
    if not result.did_work:
        if once:
            return f"[{timestamp}] idle  duration={duration}  no_work"
        return f"[{timestamp}] idle  streak={idle_streak}  sleep={poll_interval_seconds:.2f}s"
    return (
        f"[{timestamp}] work  duration={duration}  "
        f"seen={pending.turns_seen}  "
        f"completed={pending.turns_completed}  "
        f"failed={pending.turns_failed}  "
        f"steps={pending.steps_executed}  "
        f"recovered_turns={pending.stale_turns_recovered}  "
        f"retried_tools={pending.stale_tool_invocations_retried}  "
        f"failed_tools={pending.stale_tool_invocations_failed}"
    )


def build_pass_printer(state: WorkerPrinterState, *, poll_interval_seconds: float):
    """Return a callback that pretty-prints worker pass summaries."""

    def _print_pass(result: WorkerPassResult) -> None:
        if result.did_work:
            state.idle_streak = 0
            print(
                format_pass_result(
                    result,
                    idle_streak=0,
                    poll_interval_seconds=poll_interval_seconds,
                    once=False,
                ),
                flush=True,
            )
            return
        state.idle_streak += 1
        if state.idle_streak == 1 or state.idle_streak % 20 == 0:
            print(
                format_pass_result(
                    result,
                    idle_streak=state.idle_streak,
                    poll_interval_seconds=poll_interval_seconds,
                    once=False,
                ),
                flush=True,
            )

    return _print_pass


def install_signal_handlers() -> None:
    """Install minimal signal handlers so the script exits cleanly."""

    def _handle_signal(signum, _frame) -> None:
        name = signal.Signals(signum).name
        print(f"\nworker stopping on {name}", flush=True)
        raise SystemExit(0)

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)


def build_event_emitter(args: argparse.Namespace) -> RuntimeEventEmitter | None:
    """Return the composite runtime event emitter requested by CLI flags."""
    sinks: list[RuntimeEventEmitter] = []
    if args.event_pretty:
        sinks.append(PrettyPrintRuntimeEventSink())
    if args.event_jsonl is not None:
        sinks.append(JsonlRuntimeEventSink(args.event_jsonl))
    if not sinks:
        return None
    return CompositeRuntimeEventEmitter(sinks)


def main() -> int:
    """Run the corpus-assistant worker once or forever."""
    args = parse_args()
    if args.event_jsonl is None:
        args.event_jsonl = default_event_jsonl_path()
    if args.verbose_logs:
        configure_logging()
    default_provider = args.provider or "openai"
    default_model = args.model or "openai/gpt-5.4-mini"
    event_emitter = build_event_emitter(args)
    db = sqlite_db(args.db_path)

    with db.connect() as connection:
        apply_pending_migrations(connection)

    worker = AgentRuntimeWorker(
        db=db,
        loop=build_runtime_loop(
            default_provider=default_provider,
            default_model=default_model,
            emitter=event_emitter,
        ),
        emitter=event_emitter,
    )
    state = WorkerPrinterState()
    print(
        format_header(
            args,
            default_provider=default_provider,
            default_model=default_model,
        ),
        flush=True,
    )
    if args.once:
        result = worker.run_once(
            max_turns=args.max_turns,
            max_steps=args.max_steps,
            thread_id=args.thread_id,
        )
        print(
            format_pass_result(
                result,
                idle_streak=0,
                poll_interval_seconds=args.poll_interval,
                once=True,
            ),
            flush=True,
        )
        return 0

    install_signal_handlers()
    worker.run_forever(
        max_turns=args.max_turns,
        max_steps=args.max_steps,
        thread_id=args.thread_id,
        poll_interval_seconds=args.poll_interval,
        on_pass=build_pass_printer(state, poll_interval_seconds=args.poll_interval),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
