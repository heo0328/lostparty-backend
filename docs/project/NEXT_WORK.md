# 다음 실행

2026-10-20. 현재 **feat/raid-recruitment**, 설계 본문 **35dd5f9 로컬 커밋·미push**. main77a1fe5/dev ce3064f 유지. 별도 활동 브랜치 feat/activity-selection/89a3248 보존. 미커밋 변경을 다른 브랜치로 옮기지 않는다.

## 현재 — #13 R0 계약 고정 초안 게시 / Flutter 실제 소비 대조

[계약 고정 초안](../ISSUE_13_FIXED_CONTRACT_DRAFT.md)을 [전체43번째 Backend 회신](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6271860507)에 본문 전체로 게시했다. [Flutter41번째 정정](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6271510136)·[42번째 대조](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6271574011)에 대한 기술 답변이다. 완료는 검토 초안 작성/게시이며 최종 계약·통합 구현·Flutter 적용은 미완료다.

### 다음 담당·완료 조건

1. Flutter: 실제 Router/DI/Repository와 구자료의 필드·상태·권한·변환을 대조해 누락/불일치를 #13에 회신한다. 구현 테스트 요청이 아니다.
2. Backend: 관련 최신 댓글을 확인하고 Selection의 기존 정확한 필드/다중 item CAS·생성 DTO와 공개목록/detail/application/choice 전체 소비 DTO를 대조 보완한다. 초안의 G1~G7 중 실제 필요한 제품 결정만 분리한다. 네이티브 소스는 직접 읽지 않는다.
3. 계약 고정 후 R1 모델/보존 이행 → R2 개인표·관계/원장 → R3 예약/투표/확인/다음주 → R4 부분 완료/권한·원자성 → R5 OpenAPI/앱/DB 준비 검증과 구현 구간 commit/push/원격 확인 후 필요한 소비 인계로 진행한다.

G1 N1/세션별 quorum, G2 권위06시 이벤트/지연·마감 정각, G3 앱4인 구성, G4 부분 완료의 방 탈퇴 연동·중단 범위/선언 자격, G5 다음주 설정/blocked 정리, G6 최근 성공 저장 보존의 기존 P1 호환, G7 기술 상한은 대조할 항목이다. 확정된 저장 점수 비교·missing 판정/하위 기간 합산·수06 운영/10 플레이는 다시 질문하지 않는다. bundle_total 새 입력 UI는 필수 추가하지 않는다.

### 보존할 확정 경계·실제 상태

시간 중복은 명시 행동 성공+경고/예약 보존, 자동 후보만 회피한다. 기존 동일 캐릭터 raid/cycle 원장·슬롯/한도/소유·CAS/원 ACK 가드를 유지한다. 초록 pending의 본인 확인은 최신 일정 예약 생성이며 투표와 별도다. 묶음 item B 완료로 A/C 시각을 이동하지 않는다. 기간은 하위 유효값 합계, 앱4와 게임8/단독8을 분리한다.

기존 로컬 F1/F2/F3 코드는 이전 후보이며 새 통합 모델 완료가 아니다. 원본 OpenAPI/main·실행 개발DB0016/API/이미지에는 모집 미반영이다. 기존 101/97/보존25 PASS를 새 초안의 구현 검증으로 쓰지 않는다. 이번은 문서·설계 예시 검사뿐이며 코드/DDL/OpenAPI·서버/자료 변경·앱/DB/provider/Flutter/기기 시험은 없었다. 설계 검토 회신이므로 미push 상태를 명시하고 댓글 전체로 산출물을 제공했다.

## 별도 보존

- #18 설계5fff83b와기록은활동브랜치89a3248에보존. [전체3번째Flutter](https://github.com/heo0328/lostparty-backend/issues/18#issuecomment-6264981603)는접수/별도소비검토대기이며승인아니다. 모집에자동활동추가를섞지않는다.
- #15 [전체9번째Flutter](https://github.com/heo0328/lostparty-backend/issues/15#issuecomment-6263145675) 화면수정8937445 dev/push·사용자기기3항목성공보고. 분쟁인수는별도보류다.
- G3완료구간dev/ce3064f통합·그룹브랜치정리상태유지. #16조건부해산은실제그룹모집원본/정합성후속이다. #17근거검토/#19통계는별도이슈로추적한다.


## 주간 사용횟수 통계 확인 — #19

2026-10-19 읽기확인: [#13전체7번째Flutter 원요구](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6232893737)는#19로이관됐으며아직통계구현/실제집계는없다. 실행DB0016에모집room/round/membership/application표와통계표·통계API가없다. 기존WeeklyState6행중manual완료4행·party완료/활성party는각0이며개인수동체크는모집이용/결과통계로전용하지않는다. 현재한도usage와주간누적이용도분리한다. 통합모집설계의실제생성/참가구간·결과/함께하기이력원천을확보하고#19귀속/마감/coverage정책확정뒤집계·조회로이어간다. 미지원자료는이용0으로보고하지않는다.
