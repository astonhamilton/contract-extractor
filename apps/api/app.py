import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, Response
from fastapi.staticfiles import StaticFiles

from apps.api.agent_runtime import build_embedded_agent_runtime_service
from apps.api.auth import (
    AuthenticationMiddleware,
    build_login_rate_limiter,
    install_session_middleware,
)
from apps.api.routes.auth_login.handler import auth_login
from apps.api.routes.auth_login.schema import AuthLoginResponse
from apps.api.routes.auth_logout.handler import auth_logout
from apps.api.routes.auth_logout.schema import AuthLogoutResponse
from apps.api.routes.auth_session.handler import auth_session
from apps.api.routes.auth_session.schema import AuthSessionResponse
from apps.api.db_startup import ensure_app_db_schema
from apps.api.routes.corpus_document_detail.handler import corpus_document_detail
from apps.api.routes.corpus_document_detail.schema import CorpusDocumentDetailResponse
from apps.api.routes.corpus_document_page_notes.handler import corpus_document_page_notes
from apps.api.routes.corpus_document_page_notes.schema import CorpusDocumentPageNotesResponse
from apps.api.routes.corpus_document_page_detail.handler import corpus_document_page_detail
from apps.api.routes.corpus_document_page_detail.schema import CorpusDocumentPageDetailResponse
from apps.api.routes.corpus_document_notes.handler import corpus_document_notes
from apps.api.routes.corpus_document_notes.schema import CorpusDocumentNotesResponse
from apps.api.routes.corpus_document_pages.handler import corpus_document_pages
from apps.api.routes.corpus_document_pages.schema import CorpusDocumentPagesResponse
from apps.api.routes.corpus_documents.handler import corpus_documents
from apps.api.routes.corpus_documents.schema import CorpusDocumentsResponse
from apps.api.routes.corpus_summary.handler import corpus_summary
from apps.api.routes.corpus_summary.schema import CorpusSummaryResponse
from apps.api.routes.health.handler import health
from apps.api.routes.health.schema import HealthResponse
from apps.api.routes.root.handler import root
from apps.api.routes.root.schema import RootResponse
from apps.api.routes.stats.handler import stats
from apps.api.routes.stats.schema import AppStatsResponse
from apps.api.routes.thread_detail.handler import thread_detail
from apps.api.routes.thread_detail.schema import ThreadDetailResponse
from apps.api.routes.thread_create.handler import thread_create
from apps.api.routes.thread_create.schema import ThreadCreateResponse
from apps.api.routes.thread_delete.handler import thread_delete
from apps.api.routes.thread_items.handler import thread_items
from apps.api.routes.thread_items.schema import ThreadItemsResponse
from apps.api.routes.thread_post_items.handler import thread_post_items
from apps.api.routes.thread_post_items.schema import ThreadPostItemsResponse
from apps.api.routes.thread_stream.handler import thread_stream
from apps.api.routes.thread_title_suggestion.handler import thread_title_suggestion
from apps.api.routes.thread_title_suggestion.schema import ThreadTitleSuggestionResponse
from apps.api.routes.thread_update_title.handler import thread_update_title
from apps.api.routes.thread_update_title.schema import ThreadUpdateTitleResponse
from apps.api.routes.thread_turns.handler import thread_turns
from apps.api.routes.thread_turns.schema import ThreadTurnsResponse
from apps.api.routes.threads.handler import threads
from apps.api.routes.threads.schema import ThreadsResponse
from apps.api.routes.turn_detail.handler import turn_detail
from apps.api.routes.turn_detail.schema import TurnDetailResponse
from apps.api.routes.turn_model_calls.handler import turn_model_calls
from apps.api.routes.turn_model_calls.schema import TurnModelCallsResponse
from apps.api.routes.turn_tool_invocations.handler import turn_tool_invocations
from apps.api.routes.turn_tool_invocations.schema import TurnToolInvocationsResponse
from apps.api.routes.web_app.handler import serve_web_app_index, web_app_dist_dir
from packages.data_store.connect import default_db
from apps.api.settings import ApiAuthSettings, ApiSettings

