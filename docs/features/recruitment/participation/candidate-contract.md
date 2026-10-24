# 신청·캐릭터 변경 후보조회 보완 계약2

2026-10-24 / **계약2 구현·격리 검증 완료/실제 개발 미반영** / 작업 구간 `모집 신청·캐릭터 변경 통합 자격 보완(#26)` / `feat/raid-recruitment`. [공통 설계](eligibility-design.md)가 판정 원본이다. [제안1](candidate-proposal.md)은 이전 범위로 보존한다. 현재 구현후보의 정확한 HTTP shape는 [실행 OpenAPI](../../../../openapi/two-cycle.openapi.yaml)다. 독립 schema/작성 예시는 소비검증 자료이며 실제 개발서버 성공 근거가 아니다.

## 요청·권한·전체 응답

신규 읽기 경로는 **GET `/v2/raid-rooms/{room_id}/admission-character-candidates`**다. 제안1 application-character-candidates는 구현 대상에서 제외했으므로 호환 alias나 fallback을 신설하지 않는다.

필수 query `target_cycle_key`(기존 C/N 실제 날짜), `intent`(`apply|change_character`), 선택 `limit`(기본50/1~100), `cursor`(기본없음/1~2048문자). UUID room·현재 인증 필수, query 중복/unknown·GET body는400 INVALID_REQUEST. 같은 한 endpoint의 intent별 명시 문맥이며 apply조회로 change를 대신하지 않는다.

- 공통: 기존 방 가시성·현재 활성/open/explicit 실제T·양수gen·카탈로그 resolve. 비공개 타방404, target/room 상태 오류는 기존 code/409다.
- apply: leader_only 신청모드만, 아니면409 ADMISSION_MODE_CHANGED. actor=null. 기존 멤버/신청중·한도/일정 등 전체 쓰기 권한은 선택 후 context에서 확인한다.
- change_character: 본인 target/현세대 participating CM·현재 active Assignment 완전묶음을 서버 도출. 없으면403 WEEKLY_PARTICIPANT_REQUIRED, 불완전/상태변화는 기존409. 어떤 admission_mode든 기존 변경 권한으로 평가한다. 클라이언트 membership/CM/assignment query를 받지 않는다. actor는 본인 현재 관계 식별·revision/배치를 제공하고 snapshot에 결합한다.

응답 root는 `{scope,data}`. scope는 기존two-cycle Scope를 재사용하되 이 읽기는 target_revision/room_cycle_id/target_generation이 반드시 양수/비null이다. 모든 속성은 [closed schema2](examples/candidate-contract-v2.schema.json)의 필수/nullable/상한대로만 반환한다. source의 전체평가가 실패하면 부분 items/정상0건200을 반환하지 않는다.

| data | 의미 |
|---|---|
| room_id, intent | 요청의 명시 문맥 |
| eligibility_policy_version | 항상 admission-eligibility-2; 순서/역할/필터 의미 식별 |
| actor | apply=null, change는 membership_id·cycle_member_id/revision과 대상 assignments. IDs는 기존 본인 관계 UUID |
| evaluated_at, catalog_version | 한 snapshot의 서버시각/기존 카탈로그 version |
| snapshot_token |64hex opaque HMAC. 권한 token/선택동의 아님 |
| raw_candidate_count, eligible_candidate_count | 현재 인증·활동·usable 본인 캐릭터 distinct 전체/통합자격의 유효역할1개 이상인 전체 수. 페이지와 독립 |
| exclusion_summary | 제외 캐릭터들의 대표사유별 집계. `{reason,detail,character_count}`. COMBAT_POWER_REQUIRED의 detail만 missing/below, 나머지는 null |
| items | eligible만 UUID 오름차순으로 최대limit개. 현재 캐릭터도 자격이 있으면 유지 |
| next_cursor | 후속 없으면null. 페이지를 이어받을opaque문자열 |

