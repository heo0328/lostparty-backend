# #24/#25 개발 API·DB0031 반영

2026-10-24 / Backend / feat/raid-recruitment / 구현 source `15e143aeb9f3105a1b8a5816051e0e837726892c`.

사용자의 다음 구간 진행 지시에 따라 기존 로컬 개발 서버를0030→0031로 이행하고 API·동일 lifespan의 worker를 교체했다. [집계 증거](../artifacts/issue24-25-development-rollout.json) · [구현 계약](ISSUE_24_25_MEMBERSHIP_ACTIONS_DEVELOPMENT.md).

## 반영과 보존

- 기존 API/worker를 정지한 뒤 다른 실행 중 DB 쿼리가 없음을 확인하고106표603행의 비공개 checkpoint·pg_dump·인증 키·환경/실행 설정을 보관했다. `backups/membership0031-7edffda86ab7`은0700/0600이며 Git/Docker build 제외다. 원본 자료·키·환경은 게시하지 않는다.
- 별도 internal network/tmpfs PostgreSQL에 백업을 제한 LOGIN으로 복원했다. 복원 지문 일치→명시 `alembic upgrade 0031_membership_actions`→기존105개 업무 표의 모든 행/열 정의/기록 시각 및 시퀀스·키 보존→비관리자 readiness를 검증했다. 앱 모델 등록 전 단독 검사에서 발생한 NullType은 앱 factory를 먼저 구성해 해결했으며 migration/자료 보존 실패가 아니었다.
- 실제 DB도 같은 제한 LOGIN·검증 이미지로 정확0031 이행했다. 두 표와 현재 CM/Assignment partial unique를 추가했고 기존 행을 재작성하지 않았다.106→108표, 총603행 유지, 새 감사/복구 표0행이다. 기존 업무 표105개의 내용/열/기록 시각·시퀀스·키를 복원 리허설/실제 이행/worker 기동 후 각각 대조했다.
- 이미지 app/alembic Python 및 설정236파일이 workspace와 일치함을 교체 전에 확인했다. 실행 이미지 `sha256:67322372b0e7a92344e62e37b06d06e97f1cbc097d0b8fcaffeab49d86695db6`. 이전 이미지92490ff3…를 `lostparty-backend-api:before-membership0031`로 보존했다.
- compose.yaml+compose.two-cycle.yaml의 `--no-deps --no-build --wait`로 API만 교체했다. DB 컨테이너/볼륨은 동일하고 환경 값(순서 정규화), factory/포트/보안/읽기 전용 키 mount와 키 내용이 일치한다. 이전 worker를 새 DB에 기동하거나 downgrade/백업 덮어쓰기를 하지 않았다. 새 쓰기 이후 이전 checkpoint로 되돌려 새 자료를 버리지 않는다.
- 임시 source reader/migration runner/복원 DB·network를 제거했다. 현재 기존 프로젝트 API/DB 두 컨테이너만 healthy다.

## 실제 확인과 한계

실행 컨테이너의 two-cycle176/기본116 OpenAPI 전체 객체 비교가 통과했다. 실제 HTTP health200·C/N 공개검색200/no-store·새 Context/POST 각각 무인증/잘못된 Bearer401 ACCESS_INVALID/WWW-Authenticate/no-store, 총7검사를 통과했다. 최초 검색 probe는 필수 필드 누락400이었고 게시 계약의 전체 필드로 고쳐 두 검색을 확인했다.0031 readiness는 NOSUPERUSER/NOCREATEDB/NOCREATEROLE LOGIN에서 통과했다.

직전 합성 DB 고유38PASS는 구현 검증 근거이며 이번 실서버 검사와 합산하지 않는다. 실제 로그인한 회원의 명령·탈퇴/해산·기기 인수는 실행하지 않았다. Flutter는 게시 source/176계약을 연결하고 정상 로그인으로 신규 메뉴/명령·profile/종료 기록·선택T 검색의 직접 영향 범위를 확인해 #24/#25에 결과를 회신한다. 실제 자료를 변경하는 사용자 시나리오는 네이티브/사용자 인수 범위다.

IF-001 앱 비활성·기존 서버 권한/endpoint·원 pending/24h ACK는 유지한다. recover_leadership UX는 별도 제품 승인 전 제안이다. #13/#24/#25 OPEN이며 dev/main 병합·AWS 운영 배포·실기기 전체 인수 완료를 뜻하지 않는다. 재기동은 기존 compose.yaml+compose.two-cycle.yaml을 사용하며 이 파일 자체가 migration을 실행하지는 않는다.

게시: 전환 기록 `920cc059e5c15a88a8c35e529ebd821af253fc20` commit/push·원격 확인 뒤 [#24 전체5번째 Backend · 개발 반영 완료](https://github.com/heo0328/lostparty-backend/issues/24#issuecomment-6371617690)·[#25 전체7번째 Backend · 개발 반영 완료](https://github.com/heo0328/lostparty-backend/issues/25#issuecomment-6371618996) 회신·전문/전체 순번을 검증했다. 다음 담당 Flutter 연결·자동 검증/정상 로그인 인수, Backend 차이 대응이다.
