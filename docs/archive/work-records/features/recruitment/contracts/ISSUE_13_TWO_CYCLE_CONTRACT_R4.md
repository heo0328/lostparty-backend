> **보관된 작업 원문:** 아래 현재·다음·미구현 표기는 작성 당시 상태입니다. 현재 설명: [weekly-cycles](../../../../../features/recruitment/weekly-cycles/README.md) · [creation-and-settings](../../../../../features/recruitment/creation-and-settings/README.md) · [participation](../../../../../features/recruitment/participation/README.md) · [scheduling](../../../../../features/recruitment/scheduling/README.md) · [completion-and-records](../../../../../features/recruitment/completion-and-records/README.md) · [membership-actions](../../../../../features/recruitment/membership-actions/README.md) · [search](../../../../../features/recruitment/search/README.md). [문서 대응표](../../../../../engineering/documentation/README.md). 원문 바이트와 근거는 기준 커밋 `7f7f767`에서 확인합니다.

> **현재 구현 기준(2026-10-21):** [전체84번째 Flutter · 계약 소비 검토 마감](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6310097083)에서 잔여 충돌 없이 소비 검토를 마감했다. 계약0.4.1/policy4를 고정하며 [W1~W5 작업계획](../planning/ISSUE_13_TWO_CYCLE_WORK_PLAN.md)을 따른다. 아래 검토대기/후속질문·구판 단계표는 당시 기록이다. 실제 기능/실행API·DB 인수는 별도 미완료다.

# Issue #13 전체 계약 보완4판 — Flutter80번째 수정 요청 대응

최신: [공통 설정 ACK 보완](ISSUE_13_COMMON_SETTINGS_ACK_ADDENDUM.md)이 아래 200:Ack 및 202schema/70사례 기준을 대체한다. 기존 네 항목은 Flutter82에서 검토 완료다.

2026-10-21 / Backend / feat/raid-recruitment / HEAD6490f69·실행 구현 cc003e9 계열.

[전체80번째 Flutter 검토](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6308381113)의 네 항목을 보완한 **계약 후보**다. L1핵심/G1/A1은 확정 그대로이며 재채택을 요청하지 않는다. 앱 기능·실행 원본 `openapi/openapi.yaml`·DB·자료·이미지는 변경하지 않았다. 설계 문서·명세 생성/검증 도구·예시만 미커밋·미push다. 아래 원자 처리/권한/SQL 동작은 향후 구현 의무이며 실제 서버 시험 결과가 아니다.

## 1. 제목 속성 삭제 오류

제가 작성한 3판의 clean이 schema annotation과 properties 이름 공간을 구분하지 못해 실제 title 필드를 삭제했다. 앞선 메타검증만으로 이 모순을 잡지 못한 점도 보완했다.

clean은 schema가 들어가는 위치(properties의 **값**, items/anyOf/$defs 등)만 방문한다. properties의 키 title/default/description과 default/examples의 실제 데이터는 건드리지 않는다. 생성 요청·공통제목 변경·카드의 required title/허용 properties가 모두 일치한다.

- 생성/공통수정 title은 기존처럼 **필수 string, 길이1..60**. 빈문자열/누락/null은400이며 새로운 서버 자동제목·기본값·trim 규칙을 추가하지 않는다. Flutter의 기존 기본제목 계산/빈입력 보완을 보존하고 실제 전송은 기존 유효 문자열이다.
- 카드 제목 응답도 실제 title 필드를 유지한다. title annotation만 제거한다.
- 전체 닫힌 객체의 required⊆properties 검사와 제목이 포함된 전체 생성·공통수정·카드 성공 인스턴스를 추가했다. 3판의 구조 모순3건을 재현하고 4판에서는0건을 확인했다. annotation 제거와 instance default/examples 보존도 별도로 검사했다.

## 2. 전역 leave/end — persistent CAS만 사용

두 기존 경로의 body를 동일 `GlobalMembershipCommand`로 교체한다. 불필요한 target/round/실제참가자·계획 CAS는 받지 않는다. 존재하지 않는 회차를 GET에서 생성하거나 client가1/과거값을 추정할 필요가 없다.

```json
{
  "expected_cycle_key":"2026-10-21",
  "expected_room_revision":7,
  "expected_persistent_membership_revision":3,
  "context_token":"synthetic-token"
}
```

