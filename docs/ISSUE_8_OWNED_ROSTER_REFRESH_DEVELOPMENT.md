# Issue #8 — 본인 원정대 API 목록 갱신

> 후속: [인증 대상 선택/본인 재인증·타소유 도전](ISSUE_8_VERIFICATION_TARGET_DEVELOPMENT.md)으로현재본인등록재인증과미연결claim의start201/pending·장비확인후pending경로까지구현했다. 아래start409/본인재인증미완료는당시이력이며소유이전/24시간분쟁·퇴역은여전히별도다.

2026-10-16. [76번째 API목록 기준 확정](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6212824900)·[77번째 자동실행 누락](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6212848615)·[79번째 데이터 정의](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6213474915) 및 사용자 진행 지시에 따른 구현이다. [착수](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6213586779)에 범위를 공유했다.

## 제공하는 명령

기존 `POST /v1/me/game-accounts/{registration_id}/refresh` + 빈 JSON `{}` + UUIDv4 Idempotency-Key를 사용한다. 현재 본인 소유 등록에서 서버가 Lost Ark siblings를 수집하고 DB에 반영한다. 회원별 API키·호출quota/멱등·세션/등록/소유/roster/claim snapshot fencing은 유지한다. 명령을 재전송해도 성공한 같은 명령은 provider를 다시 호출하거나 revision을 또 올리지 않는다. 새 관찰은 새 명시 명령이다.

`OwnedScope`는 이미 저장된 본인 등록/account/owner와 revision·현재 usable claim 목록을 고정하는 내부 인가 범위다. BindingEvidence가 아니며 원정대 소유권/영구세대를 이름으로 새로 추론하지 않는다. 최종 transaction에서 같은 회원/등록/account/소유·snapshot과 실제 조회 대상의 서버+이름을 재검사하고 다른 account claim이 섞인 결과는 전체 거절한다. 동일 회원이 가진 다른 원정대여도 자동 합치지 않는다.

일반 등록 목록 GET/V1·V2캐릭터 GET은 저장 DB 조회만 수행한다. 화면 진입마다 provider를 호출하는 방식으로 바꾸지 않는다. 한 회원의 여러 실제 원정대는 독립 등록/소유범위로 갱신하며, 원정대 소속 전체 목록을 활동/표시 집합으로 축소하지 않는다.

## 정상 반영

- API에 계속 보이는 현재 비퇴역/현재 claim은 같은 UUID로 갱신한다. 관찰 사이 동명 삭제·재생성의 미식별 한계는 사용자 API목록 기준으로 수용하며 공급자 보장으로 주장하지 않는다.
- 미점유 새 주소는 신규 UUID/빈 개인자료로 추가한다. 개명 전후를 자동 매칭하거나 빌드/파티/대표/활동을 승계하지 않는다.
- 누락은 suspect·사용불가로 표시하며 lifecycle revision을 바꾼다. 기존 활동/대표 ID는 보존하고 선택 안에 부적격 대상이 있으면 needs_reconfiguration으로 표시한다. 자동 대체/전체활동 선택은 없다.
- 같은 본인 원정대의 정상 API 관찰에 다시 나타난 suspect는 현재 claim이 같은 비퇴역 ID를 가리킬 때 복구한다. 이 변경도 lifecycle revision을 바꾼다. 등록/소유가 없는 단순 이름 조회나 타소유 도전으로 복구하는 것은 아니다.
- 이미 retired인 ID는 제외한다. 그 주소가 다시 나타나고 현재 점유가 없다면 신규 ID로 만든다. 이번 명령이 퇴역·소멸이력정리·claim 해제·개인자료 삭제를 수행하지 않는다.
- 정상 적용은 registration.version과 account.roster_revision을 증가시키고, account.owner_id/ownership_revision/verified_at은 그대로 유지한다. 실제 인증 캐릭터가 사라져도 기존 원정대 인증을 취소하지 않는다.

## 조회 기준 복구·실패

현재 lookup_name이 usable claim이면 우선 사용하고, 아니라면 같은 account의 현재 usable claim 중 정렬된 첫 기준을 사용한다. **명확한 upstream HTTP404에만** 다음 후보를 시도하며 명령당 최대3개 기준을 조회한다. 성공 관찰에 실제 대상/서버가 포함되고 scope/충돌 검증을 통과해야 운영 lookup_name을 저장한다. 인증 당시 Verification.lookup_name/이력, 대표·활동은 변경하지 않는다.

