# Issue17 완료 프로필 계약 보정

2026-11-10 현재 결과: [완료 오류·계정 복구 인수/Native 게시](completion-recovery-acceptance-20261110.md) 완료. 기존 계정은 문구 수정 전에 복구됐고 사용자 기기 테스트 통과, Native 구현5df515f push가 확인됐다. 아래 조사·회신의 복구 미확인/기기 대기·Native 미게시 표기는 당시 기록이며 현재 대기가 아니다. 누락 캐릭터/부분 완료 자료·기기 검증과 일괄 완료 기획은 별도 미완료다.

후속 BUG-033: [계정 정정/수동 완료의 그룹 옵션 확인](account-completion-group-profile-bug033.md)에서 계정3경로에도 DB0036 group gate가 적용됨을 확인했다. participation_profile 선택성과 별개로 신규 계정 호출에는 기존 group_policy_version을 연결해야 한다. 앞선 무옵션 소비 가정은 정정하며 계약 파일 자체를 다시 바꾸는 것은 아니다.

2026-11-09 / Backend / feat/character-lifecycle. 사용자 승인 구현·격리 검증·관련 commit/push·로컬 API 반영·Issue 인계 구간이다. [원인 조사](completion-context-profile-audit.md)와 [Native 전체33번째 요청](https://github.com/heo0328/lostparty-backend/issues/17#issuecomment-6733769180)을 따른다. 구현·격리 검증·게시·로컬 API 반영·Issue 인계를 완료했다. Native 계약 연결·사용자 기기 확인은 미완료다.

## 문제와 변경

완료 context GET은 participation_profile을 선언하지만 완료 POST2개에는 선언이 없어, 계약을 따라 query를 만드는 앱이 GET1/POST0 조합으로 CONTEXT_INVALID를 받는다. 실제 서버는 이미 profile을 허용하고 토큰 일치·권한을 검사하므로 업무 제한을 바꾸지 않고 공개 선언을 일치시킨다. 실제 제보 요청의 내부 분기는 로그만으로 확정하지 않았다.

`app/raid_rooms/contracts/roster_openapi.py`의 PARTICIPATION_OPERATIONS는 HTTP method·경로 template65쌍을 명시한다. 프로필 선언을 기존 경고/응답 확장과 분리하고, 모든 실제 라우트의 query 허용과 대조한다. profile을 허용하지 않는 preset은 제외한다. 기존 metadata 확장 범위는 유지한다.

`openapi/two-cycle.openapi.yaml`에는 아래10동작에 선택적 query `participation_profile=remaining-active-1`만 추가한다. 기존55개와 합쳐65개이고 중복0이다. 기본 OpenAPI 전체/bytes와 두 계약의 DTO·모델 이름·참조·operationId·요청/응답 본문·오류·기존 확장 필드는 유지한다. 런타임 query/token/CAS·권한·transaction·DB·migration 코드는 변경하지 않는다.

| HTTP | 추가 선언 경로 |
|---|---|
| `GET` | `/v2/me/characters/{character_id}/raid-weekly-states/{raid_id}/completion-correction-context` |
| `GET` | `/v2/me/raid-schedule-overlaps` |
| `GET` | `/v2/raid-schedule-groups/{group_id}/candidates` |
| `POST` | `/v2/me/characters/{character_id}/raid-weekly-states/{raid_id}/completion-corrections` |
| `POST` | `/v2/raid-rounds/{round_id}/completion` |
| `POST` | `/v2/raid-rounds/{round_id}/personal-completion` |
| `POST` | `/v2/raid-schedule-groups/{group_id}/selections` |
| `POST` | `/v2/raid-schedule-proposals/{proposal_id}/responses` |
| `POST` | `/v2/raid-sessions/{session_id}/participation-confirmations` |
| `PUT` | `/v2/me/characters/{character_id}/raid-weekly-states/{raid_id}/manual-completion` |

계약 SHA256:

- 이전 two-cycle: `2aeca907115ffc768cad723d227f0c2339b042f56f46ffed251c1037d235b6c4`
- 새 two-cycle: `864de38b53ec23a305074bb3844a7a603ba1f992815427fdba3e6931793119b6`
- 기본: `18491bc066d08a578aa9228cd0da85eee508288c28d14d563d788e73e324c3dd`

## 검증 범위

신규 `tests/raid_rooms/outcomes/test_completion_profile_contract.py`는 저장 계약의 지원 목록으로 query를 구성한다. 두 완료 경로의 profile 일치 성공/불일치400 CONTEXT_INVALID·입력 오류400 INVALID_REQUEST, 원ACK/업무 불변·반대 주차/완료 기록 보존, 혼합 M/P 교체 후 profile 없는 조회의409 CLIENT_UPGRADE_REQUIRED와 명령의 token/profile 불일치 선검증400 CONTEXT_INVALID를 구분한다. 각 조합은 독립 fixture다.

추가8동작도 실제 HTTP로 검사한다. overlaps/candidates 조회, participation-confirmations의 CAS와 원ACK, proposal responses의 원ACK, manual PUT과 correction GET→POST profile 토큰 연계를 포함한다. beta group selections의 기존409 SCHEDULE_PROPOSAL_REQUIRED와 잘못된 CAS의409 TARGET_CONTEXT_STALE를 성공으로 바꾸지 않는다. 정정 실패 시 업무 불변·성공 시 과거 참가 미복원과 원ACK를 확인한다.

기존 완료·정정·일정·원정대 참가/후속·beta 회귀는 만료/stale·공대장/본인 권한·rollback·동시성·원ACK·M/P 이력·반대 주차/개인정보 경계를 담당한다. 전체 기존1923개 재실행이 아닌 영향 범위 검사이며, 과거 고유1921PASS/기존 기대 불일치2FAIL과 이번 실행 수를 합산하지 않는다. 기존2개는 그룹 활동 해제 후 기존 참가 거절 기대와 stopped 상태의 미선택 N 개설 기대다.

시험 준비 과정에서 실제 no-store middleware 누락과 과거 동결 계약을 사용하던 검증 도우미를 발견했다. 신규 도우미를 현재 실제 라우트 middleware·현재 저장 계약으로 수정했다. 중단된 준비 실행과 반복 실행 수는 최종 고유 통과 수에 합산하지 않는다. 혼합 상태 POST도 토큰의 profile이 다르면 capability 검사보다 먼저400 CONTEXT_INVALID가 발생하므로 신규 시험의409 기대1개를 기존 검증 순서에 맞췄다. 제품의 권한/입력 검사를 완화하지 않았다.

현재 신규17사례는 최초 완주16PASS/1FAIL(209.47s) 후 위 기대값1개를 수정해1PASS(21.17s), 최종 고유17PASS다. 참가·후속·beta42PASS(484.11s), 도구63PASS(0.613s)를 확인했다. 완료·정정·일정55PASS(720.18s)로 이번 영향 회귀는 최종 고유114PASS/미해결0이다. 재실행1개를 중복 합산하지 않는다.

## Native 인계 기준

[전체35번째 Native 오류 안내 결과](https://github.com/heo0328/lostparty-backend/issues/17#issuecomment-6733937729)를 유지한다. Native 자체2832PASS/68s·analyze0은 Backend 시험 결과나 기기 완료 성공이 아니다. Native 화면 구현/동일 오류 안내 재수용을 요구하지 않는다.

Native는 게시된 새 계약/hash를 채택하고 **새 조회·새 명령**에 같은 profile을 적용한다. 기존 원query·본문·키·검증 snapshot·pending/ACK는 그대로 보존한다. 새 wire code/details.reason·자동 재명령은 추가하지 않는다. Native 계약 연결·자동 검증 이후 실제 기기 완료 성공은 사용자가 별도로 확인한다.

## 실행 기록

- 고정 구현 `16c9cd4b9016a881bbb26c8438f3347049603902` / feat/character-lifecycle, origin push·원격 SHA 일치 확인. 후행 문서 커밋은 게시/실행 결과를 기록하며 런타임 소스는 이 구현 SHA로 고정한다.
- 격리 업무 영향 회귀114PASS·도구63PASS·두 전체 계약/10개 선언 차이·문서/동결/경로/diff 검사 통과. [비민감 집계](../../../engineering/operations/records/completion-profile-contract-verification.json)를 따른다.
- 실제 로컬 API image `sha256:101cd82d630f3897707f411ba6ee444101016bf715c2b975f2db9323c1dabf6f`, 이전2f86172d에서 API만 교체. 2026-11-09 17:03:27 KST 기동, 앱285파일/282모듈·후보/게시 소스/실행 두 전체 계약 일치, API/DB healthy다.
- 반영 직전·직후 DB0036·117업무표355행의 전체 hash·컬럼/제약/index·sequence, 키4개 내용/권한/소유자·호스트 .env·API 환경/포트/보안/mount·DB컨테이너/시작시각/이미지/볼륨 동일. 직전 구조 배포 당시357행과 이번 직전355행을 혼동하지 않는다. migration·실자료 명령·새 키/환경·dump/자료복구 없음. 기존 유효 보관본과 로컬 DBdump 제외 결정을 재사용했다.
- 실제 localhost listener7개: health/주차200, 보호된 GET/두 완료POST 무인증401·no-store, docs/openapi.json404. 새 실행 로그17이벤트 오류0이며 복귀 사용0이다. 실제 회원 완료/교체 쓰기·기기 성공·장시간 성능 검증이 아니다.
- [전체36번째 Backend 계약 보정·로컬 반영 인계](https://github.com/heo0328/lostparty-backend/issues/17#issuecomment-6735265341)의 본문을 재조회해 일치와 실제 댓글36개/순번을 확인했고 Issue 본문 상단을 갱신했다. 이전 사용 한도로 자동 승인 검토가 완료되지 않아 첫 게시 시도는 실행되지 않았다. 사용자 재개 후 준비된 동일 내용을1회 게시했으며 중복 댓글은 없다.

다음은 Native의 새 계약 채택·새 조회/명령에 일관된 profile 연결·자동 검증과 사용자의 실제 기기 완료 확인이다. 기존 저장 pending/원query·본문·키·검증 snapshot·ACK는 보존한다. Backend는 구체 차이에 대응한다. 운영/APK 배포·merge·Issue 종료는 하지 않았다.
