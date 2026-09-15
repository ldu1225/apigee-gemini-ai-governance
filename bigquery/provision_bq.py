#!/usr/bin/env python3
"""
Provisions BigQuery Dataset, Table, Looker Studio Views, and Optional Demo Traffic
for the Apigee x Gemini AI Governance & Chargeback Demo.
"""

import os
import sys
import uuid
import random
from datetime import datetime, timedelta, timezone
from google.cloud import bigquery

import subprocess
from google.oauth2.credentials import Credentials

DEFAULT_PROJECT = os.environ.get("GCP_PROJECT_ID", "your-gcp-project-id")
DATASET_ID = "apigee_ai_governance"
TABLE_ID = "llm_token_usage"


def get_gcloud_creds():
    try:
        cmd = ["gcloud", "auth", "print-access-token"]
        account = os.environ.get("GCP_ACCOUNT")
        if account:
            cmd.append(f"--account={account}")
        token = subprocess.check_output(
            cmd,
            stderr=subprocess.DEVNULL,
        ).decode().strip()
        if token:
            return Credentials(token=token)
    except Exception:
        pass
    return None

# Official Vertex AI Unit Pricing (USD per 1M tokens & KRW exchange rate 1,400)
PRICING = {
    "gemini-3.5-flash": {"input_usd_1m": 0.15, "output_usd_1m": 0.60, "krw_rate": 1400.0},
    "gemini-3.1-pro": {"input_usd_1m": 1.25, "output_usd_1m": 5.00, "krw_rate": 1400.0},
}

DEPT_A = {
    "id": "dept-a",
    "name": "A 부서 (AI 연구개발팀)",
    "token": "dept-a-rnd-token-2026",
    "allowed_models": ["gemini-3.5-flash", "gemini-3.1-pro"],
}

DEPT_B = {
    "id": "dept-b",
    "name": "B 부서 (품질관리팀)",
    "token": "dept-b-quality-token-2026",
    "allowed_models": ["gemini-3.5-flash"],
}


