> **현재 구현 기준(2026-10-21):** [전체84번째 Flutter · 계약 소비 검토 마감](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6310097083)에서 잔여 충돌 없이 소비 검토를 마감했다. 계약0.4.1/policy4를 고정하며 [W1~W5 작업계획](ISSUE_13_TWO_CYCLE_WORK_PLAN.md)을 따른다. 아래 검토대기/후속질문·구판 단계표는 당시 기록이다. 실제 기능/실행API·DB 인수는 별도 미완료다.

> **최신 보완:** [계약 후보4판](ISSUE_13_TWO_CYCLE_CONTRACT_R4.md)이 전체80번째의 제목/전역CAS/생성checkbox/숙련도검색 수정을 반영한다. 아래3판까지의 생성후추가활성화/제목schema·global target CAS 가정은 최신계약이 아니다. 이 문서는 당시 기록으로 보존한다.

> **최신 계약 후보:** [전체 계약3판](ISSUE_13_TWO_CYCLE_CONTRACT_R3.md)이 전체77/78번째의 기술 보완·L1/G1/A1 확정을 반영한다. 아래 정책 대기/부분 core 상태는 당시 기록이며 최신 전체 JSON은 별도 full 파일이다.

> **2026-10-21 보완:** 아래는 전체73번째에 게시한 1판 기록이다. 전역공대장/빈N개방/승계선행취소/매주새N자동개방 가정은 [주차별 공대장 보완2판](ISSUE_13_TWO_CYCLE_LEADERSHIP_R2.md)이 대체한다. 현재 검토JSON도2판(11경로/39schema)이며 아래7경로/27schema 검증수는1판당시 결과다. 실행 구현/최종 계약으로 해석하지 않는다.

# Issue #13 이번 주·다음 주 선택 설계 1판

2026-10-21 / Backend / feat/raid-recruitment / 기준 구현 cc003e9, 문서 시작 HEAD6490f69.
**제품 확정 반영·기술 계약 검토안이다. 구현/최종 OpenAPI/DB 이행·성능 측정/Flutter 적용 완료가 아니다.** 실제 서버·DB·자료는 변경하지 않는다. 문서와 별도 JSON은 로컬 미커밋·미push이며 협업 회신에 설계 전문을 함께 제공한다.

입력: Flutter 전체 [70번째](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6294883916), [71번째](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6295440094), 최우선 [72번째](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6296073970). 69번째 수00시 gate, 70/71번째 원자 방 이동, 기존 유지의사→06시 자동 참가 방식 중 충돌하는 부분은 대체한다. 통계 구현은 별도 #19에 남긴다.

## 1. 확정 기준과 실제 변경 지점

- DB 서버 실제 현재주차 C, 바로 다음주 N=C+7일, 선택 대상 T∈{C,N}. 수06시 전환/수10시 플레이, 언제든 N 생성·검색·신청·참가 가능. C+14 개방 없음.
- 같은 방 UUID에 서로 다른 T의 레이드 회차·설정·멤버·자리·캐릭터·일정. 함께하기 ON이면 N을 공개범위에 맞게 모집하며 현재 인원을 복제하거나 자리를 선점하지 않는다.
- 기존 실제 C 참가자의 N 참가 성공은 즉시 확정이고 승인제에서도 재승인 없음. 자격/자리/한도/주간 유일성은 그대로 검사한다. 대체 캐릭터에도 같은 소스 참가자 권한을 검사한다.
- 충돌은 B 보존/A 원자 무변경. 자동 탈퇴·임시 선점·원자 A↔B 이동 없음. N 취소 후 새 참가 사이 빈자리는 보장하지 않는다.
- 완료 체크/개인완료/방 이번주 미완료종료 및 완료 정정·취소는 T=C이면서 해당 수10시 이후에만 허용한다. 기존06~10시 허용을 정정한다. 출발 이후 추가 조건은 없다. 과거 결과 읽기와 기존 자료는 보존한다.

| 실제 코드 근거 | 현재 제약 | 변경 설계 |
|---|---|---|
| integrated_models.Round/Assignment, weekly_links.WeeklyOccupancy | cycle 포함, 재사용 가능. Round는 같은 item/cycle의 재개 세대가 존재 가능 | UUID·복합 FK·원장 유지, 아래 RoomCycle에 세대/설정 연결 |
| source_models.RoomSettings/ItemSettings | 입장/숙련도/전투력/기간이 전역 | 이미 열린 T의 스냅샷과 수정 revision 분리 |
| participation_core.admit_bundle | expected=current 고정, persistent member 수로 정원 검사 | expected 현재 기대값과 T 분리, T의 슬롯/실참가만 정원 검사 |
| search.card/search, member_reads.detail/projections | 전역 멤버 수/가장 최근 assignment/현재 cycle | T의 명시 회차·참가 투영만 사용, 미래 choice fallback 제거 |
| AvailabilitySubmission PK membership, scheduling/schedule_service | 제출표 공유·현재주차 암묵 선택 | T별 명시 복사와 모든 스케줄 읽기·쓰기의 T 결합 |
| continuation.replace_choices/open_current/process_room | 선택만 저장, 개시 때 일괄 admit; created_at 기준 제안 폐기 | 즉시 admit, 대상 cycle 기준 활성화/제안 마감; 기존 intent 자동 확정 금지 |
| completion.drop_membership/character_change.change | 모든 주차 assignment/choice 해제·수정 가능 | 회차 취소/변경은 T만, 전역 탈퇴·추방은 명시 전역 효과 |
| raid_weekly.service.entry/put | 미래 읽기 거절, 현재 완료에10시 guard 없음 | 기존 GET 보존+새 summary, 모든 완료 writer에 동일10시 guard |

