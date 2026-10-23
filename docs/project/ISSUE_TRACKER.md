# 이슈 주제별 추적표

현재 작업 브랜치: **feat/raid-recruitment**. G3는 PR20 bb144e0/후행ce3064f로 dev통합·원격확인/그룹브랜치로컬·원격정리했고 main77a1fe5는유지한다. 모집 구현은 작업 브랜치에서 게시/협업하며 dev/main 통합은 별도다.

2026-10-18 사용자 지시로 정리했다. 한 이슈의 직접 기능/완료 조건에 집중하고 독립 후속은 링크로만 연결한다. 아래 번호는 GitHub 이슈 번호이며 Backend 작업 단계 번호가 아니다. 당시 통합 기준은 dev/ce3064f·main/77a1fe5였다. 현재 개발API는 two-cycle174경로/DB0030이며 최신실행은 NEXT_WORK를 따른다.

## 열려 있는 주제

| 이슈 | 주제 | 다음 담당·상태/완료 조건 |
|---|---|---|
| [#12](https://github.com/heo0328/lostparty-backend/issues/12) | 그룹 G1/G2 Flutter 연결 | Backend 구현/통합 완료. Flutter 연결/관련 검증과 사용SHA 회신 미확인. 현재 Flutter 우선작업을 중단시키지 않음 |
| [#13](https://github.com/heo0328/lostparty-backend/issues/13) | 통합모집·시간/참가/주간관리 | Flutter133 A/e9d2783d·134 B/797c16b3 구현/자동검증 보고수신. [135 검색제외](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6366977367)·[136 최신탈퇴/해산](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6367266418)는새Backend계약/구현요청·미구현. 사전위임없는C/N탈퇴·모두탈퇴/본인리더인모든T다인해산으로정책변경전달,구명령원효과보존. [수신정리](../ISSUE_13_OCT24_NATIVE_FEEDBACK.md)·다음Backend 계약/호환설계,실인수·운영미완료/OPEN |
| [#15](https://github.com/heo0328/lostparty-backend/issues/15) | V2 Flutter 인증/분쟁 | #13 전체16번째Flutter 보고기준 D1~D4 dev반영·마감, 분쟁실기기는사용자판단보류. 이후 #13 전체17번째에서 로그인화면재구성수정 별도마감·계약검토전환을보고했으며분쟁실기기보류는별도 |
| [#16](https://github.com/heo0328/lostparty-backend/issues/16) | G3 완료 구현/dev 통합·조건부 해산 후속 | 관리GET/이전/일반탈퇴는 구현332a8ab·인계349fb79/PR20 bb144e0 dev통합·원격확인/완료브랜치정리. 통합전45PASS·실행계약일치(기존148PASS와중복), [전체6번째 Backend 통합결과](https://github.com/heo0328/lostparty-backend/issues/16#issuecomment-6262944673). 조건부해산은실제그룹모집원본후속·추방/대표변경미구현/Flutter연결·실기기별도, 이슈유지 |
| [#17](https://github.com/heo0328/lostparty-backend/issues/17) | 캐릭터 소멸 근거·이력·이름 재사용 ID | Flutter전체1번째범위확인·Backend 현재기능/증거공백 검토·최소계약 보완. 기존L1/claim/조회 재사용. 실제삭제/보류해제 승인 아님 |
| [#18](https://github.com/heo0328/lostparty-backend/issues/18) | 활동 자동추가·직접제외 보존 | 활동브랜치89a3248/설계5fff83b 로컬미push보존. [전체3번째Flutter](https://github.com/heo0328/lostparty-backend/issues/18#issuecomment-6264981603)는설계접수/별도소비검토대기이며미승인·구현전 |
| [#19](https://github.com/heo0328/lostparty-backend/issues/19) | 사용자/그룹 주간 이용 통계 | Flutter전체1번째검토·type최초고정/함께집계·해산OFF/평균분모/그룹조회권한미확정·실제방원천선행. 집계/조회 미구현·개인manual결과 집계 금지 |
| [#22](https://github.com/heo0328/lostparty-backend/issues/22) | 개인 완료후 선택T 탈퇴·공대장 자동승계 | 전체2번째 Backend 표시보완 구현/개발반영 완료. [개발안내](../ISSUE_22_23_ATOMIC_MEMBER_ACTIONS_DEVELOPMENT.md)·고유39PASS(23합동)/174경로·DB0030. 소비0eed67c push/원격확인·[전체3번째 Backend 인계](https://github.com/heo0328/lostparty-backend/issues/22#issuecomment-6362447014) 완료→[전체5번째 Flutter D22 연결결과](https://github.com/heo0328/lostparty-backend/issues/22#issuecomment-6363334658) fece2003 push/133mock·분석0 보고수신, Backend추가요청없음·다음Flutter 실회원/기기인수미완료·OPEN |
| [#23](https://github.com/heo0328/lostparty-backend/issues/23) | 현재/양T 동일회원 원자적 내보내기 | Backend0eed67c 인계·개발완료. [전체5번째 Flutter E23 연결결과](https://github.com/heo0328/lostparty-backend/issues/23#issuecomment-6363846643) b6720079 push/178mock·분석0 보고수신. 추가 계약요청없음/실회원·기기전체인수미완료·OPEN |


## 이번 종료

| 이슈 | 종료 구분 | 근거/보존한 미완료 |
|---|---|---|
| [#21](https://github.com/heo0328/lostparty-backend/issues/21) | completed (내용전달·문서정리) | 사용자 종료 지시. 공통원문62240fe·[Backend 품질/UX 기준](../DEVELOPMENT_QUALITY_AND_UX_STANDARD.md)을 AGENTS/개발·협업에 연결·보존, 추가댓글/회신대기없음. 이후승인작업에적용·기능/전면감사/최적화완료뜻아님·사용자지시로지침/전달정리 작업브랜치push |
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