타임아웃/네트워크·429/키거절·빈/부분 형식오류·중복/잘못된 행·대상누락·서버변경·타account claim에는 다른 대상을 연쇄 조회하지 않는다. 기존 공개 오류 code/HTTP를 유지하고 자료/owner·revision을 성공처럼 갱신하지 않는다. 현재 API가 부분 누락 여부를 별도 표식 없이 정상 목록처럼 반환하는 경우까지 추가 영구증거로 구별한다고 주장하지 않는다. 정상 유효 목록은 합의된 구성 기준으로 쓰되 이번 구현은 누락을 suspect까지만 반영해 삭제하지 않는다.

다른 usable 기준이 없거나 최대3개 조회로 복구되지 않으면 명령 실패/조회 미완료이며 기존 원정대 인증/자료를 보존한다. 모든 캐릭터 기준이 바뀐 경우나 새 이름만으로 기존 원정대 전체를 자동 연결하는 경로는 이번에 없다. 실패의 멱등 lease는 기존 retryable이며 같은key/body로 명시 재시도할 수 있고 quota/Retry-After를 지킨다. provider 404 표식은 내부 복구용이며 새 HTTP 오류/필드를 추가하지 않는다.

## Flutter 소비·완료 의미

성공200의 기존 RefreshOut은 다음을 포함한다.

| 값 | 의미 |
|---|---|
| registration | 반영 후 등록/roster/설정 version 및 소유 상태 |
| added_count | 이번 반영으로 새로 만든 캐릭터 수 |
| suspect_count | 반영 후 여전히 확인이 필요한 비퇴역 누락 수 |
| requires_refresh | 미해소 suspect 존재. HTTP 명령이 계속 실행 중이라는 뜻이 아님 |

성공/replay 뒤 최신 canonical/설정 목록을 다시 읽어 유효한 활동 집합을 정한다. 이전 cursor는 revision 변화로 stale일 수 있으므로 최신 목록의 첫 페이지부터 수집한다. API실패는 자동준비 성공/상세검사 완료로 소진하지 않는다.

Flutter 순서: 환경/회원별1회 준비 → 현재소유 각 원정대 refresh → 최신 등록/roster/settings·canonical 전체 재조회 → 유효한 앱 활동 캐릭터 집합 → 상세/빌드 검사. 표시 숨김/count로 목록이나 활동 검사 집합을 줄이지 않는다. 나이스단OFF는 해당 상세/빌드만 제외하고 목록 갱신은 유지한다. 동일 실행의 멱등키/명시 미완료 재시도·준비실패미소진·회원전환 late 차단은 기존 정책이다. Flutter 연결은 Backend 게시 후 상대 측 작업이며 서버 구현만으로 완료 표시하지 않는다.

## 검증과 제외

공개endpoint/DTO/enum/DB구조 불변. OpenAPI owned_roster_refresh와 lifecycle의 evidence/recovery 정책 설명을 맞춘다. 실제HTTP수집기+모의응답·격리PostgreSQL에서 추가/누락/복구/종료ID재등장·실패원자성/인증보존·404대체기준/상한·명령replay/GETprovider0·타account충돌·늦은수집결과를 확인한다. 기존 강한binding경로의검사는유지하며현재정책과달라진기존시험기대만정정한다. 실행 수/실패·수정·개발API반영·게시상태는DEV_LOG/결과댓글을따른다.

기존8000/DB0010/개발자료를 유지하며 API만 반영한다. 실제 게임/기기 관찰은 사용자 결정대로 나중이다. 본인 장비 재인증/타소유pending 도전·퇴역/claim 정리·24시간 분쟁/이전·운영은 별도 후속이다. Flutter자동실행연결/실사용·운영완료와 이번 Backend완료를 구분한다.

최종 격리 PostgreSQL **422PASS·기존경고1·230.32초**, 초기 실패 없음. 첫 직접128PASS/60.18초 후 조회중 소유/키/등록삭제 변화 거절을 추가하고 전투력/설정/생명주기/인증·복원 회귀를 검증했다. 실행을 합산하지 않는다. 기존8000 API 반영·실행전체OpenAPI/health·새모듈·DB0010 유지 확인. 실제 provider/장비/기기 인수와 Flutter 자동 실행 연결은 미실행이다.

구현/계약3c8e7998f90e77180fc522bca461004b98c3007f·feat/representative-selection push/원격일치/dev미통합. [82번째Backend결과/Flutter연결요청](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6213790275). Flutter자동준비연결은다음 단계이며본인장비재인증/타소유pending은Backend독립후속이다.