실제 값은 GET `/v2/me/raid-rooms/{room_id}/common-context?command=leave|end`의 data.expected_cycle_key/room_revision/persistent_membership_revision/context_token에서 그대로 복사한다. 이 GET의 target_cycle_key query는 제거했다. 응답은 `{scope:GlobalScope,data:CommonContextData}`이며 GlobalScope는 server_now/current_cycle_key/policy_version만 가진다. target가 없는 것을 임의C/N으로 위장하지 않는다.

context는 실제 전체 영향의 target/members/plan/leadership revisions와 현재 actor 관계·회원상태를 token digest에 결합한다. impact_cycles의 각 행에는 기존 값에 members_revision/plan_revision/actor_cycle_member_id/revision(nullable)를 더했지만, client는 이 값을 body로 재제출하지 않는다. 실제 영향0이면 impact_cycles=[]로 합법적이다. 공통설정 수정도 target CAS 대신 room_revision+전체 영향 token/G1을 사용하며 current_settings에 현재 title/scope/group_id/group_revision을 제공한다.

| 사례 | context/명령·보존 효과 |
|---|---|
| 회차 없이 persistent만 유지 | impact=[],네 필드로 leave,기존 persistent 관계만 종료/1room 회복;회차 생성·완료자료 삭제0 |
| N 취소 뒤 활성 영향0 | 같은 leave 계약;이미 닫힌 N의 과거 assignment/결과를 재작성하지 않음 |
| C/N 일반 참가자가 전역 leave 선택 | context에 두 주차 영향 명시·확인 후 전체 관계 정리;N 전용 취소로 암묵 실행하지 않음 |
| N만 취소하며 C 유지 | 기존 participation-cancellations 사용;C와 persistent 관계 보존·자동한도회복0 |
| 본인이 열린T 리더 | leave permission=false/LEADERSHIP_RESOLUTION_REQUIRED;그T 승계/대상탈퇴 먼저,자동C승계로 메우지 않음 |
| G1이 허용한 전체 마지막1인 end | 전역 안전조건·다른T실제참가자 없음 검증;허용된 범위만 종료/과거완료 보존 |
| 다른T에 참가자 존재/리더review·권한없음 | end 거절;N 마지막1인 취소와 전역해산을 구별 |
| 영향/권한/회원관계 변경 | 새 명령은 TARGET_CONTEXT_STALE/REVISION_CONFLICT,쓰기0·context 재확인;원 성공ACK는 먼저 복구 |

전역 성공은 `{scope:GlobalScope,data:GlobalMembershipAckData}`다. room_id/membership_id/수행 후 persistent revision/affected_cycle_keys/room_ended/원명령ID·결과·시각·revisions를 돌려준다. 실제 target가 없는 ACK에 가짜 target key/revision을 채우지 않는다. 두 주차와 quota 영향은 확인한 명령에만 한 transaction으로 기록한다. 기존 leave/end를 쓰며 별도 방관계종료 진입점·연속확인 UX는 추가하지 않는다.

## 3. 생성 체크박스 유지 — 단일 생성 명령의 원자 확정

3판의 `continuation.enabled=false` 강제와 '성공 후 사용자가 다시 활성화' 단계를 철회한다. 승인된 생성화면의 **다음 주도 함께하기 체크박스/한 번의 생성 동작**을 그대로 소비한다. API 두 단계 partial 성공을 만들지 않고 **한 POST가 필요한 주차를 모두 확정**하는 계약이다.

### 사전 검토와 wire

GET creation-context에 `continuation_enabled`(생략false)를 추가한다. 체크 상태/선택·아이템·그룹이 바뀌면 submit 전에 새 context를 받되 별도 사용자 버튼은 요구하지 않는다.

- T=C, 미체크: C만 검토/생성, effect=`target_only`.
- T=C, 체크: C/N의 자격·중복·소유/활동·선택 역할·주간원장/한도를 사전 검토하고 effect=`target_and_next`. 본인이 두 주차의 첫 참가자/공대장이다. persistent room 한도는 고유room1개만 사용한다.
- T=N: 선택한 N만 검토/생성. 체크해도 서버의 바로 다음 주 N과 이미 같은 대상이므로 effect=`target_is_next`, C+14를 개방하거나 예약·동의하지 않는다. 미체크는 target_only. 결과는 명시 실제 cycle 키로 반환한다.

