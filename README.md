# 🚀 Google Cloud Apigee x Gemini AI Governance & Real-Time Chargeback

> **엔터프라이즈 AI 게이트웨이 거버넌스 및 실시간 부서별 비용 정산(Chargeback) 참조 아키텍처**  
> Google Cloud **Apigee API Management**, **Vertex AI (Gemini 3.5 Flash & 3.1 Pro)**, **BigQuery**, 및 **Looker Studio**를 결합하여 **코드 변경 없는 부서별 모델 접근 제어(RBAC)**와 **실시간 토큰 사용량·비용 정산 대시보드**를 구현한 엔드투엔드 데모 솔루션입니다.

---

## 📌 1. 핵심 해결 과제 (Business Challenge)

기업 내 여러 부서가 생성형 AI(Gemini)를 도입할 때 다음과 같은 운영 및 보안 과제가 발생합니다:
1. **무분별한 고단가 모델 호출로 인한 비용 급증**: 단순 요약·분류 업무에도 고단가 추론 모델(`gemini-3.1-pro`)을 호출하여 예산 초과 발생
2. **애플리케이션별 개별 로깅 코드 중복 개발**: 현업 개발자가 매번 토큰 수를 계산하고 DB에 적재하는 코드를 직접 작성해야 하는 부담
3. **부서별 명확한 비용 정산(Chargeback) 부재**: 어느 부서가 어떤 모델을 얼마나 호출했는지 실시간으로 파악하기 어려움

본 리포지토리는 **Apigee AI Gateway**를 단일 진입점(Single Entrypoint)으로 배치하여 현업 개발자의 코드 변경 없이 위 3가지 문제를 동시에 해결하는 아키텍처를 제공합니다.

---

## 🏗️ 2. 전체 아키텍처 및 데이터 파이프라인

```mermaid
graph LR
    subgraph Clients["1. 부서별 클라이언트 요청"]
      A["A 부서 (AI 연구개발팀)\nToken: dept-a-rnd-token-2026\n허용: 3.5 Flash + 3.1 Pro"]
      B["B 부서 (품질관리팀)\nToken: dept-b-quality-token-2026\n허용: 3.5 Flash 전용"]
    end

    subgraph Apigee["2. Apigee AI Gateway (단일 URL)"]
      EV["ExtractVariables 정책\n(EV-ExtractModelAndDept.xml)\n헤더 토큰 & JSON $.model 추출"]
      RF["RaiseFault 403 정책\n(RF-UnauthorizedModel403.xml)\nB부서 Pro 호출 시 즉시 차단"]
      SC["ServiceCallout 정책\n(SC-BigQueryLogUsage.xml)\n비동기 실시간 토큰/비용 전송"]
    end

    subgraph Backend["3. Google Cloud Backend"]
      Vertex["Vertex AI Gemini\ngemini-3.5-flash / gemini-3.1-pro\n(usageMetadata 토큰 반환)"]
      BQ[("BigQuery\napigee_ai_governance\n.llm_token_usage")]
      Looker["Looker Studio\n부서 × 모델 실시간 정산 대시보드"]
    end

    A & B -->|"POST /v1/models:generateContent"| EV
    EV -->|"RBAC 조건 검사"| RF
    RF -->|"403 Forbidden (비용 $0)"| B
    EV -->|"200 OK 인가 요청"| Vertex
    Vertex -->|"usageMetadata (토큰 수)"| SC
    SC -->|"Streaming Insert"| BQ
    BQ -->|"v_looker_dept_model_chargeback"| Looker
```

---

## 🎬 3. 데모 시나리오 (부서별 모델 RBAC 및 비용 정산)

| 구분 | 부서명 | API 토큰 (`Authorization: Bearer`) | 허용 모델 | 비허용 모델 | 시연 결과 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **A 부서** | **AI 연구개발팀** | `dept-a-rnd-token-2026` | `gemini-3.5-flash`<br>`gemini-3.1-pro` | 없음 | 두 모델 모두 **200 OK** 응답 및 BigQuery 실시간 정산 |
| **B 부서** | **품질관리팀** | `dept-b-quality-token-2026` | `gemini-3.5-flash` | `gemini-3.1-pro` | Flash는 **200 OK**, Pro 호출 시 **403 Forbidden 즉시 차단** |

