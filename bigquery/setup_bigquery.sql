-- ============================================================================
-- Apigee x Gemini AI Governance & Chargeback Demo - BigQuery Schema & Views
-- Target Dataset: apigee_ai_governance
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS `apigee_ai_governance`
OPTIONS(
  location="US",
  description="Apigee AI Gateway Department x Model Token Usage & Chargeback Dataset for Looker Studio"
);

CREATE TABLE IF NOT EXISTS `apigee_ai_governance.llm_token_usage` (
  timestamp TIMESTAMP NOT NULL,
  request_id STRING NOT NULL,
  department_id STRING NOT NULL,
  department_name STRING NOT NULL,
  model STRING NOT NULL,
  status_code INT64 NOT NULL,
  status_label STRING NOT NULL,
  prompt_tokens INT64 NOT NULL,
  completion_tokens INT64 NOT NULL,
  total_tokens INT64 NOT NULL,
  unit_price_per_1k_usd FLOAT64 NOT NULL,
  estimated_cost_usd FLOAT64 NOT NULL,
  estimated_cost_krw FLOAT64 NOT NULL,
  prevented_cost_usd FLOAT64 NOT NULL,
  prevented_cost_krw FLOAT64 NOT NULL,
  apigee_policy STRING NOT NULL,
  use_case STRING
)
PARTITION BY DATE(timestamp)
CLUSTER BY department_name, model, status_code;

-- ============================================================================
-- View 1: Looker Studio Department x Model Chargeback Summary View
-- Shows exact token usage and chargeback settlement broken down by Dept & Model
-- ============================================================================
CREATE OR REPLACE VIEW `apigee_ai_governance.v_looker_dept_model_chargeback` AS
SELECT
  department_id,
  department_name,
  model,
  COUNTIF(status_code = 200) AS successful_calls,
  COUNTIF(status_code = 403) AS blocked_403_calls,
  SUM(IF(status_code = 200, prompt_tokens, 0)) AS prompt_tokens,
  SUM(IF(status_code = 200, completion_tokens, 0)) AS completion_tokens,
  SUM(IF(status_code = 200, total_tokens, 0)) AS total_tokens,
  ANY_VALUE(unit_price_per_1k_usd) AS unit_price_per_1k_usd,
  ROUND(SUM(IF(status_code = 200, estimated_cost_usd, 0)), 4) AS total_chargeback_usd,
  ROUND(SUM(IF(status_code = 200, estimated_cost_krw, 0)), 0) AS total_chargeback_krw,
  ROUND(SUM(IF(status_code = 403, prevented_cost_usd, 0)), 4) AS total_prevented_cost_usd,
  ROUND(SUM(IF(status_code = 403, prevented_cost_krw, 0)), 0) AS total_prevented_cost_krw
FROM
  `apigee_ai_governance.llm_token_usage`
GROUP BY
  department_id,
  department_name,
  model
ORDER BY
  department_name ASC,
  model ASC;

-- ============================================================================
-- View 2: Looker Studio Time-Series Usage & Cost Settlement View
-- ============================================================================
CREATE OR REPLACE VIEW `apigee_ai_governance.v_looker_hourly_chargeback` AS
SELECT
  TIMESTAMP_TRUNC(timestamp, HOUR) AS usage_hour,
  department_name,
  model,
  status_code,
  status_label,
  COUNT(*) AS request_count,
  SUM(total_tokens) AS total_tokens,
  ROUND(SUM(estimated_cost_usd), 4) AS chargeback_usd,
  ROUND(SUM(estimated_cost_krw), 0) AS chargeback_krw,
  ROUND(SUM(prevented_cost_krw), 0) AS prevented_cost_krw
FROM
  `apigee_ai_governance.llm_token_usage`
GROUP BY
  usage_hour,
  department_name,
  model,
  status_code,
  status_label
ORDER BY
  usage_hour DESC;
