# 다음 실행

2026-10-20. 현재 **feat/raid-recruitment**, 최신 계약 보완 본문 **7e9c2f2 로컬 커밋·미push**. main77a1fe5/dev ce3064f 유지. 별도 활동 브랜치 feat/activity-selection/89a3248 보존. 미커밋 변경을 다른 브랜치로 옮기지 않는다.

## 현재 — #13 R0 계약 보완3판 게시 / Flutter 재대조

[계약 고정 초안](../ISSUE_13_FIXED_CONTRACT_DRAFT.md)을 [전체43번째 Backend 회신](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6271860507)에 본문 전체로 게시했다. [Flutter41번째 정정](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6271510136)·[42번째 대조](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6271574011)에 대한 기술 답변이다. 완료는 검토 초안 작성/게시이며 최종 계약·통합 구현·Flutter 적용은 미완료다.

### 다음 담당·완료 조건 — 보완3판 게시

[46번째 소비 검토](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6282880292)/[47번째 사용자 결정](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6283062852)을 [계약 보완3판](../ISSUE_13_R0_CONTRACT_R3.md)에 반영해 [전체48번째 Backend](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6283178369)에 전문 게시했다. 설계7e9c2f2 로컬 커밋·미push다. 기존 두 초안의 충돌 정의는3판을 따른다.

1. **다음 Flutter**: nullable 숙련도/실제 P1 출처·기본미정/요일만/전체주차 조율·최종 입력 타입과 JSON9개·좌석 변환·그룹 최소projection/페이지 전 서버 필터의 실제 소비 가능 여부를 재대조한다. 이미 확정한 제품 정책은 재질문하지 않는다.
2. Backend: 새 회신의 실제 타입/권한·adapter 차이만 보완해 정확한 schema를 고정한다. N1 변경 제안의 자기 확인 사례는 아직 미채택이며 생성자 수동지정/자동조율 추가인원 최소1과 분리한다. 추가0은 허용하지 않는다. 기술 상한은 Backend 근거/측정으로 제시한다.
3. 재대조/경계 고정 뒤 정확한 OpenAPI와 모델·추가migration/기존자료 보존→개인표/관계·원장→예약/투표/다음주→완료·권한/원자성→실제 앱·DB/계약 검증의 내부R1~R5를 진행한다. 검증된 구현 구간 commit/push/원격 확인 뒤 필요한 테스트 인계를 한다.

확정 반영: 각 타임 정족수 전체 충족 후 원자적용/레이드 자체 불참 모드 제외/정각부터 신규 마감/혼합4인 구성/A완료 표시·B,C 유지/item단독탈퇴 제외·묶음전체탈퇴/마지막 개인완료 ON/OFF·choice/방전체 이번주 중단·실제참가자 선언/자동OFF·06경계 효력/타임합계24h. 원장/CAS/옛ACK·명시 시간중복 경고와 P1최근성공 보존 기술안은 유지한다.

완료는 계약 보완안 작성/게시이며 최종 소비 인수·통합 구현·OpenAPI/서버/DB 반영·Flutter 연결은 미완료다. 이번은 문서·설계 예시 검사뿐이며 새 서버 시험/배포 요청은 없다. 네이티브 소스는 직접 읽지 않았다.

### 보존할 확정 경계·실제 상태

시간 중복은 명시 행동 성공+경고/예약 보존, 자동 후보만 회피한다. 기존 동일 캐릭터 raid/cycle 원장·슬롯/한도/소유·CAS/원 ACK 가드를 유지한다. 초록 pending의 본인 확인은 최신 일정 예약 생성이며 투표와 별도다. 묶음 item B 완료로 A/C 시각을 이동하지 않는다. 기간은 하위 유효값 합계, 앱4와 게임8/단독8을 분리한다.

기존 로컬 F1/F2/F3 코드는 이전 후보이며 새 통합 모델 완료가 아니다. 원본 OpenAPI/main·실행 개발DB0016/API/이미지에는 모집 미반영이다. 기존 101/97/보존25 PASS를 새 초안의 구현 검증으로 쓰지 않는다. 이번은 문서·설계 예시 검사뿐이며 코드/DDL/OpenAPI·서버/자료 변경·앱/DB/provider/Flutter/기기 시험은 없었다. 설계 검토 회신이므로 미push 상태를 명시하고 댓글 전체로 산출물을 제공했다.

## 별도 보존

- #18 설계5fff83b와기록은활동브랜치89a3248에보존. [전체3번째Flutter](https://github.com/heo0328/lostparty-backend/issues/18#issuecomment-6264981603)는접수/별도소비검토대기이며승인아니다. 모집에자동활동추가를섞지않는다.
- #15 [전체9번째Flutter](https://github.com/heo0328/lostparty-backend/issues/15#issuecomment-6263145675) 화면수정8937445 dev/push·사용자기기3항목성공보고. 분쟁인수는별도보류다.
- G3완료구간dev/ce3064f통합·그룹브랜치정리상태유지. #16조건부해산은실제그룹모집원본/정합성후속이다. #17근거검토/#19통계는별도이슈로추적한다.


## 주간 사용횟수 통계 확인 — #19

2026-10-19 읽기확인: [#13전체7번째Flutter 원요구](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6232893737)는#19로이관됐으며아직통계구현/실제집계는없다. 실행DB0016에모집room/round/membership/application표와통계표·통계API가없다. 기존WeeklyState6행중manual완료4행·party완료/활성party는각0이며개인수동체크는모집이용/결과통계로전용하지않는다. 현재한도usage와주간누적이용도분리한다. 통합모집설계의실제생성/참가구간·결과/함께하기이력원천을확보하고#19귀속/마감/coverage정책확정뒤집계·조회로이어간다. 미지원자료는이용0으로보고하지않는다.
