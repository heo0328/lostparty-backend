# 다음 실행

2026-10-25

- **작업 구간명:** 모집 전체 흐름 네이티브 점검·인수.
- **작업 내용:** 아이템레벨 보완 인수 결과 확인 후, 네이티브가 현재 앱·개발 서버 기준으로 모집 전체 연결을 점검하고 Backend가 구체 차이에 대응한다.
- **브랜치·위치:** `feat/raid-recruitment` / `/home/heowork/projects/lostparty-backend`.
- **실제 개발 반영 기준:** source `f471e3133ad60befcad77d7123e1107ba7501bb4`, 이미지6d5857b3…·177경로·DB0031. [반영 근거](../engineering/operations/application-item-level-rollout.md)·[집계](../engineering/operations/records/application-item-level-rollout.json).


공식 순서 인계: [#26 전체26번째 Backend · 보완 인수 확인/네이티브 전체 구간 점검](https://github.com/heo0328/lostparty-backend/issues/26#issuecomment-6386892285) 게시·댓글전문/실제순번 확인. 기록4f56e60 push·원격확인 후 전달했으며 다음Flutter 전체연결 점검·Backend 구체차이대응이다.

## 최신 수신·완료 경계

[#26 전체25번째 Flutter · 아이템레벨 사용자 인수 결과](https://github.com/heo0328/lostparty-backend/issues/26#issuecomment-6386859737)에서 사용자의 ‘현재 레벨이 표기됩니다’ 정상 기기 결과를 확인했다. current_saved/unavailable은 만들기 어려운 실제 분기를 강제하지 않고 구현·자동검증 근거로 사용자가 인수 수용했다. 해당 두 분기의 실제 기기 관찰은 미수행이며, 레벨 표시 자체의 기기 통과와 구분한다. Flutter source13fb5848/최종158PASS는 자체보고이며 Backend35PASS/반영HTTP12와 합산하지 않는다.

신청자 레벨 누락 보완 구간은 인수 수용됐고 추가 Backend 수정/재시험 대기는 없다. 전체 모집·변경/주차교차 인수나 Issue26 종료까지 완료한 것은 아니다. [전체24 Backend 반영 인계](https://github.com/heo0328/lostparty-backend/issues/26#issuecomment-6386808894) 후 개발 미반영 대기는 해소됐다.

## 다음 담당·순서

사용자가 다음 순서를 네이티브의 모집 전체 구간 테스트로 지정했다. Flutter가 현재 앱과 반영 서버를 기준으로 전체 연결 및 직접 영향의 검증 현황을 정리하고 아래 구간을 순서대로 점검한다.

1. 생성: 조건·모집 생성과 결과 반영.
2. 가입: 후보·역할 선택, 신청/대기/승인·거절·철회와 양쪽 상태 반영.
3. 방 내부 행위: 캐릭터/역할·배치 변경, 일정/동의와 참가 정보 반영.
4. 완료·해산: 활성 기능의 완료/해산 및 관련 기록·상태 반영. IF-001 비활성 기능은 제외 기준을 유지한다.
5. 주차 분리: C/N 전환·격리와 다른 주차 자료 보존.

[전체8 Flutter의 기존 5구간 기준](https://github.com/heo0328/lostparty-backend/issues/26#issuecomment-6382315586)을 따른다. 이는 수동시험 분량/순서이며 구현·직접 영향 회귀를 특정 구간만으로 제한하지 않는다. 사용자의 수동 확인은 소수 항목씩 나누고, 이미 통과한 항목은 근거를 유지하되 재확인이 필요한 직접 영향이 있으면 이유와 대상만 제시한다. 동일 자동시험 전체를 변화 없이 반복 실행하라는 요청은 아니다.

**다음 Flutter:** 점검 순서/기존 통과·미확인·실패를 구분해 진행하고 직접 차이를 해당 Issue에 개인정보를 제거한 상태/code·재현구간으로 회신한다. **다음 Backend:** 구체 API/계약·데이터 차이가 보고되면 재현·수정·필요검증·게시/인계한다. 현재 별도 코드/서버 수정 대상은 없다. 전체 점검과 인수 결과가 확인될 때까지 Issue26 및 독립 미완료 추적을 유지한다.

목록 진입/갱신·실시간/웹소켓/알림은 변경하지 않았다. 이전 일반오류 관찰은 HTTP/code 미확인이며 원인 수정 완료로 해석하지 않는다. 시험을 위한 실회원 자료/키 변조·고의 장애를 요구하지 않는다. 이번 수신 기록은 문서 작업으로 API·서버/DB·기기·dev/main/운영 변경이나 새 실행시험은 없다.

## 유지할 경계·독립 후속

- [IF-001](../features/recruitment/completion-and-records/inactive-features.md): 이번주 미완료 종료·같은 주차 재개는 앱 비활성, 구 endpoint/서버권한/자료·원pending/24h ACK는 보존한다. 다음주 reopen과 recover_leadership은 별개이고 복구 UX는 제품 승인 전 제안이다.
- 그룹 연결·조건부 해산, V2 분쟁 실인수 보류, 생명주기 #17·활동 자동추가/직접제외 #18·통계 #19는 [추적표](ISSUE_TRACKER.md)의 담당·미완료를 유지한다. 이번 문서 작업으로 착수/종료하지 않는다.
- 모집 pending의 앱종료 후 영속복구·F1~F6 실회원/기기 전체·성능·운영 인수, dev/main 통합·AWS 배포는 미완료다. 품질/UX 기준의 운영 안정 후 별도 최적화 검토 안내도 유지한다.
- 재기동/환경 확인이 별도 필요하면 [개발 환경](../engineering/development/environment.md)을 따른다. 기본앱·구worker 혼용이나 과거 백업 덮어쓰기/삭제는 하지 않는다.

## 다음 채팅의 작업 기준

#26 최신 회신에서 네이티브 전체 구간 점검의 진행/결과와 직접 Backend 차이를 확인한다. 아이템레벨 보완은 위 근거로 인수 수용됐고, 전체 모집 인수·dev/main/운영은 미완료다. 같은 모집 브랜치에서 이어간다.
