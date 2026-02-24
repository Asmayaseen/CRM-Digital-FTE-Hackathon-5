-- Migration 002: Seed channel configurations
INSERT INTO channel_configs (channel, enabled, config, max_response_length)
VALUES
    ('email',    TRUE, '{"format": "html_allowed", "requires_greeting": true, "requires_signature": true}', 2000),
    ('whatsapp', TRUE, '{"format": "text_only", "max_parts": 5, "preferred_length": 300}',               1600),
    ('web_form', TRUE, '{"format": "markdown_allowed", "portal_link": "https://app.cloudsyncpro.com"}',   1000)
ON CONFLICT (channel) DO UPDATE
    SET enabled             = EXCLUDED.enabled,
        config              = EXCLUDED.config,
        max_response_length = EXCLUDED.max_response_length;