각 item 필수: 기존 `registration_id,character_id,server_name,character_name,class_name,item_level` + `roles={dealer,support}`. class/level은 판정 가능한 현재 source이며 알 수 없는 자료를 가짜 값으로 만들지 않는다. 원정대 이름/대표/표시정렬 메타필드를 중복 확장하지 않는다. Flutter가 같은 회원범위의 기존 자료를 ID로 연결하며 불일치는 기존 일괄갱신/오류로 회복한다.

각 RoleEvaluation 필수는 `supported:boolean,allowed:boolean,reason:string|null,comparison:PowerComparison|null`이다.

- unsupported: false/false/ROLE_NOT_SUPPORTED/null. 일반직업support를 파티구성사유로 위장하지 않는다.
- supported: comparison은 기존 PowerComparison의 같은 필수/nullable shape. allowed=true면 reason=null·power state=unrestricted/meets. false면 ROLE_NOT_SUPPORTED를 제외한 아래 기존 reason이다. supported=true라도 다른 조건으로 실패할 수 있다.
- reason enum: ROLE_NOT_SUPPORTED(새 제안), RAID_ITEM_LEVEL_REQUIRED, COMBAT_POWER_REQUIRED, WEEKLY_ALREADY_COMPLETED, WEEKLY_ALREADY_PARTICIPATING, ROOM_FULL, ROOM_COMPOSITION_CONFLICT. 새 role code를 합의 없이 실행 API에 넣지 않는다.
- `comparison.selected_role`은 역할 key와 같고 해당 역할 최소값/성공본만 사용한다. unsupported에 다른 역할 comparison을 넣지 않는다. missing/실패자료를0으로 만들지 않는다. 전투력 상태·시각/현재/성공본 versions·issues 정책은 공통 설계를 그대로 따른다.

`actor.assignments`는 current 묶음 item UUID순, 필수는 assignment_id/revision/item_id/round_id/character_id/selected_role/party_no/slot_no다. CM/Assignment 소유·target/현세대·묶음 정합성을 서버에서 검증한다. 읽기 actor값으로 새 권한을 만들거나 원명령 ACK와 현재 관계를 섞지 않는다. 실제 변경 POST의 기존 assignments/expected revision·원본문/토큰을 유지한다.

## 계수·불가/미확인·빈화면

모든 현재 지원역할을 같은 공통 evaluator로 검사한다. unsupported는 eligible 판단에 쓰지 않는다. item에는 허용 역할1개 이상이 반드시 존재한다. 서버 source가 없는 경우 raw=eligible=0, 필터후0이면 raw>0/eligible=0이다. roles가 모두 false인 item을 보내 Flutter가 조용히 추가제외하게 만들지 않는다.

대표 제외는 **지원역할들**의 실패 중 공통사유 우선순위(레벨→전투력→완료→점유→정원/구성)로 하나를 선택한다. 같은 전투력 단계에서 missing을below보다 먼저 집계하고 나머지 동률은 dealer→support다. 이는 제외 수를 설명하는 집계이며 다른 실패가 없다는 뜻은 아니다. ROLE_NOT_SUPPORTED는 캐릭터 대표 제외집계에 넣지 않는다. 예: dealer-only의 dealer가중복이면 support 미지원이 아니라 ROOM_COMPOSITION_CONFLICT로1명 집계한다.

`sum(exclusion_summary.character_count) = raw - eligible`, 같은(reason,detail)중복 금지·count양수.0<=eligible<=raw, items중복 금지·items수<=limit/eligible. 같은snapshot 후속페이지의 계수/집계/actor·정책은 동일하다. 빈 source에서는 summary=[]이고, missing 전투력 때문에0건이면 detail=missing 집계를 표시해 인증/활동캐릭터 자체가 없다는 안내와 구분한다. DB장애/불완전 source는 오류/재시도이며 이 summary로 감추지 않는다.

예측 불가능한 level/class/관측값 무결성 누락은409 CHARACTER_DATA_UNAVAILABLE(카탈로그 문제는 기존코드), weekly/lease 불일치는409 WEEKLY_OCCUPANCY_CHANGED, 상태불확정 target은 ROOM_REVIEW_REQUIRED, DB/내부장애503 SERVICE_UNAVAILABLE. 인증401·권한404/403과 기존 에러 envelope를 재사용한다. 후보/변경 actor의 실패와 정상 후보0건을 구분한다.

