# Issue17 잔여2항목 보완·직접 명령 검증

게시 최신: 사용자 지시로 구현 `caffaf3405a53be941250132a2b50779943b15f6`를 origin/feat/character-lifecycle에 push·원격 SHA 일치를 확인했다. [전체27번째 고정 구현 인계](https://github.com/heo0328/lostparty-backend/issues/17#issuecomment-6722956197)·[DEV_LOG](../../../project/DEV_LOG.md) 기준이며 앱247파일은 실제 dev imagece59926c/DB0036과 일치한다. 아래 미커밋·미push/게시 대기는 당시 기록이다. 새 서버/DB 변경·폴더 이동/분류·merge/운영 배포는 하지 않았다.

실행 지원 인계: [전체25번째 Backend 로컬 반영](https://github.com/heo0328/lostparty-backend/issues/17#issuecomment-6722917497).

현재 실행 최신: [Native 전체24번째 보완 수용](https://github.com/heo0328/lostparty-backend/issues/17#issuecomment-6722805010) 확인 후 사용자 지시로 로컬 API imagece59926c·DB0036에 보완을 반영했다. 실행247파일과 검증 소스/두 전체 계약 일치·DB117업무표99행/sequence·키/환경/포트/볼륨 보존·healthy를 확인했다. [실제 반영 집계](../../../engineering/operations/records/roster-participation-followup-local-rollout.json)가 현재 기준이며 아래 미반영·소비 대기는 당시 이력이다. 보완은 미커밋·미push이고 Native 신규 연결/기기·운영은 별도다. 폴더 분류/파일 이동은 하지 않았다.

공식 인계: [#17 전체23번째 Backend — 잔여2항목 보완·검증](https://github.com/heo0328/lostparty-backend/issues/17#issuecomment-6722487011). 다음 담당 Native 소비 대조이며 원격 게시/실제 dev 지원은 별도다.

2026-11-08 / `feat/character-lifecycle` / 기준 HEAD7aea6b7·게시 구현4c37c2b에 로컬 변경을 누적했다. 새 보완은 미커밋·미push·실제 개발서버 미반영이다. 기존 dev image4ac36fdb/DB0036 지원과 이번 격리 근거를 구분한다. [감사](roster-participation-backend-audit.md)·[Native 전체22번째 요청](https://github.com/heo0328/lostparty-backend/issues/17#issuecomment-6721977533)·[실행별 집계](roster-participation-verification.json)를 따른다.

## 사용자 확정과 구현

사용자가 설명을 확인하고 ‘이번주 전체 완료 후 아직 참가하지 않은 다음주에 신규 참가·개설할 때’ 직접 선택하는 범위를 승인했다. 이미 다음주까지 참가한 캐릭터의 소실을 이번주 완료 때문에 신규 선택 상태로 바꾸는 정책이 아니다. 이미 참가한 다음주 자리·기록을 보존하고 누락 경고·기존 수동 교체를 사용한다.

- `existing_participation.selection`은 실제 회원/세대/assignment 연결·활성 사용자·지속 회원을 검증하고 active M만 현재 캐릭터로 반환한다. active0은 None이며 완료P를 선택하지 않는다.
- `cycle_lifecycle.qualify`는 active0에도 참가/관리 이력의 증거를 반환하고 완료P의 현재 소유/활동/전투력으로 관리 권한을 대체하지 않는다. M이 있으면 기존 소유·이름점유·관찰 연속성·활동/소유 예외 경계와 점유/전투력/레벨·정책 검사를 유지한다.
- 신규 개설/재개설·다음주 참가의 prepare에서 선택이 없으면 기존 nullable selection과 permission으로 `CHARACTER_SELECTION_REQUIRED`를 제공한다. 본문 형식이 유효해도 미선택 context에 캐릭터를 끼워 넣은 POST는409로 거절한다. 명시한 유효 캐릭터는 현재 신규 자격 검사 뒤 원자적으로 참가한다.
- 이미 열린 N의 본인 참가가 있으면 opening noop은 그 N의 active 캐릭터를 사용하며 C의 완료P를 대신 쓰지 않는다. N 누락 관찰 후에도 자리와 noop을 보존한다. continuation은 이미 참가한 대상에 기존 `ROOM_MEMBER_EXISTS`를 유지한다.
- opening token은 요청의 명시 선택 여부를 보존한다. POST에서 None을 UUID로 파싱하지 않으며, 최신 관계/대상 revision·서명 근거를 재검사한다. 기존 ACK 복구가 새 검사보다 먼저이며 요청/journal/body/원ACK를 재작성하지 않는다.

## Native 소비에 필요한 계약 차이

새 경로·query·DTO 필드·required/nullable·명령 본문 구조 변경은 없다. 기존 context selection은 nullable, permission.reason은 string이다. 선택 전에는 permission의 거절을 표시하고 기존 캐릭터 선택 흐름에서 `character_id`와 `selected_role`을 명시해 context를 다시 조회한다. POST selection/target_items의 기존 필수 조건을 완화하지 않는다. null/빈 필수값 등 형식 오류의 기존400 INVALID_REQUEST와, 유효 형식의 미선택 context409를 구분한다.

실행 HTTP에서 assertion으로 확인한 응답의 관련 필드 발췌다. 완전 DTO 예시나 임의로 만든 인증 토큰이 아니다.

GET opening/continuation context,200:

```json
{"data":{"selection":null,"permission":{"allowed":false,"reason":"CHARACTER_SELECTION_REQUIRED","next_change_at":null}}}
```

유효한 모양의 POST에 미선택 context를 사용,409:

```json
{"error":{"code":"CHARACTER_SELECTION_REQUIRED"}}
```

새 선택의 활동 자격을 잃은 뒤 context GET,200:

```json
{"data":{"selection":null,"permission":{"allowed":false,"reason":"ACTIVITY_SELECTION_REQUIRED","next_change_at":null}}}
```

이전에 받은 유효 선택 context로 위 자격 상실 뒤 실행한 POST는409 TARGET_CONTEXT_STALE다. 활동 자격 복구·새 context 조회 뒤 명시 선택 POST는200/applied, 원 key/body의 profile 생략 ACK 재조회도 동일200이다. 기존 N 참가 뒤 continuation context는 ROOM_MEMBER_EXISTS, opening은 already_open이며 누락 관찰 뒤에도200/noop을 확인했다. 재개설이 필요한 N에 open을 요청하면 기존 TARGET_REOPEN_REQUIRED를 우선 보존한다.

[기본 OpenAPI](../../../../openapi/openapi.yaml)는 바이트 그대로다. [two-cycle](../../../../openapi/two-cycle.openapi.yaml)은 `x-roster-participation.next_cycle_selection` 의미 주석만 추가했다. paths/operations/components 전체는 이전과 같으며 양쪽 전체 생성 객체 대조를 통과했다. two-cycle SHA256은 `2aeca907115ffc768cad723d227f0c2339b042f56f46ffed251c1037d235b6c4`다.

## 검증 근거와 한계

| 실행 | 실제 결과·범위 |
|---|---|
| 30479fafd378 | 초기 혼합 M/P 일정 제출/확인·실제 탈퇴/자동승계·후계자 자격·다음주 참가4PASS/76.05초 |
| 18d89396de89 | 후속6사례+기존 공개7·참가 유지20·완료 후 권한3의 관련36사례 실행:35PASS/1FAIL,685.15초. 실패는 새 rollback 시험의 미정의 변수 참조이며 제품 실패로 포장하거나 삭제하지 않음 |
| b133bb500356 | 위 시험 변수 참조 수정 후 rollback·후속 성공 재시도1PASS/30.33초 |
| 27a7f5c7951b | 신규 HTTP 초기2FAIL/44.70초: 단일주차 fixture에 다음주 설정을 함께 보냄/빈 target_items로 POST schema400 발생. fixture·시험 입력만 수정, 기존 strict 요청 조건을 유지 |
| 205ef74f905f | 신규 개설/다음주 참가 HTTP의 미선택409·활동 자격 상실/이전 context409·복구 후 명시 선택·원ACK2PASS/49.08초 |
| 4767a139c6d6 | 기존 N의 누락 후 noop 보강 포함 위2사례·종전 일반 신규 개설/기존 noop/베타 분 단위 개설 회귀3사례:5PASS/92.78초 |
| 1b0565080497 | 재개설의 동일 미선택/명시 선택·자격 상실/복구·원ACK·기존 N 누락 noop1PASS/34.51초 |
| 39887287d214 | 최종 생성 기본125경로142동작·two-cycle188경로209동작 전체 객체 일치 PASS |

새 직접 명령 시험은9개 사례이며 구간별로 실행했다. 실행별 통과 수는 중복을 포함하므로 합산하지 않는다. 격리 PostgreSQL/합성 회원·TestClient HTTP이며 실제 dev/운영 서버·실회원/provider/Native 기기 시험이 아니다. 기존 Starlette 경고1은 그대로다. 전체 repo 회귀·성능 인수는 미실행이다. 별도 WSL socket 실패는 Docker 실행 전 접근 경계였고 허용된 host 경로의 일회용 시험으로 재실행했다. 실제 개발 DB/볼륨/키는 사용하지 않았다.

## 인계와 다음 담당

Backend 두 잔여 항목의 로컬 보완·해당 검증을 완료했다. Native는 위 오류 소비와 기존 참가/다음주 선택 흐름의 차이만 대조한다. 이미 확인한 파서/화면을 일괄 재시험하도록 요청하지 않는다. 새 보완의 원격 구현 SHA와 실제 dev 지원은 아직 없으므로 실행 중이라고 안내하거나 Native 실연결 시험을 요청하지 않는다. 현재 실행은 이전 게시 구현4c37c2b·image4ac36fdb/DB0036이고 운영은 그대로다.

게시/실제 로컬 반영·merge/운영 배포·기기 인수·Issue 종료는 구분하며 사용자 별도 지시 기준을 따른다. Native는 기능 개발 후 사용자 기기에서 화면을 확인하는 순서를 보고했고 Backend는 Penpot/화면을 구현하지 않는다. 소스 파일 SHA256은 검증 집계의 followup_commands.source_manifest에 남긴다.
