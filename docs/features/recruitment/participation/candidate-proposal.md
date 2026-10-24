> 제안1 보관 기준: 이 문서의 신청 전용·전투력 후보제외 밖 범위는 [#26 전체3번째 Flutter 최신 확정](https://github.com/heo0328/lostparty-backend/issues/26#issuecomment-6381254676)으로 대체됐습니다. [전체4번째 Backend 검증 차이 회신](https://github.com/heo0328/lostparty-backend/issues/26#issuecomment-6381295804) 이후 [보완 계약2](candidate-contract.md)를 새 검토 기준으로 작성했으며, 이 제안은 실행 API가 아닙니다. 현재 담당/상태는 [NEXT_WORK](../../../project/NEXT_WORK.md)를 따릅니다.

# 신청 자격 검증·본인 캐릭터 후보 조회 제안1

2026-10-24 / Backend / feat/raid-recruitment. **읽기 계약 제안·미합의/미구현**, 실행176경로·DB0031에는 추가하지 않는다. 원본 #13 전체142/143번째 Flutter 요청과 사용자의 승인 계획을 따른다. 신청 구성 검증 보완은 기존 계약의 누락 수정이며 별도 진행한다.

## 확정 정책과 책임

사용자 확정 제외 기준은 선택 실제T/raid의 레벨미달, 확정 파티 구성 불가, 개인 또는 파티 완료, 다른 모집방 실제참가 중이다. 묶음 중 하나라도 해당하면 불가다. 전투력·회원 한도/동일방 관계·신청 중·일정 기한 등은 후보 제외를 확장하지 않고 기존 선택 후 context에서 안내한다. 후보 포함은 전체 신청 권한 보장이 아니다.

역할 dealer/support를 기존 명령과 동일하게 각각 판정한다. 직업명으로 신규 역할 제한을 만들지 않는다. 허용 역할이 하나 이상이면 후보 유지, UI 선호역할은 허용 범위에서만 사용하며 불가 역할을 자동 허용하지 않는다.8인은 파티1/2 중 유효한 배치가 있으면 유지한다. 단일8인/묶음4인이라는 현행 제약을 유지한다. pending끼리의 동일직업은 제한하지 않고 점유/예약도 만들지 않는다.

## 기존 조회 재사용 검토

본인 원정대 캐릭터 조회는 room/T가 없고, 그룹 후보조회는 그룹원 공개범위/검색 목적이라 대체할 수 없다. 기존 admission-context는 한 캐릭터/역할을 선택한 뒤 토큰·selection·동의/전투력까지 제공하므로 목록 N회 조회용으로 사용하지 않는다. 본인 인증/활동/canonical 조회와 레벨·WeeklyState/WeeklyOccupancy·확정 Assignment를 일괄 적재하고, 기존 레벨/주간 가용성/읽기 전용 구성 판정의 같은 규칙을 적용한다. 선택 후에는 기존 context/신청/승인에서 재검증한다.

## 제안 인터페이스

`GET /v2/raid-rooms/{room_id}/application-character-candidates`

- 인증 필수, path room UUID. 필수 query `target_cycle_key`: 기존 C/N 실제 날짜. 선택 `limit`: 정수1~100/기본50, `cursor`:1~2048문자. 알 수 없는/중복 query·GET body는 기존 방식400. 다른 회원/방/T나 위조 cursor400 INVALID_REQUEST, 관련 상태 변경409 CURSOR_STALE. page limit은 snapshot 범위에 넣지 않는다.
- 기존 room 접근권한과 open/explicit 실제T resolve를 재사용한다. 비공개 다른방404, 닫힌/미확정T는 기존 reason/409이며 후보0으로 숨기지 않는다. 신청모드가 아닌 방은409 ADMISSION_MODE_CHANGED. 현재 개인 본인 자료만 응답하고 다른 참가자 개인정보/공개회원 식별자는 추가하지 않는다.
- 응답은 `scope/data`. 필수/nullable/타입은 [독립 closed JSON Schema](examples/application-character-candidates.proposal.schema.json)가 기준이다. 이 schema는 proposal artifact이며 runtime OpenAPI에는 추가하지 않는다. [합성 작성 예시3개](examples/application-character-candidates.proposal.examples.json)는 실제 서버 응답/시험 결과가 아니다.

| data 필드 | 의미 |
|---|---|
| room_id / intent | 기존 UUID / 항상 apply |
| evaluated_at / catalog_version | snapshot 서버시각 / 기존 카탈로그 version |
| snapshot_token |64자리 hex의 opaque HMAC. actor/session·room/T/세대·카탈로그·필터 기준과 후보/주간/구성 자료를 결합. 쓰기 권한 token으로 사용하지 않음 |
| raw_candidate_count | 현재 인증·등록·활동·usable 본인 캐릭터 distinct 전체 수 |
| eligible_candidate_count | 네 기준 중 역할 하나 이상 통과한 전체 수, 페이지 크기와 독립 |
| items | eligible만 character UUID 오름차순으로 페이지. character_id·registration_id·server_name·character_name·class_name·문자열 item_level·dealer/support별 Permission |
| next_cursor | 후속이 없으면 null. offset·snapshot·actor/session/room/T를 MAC으로 보호 |

Permission은 필수 `{allowed:boolean,reason:string|null}`. 허용이면 reason=null, 불가이면 기존 RAID_ITEM_LEVEL_REQUIRED/WEEKLY_ALREADY_COMPLETED/WEEKLY_ALREADY_PARTICIPATING/ROOM_FULL/ROOM_COMPOSITION_CONFLICT 중 하나다. whole-character 제외는 응답 items에서 빠지고 count로 집계한다. 제외된 타인/캐릭터 이력을 추가 공개하지 않는다.

각 역할의 사유 우선순위는 레벨→완료→점유→구성이며 묶음 레이드는 item UUID 순으로 안정 정렬한다. 레벨은 각 difficulty 기준과 비교한다. 완료는 WeeklyState의 manual_completed_at 또는 party_completed_at, 점유는 기존 가용성 검사와 lease 모두 확인한다. 현행 context와 동일하게 같은방 실제참가도 신청 후보가 아니며 점유로 제외한다. WeeklyState와 lease가 불일치하면 기존 ROOM_REVIEW_REQUIRED409로 전체 실패하고 자동 복구/빈 후보로 바꾸지 않는다.

본인 source가0이면 counts=0/items=[]/cursor=null, 필터후0이면 raw>0/eligible=0/items=[]/cursor=null. 판정에 필요한 class/level/레이드 정의가 누락되거나 수준값이 유한 숫자가 아니면 CHARACTER_DATA_UNAVAILABLE409(카탈로그 불일치는 기존 코드), DB 장애503으로 전체 실패한다. 정상 미인증/비활동/retired는 원후보 제외이며 자료누락과 구분한다. 성공/실패 모두 no-store. 외부 provider·전투력 갱신·원장 쓰기/예약·새 토큰 저장은 없다.

본인 graph/확정 Assignment/주간 상태를 한 read-only REPEATABLE READ snapshot에서 bulk load해 전체 후보를 평가한 뒤 페이지를 자른다. 성능 검증에서 후보수 증가가 캐릭터별 SQL/context 호출 증가로 이어지지 않아야 한다. 한 페이지라도 CURSOR_STALE/실패면 Flutter는 다른 snapshot 페이지와 합치지 않고 목록 전체를 무효화한다. query epoch는 회원/session·환경·room/T에 묶는다. 조회 중/실패는 정상0건 화면이 아니다.

## 구현·검증·합의 경계

기존 pending 경로의 confirmed-party 구성검사 누락을 보완해 context·신청 POST 양쪽에서 거절한다. core의 slot 계산은 읽기 전용이며 pending은 write phase 전에 반환한다. 기존 원ACK와 승인 최종 검사·게임 mutation lock을 유지한다. 신규 후보조회는 위 계약의 Flutter 차이 확인/합의 이후에만 구현한다.

검증 범위: 레벨 경계/묶음 일부, 개인/파티 완료·다른방 점유/C/N, 같은딜러·역할정원/다른직업·8인 반대파티, context후 변경/위조POST/승인 최종검사·마지막자리 경쟁, pending의 주간/자리/예약 불변·원ACK/거절/철회, 후보count/빈화면/역할·cursor/권한·불완전자료/일괄SQL. 합성시험과 실회원/기기는 구분한다. migration·실제 개발 반영/운영은 이번 승인 범위에 포함하지 않는다.

다음 Flutter는 기존 DTO/역할선택·페이지/빈화면/비동기 경계에서 소비차이를 이 후속 Issue에 회신한다. Backend는 그 차이를 반영해 계약을 확정하고 신규 읽기를 구현한다. 같은 제품정책의 반복 수용이나 서버 반영 전 실회원 시험 요청은 하지 않는다.

계수 불변식: 0 <= eligible_candidate_count <= raw_candidate_count, 페이지 items 수 <= limit/eligible 전체 수. 같은 응답/후속 페이지에 character_id 중복이 없어야 하며 각 item에는 허용 역할이 하나 이상 있어야 한다. 사전 source/판정이 온전하지 않은 경우 부분 성공을 반환하지 않는다.
