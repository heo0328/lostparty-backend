# LostParty Backend

로스트파티(LostParty) 모바일 앱의 백엔드 프로젝트입니다. Firebase 기반으로 서버 기능을 구현하고 테스트하던 중, 더 다양한 기능을 추가하고 유연하게 운영하기 위해 자체 백엔드 서버 개발을 시작했습니다.

Flutter 앱은 별도의 Windows 개발 환경과 GitHub 저장소에서 개발합니다. 이 저장소는 백엔드 구현과 OpenAPI 계약을 관리하며, 양쪽 저장소는 GitHub Issues와 API 계약을 기준으로 협업합니다.

현재는 `/health`와 Google 인증·회원 조회·세션 갱신·로그아웃 API가 구현되어 있습니다. 실제 Google·Flutter 연동 검증은 후속 단계이며, AWS Lightsail의 Linux 서버에 배포할 예정입니다. 실행·검증 방법은 [인증 개발 안내](docs/AUTH_DEVELOPMENT.md)에 있습니다.

## Flutter와 API 계약 협업

작업 원칙은 [AGENTS.md](AGENTS.md), 상세 흐름은 [개발 작업 규칙](docs/DEVELOPMENT_WORKFLOW.md)과 [API 협업 규칙](docs/API_COLLABORATION.md)에 정리합니다.

OpenAPI 계약의 원본은 이 저장소의 `openapi/openapi.yaml`입니다. 현재 계약은 `/health`와 Issue #2의 6개 인증 API를 정의합니다.

API 추가·변경은 GitHub Issues에서 요청·응답과 호환성 영향을 합의하고 관련 Flutter Issue/PR을 연결합니다. Backend 구현과 계약은 함께 변경하며, Docker API를 갱신한 뒤 `python3 scripts/check_openapi.py`로 일치 여부를 검증합니다.

Flutter는 합의된 계약의 커밋을 기준으로 연동합니다. 버그 보고에는 계약 커밋과 재현 요청·응답을 포함하며 비밀정보는 제외합니다.

## 개발 환경과 기술 구성

| 구분 | 구성 |
|---|---|
| 백엔드 개발 환경 | Ubuntu WSL2 / Bash |
| 백엔드 언어 | Python 3.12 — 프로젝트 기준 버전 |
| 프레임워크 / 서버 | FastAPI / Uvicorn |
| 데이터베이스 / 드라이버 | PostgreSQL 17 / psycopg 3 |
| 기본 실행 환경 | Docker Compose — API와 DB를 컨테이너로 실행 |
| 컨테이너 플랫폼 | Linux amd64 |
| API 계약 | OpenAPI 3.1 — `openapi/openapi.yaml`이 원본 |
| 버전 관리와 협업 | Git / GitHub Issues / OpenAPI 계약 |
| 모바일 앱 | Flutter — 별도의 Windows 환경과 저장소에서 개발 |
| 배포 예정 환경 | AWS Lightsail Linux 서버 — 아직 배포하지 않음 |

WSL의 시스템 Python 3.14는 유지하며 백엔드는 Docker의 Python 3.12로 실행합니다. Python 라이브러리의 직접 의존성 버전은 `requirements.txt`, 컨테이너 구성은 `Dockerfile`과 `compose.yaml`에서 관리합니다.
