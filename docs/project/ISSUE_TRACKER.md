# 이슈 주제별 추적표

**현재 Git 통합 완료:** [재신청 수정 브랜치 통합 기록](../features/recruitment/reapplication-integration-2026-10-27.md)·[PR28](https://github.com/heo0328/lostparty-backend/pull/28)/병합41a47ed의 dev 원격 반영과 완료 브랜치 로컬/원격 정리를 확인했다. 2026-10-28 main/dev를1b6f57b로동기화·원격확인후동일지점에서feat/group-management분기·checkout. 미완료 활동 선택 브랜치와 실행 API·DB는 보존. 최신 실행/다음 작업은 NEXT_WORK이며 아래 종료 전 검토 문장은 당시 이력이다.

## 최신 Git 통합 — 2026-10-30

사용자 승인으로 그룹 작업 `48bf88c`를 [PR30](https://github.com/heo0328/lostparty-backend/pull/30)·병합 `fc6c06a`로 dev에 통합하고 main도 fast-forward하여 원격 일치를 확인했다. `feat/group-management`는 로컬·원격 정리하고 checkout은 dev다. 위 2026-10-28 분기 상태는 과거 기준이며 미완료 활동 선택 브랜치는 보존한다. 그룹 새 기기 확인·Issue 상태·실제 실행 서버는 변경하지 않았다.

## 최신 그룹 후속 — 주차별 그룹 변경·승계 정책 정정

[#16 전체27번째 Flutter · 정책/구현 요청](https://github.com/heo0328/lostparty-backend/issues/16#issuecomment-6521839291)·[전체28번째 Flutter · 문서78e53aa0 게시](https://github.com/heo0328/lostparty-backend/issues/16#issuecomment-6521897849)에 대응해 [전체29번째 Backend 계약 후보](https://github.com/heo0328/lostparty-backend/issues/16#issuecomment-6522746434)를 먼저 인계했다. feat/raid-group-policy에서0035 주차/세대 원본·설정/승계/개방·조회/그룹판정과 원ACK 보존 전환을 구현했다. [소비 계약](../features/groups/cycle-group-policy.md)·[검증 집계](../features/groups/cycle-group-policy-verification.json)·NEXT_WORK 기준이며 새 Flutter 미연결이며 사용자 승인으로 sourceb8542ef/이미지930c25f8·개발DB0035 반영/실행검증을 완료했다([반영 기록](../engineering/operations/cycle-group-policy-rollout.md)). 구현b212ad0 commit/push·원격일치 및 [전체30번째 Backend 고정 계약 인계](https://github.com/heo0328/lostparty-backend/issues/16#issuecomment-6523975291) 완료, 다음 Flutter 연결/소비 차이 회신 대기다. 다음은 새 계약 연결/기기 결과이며 Issue종료·dev/main통합은 별도다. 기존 그룹 기기 인수·Issue13 completed는 유지한다.


## 2026-10-27 마감 — Issue13 사용자 승인 종료

사용자가 이슈13 클로즈를 명시적으로 지시했고 **closed/completed**를 실제 확인했다. [전체192번째 Backend · 1차 구현/기기 인수 마감](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6438046779)이 종료 근거다. Backend 구현/개발 반영과 Native 보고 정상 흐름·표시의 사용자 기기 인수는 완료다.190/191의 정밀도 소비·알럿·UX 등은 [차후 보완 추적](../features/recruitment/follow-up-backlog.md)에 담당·현재 보류·재착수 조건으로 보존했다. 이들은 현재 착수/1차 인수 선행 조건이 아니다.

현재 추가 Backend 구현·시험 요청은 없다. 다음은 사용자와 별도 구간을 재시작하거나 새 구체 차이가 생길 때 해당 주제 Issue에서 진행한다. dev/main18830c2·실행 sourcec1f86d8/이미지581a1a5e·DB0033 유지, 서버/DB/자료·다른 이슈 상태 변경 없음. 기기 회신 수신부터 이번 사용자 승인 종료까지의 누적 문서 기록을 같은 수정 브랜치에서 의미 있는 마감 구간으로 게시한다. 별도 merge/AWS·반복 시험은 없다. 아래 OPEN/종료 차단·확인 대기는 종료 전 각 시점의 이력이다.


## 2026-10-27 사용자 정정 수신 — 차후 보완은 현재 인수·종료의 선행 조건 아님

[전체191번째 Flutter · 사용자 정정](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6437976324)을 확인했다. 실제 BetaSchedule.session_id 정밀도 판정·다음 주 개방 알럿 로그·일정 제안 확인/수락 발견성 등은 **사용자와 차후로 합의한 Native 보완**이다. 미수정/개선 기록은 보존하되 현재 착수·즉시 다음 작업·현재 베타 인수의 선행 조건으로 두지 않는다. 별도 보완 구간 재시작 시 최신 계약·코드/UX를 확인한다.

기존 모집 정상 흐름·표시의 사용자 기기 통과/1차 구현 완료는 유지한다. **이전 Backend의 ‘미수정1건 때문에 현재 인수/종료 차단’ 판단을 정정한다.** 현재 추가 Native/Backend 구현·시험·서버 변경 요청은 없다.191에서 Native는 Issue13을 종료하지 않았다고 명시했으며, 이번 최신 회신 조회에서도 이슈 상태는 OPEN이다. 1차 구현 완료와 차후 보완 추적을 구분하며 보완 착수를 다시 요청하지 않는다. 아래190 기준 즉시 다음 작업/종료 차단 표현은 이번 정정으로 대체한다.


최신 #13 종료 검토: [전체189 Flutter](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6437895407) 표시 기기 확인 완료·[전체190 Flutter](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6437933418) 추가 Backend 누락 없음. **실제 세션 정밀도 Native 미수정1건**이 남아 OPEN 유지. 다음 Native 보완 완료 또는 별도 Issue로 담당/완료 조건 이관 확인 뒤 종료한다. 사용자 1차 구현/정상 흐름 기기 인수 완료와 구분한다.

2026-10-27 사용자 확정으로 **레이드 모집 1차 구현·네이티브 디바이스 인수 완료**를 기록한다. 추가 Backend 수정 요청은 없으며 새 구체 차이에 대응한다. 별도 성능/원ACK 검증·Git 통합·AWS/Issue 종료와 구분한다. 아래 미완료 표현은 당시 이력이며 현재 단계는 NEXT_WORK를 따른다.

모집 누적 이력은 `feat/raid-recruitment`이며 사용자 승인으로 [2026-10-27 통합 체크포인트](../features/recruitment/integration-checkpoint-2026-10-27.md)를 정리해 PR27/4a5f590으로 dev/main 같은 기준에 병합·푸시했고 완료 브랜치를 정리했다. 후행 결과 기록도 양 기준에 함께 게시하며 후속은 최신 dev에서 새 목적 브랜치로 진행한다. 이슈 OPEN과 부분/전체 인수는 Git 통합과 구분한다. 활동 선택의 미완료 로컬 작업은 별도로 보존한다. 아래 각 이슈의 고정 댓글·구현/검증 근거와 당시 이력은 유지한다.

2026-10-18 사용자 지시로 정리했다. 한 이슈의 직접 기능/완료 조건에 집중하고 독립 후속은 링크로만 연결한다. 아래 번호는 GitHub 이슈 번호이며 Backend 작업 단계 번호가 아니다. 당시 통합 기준은 dev/ce3064f·main/77a1fe5였다. 현재 개발API는 two-cycle178경로/199 operation·DB0033이며 최신실행은 NEXT_WORK를 따른다.

## 열려 있는 주제

| 이슈 | 주제 | 다음 담당·상태/완료 조건 |
|---|---|---|
| [#29](https://github.com/heo0328/lostparty-backend/issues/29) | 문서 역할·갱신·이관 기준 상호 확인 | Backend 원본c1fa205·Flutter 참조4bdec0e 원격 반영/내용 대조 완료. [전체5번째 Backend 완료 조건 확인](https://github.com/heo0328/lostparty-backend/issues/29#issuecomment-6520322169). 추가 수정 대기 없음·Issue 종료 별도/OPEN 유지 |
| [#12](https://github.com/heo0328/lostparty-backend/issues/12) | 그룹 핵심 표시·활동·집계/Flutter 연결 | 구현계약22b1620·개발실행2602e45/DB0034반영·실행검증완료. [전체27 Flutter 연결구현](https://github.com/heo0328/lostparty-backend/issues/12#issuecomment-6488900145)·자동검증자체보고/추가API요청없음. 후속#12전체29/30후보검색/역할표시도5d24244/507cd78a로개발반영·실행검증완료. 전체36사용자기존그룹정상시험통과수용. 최신 [전체39번째 Backend 서버반영 인계](https://github.com/heo0328/lostparty-backend/issues/12#issuecomment-6503318325). 새목록그룹명/소속배지후속은[계약](../features/groups/raid-link-contract.md)·개발반영완료. [전체40번째 Flutter 소비 인계](https://github.com/heo0328/lostparty-backend/issues/12#issuecomment-6503895589)의5f024e53 연결/push·전체2707PASS자체보고 수신. 추가API요청없음·사용자새기기확인/Flutter대응대기. [반영기록](../features/groups/implementation-2026-10-28.md) |
| [#15](https://github.com/heo0328/lostparty-backend/issues/15) | V2 Flutter 인증/분쟁 | #13 전체16번째Flutter 보고기준 D1~D4 dev반영·마감, 분쟁실기기는사용자판단보류. 이후 #13 전체17번째에서 로그인화면재구성수정 별도마감·계약검토전환을보고했으며분쟁실기기보류는별도 |
| [#16](https://github.com/heo0328/lostparty-backend/issues/16) | 그룹 관리·레이드 생명주기 | 새 주차별 그룹 정책0035 구현·격리검증, 고정 계약 게시·실제0035 반영 완료/Flutter 연결 대기는 위 현재 요청을 따른다. 아래는 기존0034 실행/소비 이력이다. 관리/기존레이드보존 구현·개발실행2602e45/DB0034반영·자료보존/실행검증완료. [전체17 Flutter 연결구현](https://github.com/heo0328/lostparty-backend/issues/16#issuecomment-6488900495)자체보고. 전체21기존그룹잔여기기통과수용·전체22최초그룹연결/표시승인후속구현·격리검증/개발반영/실행검증완료·[전체25번째 Backend 서버반영 인계](https://github.com/heo0328/lostparty-backend/issues/16#issuecomment-6503318794) 후 [전체26번째 Flutter 소비 인계](https://github.com/heo0328/lostparty-backend/issues/16#issuecomment-6503895060)의5f024e53 연결/push보고 수신·추가API요청없음·사용자새기기확인/Flutter대응대기·실서버 최초연결 성공 미확인·복구승계미정/그룹장전용레이드권한없음. [반영기록](../features/groups/implementation-2026-10-28.md) |
| [#17](https://github.com/heo0328/lostparty-backend/issues/17) | 캐릭터 소멸 근거·이력·이름 재사용 ID | Flutter전체1번째범위확인·Backend 현재기능/증거공백 검토·최소계약 보완. 기존L1/claim/조회 재사용. 실제삭제/보류해제 승인 아님 |
| [#18](https://github.com/heo0328/lostparty-backend/issues/18) | 활동 자동추가·직접제외 보존 | 활동브랜치89a3248/설계5fff83b 로컬미push보존. [전체3번째Flutter](https://github.com/heo0328/lostparty-backend/issues/18#issuecomment-6264981603)는설계접수/별도소비검토대기이며미승인·구현전 |
| [#19](https://github.com/heo0328/lostparty-backend/issues/19) | 사용자/그룹 주간 이용 통계 | Flutter전체1번째검토·type최초고정/함께집계·해산OFF/평균분모/그룹조회권한미확정·실제방원천선행. 집계/조회 미구현·개인manual결과 집계 금지 |
| [#22](https://github.com/heo0328/lostparty-backend/issues/22) | 개인 완료후 선택T 탈퇴·공대장 자동승계 | 전체2번째 Backend 표시보완 구현/개발반영 완료. [개발안내](../features/recruitment/membership-actions/README.md)·고유39PASS(23합동)/174경로·DB0030. 소비0eed67c push/원격확인·[전체3번째 Backend 인계](https://github.com/heo0328/lostparty-backend/issues/22#issuecomment-6362447014) 완료→[전체5번째 Flutter D22 연결결과](https://github.com/heo0328/lostparty-backend/issues/22#issuecomment-6363334658) fece2003 push/133mock·분석0 보고수신, Backend추가요청없음·다음Flutter 실회원/기기인수미완료·OPEN |
| [#23](https://github.com/heo0328/lostparty-backend/issues/23) | 현재/양T 동일회원 원자적 내보내기 | Backend0eed67c 인계·개발완료. [전체5번째 Flutter E23 연결결과](https://github.com/heo0328/lostparty-backend/issues/23#issuecomment-6363846643) b6720079 push/178mock·분석0 보고수신. 추가 계약요청없음/실회원·기기전체인수미완료·OPEN |
| [#24](https://github.com/heo0328/lostparty-backend/issues/24) | 선택T 본인실제참가방 검색제외 | Flutter 전체3 계약 수용·추가 차단없음. [개발 안내](../features/recruitment/membership-actions/contract.md) [Backend 전체4 구현 인계](https://github.com/heo0328/lostparty-backend/issues/24#issuecomment-6371301279)·소비15e143a push/원격 확인, SQL/semantics cursor 구현·격리 검증, [전체5번째 Backend 개발 반영](https://github.com/heo0328/lostparty-backend/issues/24#issuecomment-6371617690)·실제 개발176/DB0031 완료. 다음 Flutter 캐시/직접 연결·실인수, Backend 차이 대응·OPEN |
| [#26](https://github.com/heo0328/lostparty-backend/issues/26) | 신청·변경 통합자격·본인 후보조회 | [전체6 Flutter 계약2/UX수용](https://github.com/heo0328/lostparty-backend/issues/26#issuecomment-6381816954) 반영, [계약/구현](../features/recruitment/participation/candidate-contract.md)·고유45PASS(신규19/기존26)·177/116/기존DTO·별도factory 검증. 공통판정/정확자기제외·명시배치/승인실패pending유지/후보GET 구현 및 [실제개발 반영/자료보존검증](../engineering/operations/eligibility-rollout.md) 완료. [#26 전체7번째 Backend · 계약2 구현/검증 인계](https://github.com/heo0328/lostparty-backend/issues/26#issuecomment-6382258395)·source484ca17 push/원격확인. [전체9 Flutter 통합연결](https://github.com/heo0328/lostparty-backend/issues/26#issuecomment-6382646003) f89c009f push/493PASS·분석0 자체보고수신. 새Backend수정요청없음·개발API177 반영 완료·[전체10 Backend 반영인계](https://github.com/heo0328/lostparty-backend/issues/26#issuecomment-6383315604)·[전체11 Flutter 가입소수3항목 정상보고/표시계약 요청](https://github.com/heo0328/lostparty-backend/issues/26#issuecomment-6384482003) 수신·[표시 계약 제안1](../features/recruitment/participation/application-display-proposal.md)·작성22예시/음성15 정적검증·소비합의/구현·격리28PASS완료·실제개발반영완료·[전체12 Backend 제안](https://github.com/heo0328/lostparty-backend/issues/26#issuecomment-6384757210)·[전체13 Flutter 수용](https://github.com/heo0328/lostparty-backend/issues/26#issuecomment-6384902537)·[전체14 Backend 구현인계](https://github.com/heo0328/lostparty-backend/issues/26#issuecomment-6385227653)·[전체16 Flutter 연결/413PASS 보고](https://github.com/heo0328/lostparty-backend/issues/26#issuecomment-6385536441)·상세예시8 정정/추가12PASS·API불변·[전체17 Backend 자료보완회신](https://github.com/heo0328/lostparty-backend/issues/26#issuecomment-6385820194)·[전체18 Backend 실제반영인계](https://github.com/heo0328/lostparty-backend/issues/26#issuecomment-6386031663)·[전체19 레벨누락](https://github.com/heo0328/lostparty-backend/issues/26#issuecomment-6386174761)·[전체20 Backend 최소보완제안](https://github.com/heo0328/lostparty-backend/issues/26#issuecomment-6386261019)·[전체21 Flutter 소비/UX수용](https://github.com/heo0328/lostparty-backend/issues/26#issuecomment-6386405233)·신규저장/기존누락읽기구현·격리35PASS/구현 당시 실제개발미반영·[전체22 Backend 구현인계](https://github.com/heo0328/lostparty-backend/issues/26#issuecomment-6386634008)·[전체23 Flutter 연결](https://github.com/heo0328/lostparty-backend/issues/26#issuecomment-6386758343) 13fb5848/158PASS 자체보고 수신·[아이템레벨 실제개발 반영](../engineering/operations/application-item-level-rollout.md) 완료(sourcef471e31/6d5857b3)·[전체24 Backend 반영인계](https://github.com/heo0328/lostparty-backend/issues/26#issuecomment-6386808894)·[전체25 Flutter 보완인수 수용](https://github.com/heo0328/lostparty-backend/issues/26#issuecomment-6386859737)·레벨표시기기통과/두예외분기자동검증근거수용·네이티브 작업순서는 해당측 관리/Backend 구체차이대응·OPEN |
| [#25](https://github.com/heo0328/lostparty-backend/issues/25) | 주차/모두탈퇴 자동승계·공대장T 해산 | Flutter 전체5 네 차이 해소. [개발 안내](../features/recruitment/membership-actions/contract.md) [Backend 전체6 구현 인계](https://github.com/heo0328/lostparty-backend/issues/25#issuecomment-6371301934)·소비15e143a push/원격 확인, 새 원자 명령·기록/profile·0031 이행 구현/격리 검증, [전체7번째 Backend 개발 반영](https://github.com/heo0328/lostparty-backend/issues/25#issuecomment-6371618996)·실제 DB0031/API176 완료. [Flutter A 결과](https://github.com/heo0328/lostparty-backend/issues/25#issuecomment-6371981415) 6968f47a push/177mock·분석0 보고수신(독립재현아님). 이후 [전체9번째 Flutter B메뉴/성공처리](https://github.com/heo0328/lostparty-backend/issues/25#issuecomment-6372783376) 0487788a push/295mock·[전체10번째 Flutter C프로필/본인기록](https://github.com/heo0328/lostparty-backend/issues/25#issuecomment-6373322164) 0c5ae941 push/413mock·최종분석0 보고수신(범위별 수치·미합산/독립재현아님). 다음Flutter #24검색 후속/정상로그인 실인수, Backend 재현차이 대응·복구UX제안·OPEN |


## 이번 종료

| 이슈 | 종료 구분 | 근거/보존한 미완료 |
|---|---|---|
| [#13](https://github.com/heo0328/lostparty-backend/issues/13) | completed (사용자 승인·모집 1차 구현/기기 인수) | [전체192 Backend 마감](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6438046779). 보고된 정상 흐름·표시 사용자 인수 완료,190/191의 Native 보완/UX·별도 검증은 [차후 보완 대장](../features/recruitment/follow-up-backlog.md)에 담당·재착수 조건 보존. 현재 착수/인수 선행 조건 아님·추가 Backend 요청 없음. 새 주제 재시작 시 별도 Issue 추적·merge/AWS/다른 이슈 종료 아님 |
| [#21](https://github.com/heo0328/lostparty-backend/issues/21) | completed (내용전달·문서정리) | 사용자 종료 지시. 공통원문62240fe·[Backend 품질/UX 기준](../engineering/development/quality-and-ux.md)을 AGENTS/개발·협업에 연결·보존, 추가댓글/회신대기없음. 이후승인작업에적용·기능/전면감사/최적화완료뜻아님·사용자지시로지침/전달정리 작업브랜치push |
| [#10](https://github.com/heo0328/lostparty-backend/issues/10) | completed | 카탈로그/주차2GET 구현/검증·Flutter소비/실기기로그. 최신게임패치 검증/기능전체인수까지 완료라는 뜻 아님 |
| [#11](https://github.com/heo0328/lostparty-backend/issues/11) | completed (개인원장 구간) | 개인GET/manual완료·정정 구현/연결·manual true 실제보고. 미완료 실제파티/membership/i/영향확인·전체완료권한은 #13 본문에 이관 |
| [#8](https://github.com/heo0328/lostparty-backend/issues/8) | not_planned (원본 보관/추적 이관) | 길어진 다주제 스레드만종료. 미완료 생명주기 #17/활동 #18/V2 #15/실제파티 #13은유지. 요구취소/기능전체완료아님 |

기존 #1~#7 종료 상태는 그대로 유지한다. #12/#13의 원문은 당시 계획/근거로 보존하고 상단에 현재 범위를 표시했다. #8의 새 작업 요청/회신은 전용 이슈에 작성한다.

## Backend 정리·이관 회신 순번

아래는 본문을 제외한 실제 전체 댓글 순서이며 모두 Backend 작성/단계 이슈 정리·완료/이관이다.

| 이슈/순번 | 결과 댓글 |
|---|---|
| #8 전체154번째 | [원본 보관 종료](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6249418070) |
| #10 전체4번째 | [카탈로그/주차 완료](https://github.com/heo0328/lostparty-backend/issues/10#issuecomment-6249415959) |
| #11 전체8번째 | [개인원장 완료/파티후속 이관](https://github.com/heo0328/lostparty-backend/issues/11#issuecomment-6249417104) |
| #12 전체16번째 | [Flutter G1/G2·G3분리](https://github.com/heo0328/lostparty-backend/issues/12#issuecomment-6249414405) |
| #13 전체9번째 | [실제파티 유지/통계분리](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6249414899) |
| #15 전체1번째 | [V2 추적 유지/한주제 원칙](https://github.com/heo0328/lostparty-backend/issues/15#issuecomment-6249415434) |

이번 정리는 서버 구현·DB변경·자동정리·자료삭제/초기화·기존키/로그인 재시험·운영배포 승인이 아니다. 기능코드/실행계약은 같고 새 이슈를 만들었다고 기능 구현을 시작한 것이 아니다.