LOGGER = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start and stop the embedded agent-runtime worker with the API app lifecycle."""
    repo_root = Path(__file__).resolve().parents[2]
    db = default_db(repo_root)
    ensure_app_db_schema(db)
    service = build_embedded_agent_runtime_service(
        repo_root=repo_root,
        db=db,
    )
    app.state.agent_runtime_service = service
    service.start()
    try:
        yield
    finally:
        service.stop()

app = FastAPI(
    title="Contract Extractor API",
    version="0.1.0",
    lifespan=lifespan,
)
auth_settings = ApiAuthSettings.from_env()
app.state.login_rate_limiter = build_login_rate_limiter(auth_settings)
app.add_middleware(AuthenticationMiddleware)
install_session_middleware(app, auth_settings)


def _parse_debug_delay_ms(request: Request, *, max_delay_ms: int) -> int:
    """Parse a bounded debug delay from query params or headers."""

    raw_value = (
        request.query_params.get("x_debug_delay_ms")
        or request.headers.get("X-Debug-Delay-Ms")
        or ""
    ).strip()
    if not raw_value:
        return 0
    try:
        delay_ms = int(raw_value)
    except ValueError:
        return 0
    if delay_ms <= 0:
        return 0
    return min(delay_ms, max_delay_ms)


@app.middleware("http")
async def debug_delay_middleware(request: Request, call_next) -> Response:
    """Apply an opt-in bounded debug delay for frontend loading-state testing."""

    settings = ApiSettings.from_env()
    if not settings.enable_debug_delay:
        return await call_next(request)

    delay_ms = _parse_debug_delay_ms(request, max_delay_ms=settings.max_debug_delay_ms)
    if delay_ms > 0:
        await asyncio.sleep(delay_ms / 1000)

    response = await call_next(request)
    if delay_ms > 0:
        response.headers["X-Debug-Delay-Applied-Ms"] = str(delay_ms)
    return response


app.get("/api", response_model=RootResponse)(root)
app.get("/api/health", response_model=HealthResponse)(health)
app.get("/api/stats", response_model=AppStatsResponse)(stats)
app.post("/api/auth/login", response_model=AuthLoginResponse)(auth_login)
app.post("/api/auth/logout", response_model=AuthLogoutResponse)(auth_logout)
app.get("/api/auth/session", response_model=AuthSessionResponse)(auth_session)
app.get("/api/threads", response_model=ThreadsResponse)(threads)
app.post("/api/threads", response_model=ThreadCreateResponse)(thread_create)
app.delete("/api/threads/{thread_id}", status_code=204)(thread_delete)
app.post("/api/threads/title-suggestion", response_model=ThreadTitleSuggestionResponse)(
    thread_title_suggestion
)
app.get("/api/threads/{thread_id}", response_model=ThreadDetailResponse)(thread_detail)
app.patch("/api/threads/{thread_id}/title", response_model=ThreadUpdateTitleResponse)(
    thread_update_title
)
app.get("/api/threads/{thread_id}/items", response_model=ThreadItemsResponse)(thread_items)
app.post("/api/threads/{thread_id}/items", response_model=ThreadPostItemsResponse)(
    thread_post_items
)
app.get("/api/threads/{thread_id}/stream")(thread_stream)
app.get("/api/threads/{thread_id}/turns", response_model=ThreadTurnsResponse)(thread_turns)
app.get("/api/turns/{turn_id}", response_model=TurnDetailResponse)(turn_detail)
app.get("/api/turns/{turn_id}/model-calls", response_model=TurnModelCallsResponse)(
    turn_model_calls
)
app.get(
    "/api/turns/{turn_id}/tool-invocations",
    response_model=TurnToolInvocationsResponse,
)(turn_tool_invocations)
app.get("/api/corpus/summary", response_model=CorpusSummaryResponse)(corpus_summary)
app.get("/api/corpus/documents", response_model=CorpusDocumentsResponse)(corpus_documents)
app.get("/api/corpus/documents/{doc_id}", response_model=CorpusDocumentDetailResponse)(
    corpus_document_detail
)
app.get(
    "/api/corpus/documents/{doc_id}/page-notes",
    response_model=CorpusDocumentPageNotesResponse,
)(corpus_document_page_notes)
app.get(
    "/api/corpus/documents/{doc_id}/pages",
    response_model=CorpusDocumentPagesResponse,
)(corpus_document_pages)
app.get(
    "/api/corpus/documents/{doc_id}/pages/{page_number}",
    response_model=CorpusDocumentPageDetailResponse,
)(corpus_document_page_detail)
app.get(
    "/api/corpus/documents/{doc_id}/notes",
    response_model=CorpusDocumentNotesResponse,
)(corpus_document_notes)
app.get("/health", response_model=HealthResponse)(health)
app.get("/stats", response_model=AppStatsResponse)(stats)
app.get("/threads", response_model=ThreadsResponse)(threads)
app.post("/threads", response_model=ThreadCreateResponse)(thread_create)
app.post("/threads/title-suggestion", response_model=ThreadTitleSuggestionResponse)(thread_title_suggestion)
app.get("/threads/{thread_id}", response_model=ThreadDetailResponse)(thread_detail)
app.patch("/threads/{thread_id}/title", response_model=ThreadUpdateTitleResponse)(thread_update_title)
app.get("/threads/{thread_id}/items", response_model=ThreadItemsResponse)(thread_items)
app.post("/threads/{thread_id}/items", response_model=ThreadPostItemsResponse)(thread_post_items)
app.get("/threads/{thread_id}/stream")(thread_stream)
app.get("/threads/{thread_id}/turns", response_model=ThreadTurnsResponse)(thread_turns)
app.get("/turns/{turn_id}", response_model=TurnDetailResponse)(turn_detail)
app.get("/turns/{turn_id}/model-calls", response_model=TurnModelCallsResponse)(turn_model_calls)
app.get("/turns/{turn_id}/tool-invocations", response_model=TurnToolInvocationsResponse)(
    turn_tool_invocations
)
app.get("/corpus/summary", response_model=CorpusSummaryResponse)(corpus_summary)
app.get("/corpus/documents", response_model=CorpusDocumentsResponse)(corpus_documents)
app.get("/corpus/documents/{doc_id}", response_model=CorpusDocumentDetailResponse)(
    corpus_document_detail
)
app.get(
    "/corpus/documents/{doc_id}/page-notes",
    response_model=CorpusDocumentPageNotesResponse,
)(corpus_document_page_notes)
app.get(
    "/corpus/documents/{doc_id}/pages",
    response_model=CorpusDocumentPagesResponse,
)(corpus_document_pages)
app.get(
    "/corpus/documents/{doc_id}/pages/{page_number}",
    response_model=CorpusDocumentPageDetailResponse,
)(corpus_document_page_detail)
app.get(
    "/corpus/documents/{doc_id}/notes",
    response_model=CorpusDocumentNotesResponse,
)(corpus_document_notes)

repo_root = Path(__file__).resolve().parents[2]
deployed_web_dist_dir = web_app_dist_dir(repo_root)
if deployed_web_dist_dir.exists():
    app.mount(
        "/assets",
        StaticFiles(directory=deployed_web_dist_dir / "assets"),
        name="web-assets",
    )


@app.get("/corpus", include_in_schema=False)
def web_corpus():
    """Serve the SPA entrypoint for corpus permalinks."""

    return serve_web_app_index(repo_root)


@app.get("/", include_in_schema=False)
def web_root():
    """Serve the SPA entrypoint at the site root."""

    return serve_web_app_index(repo_root)
