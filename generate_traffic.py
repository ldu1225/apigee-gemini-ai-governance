#!/usr/bin/env python3
"""
Standalone Traffic Generator for Apigee x Gemini AI Governance & Chargeback Demo.

Supports two modes:
1. --mode bigquery (default): Directly loads N realistic enterprise traffic records
   into Google Cloud BigQuery (fast bulk load for Looker Studio charts).
2. --mode gateway: Sends real HTTP POST requests to the running Apigee Gateway
   (http://127.0.0.1:8080/v1/models:generateContent) across Department A (Battery Dev)
   and Department B (Quality Mgmt), triggering real Vertex AI Gemini calls & 403 blocks.
"""

import argparse
import os
import sys
import time
import urllib.request
import json
from google.cloud import bigquery
from bigquery.provision_bq import generate_seed_rows, get_schema, DEFAULT_PROJECT, DATASET_ID, TABLE_ID

GATEWAY_URL = "http://127.0.0.1:8080/v1/models:generateContent"

LIVE_SCENARIOS = [
    {
        "name": "A 부서 (AI 연구개발팀) - gemini-3.5-flash (200 OK)",
        "token": "dept-a-rnd-token-2026",
        "model": "gemini-3.5-flash",
        "prompt": "글로벌 클라우드 아키텍처 보안 감사 체크리스트 핵심 기준 1줄 요약해줘",
    },
    {
        "name": "A 부서 (AI 연구개발팀) - gemini-3.1-pro (200 OK)",
        "token": "dept-a-rnd-token-2026",
        "model": "gemini-3.1-pro",
        "prompt": "엔터프라이즈 마이크로서비스 장애 대응 매뉴얼 핵심 방안 1줄 요약해줘",
    },
    {
        "name": "B 부서 (품질관리팀) - gemini-3.5-flash (200 OK)",
        "token": "dept-b-quality-token-2026",
        "model": "gemini-3.5-flash",
        "prompt": "서비스 품질 점검 리포트(QA) 불량 판정 주요 기준 1줄 요약해줘",
    },
    {
        "name": "🚨 B 부서 (품질관리팀) - gemini-3.1-pro (403 Forbidden 차단 시연)",
        "token": "dept-b-quality-token-2026",
        "model": "gemini-3.1-pro",
        "prompt": "고단가 Gemini 3.1 Pro 모델을 무단으로 호출하여 전체 공정 원시 로그 일괄 추론 요청",
    },
]


def run_bigquery_bulk_seed(project_id: str, count: int):
    print(f"[*] Generating {count} realistic traffic records for BigQuery ({project_id}.{DATASET_ID}.{TABLE_ID})...")
    client = bigquery.Client(
        project=project_id,
        client_options={"quota_project_id": project_id},
    )
    table_ref = f"{project_id}.{DATASET_ID}.{TABLE_ID}"
    rows = generate_seed_rows(count)

    job_config = bigquery.LoadJobConfig(
        schema=get_schema(),
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
    )
    load_job = client.load_table_from_json(rows, table_ref, job_config=job_config)
    load_job.result()
    print(f"[+] Successfully inserted {len(rows)} records into BigQuery!")


def run_gateway_live_requests(count: int):
    print(f"[*] Sending {count} live HTTP requests to Apigee Gateway ({GATEWAY_URL})...")
    for i in range(count):
        sc = LIVE_SCENARIOS[i % len(LIVE_SCENARIOS)]
        payload = json.dumps({
            "model": sc["model"],
            "contents": [{"role": "user", "parts": [{"text": sc["prompt"]}]}],
        }).encode("utf-8")

        req = urllib.request.Request(
            GATEWAY_URL,
            data=payload,
            headers={
                "Authorization": f"Bearer {sc['token']}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                body = json.loads(resp.read().decode("utf-8"))
                tokens = body.get("usageMetadata", {}).get("totalTokenCount", 0)
                cost_krw = body.get("apigeeGovernanceMetadata", {}).get("chargebackKRW", 0)
                print(f"  [{i+1}/{count}] ✅ {sc['name']} -> HTTP {resp.status} (Tokens: {tokens:,}, Cost: ₩{cost_krw:,})")
        except urllib.error.HTTPError as e:
            err_body = json.loads(e.read().decode("utf-8"))
            msg = err_body.get("error", {}).get("message", "")
            print(f"  [{i+1}/{count}] 🛑 {sc['name']} -> HTTP {e.code} Forbidden! ({msg})")
        except Exception as e:
            print(f"  [{i+1}/{count}] ⚠️ Request error: {e}")
        time.sleep(0.3)
    print("[+] Completed live Gateway traffic simulation!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate demo traffic for Apigee x Gemini Governance Demo")
    parser.add_argument("--mode", choices=["bigquery", "gateway"], default="bigquery",
                        help="'bigquery' for instant BigQuery bulk insert, 'gateway' for real HTTP calls through Apigee Gateway")
    parser.add_argument("--count", type=int, default=30, help="Number of traffic records/requests to generate")
    parser.add_argument("--project", type=str, default=DEFAULT_PROJECT, help="GCP Project ID")
    args = parser.parse_args()

    if args.mode == "gateway":
        run_gateway_live_requests(args.count)
    else:
        run_bigquery_bulk_seed(args.project, args.count)