파일 docstring의 'not mounted' 등은 과거 단계 설명이다. 현재 구현은 main에 연결되어 있으며 이번 검토가 미구현 상태로 되돌리는 것은 아니다.

## 2. A — 최소 저장 구조·영향표

기존 Room/Item/Round/Member/Assignment/Session/WeeklyState/WeeklyOccupancy/예약/OpeningEvent를 재사용한다. membership은 방의 지속 관계·권한/한도이고 좌석 그 자체가 아니다.

새 저장 구조 제안은 다음 3종이다. 이름/DDL은 구현 전 고정하며 이번에는 migration 파일을 만들지 않는다.

1. `recruitment_room_cycles`: 유일(room_id,cycle_key), id UUID, state(`open|closed|review_required`), revision/settings_revision/members_revision/plan_revision, admission_mode/experience/combat/app_capacity, authorized_effective_at/search_floor_at, activation_revision/activated_at nullable, blocked_reason nullable. 레이드별 난이도/카탈로그/기간은 기존 Round와 그에 연결한 duration 스냅샷 열로 보존한다. 완료/재개는 별도 Round 세대이며 같은 cycle의 활성 세대 포인터/부분 유일 인덱스를 사용한다. 단순 UNIQUE(item,cycle)는 재개 이력을 파괴하므로 추가하지 않는다.
2. `recruitment_cycle_submissions`: (membership_id,cycle_key) PK, 개인표 원본 version·복사본·revision·submitted_at. 기존 제출표는 그대로 보존하고 검증 가능한 현재주차에만 최초 복사한다. N 자동 복사 없음. 개인표 원본은 주차 없는 기존 저장소를 유지한다.
3. `recruitment_participation_events`: T·room/item/round/member/assignment·행위·효력시각·서버 명령키·revision, 참가/취소/변경·결과의 불변 최소 이력. 통계 집계 테이블은 아니다. 중복 원천 유일키와 coverage 시작점을 둔다. 기존 assignment 재활성화 전후 구간도 기록한다.

추가 열/제약: Application.target_cycle(기존 targets의 Round와 복합 FK/서버 정합성), pending 유일키(room,user,T); Proposal/ResumeProposal의 명시 cycle(세션/round와 일치); target가 필요한 token/version; Round.room_cycle_id와 복합 소유 FK·활성 세대 참조, Round별 기간 근거; Choice의 legacy 취급 메타(자동 전환 없음). 기존 세션은 binding→schedule_group.cycle 및 segment→round.cycle가 모두 같은지 검사한다. 불일치 데이터는 review로 격리하며 다른 T로 추정하지 않는다.

| 자원/수정 | 소유·권한 | 영향 |
|---|---|---|
| 방 UUID/제목/공개범위/연결 그룹/책임자/해산 | 기존 공대장 및 그룹 검증 | 전역 C/N 모두. 그룹 연결 불변 등 기존 제한 유지 |
| 레이드 묶음 구성·room identity | 기존 고정 구성 | 이번에 레이드 추가/삭제 기능을 새로 만들지 않음 |
| 난이도·기간·전투력·숙련도·입장 방식·편성/자리 | 해당 T의 RoomCycle/활성 Round, 공대장 | T만. C 수정이 이미 열린 N을 덮지 않음 |
| app_capacity | T 스냅샷, 단독 raid 정원/묶음4 규칙으로 산출 | 임의 정원 변경 기능 없음 |
| 참가/예약/제출표/세션·제안/투표/캐릭터 변경 | 해당 T의 실제 관계와 기존 역할 권한 | T만. 다른 T의 최신 assignment를 대신 쓰지 않음 |
| 함께하기 ON/OFF/향후 회차 템플릿 | 전역 공대장 | ON에서 N을 원자 생성(비어 있는 인원), 이미 존재하면 동일 회차 반환. OFF가 확정 N참가·예약을 자동 삭제하지 않음 |

OFF는 이후 회차 생성/기존 참가자 특례의 새 사용을 중단하는 안이다. 이미 열린 N의 일반 모집·취소는 유지한다. 현재 auto_open_enabled UI를 v2에서는 '자동 참가'로 노출하지 않으며 아래 소비 대조에서 폐기/표시 전환을 확인한다. ON 유지 방은 전환 뒤 새 N만 빈 회차로 확보하고, 기존 N→C는 재생성하지 않는다. 새 N을 조회 시 쓰기로 만들지 않으며 worker/명시 ON·개시 명령이 생성한다. worker 지연 시 N 준비 상태/개시 권한을 메타로 표시한다.

