# Issue53 — 캐릭터 관리 즉시 저장 조사·계약 제안

2026-11-14 / 코드 기준 fe5e082 / 미구현. 아래는 Native 전체10 요청에 대한 Backend 조사 및 추천이다.

## Backend — 캐릭터 관리 즉시 저장 조사·추천 계약 (미구현)

전체10 요청을 현재 게시 Backend fe5e082/dd69159의 설정·대표·개인preferences writer와 대조했습니다. 예약 GET은 변경하지 않습니다. 아래는 구현 제안이며 API/OpenAPI/DB를 수정하지 않았습니다.

### 1. 기존 API로 가능한 것·제약
**사용 ON/OFF와 대표 변경은 기존 PUT /v1/me/game-accounts/{registration_id}/character-settings 한 요청으로 가능합니다.** activity_character_ids+representative_character_id와 expected_settings_version/expected_ownership_revision/expected_roster_revision을 전송합니다. 선택 최대200, 중복금지·빈선택400 EMPTY_ACTIVITY_SELECTION·대표가 선택집합 밖이면400 REPRESENTATIVE_REQUIRED, 소유권없음403 OWNERSHIP_REQUIRED·허용되지 않는 선택404 CHARACTER_NOT_FOUND 또는 실제 자격검사의 CHARACTER_UNUSABLE/IDENTITY_CONFLICT, CAS불일치409 REVISION_CONFLICT입니다. 데이터는 한 트랜잭션이며 변경/초기설정 시 settings_version을 올리고 의미상 동일한 저장은 버전을 불필요하게 올리지 않습니다. 쿨다운/대표 확인창은 서버 요구가 아닙니다.
원 대표 OFF를 서버가 '대표 변경 없이' 허용하지 않습니다. Native는 해당토글을 막고 최소1명 제약을 유지합니다. 서버가 다른 캐릭터를 자동대표로 고르지 않습니다. 소유/usable 실패를 활동 OFF나 정원 손실로 자동 보정하지 않습니다.

전용 /v1/me/game-accounts/{registration_id}/representative PUT은 expected_registration_version까지 검사하고 **is_main=true인 원정대만 허용**합니다(MAIN_REGISTRATION_CHANGED). 선택이 없으면 SETTINGS_NOT_CONFIGURED, 비활동은 CHARACTER_NOT_ACTIVE입니다. 따라서 여러 원정대 공통 관리에서는 대표 전용API로 갈아타기보다 같은 character-settings를 재사용하는 편을 권장합니다. 기존 전용API/소비/원ACK는 삭제하지 않습니다.

unconfigured 또는 needs_reconfiguration도 첫 명시조작에서 유효한 선택+대표 전체를 character-settings 한 명령으로 configured로 만들 수 있습니다. 진입만으로저장하지 않습니다. ON/OFF를 추천draft 전체에 반영한 결과가 비어있거나 대표가 빠지면 송신하지 않고 사용자가 선택을 완성하게 합니다. 최초서버 version기본1은 성공한 현재 조회에서만 채택하며 조회실패를1로 추정하지 않습니다.

현재 성공 SettingsOut은 configuration_state/activity_character_ids/representative_character_id/settings_version/ownership_revision/next_change_at=null/selection_complete/ineligible_character_ids이며 roster_revision은 이 응답에 없습니다. 다음 요청의 roster_revision은 기존 원정대 조회/bootstrap 근거를 유지/재조회해야 합니다. 원 ACK는 과거 성공이며 최신상태가 아닙니다.

