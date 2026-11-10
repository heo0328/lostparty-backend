# BUG-033 기존 v3의 현재 서버 상태 채택·로컬 대기 해제

2026-11-10 현재 결과: [완료 오류·계정 복구 인수/Native 게시](completion-recovery-acceptance-20261110.md) 완료. 기존 계정은 문구 수정 전에 복구됐고 사용자 기기 테스트 통과, Native 구현5df515f push가 확인됐다. 아래 조사·회신의 복구 미확인/기기 대기·Native 미게시 표기는 당시 기록이며 현재 대기가 아니다. 누락 캐릭터/부분 완료 자료·기기 검증과 일괄 완료 기획은 별도 미완료다.

2026-11-10 후속 [Native 전체51번째 연결 결과](https://github.com/heo0328/lostparty-backend/issues/17#issuecomment-6742522210): 기존 v3의 실제 POST409→정확한 대상 GET→명시 현재 상태 유지로 계정 ViewModel/버튼/단일 slot 정리를 연결하고 자체전체2856PASS/analyze0을 보고했다. 누적 미커밋·미push이며 실제 사용자 계정 복구는 미확인이다. 다음은 수정 코드 재실행 후 이 복구 구간과 주차 전환/다른 레이드 조작 가능 여부만 확인한다. 실패하면 해당 복구 구간을 조사하고 정상 흐름 시험을 확대하지 않는다.

[Native 전체48번째](https://github.com/heo0328/lostparty-backend/issues/17#issuecomment-6742031537)를 확인했습니다. **이번 무옵션 v3 correction에 한해, 원문 그대로 재전송한 현재 시도가409 CLIENT_UPGRADE_REQUIRED로 차단되고 서버 GET이 성공하면, 사용자가 ‘현재 상태 유지’를 선택해 해당 로컬 대기를 끝내는 흐름을 지원할 수 있습니다.** 과거 성공/실패를 확정하거나 서버 완료 기록을 지우는 동작이 아닙니다.

앞선45번째 회신은 ‘과거 시도를 실패로 확정하는 조건’을 이번 ‘과거 결과 미확인 + 현재 상태 채택’에도 적용해 너무 좁게 안내했습니다. 이 선택에는 **최초부터 모든 과거 시도가 거절됐다는 전체 이력 증명이 필수는 아닙니다.** 재시도 반복 중단만으로 사용 복구라고 표시했던 것은 아니지만, 현재 상태 채택을 막는 추가 조건으로 삼지 않도록 정정합니다.

### 이번 건의 조건과 처리 순서

1. 같은 환경/회원의 저장된 **기존 계정 correction 원요청**을 원 method/path/key/body/token·무옵션 query로 재전송합니다. group/contract/participation 옵션을 주입하거나 다른 명령으로 바꾸지 않습니다. 이 원무옵션 형태가 해당 저장 버전의 복원/송신 경로라는 점을 Native에서 확인합니다.
2. 그 시도의 실제 응답이 **409 CLIENT_UPGRADE_REQUIRED**여야 합니다. DB0035/0036 gate가 켜져 있고 group 표식이 없는 이 경로의 거절이라는 조건입니다. 현재 로컬의 DB0036 및 gate/execute/dedup 소스3개 해시가 고정 소스와 같음을 읽기 전용으로 확인했습니다.
3. 해당 회원·캐릭터·raid·실제 주차의 기존 GET을 성공시켜 **현재 서버 완료 상태를 그대로 표시**합니다. 조회 실패·회원/환경 전환이면 대기를 조용히 해제하지 않습니다.
4. 사용자의 명시적 **‘현재 상태 유지’** 선택으로 기존 로컬 정리 경로에서 이 요청의 활성 대기/hasPending 제한을 해제할 수 있습니다. 과거 결과는 미확인으로 두고, 성공 ACK/성공 이벤트·‘미처리 확정’·‘과거 실패 확정’을 합성하지 않습니다. 해당 원요청의 자동 재송신도 중단합니다. 원문/ACK를 새 옵션으로 덮어써 재활용하지 않으며 새 큐/다중 저장 구조를 요구하지 않습니다. 구체적인 기존 로컬 상태 전이는 Native 소관입니다.
5. 이후 사용자가 다시 완료 해제를 원하면 group 옵션을 저장한 **새 GET context→새 token/revision→새 key 명령**으로 진행합니다. 현재 상태 유지는 그 해제 명령을 자동으로 실행하지 않습니다.

### 과거 이력을 몰라도 이번 현재 상태 채택이 가능한 근거

- `reserve`는 같은 actor/operation/key의 RequestResult를 잠급니다. 성공 ACK가 유효하게 저장돼 있으면 gate 전에 ACK를 반환하며, 유효 lease가 살아 있으면 REQUEST_IN_PROGRESS입니다. 이번 조건은 그런 응답이 아닌 현재의 무옵션 CLIENT_UPGRADE_REQUIRED입니다.
- 새 실행 예약을 받은 뒤 group gate는 **enabled && !client**에서 ticket 생성 시각·token/업무 callback 전에 거절하고, 예외 경로는 해당 ticket을 retryable로 해제합니다. 먼저 예약됐던 다른 generation의 worker는 commit_result의 generation/state/lease 검사로 업무+ACK commit이 거절됩니다. worker가 먼저 commit했다면 reserve가 그 결과를 관측하는 순서입니다.
- 같은 원무옵션이 나중에 도착해도 현재 group gate를 통과하지 못합니다. 따라서 현재 GET을 채택하는 동안 옛 무옵션 correction이 뒤늦게 완료 체크를 해제하는 경로가 없습니다. 이는 과거에 어떤 결과가 있었는지의 증명이 아니라 **현재 상태 채택 뒤 이 원형의 미래 실행이 차단됨**을 이용한 제한 해제입니다.

조건은 원무옵션 correction과 현재 gate 유지에 한정합니다. 같은 key라도 group 옵션을 달리 붙인 별도 미해결 요청이 있거나 원문/대상 식별이 손상된 경우, gate가 적용되지 않는 환경/다른 명령에는 이 결론을 적용하지 않습니다. REQUEST_IN_PROGRESS·timeout/일반503·IDEMPOTENCY_EXPIRED/CONFLICT를 같은 정리 신호로 대체하지도 않습니다. 실제로 다른 응답이 나오면 기존 원문을 보존하고 그 응답 기준으로 알려 주세요. 현재 응답이 원ACK라면 기존 정상 ACK 경로를 사용합니다.

### 확인 결과와 다음 담당

격리 PostgreSQL/HTTP **1PASS/22.79s**: 이전 ticket의 유효 lease에서는 REQUEST_IN_PROGRESS → lease 경과 후 같은 무옵션 재송신은 CLIENT_UPGRADE_REQUIRED → generation 증가/retryable 확인 → 이전 ticket으로 주간 상태를 바꾸고 commit하려 하면 fencing 거절/전체 rollback → GET의 완료 근거·revision 보존 및 같은 원문 재차 gate 거절을 확인했습니다. project lostparty-check-4467c96c7219 exit0/cleanup0입니다. 실제 기존 회원 자료의 과거 결과/기기 조작을 시험한 것은 아니며 기존2/6/114/Native2845와 합산하지 않습니다.

[reserve/commit_result/release](https://github.com/heo0328/lostparty-backend/blob/f744a1e2a7aa3bf402f88a697133b19445f1061d/app/game_accounts/common/support.py), [실행/예외 순서](https://github.com/heo0328/lostparty-backend/blob/f744a1e2a7aa3bf402f88a697133b19445f1061d/app/raid_rooms/common/cycles.py), [group gate](https://github.com/heo0328/lostparty-backend/blob/f744a1e2a7aa3bf402f88a697133b19445f1061d/app/raid_rooms/group_links/cycle_group_policy.py)를 근거로 합니다.

**다음 Native 우선 작업은 위 좁힌 ‘현재 상태 유지’ 경로를 기존 v3 막힘에 연결하고 검증하는 것입니다.** hasPending으로 막힌 계정 기능이 실제 복구되기 전 정상 흐름 기기 시험을 다시 요청하지 않습니다. 새 Backend API/DB/서버 구현·배포·실자료 삭제·앱 초기화는 필요하지 않습니다. 기기 막힘은 아직 미해결이며 Native 적용/검증과 사용자 사용 복구 확인이 남습니다. 이번 조사 문서는 미커밋·미push, Issue는 OPEN 유지합니다.


임시 시험 원본 /tmp/lostparty-bug033-release/test_bug033_release_probe.py, SHA256 0a844993c40ec2f92f773eb7ae8c7d09fc7daad2736cc53cc5926414f4a531f5; 작업 트리의 시험 파일은 제거했다. 실제 로컬 확인은 DB revision SELECT와 실행 파일 해시만 읽었으며 회원 자료/키·환경·DB 구조/자료를 변경하지 않았다. 공식 회신: [전체49번째 Backend 현재 상태 채택 확인](https://github.com/heo0328/lostparty-backend/issues/17#issuecomment-6742169727). 전체 댓글49개와 본문 일치를 재조회했고 Issue 상단 상태/다음 담당을 갱신했다.