공대장 관리 권한은 전역 membership에서, 좌석은 T assignment에서 온다. 공대장이 아직 N에 참가하지 않아도 N 설정/신청 관리가 가능하며 관리 권한만으로 자리는 차지하지 않는다. 공대장이 자신의 N 좌석 취소 시 기존 책임자 승계/마지막 인원 종료 규칙을 우회하지 않는다(별도 승계·전역 종료 확인 필요).

## 3. B — 즉시 참가·충돌·취소 명령

### 소스 증명과 즉시 참가

`GET /v2/me/raid-rooms/{room_id}/continuation-context?target_cycle_key=T&action=join`는 기본 현재 C 실제 참가 캐릭터/역할과 최신 selection/대상 bundle을 반환한다. 정상 진입에서 character 입력을 요구하지 않는다. 충돌 대체 조회에만 `character_id`와 `selected_role`을 둘 다 제공한다. 일부만 보내면400이다.

소스 자격: 같은 room의 현재 유지 membership, 서버 실제 C에 실제 참가했던 assignment(활성 또는 완료/회차 미완료종료 이력), 전역 탈퇴/추방되지 않음. 신청만 있거나 legacy Choice만 있는 사람은 자격 없음. 단순 public/group 방을 볼 권한으로는 우회 불가다. 실제 참가 이력 판정은 유효 구간으로 검증하며 명시 좌석 취소로 소스 자격이 사라진 경우는 특례를 다시 사용하지 못한다. C 묶음의 캐릭터/역할이 일치하지 않는 보존자료는 REVIEW_REQUIRED다.

명시 불참은 action=decline context를 사용한다. context의 AEAD token(최대4096bytes,120초,06시 경계로 만료)에 actor·room·source C/member/assignment IDs+revisions·T·대체 여부·선택 캐릭터 역할/소유·대상 round·weekly 원장·그룹/한도/RoomCycle revisions를 결합한다. 다른 회원 원장 CAS/타방 개인정보를 본문으로 노출하지 않는다. 서버 조회 때와 실행 직전 모두 소스 자격을 검증한다.

`POST /v2/raid-rooms/{room_id}/continuation-participations`:

1. 기존 reserve/직렬화(game-mutations-v1)/원 ACK replay 순서를 유지하며 operation namespace와 payload에 room/T 포함. 같은 key의 다른 T/본문은409 멱등 충돌이며 자동 새 키 재송하지 않는다.
2. expected_cycle_key는 실제 C 기대값 그대로, target_cycle_key는 실제 T. 소스 특례는 T=N에서만 신규 사용한다. C로 전환된 후에는 새 현재회차 admission/plan으로 명시 재진입하며 원 명령 ACK는 먼저 복구한다.
3. 서버 최신 소스 자격·token/CAS·현재 소유/활동/레벨/역할·그룹/전투력·한도·마감·전체 묶음 target 유일성·슬롯을 검증한다. 외부인은 기존 apply/join, 승인 생략 flag는 받지 않는다.
4. 같은 A/T에 이미 bundle 전체가 확정이면 새 자리 없이 `noop` ACK(캐릭터가 다르면 참가가 아니라 명시 캐릭터변경). 다른 B/T 점유는409 `TARGET_CHARACTER_CONFLICT` + 본인권한 최소 안내. partial bundle은 review/실패, 나머지만 추가하지 않는다.
5. 성공은 T의 Assignment+WeeklyState+WeeklyOccupancy+필요 세션참여/예약+참가이력+ACK를 한 transaction에 확정한다. 수동/확정일정의 기존 확인·예약 정책을 공유한다. 미정 일정은 시간 예약 없음. 선택 상태는 actual assignment가 권위이며 Choice만으로 i를 켜지 않는다.
6. 실패는 A의 choice/slot/예약/원장 변경0, B/C 그대로. context의 충돌은 HTTP200의 permission false로도 표시하고 실행시 동일 code를 강제한다. 닫기는 요청을 보내지 않으므로 불참 저장 없음.

`다른캐릭터`는 같은 소스 권한에 대체 selection만 결합한 새 context를 받아 동일 endpoint를 호출한다. 실패 후 다른 body/새 확정 시도는 새 명령키, 결과불명은 원키·원본문을 유지한다.

### 선택과 취소

