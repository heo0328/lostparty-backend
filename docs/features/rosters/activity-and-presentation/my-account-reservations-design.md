# Issue53 — 내 계정 리메이크 계약 설계안

현재 상태: 합의 계약을 구현·검증·로컬 dev에 반영했다. 아래 설계 단계 표현은 협의 이력이며 최신 결과는 [구현/검증](my-account-reservations-implementation.md)을 따른다.

2026-11-13 / feat/my-account-contracts / 코드 기준 dev f527c0c. **설계 제안·미구현**이며 공개 OpenAPI가 아니다.
[Native 전체2 사용자 확정](https://github.com/heo0328/lostparty-backend/issues/53#issuecomment-6853275922)과 [기존 계약 조사](my-account-remake-contract-review.md)를 따른다.

## 목적과 보존 흐름

활동 선택 캐릭터 전원 표시와 이번/다음 달력 주간의 본인 실제 예약 그래프를 제공한다. 대표·수동 순서·소유/usable·누락 경고·기존 pending/원 ACK와 충돌 조회를 보존한다. 완료 이력 시간표, 활동 자동추가(#18), 통계(#19), 소유권 이전(#15), 누락 시험자료(#17)는 포함하지 않는다.

화면/Penpot·반응형 배치·선택 구간 표시는 Native 담당이다. Backend는 현재 유효한 본인 예약과 최소 표시 원본을 한 목록으로 제공하며 방별 상세 선조회·추가 provider 호출·polling을 요구하지 않는다.

## 조회 경로 추천

**GET `/v2/me/raid-reservations` 하나를 추가하는 안을 추천한다.** 이름/경로는 Native와 계약 대조 전의 후보다.

| 방식 | 평가 |
|---|---|
| 기존 overlaps의 response_profile | 경로는 늘지 않지만 충돌쌍/전체예약의 단위·count·기간·과거시각·인접주차 의미가 다르다. 한 경로의 서로 다른 책임을 선택자로 나누게 된다 |
| 회원 예약 조회 하나 | 독립 역할이 명확하고 현재 겹침 소비를 전혀 바꾸지 않는다. 예약 단위·달력 기간·페이지 계약을 독립 고정할 수 있다 |
| 방별 상세/충돌쌍 재조합 | 단독예약 누락과 N+1 때문에 제외 |

앞선 전체1의 profile 우선 검토에서 **이번 정밀 설계 추천을 변경**한 것이다. API 개수 자체를 줄이려고 다른 의미를 한 경로에 넣지 않는다. 새 count/상태/재검증 endpoint·새 예약 원장·기존 overlaps 삭제는 추가하지 않는다. DB migration은 현재 조사상 필수가 아니며 인덱스 필요성은 실제 계획/측정 후 결정한다.

## 달력 범위와 사용자 확정

확정된 표시 창은 KST 수요일00:00부터 다음 수요일00:00 미만이다. 실제 게임 주차는 수요일06:00 전환을 유지한다.

**사용자 확정:** 그래프의 ‘이번 주’는 달력 수요일00시에 바꾼다. 그래프 주차 키 `calendar_week_key`와 게임 `current_cycle_key`를 별도 반환한다. 수요일00~06시에는 둘이 다른 날짜여도 정상이다. 내 계정 그래프를 맞추려고 게임 주차 계산이나 다른 화면을 바꾸지 않는다. 2026-11-13 사용자 진행·commit/push 지시로 이 전환 기준을 확정했다.

예: 2026-11-18 03:00 KST라면 달력 이번 주는 11/18 00:00~11/25 00:00, 게임 현재 주차 키는 11/11이다. 그래프가 게임 주차 전환을 기다리는 대안은 이6시간 동안 이미 끝난 달력 창을 ‘이번 주’로 보여주므로 추천하지 않는다.

입력 후보:
- `calendar_week_key`: ISO 날짜 YYYY-MM-DD, 수요일만. 현재 달력 주차 또는 +7일만 허용한다. 생략/자동 보정 없이 명시한다.
- `limit`: 기본100, 1..200 정수. `cursor`: 후속 페이지용 불투명 토큰.
- 임의 user/캐릭터/방 ID·임의 기간·상태·timezone·profile 입력은 없다. 중복/추가 query·미지원 값은400이다.

서버가 KST에서 달력 창을 계산하고 UTC 시간대 포함 start/end를 응답한다. `window_start` 포함, `window_end` 배타. 실제 예약 시간은 자르지 않고 Native가 자정별 분할/clipping한다. 첫날00~06시의 이전 실제T 예약은 기간이 교차하면 포함한다. 다음 수요일00~06시는 다음 달력 창에 속하며8번째 행은 없다. 시작이 window_end와 같거나 끝이 window_start와 같으면 제외한다.

주차 전환으로 기존 허용 주차를 벗어난 요청은409 `CALENDAR_WEEK_UNAVAILABLE` 후보로 재선택한다. 허용 범위 안에 남은 주차도 현재 달력 세대가 바뀌면 기존 cursor를409 stale로 닫는다. 임의 과거 주차 이력 조회를 허용하지 않는다.

## 읽기 원본·권한·수명

`recruitment_reservations.user_id=로그인회원`, `released_at IS NULL`, `starts_at<window_end AND ends_at>window_start`를 SQL 페이지 선택 전에 적용한다. 현재 소유 목록/activity/visible/count로 다시 제한하지 않는다. 서버가 제공하는 본인 예약은 현재 다른 화면의 쓰기/상세 권한을 보장하지 않는다.

Reservation→Assignment 및 CycleRound→RoomCycle로 실제 cycle_key와 세대를 연결하고 참여·예약·배정의 room/membership/user/session/segment 관계를 검증한다. 기존 overlaps의 현재T·participating·ends_at>now 조건을 복사하지 않는다. 과거 시간이어도 미해제 예약이면 포함하며 미확정 베타 약속 예약도 실제 원장에 있으면 포함한다. 시간 후보·개인 가능시간은 예약이 아니다.

- 실제 해제된 완료/취소/탈퇴/해산 예약은 제외한다. 일부 완료/교체 후 미해제 원본은 보존한다. 같은 방 재참가에서도 reservation_id를 합치지 않는다.
- 회원 소유 예약의 최소 정보만 반환한다. 현재 그룹 공개 여부를 목록 검색 권한과 동일하게 다시 검사해 본인의 유효 예약을 감추지 않는다. 방 제목·타회원 정보·등록 식별자/인증정보는 포함하지 않는다.
- **불변식 오류 처리 후보:** 미해제 원장인데 종료 참여/비현세대·필수 연결 누락 등 논리 모순이 있으면 정상 빈값으로 숨기지 않고 조회 전체503 `RESERVATION_DATA_UNAVAILABLE`로 닫는다. 자동 해제/복구 쓰기는 하지 않는다. 구현 전에 종료·review_required·베타 약속·소유권 상실 원장을 합성 대조해 정상 보존 상태를 오류로 잘못 분류하지 않는 상태표를 확정한다. 이 상태표는 현재 구현 착수 전 기술 확인 항목이다.

## 응답 후보

기존 오류 envelope/request_id/no-store를 재사용한다. 성공 형태는 `scope`, `data`로 제한한다.

scope: `server_now`, `current_cycle_key`(게임06시), `current_calendar_week_key`, `calendar_week_key`, `timezone='Asia/Seoul'`, `window_start`, `window_end`, `policy_version='personal-reservations-1'`.

data: `items`, `result_revision`, `next_cursor`(종료 null), `evaluated_at`. 별도 전체 count는 현재 화면에 필요 없어 추가하지 않는다. 전 페이지 성공과 next_cursor=null이 전체 수집 완료의 조건이다.

| item | 타입·원본/의미 |
|---|---|
| reservation_id/session_id/segment_id/room_id | 필수 UUID. 예약 원장의 식별자, room_id는 후속 권한 보장이 아님 |
| cycle_key | 필수 실제 주차 날짜. CycleRound/RoomCycle 원본, 화면 달력 키와 다를 수 있음 |
| starts_at/ends_at | 필수 timezone 포함 시각, starts_at<ends_at. 원본 정밀도 보존·5분 반올림 없음 |
| schedule_revision | 필수 양수 정수, 예약이 저장한 일정 버전 |
| raid | raid_id/difficulty_id 필수 식별자(Item/Round), display_name nullable 문자열(서버 카탈로그). 사라진 카탈로그 이름을 다른 레이드 이름으로 추정하지 않음 |
| character | character_id 필수 UUID(해당 Assignment), display는 예약에 연결된 Assignment.display snapshot에서 본인 이름/서버/직업만 allowlist로 투영 |

character.display는 `{name,server_name,class_name}`이고 각 문자열은 원본 미확인 시 null을 허용한다. 현재 소유권이나 provider 재조회로 snapshot을 덮지 않고 canonical ID와 표시 이름을 구분한다. 카탈로그/과거 display 원본 키의 실제 변형은 구현 전 fixture 대조 항목이다. 이름 누락이어도 유효 예약/시간은 유지하며 Native는 ‘이름 확인 불가’ 같은 기본 표시를 사용한다. 필수 식별자·시간 누락은 nullable로 숨기지 않는다. 아이템레벨/전투력·역할·타회원 display·원 snapshot 전체를 전송하지 않는다.

시간은 UTC ISO8601 출력/KST 렌더링을 기본으로 한다. 상태 enum은 그래프 요구에 없어 추가하지 않는다. 미해제라는 사실을 일정 확정/게임 완료 증거로 표현하지 않는다. 같은 session의 여러 레이드/segment는 실제 예약 행으로 반환하고 Native가 시각적으로 겹침을 표현하며 임의 dedup으로 레이드 정보를 잃지 않는다.

## 페이지·세대·조회 비용

각 요청은 read-only REPEATABLE READ에서 본인 전체 조건과 결과 세대·페이지를 계산한다. 정렬 starts_at ASC/reservation_id ASC, cursor는 마지막 정렬키를 가진 keyset 방식 후보다. HMAC은 본인·인증세션·달력 창·profile·limit·달력 현재세대·result_revision을 결합한다. 다른 회원/기간/limit·위조는400, 정상 서명인데 결과 세대/만료가 달라지면409 `CURSOR_STALE`. 토큰 만료 후보10분이며 페이지 사이 트랜잭션은 유지하지 않는다.

결과 세대는 전체 조건의 정렬된 예약 ID/시각/일정revision·실제 주차·선택 표시 snapshot/카탈로그 표시 버전 등 응답 의미를 지문화한다. 페이지 밖 예약의 생성/해제·수정과 표시정보 변경도 stale이 되어야 한다. 해제되어 사라진 행도 집합 변경으로 감지한다. 본인 현재 달력 세대까지 포함하며 단순 페이지 항목만 hash하지 않는다.

전체 조건 지문 계산은 페이지마다 비용이 있다. 기존 user_id/starts_at의 미해제 partial index와 bulk join을 우선 활용한다. 카탈로그는 같은 요청에서 고정 관측하며 페이지마다 무조건 provider/방 상세를 읽지 않는다. 응답 상한1MiB 후보, 초과 시413 `RESPONSE_TOO_LARGE`; 무음 잘림/가짜빈값 금지. 지문 계산에 필요한 전체 SQL 행수·최악 비용을 측정하고 지원량/추가 인덱스가 필요한 경우 계약 확정 전에 제시한다. 성능 개선·무제한 확장성을 미측정으로 보장하지 않는다.

Native는 성공한 모든 페이지를 임시 누적 후 그래프에 원자 반영한다. 중간실패는 기존 성공 화면을 유지하고 오류/재시도, stale은 원래 창의 첫 페이지부터 다시 수집한다. 오류를0건으로 표시하지 않는다. 반복cursor/예약ID 중복은 오류다. 회원/환경/주차/화면 세대 전환의 늦은 응답은 폐기한다. 공용 장기 캐시·주기polling은 추가하지 않고 진입/수동 새로고침·관련 명령 성공 후 갱신한다. 렌더링용 최신 데이터가 새 명령의 권한을 대신하지 않는다.

## 표시 설정의 기존 API 재사용

Native 렌더링은 activity 전원 표시로 바꾸되 최신 preferences.visible과 변경하지 않는 role/order를 신규 전체 PUT에 보존한다. batch profiles1..50의 항목별 성공을 확인하며 실패를true로 추정하지 않는다. count 신규쓰기·순서 저장의 count 성공 의존을 중단한다. 구필드/GET/PUT/validation·기존 outbox/키/원본문/ACK는 그대로다. CAS 충돌은 재조회 후 사용자 새 의도로 새 명령을 구성하며 과거 명령을 변조하지 않는다. 이 부분은 Backend 기능 수정이 없다.

## 구현 전 계약·검증 순서

1. 사용자: 달력 ‘이번 주’ 자정 전환 기준 확정 완료. 경로/DTO·기술 수치는 Native 소비 대조로 확정하며 매 항목을 사용자 결정으로 넘기지 않는다.
2. Backend/Native: 독립 예약 조회 추천·정확 DTO·nullable·페이지/오류 및 원장 정상/모순 상태표 대조. 부족한 표시정보는 batch projection으로 해결하고 API를 더 늘리지 않는다.
3. 합의 후 별도 구현 지시: reader/HTTP/OpenAPI·회귀시험을 같은 목적 브랜치에서 구현. 기존 overlaps·원 pending/ACK strict 호환 검증.
4. 임시 DB 검증 후 로컬 dev 연결 인계, Native 소비/합성 검증과 사용자 화면 확인. 운영 반영은 추가 개발 후 별도 릴리즈 지시.

필요 시험: 0/1/100/101/200/201행·단독/중복시간·타원정대·과거시간 미해제·미확정 약속·모든 페이지 집합; 회원/세션/권한·위조/교차/만료cursor; 완료/부분완료/교체·탈퇴/해산·재참가/옛세대; 자정/수06·이번/다음달력·이전T 새벽/창끝·24시간/겹침; 누락 카탈로그/nullable display·필수 연결 모순; 페이지 사이 생성/해제/시각 변경·같은 snapshot 중 쓰기; 늦은 응답/페이지 실패·stale 재시작. 기존 충돌 DTO·role/order와 과거 count 명령/원 ACK는 영향 범위만 검증한다.

이번 단계 검증은 문서 링크·확정/제안 표현·필드 출처와 diff 검사뿐이다. 업무/API/OpenAPI/DB 변경·서버 재시험·Penpot/commit/push/merge/배포/이슈 종료는 하지 않는다.

## Native 전체5 대조 후 계약 마무리 — 이전 후보의 구체화

[전체5 Native 요청](https://github.com/heo0328/lostparty-backend/issues/53#issuecomment-6853911329)을 반영한다. 이 절이 앞선 미정 표현보다 우선한다. 아래는 구현 대상으로 합의할 계약 문서이며 실행 OpenAPI를 변경하지 않았다.

### 정확 wire·크기와 표시 투영

[닫힌 응답 JSON Schema](reservation-page.candidate.schema.json)와 [완전한 합성200 예시](reservation-page.candidate.example.json)를 추가했다. 예시 ID/이름/raid는 전부 합성이며 운영 자료·실제 카탈로그를 뜻하지 않는다. 성공 payload 모든 속성은 필수이고 additionalProperties=false, nullable은 display 문자열·next_cursor뿐이다. JSON schema 밖 의미 검사는 수요일 날짜·허용C/N달력·UTC window 정확값·starts<ends/기간교차·페이지 정렬/ID중복·limit 이하다. 날짜 문자열 길이10, 시각 UTC ISO8601 Z/소수초 최대6자리·길이20..27을 wire 규칙으로 고정한다.

result_revision은 소문자 SHA-256 hex64, next_cursor는 null 또는 길이1..8192 ASCII URL-safe opaque token이다. query cursor 최대8192, 정상서명 토큰의 발급시점+600초 만료를 모든 후속 페이지에 그대로 전파해 페이지마다 만료를 연장하지 않는다. UUID는 canonical 소문자 하이픈 형식. schedule_revision은1..2147483647. raid_id/difficulty_id는 기존 카탈로그와 같은 `[a-z0-9_]{1,64}`다. 문자열 길이는 Unicode code point 기준이며 전체 응답은 UTF-8 bytes 기준이다.

표시 이름의 실제 원본 대조:
- `app/groups/admission_core.py:display`는 server_name/character_name/class_name을 생성한다. `cycle_admission` 및 `admission_service`가 이 값을 Assignment.display에 저장한다.
- `tests/raid_rooms/common/test_recruitment_sources.py`의 fixture도 같은3키 및 class_name=null을 사용한다. `tests/raid_rooms/admissions/test_admission_eligibility.py`에도 같은 키가 있다. 실제 원본 키는 **character_name**이며 응답 name과의 명시 매핑이다. 원본의 임의 name/별칭을 우선순위 fallback으로 읽지 않는다.
- character_name→name 최대128, server_name 최대64, class_name 최대64. missing/null/빈문자/whitespace-only는 null; nonblank 문자열은 원본 그대로 보존하고 trim/자름/현재 이름 덮기를 하지 않는다. nonstring 또는 길이초과는503 RESERVATION_DATA_UNAVAILABLE. 레거시 snapshot 변형은 허용키 누락/null이면 이 규칙으로 처리하며 무관한 원본키를 노출하지 않는다.
- raid display_name은 Item.raid_id의 현 요청 고정 카탈로그명(최대128), 식별자는 Round의 difficulty_id. 카탈로그 항목 없음/blank 이름은 null. 비활성 카탈로그라는 이유로 예약을 숨기지 않는다. 필수 ID가 형식 위반이면503. 카탈로그 이름은 참가 당시 snapshot이라는 보장이 없으므로 character snapshot과 출처를 구분한다.

1MiB(1,048,576 bytes)는 **페이지 전체 JSON envelope** 기준이다. 성공 직렬화/내보내기 전에 검사한다. 요청 limit의 페이지를 자동 축소하거나 잘라 성공으로 내지 않고413 RESPONSE_TOO_LARGE를 반환한다. item1개만으로 초과해도 동일413, 정상 item 길이 제한과200행 상한 안에서 oversized 사례는 방어 시험으로 검증한다. Native는 자동 limit 축소·부분 결과 표시를 하지 않는다.

### 관측시각과 clock bootstrap

각 페이지 요청의 읽기 snapshot에서 DB 시각 S를 한 번 얻고 scope.server_now=data.evaluated_at=S로 반환한다. 다음 페이지의 시각은 달라도 되며 페이지 간 트랜잭션 동일성을 뜻하지 않는다. 모든 페이지의 동일 result_revision은 결과 의미가 같다는 조건이다. **S/server_now/evaluated_at·cursor 발급/만료시각은 결과지문에서 제외**한다. 현재 달력 키와 예약/표시 값·카탈로그 변경은 포함한다. 페이지가 바뀌어도 단순 시각 경과만으로 stale이 되지 않으며 달력00시 전환은 명시 세대 변경이다.

기존 `/v2/raid-cycles`의 DTO는 최상위 server_now를 제공하므로 Native bootstrap안을 수용한다. KST에서 server_now의 날짜로 달력 수00을 계산하고 game current key에서 calendar key를 복사하지 않는다. 게임 DTO/endpoint를 확장하지 않는다. 시각 미확보/CALENDAR_WEEK_UNAVAILABLE이면 기존 cycles 1회 재조회 후 상대선택 재계산, 재실패는 오류다. stale 재시작도1회로 제한하며 무한 교차 재시도하지 않는다. scope 추가 오류메타를 요구하지 않는다. 회원/환경/session/날짜 전환의 늦은 응답 폐기와 같은 창 이전 성공값 유지 규칙을 수용한다.

### 정상/모순 판정 상태표

원장 user_id와 복합 FK로 증명된 본인 소유가 읽기 권한의 기준이다. current ownership·활동·그룹 공개권한·현역CM만으로 재인가/제외하지 않는다. 날짜/교차 조건 이외 필터로 행을 감춰 완전성을 위조하지 않는다.

| 상태 | 처리·근거 |
|---|---|
| released_at 비null | 제외. 종료 이유·당시 이름으로 다시 활성 예약을 합성하지 않음 |
| 현 generation/active 배정·active 참여, confirmed | 미해제면 포함 |
| beta unconfirmed/confirmation_pending, 실제 약속 원장 존재 | 포함. beta_schedule.enrol의 약속 예약 생성 경로 확인. 세션 미확정만으로 오류 아님 |
| row/CM review_required·소유/usable 상실·명시 recovery | 미해제·증명된 본인 원장이면 포함. cycle_worker는 current주 자격 실패 때 review만 표시하며 예약을 해제하지 않는 경로가 있음. 새 참가 자격 판정을 읽기에 재사용하지 않음 |
| 과거시각·이전 실제T의 창 교차 | 미해제면 포함. worker 실행 전 시간 경과만으로 해제 추정 금지 |
| 일부완료/교체 | 해제 segment 제외/남은 미해제 포함. scheduling.release는 assignment/participation의 정확 원본을 해제함 |
| 탈퇴/해산/완료 또는 구 generation | 해제된 정상 이력은 제외. **상태 enum/현세대 불일치만으로는 미해제 원본을 무조건503/누락 처리하지 않는다.** 증명된 원장과 참조가 온전하면 포함한다. 읽기는 아직 해제되지 않은 시간 점유를 보여주며 종료를 추정해 정리하지 않음 |
| 필수 FK 대상/실제주차 연결 부재·복합 소유자 불일치·시간/필수ID 불량 | 전체503 RESERVATION_DATA_UNAVAILABLE. 다른 user의 행/표시를 반환하지 않음. 누락 연결은 inner join으로 조용히 제거하지 말고 검출 |
| 표시키 누락/null/빈문자·카탈로그 항목 부재 | 정의한 nullable로 포함. 현재 캐릭터/provider/방 상세 GET으로 채우지 않음 |

앞선 ‘종료/옛세대면 모순일 수 있음’ 후보를 이 표로 구체화했다. **종료 상태와 미해제 원장이 함께 있다는 이유만으로 정상 실패를 만들지 않는다.** 별도 정리 명령이나 자동해제 쓰기는 이 reader 범위가 아니다. 구조적 모순 검출과 실제 업무 종료의 정상 해제는 구현 시험에서 구분한다. CycleAssignment가 없는 legacy라도 CycleRound로 actualT와 복합 소유 원본을 증명하면 포함하며 current-generation join을 필수로 강제하지 않는다. 실제T조차 증명되지 않으면503이다.

### 지문 비용·지원 범위와 구현 검증 한계

요청당 동일 본인/기간 조건의 **가벼운 원장/표시 투영 최대10,000행**을 지원 범위로 제안 고정한다. SQL에서10,001행 sentinel을 읽어 초과를 명시503 RESERVATION_QUERY_LIMIT_EXCEEDED로 거절한다. 잘라서 지문/성공 목록을 만들지 않는다. 이 상한은 원장 삭제·가입 한도·무제한 성능 보장이 아니라 읽기 보호 조건이다. Native는 기존503 예약영역 오류로 처리한다. 상한 수치의 실제 환경 적합성은 구현 측정 후 바꾸어야 할 경우 소비측에 먼저 알린다.

결과 membership/참조 무결성을 읽기 snapshot에서 검증하고 canonical JSON 투영을 예약 정렬 순서로 hash한다. 모든 출력 의미 필드와 정책/회원/창/달력세대, 카탈로그 투영 값이 바뀌면 지문이 바뀐다. missing/null 등의 투영 결과가 같은 저장소 변경은 불필요한 stale을 만들 필요 없다. 페이지 cursor에는 별도로 세션/limit·마지막 sort key를 결합한다. 전체 결과지문은 limit/관측시각/페이지번호와 무관하게 계산한다.

최대N행의 read/projection/hash O(N), DB 정렬은 기존(user_id,starts_at) partial index 후 UUID 동률 정렬 비용이 있고 최악 O(N log N)이다. keyset 페이지가 빨라도 **지문용 전체 스캔 비용은 페이지마다 남는다**. ORM per-item db.get을 사용하지 않고 필요한 원장·Assignment·Item/Round·CycleRound/RoomCycle을 bulk projection/고정 수 조회로 읽는다. 누락 참조를 검출하려고 outer join과 검사를 사용한다. 카탈로그 snapshot은 한 요청에서 고정한다. 새 세대 테이블/worker·migration/공용 캐시는 도입하지 않는다.

현재 실행 reader가 없어 실제 SQL plan·query count·latency·memory·페이지 bytes는 **미측정**이다. 상태표는 위 저장 경로/worker/release/기존fixture의 정적 대조이지 새 HTTP 시험 통과가 아니다. 구현 단계에서0/1/100/101/200/201/10,000/10,001·혼합 참조/종료/review/legacy·표시 변형·페이지사이 쓰기·실제 query count/EXPLAIN/직렬화 bytes를 확인한다. 지원 범위에서 현저한 지문 비용이면 구현 완료로 넘기지 않고 인덱스·상한/세대 방식의 변경 필요성과 소비 영향을 재협의한다. 이번 문서 단계에 임의 성능 수치를 쓰지 않는다.

완료 근거는 Native의 이 구체화 계약 수용이며 기능/API/DB·실서버/성능 완료는 후속이다. 구현 승인 전 원본 OpenAPI/서버를 변경하지 않는다.

## 구현 준비 — Native 전체7 최종 수용 반영

[전체7 Native 최종 수용](https://github.com/heo0328/lostparty-backend/issues/53#issuecomment-6854268594). 새 사용자 제품 결정·미해결 설계질의는 없다. 다음은 아래 순서의 Backend 구현이며 이번 ‘구현 준비’ 단계에서 업무 파일/공개 OpenAPI는 변경하지 않는다. 최종 문서/schema/example 추가분은 미커밋·미push이므로55923cc에 전부 포함됐다고 인계하지 않는다.

### 코드 배치와 변경 책임

| 대상 후보 | 구현할 내용 |
|---|---|
| app/raid_rooms/schemas/personal_reservations.py | 닫힌 입력/출력 DTO·UTC/canonical UUID/문자길이·query·의미 검증. 기존 parser/DTO 전면 변경 없음 |
| app/raid_rooms/schedules/personal_reservations.py | 달력 창 계산·RR read-only 권한/원장 projection·무결성/nullable·10,001 sentinel·전체지문·keyset 페이지 |
| app/raid_rooms/schedules/reservation_cursor.py | 예약 조회 전용 HMAC scope/서명/600초 최초 만료·길이/위조/교차/stale 검증. 기존 키 재사용·새 키 생성 없음 |
| app/raid_rooms/api/personal_reservations_router.py | 인증 GET1개, no-store·query/오류 envelope·페이지 envelope1MiB guard. 기존 beta/group/remaining profile를 새로운 필수 query로 추가하지 않음 |
| app/main.py create_app | 현재 앱에만 새 router 등록. 공통 router 집합/legacy 앱에는 새 route 추가하지 않음 |
| openapi/openapi.yaml | 합의 API1개의 현재 앱 생성 명세와 전체 객체 동기화. legacy.openapi.yaml·동결 계약 보존 |
| tests/raid_rooms/schedules/test_personal_reservations.py | 임시 DB 원장/HTTP·시간·snapshot·cursor·상한·동시성·query/byte 비용 검증 |

파일명은 실제 구현 시 중복 정의/통합 적합성을 확인한 후 위 기능 분류 안에서 확정한다. 새 ORM/예약 원장·worker·migration/일괄 리팩토링은 기본 범위에 없다.

### 재사용 시 확인한 차이

- `app/game_accounts/common/support.py:cursor_decode`는2048자/offset 전용이며 만료를 직접 검사하지 않는다. 새 계약에 맞추려고 공용 helper 상한/의미를 바꾸지 않는다. 기존 recovery_key 재사용과 서명 canonical JSON/HMAC primitive를 따르되 새 domain prefix로 예약 keyset payload를 분리한다. exp는 최초 토큰에서 유지, last sort key만 다음 페이지로 진행한다.
- 현재 create_app의 router 등록과 공통/legacy 등록은 분리되어 있다. 새 reader는 current-only에 등록하고 legacy 계약 전체 비교를 유지한다.
- 기존 `/v2/raid-cycles` 최상위 server_now를 사용한다. **수06시 current_cycle_key만 바뀌는 것은 결과지문/cursor stale 사유가 아니다.** current_calendar_week_key/창·정책·예약/표시의 출력 의미만 세대를 바꾼다. 00시 달력세대 전환과06시 게임세대 전환을 별도 fixture로 검사한다.
- raid 카탈로그는 요청 시작에 한 번 로드/검증하고 해당 객체로 응답/지문을 만든다. request 도중 전역 카탈로그 값을 다시 읽지 않는다.
- SQL의 limit는10,001 sentinel 투영 단계에 적용하며 page limit는100/200이다. 이 둘을 혼동해 전체지문을 페이지 자료만으로 계산하지 않는다. 누락참조 검사는 inner join으로 삭제하지 않는 bulk projection을 사용한다.

### 구현 순서와 통과 기준

1. 최종 문서/schema/example의 게시 여부를 고정한다. 이번 사용자 요청은 commit/push 지시가 아니므로 현재는 로컬 준비이며, 게시 단계는 직접 지시 기준을 따른다.
2. 달력/시각·DTO·snapshot 투영·전용 cursor를 구현하고 합성 계약 예시/거절 벡터와 일치 검증한다. 실제 ORM 참조 모순을 검출하면서 정상 review/legacy/소유상실은 유지한다.
3. 임시 DB reader와 HTTP route를 구현·현재 OpenAPI 동기화한다. query검증·권한/회원·키형식/상한·응답바이트/오류를 확인한다. 기존 overlaps·legacy 계약을 동시에 대조한다.
4. 단독/혼합/부분완료·해제/재참가, C/N달력·자정/06시, 페이지사이 쓰기·관측시각 변화, cursor 위조/타session/만료,0/200/201/10000/10001·nullable/유니코드/문자열길이를 표적 검증한다. 임시 DB 외 자료/운영 쓰기 재현은 하지 않는다.
5. 쿼리 수·EXPLAIN·latency/memory·bytes를 같은 조건으로 측정한다. 전체지문 비용/상한 지원에 문제가 있으면 완료 인계 전 원인과 변경 필요성을 같은 Issue로 협의한다. 구현 전 성능은 미측정이다.
6. 검증 완료 후 로컬 dev API 반영 범위·DB/키/환경 보존을 확인하고 실제 HTTP/현재 생성 명세를 확인한다. 이후 Native에 고정 SHA/OpenAPI·실행 버전·미확인 항목을 구분해 인계한다. 미게시/미반영 코드를 연결 가능으로 보고하지 않는다.

준비 단계 완료는 최종 설계 수용·코드 변경 위치·차이/검증 순서가 정리된 상태다. 기능 구현/성능·로컬 실행·Native 구현/Penpot·배포 완료는 별도다.
