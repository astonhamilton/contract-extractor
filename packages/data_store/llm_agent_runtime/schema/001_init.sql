PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS asst_threads (
    thread_id TEXT PRIMARY KEY,
    thread_kind TEXT NOT NULL DEFAULT 'conversation',
    agent_id TEXT NOT NULL,
    title TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    phase TEXT NOT NULL DEFAULT 'idle',
    active_turn_id TEXT,
    last_turn_id TEXT,
    execution_options_json TEXT NOT NULL DEFAULT '{}',
    provider_continuations_json TEXT NOT NULL DEFAULT '{}',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS asst_turns (
    turn_id TEXT PRIMARY KEY,
    thread_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    execution_options_json TEXT NOT NULL DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'queued',
    phase TEXT NOT NULL DEFAULT 'created',
    usage_json TEXT NOT NULL DEFAULT '{}',
    error_json TEXT NOT NULL DEFAULT '{}',
    provider_response_id TEXT,
    provider_conversation_id TEXT,
    claim_worker_id TEXT,
    heartbeat_at TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    queued_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TEXT,
    FOREIGN KEY (thread_id) REFERENCES asst_threads(thread_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS asst_model_calls (
    model_call_id TEXT PRIMARY KEY,
    thread_id TEXT NOT NULL,
    turn_id TEXT NOT NULL,
    ordinal INTEGER NOT NULL,
    provider TEXT,
    model TEXT,
    status TEXT NOT NULL DEFAULT 'created',
    agent_spec_snapshot_json TEXT NOT NULL DEFAULT '{}',
    request_json TEXT NOT NULL DEFAULT '{}',
    response_json TEXT NOT NULL DEFAULT '{}',
    usage_json TEXT NOT NULL DEFAULT '{}',
    error_json TEXT NOT NULL DEFAULT '{}',
    provider_request_id TEXT,
    provider_response_id TEXT,
    worker_id TEXT,
    heartbeat_at TEXT,
    started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TEXT,
    FOREIGN KEY (thread_id) REFERENCES asst_threads(thread_id) ON DELETE CASCADE,
    FOREIGN KEY (turn_id) REFERENCES asst_turns(turn_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS asst_items (
    item_id TEXT PRIMARY KEY,
    thread_id TEXT NOT NULL,
    turn_id TEXT,
    model_call_id TEXT,
    parent_item_id TEXT,
    seq INTEGER NOT NULL,
    item_type TEXT NOT NULL,
    role TEXT,
    content_text TEXT,
    name TEXT,
    arguments_json TEXT NOT NULL DEFAULT '{}',
    result_json TEXT NOT NULL DEFAULT '{}',
    provider_item_id TEXT,
    provider_item_type TEXT,
    provider_payload_json TEXT NOT NULL DEFAULT '{}',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (thread_id) REFERENCES asst_threads(thread_id) ON DELETE CASCADE,
    FOREIGN KEY (turn_id) REFERENCES asst_turns(turn_id) ON DELETE SET NULL,
    FOREIGN KEY (model_call_id) REFERENCES asst_model_calls(model_call_id) ON DELETE SET NULL,
    FOREIGN KEY (parent_item_id) REFERENCES asst_items(item_id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS asst_tool_invocations (
    tool_invocation_id TEXT PRIMARY KEY,
    thread_id TEXT NOT NULL,
    turn_id TEXT,
    model_call_id TEXT,
    tool_call_item_id TEXT,
    tool_result_item_id TEXT,
    tool_name TEXT NOT NULL,
    arguments_json TEXT NOT NULL DEFAULT '{}',
    result_json TEXT NOT NULL DEFAULT '{}',
    status TEXT NOT NULL,
    error_text TEXT,
    worker_id TEXT,
    heartbeat_at TEXT,
    started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TEXT,
    FOREIGN KEY (thread_id) REFERENCES asst_threads(thread_id) ON DELETE CASCADE,
    FOREIGN KEY (turn_id) REFERENCES asst_turns(turn_id) ON DELETE SET NULL,
    FOREIGN KEY (model_call_id) REFERENCES asst_model_calls(model_call_id) ON DELETE SET NULL,
    FOREIGN KEY (tool_call_item_id) REFERENCES asst_items(item_id) ON DELETE SET NULL,
    FOREIGN KEY (tool_result_item_id) REFERENCES asst_items(item_id) ON DELETE SET NULL
);