| 명령/상태 | 효과 | 주요 거절 |
|---|---|---|
| N 미선택→참가 | 위 특례/일반 admission, 실제 자리 | SOURCE_PARTICIPATION_REQUIRED, TARGET_CHARACTER_CONFLICT, ROOM_FULL, 기존 자격오류 |
| N 미선택→참가하지 않기 | `continuation-declines`로 명시 decline 이벤트만 저장, 자리0 | SOURCE_PARTICIPATION_REQUIRED, CONTEXT_STALE |
| N 이미 참가 후 '참가하지 않기' | 별도 cancellation context/사용자 확인 후 `participation-cancellations` | 책임자 LEADERSHIP_RESOLUTION_REQUIRED, CAS 변경 |
| N pending 철회 | 기존 application withdraw를 T 결합 | 실제 application T 불일치/다른회원 거절 |
| legacy 유지선택 해제 | 명시 decline에서 해당 T choice만 종료, C 무변경 | 실제 N assignment가 있으면 취소 확인 필요 |
| N 확정 참가 취소 | 전체 묶음 N assignment/점유/해당 예약 해제, N decline 이벤트 기록 | 부분 묶음 취소 불가, 책임자 규칙 유지 |
| 전역 탈퇴/추방·해산 | 전역 영향 context로 모든 유지 T를 표시하고 기존 권한 처리 | N 취소 UI에서 전역명령 호출 금지 |
| N 캐릭터변경 | 대상 T 미완료 묶음만 CAS·새 자격 검증 후 원자 변경 | 실패 시 이전 N 캐릭터/예약·C 보존 |

취소는 방 persistent membership을 유지하므로 그 방 한도를 자동 회수하는 명령이 아니다. 한도 회복은 별도 전역 탈퇴/추방/해산이다. 전역 관계의 무제한 잔류 정책을 추가하지 않으며 현재 유지 관계10개 제한을 그대로 적용한다. 같은 Round/member 재참가 시 기존 UNIQUE 때문에 무조건 INSERT하지 않는다. 취소된 Assignment는 명시 재참가 검증 후 같은 ID를 재활성화하고 각 구간은 이벤트에 남긴다. 완료된 assignment를 이 방법으로 부활시키지 않는다.

## 4. C — 시간·완료·06시 전환

- `playable_from(T)=T 수10시`, 시작 하한은 `ceil5(max(playable_from(T), stored search_floor_at, server_now))`. search_floor_at=실제 승인된 개시시각+30분은 저장값이며 worker 실행시각으로 밀지 않는다. cycle 끝 이내/정비/전체 진행기간 합계도 검사한다. 수요일00~06시 날짜 해석은 실제 대상 cycle 안의 날짜를 찾아 검사하고 단순 요일 offset이 이전 cycle을 가리키지 않는지 시험한다.
- 미래 일정 확인/시간예약은 허용한다. actual 날짜 시간으로 모든 관련 방 예약과 비교, 명시 겹침 경고/자동 후보 회피 정책 유지. 미래 '참가 확정'과 '일정 확인'은 별개 상태다.
- N은 회차 state open + temporal phase future. 수06시에는 같은 UUID/assignment/예약을 유지하고 activation_revision만 멱등 전환/재검사한다. worker가 지연되어도 요청 시 DB시간으로 권한을 계산하며 worker 성공을 완료 권한의 유일한 근거로 삼지 않는다.
- 이전 C의 active assignment만 주차 마감. N의 제안은 created_at이 이전 C라는 이유로 폐기하지 않는다. Proposal/ResumeProposal/Session은 연결 T 기준으로만 마감한다. old cleanup의 무조건 drop_membership/end_participations 전역 호출도 교체한다.
- 소유권/자격/한도 변경은 해당 T의 review/blocked reason으로 보이며 무단 다른 캐릭터 배치/재가입하지 않는다. 기존 원장 점유를 자동 해제해 타방이 차지하게 하지 않고 명시 변경·취소·전역 정리를 제공한다. 한도 초과 제한과 조회/탈퇴/추방 회복은 유지한다.
- 중복 worker·명시개시는 (room,T) 및 item/T applied opening을 직렬화하고 한 번만 처리한다. 전환 전에 시작해06시를 넘긴 새 명령은 rollback/CYCLE_CHANGED, 이미 확정한 원키 ACK는 새주차 검증 전에 복구한다.

| 완료 명령 | 주차/시각 guard | 자료 효과 |
|---|---|---|
| 개인 수동체크 true/false·난이도 정정 | T=C AND now≥수10시 | manual source만 변경, party source/다른 T 불변 |
| 개인 raid 완료 | 동일 | 본인 target assignment/해당 원장·예약만; 다른 T 종료 금지 |
| 공대장 item 완료 | 동일 + 기존 공대장/target | 해당 Round assignment·party source; N 무변경 |
| 이번주 미완료종료 | 동일 + 기존 실제 참가자/함께하기 권한 | T의 미완료만 종료, 완료 이력/N 보존 |
| 과거/미래 완료/정정·취소 | 금지 | 과거 조회만. 기존 party 완료 취소 기능은 새로 추가하지 않음 |
| N 예정 취소/신청 철회/전역 방 정리 | 완료10시 guard 적용 안 함 | 완료 위조와 구별; 기존 전역 책임자·해산 조건 유지 |

