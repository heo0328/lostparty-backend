# BUG-033 계정 완료 정정의 그룹 옵션·거절 요청 복구 확인

2026-11-10 현재 결과: [완료 오류·계정 복구 인수/Native 게시](completion-recovery-acceptance-20261110.md) 완료. 기존 계정은 문구 수정 전에 복구됐고 사용자 기기 테스트 통과, Native 구현5df515f push가 확인됐다. 아래 조사·회신의 복구 미확인/기기 대기·Native 미게시 표기는 당시 기록이며 현재 대기가 아니다. 누락 캐릭터/부분 완료 자료·기기 검증과 일괄 완료 기획은 별도 미완료다.

후속 정정: [기존 v3의 현재 상태 채택·Backend49](bug033-current-state-adoption.md)에 따라 ‘과거 결과는 미확인으로 두고 현재 서버 상태 유지’는 과거 실패 확정과 다른 경로다. 좁힌 원무옵션 correction의 현재 gate 거절·대상 GET 성공·명시 선택 조건에서는 과거 전체 거절 이력 증명을 필수로 두지 않는다. 아래45번째의 엄격한 이력 조건을 이 현재 상태 채택까지 확대해 적용하지 않는다. 실제 계정 막힘 복구는 아직 Native 연결/검증과 사용자 확인이 남는다.

