# #12 그룹 G1 API 명세안

2026-10-17. **G1 HTTP 구현 구간. 최신 요청/응답·검증/적용 상태는 [개발 안내](ISSUE_12_GROUP_G1_DEVELOPMENT.md) 우선.** 최초 명세의 이력은 아래와 같다. [#12 첫 번째 Backend 명세 댓글](https://github.com/heo0328/lostparty-backend/issues/12#issuecomment-6232074318). 작업 브랜치 `feat/raid-services`, 기존 구현 HEAD `2297fba`. [Issue #12](https://github.com/heo0328/lostparty-backend/issues/12)의 본문과 댓글0개, #13 댓글0개, #8 최신120번째까지 확인했다. 기존 현황문서의 미커밋 변경3개를 보존한다. 이 문서는 검토용이며 실행 중인 OpenAPI에 미구현 경로를 추가하지 않는다.

최신 정정: [#12 세 번째 Flutter 회신](https://github.com/heo0328/lostparty-backend/issues/12#issuecomment-6232491349)으로 **계정별 기본 그룹정원15명/현재가입5그룹, 생성·가입 캐릭터의 현재 활동집합 포함 필수, 그룹명 또는 그룹전용대표 캐릭터명 검색**을 확인했다. 아래 명세에 반영하되 내부기초코드/HTTP/개발DB에는 아직 이 정정을 적용하지 않았다.

## 1. 범위와 정책

G1은 생성/공개 검색·요약/내 그룹·상세/멤버 조회와 그룹명 수정이다. 초대·신청·코드·차단은G2, 그룹장 이전·탈퇴·해산은G3다. 파티/모집·주간 원장과 결합하지 않는다. G1에서 일반 회원을 직접 가입시키는 명령은 없다.

- 그룹은 원정대/캐릭터가 아닌 앱 회원의 모임이다. `group_id + user_id`는 유일하며 생성자는 그룹장 membership1개로 즉시 등록된다. 여러 원정대를 가졌다고 여러 자리가 생기지 않는다. 멤버 권한은 현재 서버 세션/그룹 membership에서 판정한다.
- 생성 캐릭터는 요청 등록 범위의 현재 인증 소유·usable canonical UUID여야 한다. active/confirmed/정상NameClaim과 예상 revision을 검사한다. 별도1700 하한·레이드 입장레벨·표시 수·대표 여부·주간 완료를 그룹 생성 조건으로 추가하지 않는다. 현재 활성 설정의 Activity 집합 포함을 생성/가입의 최종transaction에서 검사한다. 이후 활동해제만으로 기존membership/그룹장권한을 삭제하지 않는다.
- 그룹 대표는 생성 시 선택한 캐릭터의 UUID/그 당시 표시 snapshot을 그룹에 별도로 보관한다. 사용자 대표 변경으로 바꾸지 않는다. 이름만으로 새 ID를 이어 주지 않는다. 현재 소유/생명주기/claim이 무효가 되면 `needs_update`를 표시하되 그룹·membership/그룹장 권한을 지우지 않는다. 대표 변경 명령·그룹장 이전 이후 선택 범위는G3에서 확정한다.
- 현재 User 모델에는 공개 닉네임 필드가 없다. 새 회원 프로필 기능을 만들거나 계정 UUID를 이름처럼 표시하지 않는다. 그룹장 표시는 그룹 membership에 저장한 캐릭터 표시 snapshot으로 제공한다. G1에서 생성자의 표시와 그룹 대표 표시는 같은 snapshot으로 시작하지만 별개 기록이다.
- 그룹명은 원문의 줄바꿈/줄 구분 문자·제어문자를 먼저 거부하고 trim 후 Unicode code point1~20자인지 검사한다. 이름 중복은 허용한다. NFC 변환·이름 기반 identity는 추가하지 않는다. 생성 요청의 name 생략은 선택 캐릭터명+`의 그룹`이다. 기본명이20자를 넘으면 자르지 않고400 GROUP_NAME_REQUIRED로 명시 이름을 받는다. null/빈 이름은400 INVALID_REQUEST다.
- 최신다섯번째회신에따라한계는계정별서버데이터다. 그룹정원은현재그룹장의기본15명(생성자/그룹장포함), 현재가입그룹은회원기본5개(직접생성포함/종료membership제외)다. 실제검사는유효한도/현재사용량/revision을읽고고정상수로영구확정하지않는다. G1 생성에서는현재가입5개를, G2가입/수락에서는그룹15명·회원5개를DB transaction/동시성경계에서검사한다. 과거50/50·제한미확정/무제한설명은최신정책이아니다. 조회limit와제품정원은별개다.

## 2. 경로와 접근 범위

일반 공개 검색이라는 요구에 맞춰 공개 GET2개는 세션 없이 최소 정보만 제공하는 안이다. 회원 전용 경로는 현재 로그인·활성 membership을 검사한다. 세 번째 Flutter 회신은 공개최소요약/회원전용분리안이기존공개검색진입과충돌하지않음을확인했다.

| Method/path | 인증/권한 | 입력·결과 |
|---|---|---|
| POST `/v1/groups` | 활성 로그인, 선택 캐릭터 현재 소유/사용가능 | GroupCreateIn →201 GroupDetail, 그룹과 생성자 membership 원자 생성 |
| GET `/v1/groups` | 공개·무인증 | q/limit/cursor →200 GroupSummaryPage |
| GET `/v1/groups/{group_id}` | 공개·무인증 | UUID →200 GroupSummary |
| GET `/v1/me/groups` | 활성 로그인 | limit/cursor →200 MyGroupPage(본인 활성 membership 그룹만) |
| GET `/v1/me/groups/{group_id}` | 활성 로그인·해당 그룹 멤버 | UUID →200 GroupDetail |
| GET `/v1/groups/{group_id}/members` | 활성 로그인·해당 그룹 멤버 | limit/cursor →200 GroupMemberPage |
| PATCH `/v1/groups/{group_id}` | 활성 로그인·현재 그룹장 | GroupRenameIn →200 GroupDetail(이름만 수정) |

모든 경로는 Cache-Control:no-store. 조회는 DB 저장 상태만 읽으며 기본 head/자료를 삽입하거나 외부게임API·개인키를 호출하지 않는다. GET본문/알 수 없는 query/중복 scalar query는400이다. 대표 변경·일반 가입·join URL을 미리 제공하지 않는다.

## 3. 요청 DTO

추가필드는 거부하고 revision은 strict integer>=1, UUID는 정규 UUID, 멱등키는UUIDv4다.

`GroupCreateIn`:

- registration_id:UUID, character_id:UUID
- expected_registration_version, expected_ownership_revision, expected_roster_revision, expected_lifecycle_revision: integer>=1
- name: 선택 문자열. 생략만 자동 이름이며 null은 거부한다.

registration은 actor의 현재 등록이어야 하며 character의 account와 일치해야 한다. actor/leader_user_id/member_id/role/client snapshot을 입력으로 받지 않는다. 생성자와 그룹 UUID는 서버가 결정한다. 대표/활동 settings_version은 입력받지 않으며 현재활동포함은 최종transaction에서 검사한다. 최신 생성DTO는 expected_limits_revision/expected_usage_revision도 필수다.

`GroupRenameIn`: name:string(필수), expected_revision:integer>=1, expected_membership_revision:integer>=1. 현재 그룹장 여부와 actor membership을 최종 transaction에서 다시 검사한다. 그룹 대표의 현 상태가 나빠졌다는 이유로 이름 수정 등 현재 그룹 권한을 없애지 않는다.

POST/PATCH에는 Idempotency-Key가 필수다. 두 명령의 scope는 각각 actor+group-create, actor+group-rename이며 target/정규화본문을 digest에 포함한다. 생성의 생략 name은 auto marker로 보존해 재전송 시 현재 캐릭터명으로 다시 명령을 만들지 않는다.

## 4. 응답 DTO·필수 nullable

아래 모든 필드는 필수다. `|null`로 적은 필드만 null을 허용한다. 시각은 UTC RFC3339다. 레벨/전투력·원정대 전체 목록·개인설정·키/토큰·연락처는 응답하지 않는다.

| DTO | 필드 |
|---|---|
| CharacterDisplay | server_name:string, character_name:string, class_name:string|null. 저장된 표시 snapshot이며 현재 소유 증거가 아님 |
| GroupRepresentative | display:CharacterDisplay, status:`valid|needs_update`. 공개 응답에는 canonical UUID/앱 회원UUID를 포함하지 않음 |
| GroupSummary | group_id:UUID, name:string, revision:integer>=1, member_count:integer>=1, representative:GroupRepresentative, leader_display:CharacterDisplay|null |
| MyMembership | membership_id:UUID, role:`leader|member`, revision:integer>=1, joined_at:datetime |
| Permission | allowed:bool, reason:string|null. 허용이면null |
| GroupDetail | group:GroupSummary, created_at:datetime, leader_membership_id:UUID, members_revision:integer>=1, my_membership:MyMembership, permissions:{rename:Permission,list_members:Permission} |
| GroupMember | membership_id:UUID, role:`leader|member`, revision:integer>=1, display:CharacterDisplay|null, joined_at:datetime, is_me:bool |
| GroupSummaryPage | items:list[GroupSummary], directory_revision:integer>=1, next_cursor:string|null |
| MyGroupPage | items:list[GroupDetail], directory_revision:integer>=1, next_cursor:string|null |
| GroupMemberPage | group_id:UUID, group_revision:integer>=1, members_revision:integer>=1, items:list[GroupMember], next_cursor:string|null |

공개 정보는 GroupSummary로 고정하고 토큰 유무로 private 필드를 추가하지 않는다. 공개 검색 결과에는 초대코드·멤버목록·권한·내 역할을 넣지 않는다. private 조회는 GroupDetail/GroupMemberPage를 사용한다. 회원 목록에는 다른 회원의 전역 user_id나 원정대 UUID를 노출하지 않고 그룹 범위 membership_id로 구분한다. 생성 시 snapshot만으로 membership 권한을 만들지 않는다.

`permissions.rename`은 현재 그룹장에게만true, 일반 멤버에게false/reason GROUP_LEADER_REQUIRED다. `list_members`는 현재 멤버에게true다. G2/G3 미구현 동작을 allowed로 광고하지 않는다. 현재 G1에서는 생성자1명이지만 이후 멤버/역할 구조와 private 차단을 검증한다.

대표 status/현재 멤버 권한은 조회의 일관된 DB snapshot에서 계산한다. 저장된 이름/직업을 현재 다른 ID에서 가져오지 않는다. 캐릭터 상태만 변해도 대표 status는 달라질 수 있으며 그 자체는 그룹 메타데이터 revision을 올리지 않는다. group_revision을 소유/생명주기 revision의 대체 증거로 사용하지 않는다.

## 5. 예시

생성 요청(샘플 UUID/버전):
```json
{"registration_id":"00000000-0000-4000-8000-000000000001","character_id":"00000000-0000-4000-8000-000000000002","expected_registration_version":1,"expected_ownership_revision":1,"expected_roster_revision":1,"expected_lifecycle_revision":1,"name":"주말 레이드"}
```

생성201/본인상세200/이름수정200의 GroupDetail 예시:
```json
{
  "group": {
    "group_id":"00000000-0000-4000-8000-000000000003",
    "name":"주말 레이드", "revision":1, "member_count":1,
    "representative":{"display":{"server_name":"예시 서버","character_name":"예시 캐릭터","class_name":"예시 직업"},"status":"valid"},
    "leader_display":{"server_name":"예시 서버","character_name":"예시 캐릭터","class_name":"예시 직업"}
  },
  "created_at":"2026-10-17T00:00:00Z",
  "leader_membership_id":"00000000-0000-4000-8000-000000000004",
  "members_revision":1,
  "my_membership":{"membership_id":"00000000-0000-4000-8000-000000000004","role":"leader","revision":1,"joined_at":"2026-10-17T00:00:00Z"},
  "permissions":{"rename":{"allowed":true,"reason":null},"list_members":{"allowed":true,"reason":null}}
}
```
공개200은 위 group 객체만 반환한다. 예시는 가상 자료이며 실제 사용자 정보가 아니다.

이름 수정 입력은 `{"name":"새 그룹명","expected_revision":1,"expected_membership_revision":1}`이다.

## 6. 목록과 revision

- public 검색q는 선택이며 빈 값은 전체다. 그룹명 또는 저장된 그룹전용대표 캐릭터명을 대상으로 trim·대소문자·분리한글 정규화 검색키를 사용한다. 표시원문/UUID는 검색키로 대체하지 않고 원격Flutter 기준과 세부정규화를 대조한다. 부분 일치 검색에서 SQL wildcard `%`/`_`도 문자 그대로 취급한다. 알 수 없는 필터를 거부하며 public 경로에서 private 목록을 선택하지 못한다.
- 모든 목록의limit는 기본20/최대50이다. public/my는created_at 내림차순+group_id 내림차순, members는joined_at 오름차순+membership_id 오름차순이다. next_cursor는 마지막 페이지에서null을 반드시 반환한다.
- 기존 HMAC cursor를 재사용하고 path·public/member scope·actor(회원 전용)·정규화q·limit·revision·offset을 서명한다. 다른 회원/경로/변조cursor는400 INVALID_REQUEST다. 서명이 정상이더라도 목록 변경 후에는409 CURSOR_STALE로 처음부터 다시 조회한다.
- directory_revision은 생성/이름 변경/후속membership·공개표시snapshot 갱신에서 증가하는 공유head다. my 목록도 같은head를 사용하므로 다른 그룹 변경에 따른 보수적인stale을 허용한다. members cursor는group revision+members_revision에 묶는다. cursor가 있어도 현재membership을 검사하므로 권한 상실을 우회하지 못한다.
- 페이지는REPEATABLE READ의 일관된snapshot으로 반환한다. 캐릭터 기반status는 페이지 사이에 바뀔 수 있으므로 전체 목록 조회로 소유 자격이 고정됐다고 보지 않는다. 최종 쓰기는 현재 상태를 검사한다.

## 7. 저장·원자성·재송신

최소 구조안은groups, group_memberships, group_directory_head의3개 테이블이다. 물리DDL/명명은 구현 시 검토한다.

- groups: UUID/name/created_at/revision/members_revision, leader_membership_id, 그룹대표 canonicalUUID·당시member 귀속/표시snapshot. 후속G3의 종료를 구분할 종료시각을 둔다.
- memberships: UUID/group_id/user_id/표시용canonicalUUID와snapshot/joined_at/revision/종료시각. group_id+user_id는unique다. role은leader_membership_id와현재membership으로계산하며별도role열로그룹장기준을이중관리하지않는다.
- groups의leader_membership_id는같은group의membership을참조하는지연검증가능복합FK이며membership은groups를참조한다. 생성transaction에서둘을추가하고commit시동일그룹의leader member존재를보장한다. singleton directory head는migration에서만들고GET은삽입하지않는다.
- 최종쓰기는기존authorize(write=True)의game-mutations lock/actor user/session lock을재사용한다. 네트워크호출없이등록/owner/claim/lifecycle·모든입력revision을검사하고group+membership+directory head+멱등결과를같은transaction에서commit한다.
- 이름수정은현재membership/leader와예상group/member revision을검사하고실제이름변경때만group/directory revision을올린다. trim후동명no-op도권한/CAS를먼저검사하고revision은유지한다. 이름만바뀌면members_revision은유지하며실패는전부rollback한다.
- 같은key/정규화요청은원성공201/200을반환한다. 현재role/permissions와다를수있으므로ACK후현재GET을조회한다. 다른본문/target은409 IDEMPOTENCY_CONFLICT, 진행중은409 REQUEST_IN_PROGRESS/Retry-After2, 만료는409 IDEMPOTENCY_EXPIRED다. 실패는기존lease/generation fencing을따른다.
- 성공replay도현재actor/session·그룹존재/active membership을재검사한다. 과거leader ACK는현재권한이아니다. 캐릭터소유상실만으로그룹membership은없어지지않으므로기존group ACK/조회에새장비인증이나대표소유를요구하지않는다.
- 후속G2/G3도같은group/member/directory revision과transaction경계를쓴다. G1에아직없는pending/party를0건으로가정해해산하는API를만들지않는다.

## 8. 오류와 재시도

기존 `{error:{code,message,request_id}}`, no-store, 401 Bearer를사용한다. 검사를생략해권한을만들지않는다.

| HTTP | code/발생 조건 | 대응 |
|---|---|---|
| 400 | INVALID_REQUEST、GROUP_NAME_REQUIRED、알 수 없는query/잘못된UUID/추가body | 입력 수정 |
| 401 | 기존ACCESS/SESSION 오류 | 기존 세션 복구. 게임키 거부를 로그아웃으로 처리하지 않음 |
| 403 | OWNERSHIP_REQUIRED、GROUP_MEMBERSHIP_REQUIRED、GROUP_LEADER_REQUIRED、기존 회원 비활성 오류 | 현재 권한 확인. 공개 정보의 존재를private 접근 허용으로 해석하지 않음 |
| 404 | REGISTRATION_NOT_FOUND/CHARACTER_NOT_FOUND/GROUP_NOT_FOUND | 현재 자원 조회. foreign 등록/캐릭터는404로 숨김 |
| 409 | CHARACTER_UNUSABLE/IDENTITY_CONFLICT/REVISION_CONFLICT/CURSOR_STALE/기존 멱등code | revision/cursor 충돌은 현재GET/처음부터 재조회 후 새 판단. 응답 불명은 원key/body 복구 우선 |
| 503 | SERVICE_UNAVAILABLE | 같은 명령을backoff 후 재시도. 결과 불명으로 새key를 만들지 않음 |

G1에 외부provider 호출/임의24시간TTL/과거50/50을적용하지않고확정15/5제한거절을안정적인오류로연결한다. 최종오류code는HTTP연결인계에서정리한다. private 자료를 오류 상세로 노출하지 않고 실제 그룹명/snapshot을 로그나 협업 댓글에 출력하지 않는다.

## 9. 구현 구간·확인 사항

G1의DDL/DTO·생성·공개/회원조회·이름수정·권한/cursor/재송신·검증을 하나의 구현 인계 구간으로 묶는다. G2를 생성API의 선행 대기 조건으로 삼지 않는다. 추가DDL은 기존DB내용을 유지하고 자료 이관/초기화/새 환경을 만들지 않는다. rollback은 이전API이미지와 추가자료 보존을 기본으로 하고 데이터가 있는 테이블을 임의drop하지 않는다.

구현 시 격리PostgreSQL 검증:

1. group+creator membership/leader FK 원자 생성·실패rollback·동일key replay/다른 본문 충돌·이름 중복 허용·trim/길이/기본명 경계.
2. 위조actor/외부character/suspect/retired/claim/owner·revision 변경 거부. 저레벨usable 생성과 기존 대표 자동변경 없음.
3. 비member private 조회 거부·membership UUID만으로 열람 불가·다른 회원cursor 거부. 공개 응답에 멤버/코드/개인key·전역user ID가 없음.
4. 이름 변경의 동시CAS/비leader 거부/no-op/replay와snapshot·member count/멤버revision 보존.
5. 그룹 대표가 사용 불가여도snapshot/회원관계·leader권한을 보존하고needs_update 표시. 옛 이름 재사용 시 새character의 표시/권한을 승계하지 않음.
6. 각 목록 순서·cursor stale/변조·GET쓰기0, DDL/model일치·기존API/OpenAPI유지. G2/G3 동시가입/마지막자리/이전/해산은 해당 구현에서 검증하며 G1 결과와 섞지 않음.

공개최소조회/회원전용DTO분리안은소비가능회신을받았고활동선택필수·계정별기본15/5·검색범위를정정했다. 다섯번째회신의모집기본10·계정별유효한도/초과관련전체방제한·회복명령은공통계약을먼저설계한다. 필수policy에이조건을연결한뒤HTTP/목록/cursor/OpenAPI를이어간다. 가입시멤버표시와대표변경권한/대상·G3모집연계는후속범위다. G1에서 종료된 그룹이나 없는 G2/G3 동작 권한을 선제 허용하지 않는다.

내부 선행 구현/검증은 [기초 구현 기록](ISSUE_12_GROUP_G1_FOUNDATION.md)을 따른다. 아직 새HTTP/OpenAPI/서버반영은 없다. Flutter는 명세와 #12 게시내용의 소비 충돌을 회신한다. 기존 로그인/키/장비인증 재시험은 요청하지 않는다. 다음Backend는 G1 구현이며 Flutter 구현/실기기 완료와 별도 단계다.

게시 상태: 명세 전체는 #12 첫 댓글에 게시했다. 내부 선행 구현과 문서를 같은 작업 브랜치로 게시하며 실제SHA/결과댓글은 기초 구현 기록과DEV_LOG에 남긴다. dev/main 통합과 HTTP 실행 반영은 별도다.

최신 확장 입력: [#12 다섯 번째 Flutter 계정별 한도 요청](https://github.com/heo0328/lostparty-backend/issues/12#issuecomment-6232562970). 그룹15/가입5/모집10은기본값이며서버계정별조정·초과시관련전체방제한/정리후회복·타회원진행차단/회복권한표와#11개인완료우회방지를별도계약으로제안해야한다. 결제/광고/자료삭제는범위밖이다. 이문서의HTTP예시는아직그확장응답을반영한실행계약이아니다.

공통계약의현재검토안은 [계정별이용한도/방제한명세](ISSUE_12_MEMBER_LIMITS_CONTRACT_DRAFT.md)와 [#12 일곱번째제안](https://github.com/heo0328/lostparty-backend/issues/12#issuecomment-6232669446)이다. G1본인한도GET·생성expected_limits_revision/expected_usage_revision·상세access/permissions의추가안을포함하며최종HTTP계약은이검토결과와함께정리한다. 현재내부명령/DB/서버는변경하지않았다.


## 최신 정정 — #12 아홉 번째 확정

[#12 아홉 번째 Flutter](https://github.com/heo0328/lostparty-backend/issues/12#issuecomment-6232797572)가 이전의 ‘개인초과→모든 그룹/연결방 제한’ 제안을 대체한다. 개인 레이드 초과는 직접 참가한 공개/그룹 방, 개인 그룹 초과는 직접 참가한 그룹전용 방에만 적용한다. 기존 그룹 운영은 유지한다. 그룹 자체 정원 초과만 그 그룹의 모든 그룹전용 방을 제한한다. 정확히 한도에서는 기존 이용 정상/해당 증가만 차단한다. 세 질문은 해소됐고 추가 사용자 결정 대기는 없다. 상세는 [공통계약4·6절](ISSUE_12_MEMBER_LIMITS_CONTRACT_DRAFT.md)이다. 위 과거 다섯 번째 기준의 광범위 제한 설명은 최신 확정으로 대체된다.

주간 통계는 [별도 설계](../recruitment/contracts/ISSUE_13_WEEKLY_STATISTICS_DRAFT.md)를 따른다. 현재한도/사용량 head를 주간 통계 카운터로 사용하지 않는다.


## G1 최종 HTTP 반영

[개발 안내](ISSUE_12_GROUP_G1_DEVELOPMENT.md)와OpenAPI가최종구현형식이다. 본인한도GET와생성예상limits/usage revision을추가하고회원상세에는capacity를제공한다. 공개요약은유지한다. 과거HTTP미연결/정책미반영설명은당시상태이며최종검증·로컬적용여부는NEXT_WORK/DEV_LOG를따른다. G2/G3·실제방API·통계집계는이번구간에포함하지않는다.
