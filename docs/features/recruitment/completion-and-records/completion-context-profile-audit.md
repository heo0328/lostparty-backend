# Issue17 완료 CONTEXT_INVALID 조사·오류 분류

최신 소비 상태: [전체35번째 Native](https://github.com/heo0328/lostparty-backend/issues/17#issuecomment-6733937729)에서 오류 안내/안전한 진단·완료 성공과 후속 조회 실패 분리 구현, 자체2832PASS/analyze0을 보고했다. 미커밋·미push·실기기 미확인이며 Backend 보정 계약을 기다린다. 새 코드/필드를 추가하지 않고 현재 schema/query를 유지한다. 아래8PASS 진단과 Native의 안내 파트 통과 모두 완료 차단 수정 성공은 아니다.


후속 실행 상태: [최신 구조 로컬 반영](../../../engineering/operations/source-layout-local-rollout.md)·[Backend 전체34번째](https://github.com/heo0328/lostparty-backend/issues/17#issuecomment-6733877672)을 완료했다. 실제 dev는API2f86172d/소스ccf091d이며 완료 계약 불일치는 그대로다. Native 전체33번째에서 사용자 승인 구현/Backend 계약 보정 요청을 수신했다. 아래 조사는 반영 전 근거이며 기능 수정 완료가 아니다.


2026-11-09 / Backend 조사. 기준 브랜치는 `feat/character-lifecycle`, HEAD는 `ccf091d5d52d72582ae33d4680ffd7aa73d27474`다. Native 전체29번째에서 구현/문서7a165ac1의 원격 게시를 확인했고 전체30번째 완료 차단 제보에 대응한다. 아래 결과는 조사이며 오류 수정 완료가 아니다. 이번 변경은 이 보고서와 현재 상태 문서뿐이고 미커밋·미push다.

공식 회신: [전체31번째 Backend 조사·분류 회신](https://github.com/heo0328/lostparty-backend/issues/17#issuecomment-6733182655)

## Backend — 완료 CONTEXT_INVALID 원인 경로 재현·오류 분류 회신 (조사 단계)

[전체30번째 Native 제보](https://github.com/heo0328/lostparty-backend/issues/17#issuecomment-6732895692)에 대한 조사 결과입니다. **공대·개인 완료의 프로필 불일치 경로를 합성 DB/실제 HTTP에서 재현했습니다. 기능 수정이나 기기 오류 해소 완료는 아닙니다.**

### 1. 확인한 원인과 실제 지원 범위

- 현재 저장소와 실제 dev image `ce59926c`/DB0036의 생성 계약 모두 GET `command-context`에는 `participation_profile=remaining-active-1`을 선언하고, POST `raid-rounds/{round_id}/completion`, `personal-completion`에는 선언하지 않습니다. 실행 계약 SHA256은 기존 `2aeca907115ffc768cad723d227f0c2339b042f56f46ffed251c1037d235b6c4` 그대로입니다.
- 그러나 `CycleRoute.allowed_query`는 이 POST들에서도 profile을 허용합니다. 조회의 `life.sign`/`opaque.seal`이 profile을 토큰에 넣고, 명령의 `opaque.unseal`/`roster_participation.check_marker`가 요청과 비교합니다. **GET에만 profile을 붙이면 새 완료 명령이 400 CONTEXT_INVALID로 거절됩니다.** 유효한 명령인데도 계약 기반 자동 query 소비에서 이 조합이 만들어지는 Backend 선언 누락입니다.
- `roster_openapi.decorate`의 경로 문자열 필터가 `raid-rooms`/`raid-room-`만 포함해 `raid-rounds` 등을 놓칩니다. [계약 보정](https://github.com/heo0328/lostparty-backend/blob/6a87e143e651bd9fc51129f969bfd9ced314a5a1/app/raid_rooms/contracts/roster_openapi.py), [실제 허용 query](https://github.com/heo0328/lostparty-backend/blob/6a87e143e651bd9fc51129f969bfd9ced314a5a1/app/raid_rooms/api/cycle_router.py), [토큰 검사](https://github.com/heo0328/lostparty-backend/blob/6a87e143e651bd9fc51129f969bfd9ced314a5a1/app/raid_rooms/common/command_context.py)를 대조했습니다. 검증·권한을 유지하면서 선언/소비를 일치시키는 방향을 권장합니다.

실제 CycleRoute가 허용하지만 공개 선언에서 빠진 동작은 **10개**입니다. 완료2개 외에는 영향 검토 대상이며 같은 완료 토큰 오류가 전부 재현됐다는 뜻은 아닙니다.

| 분류 | 선언 누락 동작 |
|---|---|
| 완료 | POST `/v2/raid-rounds/{round_id}/completion`, `/personal-completion` |
| 일정 | GET `/v2/me/raid-schedule-overlaps`; POST `/v2/raid-sessions/{session_id}/participation-confirmations`; GET `/v2/raid-schedule-groups/{group_id}/candidates`; POST 해당 group의 `/selections`; POST `/v2/raid-schedule-proposals/{proposal_id}/responses` |
| 개인 주간 상태 | PUT `/v2/me/characters/{character_id}/raid-weekly-states/{raid_id}/manual-completion`; GET 해당 상태의 `/completion-correction-context`; POST `/completion-corrections` |

권장 후속은 완료2개 우선으로 실제 지원 동작 목록을 명시하고, 나머지8개도 실제 사용·토큰/능력표식 검사를 대조하는 것입니다. Native는 합의된 새 계약/hash를 소비한 뒤 **새 조회와 새 명령**에 일관된 profile을 사용해야 합니다. 새 계약은 아직 작성/게시하지 않았습니다. 영향 방·주차의 `CLIENT_UPGRADE_REQUIRED` 검사가 있으므로 일괄 profile 제거를 복구책으로 삼지 않습니다. `close_weekly`/동일주 재개 앱 비활성 정책은 유지합니다.

### 2. 이번 재현과 실제 요청의 한계

격리 PostgreSQL/합성 회원/실제 CycleRoute HTTP에서 공대·개인 완료 × profile4조합 = **8PASS / 111.54초**입니다. 이 통과는 버그 경로를 확인한 진단 결과입니다.

| GET profile | POST profile | 두 완료 경로 결과 |
|---|---|---|
| 없음 | 없음 | 200 (능력표식 없는 정상 방) |
| 있음 | 있음 | 200 |
| 있음 | 없음 | 400 CONTEXT_INVALID, 완료·원장·예약 등 업무 표 hash 불변 |
| 없음 | 있음 | 400 CONTEXT_INVALID, 같은 업무 표 hash 불변 |

불일치 거절 뒤 합성 진단에서만 profile을 맞추면 같은 키/본문으로 200, 이후 원 ACK 재생이 토큰 검증보다 먼저 반환됨도 확인했습니다. **이는 원인 분리를 위한 시험이며 Native 저장 원요청의 query/키/본문을 수정하라는 인계가 아닙니다.** 원키/본문/ACK·원 pending snapshot은 보존합니다. 초기는 같은 캐릭터로 여러 방을 연속 준비해 정상 WEEKLY_ALREADY_PARTICIPATING 가드에 걸린 준비 오류2건이 있었고, 각 조합을 독립 fixture로 바꿔8PASS했습니다. 중간 수는 합산하지 않습니다. 두 시험 프로젝트 cleanup0입니다.

실제 dev의 최근 로그에서도 공대 완료 POST `400/CONTEXT_INVALID` 3건을 읽기 전용으로 확인했습니다. request_id는 `0d505a6f-4d83-457b-add0-84213a182bfa`, `ea2ea73f-2e6b-46fb-af8d-e569df2b8251`, `06dd31f9-e324-4e33-86af-ccc37063604e`입니다. 현재 허용목록 로그에는 내부 실패 분기나 query가 없어 **이 요청들을 profile 불일치로 확정하지는 않습니다.** Native가 제보 기기 request_id와 해당 GET/POST의 profile 유무만 대조할 수 있으면 실제 요청 상관관계를 확정하는 데 충분합니다. 토큰·키·원본문·다른 회원 정보는 요청하지 않습니다.

기존 HTTP 시험은 profile 생략 쌍, 서비스 시험은 동일 요청 범위의 profile을 사용해 통과할 수 있었습니다. 계약 기반 자동 query로 GET만 profile이 생기는 실제 연결의 검증이 빠져 있었습니다. 과거 Backend/Flutter 전체 통과 수를 이 경로의 성공 근거로 재사용하지 않습니다.

### 3. 오류 분류·권장 행동 (현재 POST 소스 기준)

아래는 대표 코드이며 GET context의 `permission.allowed=false/reason`은 HTTP200으로도 반환됩니다. 사용자 최종 문구·배치는 Native가 주도합니다.

| 구분 | 기존 HTTP / code | 완료 효과·권장 행동 |
|---|---|---|
| 확인 정보 검증 불가 | 400 `CONTEXT_INVALID` | 해당 검증 거절 시 새 완료 효과 미반영. 상태/확인 정보 재조회 후 사용자 재확인; 반복 시 request_id로 조사. 회원·캐릭터 잘못으로 안내하지 않음 |
| 확인 시간 만료 | 409 `COMMAND_CONTEXT_EXPIRED` | 새 실행은 거절. context 재조회·사용자 재확인. 원 ACK가 있으면 기존 원요청으로 먼저 복구 |
| 대상·참가·일정·주차 변경 | 409 `TARGET_CONTEXT_STALE`, `REVISION_CONFLICT`, `CYCLE_CHANGED`, `TARGET_CYCLE_UNAVAILABLE` | 거절/rollback. 해당 실제 주차·대상 재조회 후 명시 확인. 다른 주차로 자동 전환하지 않음 |
| 아직 완료 가능한 시점이 아님 | 409 `TARGET_CYCLE_NOT_CURRENT`, `PLAY_NOT_STARTED` | 미반영. 현재 주차·플레이 가능 시각 안내 |
| 권한·접근 불가 | 403 `TARGET_LEADER_REQUIRED`, `WEEKLY_PARTICIPANT_REQUIRED` 등; 401 `SESSION_EXPIRED`/`SESSION_REVOKED`; 권한 비공개 대상은404 가능 | 현재 시도 실행 거절. 실제 주차 권한/로그인 상태 확인. 404로 타회원 정보 존재를 추론하지 않음 |
| 더 이상 진행 중인 대상이 아님 | 409 `ROUND_NOT_ACTIVE`, `ROOM_NOT_ACTIVE` | 신규 완료 거절. 최신 상세/기록에서 완료·종료를 구분. 이 코드만으로 ‘이미 완료’라 단정하지 않음. 같은 키/같은 원요청의 기존 성공은200 원 ACK |
| 클라이언트 지원 부족 | 409 `CLIENT_UPGRADE_REQUIRED` | 새 실행 거절. 지원 계약/앱 갱신 안내. 사용자 원정대 새로고침을 해결책으로 안내하지 않음 |
| 기능 준비 필요 | 503 `RECRUITMENT_COMMAND_NOT_READY`, `GROUP_FEATURE_NOT_READY`; 409 `ROOM_REVIEW_REQUIRED` | 실행 전 준비/검토 거절. 서버 준비·검토 확인, 반복 명령 금지 |
| 처리 중 | 409 `REQUEST_IN_PROGRESS` (Retry-After2) | 결과 확정 전. 원 method/path/query/body/key와 pending 유지, 기존 복구 흐름 사용 |
| 원요청 식별 충돌·보존 만료 | 409 `IDEMPOTENCY_CONFLICT`, `IDEMPOTENCY_EXPIRED` | 이전 시도의 성공 여부를 이 응답만으로 판단하지 않음. 원 ACK/현재 상태 확인; 새 키로 강제 복제하지 않음 |
| 통신/서버 결과 확인 불가 | 응답 미수신·timeout/게이트웨이5xx·일반503 `SERVICE_UNAVAILABLE` | 결과불명으로 취급. 원요청 보존·원 ACK 복구와 현재 상태 확인. 오류 코드만으로 미반영 단정/새 명령 복제 금지 |

4xx 거절 설명은 **해당 시도**의 검증 기준입니다. 이전 시도의 응답이 유실됐다면 현재 오류만으로 그 이전 완료가 미반영됐다고 단정하지 않습니다. 성공 ACK 뒤 후속 GET 실패는 완료 성공을 유지하고 조회만 복구합니다. 일반503은 COMMIT 응답 실패 가능성 때문에 기능 준비 전용503과 구분합니다.

현재 권장안은 **새 wire code/필드 없이 기존 코드+status+request_id를 활용**하는 것입니다. `CONTEXT_INVALID`만으로 프로필 불일치와 해독/형식 문제를 구별할 수 없으므로, 상세 진단은 서버 허용목록 분기 분류 로그를 보강하는 안을 검토합니다(미구현). 실제 키·암호문 내부를 노출하지 않습니다. 외부에서 프로필 불일치를 별도 처리해야 한다는 요구가 합의되면 별도400 `CONTEXT_PROFILE_MISMATCH` 같은 코드를 검토할 수 있지만, 이번에 확정/추가하지 않습니다. 현재 `ErrorDetails`는 extra-forbid이므로 `details.reason`을 임의 추가하지 않습니다.

**다음 담당:** Native는 기존 코드 분류/최소 진단정보 보존·새 계약 소비 시 변경 범위를 검토하고 위 request_id와 profile 유무의 상관 여부만 회신할 수 있습니다. Backend는 완료2경로의 계약 선언 누락과 추가8경로 대조, 계약 기반 query→실제 HTTP 짝 검증을 수정 범위로 제안합니다. 정책·오류 계약 변경은 사용자 확인 후 진행하며 현재는 조사·협의입니다. 기능 코드/OpenAPI/서버/DB·실자료·키/환경 변경, commit/push/merge·배포·자동 재명령·Issue 종료는 하지 않았습니다. 실제 완료 재확인은 수정·표적 검증·로컬 반영 이후 사용자 기기에서 별도로 진행합니다.

## 재현 기준과 후속 시험

조사 시험은 저장소 기능/시험 코드를 수정하지 않고 임시 조사 이미지에서 실행했다. 기존 `presence_db`(0036)와 `bundle(continuation=False)`·`outcome_body`·`client`를 재사용하고 각 GET/POST profile 조합에 독립 fixture를 사용했다. 업무 hash는 `recruitment_`/`raid_` 표를 비교하며 실패 시 dedup 예약 행의 retryable 전환을 업무 변경으로 오인하지 않는다. 조사 프로젝트는 `lostparty-issue17-audit-4c6260449d`(pytest111.54s, 전체118.0s, exit0/cleanup0), 초기 준비 오류 프로젝트는 `lostparty-issue17-audit-a8f6647ddf`(2FAIL/34.73s, cleanup0)다. 임시 시험은 정식 회귀 파일 추가나 기능 수정이 아니다.

향후 수정 때는 계약의 지원 query로 실제 GET/POST를 자동 구성하는 두 완료 경로 HTTP 회귀를 정식 추가한다. 같은 프로필/불일치 거절·원ACK·만료·대상/CAS·권한·부분완료 후 capability·미반영/rollback을 필요한 영향 범위에서 검증한다. 추가8동작은 토큰 없는 CAS 명령, 양쪽 모두 선언 누락인 정정, 단순 조회를 구분한다. 이번8PASS는 이런 모든 후속 경우나 Native 기기 인수를 새로 확인한 수치가 아니다.