## 페이지·snapshot·소비

한 read-only REPEATABLE READ에서 본인 graph/role heads·성공본/주간state·lease/target·generation·rounds·확정배치·교체대상을 bulk 적재하고 메모리에서 모든 자격/계수를 계산한 뒤 자른다. 캐릭터별 context N회/선행 전체멤버GET·provider/쓰기·persistent token은 없다. 구현 시험에서 DB query 수가 후보수에 비례하지 않음을 계측한다.

HMAC은 회원/session·배포환경 key·room/실제T/현세대·intent·actor/대상Assignment IDs/revisions·권한/등록/활동/canonical/lifecycle·class/level·두role 성공본/현재head/전투력 최소값·catalog·전체묶음/확정구성·주간/lease·정책version을 결합한다. `evaluated_at`/limit은 hash에서 제외해 같은 자료의 후속조회만으로 stale을 만들지 않는다. 회복 가능한 권한이나 schema를 token으로 인코딩/공개하지 않는다. 현재C/N 기준 변동도 scope에 결합한다.

cursor는 actor/session·room/T/intent 범위와 snapshot/offset을 MAC 보호한다. 위조·다른범위400 INVALID_REQUEST, 같은범위 자료변경409 CURSOR_STALE; 타인cursor를 stale로완화하지 않는다. limit변경은 허용하고 offset은 절대로 total범위를 넘기지 않는다. 끝이면 next_cursor=null. 페이지 직렬화 응답은 기존 후보조회와 같은1MiB 상한을 사용하고 초과하면 기존413 RESPONSE_TOO_LARGE, 자료정합성검사 실패면 해당 전체 오류다. 부분 성공/잘림으로 정상0건을 만들지 않는다. 서버에 MVCC snapshot을 요청 간 유지하는 것이 아니라 같은 내용지문인지 재검증하는 방식이다.

Flutter는 전페이지를 같은snapshot/계수/actor·정책에서 취합하고 UUID중복/역행·cursor순환·최종누락을 거절한 뒤 기존 원정대별 레벨순으로 한 번 표시한다. 기존 선호역할이allowed이면 유지, 아니면 유효역할 선택. 불가역할로 상향하지 않는다. 회원/환경/session/readGeneration·room/T/intent·선택/조회epoch/dispose로 늦은 응답을 차단한다. 새 명시조회는 실제남아있는 선택만 유지한다. 로딩/부분페이지/실패를0건과 구분한다.

선택 후 기존 admission-context(intent=apply|change_character)와 현재 context의 targets/selection/동의·토큰을 사용한다. 후보 snapshot_token은 쓰기본문에 추가하지 않는다. 후보조회와 선택/쓰기 사이 변화는 기존context/POST·승인에서 재검증한다. 원pending/24hACK·권한/현재상태와 원성공 분리는 보존한다. 성공/오류 모두 no-store다.

## 예시·검증·합의 대상

[합성 작성 예시](examples/candidate-contract-v2.examples.json)는 일반 dealer-only, 복수역할 한/양역할·역할별전투력, missing/조건필터후0/source0, retained 성공+새head실패/경고, 변경actor/원파티자기제외·반대파티, 페이지2개를 포함한다. 실제 개발DB/HTTP 응답이나 본 기능 실행 시험이 아니다. [정적 검증 도구](tools/validate-candidate-contract.py)는 closed shape·권한/role/power/계수/페이지 불변식을 검사한다.

네이티브 검토가 필요한 변경은 새공통GET/intent·서버도출actor, ROLE_NOT_SUPPORTED와 지원역할 필터/eligible, exclusion_summary의 missing구분, 보존 성공값/경고·시각 표시,8인변경 원파티우선→반대파티 배치 및 공통사유 우선순위다. 기존에 확인된 정책의 반복 수용이 아니라 이 wire/행동 차이를 확인한다. 합의 뒤 공통검증→읽기→직접회귀/계약검증→게시/소비 인계 순서로 진행한다. DB migration·원자료변경/개발배포·dev/main 통합은 승인 범위에 포함하지 않는다.