새 오류 제안: T=N 완료→409 `TARGET_CYCLE_NOT_CURRENT`, T=C 06~10→409 `PLAY_NOT_STARTED`(`available_at` 제공). permissions는 동일 predicate를 사용하고 `next_change_at`에10시를 제공해 stale true/false 캐시를 피한다. 10시에 context/permission 재조회가 가능하며 상시 polling 요구는 없다. 개인 마지막 완료는 N을 자동 가입/취소하거나 방 전역 탈퇴시키지 않는다. 이미 N참가가 있으면 유지하며, 미선택이면 다음주 참가 action을 별도로 제시한다. 기존 continuation_resolution keep를 새 미래가입으로 조용히 변환하지 않는다.

## 5. D — 한도·통계

- 한도: 현재 유지 `(user,room)` 고유 수, 기본10. C/N 또는 생성자 중복0. 새 N 다른 방은 한도1, pending 신청은 기존대로 점유/확정참가 아님. RoomCycle 실제좌석 수와 전역 유지 membership 수를 분리한다. 한도 축소 상태에서도 조회/취소/탈퇴 회복을 허용하되 새 진행 제한을 우회하지 않는다.
- #19 전체1번째 Flutter 검토까지 확인했다. 주간 원천·정책은 별도 주제이며 집계 API/DB를 이 변경에 포함하지 않는다. 시간에 따른 membership만으로 주간 모집 이용을 계산하면 미리 참가한 N이 C에 혼입되므로 실제 assignment의 target와 유효 구간을 사용해야 한다.
- 제안: N 사전 확정은 N의 prospective 원천, C 이용0. T가 실제주차가 된06시에도 유지 중이면 T effective 이용으로 편입. 주차 시작 전에 전부 취소된 사전참가는 취소 원천을 보존하되 실제주차 이용에는 불산입. 시작 후 한 번이라도 확정 참가했다면 이후 취소해도 `(user,room,T)` 이용을 보존한다. 반복 같은 room은 실제 새 방 생성0. 작성 wall-clock cycle와 target cycle는 별도로 저장한다.
- 위 취소전환 기준은 '한번이라도 확정 참가한 고유방'을 **실제주차와 겹친 유효 참가**로 해석한 기술 제안이다. 사전 확정 후 시작 전 취소도 N 이용으로 셀지는 #19에서 제품 결정을 분리해야 하며 확정했다고 보고하지 않는다. 원천 둘 다 보존하므로 모집 구현을 막지 않는다. type 분류/함께하기 마감값 등 #19 미확정 정책도 그대로 남긴다.

## 6. E — wire·오류·호환 제안

### 버전과 공통 scope

v1 expected_cycle_key의 '실행 시 실제 현재주차 기대값' 의미와 현재 응답을 유지한다. 두 주차를 명시하는 모집 계약은 **/v2**로 분리 제안한다. 기존 v2 계정 bootstrap과는 독립 경로다. 별도 검토용 OpenAPI `docs/design/issue13-two-cycle.openapi.json`은 신규 공통/계속참가/취소/주간summary의 정확한 schema 초안만 담는다. 전체 기존 모집 endpoint 전환 명세는 아래 변경표로 검토한 뒤 구현 단위마다 보충한다. 원본 `openapi/openapi.yaml`은 이번에 수정하지 않는다.

- GET 모집 자원은 `target_cycle_key` 필수, null/생략 없음. 검색/모든 회차 쓰기는 body에 actual T 필수. T형식은 정규 ISO수요일 date, C/N 이외 새 조회/참가는400 TARGET_CYCLE_OUT_OF_RANGE(과거 종료기록은 기존 별도 history 계약).
- 쓰기에는 `expected_cycle_key`(실제 C 기대), `target_cycle_key`, `expected_target_revision` 필수. 생성처럼 기존 target가 없는 경우 expected_target_revision은 명시 null. 읽기 scope의 `target_revision`은 아직 미개시인 경우만 null. null과 생략을 혼동하지 않는다.
- 단일 target의 신규 context/명령 응답은 `scope`와 `data`로 구분한다. 목록·detail 등 기존 모집 응답의 전체 wrapper 전환은 소비 대조 후 고정한다. metadata와 복수 target summary는 별도 schema로 실제 키들을 직접 제공한다. scope: server_now,current_cycle_key,target_cycle_key,playable_from,phase(future|current),target_revision nullable,policy_version. 구버전 body를 그대로 v2에 전달하지 않는다.
- token/커서는 actor/session에 따른 권한 범위·room/명령·T·target/config/member/plan/그룹/소유/한도·catalog revision을 결합한다. 같은 그룹필터 context는 주차를 바꿔도 그룹 권한이 같으면 재사용한다. N이C가 되면 old cursor는 명시409 CURSOR_STALE로 재시작, 방 UUID/T는 그대로다.
- 숫자 revision은1..2147483647 strict integer(boolean/float 거절), UUID/date는 정규형, 모든 객체 unknown key400. token/context expiry120초·최대4096, cursor 최대2048. no-store. auth는 기존 회원세션이며 본인만 continuation·weekly summary 요청 가능.

### 기존 API 전환 영향표 (모두 v2 제안, 단순 prefix 치환만으로 구현되지 않음)

