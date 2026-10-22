# 이슈 주제별 추적표

현재 작업 브랜치: **feat/raid-recruitment**. G3는 PR20 bb144e0/후행ce3064f로 dev통합·원격확인/그룹브랜치로컬·원격정리했고 main77a1fe5는유지한다. 기존모집c41fd03/F1·F2는보존·미push이며dev기준을merge로반영한다.

2026-10-18 사용자 지시로 정리했다. 한 이슈의 직접 기능/완료 조건에 집중하고 독립 후속은 링크로만 연결한다. 아래 번호는 GitHub 이슈 번호이며 Backend 작업 단계 번호가 아니다. 현재 통합 기준은 dev/ce3064f·main/77a1fe5이며 기존로컬API8000/DB0016은 유지한다.

## 열려 있는 주제

| 이슈 | 주제 | 다음 담당·상태/완료 조건 |
|---|---|---|
| [#12](https://github.com/heo0328/lostparty-backend/issues/12) | 그룹 G1/G2 Flutter 연결 | Backend 구현/통합 완료. Flutter 연결/관련 검증과 사용SHA 회신 미확인. 현재 Flutter 우선작업을 중단시키지 않음 |
| [#13](https://github.com/heo0328/lostparty-backend/issues/13) | 통합모집·시간/참가/주간관리 | [전체84번째 Flutter · 계약 소비 검토 마감](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6310097083) 기준0.4.1/policy4. W1/W2·[W3](../ISSUE_13_W3_CYCLE_LIFECYCLE.md) 로컬 구현·격리 검증·구간 커밋 및 W4 준비 e8deb02까지 작업 브랜치 push/원격 확인 완료. [W4-A1](../ISSUE_13_W4A1_SUBMISSION_CONSENT.md) target 제출표/명시확인·새 동의 구간 구현/검증·6d2b301 push·원격 확인·[전체85번째 Backend 결과](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6314976554) 게시 완료. [W4-A2](../ISSUE_13_W4A2_CYCLE_PLANNING.md) 일정 조율·제안/세션별 투표·shadow0028 불변4표 구현/검증 완료(신규31/회귀218·고유249 분리 실행), `88583a9` push/원격 확인·[전체86번째 Backend · W4-A2 결과](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6316089641) 게시 완료. [W4-B](../ISSUE_13_W4B_CYCLE_OUTCOMES.md) 완료/정정·현재주 재개 구현·격리 검증 완료(132PASS/1081.82초, 신규26 포함), 구현 `0d8b58111356b69d817b23b154a56efb64c974f9` commit/push·실제 원격 SHA 확인·[전체87번째 Backend · W4-B 결과](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6319271776) 게시 완료. [W4-C](../ISSUE_13_W4C_CYCLE_MANAGEMENT.md) T 관리/G1 공통·전역8동작 구현/격리 검증 완료(고유98PASS(25+26+47 분리 실행, 마지막47PASS/374.96초), 신규27 포함), 구현 `babb25b8599fb3564fec59bae13a690e2f53d5b6` commit/push·실제 원격 SHA 확인·[전체88번째 Backend · W4-C 결과](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6330196057) 게시 완료. 후보50경로53동작 main/서버 미공개. [W4-D](../ISSUE_13_W4D_CUTOVER.md) worker/v1/summary·legacy 조회·전환 factory 구현/격리 검증 완료(151PASS/611.48초, 신규16), 구현 `8085e90877561c28c45eb7279929d790da0a7c5b` commit/push·실제 원격 SHA 확인·[전체89번째 Backend · W4-D 결과](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6330758804) 게시 완료. 기본116경로·준비167경로/0029, 실제 서버 전환 미실행. [W5](../ISSUE_13_W5_INTEGRATION.md) 배치 검색/성능·통합 검증 완료(전체303PASS/1855.45초 후 최종 보강31PASS/334.92초(중복30 제외·고유304, 신규7 포함)), 구현 `a10187ca238afc1fb41bbdc026228410bb85a311` commit/push·실제 원격 SHA 일치 확인·[전체90번째 Backend · W5 결과](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6331483028) 게시 완료. 실제 DB0023/API114경로·factory 없음 조회, 실제 전환 미실행. [복원 리허설](../ISSUE_13_W5_RESTORE_PREFLIGHT.md) 실제83표/414행·제한 LOGIN0029 이행/보존·별도0023 복구·키4개/시퀀스·보호7시험 완료, 구현 `372988108b8e7054d76da94838162480c3a2c12c` commit/push·실제 원격 SHA 일치 확인·[전체91번째 Backend · W5 복원 준비 결과](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6332223435) 게시 완료. 다음 Backend는 실제 전환 대상/영향 확인·개발 DB/API 전환·인계. 실제 준비/게시 후 Flutter 인계하며 서버/DB·전체 실행 계약/성능·Flutter 인수 미완료 |
| [#15](https://github.com/heo0328/lostparty-backend/issues/15) | V2 Flutter 인증/분쟁 | #13 전체16번째Flutter 보고기준 D1~D4 dev반영·마감, 분쟁실기기는사용자판단보류. 이후 #13 전체17번째에서 로그인화면재구성수정 별도마감·계약검토전환을보고했으며분쟁실기기보류는별도 |
| [#16](https://github.com/heo0328/lostparty-backend/issues/16) | G3 완료 구현/dev 통합·조건부 해산 후속 | 관리GET/이전/일반탈퇴는 구현332a8ab·인계349fb79/PR20 bb144e0 dev통합·원격확인/완료브랜치정리. 통합전45PASS·실행계약일치(기존148PASS와중복), [전체6번째 Backend 통합결과](https://github.com/heo0328/lostparty-backend/issues/16#issuecomment-6262944673). 조건부해산은실제그룹모집원본후속·추방/대표변경미구현/Flutter연결·실기기별도, 이슈유지 |
| [#17](https://github.com/heo0328/lostparty-backend/issues/17) | 캐릭터 소멸 근거·이력·이름 재사용 ID | Flutter전체1번째범위확인·Backend 현재기능/증거공백 검토·최소계약 보완. 기존L1/claim/조회 재사용. 실제삭제/보류해제 승인 아님 |
| [#18](https://github.com/heo0328/lostparty-backend/issues/18) | 활동 자동추가·직접제외 보존 | 활동브랜치89a3248/설계5fff83b 로컬미push보존. [전체3번째Flutter](https://github.com/heo0328/lostparty-backend/issues/18#issuecomment-6264981603)는설계접수/별도소비검토대기이며미승인·구현전 |
| [#19](https://github.com/heo0328/lostparty-backend/issues/19) | 사용자/그룹 주간 이용 통계 | Flutter전체1번째검토·type최초고정/함께집계·해산OFF/평균분모/그룹조회권한미확정·실제방원천선행. 집계/조회 미구현·개인manual결과 집계 금지 |

## 이번 종료

| 이슈 | 종료 구분 | 근거/보존한 미완료 |
|---|---|---|
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