### 단계별 시연 흐름
1. **1단계: 개발자 편의성 시연 (Zero-Code Logging)**
   - 현업 개발자는 표준 Gemini REST API 규격(`{"model": "gemini-3.5-flash", "contents": [...]}`) 그대로 Apigee Gateway URL과 부서 토큰만 지정하여 호출합니다.
   - 별도의 토큰 측정·로깅 코드를 작성할 필요가 전혀 없습니다.
2. **2단계: Apigee RaiseFault 정책을 통한 비인가 모델 원천 차단**
   - **시연 2-A**: B 부서(품질관리팀)가 허용된 `gemini-3.5-flash` 호출 ➔ **200 OK 정상 응답**
   - **시연 2-B**: B 부서(품질관리팀)가 고단가 `gemini-3.1-pro` 무단 호출 ➔ **Vertex AI 도달 전 Apigee에서 즉시 403 Forbidden 차단**
   - 차단 메시지: `"Access Denied: Quality Dept is not authorized to call [gemini-3.1-pro]."` (백엔드 토큰 과금 원천 차단)
3. **3단계: BigQuery & Looker Studio 실시간 정산(Chargeback) 대시보드**
   - Vertex AI 공식 단가(`gemini-3.5-flash`: Input $0.15/1M, Output $0.60/1M / `gemini-3.1-pro`: Input $1.25/1M, Output $5.00/1M)를 기반으로 부서별·모델별 누적 토큰 사용량, 정산 금액(USD/KRW), 403 차단으로 절감한 비용(Prevented Cost)을 실시간 시각화합니다.

---

## 📂 4. 디렉토리 구조

```text
.
├── apigee-proxy/
│   ├── deploy_to_apigee.py                     # Apigee X 환경/프록시 번들 자동 패키징 및 배포 스크립트
│   └── apiproxy/                               # Apigee X 표준 API Proxy XML 번들
│       ├── gemini-ai-governance.xml            # 프록시 매니페스트
│       ├── policies/
│       │   ├── EV-ExtractModelAndDept.xml      # Authorization 헤더 및 JSON Body $.model 추출
│       │   ├── RF-UnauthorizedModel403.xml     # B부서 Pro 호출 시 403 Forbidden 차단 정책
│       │   └── SC-BigQueryLogUsage.xml         # BigQuery 실시간 스트리밍 적재 정책
│       ├── proxies/
│       │   └── default.xml                     # PreFlow RBAC 조건문 및 PostFlow BigQuery 로깅 정의
│       └── targets/
│           └── default.xml                     # Vertex AI Gemini 엔드포인트 연결 설정
├── bigquery/
│   ├── setup_bigquery.sql                      # BigQuery 테이블 및 Looker Studio 전용 뷰 DDL
│   └── provision_bq.py                         # BigQuery 데이터셋/테이블/뷰 자동 생성 및 시드 생성기
├── gateway-service/
│   ├── main.py                                 # FastAPI 기반 Apigee Gateway 시뮬레이터 & Vertex AI/BigQuery 연동 서버
│   ├── index.html                              # 4단 수평 아키텍처 파이프라인 & 인터랙티브 코드 인스펙터 웹 UI
│   ├── requirements.txt                        # Python 의존성 목록
│   └── Dockerfile                              # Cloud Run 배포용 컨테이너 이미지 정의
├── postman/
│   └── Apigee_Gemini_Governance_Demo.postman_collection.json # Postman 원클릭 시연 컬렉션
├── generate_traffic.py                         # CLI 기반 실시간 게이트웨이/BigQuery 트래픽 생성기
└── deploy.sh                                   # 원클릭 BigQuery 프로비저닝 및 로컬 웹 서버 실행 스크립트
```

---

## ⚡ 5. 빠른 시작 (Quick Start)

### 사전 준비 사항
- Google Cloud SDK (`gcloud`) 설치 및 인증 완료
- Python 3.10 이상
- 대상 Google Cloud 프로젝트에서 Vertex AI API 및 BigQuery API 활성화