| 대상 | 정확한 변경·revision 출처 |
|---|---|
| GET /v2/raid-cycles | server_now,C/N key/starts/ends/playable_from/permissions/next_change_at, policy_version. 기존 /v1/raid-cycle 불변 |
| creation-context / POST raid-rooms | T query/body, 현재 C 기대는 별도, target의 WeeklyState revisions·선택 context. 생성201 ACK resource room+RoomCycle revision |
| search / GET list·room summary | T 조건→가시권한/raid·난이도·그룹회원/캐릭터→자리→정렬→SQL page. sort wire는 member_count 유지, 값은 target 실제 확정 인원으로 변경(명시 v2 변경). inactive global member/legacychoice 제외 |
| detail / plan / member-projections | T round/assignment·현재 소유 비교·해당 캐릭터만. settings_revision/members_revision/plan_revision은 RoomCycle에서, global room_revision은 Room에서 별도 |
| admission-context / join / applications / approve·reject·withdraw | application 자체 T, round/weekly CAS·실행 C 기대, scope T 불일치 거절. external 일반 승인제 보존 |
| GET me memberships / applications | T필수, page≤50/default20, cursor nullable. current/ended 전역 membership과 target participation_state를 별도 표시; N pending/legacyselected/confirmed/review 구분 |
| availability-submission / schedule-context / groups/candidates/selections | T필수·RoomCycle plan/submission revision. 개인표 저장은 기존 API 그대로 |
| session participant·confirmation / proposal responses / resume | 경로 ID가 가리키는 T와 body T 일치, target 계획/세션 revision. 투표분모·N1/확인/예약 기존 규칙 |
| command-context / item·personal complete / incomplete closure | target-bound120초 AEAD·10시 permission. 기존 opaque 타인원장 CAS 보호 유지 |
| settings / formation / character-changes | T snapshot/members/plan/assignment CAS. 캐릭터변경에서 모든 futurechoices 동시수정 제거 |
| visibility / leadership / leave / removal / end | 전역 명령. 영향 context에 C/N 관계와 원장/예약별 effect 명시, global revision. N cancellation과 분리 |
| continuation-settings / recruitment-openings | 공대장 global setting CAS+target개시 CAS, 이미 열린 T noop. 자동 참가자 생성 없음 |
| POST /v2/me/raid-weekly-summary | 읽기 전용 bounded batch. 아래 계약 참조 |

주간summary body는 character_ids 고유1..50, target_cycle_keys 고유1..2(각 C/N) 모두필수, null 없음. 출력 최대50×2×카탈로그 raid수(현재5=500) entries. 각 entry는 character_id/raid_id/T/weekly_revision/ownership_revision/lifecycle_revision, completion_sources[], participation nullable, continuation_state, permissions를 분리한다. 실제 참가 i는 participation의 room_id/round_id/assignment_id만으로 표시하고 유지선택은 i 없음. party/manual 완료 source와 참여를 boolean 하나로 합치지 않는다. bootstrap·캐릭터·장비/Armory를 다시 읽는 API가 아니다. 본인 소유 아닌 character가 섞이면 전체403, 부분 성공/빈데이터로 은폐하지 않는다. 허용된 방 권한이 사라진 경우 room 제목 등 최소안내는 null/restricted로 제한한다.

### 오류/재시도

기존 인증401/권한403/존재숨김404·자격/자리/한도409·입력400/속도429·장애503를 유지한다. 신규 code는 검토용이며 기존 공통 오류 envelope 안 `error.code`로 전달한다.

| code/status | 의미·다음 동작 |
|---|---|
| TARGET_CYCLE_OUT_OF_RANGE /400 | 형식 또는 지원 C/N 밖. 자동 +7일 보정 없음 |
| TARGET_SCOPE_MISMATCH /400 | body/경로 round/session/application T 불일치, 쓰기0 |
| SOURCE_PARTICIPATION_REQUIRED /403 | 실제 소스 참가·유지 권한 소멸. context 재조회/일반 admission만 가능 |
| TARGET_CHARACTER_CONFLICT /409 | 본인 다른방 동일raid/T 점유. 최소 conflict 안내, B 변경 없음 |
| TARGET_CYCLE_NOT_CURRENT, PLAY_NOT_STARTED /409 | 완료 금지. available_at(T수10시), 새 권한 조회 |
| TARGET_CONTEXT_STALE /409 | target/source/선택/token의 snapshot 변경. 초안 보존·context 새로 조회/명시 재확인 |
| COMMAND_CONTEXT_EXPIRED /409 |120초 또는06시 expiry, 원 성공 ACK가 없으면 재확인 |
| CLIENT_UPGRADE_REQUIRED /409 | legacy 명령이 미래 관계까지 잘못 수정할 위험. 새 UI 필요, 자동 재시도 금지 |
| CYCLE_CHANGED /409 | 기대 C/DB 경계 변경. T는 자동 변경하지 않고 현재 metadata와 새 context |
| CURSOR_STALE, FILTER_CONTEXT_STALE /409 | 페이지·그룹 scope 재조회, 멤버별 local 재정렬 금지 |

