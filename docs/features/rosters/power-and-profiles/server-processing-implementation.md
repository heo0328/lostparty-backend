# 서버 수집·분석 구현 기록

2026-11-16 / [Issue55](https://github.com/heo0328/lostparty-backend/issues/55) / `refactor/lostark-server-processing` / 시작 HEAD `cda4db352c9ac922f269b9ec2794f0d888d4dca6`. 사용자 구현 지시에 따른 로컬 변경이며 미커밋·미push다. 개발 API·기존 DB0036·실제 키/환경·운영에는 적용하지 않았다.

## 구현과 데이터 책임

[확정 계약](analysis-refresh-contract.md)에 따라 서버 secret 공급·공유 제한을 HTTP/소유권 worker/진단에 연결했다. Native 고정302243fb의 분석 카탈로그와 순수 규칙을 Python으로 옮기고 합성8계열을 사용한다. 새 POST는 항목별 현재 명령 ledger·감지역할 CAS·fresh 관찰 합류를 제공하며 summary/detail/version을 한 트랜잭션에서 저장한다. 실패 관찰은 기존 head를 유지하고 성공한 null·낮은 수치·세팅 오류는 최신값으로 저장한다. 그룹/모집/신청·후보/토큰도 최신 head를 사용하며 이전 성공값 저장소와 fallback을 제거했다. 기존 입장 스냅샷은 현재 head와 분리한다. 공개 탐색/예시는 Native 담당이며 Backend 공개 범위는 확대하지 않았다.

개인키 CRUD/restore와 클라이언트 role-summary PUT/batch, 회원키 암호화 모듈·성공값 모델을 제거했다. 앱 factory는 create_app 하나이며 미사용 compose.two-cycle 호환 override도 제거했다. 과거 OpenAPI/마이그레이션/배포 기록은 동결 자료로 유지하며 배포 hash 도구는 과거 명세 파일을 읽는다. 과거 앱을 새 실행의 비교 서버로 만들지 않는다. 현재 기능 시험은 최신 스키마를 직접 준비하며 마이그레이션 보존 시험과 구분한다.

## 외부 오류·추가 수집 억제

[전체7 Native 요청](https://github.com/heo0328/lostparty-backend/issues/55#issuecomment-6910971244)을 [전체8 Backend B1 중간 결과](https://github.com/heo0328/lostparty-backend/issues/55#issuecomment-6911910416)에 회신했다. [공식 오류/점검 안내](https://developer-lostark.game.onstove.com/usage-guide#api-errors)와 [throttling](https://developer-lostark.game.onstove.com/getting-started/#throttling)을 대조했으며 wire delta는 없다.

| 관찰 | 프로젝트 처리 |
|---|---|
| 200 | JSON/크기/형식/대상/역할 검증 후 저장. Remaining0이면 이번 성공을 유지하며 새 수집 제한 |
| 401/403 | 503 LOSTARK_KEY_REJECTED, 같은 서버 키 새 수집60초 억제. 개인키 입력/Google 로그아웃 요구 없음 |
| 404 | 분석 실패·저장 불변, 우리 UUID/등록404와 별개. 기존 owned roster provider404 전용 anchor fallback만 유지 |
| 415 | UPSTREAM_UNAVAILABLE·60초 억제, 요청 형식/설정 점검 대상 |
| 429 | UPSTREAM_RATE_LIMITED·유효 Reset/Retry-After 중 늦은 시각. 비정상 Reset fallback60초 |
| 500/502/503/504·통신 실패 | UPSTREAM_UNAVAILABLE·30초 억제. 유효 Retry-After가 더 늦으면 반영. 503만으로 점검 확정 안 함 |
| redirect/불량 JSON/HTML·기타 비200 | 안전한 실패, 성공값 fallback/원문 노출 없음 |

억제는 fingerprint별 기존 DB 행에 code·상태·deadline만 저장하며 모든 생산자가 공유한다. 30/60초·최대300초의 헤더 대기 범위·자체80회/분은 프로젝트 정책이다. 이미 전송한 최대2개 요청의 결과에는 권한·세대·수명 fence를 계속 적용한다. 새로운 일반 작업 시스템·자동 재시도는 없다. 일반 GET·공개 모집·기존 저장자료 읽기는 영향을 받지 않는다. 외부 실패는 failed/new_command와 명시 재시도, 예산미시도는 not_processed/same_command, DB commit 불명은 unknown/same_command다.

## DB·설정 적용 전 경계

0037은 개인키/과거 분석·연결 snapshot 등 비호환 행이 있으면 **DDL 전에 중단**한다. 자료를 자동 삭제·새 출처로 변환하지 않는다. 대상과 영향이 명시된 별도 데이터 준비 승인 없이 실제 dev/운영 DB에서 실행하지 않는다. 빈 호환 DB의 전진 적용과 비호환 자료 보존 거절은 일회용 제한 LOGIN DB에서 검증한다.

실제 적용 때 `.secrets/lostark-api-token`을 읽기 전용 secret으로 공급해야 한다. 값은 서버/보관본에만 두고 Git/로그/Issue/앱에 넣지 않는다. 기존 `.secrets/lostark-fingerprint.key`를 재사용하며 새 키를 반복 생성하지 않는다. `.env`·JWT/recovery/fingerprint 및 새 token 파일은 [백업 원장](../../../engineering/operations/backup-and-recovery.md)의 기존 별도 사본 위치에 보관하고 접근 권한을 제한한다. 기존 lostark-credential.key와 과거 DB 복구용 사본은 이번 코드 제거로 삭제하지 않는다. 이번에는 실제 파일 생성/키 복사/DB 초기화·복구를 실행하지 않았다.

## 최종 검증과 남은 환경 경계

- 최종 수집1,889개 시험 항목의 통과 근거를 분할 로그와 대조했다. 초기 실패를 수정한 재검증을 포함해 중복을 제외한 누락0·미해결 실패0이다. 한 차례 전체 green 실행으로 표시하지 않는다. 동적 UUID1 parameter1건은 같은 시험 사례로 대조했다. 서버/provider는 합성 자료이며 실제 FastAPI HTTP와 일회용 제한 LOGIN PostgreSQL을 사용했다.
- 현재 분석·인증·회원설정 세트130PASS/분석13subtests, 개인 프로필 reader/입장 snapshot11PASS, 주간 요약33PASS, 관리/실제 인증28PASS 및0037/전체 표 timestamp6PASS를 확인했다. 이 수치는 전체1,889개에 포함되며 합산하지 않는다.
- 도구 unittest87PASS. 현재 OpenAPI191경로/211동작의 생성 객체 전체 비교·의존성·문서/링크·기존 본문128개/동결JSON20개 보존·compile/diff 점검 PASS.
- 실제 provider/개발 서버 연동·Native UI/기기·운영·실제 자료 정리/복원은 미실행이다. 실제 개발 API/DB는 이전 컨테이너로 healthy이며 교체하지 않았다.

[현재 시험 대응표](../../../engineering/development/current-test-consolidation.md)에 DB0023 실행 전용8모듈과0034 공통 연결 시험 종료/현재0035 대상별 정책 검증 위치를 기록했다. 최신 head에 이전 revision upgrade·전체 표 hash를 반복하던 무효 준비 단계를 제거했으며, 실제0033/0035 SQL migration 전후 보존은 별도 시험으로 유지한다. 개인 프로필 배치 GET의 권한/단일 GET 일치·쿼리 수·읽기 snapshot은 현재 reader 전용 시험으로 보존했다.

현재 앱 전체 검사에서 드러난 소비 경계도 보완했다. 제거한 successes 집합 잔여 참조를 없애고 opt-in 신청/상세·후임자 DTO가 현재 그룹 metadata를 보존하도록 맞췄다. 카드 목록의 대상 cycle/generation 정책을 일괄 조회해 N+1을 제거했고 성능5건을 통과했다. 공통 제목 noop은 영향 주차를 빈 목록으로 반환하며,0037에서 roster_participation_capabilities의 빠진 DB 기록 시각 trigger를 추가했다. 과거 migration은 수정하지 않았다. 재참가 시험은 옛 CM/assignment 재사용을 기대하지 않고 기존 이력 보존+새 참여를 검사한다.

Backend 로컬 구현·자동 검증은 완료했다. 다음 Backend는 사용자 지시 범위에서 코드 게시/SHA 인계와 실제 설정/자료 준비·개발 실행 전환을 진행한다. 새 소비 SHA/실행 서버가 없으므로 Native 원격 구현 시험을 요청하지 않았다. Native 공통 UI/가상 예시·통합/기기 확인과 실제 운영은 별도 미완료이며 Issue55는 OPEN이다.

[전체9번째 댓글·Backend B1/B2 구현 결과](https://github.com/heo0328/lostparty-backend/issues/55#issuecomment-6914853896)로 회신하고 실제 댓글9개/작성 측/단계를 재조회했다. 본문 상단도 현재 완료/다음 담당·미적용 경계로 갱신했으며 Issue는 OPEN이다.
