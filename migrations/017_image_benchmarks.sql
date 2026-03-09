-- Migration 017: Image benchmarking tables
-- Stores per-image quality scores and category benchmark averages

CREATE TABLE IF NOT EXISTS image_benchmarks (
    id VARCHAR PRIMARY KEY,
    user_id VARCHAR NOT NULL REFERENCES users(id),
    integration_id VARCHAR REFERENCES integrations(id) ON DELETE SET NULL,
    product_id VARCHAR,
    product_title VARCHAR,
    image_url VARCHAR,
    job_item_id VARCHAR REFERENCES job_items(id) ON DELETE SET NULL,
    scores JSON NOT NULL,
    overall_score INTEGER NOT NULL,
    suggestions JSON,
    category VARCHAR(100),
    created_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE INDEX idx_benchmarks_user ON image_benchmarks(user_id);
CREATE INDEX idx_benchmarks_integration ON image_benchmarks(integration_id);

CREATE TABLE IF NOT EXISTS category_benchmarks (
    id VARCHAR PRIMARY KEY,
    category VARCHAR(100) NOT NULL UNIQUE,
    avg_scores JSON NOT NULL,
    sample_size INTEGER NOT NULL DEFAULT 0,
    updated_at TIMESTAMP NOT NULL DEFAULT now()
);

-- Seed category benchmarks with industry averages
INSERT INTO category_benchmarks (id, category, avg_scores, sample_size) VALUES
    ('catbench_fashion', 'fashion', '{"resolution": 72, "background": 65, "lighting": 68, "composition": 62, "text_penalty": 85, "image_count": 70}', 500),
    ('catbench_electronics', 'electronics', '{"resolution": 78, "background": 75, "lighting": 72, "composition": 70, "text_penalty": 80, "image_count": 65}', 500),
    ('catbench_jewelry', 'jewelry', '{"resolution": 70, "background": 60, "lighting": 65, "composition": 58, "text_penalty": 88, "image_count": 55}', 500),
    ('catbench_home', 'home & garden', '{"resolution": 68, "background": 55, "lighting": 62, "composition": 60, "text_penalty": 82, "image_count": 60}', 500),
    ('catbench_beauty', 'beauty', '{"resolution": 75, "background": 70, "lighting": 72, "composition": 68, "text_penalty": 78, "image_count": 65}', 500),
    ('catbench_food', 'food & beverage', '{"resolution": 65, "background": 50, "lighting": 60, "composition": 55, "text_penalty": 90, "image_count": 50}', 500),
    ('catbench_toys', 'toys & games', '{"resolution": 70, "background": 62, "lighting": 65, "composition": 60, "text_penalty": 75, "image_count": 60}', 500),
    ('catbench_sports', 'sports & outdoors', '{"resolution": 72, "background": 60, "lighting": 66, "composition": 62, "text_penalty": 82, "image_count": 58}', 500),
    ('catbench_general', 'general', '{"resolution": 70, "background": 62, "lighting": 65, "composition": 60, "text_penalty": 82, "image_count": 60}', 500)
ON CONFLICT (id) DO NOTHING;