conflict는 새 top-level 민감 payload 대신 `error.details` 확장 제안으로 actor 소유 최소 `{room_id,target_cycle_key,raid_id,character_id,can_view_detail}`를 제공한다. 여러 raid 충돌은 최대 bundle item수까지 반환하고 title/다른 회원UUID/원장revision는 노출하지 않는다. 세션이 유효해도 현재 B 조회권한이 없다면 can_view_detail=false·room_id=null로 표시하고 별도 본인참가 복구경로를 제공한다. 기존 공통 오류 schema의 확장이므로 consumer 대조 후 명세에 반영한다.

### v1 호환·전환

- v1 읽기는 현재 C 투영을 유지, 미래의 최신 assignment/인원이 섞이지 않게 adapter로 수정한다. 과거 경로·필드 삭제 없음. 개인표·계정 bootstrap·catalog API는 불변.
- v1 쓰기는 결과 replay를 먼저 처리하고 안전한 current-only adapter를 통과한 경우만 실행한다. 미래 관계가 있는 방의 전역파괴/캐릭터변경/keep→자동참가 같은 구버전 의미는409 CLIENT_UPGRADE_REQUIRED. v1 전체 기능이 무조건 호환된다고 주장하지 않는다.
- 10시 guard는 사용자 확정 정책이므로 v1 수동완료와 v2에도 동일 적용하며 소비 변경/적용 순서를 인계한다.
- legacy Choice는 보존 읽기 `legacy_intent`로 표시, actual N참가로 자동 전환하지 않는다. 사용자가 새 context로 재확인했을 때만 같은 transaction에서 choice 종료+실제 참가. 이미 N assignment가 있다면 actual관계를 우선/noop. worker 자동입장 중단과 신규경로 공개를 같은 전환 단위로 처리한다.
- 같은 요청키의 기존 성공 ACK 형식/operation을 재작성하지 않는다. 새 계약은 별도 operation version이며 24h 결과불명 복구 정책을 보존한다. ACK는 현재 권한이 허용한 최소응답만 제공하고 타인 세션 replay는 금지한다.

## 7. F — 보존 이행·성능 측정·구현 순서

### 이행

1. 원격/로컬 최신 SHA·migration head·실제 자료를 먼저 읽기 점검. 실제 자료가 생겼으므로 과거의 '모집0건'을 현재 보존 근거로 재사용하지 않는다.
2. additive 구조/nullable target 열·index를 만들고 기존자료/시각·원장/원ACK를 보존. target는 실제 Round FK에서 유일하게 증명한 값만 backfill. 여러 T 혼합/빈 targets/기간 불명은 review, 임의 C 대입/미래 복제 없음.
3. RoomCycle별 기존 Round/Assignment/스케줄을 분류, 이미 열린 회차에만 설정 스냅샷. 과거 설정 변경 이력이 없으면 '현재값으로 과거 설정 복원'을 주장하지 않고 provenance unknown/review. legacy 제출표 원본은 삭제 안 함.
4. 보존 검증 뒤 FK/NOT NULL/partial unique 제약 적용, readiness 새 revision, v1 target-safe adapter와 새 worker 동시 전환. 일부 adapter만 게시하지 않는다. destructive downgrade/자료 삭제 대신 신규쓰기 중지와 읽기/정리 보존 경로를 준비한다.
5. 원본 OpenAPI는 합의된 구현 단위만 반영하고 실행 전체 비교. 격리 테스트/보존 검증→묶음 커밋·push/원격 SHA 확인→네이티브 인계. 실서버 DB 이행/이미지 반영은 구현 인계와 별도 승인 범위를 확인한다.

### 측정 계획 (아직 미측정)

- baseline cc003e9와 새 코드에서 동일 합성 데이터/환경으로 public target 첫·후속 페이지, 50캐릭터×C/N summary, own membership/application, detail/plan, 마지막자리경합,06시 backlog를 측정한다.
- 데이터축: 빈데이터/대표1천·1만 room, C/N 동시비율·공개/그룹/종료 혼합, 정원4/8·다중 item/session, 회원별10방, 장기이력. 로컬실자료 복제 대신 합성하고 정책 경계의 마지막자리8→9 경합도 분리한다.
- SQL 개수(페이지 방수에 비례하는 N+1 여부), DB 실제 rows/buffers, UTF-8 응답bytes, p50/p95·최대 지연/메모리, query별 EXPLAIN(ANALYZE,BUFFERS)을 격리 DB에서 수집한다. 첫/반복/warm/cold·표본수/환경을 기록하고 측정전 ms/2배·0비용을 보장하지 않는다.
- 후보 인덱스: RoomCycle(cycle,state,room), Round(room,cycle,item,active generation), Assignment(round,state,membership)/(user,round,state), Application(user,target,state,created_at,id)/(room,target,state), cycle submissions(member,cycle), events(user,target,room,effective_at). 기존 PK/FK/slot/occupancy 인덱스와 중복 제거 후 실제 EXPLAIN으로 채택한다.
- 공개목록은 SQL에서 먼저 T/조건·자리/정렬/page≤50 적용 후 선택된 room의 settings/items/멤버를 각각 bounded batch로 읽는다. 현재 card 반복 db.get/각방 queries는 그대로 두고 요청수만 줄인 것으로 성능 완료라 하지 않는다.
- 내계정은 단일 RR snapshot의 bounded 최소 summary를 우선. 처음부터 C/N 전체 detail 선조회 없음. 대안은 같은 endpoint에 한 T만 보내는 lazy(두 탭 왕복 요청은 늘지만 초기 rows/bytes 감소). 두 방식 실제 측정 후 선택. 내참가/신청 페이지도 최소카드 batch를 재사용하되 public목록과 권한 캐시는 분리한다.