후속 [Native 전체47번째 구현 결과](https://github.com/heo0328/lostparty-backend/issues/17#issuecomment-6741254789): 신규 group 옵션·schema4 원query/불명 이력 보관·반복 안내 보완을 구현하고 자체전체2845PASS/analyze0을 보고했다. 누적 미커밋·미push이며 기존 이력 불명 v3와 기기 막힘은 해결로 표시하지 않는다. 다음 Backend는 [전체46번째](https://github.com/heo0328/lostparty-backend/issues/17#issuecomment-6741157735)의 특정 원요청을 기존 로그/저장 근거로 좁혀 확인할 최소 증거가 있는지 대조·회신해야 한다. 아직 이 추가 확인은 미실행이다.

[Native 전체44번째 제보](https://github.com/heo0328/lostparty-backend/issues/17#issuecomment-6740202376)를 코드/저장 계약과 대조했습니다. **원인 경로가 일치하며 새 서버/API/DB 변경 없이 계정 경로의 기존 옵션 연결로 대응할 수 있습니다.** Native43의2840PASS는 이 기기 버그 해결 근거로 확대하지 않습니다.

앞서 채택한 ‘계정3경로 대칭 무옵션 유지’ 소비안은 참여 profile의 선택성만 확인하고 현재 DB의 공통 group gate를 반영하지 못했으므로 이번 범위에서 정정합니다. 직전114PASS의 계정 HTTP 시험도 group 옵션을 포함한 조합이어서 무옵션 실행 가능의 근거가 아니었습니다.

### 1. 새 계정 명령의 최소 옵션

DB0036에서는 다음3경로에 `group_policy_version=cycle-group-policy-1`을 사용하면 됩니다.

| 경로 | 최소 query/동작 |
|---|---|
| GET completion-correction-context | 기존 target_cycle_key + group_policy_version. 새 확인 token/주간·소유/lifecycle revision을 받음 |
| POST completion-corrections | group_policy_version. 위 새 확인의 token·revision을 사용하고 새 사용자 명령/key로 송신 |
| PUT manual-completion | group_policy_version. 기존 CAS/주차/자격 제한은 그대로 적용 |

**이 계정3경로에 contract_profile/participation_profile은 필수가 아닙니다.** contract_profile을 추가하지 않으면 기존 `recruitment-v2-correct-weekly` / `recruitment-v2-manual` namespace와 응답 의미가 유지됩니다. participation_profile도 생략할 수 있으며 GET/POST에서 대칭 유지합니다. 기존 원요청에는 새 옵션을 주입하지 않습니다.

근거: CycleRoute는3개 query를 이미 허용/선언합니다. cycles.execute는 reserve/원ACK 재생 뒤 group_policy.require_client preflight를 실행하고 DB0035/0036에서 group 표식이 없으면 CLIENT_UPGRADE_REQUIRED를 반환합니다. 수동 PUT도 이 공통 gate에 포함됩니다. 계정 명령은 room_id가 없어 beta 방 일정 gate를 이유로 contract_profile을 요구하지 않으며, correction GET은 DB의 group marker를 token에 포함합니다. 새 POST는 group 표식·token marker·cutover 이후 새 요청 기록·기존 업무 검증을 모두 통과해야 합니다. GET200만으로 POST 실행 가능을 판정하면 안 됩니다.

### 2. 제보된 기존 무옵션 v3 pending의 한정된 종료

다음 조건을 Native가 원 저장/송신 이력으로 확인할 수 있다면, 이 건은 **기존 failed→서버 재조회→현재 상태 유지**로 이번 거절 시도를 정리하고 사용자가 새 확인/새 명령을 하도록 연결할 수 있습니다.

- 해당 계정 correction 원요청의 **최초 송신부터** DB0035/0036 gate가 적용된 환경이고, 같은 회원/namespace/key/body/token·무옵션 query가 일관되게 유지됨.
- 알려진 최초 시도와 재시도는 해당 CLIENT_UPGRADE_REQUIRED이며, 과거 gate 적용 전 송신·group 옵션을 달리 보낸 시도·다른 namespace/명령으로 보낸 이력·이와 모순되는 성공 ACK가 없음. 과거 전송 이력이 불명/손상이라면 이 조건을 만족한다고 추정하지 않음.

이 조건에서는 무옵션 원요청이 늦게 도착하거나 같은 상태로 재전송돼도 group gate에서 막혀 correction 업무 callback에 진입하지 않습니다. 원ACK가 유효하게 보관돼 있다면 gate 이전에 재생되므로, 이 오류를 성공 ACK로 바꾸거나 원래 완료 체크를 지우면 안 됩니다. **실패로 정리하는 것은 Native pending의 해당 거절 시도이지 서버 완료 기록이 아닙니다.** Native의 실제 failed 보관/정리 전이는 기존 구조 안에서 적용합니다.

그 뒤 GET으로 현재 완료 상태를 유지해 표시하고, 사용자가 다시 해제할 때 **group 옵션이 고정된 새 context→새 token/revision→새 key**를 사용합니다. 원query/키/본문/token을 고쳐 같은 pending을 재송신하지 않습니다. 기존 token의 시간/상태 검사를 피하려고 재사용하지도 않습니다. 조회 성공 자체가 pending 삭제 근거인 것은 아니며, 이번은 ‘알려진 모든 시도가 업무 전 gate에서 거절되고 지연 원문도 같은 gate로 차단’되는 좁힌 조건입니다. 일반 CLIENT_UPGRADE_REQUIRED·다른 결과불명/과거 이력으로 확장하지 않습니다.

### 3. Native 주간 pending 옵션 보관

신규 주간 명령은 최초 송신 전에 실제 옵션을 원요청과 함께 고정하고 재시도에도 그대로 사용해야 합니다. 기존 v3 무옵션 row는 원옵션 없음으로 재생하고 현재 기본 옵션을 fallback 주입하지 않습니다. 옵션을 본문에 넣지 말고 기존 query로 전송합니다. 이는 계정 주간 pending에 한정한 최소 소비 변경으로 설계할 수 있으며 서버 wire/공용 큐·다중 저장 확대는 필요하지 않습니다. 저장 형식/호환 decoder의 세부 구현은 Native가 소유합니다.

검증: 격리 PostgreSQL0036·실제 HTTP **2PASS/48.98s**, project lostparty-check-1312a23cf110 exit0/cleanup0입니다. ①수동 PUT 무옵션 반복409/업무 불변→group만 새 key200/원ACK ②실제 공대 완료를 준비한 뒤 무옵션 정정 GET200/POST 반복409·callback 진입0/업무 불변→group만 새 GET/새 key POST200·기존 recruitment namespace/완료 근거 해제·참가 미복원→늦은 옛 무옵션 원문도409/추가 변경0을 확인했습니다. 새 성공 명령은 같은 namespace/digest에서 query를 생략해도 gate 이전에 원ACK가 재생됨도 확인해, 성공 ACK와 gate 거절을 구분했습니다. 마지막 조회는 검증용 합성 호출이며 Native 저장 옵션을 바꾸라는 지시가 아닙니다. 기존2개 계정 경로의 완주2사례이고 이전6/114/Native2840 수와 합산하지 않습니다. 실제 기기 오류/원pending 이력과 로그는 Native44 보고이며 이번 Backend가 실자료/송신 원문을 직접 확인한 것은 아닙니다.

고정 소스16c9cd4/후행기록f744a1e: [공통 실행 순서](https://github.com/heo0328/lostparty-backend/blob/f744a1e2a7aa3bf402f88a697133b19445f1061d/app/raid_rooms/common/cycles.py), [group gate/cutover/token 검사](https://github.com/heo0328/lostparty-backend/blob/f744a1e2a7aa3bf402f88a697133b19445f1061d/app/raid_rooms/group_links/cycle_group_policy.py), [계정 정정](https://github.com/heo0328/lostparty-backend/blob/f744a1e2a7aa3bf402f88a697133b19445f1061d/app/raid_rooms/outcomes/completion_correction.py), [수동 완료](https://github.com/heo0328/lostparty-backend/blob/f744a1e2a7aa3bf402f88a697133b19445f1061d/app/raid_rooms/outcomes/cycle_outcomes.py).

다음 담당은 Native의 계정 옵션 연결/원옵션 보관·해당 거절 분류/표시 반복 해소와 자동 검증이며, 위 과거 이력 조건을 확인하지 못하는 pending은 원문을 보존하고 구체 차이를 회신해 주세요. 사용자 기기 재확인은 이후 단계입니다. 기존 미커밋 변경을 보존했고 서버 구현/OpenAPI/실자료 쓰기·배포·commit/push·Issue 종료는 하지 않았습니다.


조사 기준: feat/character-lifecycle, 현재 HEAD f744a1e/업무16c9cd4. 이번 문서는 미커밋·미push다. 임시 시험 원본 /tmp/lostparty-bug033/test_bug033_probe.py, SHA256 92496188f26b21bd8c826fc29a86825564e071c0f73f828619e85aaa112711f0이며 시험 파일은 작업 트리에서 제거했다. 기존 조사·미커밋 문서는 보존한다. 공식 회신: [전체45번째 Backend BUG-033 확인](https://github.com/heo0328/lostparty-backend/issues/17#issuecomment-6740367084). 전체 댓글45개와 게시 본문 일치를 재조회했고 Issue 상단 상태/다음 담당도 최신화했다.
