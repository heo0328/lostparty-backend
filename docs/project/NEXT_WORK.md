# 다음 실행

2026-10-20. 현재 **feat/raid-recruitment**, 최신 계약 보완 본문 **d1bdb47 로컬 커밋·미push**. main77a1fe5/dev ce3064f 유지. 별도 활동 브랜치 feat/activity-selection/89a3248 보존. 미커밋 변경을 다른 브랜치로 옮기지 않는다.

## 현재 — #13 기술 계약 보완4판 게시 / Flutter 해당분 재대조

[계약 고정 초안](../ISSUE_13_FIXED_CONTRACT_DRAFT.md)을 [전체43번째 Backend 회신](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6271860507)에 본문 전체로 게시했다. [Flutter41번째 정정](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6271510136)·[42번째 대조](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6271574011)에 대한 기술 답변이다. 완료는 검토 초안 작성/게시이며 최종 계약·통합 구현·Flutter 적용은 미완료다.

### 다음 담당·완료 조건 — 기술 보완4판 게시

[49번째 Flutter](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6283395513)의 두 경계를 [기술 계약 보완4판](../ISSUE_13_R0_TECHNICAL_BOUNDARIES_R4.md) **d1bdb47 로컬·미push**에 반영해 [전체50번째 Backend](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6283620362)로 전문/JSON8개 인계했다. 이전 초안의 필터/그룹범위·종료완료 입력·N1 충돌 정의를 대체한다.

1. **다음 Flutter**: 회원별캐릭터AND/OR·복수그룹 동일회원/커서·그룹연결과입장scope 분리, 권한내 영향context/암호화snapshot으로 생성하는 종료·완료 입력의 실제 소비 가능 여부만 재대조한다. 기존제품/기본상태/JSON9개 전체를 다시 요청하지 않는다.
2. Backend: 회신된 실제 schema/권한·참조 차이를 보완하고 정확한 OpenAPI/구현 계약을 함께 고정한다. N1명시본인확인은 확정, 자동추가0은 금지다. 기술 상한/TTL·토큰/페이지·탐색비용은 Backend 근거/측정으로 확정한다.
3. 통합 모델/추가migration·자료보존→개인표/관계/원장→예약·투표·다음주→완료/권한·잠금/원자성→실제앱·DB/계약 검증을 내부R1~R5로 진행한다. 검증된 구현 구간 commit/push/원격 확인 후 필요한 소비시험 인계를 한다.

핵심 기준: member_ref는 조회자·선택그룹·권한세대 한정, 회원간AND/각회원캐릭터OR/그룹OR를 페이지전에 판정한다. group_id는연결그룹/scope는입장범위이며공개전환으로연결을지우지않는다. 전체종료/완료는타인원장버전배열을입력받지않고권한내context token으로내부영향집합을잠금검사/변경409전체rollback한다. GET는무쓰기/성공원ACK는만료token재실행보다우선한다.

완료는 기술 보완안 작성/게시이며 최종 소비/API인수·통합구현/이행·실행OpenAPI·서버DB반영·Flutter연결은 미완료다. 이번은 설계예시/문서검사뿐이며 새 서버시험/배포요청은 없다. 네이티브 소스는 읽지 않았다.

### 보존할 확정 경계·실제 상태

시간 중복은 명시 행동 성공+경고/예약 보존, 자동 후보만 회피한다. 기존 동일 캐릭터 raid/cycle 원장·슬롯/한도/소유·CAS/원 ACK 가드를 유지한다. 초록 pending의 본인 확인은 최신 일정 예약 생성이며 투표와 별도다. 묶음 item B 완료로 A/C 시각을 이동하지 않는다. 기간은 하위 유효값 합계, 앱4와 게임8/단독8을 분리한다.

기존 로컬 F1/F2/F3 코드는 이전 후보이며 새 통합 모델 완료가 아니다. 원본 OpenAPI/main·실행 개발DB0016/API/이미지에는 모집 미반영이다. 기존 101/97/보존25 PASS를 새 초안의 구현 검증으로 쓰지 않는다. 이번은 문서·설계 예시 검사뿐이며 코드/DDL/OpenAPI·서버/자료 변경·앱/DB/provider/Flutter/기기 시험은 없었다. 설계 검토 회신이므로 미push 상태를 명시하고 댓글 전체로 산출물을 제공했다.

## 별도 보존

- #18 설계5fff83b와기록은활동브랜치89a3248에보존. [전체3번째Flutter](https://github.com/heo0328/lostparty-backend/issues/18#issuecomment-6264981603)는접수/별도소비검토대기이며승인아니다. 모집에자동활동추가를섞지않는다.
- #15 [전체9번째Flutter](https://github.com/heo0328/lostparty-backend/issues/15#issuecomment-6263145675) 화면수정8937445 dev/push·사용자기기3항목성공보고. 분쟁인수는별도보류다.
- G3완료구간dev/ce3064f통합·그룹브랜치정리상태유지. #16조건부해산은실제그룹모집원본/정합성후속이다. #17근거검토/#19통계는별도이슈로추적한다.


## 주간 사용횟수 통계 확인 — #19

2026-10-19 읽기확인: [#13전체7번째Flutter 원요구](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6232893737)는#19로이관됐으며아직통계구현/실제집계는없다. 실행DB0016에모집room/round/membership/application표와통계표·통계API가없다. 기존WeeklyState6행중manual완료4행·party완료/활성party는각0이며개인수동체크는모집이용/결과통계로전용하지않는다. 현재한도usage와주간누적이용도분리한다. 통합모집설계의실제생성/참가구간·결과/함께하기이력원천을확보하고#19귀속/마감/coverage정책확정뒤집계·조회로이어간다. 미지원자료는이용0으로보고하지않는다.
