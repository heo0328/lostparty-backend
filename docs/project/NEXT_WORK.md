# 다음 실행

2026-10-20. 현재 **feat/raid-recruitment**, 최신 계약 보완 본문 **d1bdb47 로컬 커밋·미push**. main77a1fe5/dev ce3064f 유지. 별도 활동 브랜치 feat/activity-selection/89a3248 보존. 미커밋 변경을 다른 브랜치로 옮기지 않는다.

## 현재 — #13 설계 소비 대조 완료 / Backend 명세 고정·통합 구현

[계약 고정 초안](../ISSUE_13_FIXED_CONTRACT_DRAFT.md)을 [전체43번째 Backend 회신](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6271860507)에 본문 전체로 게시했다. [Flutter41번째 정정](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6271510136)·[42번째 대조](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6271574011)에 대한 기술 답변이다. 완료는 검토 초안 작성/게시이며 최종 계약·통합 구현·Flutter 적용은 미완료다.

### 다음 담당·완료 조건 — Flutter51번째 설계 대조 마감

[전체51번째 Flutter](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6283811575)에서49번째의 두 기술 경계 소비 검토를 마감했다. **제품 결정과 제시된 설계 대조는 완료**됐으며 같은 두 영역의 설계 전문/제품 협의를 반복 요청하지 않는다. 실제 API/암호화·DB동시성 인수는 구현 이후 별도다. 다음 담당은 **Backend 명세 고정·통합 구현**이다.

1. 정확한 OpenAPI/구현 schema: R4 검색에 기존 raidIds/difficultyIds와 적용 중인 정렬·자리 필터의 대응을 함께 명시한다. 다른 조회와 분리해도 회원조건과 페이지 전에 결합하며 로컬 재필터로 결과를 누락시키지 않는다. 이는 기존 기능 보존이며 새 제품 재협의가 아니다.
2. 필드 required/null·permissions 거절·에러/ACK·읽기context, token 만료/크기·페이지/구간·탐색 상한을 Backend 측정 근거로 고정한다. 예시20건/5분을 확정 상한으로 삼지 않는다.
3. 내부R1 모델·추가migration/기존자료 보존 → R2 개인표/관계·원장 → R3 예약/투표·다음주 → R4 완료·권한/잠금·원자성 → R5 실제앱/DB·OpenAPI 검증을 진행한다. 미합의초안을 공개API에 추가하는 단계가 아니라 합의된계약의 정확한구현을고정하는 단계다.
4. 검증된 인계 가능 구간을 commit/push/원격 확인하고 API/DB 준비·미완료를 구분해 #13 전달한다. Flutter는 실제 구현계약/인계를 소비하며 현재token/DTO를추정해선연결하지않는다. 기존PendingRepository/Stream존재는연결완료가아니며상시polling을추가하지않는다.

이번은51번째수신/단계전환기록이다. Backend코드/OpenAPI/서버DB를이미변경한것은아니다. Flutter도문서/JSON예시검증만보고했고실행코드·서버시험없음/HEAD6d3f617·미커밋미push다. 같은접수댓글을반복하지않고다음실제구현계약/결과로인계한다.

### 보존할 확정 경계·실제 상태

시간 중복은 명시 행동 성공+경고/예약 보존, 자동 후보만 회피한다. 기존 동일 캐릭터 raid/cycle 원장·슬롯/한도/소유·CAS/원 ACK 가드를 유지한다. 초록 pending의 본인 확인은 최신 일정 예약 생성이며 투표와 별도다. 묶음 item B 완료로 A/C 시각을 이동하지 않는다. 기간은 하위 유효값 합계, 앱4와 게임8/단독8을 분리한다.

기존 로컬 F1/F2/F3 코드는 이전 후보이며 새 통합 모델 완료가 아니다. 원본 OpenAPI/main·실행 개발DB0016/API/이미지에는 모집 미반영이다. 기존 101/97/보존25 PASS를 새 초안의 구현 검증으로 쓰지 않는다. 이번은 문서·설계 예시 검사뿐이며 코드/DDL/OpenAPI·서버/자료 변경·앱/DB/provider/Flutter/기기 시험은 없었다. 설계 검토 회신이므로 미push 상태를 명시하고 댓글 전체로 산출물을 제공했다.

## 별도 보존

- #18 설계5fff83b와기록은활동브랜치89a3248에보존. [전체3번째Flutter](https://github.com/heo0328/lostparty-backend/issues/18#issuecomment-6264981603)는접수/별도소비검토대기이며승인아니다. 모집에자동활동추가를섞지않는다.
- #15 [전체9번째Flutter](https://github.com/heo0328/lostparty-backend/issues/15#issuecomment-6263145675) 화면수정8937445 dev/push·사용자기기3항목성공보고. 분쟁인수는별도보류다.
- G3완료구간dev/ce3064f통합·그룹브랜치정리상태유지. #16조건부해산은실제그룹모집원본/정합성후속이다. #17근거검토/#19통계는별도이슈로추적한다.


## 주간 사용횟수 통계 확인 — #19

2026-10-19 읽기확인: [#13전체7번째Flutter 원요구](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6232893737)는#19로이관됐으며아직통계구현/실제집계는없다. 실행DB0016에모집room/round/membership/application표와통계표·통계API가없다. 기존WeeklyState6행중manual완료4행·party완료/활성party는각0이며개인수동체크는모집이용/결과통계로전용하지않는다. 현재한도usage와주간누적이용도분리한다. 통합모집설계의실제생성/참가구간·결과/함께하기이력원천을확보하고#19귀속/마감/coverage정책확정뒤집계·조회로이어간다. 미지원자료는이용0으로보고하지않는다.