```bash
# 1. Google Cloud 인증 및 프로젝트 환경변수 설정
gcloud auth login
gcloud auth application-default login
export GCP_PROJECT_ID="your-gcp-project-id"

# 2. 의존성 패키지 설치
pip install -r gateway-service/requirements.txt

# 3. 원클릭 BigQuery 프로비저닝 및 인터랙티브 데모 서버 실행
chmod +x deploy.sh
./deploy.sh "$GCP_PROJECT_ID"
```

서버가 시작되면 브라우저에서 **`http://127.0.0.1:8080`** 에 접속하여 실시간 4단 아키텍처 파이프라인, 코드/헤더 인스펙터, 시나리오별 원클릭 호출 시연기, BigQuery 실시간 정산 대시보드를 확인할 수 있습니다.

---

## 🧪 6. cURL 및 CLI 테스트 가이드

### ① A 부서 (AI 연구개발팀) - `gemini-3.5-flash` 호출 (200 OK)
```bash
curl -X POST http://127.0.0.1:8080/v1/models:generateContent \
  -H "Authorization: Bearer dept-a-rnd-token-2026" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemini-3.5-flash",
    "contents": [{"role": "user", "parts": [{"text": "글로벌 클라우드 아키텍처 보안 감사 체크리스트 1줄 요약해줘"}]}]
  }'
```

### ② A 부서 (AI 연구개발팀) - `gemini-3.1-pro` 호출 (200 OK)
```bash
curl -X POST http://127.0.0.1:8080/v1/models:generateContent \
  -H "Authorization: Bearer dept-a-rnd-token-2026" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemini-3.1-pro",
    "contents": [{"role": "user", "parts": [{"text": "엔터프라이즈 마이크로서비스 장애 대응 매뉴얼 핵심 요약해줘"}]}]
  }'
```

### ③ B 부서 (품질관리팀) - `gemini-3.1-pro` 무단 호출 (403 Forbidden 차단)
```bash
curl -i -X POST http://127.0.0.1:8080/v1/models:generateContent \
  -H "Authorization: Bearer dept-b-quality-token-2026" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemini-3.1-pro",
    "contents": [{"role": "user", "parts": [{"text": "무단 고단가 Pro 모델 추론 요청"}]}]
  }'
```
**응답 예시 (HTTP 403 Forbidden):**
```json
{
  "error": {
    "code": 403,
    "status": "PERMISSION_DENIED",
    "message": "Access Denied: Quality Dept is not authorized to call [gemini-3.1-pro].",
    "policy": "RF-UnauthorizedModel403",
    "gateway": "Google Cloud Apigee X AI Gateway"
  }
}
```

---

## 📊 7. Looker Studio 연동 가이드

BigQuery에 자동 생성된 **`apigee_ai_governance.v_looker_dept_model_chargeback`** 뷰를 Looker Studio 데이터 소스로 연결하면 즉시 부서별·모델별 실시간 정산 리포트를 구성할 수 있습니다.

1. [Looker Studio](https://lookerstudio.google.com/) 접속 ➔ **[만들기]** ➔ **[데이터 소스]** 클릭
2. **BigQuery** 커넥터 선택 ➔ 프로젝트(`your-gcp-project-id`) ➔ 데이터세트(`apigee_ai_governance`) ➔ 뷰(**`v_looker_dept_model_chargeback`**) 선택
3. 주요 측정기준 및 지표 설정:
   - **측정기준(Dimension)**: `department_name` (부서명), `model` (모델명)
   - **측정항목(Metric)**: `total_tokens` (총 토큰 수), `total_chargeback_krw` (정산 금액 ₩), `blocked_403_calls` (Apigee 403 차단 건수), `total_prevented_cost_krw` (사전 차단 절감액 ₩)

---

## ☁️ 8. Apigee X 실제 배포 및 Cloud Run 배포 (선택 사항)

### Apigee X Organization에 프록시 번들 배포
```bash
export GCP_PROJECT_ID="your-gcp-project-id"
python3 apigee-proxy/deploy_to_apigee.py
```

### Google Cloud Run에 데모 웹 콘솔 배포
```bash
gcloud run deploy apigee-gemini-governance \
  --source ./gateway-service \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars="GCP_PROJECT_ID=your-gcp-project-id"
```
