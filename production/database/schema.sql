-- =============================================================================
-- CUSTOMER SUCCESS FTE — CRM / TICKET MANAGEMENT SYSTEM
-- CloudSync Pro Support Database
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "vector";

-- ---------------------------------------------------------------------------
-- customers — unified identity across all channels
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS customers (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email       VARCHAR(255) UNIQUE,
    phone       VARCHAR(50),
    name        VARCHAR(255),
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    metadata    JSONB DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_customers_email ON customers(email);

-- ---------------------------------------------------------------------------
-- customer_identifiers — cross-channel contact point mapping
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS customer_identifiers (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id      UUID REFERENCES customers(id) ON DELETE CASCADE,
    identifier_type  VARCHAR(50) NOT NULL,   -- 'email', 'phone', 'whatsapp'
    identifier_value VARCHAR(255) NOT NULL,
    verified         BOOLEAN DEFAULT FALSE,
    created_at       TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(identifier_type, identifier_value)
);

CREATE INDEX IF NOT EXISTS idx_customer_identifiers_value
    ON customer_identifiers(identifier_value);

CREATE INDEX IF NOT EXISTS idx_customer_identifiers_type_value
    ON customer_identifiers(identifier_type, identifier_value);

-- ---------------------------------------------------------------------------
-- conversations — a thread that may span multiple channels
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS conversations (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id      UUID REFERENCES customers(id) ON DELETE CASCADE,
    initial_channel  VARCHAR(50) NOT NULL,   -- 'email', 'whatsapp', 'web_form'
    started_at       TIMESTAMPTZ DEFAULT NOW(),
    ended_at         TIMESTAMPTZ,
    status           VARCHAR(50) DEFAULT 'active',
    sentiment_score  DECIMAL(3,2),
    resolution_type  VARCHAR(50),
    escalated_to     VARCHAR(255),
    metadata         JSONB DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_conversations_customer ON conversations(customer_id);
CREATE INDEX IF NOT EXISTS idx_conversations_status   ON conversations(status);
CREATE INDEX IF NOT EXISTS idx_conversations_channel  ON conversations(initial_channel);
CREATE INDEX IF NOT EXISTS idx_conversations_active   ON conversations(customer_id, status, started_at);

-- ---------------------------------------------------------------------------
-- messages — every communication unit (inbound + outbound)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS messages (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id    UUID REFERENCES conversations(id) ON DELETE CASCADE,
    channel            VARCHAR(50) NOT NULL,
    direction          VARCHAR(20) NOT NULL,   -- 'inbound', 'outbound'
    role               VARCHAR(20) NOT NULL,   -- 'customer', 'agent', 'system'
    content            TEXT NOT NULL,
    created_at         TIMESTAMPTZ DEFAULT NOW(),
    tokens_used        INTEGER,
    latency_ms         INTEGER,
    tool_calls         JSONB DEFAULT '[]',
    channel_message_id VARCHAR(255),
    delivery_status    VARCHAR(50) DEFAULT 'pending'
);

CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_messages_channel      ON messages(channel);
CREATE INDEX IF NOT EXISTS idx_messages_created      ON messages(created_at DESC);

-- ---------------------------------------------------------------------------
-- tickets — discrete support issues
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS tickets (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id  UUID REFERENCES conversations(id) ON DELETE CASCADE,
    customer_id      UUID REFERENCES customers(id),
    source_channel   VARCHAR(50) NOT NULL,
    category         VARCHAR(100),
    priority         VARCHAR(20) DEFAULT 'medium',
    status           VARCHAR(50) DEFAULT 'open',
    created_at       TIMESTAMPTZ DEFAULT NOW(),
    resolved_at      TIMESTAMPTZ,
    resolution_notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_tickets_status      ON tickets(status);
CREATE INDEX IF NOT EXISTS idx_tickets_channel     ON tickets(source_channel);
CREATE INDEX IF NOT EXISTS idx_tickets_customer    ON tickets(customer_id);

-- ---------------------------------------------------------------------------
-- knowledge_base — product documentation with vector embeddings
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS knowledge_base (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title      VARCHAR(500) NOT NULL,
    content    TEXT NOT NULL,
    category   VARCHAR(100),
    embedding  VECTOR(1536),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_knowledge_embedding
    ON knowledge_base USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- ---------------------------------------------------------------------------
-- channel_configs — per-channel runtime settings
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS channel_configs (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    channel             VARCHAR(50) UNIQUE NOT NULL,
    enabled             BOOLEAN DEFAULT TRUE,
    config              JSONB NOT NULL DEFAULT '{}',
    response_template   TEXT,
    max_response_length INTEGER,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

-- ---------------------------------------------------------------------------
-- agent_metrics — append-only time-series performance data
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS agent_metrics (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    metric_name  VARCHAR(100) NOT NULL,
    metric_value DECIMAL(10,4) NOT NULL,
    channel      VARCHAR(50),
    dimensions   JSONB DEFAULT '{}',
    recorded_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_metrics_recorded ON agent_metrics(recorded_at DESC);
CREATE INDEX IF NOT EXISTS idx_metrics_channel  ON agent_metrics(channel, recorded_at DESC);
