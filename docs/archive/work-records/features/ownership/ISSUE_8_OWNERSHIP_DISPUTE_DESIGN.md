> **보관된 작업 원문:** 아래 현재·다음·미구현 표기는 작성 당시 상태입니다. 현재 설명: [ownership](../../../../features/rosters/ownership/README.md) · [registration](../../../../features/rosters/registration/README.md). [문서 대응표](../../../../engineering/documentation/README.md). 원문 바이트와 근거는 기준 커밋 `7f7f767`에서 확인합니다.

# Issue #8 — 타인 소유 원정대 24시간 챌린지 계약안

현재 상태(2026-10-18): 아래는 합의 당시 설계 근거다. Backend 구현·격리 검증과 DB0015 반영은 [개발 안내](ISSUE_8_OWNERSHIP_DISPUTE_DEVELOPMENT.md)를 따르고, 실제 REST 계약은 `openapi/openapi.yaml`을 기준으로 한다. Flutter 적용·실기기 인수는 별도다. 제안된 자동 삭제는 미추가이며 공통 날짜 기록은 [DB 기준](../../../../engineering/data/record-timestamps.md)을 따른다.

2026-10-18. **설계/검토안, 미구현·미배포**. 기준 구현은 `feat/raid-services` / `69d9a4043679d1654eaae2f50ece59811ae01b08`이다. REST 원본 OpenAPI에는 아직 추가하지 않는다.