근거: [settings writer](https://github.com/heo0328/lostparty-backend/blob/fe5e0824c28f58025af201d6ef66d8289229ae60/app/game_accounts/rosters/service.py), [DTO](https://github.com/heo0328/lostparty-backend/blob/fe5e0824c28f58025af201d6ef66d8289229ae60/app/game_accounts/schemas/schemas.py), [대표 writer](https://github.com/heo0328/lostparty-backend/blob/fe5e0824c28f58025af201d6ef66d8289229ae60/app/game_accounts/character_profiles/representative.py).

### 2. 순서의 한 요청 원자 저장 — 현재 계약 없음 / 권장 확장
현재 display_order는 캐릭터별 personal-preferences 전체PUT에만 있고 계정 단위 원자 저장은 없습니다. 순차 PUT과 사후보정은 최종안으로 권장하지 않습니다.

비교 결과 **GET/PUT /v2/me/game-accounts/{registration_id}/character-settings** 자원 하나로 확장하는 안을 추천합니다.
- 기존 v1 PUT의 필수활동/대표 계약과 strict응답·namespace를 그대로 유지합니다. v1 필드를 조용히 늘려 구버전 strict parser를 깨지 않습니다.
- 신규 v2 GET은 현재 선택+대표·완전한 순서문맥과 버전을 한 RR 관측으로 제공합니다. 신규 v2 PUT은 선택+대표 및 선택적인 드롭순서를 한 명령으로 원자확정합니다. 관리화면의 신규 ON/OFF·대표·순서를 **같은 v2 writer**로 통일할 수 있습니다. 표시순서전용GET/PUT+초기설정호출을 나누는 것보다 첫 unconfigured 드롭까지 한 행동/한명령으로 처리할 수 있습니다.
- 분리된 순서 전용API도 가능하지만 설정/대표와 별도버전·초기설정 결합이 추가됩니다. 기존 presentation count에 순서를 끼워 넣거나 역할/visible 전체PUT을 일괄송신하는 API를 추가하지 않습니다.
- 새 순서 원장은 기본적으로 필요없습니다. 기존 CharacterPersonalPreferences.display_order를 같은 트랜잭션에서 부분갱신하고 역할/visible은 현재저장값을 그대로 보존합니다. 계정 Configuration.version을 관리명령 CAS로 재사용합니다. 직접 personal-preferences의 옛 소비도 순서를 바꿀 수 있어 아래 order_digest를 추가해야 합니다. DB migration 필요 여부는 합의 후 구현 조사에서 확정하고 미리 실행하지 않습니다.

### 3. 정확한 의미 후보 — 활동subset 편집·전체 상대순서 보존
scope는 로그인회원+현재소유원정대+ownership_revision입니다. 다른원정대/이름/로컬캐릭터ID는 사용하지 않습니다. 순서문맥은 해당 원정대의 **비퇴역 canonical 캐릭터 전체**(미활동·suspect 포함)이며 새로사용 불가한캐릭터를 순서조회만으로 숨기지 않습니다. 활동선택의usable 검증과 원장순서 보존은 분리합니다. 퇴역/소유세대종료 저장행은 삭제하지 않습니다.
- 기본 전체순서는 저장 display_order 오름차순(null 마지막)·동률canonical UUID로 결정합니다. 새 캐릭터의 null 순서는 뒤에 안정정렬되며 ON시 자동상단이동은 없습니다. OFF→ON은 보존된 수동위치로 돌아옵니다.
- 대표는 **표시 시만 맨앞 고정**, 수동원장 rank=0을 강제하지 않습니다. 대표변경이 나머지 순서 재저장을 유발하지 않습니다.
- 드롭 입력 ordered_character_ids는 '명령의 최종 activity 집합에서 대표를 제외한 캐릭터'를 각각 정확히1번 포함하는 **전체 movable subset**입니다. 부분 ID patch/중복/타원정대/누락은400 또는 권한오류로 전체거절합니다. activity·대표가 동시에 바뀌면 최종집합으로 검사합니다. 대표만 있으면 빈배열이 유효합니다.
- 서버는 전체순서에서 해당movable ID가 있던 슬롯만 입력순서로 교체합니다. 대표·미활동·누락캐릭터의 상대위치를 보존합니다. 저장은 전체목록0..N-1의 정규화 rank로 만들 수 있어 **미활동의 상대순서는 유지하지만 과거 숫자 rank 자체의 불변은 보장하지 않는 안**입니다. preferred_role/visible 값은 불변, rank가 실제 변한 preferences행만 version/saved_at 갱신합니다. 기존 individual PUT은 새version을 읽어야 합니다.
- 순서입력이 없으면 기존순서를 변경하지 않습니다. '순서입력 없음'과'대표한명이라 빈movable순서'를 구분합니다. 신규행이 필요한 경우 기존preferences 기본 role=null/visible=true를 사용하지만 기존false를true로 바꾸지 않습니다.
- 기존 목록이200개를 넘을 때 잘라 전체문맥으로 제공하지 않습니다. 기존선택200상한과 맞춘 문맥 지원량/초과오류는 Native와 정확DTO를 고정할 때 합의합니다. 이번문서로 숨은 데이터삭제/활동자동추가(#18)를 하지 않습니다.

### 4. CAS·멱등·성공/오류 후보
v2 GET 후보 응답: registration_id/game_account_id/configuration_state, registration/settings/ownership/roster revisions, activity_character_ids/representative_character_id, ordered_all_character_ids, order_digest, evaluated_at. 순서지문은회원·소유세대·전체 canonical 집합·저장rank/정규순서에 결합하며 시각·role/visible 변경만으로 바꾸지 않습니다. 누락/자격은현재 roster revision과별개 eligible/ineligible 문맥으로 대조합니다.

v2 PUT 후보 입력: 기존 선택+대표와 expected_registration_version/expected_settings_version/expected_ownership_revision/expected_roster_revision/expected_order_digest, 선택적 ordered_character_ids. Idempotency-Key 필수. GET의 한문맥으로 구성하고 새 namespace로 원문지문·결과를 저장합니다.
- 모든 game writer와 같은 transaction lock에서 소유/등록/현재버전·order_digest/최종선택·대표·순서를 재검증합니다. 의미변경이 있으면 settings_version 한 번 증가하며 원자반영/결과ACK도 같은트랜잭션입니다. 기존v1 설정/대표 writer도 같은settings_version을 바꾸므로 타기기 v1 변경을 감지합니다.
- 개인preferences 직접writer가 display_order만 바꿔 Configuration.version을 올리지 않더라도 order_digest가 달라409로 거절됩니다. role/visible만의 변경은 v2가 DB의 현재값을 보존해 덮지 않습니다. 순서갱신이 바꾼 preferences.version은 구writer CAS를 보호합니다.
- 성공200은 위 GET과 같은 완전설정/순서·버전문맥을 반환해 한 화면을 원자갱신합니다. 원ACK가 이미과거라면 최신GET으로현재상태를 별도읽습니다. 의미동일명령은 불필요한 settings/rank 버전증가를 하지 않습니다.
- malformed/중복/집합불일치400 INVALID_REQUEST, 무활동/대표누락은 기존 EMPTY_ACTIVITY_SELECTION/REPRESENTATIVE_REQUIRED, 소유403·대상404·자격거절은기존정책, snapshot/CAS409 REVISION_CONFLICT 후보. 동일key+다른본문의 기존충돌규칙·응답유실복구를 재사용합니다. DB실패/해제권한변경은전체rollback하며 per-item 성공응답은 없습니다.

### 5. 연속조작·동시수정 권장
회원/환경/원정대별 직렬 write lane 하나를 권장합니다. 송신한 key/body는 불변이고, 미확정명령은 새의도로덮지않습니다. 아직송신전인 같은종류 조작은 마지막사용자의도로 합칠 수 있지만 이미송신한요청을 변경하지 않습니다.
성공ACK의 canonical문맥을적용한후 다음대기 의도를 최신문맥에재적용합니다. 명시409는 성공을위장하지않고 GET으로재조회·의도유지/충돌안내 후 재시도합니다. 네트워크유실은원key/body복구가 먼저이며 새key중복명령을 만들지 않습니다. epoch/인증/환경/원정대 전환의늦은응답을폐기하고 마지막확정화면과저장중/실패표시를분리합니다. 순서오류때자동역PUT이나같은키본문변환으로되돌리지않습니다.
초기추천draft는진입시저장하지않고 첫명시조작에서선택+대표(+드롭이면순서)를v2 한명령으로확정하는구조입니다.

### 다음 담당·미확인
Native는 v2 설정자원 확장/즉시저장 직렬수명, **활동-대표 제외subset 드롭 + 미활동 상대순서 보존(숫자rank 불변 아님)**, 대표의표시우선/수동rank 분리 추천을 사용자UX와 대조해 주세요. 사용자가 단순 사용/대표만 기존API로 우선 구현하는 선택도 가능하지만 순서까지의 완성안은 위 통합v2가 추천입니다.
Backend는 수용후 정확DTO/상한·기존writer CAS·원자트랜잭션·응답유실/연속조작/부분rollback 검증안을 고정합니다. 신규코드/DB/API구현은별도합의·지시후이며 이번은정적조사/제안입니다. 실제 시험·Penpot·서버변경/자료조작/commit/push·배포·Issue종료 없음. 조사문서는 같은 feat/my-account-contracts에 미커밋·미push로 보존합니다.
