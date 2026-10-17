# 레이드 카탈로그·서버 주차 (#10)

기준일 2026-10-17. [Issue #10](https://github.com/heo0328/lostparty-backend/issues/10), [첫 번째 Backend 명세](https://github.com/heo0328/lostparty-backend/issues/10#issuecomment-6229990139). 작업 브랜치 `feat/raid-services`. 기존 API/자료는 보존하며 DB migration 없이 읽기 두 개를 추가한다.

### 조회 계약

- `GET /v1/raid-catalog`: 공통 공개 정보이므로 세션·개인 키 없이 조회합니다. query/body 없음, cursor 없음(유한한 전체 카탈로그). 비활성 항목도 반환하며 새 명령에서 선택 불가입니다. `Cache-Control: no-store` 유지.
- 응답 필수: `schema_version`(2), `catalog_version`("2026.08.20"), `updated_at`(원본 자료 수정 UTC시각), `raids` 배열. 각 raid: `raid_id`, `official_name`, `display_name`, `aliases` 배열, `display_order`(원본 배열 순서,1부터), `party_size`(전체4/8명), `party_count`(4인 소파티1/2개), `required_support_count`(전체1/2명), `max_dealer_count_per_class`(전체1/2명), `gate_count`, `is_active`, `difficulties` 배열.
- 난이도 필수: `difficulty_id`, `name`, `display_alias`, `display_order`, `min_item_level`(정밀 십진 **문자열**), `clear_gold`, `bound_gold`(원본 비음수 정수, 새 계산 없음), `is_active`. 이번 필드에는 null이 없습니다. ID는 이름과 독립한 안정적 문자열이며 난이도 ID는 raid 범위입니다. 5raid/13difficulty와 본문 입장레벨·정원을 그대로 반영합니다.
- `schema_version`은 구조, `catalog_version`은 내용 버전입니다. ID는 재사용하지 않고 비활성으로 보존하며 내용 수정 시 버전을 변경합니다. 응답 자체가 가입 권한이 아니고 후속 쓰기에서 버전/현재 활성/정밀 레벨을 재검사합니다. 4인 소파티당 support1·동일 dealer직업1 정책은 파티 명령에서 검증하며 총원 제한만으로 대체하지 않습니다.
- `GET /v1/raid-cycle`: 같은 공개 읽기/입력 없음. 필수 `server_time`, `cycle_key`, `starts_at`, `ends_at`, `timezone`("Asia/Seoul"). 시각은 UTC RFC3339, 주차는 `[starts_at, ends_at)`입니다. cycle_key는 시작일의 KST 날짜 `YYYY-MM-DD`로 고정합니다. 클라이언트 시각/주차 입력을 받지 않습니다.

주차 예시(고정 예시이며 응답은 매번 서버 현재 시각):
```json
{"server_time":"2026-10-20T21:00:00Z","cycle_key":"2026-10-21","starts_at":"2026-10-20T21:00:00Z","ends_at":"2026-10-27T21:00:00Z","timezone":"Asia/Seoul"}
```
위 경계 직전은 cycle_key `2026-10-14`입니다. 자정·클라이언트 타임존은 주차 경계가 아닙니다.

### 오류·저장/권한 경계

두 GET의 알 수 없는 query·중복 query·본문은 `400 INVALID_REQUEST`이며 기존 envelope 예시는 아래와 같습니다. 입력 수정 없이 같은400을 반복하지 않습니다. 공개 공통 정보만 반환하므로 회원/캐릭터 소유를 노출하거나 생성하지 않습니다. 세션 오류/권한·쓰기도 없어 이 조회에401/403/멱등키/revision을 억지로 추가하지 않습니다.
```json
{"error":{"code":"INVALID_REQUEST","message":"INVALID_REQUEST","request_id":"00000000-0000-4000-8000-000000000000"}}
```
서비스 장애 시 재시도 가능한 transport/5xx와 입력400을 구분합니다. 없는 raid/잘못된 difficulty 조합·비활성·stale catalog 검사는 공통 내부 검증기를 준비하되, 현재 GET에 존재하지 않는 선택/쓰기 endpoint나 오류 상태를 추가하지 않습니다.


### 구현과 검증

- `app/raids/catalog.json`: [Flutter 원본 제품 자료](https://github.com/heo0328/LostParty_flutter/blob/5eef0d2a16c422530b0698a80ecb3f5cdeb7ef2e/assets/raid_catalog/raid_catalog.v1.json)를 snake_case DTO로 변환하고 원본 배열 순서의display_order를 추가했다. 5개 레이드/13개 난이도·보상 원본은 보존했다. 최신 게임 패치 검증이나 새 보상 정책을 뜻하지 않는다.
- `schemas.py`는 추가필드 거부/frozen 및 tuple 중첩으로 카탈로그를 보존한다. `service.py`는 패키지 자료 검증/순수 주차 계산과 후속 명령용 선택·정밀레벨 검증을 제공한다. 후속 쓰기는 현재 catalog_version과 현재 소유/활동/사용가능·역할/점유 등 별도 자격을 최종 transaction에서 재검사해야 한다. 카탈로그만으로 권한이 생기지 않는다.
- `tests/test_raid_catalog.py` 관련31PASS, 기존 Starlette/AnyIO deprecation warning1개. 테스트는 격리 PostgreSQL 프로젝트의 공통 fixture를 사용했으며 조회 경로는 DB/provider 함수 차단 중에도 통과했다. 개발DB에는 테스트 쓰기를 하지 않았다.
- 기존 OpenAPI paths/DTO/정책은 값까지 보존하고 두 경로와 신규 DTO만 추가한 것을 대조했다. 실행 이미지 OpenAPI 전체 일치 및 실제 로컬 HTTP 결과는 DEV_LOG/이슈의 구현 인계에서 최종 기록한다.

### 후속

Flutter의 문자열 레벨·공개 조회·주차 키 계약 소비 검토/연동은 별도다. #11 주간 원장은 raid_id+cycle_key를 공유하며 난이도로 권리를 분리하지 않는다. #12 그룹 기초는 주간과 독립하고 #13 참가 확정은 후속 주간 점유와 같은 transaction으로 처리한다. 이번에 주간/그룹/모집 구현, 운영 배포·자료 초기화·이관·불명확 일정 기본시간을 추가하지 않았다.
