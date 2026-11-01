# LostParty Backend

Lightsail 신규 서버 설치·무료 서브도메인 HTTPS 준비는 [첫 배포 절차](docs/engineering/operations/lightsail-first-deploy.md)를 따릅니다. `compose.lightsail.yaml`은 로컬 Compose와 합치지 않는 독립 구성입니다. 실제 운영 배포 완료를 의미하지 않습니다.

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

## 개발·협업 방식

[Flutter 앱](https://github.com/heo0328/LostParty_flutter)은 별도 저장소에서 개발합니다. [GitHub Issues](https://github.com/heo0328/lostparty-backend/issues)로 요구사항과 변경 영향을 협의하고, OpenAPI 계약을 기준으로 독립 구현·연동합니다. 백엔드 구현과 계약의 일치, 권한·동시성·트랜잭션 동작을 검증하며 자동 시험과 실제 기기 확인을 구분합니다.

## 개발 상태·문서

레이드 모집·일정과 그룹 기능은 1차 구현, Flutter 연동 및 안내된 범위의 사용자 기기 인수를 완료했습니다. 현재는 소유권 분쟁의 최종 이전에 따른 그룹·레이드 영향 처리 정책을 협의하고 있습니다. 편의성 개선과 공개 베타 준비·운영 검증·AWS 배포는 후속 작업으로 관리합니다.

최신 기능별 완료·미완료 범위는 [현재 기능 상태](docs/project/AI_CONTEXT.md), 진행할 작업과 협의 사항은 [다음 작업](docs/project/NEXT_WORK.md)에서 확인할 수 있습니다.

[기능별 문서 안내](docs/README.md) · [현재 기능 상태](docs/project/AI_CONTEXT.md) · [다음 작업](docs/project/NEXT_WORK.md) · [개발 환경](docs/engineering/development/environment.md) · [협업 규칙](docs/engineering/collaboration/api-collaboration.md)
