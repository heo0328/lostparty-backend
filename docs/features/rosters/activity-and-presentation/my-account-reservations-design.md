# Issue53 — 내 계정 리메이크 계약 설계안

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
