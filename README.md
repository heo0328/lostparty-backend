# LostParty Backend

문서는 [문서 안내](docs/README.md)에서 기능별로 찾아볼 수 있습니다.

활성 사용자 기능에서 미완료 종료·같은 주차 재개를 제외하며, 구 API/이력·원 pending/ACK는 [IF-001 비활성 보존 기준](docs/reference/INACTIVE_FEATURES.md)에 따라 유지합니다.

로스트파티(LostParty) 모바일 앱의 백엔드 프로젝트입니다. Firebase 기반으로 서버 기능을 구현하고 테스트하던 중, 더 다양한 기능을 추가하고 유연하게 운영하기 위해 자체 백엔드 서버 개발을 시작했습니다.

Flutter 앱은 별도의 Windows 개발 환경과 GitHub 저장소에서 개발합니다. 이 저장소는 백엔드 구현과 OpenAPI 계약을 관리하며, 양쪽 저장소는 GitHub Issues와 API 계약을 기준으로 협업합니다.

현재 Google 인증·회원/원정대 등록과 갱신·장비 소유 인증·캐릭터 활동/대표/개인 설정, 카탈로그·서버 주차·개인 주간 원장, 그룹 G1/G2와 회원 한도, 소유권 분쟁 V2 및 첫 화면 일괄 저장 조회를 구현했습니다. 현재 로컬 Docker API8000/DB0031·두 주차 모집 factory로 개발하며, 기능별 Backend 완료·Flutter 적용·실기기 확인 범위는 [기능 지도](docs/project/AI_CONTEXT.md)를 따릅니다. 실제 로그인/최초 장비 인증과 일괄 조회의 사용자 기기 로그를 확인했으며 모든 기능의 실기기 인수를 뜻하지는 않습니다. AWS Lightsail 운영 배포는 후속입니다.

## Flutter와 API 계약 협업

작업 원칙은 [AGENTS.md](AGENTS.md), 상세 흐름은 [개발 작업 규칙](docs/guides/DEVELOPMENT_WORKFLOW.md)과 [API 협업 규칙](docs/guides/API_COLLABORATION.md)에 정리합니다.

현재 두 주차 개발 서버의 실행 계약은 `openapi/two-cycle.openapi.yaml`이며, 기본0023 앱 계약은 `openapi/openapi.yaml`에 보존합니다. 현재 계약은 인증·회원/원정대·캐릭터·주간 원장·그룹·소유권 분쟁·일괄 조회 API를 정의합니다. 일괄 조회 범위·읽기 스냅샷/크기 제한은 [개발 안내](docs/features/account/ISSUE_8_ACCOUNT_BOOTSTRAP_DEVELOPMENT.md)에 있습니다.

API 추가·변경은 GitHub Issues에서 요청·응답과 호환성 영향을 합의하고 관련 Flutter Issue/PR을 연결합니다. Backend 구현과 계약은 함께 변경하며, 현재 개발 API를 갱신한 뒤 `python3 scripts/check_openapi.py --docker docker.exe --container lostparty-backend-api-1 --profile two-cycle`로 일치 여부를 검증합니다.

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
| API 계약 | OpenAPI 3.1 — 현재 두 주차 `openapi/two-cycle.openapi.yaml`, 기본 앱 `openapi/openapi.yaml` |
| 버전 관리와 협업 | Git / GitHub Issues / OpenAPI 계약 |
| 모바일 앱 | Flutter — 별도의 Windows 환경과 저장소에서 개발 |
| 배포 예정 환경 | AWS Lightsail Linux 서버 — 아직 배포하지 않음 |

WSL의 시스템 Python 3.14는 유지하며 백엔드는 Docker의 Python 3.12로 실행합니다. Python 라이브러리의 직접 의존성 버전은 `requirements.txt`, 컨테이너 구성은 `Dockerfile`과 `compose.yaml`에서 관리합니다.

로컬 DB 확인용 클라이언트는 `127.0.0.1:5432`로 접속합니다. `compose.yaml`은 이 주소를 DB 컨테이너의 PostgreSQL 5432 포트에 연결하며, 접속 계정과 비밀번호는 로컬 설정을 사용합니다.

현재 작업은 [NEXT_WORK](docs/project/NEXT_WORK.md), 개발 이력은 [DEV_LOG](docs/project/DEV_LOG.md), 프로젝트 지도는 [AI_CONTEXT](docs/project/AI_CONTEXT.md)에서 확인합니다.

현재 DB0031 개발 API 재기동은 다음 구성을 사용합니다. 기본 Compose 단독은0023 앱이므로 현재 DB와 혼용하지 않습니다. [실제 전환/보존·복구 경계](docs/features/recruitment/development/ISSUE_24_25_DEVELOPMENT_ROLLOUT.md)를 따릅니다.

```bash
docker.exe compose -f compose.yaml -f compose.two-cycle.yaml up -d --no-deps --build --wait --wait-timeout 180 api
```
