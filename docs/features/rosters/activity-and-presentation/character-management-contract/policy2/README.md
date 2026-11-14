# Issue53 — character-management-2 정확 계약 제안

2026-11-14. [Native 전체27](https://github.com/heo0328/lostparty-backend/issues/53#issuecomment-6872686921)·[전체28 사용자 자동 대표 정책](https://github.com/heo0328/lostparty-backend/issues/53#issuecomment-6872855905)에 대한 Backend 산출물이다. **소비 대조용 제안·미구현·미커밋/미push**다. 실행 중인 policy1 및 게시 SHA `026a74fa67c36d72fb9d6d94d8bafcf707d4ffe9`를 대체 배포한 상태가 아니다. 기존 [policy1 Schema](../schema.json)와 ACK는 보존한다.

- [정확 Schema](schema.json): Context=GET/신규 성공 PUT, PutBody=신규 요청, Error=기존 기본 오류 envelope. 모든 객체는 closed다.
- [완전 합성 예시·전이](examples.json): 메인/부원정대/예외 Context, 원자 저장·메인 전환, policy1 원문 복구, schema/의미 거절.
- [자동 선정 fixture](selection-fixtures.json): 정확 소수·전투력 동률/null·혼합 이름·기존 대표 유지·raw 승격 방지·후보 없음.
- `python3 docs/features/rosters/activity-and-presentation/character-management-contract/policy2/validate.py`: 문서 검증만 수행한다. 서버/DB/Flutter 시험과 구분한다.

## 현재 구현 상태

위 제안 당시 표기와 구분하여 현재는 [정책2 구현/검증·로컬 반영](../../character-management-policy2-implementation.md)을 완료했다. 코드·최종 계약은 미커밋·미push이고 고정 SHA는 없다. 아래 계약을 구현했으며 Native 실제 소비/사용자 인수는 후속이다.

## 같은 자원·버전 구분

GET/PUT `/v2/me/game-accounts/{registration_id}/character-settings`를 유지한다. 신규 endpoint/profile/대표 원장을 추가하지 않는다. GET과 신규 성공 PUT은 `scope.policy_version="character-management-2"`, 필수 `scope.is_main`을 반환한다. 신규 PUT도 **필수 `policy_version="character-management-2"`**를 포함한다. 기존 본문에는 이 키가 없으므로 서버가 신규 정책 의도와 과거 원문 복구를 구분할 수 있다. 알 수 없는 정책값은 400 INVALID_REQUEST다. 정책1의 엄격 DTO에 새 필드를 소급 삽입하지 않는다.

`representative_character_id`는 GET/PUT 모두 필수 키·UUID 또는 null이다. 부원정대 PUT은 null만 허용하며 다른 값은 409 MAIN_REGISTRATION_CHANGED다. 메인 PUT은 유효한 UUID를 명시 선택하거나 null로 기존 유효 대표 유지/없을 때 자동 선정을 요청한다. GET null은 미설정/유효 후보 없음의 실제 현재 상태이며 자동 선정 draft가 아니다.

활동 1..200, 현재 소유·usable·중복 없음 검증은 유지한다. 메인의 현재 유효 대표를 활동에서 빼는 OFF는 기존처럼 400 REPRESENTATIVE_REQUIRED다. 다른 대표를 먼저 명시 선택하는 흐름을 유지한다. 기존 대표가 이미 무효이면 이를 유지하도록 강제하지 않는다. 신규 nonnull 대표는 최종 활동에 속한 usable 캐릭터만 허용한다. 부원정대는 대표 포함/OFF 제약이 없으며 명시 저장에서 raw 대표를 null로 정리한다.

메인 `ordered_character_ids`는 최종 활동에서 서버가 확정할 대표를 뺀 정확 집합(최대199), 부원정대는 최종 활동 전체(최대200)다. null 자동 선정과 순서가 함께 오면 같은 CAS 문맥·최종 활동에서 대표를 결정한 후 집합을 검사하고 한 번에 저장한다. Native가 자동 선정 후보를 미리 계산할 필요가 있을 때 이 응답의 정규값만 사용한다. 캐시를 합쳐 계산하지 않는다. 순서 생략은 rank 보존, null은 400, 메인 대표 한 명은 빈 배열 허용, 부원정대의 빈 배열은 의미 거절이다. 비활동 상대 순서·슬롯 치환·동일 순서 no-op은 policy1 그대로다.

## 권위 값·정렬·지문

자동 선정 후보는 **현재 메인에 연결된 본인 소유 canonical 원정대의 최종 activity ∩ 현재 usable**다. usable은 active/confirmed 및 NameClaim의 canonical UUID 일치다. 다른 원정대·퇴역/누락/충돌·비활동을 후보로 합성하지 않는다.

같은 DB 읽기 스냅샷에서 다음 값을 만들고, 쓰기는 game-mutations-v1 lock 아래 다시 읽고 CAS를 검사한다. '같은 관측'은 동일 DB 문맥이라는 뜻이며 외부 레벨과 전투력이 같은 시각에 수집됐다는 뜻이 아니다.

| 필드 | 권위 출처·처리 |
|---|---|
| item_level | 현재 Character.summary.item_level의 정규 문자열. 유효하면 item_level_observed_at=Character.fetched_at, 아니면 둘 다 null |
| combat_power | Character.summary.combat_power + Character.power_fetched_at 및 본인 ScopedPowerCache의 동일 canonical UUID/현재 lifecycle_revision 성공값 중 가장 최근 관측. 유효 숫자와 fetched_at이 함께 있는 값만 비교 |
| combat_power_observed_at | 선택한 값의 실제 저장 관측 시각. 실패 checked_at·요청 평가 시각으로 대체하지 않음 |
| power 동시각 tie | cache가 summary보다 우선, cache끼리는 scope_key 사전 오름차순. preview/다른 회원·캐릭터·lifecycle 및 RolePowerSuccess(역할별 분석)는 제외 |

두 관측 숫자는 기존 management.level과 같은 경계로 정규화한다: 문자열만, 원문 최대128자, Decimal precision128, 유한·비음수, 0은 '0', 소수 끝0 제거, 0 아닌 값의 adjusted exponent는 -128..63, 정규 문자열 최대64자. 비수치/비유한/음수/범위 초과는 null이다. provider의 쉼표 제거는 기존 관측 저장 경계에서만 수행하며 관리 DTO에서 새 규칙을 추가하지 않는다. float 변환은 하지 않는다. 관측 시각이 없거나 잘못된 전투력은 null이다.

오래된 마지막 성공값도 저장 관측 시각과 함께 사용한다. 30분 TTL 통과/최신 요청 실패만으로 기존 숫자를 null로 바꾸지 않는다. 동점 해소용 추가 provider 호출·polling은 없다. 현재 usable 여부는 숫자 신선도와 별개로 매번 검증한다. 캐시 조회는 전체 문맥을 bulk로 처리하고 카드별 N+1은 추가하지 않는다.

자동 선정 순서는 정규 item_level DESC(null 뒤) → 정규 combat_power DESC(null 뒤) → character_name UTF-16 code-unit ASC → canonical UUID ASC다. 마지막 UUID는 이름까지 같은 완전 동률의 결정 규칙이다. 한글/숫자/영문 그룹화, locale collation·대소문자 변환·Unicode 정규화는 하지 않는다.

**카드 기본 순서**는 기존 rank(null 뒤) → item_level DESC(null 뒤) → 이름 UTF-16 ASC → UUID ASC를 유지한다. combat_power는 대표 기본 선정에만 추가되며 카드의 rank/수동 순서를 덮어쓰지 않는다. ordered_all/characters는 카드 기본 순서, 대표 우선 렌더링은 메인의 유효 대표만 별도로 처리한다.

order_digest는 불투명 SHA-256이다. 정책2/회원/등록 ID·등록 version/is_main/소유 세대와 canonical 전체 문맥의 ID·rank·정규 level/name·정규 power/두 observed_at·usable/blocked_reason을 결합한다. settings/activity는 별도 expected_settings_version, roster는 expected_roster_revision으로 검사한다. 평가 시각·TTL 경과·checked_at·role/visible은 지문에서 제외한다. 숫자/관측 시각/자격이 바뀌면 rank가 같아도 409 REVISION_CONFLICT로 재조회하며 옛 드롭을 새 문맥에 자동 적용하지 않는다.

## 저장 대표와 읽기·상태

유효한 현재 대표가 있으면 관측 레벨/전투력이 바뀌어도 유지한다. null PUT도 이 규칙을 따른다. 명시 UUID 선택은 이를 대체할 수 있다. 메인 전환은 부원정대 시절 raw를 기존 사용자 대표로 간주하지 않고 새 메인 후보를 비교해 선정한다. 같은 메인에 is_main=true를 다시 저장할 때에는 유효 대표를 유지한다.

현재 reader는 같은 스냅샷의 main selector를 공유한다. management/대표 GET·settings projection·reg_out.representative_summary·bootstrap/lifecycle 모두 부원정대의 계정대표를 null로 내보낸다. 메인이라도 활동/usable 자격이 없는 raw는 대표로 노출하지 않고 null로 내보낸다. 잔여 activity ID는 기존 복구 계약대로 보존한다. GET은 대표·state·rank를 쓰지 않는다.

후보가 전혀 없는 경우 메인 전환/소유 확인/새 관측 저장 자체를 가짜 후보로 성공시키거나 대표 선정 때문에 유효한 관측 저장을 취소하지 않는다. 대표는 null, 기존 activity는 보존하고 저장 명령에서 실제 불완전 설정은 needs_reconfiguration으로 전환한다. 아직 activity를 선택하지 않은 최초 unconfigured는 그대로다. 관리 PUT은 유효한 최종 활동1..200을 요구하므로 후보 없는 명령은 404 CHARACTER_NOT_FOUND/409 CHARACTER_UNUSABLE 등 기존 자격 오류로 거절한다. 메인/소유 원정대 자체가 없으면 사용자 대표는 0명인 예외 상태다.

배포 전부터 대표가 비어 있던 자료를 GET에서 보정하거나 일괄 초기화하지 않는다. 아래 기존 변경 명령 또는 사용자의 관리 PUT(null 포함)이 복구 경계다. 필요 시 현재 UI에서 이미 수행하는 관측 갱신/최초 설정 흐름에 연결하며 필수 대표 선택 화면이나 별도 대표 PUT을 추가하지 않는다.

## 기존 명령의 트랜잭션 경계

하나의 공통 대표 확정 함수를 다음 기존 명령의 **업무 저장 후·ACK 구성 전** 호출한다. 외부 관측은 기존대로 lock 밖에서 수집하며 자동 선정을 위한 추가 외부 호출은 없다.

| 기존 명령 | 같은 lock/transaction 안에서 확정할 내용 |
|---|---|
| PATCH /v1/me/game-accounts/{id}, is_main=true | 기존 메인 demote와 두 등록 version 갱신, 새 메인 후보 선정/대표·settings version, 최종 RegistrationOut 및 원 ACK 저장. 별도 대표 PUT 없음 |
| POST /v1/me/game-accounts 및 소유 확인 confirm | 원정대 연결/소유 확정·기존 활동 문맥이 준비된 뒤, 현재 메인이면 대표 확정. 활동이 없으면 unconfigured/null. 비활동 자동 ON 없음 |
| PUT v2 character-settings 정책2 | CAS/최종 활동·명시 대표 또는 자동 선정·선택적 순서·raw 정리·state/버전을 한 번에 저장하고 policy2 ACK |
| PUT v1 character-settings | 같은 main-only/자동 선정. 부원정대 null 및 현재 raw와 정확히 같은 기존 round-trip만 수용하고 raw는 null로 저장. 임의 nonnull은 거절. 원 ACK는 그대로 |
| POST /v1/me/game-accounts/{id}/refresh 및 소유/usable 변경의 실제 저장 경로 | 관측/자격 변경 후 유효 대표 유지, 무효면 나머지 활동 후보 자동 선정, 없으면 null. 현재 주경로 reconcile/confirm에 연결하고 내부 retirement도 같은 불변식을 지킴 |
| 기존 대표 전용 PUT | main-only·명시 활동/usable 선택 검증을 유지. 정책2 신규 명령 대신 추가 호출을 요구하지 않음 |

대표/state/활동/rank 중 실제 변경이 있을 때 해당 configuration.version은 **명령당 한 번** 증가한다. 이미 같은 정상 설정이면 no-op이다. 메인 등록 자체의 version은 기존 PATCH 규칙과 이전 메인 demote 규칙을 유지한다. 값 갱신만으로 유효 대표가 유지되면 settings_version은 증가하지 않아도 관측 지문/CAS는 바뀔 수 있다. ACK 저장 실패 시 업무 변경도 rollback한다. 반환 DTO 형식은 기존 각 자원 형식을 유지하며 policy2는 관리 자원에만 사용한다. 원 ACK는 당시 결과, 후속 GET은 현재 상태다.

그룹 생성/가입의 최종 명시 선택 및 저장된 그룹 snapshot은 그대로다. 계정대표·메인 변경으로 기존 그룹 snapshot을 갱신하지 않는다. Native의 그룹 기본 후보는 같은 roster 관측의 메인 계정대표만 참조하되 최종 후보 전체를 메인 전용으로 제한하지 않는다.

## 정책1 원문 복구와 멱등 경계

별도 namespace2를 만들지 않고 기존 **operation='character-management-1'을 영속 멱등 namespace로 유지**한다. 이 문자열은 이제 보관 식별자이며 현재 응답 정책은 아니다. 기존 actor/operation/key unique 및 같은 dedup lock을 재사용한다. 정책2 본문의 policy_version도 digest에 포함한다. target/body 포장·JSON canonicalization은 현재 reserve의 규칙을 그대로 유지한다. policy1 원문에는 새 키·null·기본값을 삽입하지 않는다.

라우트는 과거 PutBody와 신규 PutBody를 구분해 파싱한다. 먼저 인증/소유권을 검사한 뒤 같은 namespace에서 기존 key의 digest·완료/lease 상태를 검사한다. 과거 응답은 policy1 strict DTO로, 신규 응답은 policy2 strict DTO로 검증한다. 런타임 OpenAPI 구현 시 PUT 200은 이 두 응답의 oneOf로 명시하고 GET은 policy2만 내보낸다. 과거 strict 검증이 필요한 범위만 보존한다.

| 서버 기록 | 동일 policy1 원문/key 복구 결과 |
|---|---|
| 성공·completed_at부터24h 미만 | 당시 HTTP/정책1 ACK 그대로 재생. 현재 대표나 새 정책으로 응답 재작성 없음 |
| 성공·24h 이상 또는 명시 expired | 409 IDEMPOTENCY_EXPIRED, 업무 재실행 없음 |
| 아직 running·유효 lease | 409 REQUEST_IN_PROGRESS 및 기존 Retry-After: 2. 원문 유지, 제한된 복구 뒤 현재 GET. 결과 불명을 확정 실패로 바꾸지 않음 |
| running lease 만료/retryable·미완료 | **409 CONTRACT_POLICY_CHANGED**, lease 인계/새 정책 업무 실행 없음 |
| 기록 자체 없음 | **409 CONTRACT_POLICY_CHANGED**, 옛 요청 신규 예약·실행 없음 |
| 같은 key에 다른 target/body | 409 IDEMPOTENCY_CONFLICT. 정책2로 바꾼 본문도 이 범주 |

CONTRACT_POLICY_CHANGED는 새로 제안하는 확정 무실행 오류다. 공통 reserve의 만료 lease 인계보다 먼저 위 복구 전용 분기를 적용한다. 이미 진행 중인 구 프로세스의 업무 transaction은 서비스 교체 시 drain하고, 만료 ticket은 기존 commit_result의 시각/generation 검증으로 성공 커밋하지 못하게 한다. lock 순서는 기존 dedup 예약 후 업무 game lock, 최종 RequestResult row lock을 유지해 역순 deadlock을 만들지 않는다.

정책2도 같은 namespace를 사용하므로 이미 사용한 key의 본문을 바꾸면 충돌한다. 신규 의도는 현재 policy2 GET을 확인하고 사용자가 명시한 새 key로만 보낸다. 옛 명령을 자동으로 새 key·정책2 명령으로 변환하지 않는다. 정책2 신규 예약/성공/lease 인계는 기존 reserve/commit_result/release·24시간 보관 규칙을 따른다. 기존 만료 기록을 삭제하거나 기한을 갱신하지 않는다. 보존 기록을 지우면 과거 성공 구분이 사라지므로 이 작업에 DB/멱등 기록 삭제는 없다.

Native journal: acknowledged=true는 PUT 없이 현재 GET. false는 기존 원문/key로 복구하며 policy1 ACK는 옛 reader로만 검증 후 현재 policy2 GET을 한다. 확정409도 현재 GET 후 사용자 명시 재시도이며 REQUEST_IN_PROGRESS·통신 실패는 pending을 자동 삭제하지 않는다. GET 실패는 저장 실패/빈 목록이 아니다. journal에 policy 문맥이 없다는 이유로 body를 추정 변환하지 않는다.

## 대조·구현 완료 조건

이번은 계약 산출물과 합성 문서 검증이며 API/OpenAPI/DB·실행 서버는 변경하지 않는다. Native는 policy2 필수 요청 구분자, nullable 자동 선정·movable, 관측/지문, 옛 ACK 복구 분기를 대조한다. 합의 후 구현에서 정상/기존 유효 대표 유지/메인 전환/후보 없음, 부원정대200·main199, CAS/동시 관측·멱등 경합·ACK rollback·현재/legacy 계약을 검증한다. 실제 서버 및 기기 결과와 구분한다. DB초기화 불필요·미실행이며 필요해져도 사용자 사전 확인이 필수다. commit/push·merge·배포는 별도 지시 기준이다.
