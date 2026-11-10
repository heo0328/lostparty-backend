# Issue17 미해결 명령 복구·충돌 범위 조사

2026-11-10 현재 결과: [완료 오류·계정 복구 인수/Native 게시](completion-recovery-acceptance-20261110.md) 완료. 기존 계정은 문구 수정 전에 복구됐고 사용자 기기 테스트 통과, Native 구현5df515f push가 확인됐다. 아래 조사·회신의 복구 미확인/기기 대기·Native 미게시 표기는 당시 기록이며 현재 대기가 아니다. 누락 캐릭터/부분 완료 자료·기기 검증과 일괄 완료 기획은 별도 미완료다.

후속 확인 완료: [완료/개인 완료의 도착 순서 검증·Backend42 회신](completion-retry-order-check.md)에서 Native41의 좁힌3흐름을6PASS로 확인했다. 현재 다음은 Native 연결·자동 검증이며 아래 추가 공용 구조 제안을 이번 선행 조건으로 두지 않는다.

후속 사용자 범위 확정: [Native 전체41번째](https://github.com/heo0328/lostparty-backend/issues/17#issuecomment-6738162109)에 따라 별도 종결 API/fence·복구 큐·다중 저장/공용 저장 구조 확대는 이번 구현 범위에서 제외한다. 아래 추가 계약 제안은 조사 당시 근거이며 현재 보정의 선행 조건이 아니다. Backend 다음 확인은 완료/개인 완료의 기존 token/CAS·완료 상태와 지연/신규 요청 경합3흐름으로 한정한다. 원pending 자동 삭제·무조건 새 key 전송과 단일 slot 해결은 승인/완료된 것이 아니다.

2026-11-09 / Backend / feat/character-lifecycle / 조사 소스 f744a1e(업무 구현16c9cd4). [Native 전체38번째 요청](https://github.com/heo0328/lostparty-backend/issues/17#issuecomment-6737308328)에 대한 정의·설계 협의다. 기능 코드/OpenAPI/DB 변경과 새 정책 확정은 하지 않는다. [완료 프로필 보정](completion-profile-contract-fix.md)·[기존 오류 분류](completion-context-profile-audit.md)를 유지한다. Native 로컬 코드는 읽지 않았으며 slot/표시 상태 정보는 Native38 보고를 근거로 한다.

## 결론과 적용 수준

| 요청 | 판정 | 조사 결론 |
|---|---|---|
| 원ACK 재생·처리 중 복구 | 기존 지원 | 온전한 원요청과 같은 actor/operation/key·digest, 유효 인증/요청 및 보관 중 성공 기록이 필요하다. 원요청 재전송은 결과 조회 전용이 아니며 미실행이면 실제 실행할 수 있다. |
| 버튼/안내의 수명 분리 | 추가 정의·Native 구현 필요 | 첫 오류부터 취소·창 종료 가능. 원pending은 보존하며 서버 취소로 해석하지 않는다. 늦은 ACK가 닫힌 오류창을 되살리지 않게 Native에서 관리한다. |
| 확정 거절 뒤 로컬 정리 | 조건부 기존 지원/정의 필요 | 과거 유실·지연/처리 중인 시도가 없고 이번 시도의 확정 거절을 받은 경우에 한해 해당 시도를 종결할 수 있다. 과거 결과불명까지 자동 종결하는 증거는 아니다. |
| 장기 미해결의 미처리 확정·지연 요청 차단 | 현재 API로 불가능 / 서버 변경 필요 | ACK 미발견·GET 현재 상태·24시간 경과·lease 만료로 미처리를 증명할 수 없다. 아래 차단 fence/종결 계약은 제안이며 미합의·미구현이다. |
| 독립 작업의 제한 축소 | 추가 정의·Native 저장/transport 변경 필요 | 서버에는 Native owner 단위의 미해결 slot이 없다. 단일 slot 해제와 업무 충돌 판정은 별도이며 UI 조건만 풀면 다른 원요청 저장이 거절될 수 있다. |
| 새 오류 code/details.reason | 현재 단계 불필요 / 추가 요구는 미결정 | 기존 code+HTTP+로컬 전송 이력으로 안전한 행동은 구분된다. 결과 증명이 부족한 문제는 새 오류 문구/코드만으로 해결되지 않는다. |

## 1. 서버가 실제로 보장하는 것

[reserve/commit_result/release](../../../../app/game_accounts/common/support.py)의 저장 식별자는 actor+operation+UUID key다. beta 명령은 [cycles.execute](../../../../app/raid_rooms/common/cycles.py)에서 beta-v2- 접두 operation과 원 raw_body를 포함한 payload digest를 사용한다. 비beta는 별도 recruitment-v2- namespace다. 같은 key여도 operation/profile namespace를 바꾸면 같은 요청의 복구가 아니다. 모든 query가 digest에 직접 저장된다고 가정하지 않는다. participation/group query는 토큰·route/기능 검사에도 영향을 주므로 **원 method/path/query/body/key를 모두 유지**한다. digest를 맞추려고 원본문을 재구성하지 않는다.

reserve는 인증 확인→digest 충돌→완료 기록 만료/재생→실행 lease 순으로 검사한다. 유효 성공 ACK는 업무 재검증보다 먼저 반환되지만, route query/DTO/인증·기능 gate를 전부 우회하는 것은 아니다. 로그아웃/회원 전환 뒤 다른 회원으로 재생하지 않는다. 같은 회원의 정상 재인증은 원 명령 식별을 보존하는 조건으로 기존 인증 흐름을 따른다.

성공 ACK와 업무 변경은 같은 transaction에서 commit된다. 실행 lease는30초, REQUEST_IN_PROGRESS의 Retry-After는2초다. lease가 끝나면 같은 요청이 generation을 올려 takeover할 수 있으며 이전 generation의 commit_result는 거절된다. **30초는 응답/전체 처리 제한이나 미처리 증거가 아니다.** 서버는 game-mutations-v1 advisory transaction lock으로 변경을 직렬화하지만, 오래된 클라이언트 요청의 미래 도착까지 막지는 않는다.

완료/개인 완료는 [cycle_outcomes.execute](../../../../app/raid_rooms/outcomes/cycle_outcomes.py)에서 권한·서명 context·현재/실제 주차·CAS·최종 시각을 검사한다. context 수명은 최대120초/주차 경계이며 token profile도 일치해야 한다([sign/verify_token](../../../../app/raid_rooms/participation/cycle_lifecycle.py)). 성공 ACK가 보관돼 있으면 context가 만료돼도 원ACK 재생은 먼저 가능하다.

**보관 시간은 다르다.** 성공 완료 시점 completed_at부터24시간은 ACK 재생, 그 뒤 IDEMPOTENCY_EXPIRED. [cleanup](../../../../app/game_accounts/rosters/cleanup.py)은24시간 뒤 result를 지우고 expired 표식,48시간 뒤 완료 row 자체를 삭제한다. 미완료 row도 lease_expires_at 기준48시간 경과 뒤 삭제 대상이다. cleanup 실행 지연과 무관하게 reserve는24시간을 검사한다. Native의 최초 송신/저장 후24시간 보류와 서버의 completed_at+24시간은 동일한 시계가 아니다. 현재 클라이언트 보류를 임의 완화하지 않는다. **48시간 뒤에는 같은 key도 새 reserve가 될 수 있으므로 무기한 멱등 보장은 없다.** 오래된 완료 token은 만료로 새 실행이 차단되더라도, 사라진 과거 성공을 복원하는 증거는 되지 않으며 모든 공유 명령에 같은 시간 제한이 있다고 일반화하지 않는다.

추가 예외: [beta_schedule.reconcile_before](../../../../app/raid_rooms/schedules/beta_schedule.py)는 시각 도래 효과를 별도 transaction으로 반영한다. 이후 사용자 명령이 거절돼도 이 효과는 남을 수 있다. 따라서 ‘해당 완료 변경은 rollback’과 ‘DB 전체 불변’은 다르다. dedup의 running/retryable 상태 전환도 업무 완료 효과가 아니다.

## 2. 처리 의미와 버튼 내부 행동

아래 거절은 **해당 시도**의 의미다. 이전 응답 유실·지연 시도가 있으면 이 표만으로 과거 명령까지 미처리 확정하지 않는다. 최초 시도의 순서/송신 상태를 모르면 결과불명/검토를 유지한다.

| 현재 응답/상태 | 해석 | 지원 행동·금지 |
|---|---|---|
| 유효한 원요청의 성공2xx ACK | 해당 명령의 commit 결과 | ACK를 기존 Native 영속 경로에 먼저 반영한 뒤 pending 제한 정리. 최신 화면 GET 실패는 조회만 재시도하며 완료 재송신/새 명령 생성 금지. 늦은 ACK는 자료 반영만 하고 창 재개 금지. |
| 409 REQUEST_IN_PROGRESS | 실행 lease/최종 fencing 경합. 성공·실패 미확정 | Retry-After를 따르고 사용자 재시도에서 원요청 그대로 전송. 병렬 새 명령/새 키 생성 금지. 창 취소는 가능. |
| timeout/응답 미수신/연결 해제·일반5xx/503 SERVICE_UNAVAILABLE | commit 응답 유실 가능성을 포함한 결과불명 | 온전하고 보관 조건을 만족하는 원요청 복구, 또는 GET만 조회. HTTP 재송신은 미실행 명령을 실행할 수 있으므로 사용자의 재시도 행동과 연결한다. |
| 503 RECRUITMENT_COMMAND_NOT_READY / GROUP_FEATURE_NOT_READY | 현재 시도 기능 gate 거절 | 서버 준비 확인/조회 새로고침·안내 취소. 빈번한 명령 반복 금지. 과거 유실 요청의 실패 증거로 쓰지 않음. |
| 400 CONTEXT_INVALID / TARGET_SCOPE_MISMATCH / INVALID_REQUEST | profile/서명·scope/입력 검증 거절 | 현재 상태/context 조회와 진단(request_id) 가능. profile/토큰/본문을 고쳐 원pending 덮어쓰기 금지. 이전 불명 시도가 없거나 안전 종결 증거 확보 후에만 새 확인·새 사용자 명령. |
| 409 COMMAND_CONTEXT_EXPIRED / TARGET_CONTEXT_STALE / REVISION_CONFLICT / CYCLE_CHANGED 등 | 확인 정보/현재 상태가 달라 현재 실행 거절 | 새 context는 새 결정의 자료다. 기존 pending 복구용 원snapshot을 교체하지 않는다. 종결 조건을 충족한 뒤 사용자 재확인→새 키/새 명령이며 자동 주차 전환/자동 재명령 금지. |
| 403 권한·401 인증·404 비공개/없음·409 ROUND_NOT_ACTIVE/ROOM_NOT_ACTIVE | 현재 접근/업무 상태 거절 | 로그인/해당 대상의 허용된 GET 확인. 404로 타인 존재 추론 금지, ROUND_NOT_ACTIVE만으로 이미 완료라 단정 금지. 인증 오류가 과거 ACK 없음을 뜻하지 않음. |
| 409 CLIENT_UPGRADE_REQUIRED | 현재 계약 지원 부족 | 지원 계약/앱 적용. 원정대 갱신을 해결책으로 안내하거나 기존 profile 제거 금지. |
| 409 IDEMPOTENCY_CONFLICT | 같은 namespace/key에 다른 digest | 원요청 손상/잘못된 매핑 검토. 현재 보낸 변형을 다시 시도해도 원결과 조회가 아님. 원query/본문/키 수정·새 키 복제 금지. |
| 409 IDEMPOTENCY_EXPIRED | 같은 식별/digest에 completed_at 기록이 있으나 재생 기간 종료 | 정상 cycle 경로에서는 이전 완료 기록의 신호이며 ‘미처리’가 아님. ACK 상세는 복원 불가하므로 성공 ACK를 합성하지 말고 검토·허용 GET. 일반적인 실패/미처리 종료로 분류 금지. |
| 429 제한 | 현재 요청의 제한 거절 | Retry-After 준수. 과거 유실 시도의 결과 증명이 아님. |
| REQUEST_REVIEW_REQUIRED / LOCAL_STORAGE_UNAVAILABLE / UNRESOLVED_REQUEST_EXISTS | Native 로컬 복구/저장 제약 | 서버 오류로 새로 추가하지 않는다. 보존 정보가 불완전하면 추측 재송신 금지. 첫 오류부터 안내 취소 가능. |

버튼명과 최종 문구/배치는 Native·사용자 소관이다. ‘재시도’는 상태에 따라 원요청 전송 또는 ACK 이후 GET만 재조회이며, ‘새로고침’은 조회다. ‘확인’으로 새 명령을 보내는 것은 과거 불명 요청이 안전하게 해결된 뒤 새 확인 흐름에서만 가능하다. ‘취소’는 언제나 표시 종료이며 서버 명령 취소/로컬 기록 폐기를 뜻하지 않는다. 읽기 성공만으로 pending을 삭제하지 않는다.

## 3. 복구 종료의 증거와 장기 미해결

1. **성공 종료(기존 지원):** 같은 환경/회원·원 명령과 대응하는 계약상 성공 ACK를 수신·검증·영속 반영. 이미 저장한 신뢰 가능한 성공 ACK의 로컬 정리도 가능하다. 서버 request_id는 진단 식별자이며 command key/ACK 조회 API가 아니다.
2. **이번 시도 거절 종료(조건부):** 과거 유실/지연/진행 중 시도가 없고, 로컬이 이번 송신을 추적하며 명시적 거절 응답을 받았다면 해당 시도 거절로 정리할 수 있다. ‘과거 불명 시도 있음/모름’이면 일반4xx/기능503 수신만으로 이 조건을 충족하지 않는다. 취소 버튼으로 이 증거를 대신하지 않는다.
3. **미처리 확정 종료(현재 불가능):** 일반 GET의 미완료/참가 없음, ACK 부재, token/lease 만료,24시간 경과는 과거 효과 없음/미래 실행 불가를 동시에 보장하지 않는다. token 만료는 새 실행 가능성 일부를 제한할 뿐 과거 결과 증명은 아니다.
4. **원정보 손상:** 완전한 영속 원요청을 검증해 복원할 수 있을 때만 기존 복구를 사용한다. key/operation/path/body 일부가 없거나 신뢰할 수 없으면 현재 조회로 원문을 재구성하지 않는다. snapshot만 손상됐더라도 wire만 임의 재송신하도록 완화하지 않고 Native의 기존 검토 정책을 유지한다.

**추천 단계:** 현 계약으로 표시 수명/취소와 안전한 원요청·GET 복구부터 설계하고, 장기 미해결은 검토 상태로 유지한다. 장기 검토를 해제하는 사용자용 ‘안전 종료’까지 필요하면 다음 최소 서버 계약을 별도 합의한다. 영구 보류가 요구의 최종 해결이라고 표시하지 않는다.

**미합의 최소안 — 명령 종결/차단 fence:** 명령 결과 조회만 추가하는 것보다, 인증된 actor+고정 operation+key와 신뢰할 수 있는 식별 증거에 대해 원자적으로 `기존 완료 결과/처리 중·경합/미처리로 종결 후 차단/확정 불가`를 구별하는 계약을 검토한다. 이는 새 wire 이름/route/DTO를 확정한 것이 아니다.

- 결과 조회에서 row 없음은 미처리 증거가 아니다. 종결은 원 요청이 늦게 도착해도 실행할 수 없게 새 예약도 차단해야 한다.
- 실행 중 요청과 같은 serialization/row locking·generation fencing에 참여해, 먼저 완료한 요청이면 완료 결과를 반환하고 미처리 차단이 먼저 확정됐다면 이전 worker의 commit과 이후 동일 요청을 거절해야 한다. 사업 변경+ACK와 종결 fence의 원자성을 검증해야 한다. 현재30초 lease/release만으로는 이 계약이 아니다.
- 이미48시간 정리로 잃은 결과는 새 tombstone을 만든다고 복원되지 않는다. 이런 과거 요청은 명시적으로 확정 불가여야 하며 ‘미처리로 안전 종료’라고 반환하면 안 된다.
- fence 삭제 후 지연 요청이 재실행되지 않도록 보관 기간/최대 접수 기한의 서버 강제 기준이 필요하다. 현재48시간 삭제 정책을 그대로 재사용할 수 없다. 잘못된 digest의 요청도 우회하지 못해야 한다.
- namespace/회원 격리, key/원문 일부 손상 시 식별 가능한 최소 증거·의도치 않은 다른 요청 차단 방지, 인증 복구·감사·개인정보, ACK 결과 보관/손실 정책도 합의해야 한다. 이 변경은 DB 영속 상태/모든 해당 reserve·commit 경로와 계약/시험에 영향을 준다. 단순 새 code 추가로 대체할 수 없다.

## 4. 제한할 업무 범위 — Native slot과 구분한 제안

서버의 global mutation lock은 일시 직렬화 장치다. 미해결 명령마다 사용자 전체를 지속 잠그는 API 규칙은 없다. 아래는 Native 제한을 줄이기 위한 **설계 후보**이며 사용자 정책/Native 저장 구현을 확정하지 않는다. 모르는 영향 범위를 임의 축소하지 않는다.

| 미해결 명령과 새 행동 | 범위 제안·근거 |
|---|---|
| GET·다른 화면 조회·안내 취소 | 기존 인증/조회 권한 안에서 허용 가능. 조회 성공과 명령 종결은 분리. |
| 같은 room·실제 T/generation의 완료·개인 완료·캐릭터 교체·탈퇴/강퇴·승계·일정/설정·참가 승인 | 보수적으로 충돌 처리. 개인 완료도 공유 members/plan revision·세션/예약·제안 및 마지막 참가 시 주차 종료를 바꾼다. 다른 round/다른 회원이라고 독립으로 단정하지 않음. |
| 같은 room의 다른 T | 대상 한정 완료/취소·승계는 직접 효과가 해당 T에 한정되지만, C를 원천으로 하는 N 참가/개설은 source 캐릭터/완료/권한 증거를 공유한다. 방 전체 leave/end/common-settings는 C/N을 읽고 변경할 수 있다. T만 다른 것으로 독립 판정 금지. |
| 다른 room·같은 실제 주차 | 같은 회원+캐릭터+raid의 WeeklyState/WeeklyOccupancy, 같은 회원의 겹치는 TimeReservation/BetaPromiseReservation, 방 참가 수 제한 등이 공유되면 충돌. 캐릭터가 달라도 회원 시간/가용표·참가 수 공유 가능. room_id만 비교하면 부족하다. |
| 다른 room·다른 실제 주차 | room/generation·원천 C/N·주간 점유·예약 시간·공통 회원 설정/가용표/활동 한도 등 실제 공유 의존성을 대조한 뒤 조건부 독립. 일부 공통 revision은 새 context 재조회/CAS 거절로 처리할 수 있으며 공통 revision이 있다는 이유만으로 앱 전체 영구 제한을 설계하지 않는다. |
| 공대장 승계/연계 주차/방 전체 명령 | 대상 actual leader와 그룹 정책 변화·원천/목표 주차·persistent membership·수용 인원/예약을 함께 고려. 방 전체 종료/탈퇴는 같은 room의 두 주차를 포함한다. |
| 환경/회원 전환 | 저장 namespace를 격리·보존. 다른 회원에게 원요청/ACK/오류 안내가 전파되면 안 된다. |
| 식별·영향 snapshot이 손상/누락 | 충돌 없음으로 판정할 수 없다. 기존 저장 owner 제약/검토를 유지하고 해당 오류창에서는 나갈 수 있게 한다. |

근거: [완료 처리](../../../../app/raid_rooms/outcomes/cycle_outcomes.py), [주차 참가·점유](../../../../app/raid_rooms/admissions/cycle_admission.py), [C 원천의 N 참가](../../../../app/raid_rooms/admissions/cycle_continuation.py), [대상 취소/승계](../../../../app/raid_rooms/participation/cycle_leadership.py), [C/N 공통 명령](../../../../app/raid_rooms/participation/cycle_common.py), [예약·개인 가용표 기준](../../../../app/raid_rooms/schedules/beta_schedule.py), [활동 한도 projection](../../../../app/raid_rooms/common/active_usage.py).

Native가 보고한 PK=(environment,userId,owner) 및 owner의 다른 original 거절은 별도 제약이다. canAct만 바꾸면 동시 원요청 저장이 불가능할 수 있다. 최소 후보는 원 명령별 영속 레코드/복구 큐와 별도의 충돌 footprint를 관리하고, 알려진 독립 작업만 허용하는 것이다. 기존 미해결 row/snapshot은 이행 때 유실/변형하지 않는다. 자동 background 재송신과 보관 만료 후 재전송은 이 제안의 승인이 아니다. 정확한 저장 변경/범위는 Native가 설계·사용자와 확인해야 한다.

## 5. 오류 세분화와 검증 근거

CONTEXT_INVALID의 profile/해독 실패는 모두 현재 시도 검증 거절이며, 현재 안전 행동은 원문 보존·조회·진단이다. REQUEST_IN_PROGRESS는 lease 보유와 final fencing 거절을 같은 code로 내지만 둘 다 완료 결과 미확정으로 처리할 수 있다. SERVICE_UNAVAILABLE의 rollback/commit 응답 유실은 code/status로 내부 구분할 수 없으므로 모두 보수적으로 결과불명이다. 이들을 새 reason으로 나눌 필요는 현재 UX에서 확인되지 않았다. 원요청의 미래 실행 차단·과거 결과 확정이 요구될 때는 오류 세분화보다 종결 계약의 증명이 필요하다.

ErrorDetails는 conflicts/available_at/failed_cycle_key의 extra-forbid다([정의](../../../../app/raid_rooms/schemas/cycle_wire.py)). REQUEST_REVIEW_REQUIRED 등 로컬 코드와 서버 DTO를 혼합하지 않는다. 새 code/필드와 운영 진단 로그 보강도 이번에 구현하지 않았다.

이번은 **소스/저장 계약·기존 시험 대조**이며 서버/DB/실자료 재실행·새 자동 시험은 없다. 기존 완료/정정/일정·참가/beta114PASS는 [직전 보정 검증](completion-profile-contract-fix.md)의 실행 근거로만 재사용하며 새 종결/slot 축소 검증으로 표시하지 않는다.

- [원ACK 우선·만료/stale rollback·동시 완료](../../../../tests/raid_rooms/outcomes/test_recruitment_cycle_outcomes.py)의 test_completion_original_ack_after_week_and_authority_change, test_completion_expired_context_and_stale_snapshot_rollback, test_duplicate_concurrent_completion_has_one_effect_and_original_receipt. 업무 시계를 이동한 ACK 시험을 저장소의24시간 보관 연장 증거로 쓰지 않는다.
- [완료/교체 경쟁·이력/능력표식·원ACK](../../../../tests/raid_rooms/participation/test_roster_public_contract.py), [혼합 M/P·반대 주차·탈퇴/승계 rollback](../../../../tests/raid_rooms/participation/test_roster_followup_commands.py), [시각 효과의 독립 commit](../../../../tests/raid_rooms/admissions/test_beta_recruitment.py)의 test_independent_due_commits_when_stale_join_rejected.
- [공유 dedup 저장소의 lease takeover/fencing](../../../../tests/game_accounts/test_game_accounts.py)의 test_lease_takeover_fences_old_worker는 시험 소스 근거다. 이번에 이 파일을 새로 실행하거나 모든 보관 삭제/지연 종결 경합을 검증했다고 주장하지 않는다.

향후 Native 변경은 원pending/늦은 ACK·창 닫힘/재진입·동일 owner의 독립 명령 저장/복구·같은 T 및 C/N·교차 방 예약/주간 점유·손상/24시간 보류를 시험해야 한다. 종결 API를 선택하면 지연 최초 도착·in-flight commit 경합·원ACK/24h/48h cleanup·손상 식별·다른 회원·DB rollback·보관 만료 후 우회까지 별도 격리 검증이 필요하다. Native 소비와 사용자 확인 후 범위를 확정한다.

## 인계 상태

[전체39번째 Backend 조사·정의 회신](https://github.com/heo0328/lostparty-backend/issues/17#issuecomment-6737640898) 게시 완료. 실제 전체 댓글39개와 게시 본문 일치를 재조회했고 Issue 상단 범위/상태·다음 담당도 갱신했다. 답변은 고정 f744a1e의 코드/기존 계약·시험 링크를 포함하므로 미게시 로컬 문서를 읽어야만 소비 가능한 인계가 아니다. 이 조사 문서는 미커밋·미push로 보존한다.

다음 Native는 복구 의미/slot·충돌 후보를 대조하고 사용자와 최소 범위를 협의한다. Backend는 선택된 추가 계약이 있을 때 상세 설계를 이어간다. 장기 미해결 종결·fence 보관/손상 식별 정책과 Native 동시 저장 변경은 아직 확정하지 않았다. 현재 새 서버 기능/계약 구현·DB/로컬/운영 반영·commit/push·Issue 종료는 하지 않았다. 문서/동결/경로/diff 검사만 수행했으며 서버/DB는 재실행하지 않았다.
