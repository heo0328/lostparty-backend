# Issue #13 참가 인원 정렬·남은 자리 검색

2026-10-20, Flutter [전체59번째](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6287178945) 입력 조사 회신을 반영한다. 기존 로컬 저장 값을 Backend wire라고 간주하지 않는다.

## 최종 wire

POST `/v1/raid-rooms/search`의 기존 필드에 다음을 추가한다. 생략 가능한 추가 필드이며 기존 요청은 기본값으로 처리한다. null·알 수 없는 키/enum·잘못된 타입은400이다.

```json
{
  "sort": {"criterion":"member_count","direction":"descending"},
  "remaining_slot_counts":[2,3]
}
```

- Flutter local `criterion: memberCount` → Backend `member_count`. direction은 `ascending`/`descending` 그대로. criterion은 이 한 값뿐이며 기본 정렬은 member_count descending이다. sort를 생략하거나 `{}`를 보내면 기본값이다. 로컬 schemaVersion을 Backend에 전달하지 않는다.
- 비교 값은 RoomCard.app_member_count와 같은 **현재 지속 membership의 절대 인원수**다. 정원 비율/남은 자리 수·활성 assignment 수로 대체하지 않는다. 다중 레이드/세션을 JOIN해 한 회원을 중복 계산하지 않는다.
- 두 방향 모두 동률은 `created_at DESC, room_id DESC`다. Flutter가 특정 동률 키를 요구했다는 뜻이 아니라 원래 입력 순서를 서버가 안정적으로 제공하기 위한 기술 기준이다. 새 페이지에만 로컬 재정렬하지 않는다.
- `remaining_slot_counts`: 기본[] 제한 없음. 1..7의 엄격한 정수·중복 금지. 여러 값은 OR/정확히 일치. `max(0, app_capacity-app_member_count)`로 계산하여 4/8인 정원 모두 적용한다. []이면0석/만석도 유지하며 [2,3]이면 정확히2/3석만 통과한다. 파티/역할/직업 자리 필터는 추가하지 않는다.
- 가시 권한과 raid/difficulty·그룹OR/회원AND/회원별캐릭터OR → 남은자리 → 참가인원 및 동률 정렬 → 페이지 순서로 모두 서버 SQL에 적용한다. `GET /v1/raid-rooms`도 기본 인원내림차순을 공유하며 복합 입력은 POST search를 사용한다.
- cursor는 actor와 정규화한 전체 조건(sort/remaining_slot_counts 포함), directory/cycle/group 권한 세대에 바인딩한다. 배열 집합 순서만 바꾸면 같은 조건이다. 조건·목록 세대가 바뀌면409 CURSOR_STALE로 첫 페이지부터 재조회한다. 이미 발급된 구버전 cursor는 유지하지 말고 새 첫 페이지에서 시작한다. 위조/다른 actor 문맥은400, 그룹 문맥 세대 변경은 기존409 FILTER_CONTEXT_STALE다.

기존 API schema의 경로/operation은 유지하며 Search 추가 필드·Sort DTO와 검색 정책만 보완한다. DB schema0023·개인표 계약은 바꾸지 않는다. 사용자 실제 자료를 테스트용으로 수정하지 않는다.

## 개인표 회신 접수

Flutter [전체60번째](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6287470514)는 개인표 UI/GET·PUT 로컬 연결·합성48PASS/분석0을 보고했다. 미커밋/미push·실제8000/실회원/기기 수동 인수 전이며 Backend는 그 구분을 유지한다. 방 제출표 명시 복사와 개인표 원본 저장은 계속 별개다. 새로운 제품 정책/반복 시험 요구는 없다. 다음 Flutter 수동 확인/사용 SHA와 적용 범위 보고를 수신한다.

## 검증·실행 범위

격리 PostgreSQL/HTTP 기존검색3·새조합/정렬/자리/커서경계1·계약전체대조1 **5PASS/25.69초**. 테스트는 동일 그룹 내 2명/1명·동률인 방을 만들어 limit1로 페이지 순서/오름·내림·정확한 남은자리 및 만석을 검증한다. 배열 순서만 바꾼 같은 조건의 cursor 유지, 다른 정렬·새 membership세대의 cursor409와 boolean/0/8/중복자리/미지원정렬400도 확인했다.

로컬 API8000 새이미지 healthy·실행OpenAPI전체일치, 새 sort/remaining_slot_counts 입력의 읽기전용 POST실응답200/no-store(실제방0), DB0023유지. DB migration·실회원모집쓰기/provider·기기시험 없음. 전체 회귀 재실행이나 네이티브 실제 적용·인수로 표시하지 않는다.