설계 source `77be3a955cb8e3a91c5a2cf212c45d622e03aba0` commit/push·원격 SHA 일치 확인 뒤 [#26 전체5번째 Backend · 통합 자격 기획/설계·보완 계약2](https://github.com/heo0328/lostparty-backend/issues/26#issuecomment-6381680561) 게시·전문/전체 순번을 재조회했다. 다음 담당 Flutter 구체 소비차이 검토, Backend 차이 반영/합의 후 구현이며 계약 확정·새 API 실행/실인수 완료가 아니다.


## 최신 협의 상태

[#26 전체6번째 Flutter · 보완 계약2 소비 검토/사용자 UX 확정](https://github.com/heo0328/lostparty-backend/issues/26#issuecomment-6381816954)에서 공통 GET/intent·actor·역할/전투력·계수/페이지·사유우선순위를 소비 가능으로 확인했다. 문서e7bfe113 push 보고이며 Backend 독립 실행 검증은 아니다.8인 파티이동 확인·동의와 수락 자격실패 시 pending유지 UX도 확정됐다. 추가 예약/일정 영향이 발견되지 않으면 별도 사용자UX 결정을 기다리지 않고 확정범위 구현으로 진행한다.

계약2의 wire/판정·8인 변경/대표사유 순서는 전체6 기준으로 수용됐다. 본문 중 합의 대상/제안 표기는 당시 검토 항목으로 보존하며 동일 항목 재수용을 요구하지 않는다. 구현 시 확인 뒤 바뀐 targets.party_no/현재actor·Assignments/revision·자격·일정동의를 기존 token/최종검사에 결합하고 원동의로 다른배치를 실행하지 않는다. 자격미달 승인실패는 pending/기존참가·예약 불변이며 자동거절/철회하지 않는다. 상세 UX/인수구간은 [통합 설계](eligibility-design.md)의 최신 확정 절을 따른다. 추가 일정영향이 발견될 때만 구체 차이를 회신한다.


## 현재 구현·인계 경계

GET과 apply/change/approval 공통판정·확인배치 결합을 구현했다. [통합 설계의 실행 결과](eligibility-design.md#구현직접-검증-결과)·[검증 집계](validation/eligibility-results.json)를 따른다. 기본116/후보177 전체 비교·기존component/쓰기DTO 보존, 신규19+직접회귀26=고유45PASS다. 부분페이지/명령실패·승인pending유지/변경rollback은 직접시험 근거이고 디자인21벡터와 구분한다. 이 문서의 제안/합의 후 구현 표현은 작성 당시 설계 절차이며 Flutter 전체6의 수용과 현재 구현 완료 상태가 우선한다.

다음 Flutter는 게시 source/177계약으로2가입의 reader/후보/role/빈화면·원명령 연결을 진행한다. 변경 실제조작은3방내부행위/주차교차는5에 인수한다. 실제 개발서버 반영은 별도 승인 후이므로 현재 새endpoint 실서버/실회원 시험을 요청하지 않는다.


구현 source `484ca1719e21b01a59da75b62a1d3b1568ada2c3` / feat/raid-recruitment commit·push·원격 SHA 일치 확인 후 [#26 전체7번째 Backend · 계약2 구현/검증 인계](https://github.com/heo0328/lostparty-backend/issues/26#issuecomment-6382258395) 게시·전문/실제 전체 순번을 재조회했다. 다음 담당 Flutter2가입 연결·직접 자동검증/Backend 재현차이 대응이다. 실제 개발API67322372…/176·DB0031 healthy/health200·기존이미지 미교체를 읽기 확인했고 시험용 runner/DB/internal network/API probe는 정리해 기존API/DB만 남겼다. 실회원/기기·개발반영/운영은 별도 미완료다.
