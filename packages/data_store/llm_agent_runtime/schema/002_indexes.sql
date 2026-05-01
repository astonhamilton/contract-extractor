PRAGMA foreign_keys = ON;

CREATE INDEX IF NOT EXISTS idx_agent_runtime_threads_updated_at
    ON agent_runtime_threads(updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_agent_runtime_threads_active_turn_id
    ON agent_runtime_threads(active_turn_id);

CREATE INDEX IF NOT EXISTS idx_agent_runtime_turns_thread_started_at
    ON agent_runtime_turns(thread_id, started_at DESC);

CREATE INDEX IF NOT EXISTS idx_agent_runtime_turns_status_phase
    ON agent_runtime_turns(status, phase, queued_at);

CREATE INDEX IF NOT EXISTS idx_agent_runtime_turns_status_claim_heartbeat
    ON agent_runtime_turns(status, claim_worker_id, heartbeat_at, queued_at);

CREATE INDEX IF NOT EXISTS idx_agent_runtime_model_calls_turn_ordinal
    ON agent_runtime_model_calls(turn_id, ordinal);

CREATE INDEX IF NOT EXISTS idx_agent_runtime_model_calls_status_heartbeat
    ON agent_runtime_model_calls(status, heartbeat_at);

CREATE INDEX IF NOT EXISTS idx_agent_runtime_items_thread_seq
    ON agent_runtime_items(thread_id, seq);

CREATE INDEX IF NOT EXISTS idx_agent_runtime_items_turn_id
    ON agent_runtime_items(turn_id);

CREATE INDEX IF NOT EXISTS idx_agent_runtime_items_model_call_id
    ON agent_runtime_items(model_call_id);

CREATE INDEX IF NOT EXISTS idx_agent_runtime_tool_invocations_thread_started_at
    ON agent_runtime_tool_invocations(thread_id, started_at DESC);

CREATE INDEX IF NOT EXISTS idx_agent_runtime_tool_invocations_turn_id
    ON agent_runtime_tool_invocations(turn_id);

CREATE INDEX IF NOT EXISTS idx_agent_runtime_tool_invocations_status_heartbeat
    ON agent_runtime_tool_invocations(status, heartbeat_at);
