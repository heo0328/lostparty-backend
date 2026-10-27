# LostParty Backend

로스트아크의 원정대·캐릭터와 레이드 모집·일정을 관리하는 LostParty 모바일 앱의 백엔드입니다. Firebase 기반 개발에서 출발해 기능 확장과 데이터·권한 처리를 직접 관리하기 위한 자체 서버를 개발하고 있습니다.

## 주요 기능

- **로그인·계정:** Google 인증, 세션 관리, 회원 설정과 개인 API 키.
- **원정대·캐릭터:** 등록·소유 인증, 대표·활동 선택, 전투력·분석 요약과 표시 설정.
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

## 개발·협업 방식

[Flutter 앱](https://github.com/heo0328/LostParty_flutter)은 별도 저장소에서 개발합니다. [GitHub Issues](https://github.com/heo0328/lostparty-backend/issues)로 요구사항과 변경 영향을 협의하고, OpenAPI 계약을 기준으로 독립 구현·연동합니다. 백엔드 구현과 계약의 일치, 권한·동시성·트랜잭션 동작을 검증하며 자동 시험과 실제 기기 확인을 구분합니다.

## 개발 상태·문서

현재 개발 중이며 주요 기능의 백엔드 구현과 Flutter 연동을 진행하고 있습니다. [모집·일정 통합 체크포인트](docs/features/recruitment/integration-checkpoint-2026-10-27.md)에 현재까지의 구현·검증·개발 서버 반영·dev/main 통합과 남은 인수 및 새 후속 조사를 정리했습니다. 기능별 연결·실회원·기기 인수는 별도로 추적하며 AWS 운영 배포는 후속입니다.

[기능별 문서 안내](docs/README.md) · [현재 기능 상태](docs/project/AI_CONTEXT.md) · [다음 작업](docs/project/NEXT_WORK.md) · [개발 환경](docs/engineering/development/environment.md) · [협업 규칙](docs/engineering/collaboration/api-collaboration.md)
