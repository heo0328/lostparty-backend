# LostParty Backend

운영 상태·최근 로그·API만 재시작하는 명령과 자동 시작/백업 현황은 [Lightsail 짧은 운영 안내](docs/engineering/operations/lightsail-quick-ops.md)를 참고하세요.

Lightsail 신규 서버 설치·무료 서브도메인 HTTPS 준비는 [첫 배포 절차](docs/engineering/operations/lightsail-first-deploy.md)를 따릅니다. `compose.lightsail.yaml`은 로컬 Compose와 합치지 않는 독립 구성입니다. 첫 Lightsail 설치·HTTPS 공개 결과와 남은 앱/운영 검증은 [배포 기록](docs/project/DEV_LOG.md#lightsail-rollout)을 따릅니다.

로스트아크의 원정대·캐릭터와 레이드 모집·일정을 관리하는 LostParty 모바일 앱의 백엔드입니다. Firebase 기반 개발에서 출발해 기능 확장과 데이터·권한 처리를 직접 관리하기 위한 자체 서버를 개발하고 있습니다.

## 주요 기능

- **로그인·계정:** Google 인증, 세션 관리, 회원 설정과 개인 API 키.
- **원정대·캐릭터:** 등록·소유 인증, 24시간 소유권 도전·방어, 대표·활동 선택, 전투력·분석 요약과 표시 설정.
- **레이드·주간 기록:** 레이드 카탈로그, 서버 주차 기준과 개인 완료 기록.
- **그룹:** 생성·검색, 초대·가입과 멤버 관리.
- **모집·일정:** 현재주·다음주 모집, 참가·일정 조율, 완료·기록과 관계 정리.

## 기술 구성

| 구분 | 기술 |
|---|---|
| 언어·웹 서버 | Python 3.12, FastAPI, Uvicorn |
| 데이터 | PostgreSQL 17, SQLAlchemy, psycopg, Alembic |
| 인증·암호화 | google-auth, PyJWT, cryptography |
| 실행·검증 | Docker Compose, pytest, OpenAPI 3.1, JSON Schema |

의존성 버전은 [requirements.txt](requirements.txt)와 [requirements-dev.txt](requirements-dev.txt)에서 관리합니다.

## 로컬 실행과 API 명세

준비된 개발 DB에서는 `docker compose up -d --no-deps --build --wait api`로 현재 서버를 시작합니다. 기본 시작점은 `app.main:app`이며 별도 two-cycle 설정은 필요하지 않습니다. 빈 DB는 자동 준비되지 않으므로 [개발 환경 안내](docs/engineering/development/environment.md)를 먼저 따릅니다.

[현재 OpenAPI 명세](openapi/openapi.yaml)는 Native 협업과 전체 계약 검증의 기준입니다. [legacy 명세](openapi/legacy.openapi.yaml)는 과거 DB0023 시험용으로 보존합니다. Swagger UI·외부 명세 웹페이지는 아직 연결하지 않았습니다. [이름 대응과 유지 이유](docs/engineering/development/runtime-configuration.md)에서 실행과 DB 변경 번호를 구분합니다.

## 개발·협업 방식

[Flutter 앱](https://github.com/heo0328/LostParty_flutter)은 별도 저장소에서 개발합니다. [GitHub Issues](https://github.com/heo0328/lostparty-backend/issues)로 요구사항과 변경 영향을 협의하고, OpenAPI 계약을 기준으로 독립 구현·연동합니다. 백엔드 구현과 계약의 일치, 권한·동시성·트랜잭션 동작을 검증하며 자동 시험과 실제 기기 확인을 구분합니다.

## 개발 상태·문서

레이드 모집·일정과 그룹1차, 묶음 선택 완료(#47)·복구 안내/일정 읽기(#48)·모집 탐색 개선(#50)은 합의 범위의 양측 구현과 협업 마감을 완료했습니다. 기본 실행과 현재·legacy 명세 이름을 정리하고 로컬 개발 서버에 반영했습니다. #17 잔여 범위와 소유권 이전 영향(#15)·활동 자동추가(#18)·통계(#19)는 별도 선택 후속입니다. 로컬 개발과 AWS 운영은 구분합니다.

최신 기능별 완료·미완료 범위는 [현재 기능 상태](docs/project/AI_CONTEXT.md), 진행할 작업과 협의 사항은 [다음 작업](docs/project/NEXT_WORK.md)에서 확인할 수 있습니다.

[기능별 문서 안내](docs/README.md) · [현재 기능 상태](docs/project/AI_CONTEXT.md) · [다음 작업](docs/project/NEXT_WORK.md) · [개발 환경](docs/engineering/development/environment.md) · [협업 규칙](docs/engineering/collaboration/api-collaboration.md)