def get_schema():
    return [
        bigquery.SchemaField("timestamp", "TIMESTAMP", mode="REQUIRED"),
        bigquery.SchemaField("request_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("department_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("department_name", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("model", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("status_code", "INTEGER", mode="REQUIRED"),
        bigquery.SchemaField("status_label", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("prompt_tokens", "INTEGER", mode="REQUIRED"),
        bigquery.SchemaField("completion_tokens", "INTEGER", mode="REQUIRED"),
        bigquery.SchemaField("total_tokens", "INTEGER", mode="REQUIRED"),
        bigquery.SchemaField("unit_price_per_1k_usd", "FLOAT", mode="REQUIRED"),
        bigquery.SchemaField("estimated_cost_usd", "FLOAT", mode="REQUIRED"),
        bigquery.SchemaField("estimated_cost_krw", "FLOAT", mode="REQUIRED"),
        bigquery.SchemaField("prevented_cost_usd", "FLOAT", mode="REQUIRED"),
        bigquery.SchemaField("prevented_cost_krw", "FLOAT", mode="REQUIRED"),
        bigquery.SchemaField("apigee_policy", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("use_case", "STRING", mode="NULLABLE"),
    ]


def generate_seed_rows(num_rows=180):
    now = datetime.now(timezone.utc)
    rows = []

    use_cases_a_flash = [
        "기술 문서 다국어 고속 번역 및 핵심 요약",
        "실시간 애플리케이션 서버 로그 이상치 요약",
        "사내 기술 위키 FAQ 챗봇 응답 생성",
    ]
    use_cases_a_pro = [
        "분산 마이크로서비스 아키텍처 심층 코드 리뷰",
        "대규모 데이터 파이프라인 쿼리 최적화 수식 검증",
        "클라우드 네이티브 보안 아키텍처 위협 모델링",
    ]
    use_cases_b_flash = [
        "서비스 품질 점검 리포트 텍스트 자동 추출",
        "고객 VOC 티켓 품질 유형 자동 분류",
        "일일 품질 모니터링 지표 요약 리포트 생성",
    ]
    use_cases_b_blocked = [
        "무단 고단가 Pro 모델 호출 시도 - 대규모 로그 정밀 재분석 요청",
        "무단 고단가 Pro 모델 호출 시도 - 비인가 심층 추론 작업 요청",
    ]

    for i in range(num_rows):
        ts = now - timedelta(minutes=random.randint(1, 1440))
        scenario = random.choices(
            ["a_flash", "a_pro", "b_flash", "b_blocked_pro"],
            weights=[32, 28, 30, 10],
            k=1,
        )[0]

        if scenario == "a_flash":
            dept = DEPT_A
            model = "gemini-3.5-flash"
            status_code = 200
            status_label = "200 OK (정상 승인)"
            prompt_tokens = random.randint(120, 380)
            completion_tokens = random.randint(60, 180)
            total_tokens = prompt_tokens + completion_tokens
            p = PRICING[model]
            cost_usd = round(((prompt_tokens * p["input_usd_1m"]) + (completion_tokens * p["output_usd_1m"])) / 1_000_000.0, 6)
            unit_usd = round((p["input_usd_1m"] + p["output_usd_1m"]) / 2000.0, 6)
            cost_krw = round(cost_usd * p["krw_rate"], 2)
            prevented_usd = 0.0
            prevented_krw = 0.0
            policy = "Pass-Through (Authorized)"
            use_case = random.choice(use_cases_a_flash)

        elif scenario == "a_pro":
            dept = DEPT_A
            model = "gemini-3.1-pro"
            status_code = 200
            status_label = "200 OK (정상 승인)"
            prompt_tokens = random.randint(250, 750)
            completion_tokens = random.randint(150, 450)
            total_tokens = prompt_tokens + completion_tokens
            p = PRICING[model]
            cost_usd = round(((prompt_tokens * p["input_usd_1m"]) + (completion_tokens * p["output_usd_1m"])) / 1_000_000.0, 6)
            unit_usd = round((p["input_usd_1m"] + p["output_usd_1m"]) / 2000.0, 6)
            cost_krw = round(cost_usd * p["krw_rate"], 2)
            prevented_usd = 0.0
            prevented_krw = 0.0
            policy = "Pass-Through (Authorized High-Tier)"
            use_case = random.choice(use_cases_a_pro)

        elif scenario == "b_flash":
            dept = DEPT_B
            model = "gemini-3.5-flash"
            status_code = 200
            status_label = "200 OK (정상 승인)"
            prompt_tokens = random.randint(140, 420)
            completion_tokens = random.randint(70, 210)
            total_tokens = prompt_tokens + completion_tokens
            p = PRICING[model]
            cost_usd = round(((prompt_tokens * p["input_usd_1m"]) + (completion_tokens * p["output_usd_1m"])) / 1_000_000.0, 6)
            unit_usd = round((p["input_usd_1m"] + p["output_usd_1m"]) / 2000.0, 6)
            cost_krw = round(cost_usd * p["krw_rate"], 2)
            prevented_usd = 0.0
            prevented_krw = 0.0
            policy = "Pass-Through (Authorized)"
            use_case = random.choice(use_cases_b_flash)

        else:  # b_blocked_pro (Apigee RaiseFault 403!)
            dept = DEPT_B
            model = "gemini-3.1-pro"
            status_code = 403
            status_label = "403 Forbidden (Apigee RaiseFault 차단)"
            prompt_tokens = 0
            completion_tokens = 0
            total_tokens = 0
            p = PRICING[model]
            unit_usd = round((p["input_usd_1m"] + p["output_usd_1m"]) / 2000.0, 6)
            cost_usd = 0.0
            cost_krw = 0.0
            would_be_tokens = random.randint(600, 1200)
            prevented_usd = round((would_be_tokens * p["output_usd_1m"]) / 1_000_000.0, 6)
            prevented_krw = round(prevented_usd * p["krw_rate"], 2)
            policy = "RF-UnauthorizedModel403"
            use_case = random.choice(use_cases_b_blocked)

        rows.append(
            {
                "timestamp": ts.isoformat(),
                "request_id": f"apigee-req-{uuid.uuid4().hex[:12]}",
                "department_id": dept["id"],
                "department_name": dept["name"],
                "model": model,
                "status_code": status_code,
                "status_label": status_label,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
                "unit_price_per_1k_usd": unit_usd,
                "estimated_cost_usd": cost_usd,
                "estimated_cost_krw": cost_krw,
                "prevented_cost_usd": prevented_usd,
                "prevented_cost_krw": prevented_krw,
                "apigee_policy": policy,
                "use_case": use_case,
            }
        )
    return rows


def provision_and_seed(project_id: str, seed_count: int = 0):
    print(f"[*] Initializing BigQuery Client for project: {project_id}")
    creds = get_gcloud_creds()
    client = bigquery.Client(
        project=project_id,
        credentials=creds,
        client_options={"quota_project_id": project_id},
    )

    dataset_ref = f"{project_id}.{DATASET_ID}"
    dataset = bigquery.Dataset(dataset_ref)
    dataset.location = "US"
    dataset.description = "Apigee AI Gateway Department x Model Token Usage & Chargeback Dataset"
    client.create_dataset(dataset, exists_ok=True)
    print(f"[+] Ensured BigQuery Dataset: {dataset_ref}")

    table_ref = f"{dataset_ref}.{TABLE_ID}"
    table = bigquery.Table(table_ref, schema=get_schema())
    table.time_partitioning = bigquery.TimePartitioning(
        type_=bigquery.TimePartitioningType.DAY, field="timestamp"
    )
    table.clustering_fields = ["department_name", "model", "status_code"]
    client.create_table(table, exists_ok=True)
    print(f"[+] Ensured BigQuery Table: {table_ref}")

    view_summary_sql = f"""
    CREATE OR REPLACE VIEW `{dataset_ref}.v_looker_dept_model_chargeback` AS
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
      ROUND(SUM(IF(status_code = 200, estimated_cost_usd, 0)), 6) AS total_chargeback_usd,
      ROUND(SUM(IF(status_code = 200, estimated_cost_krw, 0)), 2) AS total_chargeback_krw,
      ROUND(SUM(IF(status_code = 403, prevented_cost_usd, 0)), 6) AS total_prevented_cost_usd,
      ROUND(SUM(IF(status_code = 403, prevented_cost_krw, 0)), 2) AS total_prevented_cost_krw
    FROM
      `{dataset_ref}.{TABLE_ID}`
    GROUP BY
      department_id,
      department_name,
      model
    ORDER BY
      department_name ASC,
      model ASC;
    """
    client.query(view_summary_sql).result()
    print(f"[+] Created Looker Studio View: {dataset_ref}.v_looker_dept_model_chargeback")

    view_hourly_sql = f"""
    CREATE OR REPLACE VIEW `{dataset_ref}.v_looker_hourly_chargeback` AS
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
      `{dataset_ref}.{TABLE_ID}`
    GROUP BY
      usage_hour,
      department_name,
      model,
      status_code,
      status_label
    ORDER BY
      usage_hour DESC;
    """
    client.query(view_hourly_sql).result()
    print(f"[+] Created Looker Studio View: {dataset_ref}.v_looker_hourly_chargeback")


if __name__ == "__main__":
    target_project = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PROJECT
    provision_and_seed(target_project)