context.data에 prospective_room_id/target_creation/next_cycle_creation(nullable)/continuation_effect를 추가했다. 각 ProspectiveCreateCycle은 실제target/예정cycleUUID/초기generation·revision1/그주 selection/전체아이템 예정ID·round1·실제weekly revision/permission/**conflicts**를 포함한다. 이미 있는 B방 때문에 N이 막히면 B제목을 포함한 권한 내 충돌 정보로 기존 '다른 캐릭터/기존참가확인/닫기' UX를 쓴다. N 대체 캐릭터는 optional next_character_id/next_selected_role을 함께 전송해 다시 사전 검토한다. 정상 흐름에서 캐릭터 재선택은 필요 없다.

POST Create의 기존 continuation 객체는 아래다. 생성 단일 숙련도/null·제목·나머지 입력은 유지한다.

```json
{"enabled":true,"next_selection":{"registration_id":"...","character_id":"...","selected_role":"dealer","expected_registration_version":1,"expected_ownership_revision":1,"expected_roster_revision":1,"expected_lifecycle_revision":1,"expected_role_summary_version":1,"expected_limits_revision":1,"expected_usage_revision":1}}
```

위 selection은 예시 축약이며 실제 UUID/값은 context에서 복사한다. **체크C일 때만 next_cycle_creation.selection을 next_selection에 복사**한다. 미체크 또는 T=N이면 next_selection=null. 이 관계와 context의 checkbox/target 결합은 서버에서 다시 검사한다. client가 초기revision을1로 고정하거나 N원장 정보를 추정하지 않는다. N의 주간원장·예정Round 등은 token에 결합되어 body에 중복 추가하지 않는다.

### 처리/성공·거절·결과불명

1. reserve와 원ACK 확인 → DB현재C/선택context/동의·그룹/소유/카탈로그 및 양 주차 원장·한도 검증 → 같은 transaction에서 단일Room/Item·persistent관계와 필요한C/N회차·본인실제참가를 기록 → 원201 ACK commit.
2. GET 사전검토는 자격 snapshot이다. 최종 POST는 제출된 제목·기간/일정의 유효성까지 **양 주차에 대해** 검증한다. C기록 후 N단계에서 실패해도 C까지 rollback하여 C만 검색에 노출되는 순간/부분ACK를 만들지 않는다. 실패는 failed_cycle_key로 주차를 알려주며 conflict는 기존 최소안내다. C/N 모두 성공한 경우에만201이다.
3. N에는 C의 묶음/조건·일정 의도를 target 날짜로 복사하되, 복사 자체를 N 세션의 본인 일정확인·예약 동의로 쓰지 않는다. N의 복사 의도는 확인 전 상태이며 이전인원/제출표/예약 자동복원0. C에서 본인이 명시한 새 수동시각 확인은 기존 규칙이다. 날짜·주차/수10시/개시floor·합계시간 검증은 유지한다.
4. 201 CreateAck는 기존 room_id/명령결과에 created_cycles(1..2개 actualcycle/UUID/generation/revision/리더ID),continuation_effect를 더한다. 화면은 **원ACK에 요청한 주차들이 함께 존재할 때** 생성 성공을 표시하고 선택T 상세를 조회한다. 상세실패면 조회만 재시도하고 생성POST를 새로 만들지 않는다. ACK는 당시 성공 기록이며 이후 위임/탈퇴의 현재권한으로 재해석하지 않는다.
5. 응답유실·timeout·결과불명은 **동일키·불변본문/원context**로 재전송,원ACK는context만료/새주차자격보다 먼저 복구. 새키로C를재생성하거나N만별도자동생성하지 않는다. 확정오류만초안보존→새context/명시수정 후새시도. 같은context의예정RoomUUID를다른키로재사용하면CONTEXT_ALREADY_USED/충돌로거절해중복방을막는다. 자동새키없음.

이는 생성checkbox로 본인의 N참가를 명시한 경우만이다. 다른 참가자 일괄자동참가/매주새N자동개방을 도입하지 않는다. 기존방에서나중에켜기/취소N명시재개는 별도 opening-context 명령을 그대로 사용한다.

## 4. 숙련도 다중 검색

POST `/v2/raid-rooms/search`에 optional `experience_levels`를 추가한다. 생략/default=[]/null불가. GET 목록도 같은 이름의 반복 query 배열(form/explode=true)로 지원한다.

```json
{"experience_levels":["experienced","unrestricted"]}
```

허용값은 기존 다섯 숙련도 `tryLevel,clearExp,multiClearExp,semiExperienced,experienced`와 검색 전용 **`unrestricted`**다. 최대6/중복금지,생성 experience_level에는 이 sentinel을 넣지 않는다(생성은 기존5값 또는null).

| 입력 | 의미 |
|---|---|
| 생략 / [] | 숙련도로 제한하지 않음,실제null도 포함 |
| ["unrestricted"] | 실제RoomCycle.experience_level IS NULL인 모집만 |
| ["experienced","unrestricted"] | experienced 또는 실제null 모집(OR) |
| null/중복/unknown/문자열"null"/빈값 |400;빈문자열을필터없음이나무관으로변환하지않음 |

GET예: `?target_cycle_key=2026-10-21&experience_levels=experienced&experience_levels=unrestricted`. 필터없음은 이query를생략하고CSV/빈값은쓰지않는다. 중복query key는명시array항목에만허용한다.

SQL순서: target/generation·가시권한/기존raid·difficulty·그룹/회원/캐릭터조건 **AND 숙련도OR조건** → 남은자리 → 기존인원정렬/동률 → pagination. 한페이지로컬필터금지. nullable무관과no-filter를합치지않는다. 검증후값을정렬한집합을cursor에결합해배열순서만바꾼동일조건은유지,실제값추가/삭제는CURSOR_STALE로첫페이지재조회한다. role/전투력 조건이나 생성의단일숙련도를변경하지않는다.

## 5. 검증·재현·다음 단계

현재 full 명세는 **53경로/56동작/202schema**, policy_version=`two-cycle-contract-4`다. 기존 operationId의 contract3 접두사는 식별자 안정성을 위해 유지하며 wire 정책버전은4다. runtime 원본은 그대로다.

- 전체schema 메타/내부ref,닫힌object required/property 일치,경로·query·멱등헤더/operation중복,제목삭제 회귀,제목이 있는 생성/공통수정·카드 성공,양주차 생성context/ACK·체크N/대체캐릭터,전역CAS 출처6쌍,숙련도OR/null/중복경계 등 **70개 합성 schema 사례**를 검증했다. permission 거절 예시와 원자효과 설명은 구현 의무이며 실제 guard/DB경합시험 PASS가 아니다.
- builder는 원격cc003e9 원본+전체73core/76delta 병합본을 그대로 입력으로 쓴다. UTF-8 read/write와 route-map 경로를 이식 가능하게 정리했다. 79번째의16개 예시를 입력으로 예시 builder를 실행하면4판70개를 만든다. validator는 jsonschema가 있는 환경에서 실행한다. 정식 OpenAPI validator/실행FastAPI비교·기능/DB/성능·실회원/기기시험은 아직하지않았다.
- 최신: full.openapi.json,build_issue13_two_cycle_contract.py,build_issue13_two_cycle_examples.py,validate_issue13_two_cycle_contract.py,examples.json,route-map/경로표. Issue에는 문서와 재현 도구/검증 도구·예시 생성 도구 전문을 함께 제공한다. 별도 원격문서 SHA가 있다고 가정하지 않는다.

다음 Flutter는 이번 네 항목에 한정해 명세 모순 해소·생성checkbox/선택N 효과·전역명령 source CAS·숙련도 검색 소비를 재대조한다. Backend는 남은 wire 충돌 보완 후 구현계약/W1~W5로 진행하며 이번에 새 정책 재채택·실회원 반복시험을 요청하지 않는다.

전체명세 canonical SHA-256(JSON sort_keys/ensure_ascii=False/compact UTF-8): `d6aa245c29fb533525fa136ce6ab43c06f34774e52d8d70c183b9ffa8ee0c030`. 원격73/76/79 입력만 둔 격리폴더에서도 전체명세와70개예시 재현·검증 및 로컬동일성을 확인했다. 검증은실제서버나DB에접속하지않는다.