근거: [#8 전체133번째 Flutter 요구](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6236706515), [현재 소유 정책](ISSUE_8_CURRENT_OWNER_POLICY_DEVELOPMENT.md), [장비 증거](ISSUE_8_LIVE_EQUIPMENT_PROOF_DEVELOPMENT.md), [생명주기](ISSUE_8_LIFECYCLE_REVIEW.md), [그룹 G2](../groups/ISSUE_12_GROUP_G2_SPEC.md), [주간원장](../raids/ISSUE_11_RAID_WEEKLY_DEVELOPMENT.md). [134번째 Flutter](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6236754707)는 영어 혼합 입력 검색의 사용자 기기 성공 확인이며 이 설계와 별개로 완료다.

공유 원문: [#8 전체135번째 Backend 계약안](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6236916583). 현재 문서는 미커밋/미push이며 댓글로 검토안을 공유했다. 후속 사용자 결정/기존 정책 확인 요청은 [#8 전체136번째 Backend](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6236938659)를 따른다. 137·138번째조사/정책과140번째기술검토를수신했고V2보완안을작성했다. [#8 전체141번째 Backend V2보완답변](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6237543030)으로원문/JSON초안을공유했다. [#8 전체142번째 Flutter 최종소비검토](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6245421798)로기술차단없음을확인했다. 다음Backend구현·검증이며동일계약검토대기가아니다.

## 1. 확정 정책과 제안 구분

사용자 확정:

- 타인 소유 판정 시 시도자에게 즉시 `타인에게 인증 완료된 원정대입니다.`를 표시한다. 타인의 개인정보/회원 ID/Google 정보는 공개하지 않는다.
- 새 시도자의 **10분 장비 확인 성공 transaction**에서 24시간 챌린지가 시작된다. 검색/클릭/10분 장비 확인 시작만으로 분쟁은 열리지 않는다. 장비 확인 성공은 소유 이전 성공이 아니다.
- 기존 소유자는 **새 10분 장비 인증 성공으로 방어**한다. 평소 본인 재인증 차단의 예외는 이 분쟁의 방어 전용이다.
- 방어 성공 없이 24시간이 지나면 **최종 검사 후 자동 이전**한다. 시도자의 두 번째 장비 인증을 필수로 두지 않는다.
- 기간 중 **기존 소유자 사용 유지**, 시도자에게는 해당 원정대의 소유 사용 권한을 주지 않는다.
- 알림은 **앱 내 안내 우선, 앱 밖 푸시는 후속**으로 확정했다.
- [138번째 Flutter 전달](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6237128139)의 사용자 추가 결정: **방어 성공 후 영구 인증금지·별도 재도전 대기시간 없음**. 다시 장비 확인에 성공하면 새24시간방어를 시작한다. API quota/멱등·중복차단은 유지하며 후속직접답변으로원정대당진행분쟁최대3건/일괄방어/먼저성립한분쟁우선처리를확정했다.

아래의 API/상태/동시성/복원은 Backend 제안이다. 동시 분쟁·재도전 간격은10절의후속사용자결정을반영한다. 기존정책조사뒤사용자직접선택을받았으며과거제안을확정정책으로혼동하지않는다. 과거 수동 운영자 승인·스크린샷·인증금지 정책을 자동 장비 경로에 가져오지 않는다. 설계 시작 승인을 실제 소유 변경 실행 승인으로 해석하지 않는다.

## 2. 현재 구현과 변경점

현재 `service.apply(confirm)`은 장비 수집/비교/고정 context가 통과해도 `binding_mode=pending`이면 `ACCOUNT_BINDING_EVIDENCE_PENDING`을 반환한다. live adapter는 타인의 기존 원정대를 이전하는 BindingEvidence를 만들지 않는다. VerificationOut 8필드/10분 기한은 24시간 분쟁을 나타내지 못한다.

새 경로는 기존 장비 수집·6부위/무작위1~3개 해제·요청 외 장비 유지·대상 서버/원문 이름/roster digest·키/세션/revision 검사를 재사용한다. 이후 **서버가 발급하는 분쟁 기록과 확정된 제품 이전 정책**을 별도 권한 근거로 사용한다. 이름 일치나 장비 확인을 provider 영구 ID/동일 세대/전체성 증거인 BindingEvidence로 재명명하지 않는다.

현재 claim은 조회 대상의 충돌/등록 매핑 근거이고 영구 신원 증거가 아니다. 분쟁 후보는 fresh siblings의 관찰된 모든 기존 claim이 하나의 현재 account에 속하고, 선택 대상이 그 account의 active/confirmed 현재 UUID/claim으로 고정될 때만 인정한다. 대상의 claim 부재/퇴역/여러 account 혼입/불명확은 `unresolved`로 보류한다. 대소문자는 입력 해석에만 허용하고 고정 target/server/UUID/claim 비교는 exact다.

영속 provider ID가 없어 관찰 사이 동일 이름 삭제·재생성을 완전히 식별할 수 없는 기존 한계는 유지된다. 이 경로의 권한은 사용자가 정한 앱 내 소유권 분쟁 정책이며, 그 한계를 없애는 기술적 증명으로 보고하지 않는다. 불명확한 후보를 자동 병합하거나 새 account를 만들어 타인의 claim을 빼앗지 않는다.

## 3. 두 단계 상태표

### 3.1 장비 확인

| 상태 | 사건 | 결과 |
|---|---|---|
| `pending` | 시도자 검색/시작 | 서버 관계 `other` 안내, 10분 장비 확인만 발급 |
| `pending` | mismatch/provider 실패 | 기존 pending/안전한 reason, 분쟁 생성0 |
| `pending` | `now >= equipment_expires_at` | `expired`, 분쟁 생성0 |
| `pending` | 장비 성공·후보/현재 소유 검증 통과 | `passed`, 분쟁 `defending`을 원자 생성, 소유 유지 |
| `pending` | 취소 | `cancelled`, 분쟁 생성0 |
| `passed` | 같은 요청 재전송 | 기존 proof/dispute ID 회수, 기한 연장0 |

신규 미점유 원정대의 장비 성공은 기존 신규 인증/등록 연결 흐름을 사용한다. 본인 소유는 일반 시작409 `ALREADY_VERIFIED`를 유지한다. 충돌을 타소유로 확정할 수 없으면 별도 보류로 처리하고 가짜 24시간 기한을 반환하지 않는다.

### 3.2 소유권 분쟁

| 저장 상태 | 허용 사건/조건 | 다음 상태·소유 처리 |
|---|---|---|
| `defending` | 기존 소유자 방어 시작 | 새 방어 proof만 발급. 분쟁/24시간 연장 없음 |
| `defending` | 방어 장비 성공 commit 시각 `< defense_deadline` | `defended`, 기존 소유 유지·시도자 소유0 |
| `defending` | 시도자 취소 commit 시각 `< defense_deadline` | `cancelled`, 기존 소유 유지 |
| `defending` | `now >= defense_deadline` | 방어/취소 거절, 최종 처리 작업 가능 |
| `defending` | 만기 후 최종 fresh 관찰/현재 상태/후처리 검증 모두 통과 | `transferred`, 소유 이전1회 |
| `defending` | 만기 후 일시적 provider/DB 장애 | 상태 유지·재시도 예약, 소유 유지 |
| `defending` | 기준 owner/revision 교체·anchor/claim 충돌 등 영구 불일치 | `invalidated` 또는 `review_required`, 자동 이전0 |
| `review_required` | 자동 확정 불가 | 이유 조회 가능·자동 대기열 제외, 기존 소유 유지. 시도자 철회는 허용 제안, 그 외 재검토 계약 전 관리자 임의 이전 없음 |
| terminal | 다시 confirm/settle/replay | 이미 저장된 결과, 이전/알림 중복0 |

`phase`는 서버가 조회 시 계산한다: `awaiting_defense` / `settlement_due` / `retrying_settlement` / `finished` / `review_required`. 기한 도달만으로 소유가 바뀌었다고 표시하지 않는다. `defended`, `transferred`, `cancelled`, `invalidated`는 terminal이다. `review_required`도 같은 account의 새 자동 분쟁을 막아 미해결 권한 변경이 겹치지 않게 하는 제안이다.

시각은 PostgreSQL UTC와 `server_now`를 사용한다. `started_at`은 시도자 장비 성공 최종 commit 검사 시각, `defense_deadline = started_at + 24h`이며 매일 자정/기기 시간/장비 시작시각과 무관하다. 방어proof의만료는`min(방어시작+10분,같은현재소유권진행분쟁의가장빠른deadline)`이며늦게시작된분쟁으로기한을연장하지않는다. 시작이 기한 전이어도 성공 commit이 기한 이상이면 방어 실패다. transaction 최종 flush 후 기한 경합을 재검사해 장비 성공과 분쟁 변경을 함께 rollback한다.

## 4. V2 기술계약 보완 — 140번째 검토 대응

정확한11동작/입출력·nullable/상태/actions·회원별proof목록발견·새기기복원·다른유효캐릭터방어·등록참조/한도는 [V2 기술계약 보완안](ISSUE_8_OWNERSHIP_DISPUTE_V2_CONTRACT.md)과 [검토용 OpenAPI 초안](../../../../features/rosters/ownership/examples/ownership-dispute.openapi.json)을기준으로한다. 기존135번째10동작/고정target방어/settle200·202이중본문은대체했다. 실행OpenAPI/기존V1은변경하지않았다.

사용자추가확정은원정대당진행분쟁최대3건·동일현재소유권의진행분쟁모두일괄방어·먼저성립한분쟁부터만기처리/이전후나머지종료다. 별도재도전대기는없다. proof목록을추가해11동작이며settle는200 DisputeOut 예약ACK만사용하고worker완료는GET으로확인한다. 방어는같은account의현재소유/claim/usable캐릭터를본인이명시선택한다. 개별prooftarget은그시작때고정하고자동개명/타account승계는없다.

## 5. 양측 UX·통지/복원

시도자: 검색/시작에서 타소유 안내 → 일반10분 장비 조작 → 성공 시 `24시간 방어 대기`와 서버 기한/취소 제공 → 최종 상태별 완료/방어됨/검토필요. 이전 전 계정 관리 성공 화면·활동설정으로 이동하지 않는다. 아직 분쟁이 열리지 않은 검색에는 실제 마감 대신 `장비 확인 성공 후 24시간`을 표시한다.

기존 소유자: 앱 로그인/복원 시 내 분쟁 목록에서 `소유 원정대에 인증 도전이 있습니다`와 기한·방어 동작 제공. 방어 버튼에서 전용 proof를 시작하고 성공하면 도전 종료를 표시한다. 일반 본인 재인증 화면의 ALREADY_VERIFIED 차단은 유지한다.

분쟁 DB row/양측 feed revision/최소 이벤트를 같은 transaction에 저장하고 앱 시작·복귀 시 목록 GET으로 복구한다. 기본 polling은 화면이 보이는 동안 제안30초, background 중지·네트워크/앱수명 경계에서 재조회한다. 기기 타이머는 표시 전용이며 `allowed_actions`도 명령 직전 서버가 재검사한다.

현재 push/메일/통지 인프라는 없다. 이번 최소안의 통지는 **앱 내 영속 조회**이며 앱이 닫힌 기존 소유자에게 push 전달했다고 주장하지 않는다. 사용자가 확정한 시작 기준은 장비 성공시각이고 앱 열람 시각으로24시간을 늦추지 않는다. 앱 밖 push는 사용자 결정에 따라 후속 범위이며 이번 설계의 필수 선행 조건이 아니다. 알림 미열람만으로 방어 성공/기간 연장/이전 실패를 추측하지 않는다.

## 6. 저장·동시성·자동 만기 처리

제안 additive 구조(물리명/다음 migration 번호는 구현 때 확정): ownership_control_proofs / ownership_disputes / ownership_dispute_events / ownership_dispute_member_heads. 기존 verified 이력은 수정하지 않는다.

- dispute: 방어generation·account_id/고정 target UUID·claim/lifecycle revision/원문주소, owner_at_start/challenger_id, base_ownership_revision, 장비 성공 proof 참조 unique, policy_version, started/deadline/resolved/state/version, 다음시도·lease generation·안전한 실패분류. 원본 provider JSON/키/장비 상세를 이벤트에 넣지 않는다.
- proof: actor/purpose/parent dispute, immutable snapshot·receipt/baseline/10분 기한, version/result/분쟁 연결. actor/session/keyversion·원정대 소유·대상 상태를 네트워크 전후에 재검사한다. 지난24시간 동안 시도자의 API키 교체만으로 이미 유효하게 성립한 분쟁을 지우지는 않는다. 삭제된 회원/정지·법적 접근상실 등은 최종 정책 검증에서 자동 이전을 보류한다.
- 진행분쟁은account당최대3건(defending/review_required), proof당dispute1개. account락아래slot·현재소유revision·본인중복을검사한다. 네번째동시성공은분쟁생성없이blocked로구분한다. 다른회원dispute ID/개인정보는노출하지않는다. 장비시작은자리예약이아니다. 동일현재owner/revision의일괄방어/선성립분쟁우선처리는V2보완안7절을따른다.
- 분쟁의 버전은 권한/상태 변경 시 증가한다. polling/전송횟수·worker lease 갱신은 제품 version을 바꾸지 않는다. 같은 key는 같은 결과이며 retry로 deadline을 재계산하지 않는다. 종료 후에도 원요청 결과와 현재 조회를 구분한다.
- DB lock 없이 외부 조회 → 짧은 transaction의 현재 회원/소유/account·proof/dispute/대상/등록 snapshot 재검사 → 소유/설정/등록·분쟁/감사/피드·dedup 동시 commit. 모든 경로는 기존 game transaction 직렬화 기준과 잠금 순서를 공유하며 그룹/주간 명령의 최종 현재소유 검사와 경합을 검증한다.
- 만기 worker는 PostgreSQL due scan/짧은 lease/generation fencing을 사용한다. process 재시작에도 due row가 남고 주기적 재획득이 가능해야 한다. `GET`으로 만기처리를 실행하지 않는다. 자동이전에는 worker/주기 실행 연결이 필수이며 CLI 수동 실행만 만들어 자동 완료로 보고하지 않는다. 로컬/향후 Lightsail에서도 같은 persistent DB 기반 루프를 사용하고 Redis 등 새 인프라를 요구하지 않는다.
- 최종 provider 관찰은 시도자에게 새 장비 조작을 요구하지 않는 fresh siblings/profile 확인이다. 사용 가능한 현재 키가 없거나 provider 실패면 이전하지 않고 `retrying_settlement`로 유지한다. 무한 tight retry 대신 backoff와 safe reason/next_retry_at을 노출한다. 키 복구는 기존 개인 키 설정 흐름을 이용하며 키 원문을 요청하지 않는다.
- 방어/취소/만기 worker는 같은 row/version에서 한 순서만 성공한다. `< deadline`만 방어 허용, `>= deadline`만 settlement 허용. worker가 늦었다고 방어 기한을 늘리지 않는다. 외부 조회 중 방어가 먼저 성공하면 worker commit을 거절한다. 마감 전 전송됐어도 commit이 마감 뒤면 방어로 확정하지 않는다.

## 7. 최종 이전 transaction과 자료 귀속

자동 이전의 필수조건: 유효하게 저장된 시도자 장비 성공+24시간 경과+방어/취소 없음+동일 account/owner/base ownership revision+현재 유효 target UUID/claim·fresh 원문 서버/이름 매핑+새 owner 사용가능+후처리 안전성. 여러 account 혼입/target퇴역·claim교체/다른 소유 변경은 자동 이전하지 않는다. roster 정상 성장만으로 소유 분쟁을 무효화하지 않으며 현재 관찰된 claim과 target를 다시 검사한다. 응답누락을 소멸확정/claim해제·퇴역으로 쓰지 않는다.

성공 transaction:

1. 동일 canonical account의 owner 변경·ownership_revision 증가·verified_at 갱신, dispute결과와 이전 audit를 unique하게 저장한다. 기존 canonical UUID/현재 claim은 보존하되 **앱 회원의 권한·개인자료가 새 owner에게 상속되는 뜻은 아니다**. 이름만으로 다른 account/퇴역 UUID를 연결하지 않는다.
2. 이전 owner의 활성 configuration은 ended 처리·기존 registration은 ownership_lost로 계산한다. 삭제행/과거 ID·본계정 지정·자료를 삭제하지 않는다. 영향받은 등록 version을 올려 진행중/기기 캐시를 무효화한다.
3. 등록source는살아있는본인원본등록을재사용하며명시삭제/충돌은review_required다. directsource는최종이전때유일한관련본인등록재사용또는한도20내새등록생성이다. 한도초과는기존소유/분쟁을보존하고REGISTRATION_LIMIT로재시도한다. 장비성공/분쟁개시만으로direct등록을자동생성하지않는다. 상세는V2보완안8절을따른다.
4. 새 owner configuration은 새 ownership revision의 `unconfigured`/활동없음/대표null. 과거 같은 회원의 ended configuration도 자동 부활시키지 않는다. 이전 owner의 역할·선호·표시·power cache는 user+ownership revision 범위에 남고 새 owner에게 복사하지 않는다. 늦은 작업/replay는 현재 owner/revision/session/lifecycle 검사를 통과해야 한다.
5. 그룹 대표가 이 account의 캐릭터이면 현재 ownership 기준 needs_update를 보장하고 관련 directory/group projection revision을 갱신한다. member ID/가입/그룹장/코드관리권은 owner가 아닌 앱 회원에 귀속되므로 새 owner에게 넘기지 않는다. G2 pending 요청은 최종 현재소유·활동 검사를 통과해야 하며 stale snapshot만으로 가입시키지 않는다.
6. 이전 owner의 주간 기록/과거 파티 Snapshot/이력을 새 회원에 복사하거나 지우지 않는다. 아래8절에서 정의한 현재 참가 후처리를 적용한 뒤 event/ACK까지 commit한다. transaction 중 오류는 owner/설정/감사/분쟁을 모두 rollback한다.

과거 운영자 수동 이전의 audit와 별개로 분쟁 provenance·policy version을 가진 서버 전용 transition을 추가한다. `equipment_proof.validated=True`나 임의 HTTP boolean을 실제 이전 권한으로 받지 않는다. 기존 일반 V1/legacy 내부 binding 경로도 새 분쟁 정책을 우회해 타인 owner를 즉시 바꾸지 못하도록 최종 guard를 공통화한다.

## 8. 그룹·파티·활동·주간 원장 영향 대조

| 영역 | 현재 코드/정책 | 이번 이전안 |
|---|---|---|
| 그룹가입/그룹장 | GroupMembership.user_id와leader membership, 대표캐릭터현재성은별도 | 기존회원관계/관리권보존, 새소유자에게상속0·자동가입/탈퇴0 |
| 그룹대표 | service.summary가현재owner/usable로valid/needs_update | 이전뒤needs_update·directory invalidation. 새대표자동선택0 |
| 활동/개인대표 | owner+Configuration/Activity 현재검사 | 이전owner활성종료·신규owner명시선택필요 |
| 역할/선호/표시·power cache | user/ownership/lifecycle scope | 새revision에서빈개인자료·old response차단·과거소유자자료복사0 |
| 주간manual/완료 | WeeklyState(user_id,character_id,raid,cycle) | 기존회원기록보존·새owner에완료/점유이전0. 개인manual기록을실제게임완료증거로승격하지않음 |
| 미완료파티 | 실제room API미구현, 기존회원자리보존/캐릭터확인필요정책 | 기존회원자리/과거Snapshot보존·경고, 기존회원명시교체/탈퇴허용·새캐릭터자격재검사. 새owner자동참가0 |
| 실제모집/점유경합 | #13후속, canonical/회원점유공유검사미완성 | 이전+참가/완료가동시에옛권한으로성공하지않도록공유락/최종검사필수 |

주간원장에는 이미 active_party_id/party_completed_at가 있을 수 있다. 과거 party_completed_at만 있는 완료 Snapshot은 현재 참가로 취급하지 않는다. 실제파티후처리 adapter가없는현단계에서그관계를0건으로가정하지않는다. 현재참가/영향이있는경우자동이전은`review_required`/`PARTY_IMPACT_REVIEW_REQUIRED`로보류하는제안이다. 실제방연결후기존회원의자리보존·확인필요와canonical캐릭터중복사용차단/점유정리계약을구현한뒤이를해제한다. 과거완료Snapshot은수정하지않는다. 실제room연결전주간수동완료만있는원정대는그이유로일괄이전금지하지않는다.

## 9. 구현 단위·검증 완료 조건

1. 제품 잔여안/Flutter DTO 검토 확정 → 새 OpenAPI/DB 상세 계약. 이 문서만으로 실행계약을 바꾸지 않는다.
2. V2 preview/장비 orchestration·타소유 판정/개시 snapshot·분쟁양측GET/복원/취소·사용권유지·방어전용proof/일반본인차단. worker 미구현이면 그 상태를 명시하고24시간자동이전완료로인계하지않는다.
3. 이전 transaction/legacy우회차단·worker lease/restart·등록/설정/개인자료/그룹/주간 guard와 최소앱내통지연결. API·worker·DB additive반영범위를구분한다.
4. 격리 PostgreSQL/모의HTTP 검증 → 승인된 작업브랜치commit/push/원격확인 → 같은Issue인계 → Flutter 기존화면안내/두타이머·양측행동/기기복원연결. 실제24시간사용자시험은자동시각제어검증과별개로판정한다.

필수 검증: 검색생성0/장비성공때1개·증거가짜/미해제/키변화·본인차단/방어예외권한·다른회원404·UTC24h/정확한경계/flush중만료·방어vssettle/취소/멀티시도자경합·한번만이전/알림·재전송/재실행/다른기기양측복원·worker중단재획득/stale generation·provider장애보존/재시도·claim퇴역/소유revision변화/부분응답삭제0·중간rollback·현재그룹권한/기존회원자리·개인자료비상속/캐시/늦은응답·V1우회0/기존신규인증·영어검색/owned refresh보존.

## 10. 추가 제안·아직 확정하지 않은 제품 항목

- **동시 도전(사용자확정):** account당진행분쟁최대3건. 장비확인성공후각24시간기산. 현재owner의방어성공은같은소유revision진행분쟁모두종료,미방어는먼저성립한분쟁부터처리/소유이전확정후나머지종료다. account당1건제안은폐기했다.
- **반복 도전(추가 확정):** 방어성공 뒤 영구금지·별도 재도전대기 없음. 135번째의 동일시도자24시간cooldown제안은 폐기한다. 매번 새 장비확인 성공 뒤24시간방어가 시작된다. 취소/실패/만료에 별도cooldown을 추가하는 것도 이번 확정으로 간주하지 않는다. 기존API quota·멱등/중복차단은 유지한다.
- **기존 근거:** [137번째 Flutter 조사](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6237012986), 고정본8f4209d. 과거 수동경로는 Player+원정대 pendingProof 중복검사/방어성공후운영자해제전금지였고24시간cooldown은없었다. 조회후set/Rules공백으로서버전체동시성보장은없었고awaitingOwnerResponse도pending검사에서빠졌다. 과거자동장비는인스턴스메모리10분/즉시이전경로이며24시간방어없음. 현재V1은pending보류이며구수동제재미연결이다. 이조사는구저장방식복원/제재자동채택근거가아니다.
- **알림 채널(확정):** 앱내안내우선·푸시후속. 더이상사용자선택대기가아니다. 기한시작은이미확정된장비성공시각이다.
- **영구불명확/실제파티영향:** 자동이전대신review_required보류·시도자철회허용제안. 재검토/운영자수동승인도구는아직없고동작가능한기능으로표시하지않는다.

위항목은검토안이다. 사용자답변없이새제한/관리자권한을구현하지않는다. 기존환경/DB0014/자료·키/flag유지,새환경접속/초기화/자료이전·운영배포없음. 이번산출물은설계문서와Issue검토회신이며코드/실행OpenAPI/DB/API/worker를변경하지않는다.

정정 공유: [#8 전체139번째 Backend](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6237185475).

## 11. 향후 운영자 귀속 고정 — 현재 구현 범위 밖

138번째의 사용자 방향을 설계 확장 경계로 기록한다. 운영자 도구/강제이전·Discord 연동을 지금 구현하지 않는다. 문의 경로는 향후 Discord로 변경 예정이나 URL은 미제공이다.

현재 owner와 운영자 귀속 고정은 별도 개념이다. 향후 고정은 대상 회원·처리 운영자/시각/사유·revision/감사를 서버 권한 아래 관리한다. 운영자가 해제/조정할 때까지 다른 회원의 일반 인증 도전과24시간 자동 이전을 차단한다. 클라이언트 on/off나 단순 owner 필드로 표현하지 않는다.

고정 해제(프리)는 고정 제약만 해제해 일반 규칙으로 돌아가는 것이며 기존 owner 삭제·다른 회원 즉시 귀속이 아니다. 실제 운영자 조정과 고정 해제는 구분한다. 향후 고정 변경 시 진행 중 proof/dispute/worker가 같은 정책 revision/현재 권한을 네트워크 전후/최종 transaction에서 재검사해야 한다. 고정 뒤 오래된 worker가 이전을 완료하거나, 해제 뒤 옛 자동 이전이 그대로 재개되지 않도록 무효화/재시작 계약을 함께 정한다. 현재 존재하지 않는 고정을 DB에서 이미 검사한다고 주장하지 않으며 향후 기능 도입 시 모든 일반/legacy/worker 경로 연결이 필수다. 지금 임의 boolean/DDL/API를 추가하지 않는다.
