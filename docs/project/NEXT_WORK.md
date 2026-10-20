# 다음 실행

2026-10-20. 현재 **feat/raid-recruitment**, 최신 구현 **fbf1f2f 로컬 커밋·미push**. main77a1fe5/dev ce3064f 유지. 별도 활동 브랜치 feat/activity-selection/89a3248 보존. 미커밋 변경을 다른 브랜치로 옮기지 않는다.

## 현재 — #13 R1-B 추가 원천·P1 성공 보존 구현 / Backend R2

[계약 고정 초안](../ISSUE_13_FIXED_CONTRACT_DRAFT.md)을 [전체43번째 Backend 회신](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6271860507)에 본문 전체로 게시했다. [Flutter41번째 정정](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6271510136)·[42번째 대조](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6271574011)에 대한 기술 답변이다. 완료는 검토 초안 작성/게시이며 최종 계약·통합 구현·Flutter 적용은 미완료다.

### 다음 담당·완료 조건 — R1-B 추가 원천·P1 보존 구현

[R1-B 구현기록](../ISSUE_13_R1B_SOURCES_IMPLEMENTATION.md) **fbf1f2f 로컬커밋·미push**를 [전체53번째 Backend](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6284451921)에 기록했다. 설정/item기간정책·일정/참여/예약/투표·choice/개시/신청 원천16개와P1성공snapshot1개/0020추가이행·P1저장transaction연결을구현했다. 다음은 **Backend R2**이며 네이티브시험/추가설계회신대기가아니다.

1. R2 개인가능표/방제출표의정확한schema·정규화·편집복원/버전/원ACK와인증회원scope·읽기무쓰기/저장서비스를구현한다. 구간/페이지/탐색등기술상한은대표자료측정근거로고정한다.
2. 지속관계/캐릭터선택·item/round/assignment와WeeklyState정확한귀속·현재슬롯/한도/정밀역할점수비교를새원천에연결한다. P1현재head와최근성공원천/관측·경고·버전을구분하고반대역할/최고값·강제갱신/TTL로대체하지않는다.
3. HTTP구간의required/null·권한/거절/오류/ACK·기존검색raid/difficulty/정렬·자리필터와회원조건결합을원본OpenAPI/구현에함께고정한다. 원래legacy후보서비스는아직기존표만쓰므로이중집계/이중쓰기·부분활성화하지않는다. legacy_review_required/origin_unknown자료를근거없이확정/공개원신청으로승격하지않는다.
4. R3 예약·후보/제안/정족수·확인·다음주, R4 부분완료/전체종료·암호화context/가시검색·원자성, R5 실제앱/DB·계약검증→구현구간commit/push/원격확인→필요Flutter동작인계를진행한다. 기존제품/두기술경계를재협의하지않는다.

실제검증: 격리PostgreSQL17/제한LOGIN·합성자료에서기존모든표의행·시각hash보존, source귀속/설정/활성예약·choice·floor/정책버전, P1NULL/낮은최신값/지연·재송/동시성/실패rollback/퇴역정리·타캐릭터보존과API회귀를확인했다. 넓은회귀183PASS/146.04초, 최종원천/P1·준비/기록시각45PASS/48.93초(일부중복,합산안함). 최종FK삭제규칙/seed시각·기간출처추가후검증통과다. 전용tmpfs환경정리완료.

원본OpenAPI와실행main/API8000/개발DB0016·이미지/자료는미변경이다.0020/P1보존은로컬코드/격리검증만완료했고신규코드실제적용은0020준비와함께해야한다. 새모집HTTP/통합기능·Flutter연결은미완료이며아직원격미push/동작시험요청없음이다.

### 보존할 확정 경계·실제 상태

시간 중복은 명시 행동 성공+경고/예약 보존, 자동 후보만 회피한다. 기존 동일 캐릭터 raid/cycle 원장·슬롯/한도/소유·CAS/원 ACK 가드를 유지한다. 초록 pending의 본인 확인은 최신 일정 예약 생성이며 투표와 별도다. 묶음 item B 완료로 A/C 시각을 이동하지 않는다. 기간은 하위 유효값 합계, 앱4와 게임8/단독8을 분리한다.

기존 로컬 F1/F2/F3 코드는 이전 후보이며 새 통합 모델 완료가 아니다. 원본 OpenAPI/main·실행 개발DB0016/API/이미지에는 모집 미반영이다. 기존 101/97/보존25 PASS를 새 초안의 구현 검증으로 쓰지 않는다. R1-A부터 새 모델/추가 DDL·격리 PostgreSQL 자동검증을 수행했다. 원본 OpenAPI/실행 서버·개발 DB/자료는 바꾸지 않았으며 실provider/Flutter·기기 시험은 미실행이다.

## 별도 보존

- #18 설계5fff83b와기록은활동브랜치89a3248에보존. [전체3번째Flutter](https://github.com/heo0328/lostparty-backend/issues/18#issuecomment-6264981603)는접수/별도소비검토대기이며승인아니다. 모집에자동활동추가를섞지않는다.
- #15 [전체9번째Flutter](https://github.com/heo0328/lostparty-backend/issues/15#issuecomment-6263145675) 화면수정8937445 dev/push·사용자기기3항목성공보고. 분쟁인수는별도보류다.
- G3완료구간dev/ce3064f통합·그룹브랜치정리상태유지. #16조건부해산은실제그룹모집원본/정합성후속이다. #17근거검토/#19통계는별도이슈로추적한다.


## 주간 사용횟수 통계 확인 — #19

2026-10-19 읽기확인: [#13전체7번째Flutter 원요구](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6232893737)는#19로이관됐으며아직통계구현/실제집계는없다. 실행DB0016에모집room/round/membership/application표와통계표·통계API가없다. 기존WeeklyState6행중manual완료4행·party완료/활성party는각0이며개인수동체크는모집이용/결과통계로전용하지않는다. 현재한도usage와주간누적이용도분리한다. 통합모집설계의실제생성/참가구간·결과/함께하기이력원천을확보하고#19귀속/마감/coverage정책확정뒤집계·조회로이어간다. 미지원자료는이용0으로보고하지않는다.
