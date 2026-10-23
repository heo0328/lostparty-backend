# 그룹 G3 API 명세

2026-10-19 / Backend / `feat/group-management`.

관리 GET·그룹장 이전·일반 탈퇴의 구현 계약이다. 기존 [#16 전체1번째 제안](https://github.com/heo0328/lostparty-backend/issues/16#issuecomment-6250563064)을 구현했으며 Flutter 소비 수용/연결 완료와 구분한다. 원본 #12는 Backend의 경로/DTO 설계·독립 서버 구현을 요청했고 사용자가 G3 착수/계속 진행을 승인했다. 소비 충돌 확인을 전체 구현의 선행조건으로 둔 이전 작업 기록은 정정한다. 새 제품 기능을 추가하거나 Flutter 수용을 추정한 것이 아니다. 구현·검증·게시 상태는 [개발 안내](ISSUE_16_GROUP_G3_DEVELOPMENT.md)를 따른다.

## 1. 범위와 확정 제품 규칙

그룹장 즉시 이전과 일반 멤버 본인 탈퇴가 이번 구현 대상이다. 이전 상대의 수락·대기·쿨다운은 없으며 이전자는 일반 멤버로 남는다. 탈퇴는 별도 명령이다. 그룹장인 채로 일반 탈퇴할 수 없다.

그룹 대표 canonical UUID·귀속 회원·표시 snapshot은 이전만으로 변경하지 않는다. 기존 소유/생명주기/현재 membership 검사로 대표 `valid|needs_update`를 계산한다. 이전자 탈퇴로 대표가 무효가 되더라도 권한/그룹을 삭제하거나 새 그룹장 캐릭터로 자동 교체하지 않는다.

현재 회원/그룹 membership 권한과 예전 캐릭터 자격을 구분한다. 현재 소유 상실·활동 해제·낮은 레벨을 이유로 기존 멤버의 이전/본인 탈퇴를 막지 않는다. 새 소유 인증이나 게임 API 호출은 없다.

**새 그룹장의 유효 `group_capacity`가 현재 확정 인원 이상이어야 이전할 수 있다.** 같으면 허용, 작으면 `GROUP_CAPACITY_REACHED`로 전부 거절한다. 기존 한도 계약 6절의 조건이며 ‘이전 후 초과를 그대로 허용’하는 정책을 새로 만들지 않는다. 개인 가입/모집 초과만으로 회복 명령을 막지 않으며 이전은 가입 수를 늘리지 않는다. 다른 제한 원인이 남으면 실제 방 제한은 그대로다.

조건부 해산은 본인1인·pending 없음·실제 활성 그룹전용 모집 없음의 권위 검사가 필요하다. 현재 실제 모집 원본이 없어 **이번에 해산 쓰기 API를 제공하지 않는다.** GET은 미지원 사유를 표시한다. #13 원본이 준비되면 같은 #16의 남은 해산 계약을 연결한다. 추방/대표 변경의 구체 정책·쓰기는 별도 확인 구간이며 이번 구현에 임의 포함하지 않는다.

## 2. 경로·입력 규칙

| Method/path | 권한·입력 | 응답 |
|---|---|---|
| GET `/v1/groups/{group_id}/management` | 로그인·현재 멤버. query/body 없음 | 200 `GroupManagement` |
| POST `/v1/groups/{group_id}/leadership-transfer` | 로그인·현재 그룹장, `TransferLeadershipIn` | 200 `LeadershipTransferAck` |
| POST `/v1/groups/{group_id}/leave` | 로그인·현재 일반 멤버, `LeaveGroupIn` | 200 `GroupLeaveAck` |

모든 응답 `Cache-Control: no-store`다. actor는 세션에서 결정한다. 회원 전역 UUID/role/표시 snapshot/캐릭터 소유 증거를 입력받지 않는다. 추가 body 필드·미지원 query·중복 query·GET body는400이다. UUID는 UUID형 문자열, revision은 bool/소수/문자열을 받지 않는 정수>=1이다. 입력 nullable/생략 기본값은 없고 모두 필수다. POST의 `Idempotency-Key`는 기존 UUIDv4 규칙을 따른다.

신규 GET으로 G3 관리 정보를 분리하여 기존 `GroupDetail`, `GroupMemberPage`, G1/G2 경로/DTO를 그대로 유지한다. 현재 멤버 목록에서 대상 membership ID/revision을 읽는다. 관리 GET과 목록 사이 상태가 바뀌면 쓰기에서 CAS 충돌로 거부한다.

## 3. 요청 DTO

`LeaveGroupIn`:

- `expected_group_revision`
- `expected_members_revision`
- `expected_membership_id: UUID` — 행위자 본인의 현재 가입 관계. 탈퇴·재가입으로 관계가 교체되는 경우를 구분한다.
- `expected_membership_revision`

`TransferLeadershipIn`: 위 네 필드와 `target_membership_id: UUID`, `expected_target_membership_revision`.

서버는 현재 group/actor membership·그룹장 역할을 먼저 확인하고 예상값을 검사한다. actor membership ID가 바뀌면 revision 숫자가 같아도 `REVISION_CONFLICT`다. 대상은 같은 그룹의 종료되지 않은 membership이며 소속 회원도 현재 활성 상태여야 한다. 자기 자신을 대상으로 한 명령은 `GROUP_TRANSFER_TARGET_INVALID`, 타 그룹/없는/종료/비활성 대상은 `GROUP_TARGET_UNAVAILABLE`이다. 상대의 수락 여부나 현재 캐릭터 활동을 검사하지 않는다. 대상의 최신 유효 정원과 현재 인원은 같은 쓰기 transaction에서 재검사하며 타인의 한도 원문을 응답하지 않는다.

가상 입력 예시:

```json
{
  "expected_group_revision":4,
  "expected_members_revision":3,
  "expected_membership_id":"00000000-0000-4000-8000-000000000002",
  "expected_membership_revision":1,
  "target_membership_id":"00000000-0000-4000-8000-000000000003",
  "expected_target_membership_revision":1
}
```

일반 탈퇴는 위에서 target 두 필드를 제외한다. 이전 후 탈퇴는 이전 ACK만으로 같은 버전을 재사용하지 말고 현재 관리 GET을 조회해 새 명령을 만든다.

## 4. 응답 DTO·허용 동작

모든 필드는 필수다. 아래 `reason`만 nullable이다. UTC RFC3339 시각을 사용하며 시각/버전을 클라이언트가 계산하지 않는다.

`GroupManagement`:

- `group_id: UUID`, `group_revision: int>=1`, `members_revision: int>=1`
- `my_membership`: 기존 G1 `MyMembership` (`membership_id`, `role: leader|member`, `revision`, `joined_at`)
- `permissions`: `transfer_leadership`, `leave`, `disband`, 각각 기존 `Permission` (`allowed: bool`, `reason: string|null`)

그룹장: transfer=true/null, leave=false/`GROUP_LEADER_TRANSFER_REQUIRED`. 일반 멤버: transfer=false/`GROUP_LEADER_REQUIRED`, leave=true/null. disband는 그룹장도 false/`GROUP_RECRUITMENT_STATE_UNAVAILABLE`, 일반 멤버는 false/`GROUP_LEADER_REQUIRED`다. 해산의 모든 사전 조건을 통과했다는 뜻은 아니다. transfer=true는 명령을 시도할 역할 안내이며 최종 대상·revision·정원 검사를 대체하지 않는다. disband에 대응하는 쓰기 경로는 이번에 없다.

일반 멤버의 관리 GET 예시:

```json
{
  "group_id":"00000000-0000-4000-8000-000000000001",
  "group_revision":5,
  "members_revision":4,
  "my_membership":{
    "membership_id":"00000000-0000-4000-8000-000000000002",
    "role":"member",
    "revision":2,
    "joined_at":"2026-10-17T00:00:00Z"
  },
  "permissions":{
    "transfer_leadership":{"allowed":false,"reason":"GROUP_LEADER_REQUIRED"},
    "leave":{"allowed":true,"reason":null},
    "disband":{"allowed":false,"reason":"GROUP_LEADER_REQUIRED"}
  }
}
```

관리 GET은 DB의 일관된 읽기 snapshot만 사용하고 head/행을 생성하지 않는다. 목록·코드·신청/차단 명단/타인 전역 회원ID·개인자료는 포함하지 않는다.

`LeadershipTransferAck`:

- `group_id: UUID`
- `previous_leader_membership_id: UUID`, `leader_membership_id: UUID`
- `group_revision`, `members_revision`: 성공 직후 버전
- `previous_leader_membership_revision`, `leader_membership_revision`: 두 membership의 성공 직후 버전
- `transferred_at: UTC datetime`

```json
{
  "group_id":"00000000-0000-4000-8000-000000000001",
  "previous_leader_membership_id":"00000000-0000-4000-8000-000000000002",
  "leader_membership_id":"00000000-0000-4000-8000-000000000003",
  "group_revision":5,
  "members_revision":4,
  "previous_leader_membership_revision":2,
  "leader_membership_revision":2,
  "transferred_at":"2026-10-18T03:00:00Z"
}
```

`GroupLeaveAck`: `group_id: UUID`, `membership_id: UUID`, `membership_revision: int>=1`, `ended_at: UTC datetime`.현재 그룹 상세/멤버 수/타인의 현재 권한은 넣지 않는다.

```json
{
  "group_id":"00000000-0000-4000-8000-000000000001",
  "membership_id":"00000000-0000-4000-8000-000000000002",
  "membership_revision":3,
  "ended_at":"2026-10-18T03:01:00Z"
}
```

ACK는 해당 명령의 과거 성공 확인이다. 현재 그룹장·현재 가입·현재 정원 증거가 아니다. 이전 후 관리 GET/본인 상세·멤버 목록을, 탈퇴 후 내 그룹/본인 한도를 다시 조회한다. 탈퇴 후 private 조회403은 종료된 권한의 정상 결과일 수 있다.

## 5. 원자성·revision·G2 연결

기존 `authorize(write=True)`의 `game-mutations-v1` 락과 회원/세션 락을 재사용한다. 대상 회원 상태 변경과 충돌하지 않도록 대상 User를 최종 쓰기에서 잠그고 재검사한다. 외부 호출 없이 권한/CAS·현재 상태를 검사하고 성공 ACK까지 하나의 transaction에서 commit한다.

| 변경 | group revision | members revision | membership revision | directory/usage |
|---|---:|---:|---|---|
| 이전 | +1 | +1 | 이전자·대상 각각+1 | directory+1, 가입 수/usage head 변화 없음 |
| 일반 탈퇴 | +1 | +1 | 본인+1, ended_at 기록 | directory+1, 본인 usage head+1 |

이전은 `leader_membership_id`만을 그룹장 권위로 유지한다. 대표/가입·표시 snapshot/가입 시각/인원은 그대로다. 기존 초대/신청·코드도 유지하며 관리 권한은 즉시 새 그룹장으로 바뀐다. 코드 재생성 쿨타임을 초기화하지 않는다. 이전자는 현재 일반 멤버의 권한만 가진다.

탈퇴는 membership을 물리 삭제하지 않는다. 본인이 발신한 아직 DB에 pending으로 남은 초대를 같은 transaction에서 종료한다. 이미 만료된 초대는 expired/실제 expires_at, 유효 pending은 cancelled/탈퇴 시각으로 기록하고 relation revision을 증가시킨다. 다른 발신자의 초대·신청·차단/누적 기록·기존 코드는 보존한다. 차단을 자동 설정하거나 이전 관계를 부활시키지 않는다. 새 가입은 G2를 거쳐 새 membership UUID로 생성한다.

공개/내 그룹 directory cursor와 멤버 cursor는 변경 revision으로 무효화된다. G2 목록은 현재 권한/관계 revision·논리 상태로 재평가하며 발신자 종료를 우회하지 못한다. 이전·탈퇴와 G2 수락/승인·동시 이전·한도 변경은 같은 권위 경계에서 직렬화한다. 성공 ACK 저장 실패나 최종 검증 실패면 관계/revision/head/초대 종료까지 모두 rollback한다.

현재 실제 방 원본은 미구현이다. 위 명령이 방 퇴장·슬롯 해제·주간 완료·방 공개전환을 함께 수행한다고 주장하지 않는다. #13의 실제 그룹전용 방 도입 시 그룹 membership 종료와 방 접근/잔류의 계약을 명시해 연결해야 한다. 이번에는 방 권한을 캐릭터 자격에서 새로 추정하지 않는다.

## 6. 멱등·응답 유실·권한 경계

operation scope는 actor+`group-leadership-transfer` 또는 actor+`group-leave`다. digest에는 group target과 모든 요청 필드를 포함한다. 같은 키/본문은 원성공200 ACK를 복구하고 다른 target/본문은409 `IDEMPOTENCY_CONFLICT`다. 기존 성공 후24시간 만료/30초 lease·generation fencing/진행중409 `REQUEST_IN_PROGRESS`와 Retry-After2를 재사용한다. 만료 후에는409 `IDEMPOTENCY_EXPIRED`이며 새 키로 무조건 같은 동작을 반복하지 말고 현재 상태를 조회한다.

두 명령 모두 **최소 ACK**만 저장한다. replay는 현재 세션·회원의 정상 상태와 원명령의 actor/operation/digest, 원 membership의 group/user 귀속 및 ACK 연결을 검증한다. 현재 그룹장/현재 membership 존재를 원성공 복구의 전제에 넣지 않는다. 원래 행위자가 이후 탈퇴했거나 그룹이 종료돼도 허용된24시간 안에서는 원 ACK만 반환할 수 있다. 본인 성공 기록 외 private 현재자료는 조회·노출하지 않는다.

따라서 탈퇴 후 응답 유실을 복구할 수 있으며, 재가입 후 과거 탈퇴의 같은 키/본문을 재전송해도 **과거 종료 ACK만 반환하고 새 membership은 건드리지 않는다.** 이전 ACK 재전송도 현재 그룹장을 다시 바꾸거나 이전 권한을 되살리지 않는다. 새 키의 신규 명령은 현재 membership/역할·모든 CAS를 처음부터 검사한다. replay 때문에 revision/usage/관계 종료를 다시 증가시키지 않는다.

## 7. 오류·클라이언트 처리

기존 `{error:{code,message,request_id}}`와 no-store·401 Bearer를 사용한다. 아래 code를 이번 구현에 사용한다.

| HTTP | code | 처리 |
|---|---|---|
| 400 | INVALID_REQUEST | 입력/헤더/query 수정 |
| 401 | 기존 세션/인증 오류 | 기존 세션 복구 |
| 403 | GROUP_MEMBERSHIP_REQUIRED / GROUP_LEADER_REQUIRED | 현재 관계/역할 조회; 과거 ACK로 권한 생성 금지 |
| 404 | GROUP_NOT_FOUND | 현재 자원 확인; 종료 그룹은 신규 명령 불가 |
| 409 | GROUP_LEADER_TRANSFER_REQUIRED | 일반 탈퇴 전 이전 필요. 1인 해산은 현재 미지원 안내 |
| 409 | GROUP_TRANSFER_TARGET_INVALID / GROUP_TARGET_UNAVAILABLE | 자기 자신/유효하지 않은 대상. 현재 멤버 목록에서 다시 선택 |
| 409 | GROUP_CAPACITY_REACHED | 새 그룹장 정원이 현재 인원보다 작음. 대상 변경 또는 먼저 인원 정리 |
| 409 | REVISION_CONFLICT / CURSOR_STALE | 최신 관리/멤버 GET 또는 첫 페이지부터 재조회 후 새 판단 |
| 409 | 기존 IDEMPOTENCY_CONFLICT / REQUEST_IN_PROGRESS / IDEMPOTENCY_EXPIRED | 원 키/본문 보존·기존 복구 규칙 |
| 503 | SERVICE_UNAVAILABLE | 결과 불명이면 원 키/본문으로 backoff 재시도 |

`GROUP_RECRUITMENT_STATE_UNAVAILABLE`은 현재 관리 GET의 disband 불가 reason이다. 이번에 존재하지 않는 해산 POST의 서버 오류를 구현했다고 안내하지 않는다. 실제 모집 원본 부재를 정상0건으로 표시하지 않는다.

## 8. 구현·검증 인계와 후속

관리 GET과 이전/탈퇴 POST를 라우터·OpenAPI에 반영했다. 기존 G1/G2 경로/DTO는 그대로 유지한다. 요청 경로/입력은 Backend의 기존 요청 범위 설계이며 소비 회신이 없어 서버 작업 전체를 대기하지 않는다. Flutter는 해당 그룹 연결 구간에서 신규 관리 정보/최소 ACK·현재 GET·같은 key/body 복구를 소비하고 실제 충돌이 있으면 #16에 회신한다. 기존 로그인·키·장비 인증을 반복 시험할 필요는 없다.

구현·격리 DB/HTTP·실행 계약 검증과 미확인은 [개발 안내](ISSUE_16_GROUP_G3_DEVELOPMENT.md)에 기록한다. 조건부 해산/추방/대표 변경은 이번에 쓰기 경로를 제공하지 않으며 실제 모집 원본 없는 해산을 허용하지 않는다.
