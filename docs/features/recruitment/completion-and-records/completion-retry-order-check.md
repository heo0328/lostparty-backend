# Issue17 완료·개인 완료 재확인과 지연 요청의 도착 순서

2026-11-10 현재 결과: [완료 오류·계정 복구 인수/Native 게시](completion-recovery-acceptance-20261110.md) 완료. 기존 계정은 문구 수정 전에 복구됐고 사용자 기기 테스트 통과, Native 구현5df515f push가 확인됐다. 아래 조사·회신의 복구 미확인/기기 대기·Native 미게시 표기는 당시 기록이며 현재 대기가 아니다. 누락 캐릭터/부분 완료 자료·기기 검증과 일괄 완료 기획은 별도 미완료다.

2026-11-09 / Backend / feat/character-lifecycle / 소스 f744a1e(구현16c9cd4). [Native 전체41번째의 좁힌3흐름](https://github.com/heo0328/lostparty-backend/issues/17#issuecomment-6738162109)에 답한다. 서버 변경이나 새 API·fence·복구 큐·다중 저장 확대는 하지 않는다. [이전 포괄 조사](pending-recovery-and-conflicts.md)의 추가 계약 제안은 이번 선행 조건이 아니다.

## 1. 완료로 재조회되면 화면에 반영 가능

같은 room·실제 target_cycle_key·generation/round_id의 상태를 표시한다. 개인 완료는 본인의 해당 assignment 완료, 공대 완료는 해당 round 완료를 구분한다. 본인만 완료됐다고 round 전체 완료로 표시하거나 개인 주간 합산 상태만으로 특정 모집 참가 완료를 추정하지 않는다. 캐릭터 교체가 있는 경우 현재 선택과 해당 completed assignment 이력도 구분한다.

[plan 조회](../../../../app/raid_rooms/reads/cycle_member_reads.py)의 game_items[].round_state와 my_assignments[].state/assignment_id/round_id 등 해당 계약의 근거로 최신 상태를 표시할 수 있다. 이 표시가 원요청의 성공 ACK 합성·성공 이벤트 재발행·pending 자동 삭제를 허용하는 것은 아니다. 이미 신뢰 가능한 성공 ACK가 있다면 후속 GET만 복구한다. 조회 실패는 기존 ACK 성공을 뒤집지 않는다.

## 2. 미완료 GET 후 두 key의 완료 요청이 도착하면

A=원요청, B=같은 대상·같은 완료 종류를 새 context로 사용자가 재확인한 가정상의 새 요청이다. B 전송은 현재 Native의 저장 slot/원pending 삭제를 허가하는 결정이 아니다.

[실행](../../../../app/raid_rooms/common/cycles.py)은 game mutation transaction lock으로 직렬화된다. [완료 처리](../../../../app/raid_rooms/outcomes/cycle_outcomes.py)는 token의 actor/room/T/command/round·profile/만료, 현재 round/generation, target revision/CAS·현재 snapshot digest와 권한을 확인한 뒤 **active assignment만** 완료한다. 성공은 target/plan/members revision과 관련 상태를 바꾼다([CAS](../../../../app/raid_rooms/admissions/cycle_commands.py), [bump](../../../../app/raid_rooms/schedules/cycle_planning.py)).

| 순서 | 현 검증의 결과 |
|---|---|
| A/B context 모두 미완료 S0에서 발급 → A 성공 → B 도착 | A가 바꾼 target revision 때문에 B는409 TARGET_CONTEXT_STALE. B의 완료 효과 없음. |
| A/B context 모두 S0에서 발급 → B 성공 → 지연 A 도착 | 반대로 A가409 TARGET_CONTEXT_STALE. A의 완료 효과 없음. |
| A가 이미 완료 → 성공 응답 유실 → B의 새 context GET | 같은 종류/대상은 완료 대상 없음으로 permission.allowed=false/ROUND_NOT_ACTIVE. 이때 새 명령을 만들지 않고 현재 상태 표시/기존 복구를 따른다. |
| 원 A가 성공했고 원 method/path/query/body/key 재전송 | 보관·인증/route 조건이 맞으면 원ACK 재생. 현재 token 만료/완료 상태 재검증보다 우선하며 완료를 중복 적용하지 않는다. |
| token 만료·주차/권한/편성·캐릭터·대상 세대 변경 | 기존 만료/권한/scope/CAS 검증으로 거절할 수 있다. 정확한 첫 code는 먼저 걸리는 검사에 따라 다르므로 모든 상태에 TARGET_CONTEXT_STALE만 약속하지 않는다. 새 대상/다른 T로 자동 연결하지 않는다. |

첫 두 행은 ‘먼저 발급된 context’가 아니라 **먼저 commit한 명령**이 이긴다는 뜻이다. 같은 active assignment를 두 번 완료하는 우회는 이 두 key 경합으로 생기지 않는다. 그러나 사용자가 B를 보냈다고 지연 A의 실행을 취소하거나 B만 승리하게 만들지는 않는다. GET이 미완료를 반환한 직후 A가 성공할 수도 있다.

## 3. 의도가 다른 완료가 가능한 구체 경계

- **A는 공대 완료, B는 개인 완료:** 같은 S0에서 준비한 경우 A가 먼저 commit하면 해당 round의 다른 참가자들도 완료된다. B는 stale로 거절된다. B가 먼저 성공하면 옛 A는 stale로 거절된다. 이것은 중복 완료가 아니라 원 공대 명령이 먼저 실행된 결과다. ‘창을 닫은 뒤 개인 완료만 원했으니 원 공대 명령도 취소’는 현 지원이 아니다. 취소가 안내 종료라는 합의를 유지한다.
- **A 개인 완료가 성공 → 다른 참가자들이 남은 round에서 새 공대 context:** 실제 공대장 권한이 유지되면 새 context는 나머지 active assignment를 대상으로 allowed=true일 수 있다. 사용자가 그 scope를 새로 확인해 공대 완료를 보내면 나머지 참가자가 완료된다. 본인의 기존 completed assignment는 다시 완료/변경하지 않는다. 이 새 공대 요청을 ‘개인 완료 재시도’로 자동 대체하면 의도와 다른 영향이 생긴다.
- **A 공대 완료가 성공 → 같은 round의 새 개인 context:** 본인 active assignment가 없으므로 새 개인 완료는 허용되지 않는다. 다른 round/새 generation에서 allowed=true인 context를 얻어도 그것은 다른 대상의 새 결정이지 옛 요청 복구가 아니다.

따라서 같은 종류·실제 대상에 대한 중복 완료는 기존 token/CAS/active 상태로 방지되지만, 완료 종류/대상을 바꾸어도 옛 요청이 실행되지 않는다는 보장은 없다. 버튼은 기존 원 명령의 종류/round/T를 바꾸지 않아야 한다. 새 context의 impact/permission은 사용자 재확인의 현재 범위이지 원pending을 덮어쓸 자료가 아니다.

## 이번 범위에서 충분한 기존 흐름과 남는 한계

**추천:** 짧은 안내·첫 오류 취소·해당 창의 표시 수명 분리와 보정 profile 연결을 진행한다. 원pending이 온전하고 기존 재시도 조건을 충족하면 기존 원요청 재전송/ACK 복구를 사용한다. 현재 상태 표시를 위한 GET, ACK 성공 이후 GET만 재시도는 그대로 가능하다. 별도 서버 변경은 이 범위에 필요하지 않다.

GET만으로 원pending 정리·무조건 새 key 발급, 기존 slot을 유지한 채 다른 original 저장, 원 공대 명령을 개인 명령으로 대체·지연 명령 철회, 장기/손상 원요청의 자동 복구는 여기서 지원/승인했다고 표시하지 않는다. 이 한계는 새 API 설계로 확대하지 않고 남겨 둔다. Native는 실제 저장/transport를 유지하는 범위에서 연결·안내를 구현하고 구체 차이만 회신한다.

## 검증과 인계

소스/계약 대조와 격리 PostgreSQL0036 fixture의 실제 HTTP **6PASS/96.21s**를 확인했다. 공대/개인 완료×같은 종류 두 key 양순서4개와 개인→공대/공대→개인2개다. 같은 종류4개는 원ACK 재생·다음주 my_assignments 보존도 확인했다. 시험 project lostparty-check-f50f84030ca1의 exit0/DB·network cleanup0이며 임시 시험 파일은 작업 트리에서 제거했다. 조사 원본은 /tmp/lostparty-recovery-design/test_issue17_retry_probe.py, SHA256 253ebedd1f5f04898b047411ca88ffd575ff27decfd07e26190b02c1519270ac다. 최초 준비 실행은1PASS/5FAIL(115.16s)로, permission 응답의 기존 next_change_at=null을 예상 dict에서 누락한 단언 문제였다. 해당 필드를 현재 계약과 일치시켜 재검증6PASS로 해소했다. 중간1PASS를 최종6개에 합산하지 않았고 제품 코드/계약은 변경하지 않았다. 임시 시험은 두 도착 순서의 순차 재현이며 실제 네트워크 지연/유실·새 키 병렬 부하·기기 시험을 뜻하지 않는다. 기존 동시 완료·완료/교체 경쟁 시험은 [기존 보정 검증](completion-profile-contract-fix.md)의 근거와 분리한다. 서버/업무 코드·저장 계약·실제 개발 DB/로컬 API를 변경하지 않는다. 새 contract/profile 보정·일괄 회귀를 반복하지 않는다.

공식 인계: [전체42번째 Backend 완료 경합 확인 회신](https://github.com/heo0328/lostparty-backend/issues/17#issuecomment-6738491069)을 게시했고 전체 댓글42개/본문 일치를 재조회했다. Issue 상단 범위/상태/다음 담당도 갱신했다. 다음 Native의 이 범위 내 구현·자동 검증/사용자 기기 확인이며 Backend는 구체 차이에 대응한다. 이번 문서는 미커밋·미push이고 commit/push·배포·Issue 종료는 없다.
