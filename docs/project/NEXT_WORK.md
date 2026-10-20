# 다음 실행

2026-10-20. 현재 **feat/raid-recruitment**, 최신 구현 **1a007eb 로컬 커밋·미push**. main77a1fe5/dev ce3064f 유지. 별도 활동 브랜치 feat/activity-selection/89a3248 보존. 미커밋 변경을 다른 브랜치로 옮기지 않는다.

## 현재 — #13 R2-B 관계·캐릭터/슬롯·주간 원장 내부 연결 / 다음 Backend R2-C

[R2-B 구현기록](../ISSUE_13_R2B_PARTICIPATION_IMPLEMENTATION.md). strict Selection/Target·묶음 전체 assignment/원장 transaction·정밀 역할/P1 성공값/한도·그룹/4인·8인 자리 검사와 정확한 원장 세대 연결을 구현했다. 0021은 새 연결표/복합 FK alias만 추가하며 기존 모든 자료·시각 보존/추정 backfill 없음을 검증했다. 원본 OpenAPI/main·R2-A draft/API8000/개발DB0016은 그대로다. 최종 검증과 Git 상태는 DEV_LOG 기준.

### 다음 담당·완료 조건 — Backend R2-C

1. 생성·직접참가·신청/승인 명령에 R2-B 내부 기반을 연결한다. 기존 레거시 후보 서비스는 구 표만 쓰므로 그대로 새 통합 완료로 보지 않는다. 인증 actor/승인자 권한·현재 room/context/계획 CAS·신청 원본 scope 및 현재 대상 자격·마감/주차를 검사하고 명령 원 ACK와 원자 rollback을 검증한다. R2-B 함수 자체는 HTTP 권한·신청 승인을 부여하지 않는다.
2. 생성/참가 context와 필요한 본인 관계·배치/원장 읽기 및 정확한 required/null·오류/ACK를 구현과 draft OpenAPI에 함께 고정한다. 같은 제품 설계 회신을 다시 요청하지 않는다. 새 코드의 실제 라우터 부분 활성화/구 표 이중 쓰기는 하지 않는다.
3. R3 세션/예약·명시 참여와 시간 경고·자동 후보/제안·정족수/확인·다음주를 연결한다. 개인표 밖 명시 참여와 다른 방 시간 중복은 허용+경고, 자동 후보만 회피한다. 아직 표 저장을 일정 동의/예약으로 추정하지 않는다.
4. R4 부분 완료/전체 탈퇴·종료·리더 해결·정확한 예약 해제·암호화 context/가시 검색·원자성, R5 원본 OpenAPI/main·DB/실제 준비검증→commit/push/원격확인→필요 Flutter 인계를 진행한다. 주간 연결 없는 legacy 검토 자료는 명시 대응 없이 승격/해제하지 않는다.

R2 전체·새 모집 HTTP/통합 기능·Flutter 연결은 미완료다. 현재 네이티브 회신/추가 시험 대기가 아니다. 실제DB0021 이행/서버 재시작·provider/Flutter·기기 검증은 미실행이다.

### 보존할 확정 경계·실제 상태

시간 중복은 명시 행동 성공+경고/예약 보존, 자동 후보만 회피한다. 기존 동일 캐릭터 raid/cycle 원장·슬롯/한도/소유·CAS/원 ACK 가드를 유지한다. 초록 pending의 본인 확인은 최신 일정 예약 생성이며 투표와 별도다. 묶음 item B 완료로 A/C 시각을 이동하지 않는다. 기간은 하위 유효값 합계, 앱4와 게임8/단독8을 분리한다.

기존 로컬 F1/F2/F3 코드는 이전 후보이며 새 통합 모델 완료가 아니다. 원본 OpenAPI/main·실행 개발DB0016/API/이미지에는 모집 미반영이다. 기존 101/97/보존25 PASS를 새 초안의 구현 검증으로 쓰지 않는다. R1-A부터 새 모델/추가 DDL·격리 PostgreSQL 자동검증을 수행했다. 원본 OpenAPI/실행 서버·개발 DB/자료는 바꾸지 않았으며 실provider/Flutter·기기 시험은 미실행이다.

## 별도 보존

- #18 설계5fff83b와기록은활동브랜치89a3248에보존. [전체3번째Flutter](https://github.com/heo0328/lostparty-backend/issues/18#issuecomment-6264981603)는접수/별도소비검토대기이며승인아니다. 모집에자동활동추가를섞지않는다.
- #15 [전체9번째Flutter](https://github.com/heo0328/lostparty-backend/issues/15#issuecomment-6263145675) 화면수정8937445 dev/push·사용자기기3항목성공보고. 분쟁인수는별도보류다.
- G3완료구간dev/ce3064f통합·그룹브랜치정리상태유지. #16조건부해산은실제그룹모집원본/정합성후속이다. #17근거검토/#19통계는별도이슈로추적한다.


## 주간 사용횟수 통계 확인 — #19

2026-10-19 읽기확인: [#13전체7번째Flutter 원요구](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6232893737)는#19로이관됐으며아직통계구현/실제집계는없다. 실행DB0016에모집room/round/membership/application표와통계표·통계API가없다. 기존WeeklyState6행중manual완료4행·party완료/활성party는각0이며개인수동체크는모집이용/결과통계로전용하지않는다. 현재한도usage와주간누적이용도분리한다. 통합모집설계의실제생성/참가구간·결과/함께하기이력원천을확보하고#19귀속/마감/coverage정책확정뒤집계·조회로이어간다. 미지원자료는이용0으로보고하지않는다.