### 작은 구현 구간·준비 상태

| 순서 | 작업·완료 조건 | 현재 상태 |
|---|---|---|
| W0 | 이 설계/신규 core schema·A~F 소비 대조, auto UI/legacy완료 충돌 정리 | 이번 작성·회신, 소비검토 전 |
| W1 | RoomCycle/target 보존 이행·명시 resolver/원장·멱등 기반/10시 predicate, 구 worker 격리 | 구현 전. 단독 기능 공개 금지 |
| W2 | metadata/계정 summary/생성·search/detail/plan target 읽기와 C/N 일반 admission | 전체 해당 DTO·OpenAPI 고정 후 구현. C/N 멤버·자리/필터 격리 시험 |
| W3 | 기존인원 즉시참가·대체캐릭터·충돌·decline/취소/target캐릭터변경 | W1/2 기반, bundle·source경합·무변경 검증 |
| W4 | target 일정/투표·확인예약/완료·재개·全域관리·06시worker/legacy adapter | C보존/원ACK·10시 경계/중복worker 검증 |
| W5 | 성능/보존 통합·원본OpenAPI 전체대조·커밋push/원격확인·네이티브 단계별 인계 | 미실행, 최소안이라도 전체 경계 검증 후 게시 |

W1~W4는 별도 내부 커밋이 가능하지만 불완전한 multi-cycle API를 실행서버에 먼저 노출하지 않는다. 실제 구현/DDL·최종 schema 고정이 완료됐다고 보고하지 않는다.

필수 검증: 임의요일 N허용/C+14거절, C완료→N참가, 동일A/T noop·다른T동일키409, source 탈퇴/추방·대체캐릭터vs외부우회,8인 마지막자리동시승인, B불변/A점유0/실패미선택, N취소·변경실패의C보존, 묶음부분rollback·재참가, future/06~10 완료·수동정정거절/10시해제, 현재완료후N유지, target형식/위조/다른회원, C/N group가시권한과target역할, 같은room한도중복0,06시중복worker·미래제안보존/원ACK replay,예약/통계혼입0, v1 upgrade guard·기존choice보존, 자료지문·FK·실행계약·성능.

## 8. Flutter 소비 대조와 남은 정책 구분

기존 확정 제품정책을 다시 질문하지 않는다. Flutter는 (1) v2 scope/오류details·신규명령 소비 가능 여부, (2) 기존 자동모집 UI를 자동잔류로 오해하지 않도록 변경 가능 여부, (3) 마지막 개인완료의 기존 keep/release 대화가 N을 자동가입/전역탈퇴하지 않도록 변경 가능한지, (4) 주차별 최소summary/lazy 대안을 대조하면 된다. OFF 뒤 이미 확정 N관계 보존/기존 소스 권한과 공대장 승계는 위 구체안을 기준으로 검토한다.

새 제품 판단이 남는 것은 사전 확정 뒤 주차시작 전 전부 취소된 참가를 통계35에 넣을지(#19 미확정)다. 원천 보존과 모집 기능 설계는 독립 진행한다. 현재 설계 검토 회신이며 Flutter 구현 시험/실회원 생성 반복/배포/이슈 종료 요청이 아니다.

검토용 core 명세는 7개 경로/7개 operation이다. 계속참가/불참/취소는 Idempotency-Key 필수, summary POST는 읽기 전용이며 이 헤더가 없다. continuation context는 action=join 기본/decline 명시, 대체 캐릭터·역할 두 query는 함께 제공한다. 새 명령의 body는 expected_cycle_key/target_cycle_key/expected_target_revision/context_token 모두필수이며 참가에만 selection/target_items/target_session_ids를 더한다. 아직 대상이 준비되지 않은 context는 targets=[]/permission=false로 표시할 수 있고 참가 명령은 빈 target_items를 받지 않는다.

문서 검증: JSON parse/내부 $ref 해석, 27개 schema의 JSON Schema2020-12 메타검증, 7 operation ID/필수 path parameter 검사를 통과했다. OpenAPI 전용 validator는 이 환경에 없어 실행하지 않았으며 이는 실제 FastAPI 계약 비교/기능·DB 테스트가 아니다.
