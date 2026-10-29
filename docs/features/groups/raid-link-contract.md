# 모집 그룹 최초 연결·목록 표시 계약

2026-10-30 / feat/group-management / 구현·격리검증·고정계약게시 후 사용자별도지시로개발서버 source2602e45/이미지5bd8dde6·DB0034 반영·실행검증까지완료했다. DBmigration·자료변경/삭제·병합/운영배포는없으며새Flutter연결/기기인수는별도다. [#16 전체22 Flutter 실행계획](https://github.com/heo0328/lostparty-backend/issues/16#issuecomment-6502336731), [#12 전체35 그룹명](https://github.com/heo0328/lostparty-backend/issues/12#issuecomment-6501551683)·[전체36 소속표시](https://github.com/heo0328/lostparty-backend/issues/12#issuecomment-6502226347)가 기준이다.

## 생성과 최초 연결

생성은 기존 context와 생성 POST 한 번의 원자 쓰기를 유지한다. Flutter는 그룹 선택 시 scope=group을 기본으로 채우며 명시 public도 기존처럼 가능하다. 방 복제·생성 후 자동 추가연결 명령·새 원장은 없다.

그룹 없이 만든 방의 최초 연결은 다음 두 단계다.

1. `GET /v2/me/raid-rooms/{room_id}/common-context?command=edit_common_settings&target_group_id={group_id}`로 검토한다. 해당 명령·미연결 방에서만 target query를 허용한다. 현재 공통권한 G1(C가 있으면 C, 없을 때만 N)과 기존 C/N 영향·참가근거를 보존한다.
2. 반환한 토큰과 기존 PUT `/v2/raid-rooms/{room_id}/common-settings` body를 한 번 전송한다. group_id=선택그룹, expected_group_revision=target_group.group_revision, scope=group을 넣는다. 다른 그룹/공개scope로 검토내용을 바꿀 수 없다.

선택 query가 없으면 기존 CommonContext DTO다. 선택한 경우 같은 scope/data와 다음 root.target_group을 갖는 닫힌 GroupConnectionContext DTO를 반환한다. 아래 식별자는 합성 예시다.

```json
{
  "target_group": {
    "group_id": "00000000-0000-4000-8000-000000000001",
    "group_revision": 3,
    "members_revision": 5,
    "membership_id": "00000000-0000-4000-8000-000000000002",
    "membership_revision": 2,
    "permission": {"allowed": true, "reason": null, "next_change_at": null}
  }
}
```

토큰은 actor/방/명령/유효기간·방 revision/현재 C/N 근거에 더해 대상그룹·현재 actor membership·그룹장 membership·유효한도/그룹인원 근거를 결합한다. 현재 활성그룹/회원 소속·그룹정원초과·가입한도초과를 검사한다. 전송 시 같은 game-mutations 잠금 아래 최신 CAS/권한을 재검사하며 ACK 저장 후 최종시각/대상근거를 재검사하고 실패는 전체 rollback한다. 그룹탈퇴/해산/이전·한도변경 등은 이전검토를 재사용하지 못하게 한다. 새필수 body 필드·원ACK 형식 변경은 없다.

- 원래 미연결→선택그룹과 scope=group을 같은 트랜잭션에서 변경한다. 기존 토큰만으로 새그룹을 덧붙일 수 없다.
- 연결된 A→B/해제는 GROUP_LINK_IMMUTABLE이다. 같은 A의 public↔group·제목변경은 유지하고 group 진입 시 현재그룹 자격/한도를 검사한다.
- C/N 실제영향 directory·room revision·기존 활동trigger·원ACK를 원자 확정한다. 그룹역할은 공대장 권한을 만들지 않는다.
- 기존 membership·신청·배정·일정·예약·완료기록을 재생성/취소/추방하지 않는다. pending은 보존하고 이후 신규참가/승인에는 현재자격을 적용한다.
- 원ACK 재조회는 과거성공 응답만 복구한다. 현재권한·재가입 관계에 과거명령을 재실행하지 않는다.

대표 오류는 기존 TARGET_SCOPE_MISMATCH400·TARGET_CONTEXT_STALE409·REVISION_CONFLICT409·COMMAND_CONTEXT_EXPIRED409·COMMON_LEADER_REQUIRED403·GROUP_MEMBERSHIP_REQUIRED403·GROUP_NOT_ACTIVE409·GROUP_CAPACITY_EXCEEDED409·MEMBER_GROUP_LIMIT_EXCEEDED409다. 대상 query를 다른 command에 쓰면 INVALID_REQUEST400이다. 기본/최초연결의 자세한 형태는 고정 [two-cycle OpenAPI](../../../openapi/two-cycle.openapi.yaml)를 따른다.

## 목록의 그룹명·현재 연결

아래 기존 경로에 query `include_group_state=true`를 명시한다. POST도 query이며 body/원요청 계약은 바꾸지 않는다. contract_profile 및 기존 reader_profile과 함께 사용할 수 있다.

- POST `/v2/raid-rooms/search`
- GET `/v2/raid-rooms`
- GET `/v2/me/raid-room-memberships`(기본·membership-actions-1)
- GET `/v2/me/raid-room-applications`

생략/false는 기존 DTO·cursor 의미를 유지한다. true일 때 기존 scope/data에 아래 root.group_states와 root.room_groups를 추가한 닫힌 DTO다.

```json
{
  "group_states": [
    {"group_id": "00000000-0000-4000-8000-000000000001", "name": "표시 그룹", "state": "active"}
  ],
  "room_groups": [
    {"room_id": "00000000-0000-4000-8000-000000000003", "group_id": "00000000-0000-4000-8000-000000000001"},
    {"room_id": "00000000-0000-4000-8000-000000000004", "group_id": null}
  ]
}
```

room_groups는 해당 페이지에 실제 반환한 방만 중복제거한 현재연결 대응표다. 일반 카드에는 group_id가 있으나 내신청 admission_origin은 신청당시 근거이고 일부 참가이력 content에는 현재연결이 없으므로 이 대응표도 함께 제공한다. 기존 origin/이력자료를 현재값으로 덮어쓰지 않는다. 표시할 방이 없으면 두 배열 모두 비어 있다.

group_states는 페이지의 현재연결 그룹만 일괄조회한 표시자료다. active/ended/unavailable은 기존 상세 group_state와 같다. 종료그룹의 보존이름은 표시하며 확인불가는 name=null/state=unavailable이다. DB실패는503이고 이름/UUID를 임의 생성하지 않는다. 소속밖 공개방에서도 같은 표시값이며 그룹원장/명령권한을 부여하지 않는다.

동일 읽기 스냅샷 안에서 반환방을 고른 뒤 두 일괄쿼리로 연결/그룹을 읽는다. 별도카드조회·provider·쓰기·새캐시/원장없음. 신규옵션은 DB0034를 요구한다. cursor는 옵션·원래권한/대상범위·그룹directory revision·실제T directory revision에 결합한다. 이름/종료/연결변경은 CURSOR_STALE로 회복하며 scope위조는 기존 INVALID_REQUEST다. 다른그룹의directory변경도 보수적으로cursor를무효화할수있다.

## 상세 참가자 소속 표시

group_member는 조회자의소속이아닌 각 대상참가자의현재membership으로계산한다. 기본상세와application-display-1은 `data.members[].group_member`, membership-actions-1은 현재읽기에서 `data.content.data.members[].group_member`다. include_group_state=true는그위치/의미를바꾸지않고별도root.group_state를추가한다.

종료/퇴장 등 역사읽기의 content=null은현재참가자목록이없다는뜻이다. 누락/null을 false로합성하지않는다. 방에그룹연결이없으면UI는소속배지를표시할기준이없다. 연결그룹이있을때는상세권한을가진비그룹원도같은대상참가자의현재소속을볼수있다. 그룹탈퇴/추방/종료는현재배지가false이며그자체로기존레이드접근을끝내지않는다. DB조회실패는false대신503이다. 타회원그룹원장/소속리스트를공개하지않는다.

합성격리시험의 동일참가자·조회자/프로필별 정규화예시는 [계약 예시](raid-link-examples.json)의 badge_observations를 따른다. 완전한응답이아닌표시필드/위치조각이며 실제회원자료는아니다.

## 재조회·상태 경계

최초연결성공후방상세/공통context·C/N모집목록·그룹필터context·그룹방/관리조회는갱신한다. 독립초안/선택주차/미확정다른명령은유지한다. 최초연결은그룹membership자체를바꾸지않으므로membership기반filter context가같은값으로재발급될수있다. 방목록cursor는실제T directory로무효화하고그룹방목록/해산판정은새연결의원본을다시평가한다. 명령성공·후속조회실패와원ACK복구·현재조회는분리한다. 합의된기존그룹기기인수는재시험대기로되돌리지않고새최초연결/표시/배지변경경계만확인한다.

DBnullable FK/scope와기존0034활동trigger를재사용하므로migration없다. 실제구현/검증·고정SHA·게시·개발미반영/Flutter다음담당은 [구현 기록](implementation-2026-10-28.md)과 [NEXT_WORK](../../project/NEXT_WORK.md)에누적한다.
