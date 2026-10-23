> **보관된 작업 원문:** 아래 현재·다음·미구현 표기는 작성 당시 상태입니다. 현재 설명: [usage-limits](../../../../features/login-account/usage-limits/README.md) · [management](../../../../features/groups/management/README.md) · [participation](../../../../features/recruitment/participation/README.md). [문서 대응표](../../../../engineering/documentation/README.md). 원문 바이트와 근거는 기준 커밋 `7f7f767`에서 확인합니다.

# 계정별 이용 한도·방 제한 공통 계약안

2026-10-17. **최신 사용자 확정 영향범위로 정정, L0 내부기초 작업. HTTP/실제 방 연결은 미구현**. [#12 일곱 번째 Backend 명세](https://github.com/heo0328/lostparty-backend/issues/12#issuecomment-6232669446). 기준은 [#12 다섯 번째 Flutter 요청](https://github.com/heo0328/lostparty-backend/issues/12#issuecomment-6232562970), [#13 세 번째](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6232565592)다. 최신 #12 10개/#13 7개를 확인했고, 아홉 번째 확정/일곱 번째 통계 요청을 반영한다. 작업 시작 `feat/raid-services` HEAD `6cfe4a7`, 그룹 내부 기초 `e5e97c8`을 재사용한다. 기존 문서 변경4개를 보존한다. [#13 네 번째 Backend 연결범위 회신](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6232674169)으로 공통원본과 모집/개인체크 경계를 공유했다. 새 DTO/오류/경로는 아래 검토안이며 실행 OpenAPI에 아직 추가하지 않는다.

## 1. 기본 한도와 권위 상태

| 차원 | 기본값 | 적용 주체/현재 사용량 |
|---|---:|---|
| group_capacity | 15 | 그룹의 현재 그룹장 계정값 / 해당 그룹의 현재 확정 회원 수(그룹장 포함) |
| joined_groups | 5 | 앱 회원UUID / 현재 가입 그룹 수(직접 생성 포함) |
| raid_rooms | 10 | 앱 회원UUID / 모든 원정대·캐릭터의 현재 확정 참가 방을 room UUID별 한 번 집계 |

값은 서버의 회원별 데이터다. 기본값을 HTTP 코드 곳곳에 고정 제품 상수로 박거나 사용자가 직접 PUT하게 하지 않는다. 정원과 목록limit, 한도와 주간 완료는 별개다. 수치의 저장 범위는 정수0..2147483647로 제안한다. 0이면 기존자료를 지우지 않고 새 증가를 거부하며 정리 명령은 유지한다.

유효 membership은 현재 확정 관계이고 membership/대상 group 또는 room의 종료 시각이 모두 없는 관계다. 초대·가입신청·승인대기는 사용량에 넣지 않으며 수락/승인/직접가입의 최종 쓰기에서 재검사한다. 종료된 관계는 집계에서 제외하되 이력은 보존한다. 시간 만료를 쓰는 후속 관계는 DB 서버 시각으로 유효성을 판정하고 배치 실행 여부로 권한을 만들지 않는다.

room은 생성자가 이미 참가한 경우 두 번 세지 않는다. 완료 후 잔류/다음 주 함께하기의 확정 참가관계가 계속되면 같은room1개를 유지한다. 회차/주차 변경이나 주간 점유 해제만으로 사용량을 초기화하지 않는다. G3의 그룹장 이전은 새 그룹장 유효 group_capacity로 다시 평가한다.

**정확히 한도**면 기존 관계/방은 정상이고 해당 차원의 증가만 거부한다. **초과**면 원인과 관련 방의 제한을 계산하며 기존 방/회원/주간 완료/참가 snapshot을 삭제하지 않는다. 단순 GET/캐시/클라이언트bool은 상태를 수정하거나 정상으로 승격하지 않는다.

## 2. 한도와 사용량 저장 경계

최소 추가 구조안:

- `member_usage_limits`: user_id PK, revision>=1, group_capacity/joined_groups/raid_rooms, updated_at UTC. actor UUID가 신원이며 원정대/캐릭터별 한도 행을 만들지 않는다.
- `member_usage_heads`: user_id PK, revision>=1. 가입/참가의 확정·종료가 바뀌면 해당 사용자의 사용량 revision을 같은 transaction에서 올린다. 숫자 count는 활성 관계 원본을 조회하며 head 자체를 카운터 권위로 사용하지 않는다.
- `member_usage_limit_audits`: 변경 대상·이전/새 값·revision·서버 변경 주체/사유/시각. 사용자 응답에는 운영 메모/타인 한도 원문을 노출하지 않는다.

기존회원에 행이 없는 읽기는 기본정책 revision1과 기본값을 반환하고 삽입하지 않는다. 첫 관련 명령/신규회원 초기화에서 서버가 기본 행을 만든다. 이후 계정별 값은 명시적 변경으로 관리한다. 기본정책 변경으로 기존 사용자 값을 조용히 덮지 않는다.

한도 변경은 서버 내부의 권한 있는 호출만 사용하고 예상limits_revision/CAS·감사·현재시각을 검증한다. 현재 별도 운영자 권한 API가 없으므로 공개 관리자 PUT이나 회원 role을 임의로 추가하지 않는다. 결제/구독/광고/영수증·상품/기간권을 구현하지 않고, 가상 만료일/자동grant도 만들지 않는다. 운영 변경 도구가 필요하면 대상과 권한을 별도 인계한다.

한도 감소/관계 변경과 실제 명령은 기존 `authorize(write=True)`의 전역 game-mutations 락을 공유한다. 서버 내부 한도 변경도 같은 락을 사용해야 한다. 유효 한도·현재 count·등록/소유/활동·그룹/방 역할·원장/슬롯을 최종 transaction에서 확인한다. 네트워크를 락 안에서 호출하지 않는다.

## 3. 본인 조회 API 제안

`GET /v1/me/usage-limits`: 현재 활성 로그인 필수. query/body 없음, no-store. 타회원ID 입력/다른 사용자 한도 조회/사용자PUT은 제공하지 않는다. 반환값은 권한 증명서가 아니며 읽기시점의 안내다.

필수 필드:

| 필드 | 의미 |
|---|---|
| policy_version:string | `member-room-limits-v1` |
| evaluated_at:UTC datetime | 같은 읽기 snapshot의 DB 서버 평가시각 |
| limits_revision:int>=1 | 현재 계정 한도 버전(행 없으면1) |
| usage_revision:int>=1 | 현재 관계 사용량 버전(행 없으면1) |
| limit_source:`default|account` | 서버 기본값 또는 회원별 저장값 |
| updated_at:datetime|null | 계정값의 마지막 저장시각, 행 없으면null |
| limits | `{group_capacity:int,joined_groups:int,raid_rooms:int}` |
| usage.joined_groups / usage.raid_rooms | UsageMetric |
| issues:list[AccountLimitIssue] | 현재 회원의 개인 초과 사유, 없으면[] |

UsageMetric의 모든 필드는 필수: `used:int|null`, `remaining:int|null`, `state:within|at_limit|exceeded|unavailable`, `can_increase:bool|null`. remaining은max(0,limit-used)다. 아직 원장 자체가 없는 기능은unavailable/null로 내보내고 준비된0/정상으로 주장하지 않는다. 현재 G1이 선행하면 raid_rooms 집계/제한은미지원으로 구분하며 아직 없는 모집 쓰기를 허용하는 근거로 사용하지 않는다. #13 활성화 전 실제 참가 원본/guard를 연결해야 한다. 이미 활성화된 집계가 장애인 경우에는unavailable로 명령을 허용하지 않고503 LIMIT_STATE_UNAVAILABLE로 거부한다.

AccountLimitIssue: `code:MEMBER_GROUP_LIMIT_EXCEEDED|MEMBER_RAID_LIMIT_EXCEEDED`, `dimension`, `used`, `limit`. 본인 한도 API에 타인 문제·그룹별 명단을 포함하지 않는다. 그룹 정원은 각 그룹의 현재 그룹장과 실제 인원을 기준으로 그룹 상세에서 계산하며 본인계정 하나의used로 표현하지 않는다.

G1 선행 조회 예시(숫자/시각은 가상):
```json
{
  "policy_version":"member-room-limits-v1",
  "evaluated_at":"2026-10-17T00:00:00Z",
  "limits_revision":1,"usage_revision":3,"limit_source":"default","updated_at":null,
  "limits":{"group_capacity":15,"joined_groups":5,"raid_rooms":10},
  "usage":{
    "joined_groups":{"used":2,"remaining":3,"state":"within","can_increase":true},
    "raid_rooms":{"used":null,"remaining":null,"state":"unavailable","can_increase":null}
  },
  "issues":[]
}
```

## 4. 확정된 원인별 영향 범위 (종전 광범위 상속안 대체)

최신 확정은 [#12 아홉 번째 Flutter](https://github.com/heo0328/lostparty-backend/issues/12#issuecomment-6232797572)와 [#13 여섯 번째](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6232799560)다. 일곱 번째 Backend 제안의 개인초과→모든 가입그룹 제한/연결방 상속은 채택되지 않았다. 여덟 번째 Flutter의 질문3건도 해소됐다.

| 원인 | 기존 그룹 운영 | 제한되는 현재 레이드 방 |
|---|---|---|
| MEMBER_RAID_LIMIT_EXCEEDED | 정상 유지 | 당사자가 직접 참가한 공개·그룹전용 방 모두. 미참가 연결방에는 전파하지 않음 |
| MEMBER_GROUP_LIMIT_EXCEEDED | 정상 유지 | 당사자가 직접 참가한 그룹전용 방만. 공개·미참가 방에는 전파하지 않음 |
| GROUP_CAPACITY_EXCEEDED | 운영/초과 안내 유지, 새회원 확정 차단, 탈퇴/권한있는 추방/그룹장이전 허용 | 해당 그룹의 모든 현재 그룹전용 방. 초과 원인자의 직접 참가 여부와 무관하며 일반 공개/다른 그룹에는 전파하지 않음 |

개인 가입그룹5/5·레이드10/10·그룹정원15/15는 기존 이용 정상이며 해당 차원의 증가만 거부한다. 개인 그룹6/5부터 새 그룹 생성/가입·그룹전용 레이드 참가와 직접 참가한 그룹전용 방 진행을 차단한다. 그룹장 정원15·인원18은 기존 그룹 운영을 정지/삭제하지 않지만 해당 그룹의 그룹전용 레이드는 모두 정지한다.

정지방에서는 다른 회원도 추가모집/참가확정·캐릭터교체·완료·다음주계속을 진행할 수 없다. 권한있는 조회·탈퇴·추방·정리·이전은 유지한다. 원인들은 OR로 누적하고 관련 원인이 모두 없어야 정상화한다. 관계 종료/한도 회복은 다음 원본 평가에 반영하며 캐시·배치 정상bool·주차 변경으로 원인을 없애지 않는다. 기존 완료/참가 snapshot은 보존한다. 공개전환/그룹연결 변경으로 원인을 숨기는 우회는 실제 해당 명령의 최종 관계와 권한으로 검사한다.

문제회원의 레이드 상세 문구는 ‘최대 참가 횟수 초과’다. Flutter 탭 우상단 표시는 레이드의 현재참가방수/개인레이드한도, 그룹의 현재가입그룹수/개인가입그룹한도이며 그룹정원15를 가입한도 분모로 쓰지 않는다. 미지원/실패를0/정상으로 표시하지 않는다.

## 5. 방 조회·permissions 제안

검토 중인 G1 GroupDetail과 후속 #13 RoomDetail에 `access`를 추가하는 안이다. 그룹 access는 개인 가입/레이드 초과만으로 restricted가 되지 않는다. 그룹 정원 초과도 기존 운영을 일괄 정지하는 bool 대신 명령별 permissions와 레이드 제한 원인으로 표시한다. RoomDetail만 확정 영향표에 따라 진행제한을 계산한다. G1은아직HTTP미연결이므로 최종 계약 게시에서strict DTO를함께정리한다. 이미연동된#11 DTO를지금확장하지않는다.

- `access.state:normal|restricted`, `evaluated_at:datetime`, `policy_snapshot:string`(불투명한 평가 fingerprint), `issues:list[RoomLimitIssue]`.
- RoomLimitIssue: `code`(위3종류), `dimension`, `used`, `limit`, `offender:MemberRef`, `origin_group_id:UUID|null`. MemberRef는 `{scope:group|room,membership_id:UUID,display:CharacterDisplay|null}`로 해당 조회 권한 안의 문제 회원을 표시한다. 전역user UUID·연락처·타인전체가입목록/한도변경사유는 응답하지 않는다.
- 공개요약에는 `restricted:bool`/일반적 제한사유만 제공하는 안이며 원인 회원/수치는 현재 가입자 등 권한 있는 상세에서만 보인다. 공개목록을 통해 private 명단을 추론하지 않도록 한다.
- 각 명령 Permission은 `allowed:bool,reason:string|null`을 유지하고, 허용여부는 역할/현재상태/현재한도/명령종류 모두를 확인한다. restrictions는 역할을 부여하지 않는다. 미구현G2/G3/파티명령을allowed로 노출하지 않는다.

policy_snapshot은 현재 관련한도revision·사용량head·group/member/room/회차 revision과 원인관계 집합을 digest한 불투명값이다. 클라이언트는 계산/수정하지 않는다. signature/fingerprint는권한이 아니며 최종명령은실제상태를다시읽는다. 새명령의예상snapshot이달라지면409 POLICY_CONTEXT_CHANGED로현재GET후새의사결정을받는다.

새 G1 생성은 GroupCreateIn에 `expected_limits_revision`, `expected_usage_revision`을 추가하는 안이다. 원래 registration/ownership/roster/lifecycle revision은 유지한다. G1 이름 수정은 현재그룹장/멤버·그룹revision을 유지하고, 이름만수정하는명령에새참가권한을요구하지않는다. 기타상태변경예상snapshot은실제HTTP최종명세에서명령별로정의한다.

## 6. 제한 상태의 명령표 제안

| 명령 | 정상/정확히 한도 | 초과로 제한된 관련 방 | 유지할 서버 조건 |
|---|---|---|---|
| 권한 있는 조회/문제 표시 | 허용 | 허용 | 기존public/private·membership 권한 |
| 새 그룹 생성 | 가입그룹수 증가가한도안이면허용 | actor 가입그룹수 기준. 레이드수초과만으로 거부하지 않음 | 현재활동/소유/usable·현재한도/CAS |
| 가입/수락/직접참가·새모집 생성 | 해당증가후각한도안이면허용 | 위 영향표의 해당 차원/방 원인에 따라 거부 | 역할·선택캐릭터·원장/슬롯·정원 |
| 캐릭터교체/방완료/다음주계속 | 기존제품조건으로판정 | 거부(다른회원도동일) | 기존역할/회차/주간조건 |
| 본인 탈퇴 | 기존제품조건 | 회복명령으로허용 | actor본인·현재membership, 책임자는아래이전/종료필요 |
| 권한 있는 추방 | 기존제품조건 | 회복명령으로허용 | 기존책임자권한, 타인에게새추방권한을주지않음 |
| 책임자 이전 후 탈퇴 | 기존제품조건 | 회복경로로허용 | 현재책임자→기존유효member, 회원/방증가없음. 그룹은새그룹장정원검사 |
| 마지막1인 종료/조건부해산 | 기존제품조건 | 회복명령으로허용 | 현재권한·마지막인원·pending/연결모집을실제원본으로검사 |
| 본인신청철회/권한있는초대취소 | 기존제품조건 | 정리동작허용 | 본인/관리권한, 확정참가/완료를임의복구하지않음 |
| 그룹명 등 비진행 메타데이터 수정 | 기존권한/CAS | 기존권한/CAS | 인원/역할/진행상태를바꾸지않음 |

회복을 위한 책임자 이전은 사용량이 즉시 줄지 않더라도 이후 본인탈퇴 경로를 열어야 한다. 새회원/방을 늘리지 않고 새그룹장의정원이현재인원을수용하는지검사한다. 다른초과원인이남으면이전후에도방제한은유지된다. 책임자이전이완료/다음회차진행을동시에수행하는우회명령이되면안된다. 정원이부족한대상으로이전하는대신권한있는추방/자발적탈퇴로인원을먼저정리할수있다.

G3의해산은기존조건인1인·pending없음·활성연결모집없음을유지한다. 진행이막힌모집도권한있는종료/해산으로정리할수있되완료처리/과거snapshot삭제로대체하지않는다. 자동탈퇴·임의의방유지선택·자료삭제는없다. 제한중공개전환으로그룹연결제한을우회하는경로는허용하지않고상세전환정책을G3/#13에서명시한다.

## 7. #11 개인 체크와 #13 방 명령의 경계

주간원장의완료근거/점유와현재방membership은다르다. #11첫API의원자성·완료/점유제약을임의로완화하지않는다.

- 방과무관한개인manual true/false는별도개인기록이며모든회원의수동체크를일괄차단하지않는다.
- 개인정정false는manual근거만제거하고party완료/과거snapshot·현재방진행을복원하지않으므로회복을우회하지않는다.
- 관련제한방의현재점유에영향을주는manual true/영향확인실행은그방의현재permissions를검사한다. 제한방의탈퇴+완료를한명령으로자동확인하지않고관련진행이금지면전체를거부한다. 본인탈퇴는별도회복명령으로가능하고, 종료된관계이후방상태를변경하지않는개인완료를막지않는다.
- 개인완료집계가파티자동완료/다음회차진행을유발하는후속구현은반드시방guard를통과해야한다. manual source만보고제한방을완료로승격하지않는다.

현재#11은실제파티/영향확인실행미연결이며점유있음은이미409로보류한다. 새ROOM_RESTRICTED류code/WeeklyEntry reason확장/영향확인token이필요한시점에#11/#13/OpenAPI와Flutter strict DTO를함께합의한다. 이번공통명세만으로이미연결된DTO를변경하지않는다.

## 8. transaction·회복·오류

한도변경과관계변경은같은락순서를공유한다. 증가명령은권한·현재한도·현재사용량/CAS·기타캐릭터/주간/슬롯검사후모두commit하거나rollback한다. 사용량head증가도관계변경과같은transaction이다. 단순캐시카운트나만료batch의정상bool은사용하지않는다.

동시마지막1자리/개인한도마지막1개·한도감소/생성·그룹장이전·탈퇴/추방/다음회차경합에서는하나의revision순서만성공한다. 광범위pending목록은별도종료해도최종확정시공통guard로중복진행을막는다.

멱등은기존actor/operation/UUIDv4 key+정규화target/body를사용한다. 응답유실은원key/body가우선이다. 과거성공ACK는현재진행권한이아니다. replay는현재session/기본자원접근을검사하고원성공을돌려주되새쓰기/회복/진행으로재실행하지않는다. 새로운한도나방상태는현재GET을조회한다. 권한을잃은관계를과거응답으로부활시키지않는다.

새 오류안은 기존 `{error:{code,message,request_id}}`/no-store를재사용한다.

| 상태 | code | 의미 |
|---|---|---|
| 409 | GROUP_CAPACITY_REACHED / GROUP_MEMBERSHIP_LIMIT_REACHED / RAID_MEMBERSHIP_LIMIT_REACHED | 증가 명령이 현재 한도를 넘음 |
| 409 | ROOM_RESTRICTED | 현재 관련방이초과원인으로진행제한 |
| 409 | POLICY_CONTEXT_CHANGED / REVISION_CONFLICT | 한도/사용량/관계예상기준변경, 현재GET후새판단 |
| 503 | LIMIT_STATE_UNAVAILABLE | 활성집계/정책을현재확인할수없어거부 |
| 기존401/403/404/409 | 기존인증·자원·권한/멱등code | 한도정책으로기존권한을우회하지않음 |

제한원인목록과회복가능동작은권한있는현재상세에표시한다. 기존오류DTO에타인정보를임의추가하지않는다. 예외로그에는한도대상회원원문/실제이름/전체관계목록을출력하지않는다.

## 9. G1 영향과 독립 구현 순서

1. **L0 공통한도기초**: 한도/사용량head·기본읽기·내부권한조정경계/감사·그룹현재사용량·평가형식. #13 원장미연결은명시적으로구분한다. G1필수policy에현재활동집합과계정별한도/CAS를연결할수있게한다.
2. **G1 HTTP연결**: 본인한도GET와생성예상limits/usage revision, 그룹명/저장대표이름검색정규화, 공개/회원조회·목록/cursor·permissions/OpenAPI. 격리검증후작업브랜치push·원격확인·현재DB적용/API반영을별도기록한다. group-core명령과최종HTTP명령의과거응답을혼동하지않는다.
3. **G2/G3**: 실제가입/수락·현재사용량/원인·종료/이전/해산과회복명령을연결한다. 명령을아직구현하지않았다면permissions를허용하지않는다.
4. **#13**: 실제room membership/회차조회와room별합산10·원인별직접참가/그룹자체정원제한·확정참가/주간점유·완료/반복/회복transaction을연결한다. #11관련점유영향명령은이때호환명세로맞춘다.

단계별검증은기본값/개별조정·GET쓰기0·일반회원한도조작거부·현재종료관계제외·같은방중복집계0·주차무초기화·정확한한도/초과·동시증가/한도감소·다른회원진행제한·권한있는회복/권한없는추방거부·대표이전후정원·원인해제·부분실패rollback·과거ACK/완료snapshot불변·무관한개인체크보존을해당실제구현단계에서진행한다. 아직없는그룹/파티의모의검증을실연결완료로보고하지않는다.

4절의 영향범위는 사용자 확정이며 추가 제품결정 대기는 없다. DTO/오류/HTTP는 최종 G1 인계에서 구현과 함께 확정한다. L0 내부기초 결과는 NEXT_WORK/DEV_LOG를 따른다. 개발DB/API 적용·실제 모집 연결·통계는 별도 단계다. 기본로그인/장비인증 반복시험·결제/광고·기존자료 이관/초기화는 요청하지 않는다.

정정/L0결과 게시: [#12 전체11번째 Backend](https://github.com/heo0328/lostparty-backend/issues/12#issuecomment-6232977320). 구현fcbb840/push확인·HTTP/개발DB미적용.


## G1 연결 완료 구간

본인한도GET·생성의expected_limits_revision/expected_usage_revision·현재활동/가입한도/그룹정원검사를G1 HTTP에연결했다. 그룹회원상세는capacity:{limit,used,remaining,state}로현재정원을안내하며공개요약/기존운영권한은유지한다. 미구현RoomDetail/access/방원인guard는선제노출하지않는다. 실제방/통계연계는별도이며최신실행상태/DTO는 [G1 안내](ISSUE_12_GROUP_G1_DEVELOPMENT.md)·NEXT_WORK/OpenAPI를따른다. 과거‘HTTP미적용/개발DB0011’은L0인계당시상태다.
