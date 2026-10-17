# 그룹 G1 HTTP 구현 안내

2026-10-17. 기준: [G1 명세](ISSUE_12_GROUP_G1_SPEC.md), [공통한도](ISSUE_12_MEMBER_LIMITS_CONTRACT_DRAFT.md), [#12 세 번째 정책](https://github.com/heo0328/lostparty-backend/issues/12#issuecomment-6232491349)·[아홉 번째 확정](https://github.com/heo0328/lostparty-backend/issues/12#issuecomment-6232797572). 기존 `feat/raid-services`의 내부기초/L0를 재사용한다. 새 기획결정이 필요한 G1 항목은 없으며 후속 G2/G3를 임의로 구현하지 않는다.

## 경로·기본동작

| Method/path | 접근/결과 |
|---|---|
| GET `/v1/me/usage-limits` | 로그인 본인의 한도·가입그룹 현재사용량/버전·초과원인. GET쓰기0, 모집은null/unavailable |
| POST `/v1/groups` | 로그인·현재 인증소유/usable/현재활동캐릭터·revision·가입한도/그룹정원 검사,201 회원상세 |
| GET `/v1/groups` | 무인증 공개검색, q/limit/cursor, 최소요약목록 |
| GET `/v1/groups/{group_id}` | 무인증 최소요약, Bearer 유무로 private필드가 늘지 않음 |
| GET `/v1/me/groups` | 로그인 본인의 현재 membership만, 회원상세목록 |
| GET `/v1/me/groups/{group_id}` | 로그인·현재멤버의 상세 |
| GET `/v1/groups/{group_id}/members` | 로그인·현재멤버만, 그룹범위 membership UUID/표시/역할/is_me |
| PATCH `/v1/groups/{group_id}` | 로그인·현재그룹장, 이름만 변경 |

모든 경로 no-store, GET body/미지원query/중복scalar query는400. 조회시 provider/개인키/DB쓰기는없다. 목록limit기본20/최대50, cursor최대2048자·빈값거부. q최대64자·생략/trim후빈문자열은전체다. 이름수정/생성은UUIDv4 Idempotency-Key 필수다.

## 요청·응답 계약 차이

- 생성은 기존 registration/character UUID와 expected_registration_version/ownership_revision/roster_revision/lifecycle_revision에 **expected_limits_revision/expected_usage_revision**을 추가한다. 한도GET의현재값을사용한다. 모두strict integer>=1. 추가필드/가짜actor·권한·snapshot은거부한다.
- name생략은기존선택캐릭터명+‘의 그룹’, null/빈값/원문제어문자·줄바꿈은400이다. trim후1~20code point, 기본명이길면자르지않고GROUP_NAME_REQUIRED다. 표시원문은NFC검색키로재작성하지않는다.
- GroupDetail은최초안의group/created_at/leader_membership_id/members_revision/my_membership/permissions와 **capacity:{limit,used,remaining,state}**를반환한다. state=within/at_limit/exceeded, limit은현재그룹장의계정정원이다. 원인회원의개인한도/운영메모를공개하지않는다. capacity는G2가입권한이나방진행허가가아닌현재정원안내다. 권한은이번에구현한rename/list_members만제공한다.
- 공개GroupSummary는최초합의DTO를유지하며capacity·회원UUID/명단·권한·초대코드·캐릭터canonicalUUID는노출하지않는다. 회원상세의capacity는비회원에게보이지않는다.
- 현재대표의소유/claim/생명주기가무효면needs_update이지만membership/그룹장권한은유지한다. 사용자대표/활동선택변경도기존그룹대표snapshot을자동동기화/삭제하지않는다.
- limit/usage예상revision불일치는409 POLICY_CONTEXT_CHANGED. 현재활동미포함은409 ACTIVITY_SELECTION_REQUIRED. 현재가입수>=개인한도는409 GROUP_MEMBERSHIP_LIMIT_REACHED, 생성자인원1을정원이수용못하면409 GROUP_CAPACITY_REACHED다. 나머지는기존소유/lifecycle/revision/멱등성오류를재사용한다. 그룹생성에레이드한도·1700/입장레벨·개인체크·기기표시수조건은추가하지않는다.

생성 예시(가상UUID/버전):
```json
{"registration_id":"00000000-0000-4000-8000-000000000001","character_id":"00000000-0000-4000-8000-000000000002","expected_registration_version":1,"expected_ownership_revision":1,"expected_roster_revision":1,"expected_lifecycle_revision":1,"expected_limits_revision":1,"expected_usage_revision":1,"name":"주말 레이드"}
```
이름수정은 `{"name":"새 그룹명","expected_revision":1,"expected_membership_revision":1}`이다. 상세capacity예시는 `{"limit":15,"used":1,"remaining":14,"state":"within"}`이다. 본인한도 응답의전체형식은공통계약3절/OpenAPI를따른다.

## 검색·페이지·원자성

공개검색은저장그룹명또는저장그룹대표캐릭터명부분일치다. 원격Flutter `5eef0d2`의 `lib/features/group/domain/services/group_name_normalizer.dart`를직접조회해한글조합/trim/lower를대조했다. 검색만Python/PG NFC·lower로처리하며라틴등다른정준분리도합성한다. SQLcontains는%,_,escape문자를리터럴로escape하고입력은바인딩한다. 신원/표시를검색키로대체하지않는다.

public/my정렬은created_at내림차순+UUID내림차순, 멤버는joined_at+membershipUUID오름차순이다. SQL limit+1/offset으로페이지를구하고HMACcursor는경로·actor(회원전용)·정규화q·limit·목록revision·offset에묶인다. 다른경로/actor/q/limit/변조는400, 현재revision변경은409 CURSOR_STALE다. 마지막next_cursor는null. GET은RRsnapshot이며현재membership검사를cursor보다먼저한다.

생성은기존내부core에최종HTTPpolicy/응답projection을주입한다. 필수내부정책hook을무제한으로바꾸지않는다. 활동/소유/CAS·한도/현재가입수는전역변경락아래같은transaction에서검사하고group+membership+usage head+directory head+멱등성공을원자commit한다. 실패는전체rollback한다. 기존내부scope와HTTP의group-create/group-rename은분리했다. success ACK는원래snapshot이고현재권한이아니다. replay는현재session·그룹·membership을확인하되현재소유/활동/정원으로이미성공한명령을재실행하지않는다. 이름no-op도현재권한/CAS를검사하고head를늘리지않는다.

## 운영 경계·다음 담당

개발DB에필요한추가는기존0012(그룹3테이블/directory기본행)·0013(한도3테이블)뿐이며기존업무자료복사/삭제/이관은없다. 적용·검증·SHA/push·실제HTTP와미확인항목은DEV_LOG/NEXT_WORK및최종Issue인계에기록한다. 새테이블이생겼다는이유로기본앱/로그인/장비인증을처음부터반복하지않는다.

G2초대/가입/신청/코드·G3탈퇴/추방/이전/해산·실제#13방진행제한은미구현이다. 현재capacity/본인한도조회가실제모집API완료는아니다. 주간통계는별도제안이며G1의불변created_at/joined_at/UUID는보존하고현재통계값으로조작하지않는다. 실제재가입/종료이력은G2/G3명령구현때덮어쓰기없이연결한다.


## 이번 검증·로컬 반영

관련격리검증164PASS/56.09초, 이름생략/null의OpenAPI표현을맞춘최종이미지에서G1 HTTP·기초·모델일치59PASS/13.87초다. 두검증범위는중복이며합산해고유223개라고보고하지않는다. 기존Starlette/AnyIO경고1개만있다. 최초161PASS/2FAIL은테스트가인증오류를ACCESS_INVALID대신다른이름으로기대한문제와검색문자fixture가canonical/NameClaim FK를위반한문제였다. fixture는기존이름을수정하지않고새canonical/claim/Activity로구성했고최종통과했다.

실제로기존로컬DB에0012/0013추가적용·API이미지를반영했다. 기존회원/원정대/등록/캐릭터/설정/활동/주간행수보존과새그룹/회원/한도/head/감사0행·directory1행을확인했다. 실행OpenAPI전체일치와실제HTTP의공개목록/검색200·잘못된limit400·없는그룹404·회원4GET/POST/PATCH의401/Bearer/no-store·기존health/catalog/cycle200을확인했다. 개발실제회원으로생성/이름쓰기·Flutter연결/실기기는미확인이며자동HTTP/모의로그인테스트와구분한다. 테스트DB만중지했고기존개발자료/키/flag를유지했다.
