# 영구 개발 이력

핵심 변경·결정·검증·장애를 날짜와 작업 제목으로 누적합니다. 현재 실행 계획은 [NEXT_WORK](NEXT_WORK.md), 기능 지도는 [AI_CONTEXT](AI_CONTEXT.md)에 둡니다. 비밀정보·개인정보·원시 로그를 첨부하지 않습니다.

## 2026-10-14 — Google 인증·복구 세션 구현과 로컬 커밋

### 목적·변경·결정

[Issue #2 최종 동의](https://github.com/heo0328/lostparty-backend/issues/2#issuecomment-6149615842)에 따라 6개 인증 API, 회원/identity/transaction/session/credential/recovery 모델, additive migration `0001_auth`, 테스트 환경과 원본 OpenAPI를 구현했습니다. 코드 위치는 `app/auth`, `app/core`, `alembic`, `tests`; 실행 방법은 [인증 개발 안내](../AUTH_DEVELOPMENT.md), 설계 근거는 [계약](../ISSUE_2_AUTH_CONTRACT_DRAFT.md)과 [복구 설계](../ISSUE_2_REFRESH_RECOVERY.md)입니다.

TTL·거래별 nonce·refresh 60초/추가2회·DB 시간 계측 제약은 합의됐습니다. 자세한 장기 정책은 위 계약 문서에서 관리합니다. 자체 인증을 추가해 Google proof를 일반 API의 Bearer로 쓰지 않고 세션 폐기를 서버가 검증하도록 했습니다.

### 새로 가능해진 흐름

challenge → Google 증거 검증 → 최초 회원 생성/동일 identity 재로그인 → 자체 세션 발급, 본인·현재 세션 조회, 회전과 동일 요청 복구, 현재 기기 로그아웃·만료 정리. 자동 검증은 모의 Google 증거에 기반하며 실제 Google 로그인 성공을 뜻하지 않습니다.

### 보존 확인한 기존 흐름

기존 /health의 경로·200/503 계약 유지 및 실제 200 응답, 기존 개발 DB 테이블 행 수 보존, DB volume 유지. Firebase·Flutter 로컬 자료를 수정하거나 신규 guest 회원을 생성하지 않았습니다.

### 실행한 검증·결과

- 개발과 분리된 PostgreSQL 17에서 **44개 pytest 통과**. `tests/test_auth.py`, `tests/test_google.py`에 검증 코드가 있습니다.
- 동시 첫 가입 중복 방지, refresh 회전·응답 유실·재전송 제한·replay 폐기 commit, 만료 equality·commit 지연·rollback·logout·정지·정리·키 오류 검증.
- Google 증거는 로컬 RSA 서명·모의 공개키 전송으로 signature/issuer/audience/iat/exp/nonce/azp 검사. 실제 Google는 미검증.
- OpenAPI 전체 비교, pip check, git diff --check·민감정보 검사 통과. 실제 HTTP /health 200·challenge 201/no-store·미인증 me 401·잘못된 refresh 400 확인.
- [구현 결과 댓글](https://github.com/heo0328/lostparty-backend/issues/2#issuecomment-6150036341)에 당시 결과를 기록했습니다.

### 장애와 한계

이번 변경의 첫 pytest 수집은 app 모듈 경로 미설정으로 실패했고 `pytest.ini`의 pythonpath로 해결했습니다. 키 생성은 Compose 읽기 전용 마운트 때문에 실패했고 초기화용 단일 컨테이너 쓰기 마운트로 해결했습니다. 두 오류는 재검증 통과했습니다.

기존 FastAPI/Starlette와 설치된 anyio 테스트 도구 조합의 deprecation 경고 1개가 남았으며 기능 실패는 아닙니다. Git HTTPS 인증 연동 부재로 일반 push가 실패한 이전 이력이 있지만 인증 기능의 실패와 구분합니다. 이번 구현은 push를 시도하지 않았습니다.

실제 Google·Windows→WSL·Android·Flutter 적용은 미확인입니다. 단일 프로세스 rate limit, 기간 설정 확장, JWT 구키 자동 검증·운영 역할 분리·배포·탈퇴·약관은 운영 준비 또는 후속 항목입니다.

### Git·인계 상태

로컬 브랜치 `feat/2-google-auth`, 구현/계약 커밋 **`519c609495966a3d785c6671c09bf513b28875a6`**. 코드 commit은 완료, push·PR·main/dev 통합·운영 배포는 미실행입니다. 2026-10-14 원격 조회에서 main/dev/작업 브랜치는 모두 `4ad30520f0afd52d1d5b6f27b103b83ebf1b1667`입니다.

구현 결과 댓글은 커밋 전에 작성되어 “새 계약 SHA 없음”을 기록했습니다. 이후 로컬 커밋은 생성됐지만 원격 게시와 SHA 인계가 아직 남았습니다. 계약 내용 SHA-256은 Git 커밋 SHA와 다릅니다. Flutter 요구 검토·합의·Backend 구현·자동 검증은 완료, 계약 SHA 인계·Flutter 적용·실인증은 별도 대기입니다.

## 2026-10-14 — 문서 기록 체계 정비

기존 AGENTS·개발 흐름·협업 규칙·인증 실행 안내·Issue 설계 문서를 조사했습니다. 상시 현재 계획/영구 이력/기능 지도 역할의 문서는 없어 docs/project에 NEXT_WORK·DEV_LOG·AI_CONTEXT를 추가했습니다. Issue 구현 계획은 설계 이력으로 재사용하고 상세 실행 명령·장기 정책은 복제하지 않았습니다.

AGENTS 시작 순서와 종료 기록 규칙을 추가하고 기존 개발 흐름의 “pytest·인증 미도입” 설명과 별도 이력 미관리 원칙을 실제 상태와 새 지시에 맞게 정리했습니다. 기능 코드·DB·설정은 변경하지 않았습니다.

이 작업은 문서 내용·상호 링크·git diff --check·민감정보 검사를 확인합니다. 코드 테스트·서버 재시작·DB 작업은 재실행하지 않습니다. 현재 브랜치는 feat/2-google-auth이고 이 문서 정비는 미커밋이며 push·통합·배포하지 않았습니다. 다음 작업은 NEXT_WORK의 계약 게시 승인과 공동 인수 준비입니다.


## 2026-10-14 — 문서와 인증 구현 작업 브랜치 게시

사용자 commit/push 지시에 따라 문서 체계를 `aeecaa0`으로 커밋하고 기존 인증 구현 `519c609`과 함께 원격 feat/2-google-auth에 일반 push했습니다. 앞선 미게시·미커밋 설명은 해당 작업 당시의 이력입니다.

문서 범위·참조·git diff --check를 확인했고 코드 테스트는 반복하지 않았습니다. main/dev는 4ad3052로 유지하며 PR·통합·운영 배포는 수행하지 않았습니다. NEXT_WORK·AI_CONTEXT의 게시 상태를 바로잡았습니다. 계약 SHA 인계와 Flutter 공동 인수는 다음 작업으로 남습니다.


## 2026-10-14 — 에뮬레이터 Google 로그인 401 조사

사용자가 계정 선택 후 로그인 완료 실패를 보고했습니다. 실행 API 로그에서 challenge201 이후 Google 교환401을 확인했습니다. 서버/DB healthy, 인증 키 정상, 합의 Web audience 일치, Google 공개키 endpoint200, 회원0개를 확인했습니다. 추가 azp allowlist는0개이지만 원인으로 확정하지 않습니다.

기존 로그가 거절 원인을 구분하지 못해 Google 검증 단계와 공개 error.code·request_id만 기록하도록 보완했습니다. 토큰·nonce·subject·email·claim·예외 원문은 기록하지 않으며 검증을 우회하지 않습니다. 격리 PostgreSQL에서 회귀45개 통과(민감값 없는 진단 테스트 추가), API healthy·계약 비교 재확인. 기존 테스트 도구 경고1개 유지.

[Issue 진단 요청](https://github.com/heo0328/lostparty-backend/issues/2#issuecomment-6150885671)에 Flutter 오류 코드 확인을 요청했습니다. 정확한 실패 단계와 실제 성공 여부는 사용자 재시도 대기이며 완전 해결로 보고하지 않습니다. 코드·테스트·기록은 미커밋, push/통합/배포 없음. 기존 DB 자료와 인증 계약은 변경하지 않았습니다.


같은 조사에서 새 실제 요청의 `azp_allowlist` 거절과 GOOGLE_PROOF_INVALID/401을 확인했습니다. 이전 단계의 Google 서명·audience·issuer·subject·nonce 검사는 통과했으나 정확한 Android OAuth client ID가 미인계되어 허용 목록이 비어 있습니다. 확정된 공개 ID 입력 후 설정·API 재생성·실로그인 재검증이 필요합니다. 아직 회원/session 발급 성공은 확인하지 않았습니다.


## 2026-10-14 — 확정 debug azp 개발 허용 목록 적용

[Flutter 확정 등록값](https://github.com/heo0328/lostparty-backend/issues/2#issuecomment-6151066622)을 받아 .env의 GOOGLE_AZP_ALLOWLIST에 debug Android 공개 client ID 한 개만 추가했습니다. 비밀값 출력·커밋 없이 권한600을 유지했습니다. Web audience·서명·nonce·issuer·만료 검증은 변경하지 않았습니다.

등록값 허용·미등록값 거절·잘못된 audience 거절 테스트를 추가한 뒤 격리 PostgreSQL에서46개 통과, 기존 테스트 도구 경고1개 유지. API 재생성 후 healthy와 정확한 allowlist 적용·계약 비교를 확인했습니다. 실제 Google 로그인 최종 성공은 사용자 재시도 대기입니다. 미커밋·미push, DB 초기화·운영 배포 없음.


## 2026-10-14 — 실제 Google 로그인 성공·회원 저장 확인

사용자가 에뮬레이터 로그인 완료를 보고했습니다. 개발 PostgreSQL을 읽기 전용으로 조회해 회원1개·Google identity1개·session3개·refresh hash3개, 활성 회원에 연결된 Google identity1개와 유효 session2개를 확인했습니다. 개인정보·Google subject·credential 원문은 출력하지 않았습니다.

실제 최초 가입/로그인과 DB 저장은 확인했습니다. 반복 로그인은 회원을 늘리지 않고 세션을 발급하는 구조입니다. Flutter secure pending·응답 유실 복구·앱 재시작·실기기/release·운영 인수 전체가 완료됐다고 확대하지 않습니다. 이번 확인은 데이터 수정·commit/push·배포 없이 진행했습니다.


## 2026-10-14 — Google 인증 dev 통합·push·계약 인계

사용자 승인으로 진단·테스트·성공 기록을27f1e0b로 커밋하고 dev에 fast-forward 통합했습니다. dev와 feat/2-google-auth 모두 일반 push 성공, main4ad3052는 유지했습니다. 기존46개 검증 결과를 사용했고 계약 비교·diff·민감정보 검사는 재확인했습니다. .env·로컬 인증키는 제외했습니다.

[Issue 인계](https://github.com/heo0328/lostparty-backend/issues/2#issuecomment-6151318353)에 원격 계약과 계약 커밋519c609495966a3d785c6671c09bf513b28875a6, 실제 emulator 로그인·회원 저장 결과, 남은 Flutter 검증을 전달했습니다. NEXT_WORK를 세션 공동 검증 중심으로 정리했습니다. 전체 세션·실기기/release·운영 인수 완료로 확대하지 않았고 배포·데이터 초기화는 수행하지 않았습니다.
