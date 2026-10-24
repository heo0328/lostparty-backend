# 신청 목록·본인 신청 상태 표시 계약 제안1

2026-10-24 / **협의 제안·미합의·미구현**. 작업 구간명: 모집 신청 표시·본인 승인 대기 상태 보완. 브랜치: `feat/raid-recruitment`.

[#26 전체11번째 Flutter 요청](https://github.com/heo0328/lostparty-backend/issues/26#issuecomment-6384482003)에 대한 제안이다. 기존 가입 소수3항목 정상 보고와 카드디자인 c85715c5/관련56PASS는 Flutter 보고이며 변경·반대파티/C/N 전체 인수로 확대하지 않는다. 사용자가 목록은 **전투력·분석 표시만 제공**하고 전체 승인 자격은 기존 검토/승인에서 확인하도록 선택했다. 이 문서의 새 필드는 현재 개발 API에 없다.

## 경로·프로필·호환

| 기존 GET | 새 선택 입력 | 확장 |
|---|---|---|
| `/v2/raid-rooms/{room_id}/applications` | `reader_profile=application-display-1` | 기존 페이지 각 item에 comparison/analysis/display_reason **3개 필수 필드** |
| `/v2/raid-rooms/{room_id}/detail` | `reader_profile=application-display-1` | 기존 일반 상세 data에 필수 nullable my_application |

기존 `target_cycle_key`, 목록 `state/limit/cursor` 의미를 유지한다. limit 기본20/최대50. 새 프로필은 인증 필수·기존 room/T 접근권한, 목록은 현공대장 권한을 적용한다. 다른 사람의 신청분석은 이 권한으로만 제공한다. 미지정 응답과 `membership-actions-1`은 기존 shape 그대로다. 한 요청에는 프로필 하나만 지정한다. 새 상세 프로필은 **일반 상세**만 확장하며 membership_id/cycle_member_id 입력을 받지 않는다. 본인 신청 목록·단건 application review·카드/검색·plan에는 새 프로필을 추가하지 않는다. 알 수 없는/중복 query, GET body, 잘못된 프로필/프로필과 입력 조합은400 INVALID_REQUEST다.

새 DTO는 별도 이름 `ApplicationDisplay...`를 사용한다. 기존 base/write DTO를 직접 확장하지 않는다. [실행 계약](../../../../openapi/two-cycle.openapi.yaml)의 현재 필수/nullable를 보존하며 새 필드가 있는 프로필은 [독립 closed schema](examples/application-display-v1.schema.json)를 따른다. 경로는177/기본116을 유지할 예정이지만 query/response 계약은 합의 후 별도로 변경한다. schema의 기존 구조 정의는 source484ca171 계약에서 필요한 참조만 복사한 작성 자료다.

## 신청 카드: 기준·필수/nullable

| 추가 필드 | 타입·null 의미 |
|---|---|
| comparison | 기존 BPowerComparison 전체 shape 또는 null. source/trust/역할·최소값·actual·state·시각/버전·success/current issues를 보존한다. 자료 연결 불가일 때만 null이다. |
| analysis | `{version,saved_at,analyzed_at,integrity_status,issues}` 또는 null. version은양수정수, 두시각은UTC RFC3339, integrity_status는clean/review/error/unavailable, issues는기존code/severity 최대20개. head 자체가 없거나 연결불가면null이다. 객체 내부5필드는 모두 필수·nonnull이다. |
| display_reason | null 또는 APPLICATION_CONTEXT_CHANGED/CHARACTER_DATA_UNAVAILABLE. 자료 표시 불가 사유이며 전체 승인 자격 사유가 아니다. |

`display`, character_id/selected_role은 신청 당시 저장 snapshot이다. comparison/analysis는 **해당 페이지 evaluated_at=scope.server_now 시점**의 같은 신청자·캐릭터·신청 ownership_revision·선택역할 자료다. 이름/직업·레벨 snapshot을 최신 provider 관측이라고 표현하지 않는다. 최신전투력 시각/현재분석 시각은 각 필드대로 표시한다.

- 현재 Account의 owner/revision과 신청자의 저장 소유 revision이 일치해야 한다. 소유변경은 comparison/analysis=null, display_reason=APPLICATION_CONTEXT_CHANGED. 참조 캐릭터/Account 연결이 없으면 같은 두필드null, CHARACTER_DATA_UNAVAILABLE. 다른소유자/다른역할 성공본·오래된 app.build로 대체하지 않는다.
- head 없음은 정상 미확인이다. analysis=null/display_reason=null이고 기존 power_value 정책으로 comparison을 제공한다. 실제값없음은 actual=null, success version/observed_at/success_saved_at=null, success_issues=[]다. current_summary_version/power_revision 기본1은 기존 projection 버전이며 분석성공의 근거가 아니다.
- 최소값 있으면 actual없음→missing, Decimal 비교 경계충족→meets, 미달→below. 최소값없음→unrestricted이며 actual=null일 수도 있다. 0 대체·임의TTL·경고/오류 일괄차단은 없다.
- 최신 head가 error/unavailable여도 같은 역할의 마지막 성공값은 유지한다. success/current 버전이 다를 수 있고 success_issues/current_issues를 섞지 않는다. analysis.version/ issues는 comparison.current_summary_version/current_issues와 일치한다. head가없으면current_issues=[]다.
- 실제 분석자료가 malformed이거나 DB조회 자체가 실패하면503 SERVICE_UNAVAILABLE 등 기존 오류 응답이다. 카드자료를 조용히 정상/null로 바꾸지 않는다. display_reason!=null이면 comparison/analysis는둘다null이다. 정상head가 error인 경우는 analysis.integrity_status로 표현하고 display_reason은null이다.

카드의 clean/빈issues·meets/unrestricted는 승인가능 전체판정이 아니다. 목록에 approve permission/전체 eligibility를 새로 제공하지 않는다. 기존 단건 review/context와 실제 승인POST가 최신 자격·저장신청파티·일정/정원 등을 검사하며 자격실패 pending유지/거절·철회/원ACK를 보존한다.

## 일반 상세: 본인 신청 최소 투영

`data.my_application`은 null 또는 다음 **4개 필수·nonnull 필드**의 객체다.

| 필드 | 타입·의미 |
|---|---|
| application_id | UUID, 본인 신청 식별자 |
| revision | 1..2147483647 정수, 해당 신청 revision |
| state | pending/accepted/rejected/withdrawn/expired/cancelled, 조회 시점의 유효 상태 |
| expires_at | UTC RFC3339, 저장 신청 만료시각. terminal 상태에서도 보존한다. |

현재 로그인회원·room·선택실제T·room_cycle_id·현세대가 모두 일치하는 Application만 읽는다. 유효pending(state=pending이고 expires_at>scope.server_now)을 우선하고, 없으면 created_at DESC/id DESC의 최신이력을 사용한다. 해당범위 이력이없으면null이다. 과거세대/다른T/타인 이력은null의대체 근거가 아니다. 만료경계는 `expires_at<=scope.server_now`이며 저장pending을읽기에서expired로투영한다. revision/ended_at이나DB를고치지 않는다. 현세대 판정불가·불완전자료는 기존 ROOM_REVIEW_REQUIRED/자료오류·SERVICE_UNAVAILABLE을 사용하고 정상null로감추지 않는다.

UI 우선순위는 **기존 현재 참가관계/권한 → 유효pending → 기존 신청진입 조건**이다. 참가중이면 신청버튼을숨기고 기존변경/방내부행위를유지한다. pending이면 신청버튼대신 **“공대장의 승인 대기중입니다.”**를표시한다. expired/withdrawn/rejected/cancelled/null은 자동신청허용이아니며 기존권한/context가허용하는진입만가능하다. accepted는신청처리이력이지현재참가가아니다. 수락후탈퇴·참가종료/완료상태는기존참가/권한으로판단하며 accepted만으로다시참가로만들지않는다. 현재참가정보와유효pending이불일치하면참가흐름을우선하고자료를재확인한다.

새필드누락/잘못된응답·조회실패는미확인/재시도다. null/없음으로가정해신청버튼을열지않는다. 표시자료를원명령의권한·revision·멱등key로대체하지않는다.

## snapshot·페이지·오류·갱신 경계

한 REPEATABLE READ/read-only snapshot에서 페이지신청과필요한Account/Character·역할head/성공본을bulk조회해순수power_value로투영한다. 후보평가기/명령검증을카드마다호출하지않는다. 상세의my_application도기존상세와같은snapshot이다. GET/provider/원장쓰기·예약·자동분석갱신은없다.

목록 정렬·limit·applications_revision 및 신청변경/만료에따른cursor stale정책은기존대로다. 새프로필cursor는회원/session·room/T·프로필에결합하고 state/limit·현세대도검증한다. 다른회원/방/T/프로필또는변조cursor는400 INVALID_REQUEST, 같은범위신청변경/만료·현세대변경은409 CURSOR_STALE이다. 기본프로필cursor와서로재사용하지않는다. 분석/최소값변경은신청revision이아니며각페이지조회시점값을반영한다. 전페이지분석동일snapshot·전페이지동일evaluated_at은보장하지않는다. 각페이지권한을다시검사하고no-store를유지한다. 기존1MiB응답상한과413 RESPONSE_TOO_LARGE를유지한다.

| HTTP/code | 표시와 처리 |
|---|---|
| 401 ACCESS_INVALID | 미인증/취소·만료session, 기존Bearer challenge 유지 |
| 403 ROOM_LEADER_REQUIRED / 404 ROOM_NOT_FOUND | 기존권한/공개범위와동일, 다른신청자자료로대체금지 |
| 400 INVALID_REQUEST / 409 CURSOR_STALE | 잘못된scope/입력과같은scope변경을구분, 페이지혼합금지 |
| 503 SERVICE_UNAVAILABLE | 조회/자료실패, 정상빈목록·null/오류없음으로간주금지 |

표시/권한/오류는기존envelope를사용한다. 화면의회원·환경/session·room/T·readGeneration·dispose격리를유지한다. 성공원ACK와후속GET실패를분리하고새POST를보내지않는다. **이번제안은목록진입/재조회시점·실시간동기화·웹소켓/알림정책을바꾸지않는다.** 일반오류관찰은HTTP/code미확인으로보존하며이제안으로원인수정완료라고표시하지않는다.

## 예시·정적 검증·합의 후 순서

[작성 합성 예시](examples/application-display-v1.examples.json)는 전체페이지/일반상세의닫힌성공응답과오류envelope를담는다. 정상success·current error+retained success·missing·unrestricted/missing·소유변경·head없음·자료연결없음·빈목록, pending/경계만료/철회/거절/취소/수락후참가/수락후탈퇴/이력없음을구분한다. 실제서버/회원응답이아니다. [검증도구](tools/validate-application-display.py)는schema와cross-field·음성벡터만검증하며실행API/evaluator/DB시험이아니다.

다음Flutter는새프로필을선택해일반상세를소비가능한지,3필드의시각/누락/오류분리와4필드본인상태·기존membership-actions-1과의분리에서구체차이가있는지회신한다. 같은기존정책재수용/실서버미구현필드의기기시험을요청하지않는다. 합의후Backend는구현·bulkSQL/권한·C/N/세대/만료·기존DTO/ACK회귀·177/116실행OpenAPI전체비교를수행하고commit/push·원격확인후인계한다. 서버교체는별도승인이다.
