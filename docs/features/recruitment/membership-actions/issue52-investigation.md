# Issue52 — 기록 표시 범위와 생성 상세 403 조사

2026-11-13. 목적 브랜치 `fix/recruitment-history-response`, 기준 dev `0911383e`.
[Issue52](https://github.com/heo0328/lostparty-backend/issues/52) · [Native 조사](https://github.com/heo0328/lostparty-backend/issues/52#issuecomment-6845321873).

## 결정 근거와 수정 책임

기록 화면은 선택한 실제 주차의 자료만 표시한다. 공용 목록의 의미는 유지한다.
[기존 확정 계약 §3](../../../archive/work-records/features/recruitment/contracts/ISSUE_25_CONTRACT_REVIEW_V2.md#3-reader-호환--명시-opt-in-프로필)의 명시 내용은 다음과 같다.

- `current/ended/all` SQL 선별의 기존 의미를 유지한다.
- Member가 ended이고 선택 T의 실제 CM이 없으면 `relation_only`, `record_locator=null`이며 가짜 상세 기록 링크를 만들지 않는다.
- 실제 RoomCycle이 없는 경우 주차 정책을 만들지 않는다. `group_list_display.attach`는 해당 행을 건너뛴다.

따라서 Backend에서 RoomCycle 없는 행을 SQL 선별에서 삭제하면 관계 복구 소비 계약이 바뀐다. 별도 API나 가짜 주차 정책을 추가하지 않는다. Native 기록 화면에서 `target.room_cycle_id=null` 행을 표시 대상에서 제외하고, 이 행에만 정책이 없는 것을 허용하는 소비 계약을 협의한다. 실제 주차 행은 기존대로 정책이 정확히 하나여야 하며 누락·중복을 계속 거절한다. `relation_only` 모드 전체를 무조건 제외하는 조건으로 넓히지 않는다.

표시 행이 없어도 `next_cursor`가 있으면 같은 조건으로 다음 페이지를 읽는다. 목록 전체가 끝났을 때 빈 결과를 표시한다. 페이지 사이 조건 변경·cursor 만료/세대 변경의 기존 재시작 처리를 보존한다. 기록 진입에는 기존 membership/CM anchor를 사용한다. 공용 reader나 현재 참가·관계 복구 메뉴에 기록 화면용 필터를 전역 적용하지 않는다.

## 실제 요청과 합성 검증

`GET /v2/me/raid-room-memberships`에 실제 선택 T, `state=ended`, `limit=20` 및 다음 query를 사용한다.

```
reader_profile=membership-actions-1
contract_profile=beta-recruitment-1
group_policy_version=cycle-group-policy-1
participation_profile=remaining-active-1
include_group_state=true
include_character_issues=true
```

`test_cycle_group_policy.py`에 실제 생성·해산 명령과 최신 임시 DB를 사용하는 회귀 사례를 추가했다. 선택 T 자료 있음/없음이 섞인 목록(limit=1), 전부 없음, 빈 목록을 대조한다. 첫 페이지가 관계만 담아 화면에는 빈 상태여도 cursor 뒤에는 실제 기록과 정책이 존재하는 사례를 검사한다. 같은 관계들의 현재 주차 자료도 대조한다. 기존 membership 시험의 탈퇴/해산/완료/재참가·옛 CM anchor와 생성 원 ACK 시험을 함께 실행한다. 실행 결과는 아래에 기록한다.

의미를 설명하는 비식별 발췌이며 완전한 응답 fixture가 아니다.

```json
{
  "data": {
    "items": [{
      "target": {"room_cycle_id": null, "target_generation": null},
      "viewer": {"mode": "relation_only", "record_locator": null},
      "content": null
    }],
    "next_cursor": "다음 페이지가 있으면 서버 cursor"
  },
  "cycle_groups": []
}
```

## 운영 안전 로그

기존 API 컨테이너의 2026-11-13 03:20–03:30 KST 로그만 읽었다. DB 쓰기·사용자 조작 재현·응답 원문/개인정보 로깅 추가는 하지 않았다.

- 해당 구간 `GET /v2/me/raid-room-memberships` 12건 모두 HTTP 200. 예: 03:25:04.301 / `74ae231a-c437-4022-b83a-296b3c2a6c3f`, 03:26:03.096 / `f1d015aa-84bb-4947-97cf-22684a58fa19`.
- query/회원/기기/응답 내용은 안전 로그에 없다. 특정 요청이 `state=ended`인 기록 탭 요청이었거나 Native 거절 사례와 같은 응답이었다고 확정할 수 없다. HTTP 200은 화면 파싱 성공의 증거가 아니다.
- 최초 상세 GET 403은 03:21:41.998 / `79c4fa83-c804-4923-8209-66418e693bdc`, 추가 03:24:54.143 / `057de0de-e167-4ea2-b4ab-1f1ce877ecb5`.
- 생성 context GET 03:24:35.814, 03:24:46.416은 200, 생성 POST 03:24:47.430은 201, 상세 GET 03:24:50.047은 200이다. 이후 위 상세 403도 있다. 03:27:41.270 생성 POST는 201, 03:27:43.876 상세 GET은 200이다.
- 인증 로그에는 03:20:25.725 refresh200, 03:23:27.712 Google 로그인200, 03:23:50.826 logout204, 03:23:56.832 Google 로그인200이 있다. 사용자/세션을 연결할 필드가 없으므로 모바일/웹의 로그인 순서로 특정하지 않는다.
- 로그인/복원/생성/상세 요청의 시간적 인접만으로 같은 회원·기기·방·명령을 연결하지 않는다. 최초 상세 403 전에 이 구간에서 관측된 생성 POST는 없다. 구간 밖의 과거 ACK 유무는 알 수 없다.

## 생성 403 판단

**확정:** 제보한 요청 ID는 생성 POST가 아니라 상세 GET 403이다. 생성은 현재 웹/앱 모두 정상이라는 사용자 보고가 있다. 원 ACK는 과거 명령의 성공 증거이며 현재 참가 권한이 아니다.

**재현 후보:** Native의 성공 ACK/미소비 ACK 복구 이후 anchor 없는 상세 이동 경로. 생성 직후 상세200 → 해산/전체 탈퇴 후 원 ACK 동일/상세403을 합성 서버 시험에서 확인했다. 같은 사용자의 신규 인증 세션에서도 원 ACK 동일/상세403을 확인했다. 실제 로그인 UI·기기 저장소 복구 시험과는 구분한다.

**증거 부족:** 실제 최초 요청의 방·회원·세션과 해당 ACK를 연결할 자료가 없다. 일시적 오류로 해결됐거나 모바일 로그인으로 웹이 복구됐다고 결론 내리지 않는다. 재현 가능한 경로가 있어도 이번 운영 원인 확정과 구분한다. 권한 완화·원 ACK 삭제·무조건 재생성은 하지 않는다.

## 검증과 인계 상태

최종 새 합성5건 PASS(68.54초): 목록3사례 및 해산/전체 탈퇴 각각의 과거 ACK와 현재 상세 권한. 최초 실행은 Docker Desktop 미기동으로 시험이 시작되지 않았고, 기동 후 시험 준비 코드의 구형 동결 schema helper/HTTP client 참조 오류4건을 수정해 재실행했다. 기존 그룹 정책·회원/기록·생성 회귀61건 PASS(791.31초). 초기 전체 실행의 새 준비 코드 오류4건은 최종 새 합성5건의 별도 PASS로 보완했다. 전체 실행 자체를 무실패 완료로 표시하지 않는다. 임시 시험 컨테이너/네트워크 정리 완료. 문서 링크·동결 자료 보존 검사 PASS. 실제 운영 응답 파싱·Native 수정·사용자 인수는 미확인이다.

Backend API/DTO/DB/OpenAPI 내용은 변경하지 않는다. 기존 계약 보존을 검증하는 시험과 조사 문서만 추가한다. Native가 위 표시/부가정책/cursor 계약에 동의하고 필요한 최소 수정을 완료한 뒤 합성 회귀 결과를 같은 Issue에 연결한다. 운영 반영은 양측 결과가 모인 후 별도 계획으로 제시한다. 현재 commit/push·배포·Issue 종료 범위가 아니다.

[전체3 Backend — 조사 결과·소비 계약 협의](https://github.com/heo0328/lostparty-backend/issues/52#issuecomment-6846147217)를 게시하고 실제 댓글 순서를 재조회했다. 다음 담당은 Native이며 계약 수용/최소 앱 수정·합성 회귀 결과 대기다. 공용 API 계약을 새로 바꾸는 제안이 아니며 OpenAPI도 그대로 보존한다.

## Native 설계 회신 확인

[전체4 Native 설계 수용·미구현](https://github.com/heo0328/lostparty-backend/issues/52#issuecomment-6846576987)과 [전체5 Backend 수용 확인](https://github.com/heo0328/lostparty-backend/issues/52#issuecomment-6846879058)을 연결했다. 명시 null RoomCycle 행만 기록 표시 제외, 실제 cycle 정책 정확히1개 유지, 첫 조회/더 보기의 빈 표시 페이지 cursor 연속 조회, 중복/반복 cursor 거절·중간실패 원자 반영·stale 재시작·회원/환경/주차 전환의 늦은 응답 차단 설계는 합의 범위와 일치한다.

Native 사용자 지시는 현재 설계까지여서 기능/시험 수정·자동검증·dev 화면 확인은 미진행이다. 다음 단계 담당은 Native의 별도 승인 범위 내 최소 구현·검증 회신이며 Backend 선행 변경/재검증 조건은 없다. 생성403 원인 미확정·운영 미해소를 유지한다. 이번 회신 확인은 문서·내용/diff 검사만 수행하고 기존 시험을 반복하지 않았다. commit/push·배포·이슈 종료는 하지 않는다.

## Native 구현·사용자 확인 수신

[전체6 Native 구현·자동검증](https://github.com/heo0328/lostparty-backend/issues/52#issuecomment-6847142336)과 [전체7 사용자 확인 범위 정정](https://github.com/heo0328/lostparty-backend/issues/52#issuecomment-6847809202)을 확인했다. 직접10파일266PASS(기록27 포함)·변경4파일 분석0은 담당자 보고이며 Backend가 Native 로컬 소스를 읽거나 시험을 재실행한 결과가 아니다. 보고된 명시 null 행 표시 제외·정책 strict 검증·빈 페이지 cursor/원자 반영·stale/늦은 응답 처리·옛 anchor 보존은 합의 범위와 일치한다.

기록 표시·새로고침·상세·주차/탭 왕복은 dev 사용자 정상 보고다. 더 보기/다중 페이지는 자료 부족으로 수동 미확인이며 합성 자동 시험 통과와 구분한다. 추가 자료 생성/삭제·반복 사용자 재현은 요청하지 않는다. 실제 운영 반영/해소·과거403 원인은 여전히 미확인이다.

[전체8 Backend 수신](https://github.com/heo0328/lostparty-backend/issues/52#issuecomment-6847918619)을 게시하고 실제 순번과 이슈 상단을 갱신했다. Backend API/DB/OpenAPI 변경이나 추가 재검증은 필요 없다. 양측 미커밋·미push, Native dev/main 미반영이며 다음 단계는 개발자의 게시/통합·운영 반영 결정이다. 이 수신 확인으로 commit/push·merge·배포·이슈 종료를 실행하지 않는다. 문서·diff 검사만 수행했다.

## 2026-11-13 — 사용자 게시·dev 통합 지시

사용자가 버그 수정 완료를 확인하고 커밋·dev 병합·push를 지시했다. Backend의 조사·합성 회귀·협업 기록을 같은 목적 브랜치에서 게시/통합한다. 기존 회귀61/최종 합성5와 문서 검증 근거를 재사용한다. 운영 배포는 추가 개발 후 일괄 진행하기로 했으며 이번 서버/DB/키·main 변경이나 이슈 종료는 하지 않는다. Native 저장소는 담당자 게시 회신으로 추적하며 Backend가 로컬 소스를 수정하지 않는다. 실제 커밋·원격 일치는 최종 Git 확인 및 이슈 게시 결과에 연결한다.
