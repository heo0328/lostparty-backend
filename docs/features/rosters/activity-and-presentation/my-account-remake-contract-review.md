# Issue53 — 내 계정 리메이크 계약 조사

2026-11-13. 기준 Backend dev f527c0c. 아래는 기존 사실과 미합의 제안을 구분한 협업 답변이다. 코드/OpenAPI/DB 변경·서버 시험은 하지 않았다.

## Backend — 기존 계약 조사 결과 / 표시는 기존 재사용·예약은 읽기 확장 제안

조사 기준은 Backend dev 고정 [f527c0c745019734feeed471bec107f28fe86b97](https://github.com/heo0328/lostparty-backend/tree/f527c0c745019734feeed471bec107f28fe86b97)입니다. 이번은 소스/OpenAPI 정적 대조와 계약 제안이며 업무 코드·schema·DB·서버 변경/쓰기 시험/배포는 하지 않았습니다. Native 로컬 소스는 읽지 않았고 본문의 실제 DI 보고를 기준으로 소비 영향을 검토했습니다.

### 1. 사용 선택 전원 표시: 새 API 없이 기존 계약 재사용 권장
- personal-profile의 preferences와 일괄 personal-profiles는 표시 설정 값을 반환하며, 서버가 visible=false/visible_count만으로 캐릭터 원본을 잘라 내는 구조가 아닙니다. visible은 신규 참가 자격/권한을 부여하는 값도 아닙니다. Native 내계정 렌더링에서 activity 선택을 기준으로 삼되 현재 소유/usable/누락 정책·대표·수동 순서를 기존대로 적용하면 됩니다. suspect/누락 행을 표시에서 지우는 것으로 해석하지 말고 기존 경고/허용 동작을 유지해 주세요.
- 기본 preferences는 version=1, preferred_role=null, visible=true, display_order=null, saved_at=null입니다. 계정 presentation 기본은 version=1, visible_count=6, saved_at=null이며 count 입력은 1..200입니다. 이 기본값/검증/기존 응답은 유지합니다. 기존 소비자의 노출 의미까지 전역 변경하거나 저장자료를 일괄 true/200으로 바꾸지 않습니다.
- PUT /v2/me/characters/{character_id}/personal-preferences는 preferred_role(nullable)·visible(필수 bool)·display_order(nullable 정수)와 expected_version/expected_ownership_revision/expected_lifecycle_revision이 모두 필요한 전체 설정 명령입니다. 신규 역할/순서 명령에서는 **최신 조회의 visible을 그대로 동봉**하고 변경하지 않는 역할/순서도 보존합니다. visible=false라도 새 화면에서 활동 캐릭터를 숨기는 조건으로 사용하지 않습니다. 값이 없다고 임의 true로 보정하지 말고 기존 personal-profile 또는 일괄 personal-profiles로 최신 값을 확보한 뒤 명령을 구성합니다. 카드별 N+1을 요구하지 않습니다. 기존 GET /v2/me/characters/personal-profiles는 반복 character_id query로1~50개 distinct ID를 읽는 일괄 조회이며 항목별 status/profile/error를 확인해야 합니다. 일괄 HTTP200만으로 실패 항목의 visible을 추정하지 않습니다.
- REVISION_CONFLICT 시 현재 값을 다시 읽고 사용자의 역할/순서 의도를 재적용해 새 명령으로 처리합니다. 기존 outbox 본문을 수정하거나 같은 key에 새 본문을 넣지 않습니다. 미확정 명령/원 ACK는 원계약으로 복구하며 ACK를 현재 권한·현재 상태로 취급하지 않습니다. role-summaries/{role}의 분석값 저장은 별도 계약으로 visible 필드가 필요 없습니다.
- 캐릭터 관리의 순서 저장 뒤 presentation count 저장은 신규 동작에서 중단할 수 있습니다. GET/PUT presentation-settings 자체는 구버전/원명령을 위해 유지하고 count 단독 저장을 새 역할/순서 저장의 성공 조건으로 연결하지 않습니다. 과거 count 명령은 기존대로 복구합니다.
- Backend 저장소 사용처 대조에서 이 두 값은 profile/presentation 저장·조회와 계약 메타데이터에 쓰이며 모집 검색의 서버 노출 필터로 사용되지 않습니다. 다른 배포 앱 전체의 소비 종료는 Backend만으로 확정할 수 없으므로 필드/API 삭제는 제안하지 않습니다. visible 생략형 새 writer는 현재 요구를 위해 필수가 아닙니다.

근거: [profile DTO](https://github.com/heo0328/lostparty-backend/blob/f527c0c745019734feeed471bec107f28fe86b97/app/game_accounts/schemas/profile_schemas.py), [preferences 저장·기본값](https://github.com/heo0328/lostparty-backend/blob/f527c0c745019734feeed471bec107f28fe86b97/app/game_accounts/character_profiles/profiles.py), [presentation 저장](https://github.com/heo0328/lostparty-backend/blob/f527c0c745019734feeed471bec107f28fe86b97/app/game_accounts/character_profiles/presentation.py).

### 2. 회원 전체 예약: 현재 공개 계약에는 그래프를 완성하는 API가 없음
현재 OpenAPI 전체 경로와 reader를 대조했습니다.
- GET /v1/me/play-availability는 회원 가능시간 설정으로 재사용합니다. 예약 전체 조회를 대신하지 않습니다.
- GET /v2/me/raid-schedule-overlaps?target_cycle_key=T는 충돌쌍 목록입니다. pair_count 및 reservation_count도 충돌쌍에 참여한 예약의 개수입니다. 단독예약을 주지 않습니다. 현재 구현은 released_at=null, ends_at>서버현재시각, 선택T·현generation·participating·활성 관계를 검사하므로 과거 시간대까지의 전체 예약 조회라고 확장 해석할 수 없습니다.
- 방별 schedule-context/plan은 권한 있는 해당 방의 자료이고 anonymous_busy도 회원 전체 원본이 아닙니다. 모든 방 순회나 충돌쌍 펼치기로 전체 예약을 합성하지 않습니다.
- 내부 recruitment_reservations에 user_id/예약UUID/room·session·segment·assignment·실제 시작/끝·schedule_revision/released_at이 있어 새로운 원장을 만들 필요는 없습니다. 베타 미확정 일정에도 실제 약속 예약이 생성될 수 있으므로 '확정 session만 조회'를 전체 예약으로 제안하지 않습니다. 단순 후보/개인 가능시간을 예약으로 만들어 내지도 않습니다.

근거: [현재 overlap reader](https://github.com/heo0328/lostparty-backend/blob/f527c0c745019734feeed471bec107f28fe86b97/app/raid_rooms/schedules/cycle_times.py), [예약 모델](https://github.com/heo0328/lostparty-backend/blob/f527c0c745019734feeed471bec107f28fe86b97/app/raid_rooms/models/source_models.py), [베타 약속 예약](https://github.com/heo0328/lostparty-backend/blob/f527c0c745019734feeed471bec107f28fe86b97/app/raid_rooms/schedules/beta_schedule.py).

### 3. 최소 확장 후보 — 아직 공개 계약/구현 아님
새 endpoint를 먼저 늘리지 않고 **기존 GET /v2/me/raid-schedule-overlaps의 선택 response_profile**로 회원 예약 목록을 받는 안을 우선 검토합니다(가칭 personal-reservations-1). 생략 시 기존 충돌 응답·count·페이지 의미를 유지하고 미지원 profile은400으로 닫습니다. endpoint 이름과 맞지 않는 별도 시간표 책임이 커지는 경우에만 독립 조회와 비용을 비교해 합의합니다. 충돌 목록의 items에 예약을 섞거나 기존 reservation_count 의미를 바꾸지 않습니다.

조회 주체는 로그인 회원으로 고정하고 모든 본인 원정대/캐릭터의 실제 미해제 예약 중 조회기간과 교차하는 행을 같은 읽기 스냅샷에서 읽습니다. 현재 소유 캐릭터 목록으로만 필터해 아직 유효한 본인 예약을 누락시키지 않습니다. released_at=null을 기본 원본으로 하되 이력/현세대·참가 종료와 모순된 행을 어떻게 거절/제외할지는 구현 전에 기존 원장 불변식과 대조합니다.
- 취소·탈퇴·해산·완료 명령이 실제 해제한 예약은 그래프의 현재 예약에서 제외. 일부 완료/교체는 해제된 segment만 제외하고 남아 있는 본인 예약을 보존합니다. 날짜가 지났어도 미해제이면 기간 교차 조건으로 읽는 안이며 기존 overlaps의 ends_at>now를 그대로 복사하지 않습니다.
- 이 조회는 '현재 유효 예약'이며 완료/해제된 과거 참가 이력 전체를 복원하는 API가 아닙니다. 완료된 일정도 남겨 그리는 요구라면 별도 이력 요구로 합의해야 합니다.
- 후보 items 필수값: reservation_id, session_id/segment_id, room_id, 실제 cycle_key, starts_at/ends_at(시간대 포함), schedule_revision. 필요 시 본인 character_id·예약/일정 상태를 추가합니다. 타회원 이름/캐릭터·방 전체 참가 명단은 주지 않습니다. 방 제목·표시명은 화면에 필요한지 확인 후 범위/nullable을 확정합니다. 미정 시간을 가짜 예약이나0으로 표시하지 않습니다.
- 후보 scope: timezone, target_cycle_key, window_start/window_end, server_now/evaluated_at, 결과revision 및 next_cursor. 안정 정렬 starts_at+reservation_id, 본인/세션·기간·profile·limit·결과 세대를 cursor에 결합하고 변경 시409 재시작하는 안입니다. 빈 결과는 성공한 전체 수집 완료 뒤에만0건으로 확정하며 추가 페이지 실패/지원 불가를 빈 목록으로 바꾸지 않습니다. limit/응답 상한·조회 가능 주차·세대 지문은 합의 시 고정합니다. 장기 트랜잭션 유지·polling·운영 쓰기 재현은 추가하지 않습니다.

### 4. 주차와 달력 경계 — Native 확인 필요
실제 게임주차 T는 KST **수요일06:00~다음 수요일06:00 미만**입니다. 수~화7행의 00~24시는 **수요일00:00~다음 수요일00:00 미만**이어서 같지 않습니다.
예: T=2026-11-11이면 게임주차는 11/11 06:00~11/18 06:00, 달력7행은 11/11 00:00~11/18 00:00입니다. 달력 첫 수요일00~06은 이전 게임주차이며 게임주차 마지막 수요일00~06은 그7행 밖입니다.

추천은7행 그래프의 window를 달력00시 기준으로 명시하고 예약을 **starts_at<window_end && ends_at>window_start**로 조회하는 것입니다. RoomCycle.cycle_key==T만 필터하면 첫날 새벽의 이전T 예약을 빠뜨릴 수 있어 인접 실제T도 기간 기준으로 포함합니다. 원본 시간은 보존하고 Native가 자정별 분할·window clipping합니다. 끝점은 배타적이며 next-day/end_day_offset 가능시간도 날짜에 펼친 뒤 잘라냅니다. 응답 각 행의 실제cycle_key와 화면 기준T를 구분합니다. 게임주차7일 자체를 전부 보여야 한다면8번째 날짜의00~06 표시 등 UI 정책이 필요하므로 달력7행으로 다 표시됐다고 주장하지 않습니다.
근거: [게임 주차 계산](https://github.com/heo0328/lostparty-backend/blob/f527c0c745019734feeed471bec107f28fe86b97/app/raids/service.py).

### 다음 담당·완료 조건
Native는 (1) 최신 visible 보존/신규 count 쓰기 중단 재사용안, (2) 달력00시7행 window와 이전T 새벽 포함, (3) 현재 미해제 예약만 표시하고 완료/해제 이력은 제외할지, (4) 카드 식별/표시 필드와 조회할 주차 범위를 사용자 준비 검토 때 확인해 주세요. 이는 기능 구현·기기 재시험 요청이 아닙니다.
Backend는 수용/선택 후 최소 확장 입력/출력·페이지/세대·권한·해제/부분완료·주차 경계의 정확한 계약 후보와 필요한 검증을 정리합니다. 계약 합의 및 별도 구현 지시 전 원본 API/OpenAPI를 바꾸지 않습니다. 신규 backend 코드가 없어 Penpot03 준비를 미게시 서버 소비 대기로 막지 않습니다. 조사·문서는 feat/my-account-contracts의 로컬 누적이며 미커밋·미push, 배포/자료 변경/Issue 종료 없음입니다.

## 2026-11-13 — Native 사용자 준비 검토 결과 수신

[전체2 Native](https://github.com/heo0328/lostparty-backend/issues/53#issuecomment-6853275922)가 사용자 채택4항목을 회신했다. 기존 표시 API 재사용, 이번/다음 주 달력 수00~다음수00(8행 없음)/이전 실제T 새벽 교차 포함, 현재 미해제 예약만(단순 과거시간 제외 금지/완료이력 제외), 최소 레이드명·본인 캐릭터·예약시간 표시다. 다음 Backend는 경로/profile의 조회 책임·기존 충돌 소비 보존과 정확 입력/출력·출처/nullable·페이지/세대/상한·권한/해제/부분완료/자정 검증 후보를 정리한다. 이번은 회신 확인·기록이며 새 계약 후보 작성 완료나 공개 계약 확정/구현으로 보고하지 않는다. 문서/계약 협의만 진행하고 API/OpenAPI·DB·Penpot/배포/commit/push 변경 없음.
