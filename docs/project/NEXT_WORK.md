# 다음 실행

2026-10-20. 현재 **feat/raid-recruitment**, 최신 구현 **d25c26b 로컬 커밋·미push**. main77a1fe5/dev ce3064f 유지. 별도 활동 브랜치 feat/activity-selection/89a3248 보존. 미커밋 변경을 다른 브랜치로 옮기지 않는다.

## 현재 — #13 R2-C 기본 생성·참가/신청·승인 명령/HTTP / 다음 Backend R3

[R2-C 구현기록](../ISSUE_13_R2C_ADMISSION_IMPLEMENTATION.md). 미정(schedule_groups=[]) 방의 생성·즉시참가·신청/승인·거절/본인 철회와 선택 context·본인 plan/최소 신청·권한별 관리 검토를 명령 transaction/원 ACK·정확한 미활성 HTTP 10동작에 연결했다. [정확한 draft](../../openapi/recruitment-admission.draft.json)는 구현과 전체 대조한다. 관련 회귀81PASS/164.09초, 최종 R2 HTTP11+관계13+가능표17 =41PASS/127.98초(일부중복, 합산안함). 원본 OpenAPI/main·실제API8000/개발DB0016은 유지하며 아직 통합 기능·Flutter 적용 완료가 아니다. 현재 커밋/Git·Issue 기록은 DEV_LOG 기준.

### 다음 담당·완료 조건 — Backend R3 일정/예약·확인·미래 주차

1. 미정/요일만/무요일 자동 조율의 일정 의도와 group/alternative/session을 명세대로 저장·복원한다. item별 유효 기간/출처·세션별 합계1440, 현재 주차/KST수06시·점검[06,10)/10시 이후·stored 개시floor/정각 마감을 검증하고 R2-C 생성/참가에 연결한다. nonempty schedule_groups/세션은 지금503으로 보호되므로 성공 처리나 임의 생성을 하지 않는다.
2. R3 신규 임계치와 기존 회원 본인 확인을 구분해 participation/정확한 segment 예약·일정 밖/중복 시간 경고를 연결한다. 명시 참여는 허용+경고/기존 예약 유지, 자동 후보만 busy를 회피한다. N1 기존 일정의 본인 명시 accept는 확정 적용1, GET/제안 생성 자동 찬성으로 대체하지 않는다.
3. 후보·제안/표·대상 집합·세션별 정족수/동시 원자 적용과 choice·자동개시 기본OFF/경계 효력·실제 권위 시각·처리시각/late worker를 구현한다. 한도/후보 탐색 상한은 측정 근거로 고정하고 no_candidate/search_limited를 구분한다.
4. 이어 R4 개인/item완료·묶음 전체 탈퇴/종료·리더 해결·예약 해제·권한별 목록/검색·AEAD command context/원자성, R5 준비 검사·원본 OpenAPI/main/실제DB 통합→commit/push/원격 확인→필요 Flutter 동작 인계를 진행한다. 생성/신청 선택 MAC는 R4 완료/종료용 AEAD context를 대체하지 않는다.

현재 네이티브 재설계 회신/동작시험 대기는 아니다. 신규 migration 없이0021 원천 사용, 실제DB 이행/서버 재시작·provider/Flutter·기기 검증은 미실행이다. legacy 후보 서비스/원천은 유지하며 새로운 모집 API를 부분 활성화하거나 이중 쓰기하지 않는다.

### 보존할 확정 경계·실제 상태

시간 중복은 명시 행동 성공+경고/예약 보존, 자동 후보만 회피한다. 기존 동일 캐릭터 raid/cycle 원장·슬롯/한도/소유·CAS/원 ACK 가드를 유지한다. 초록 pending의 본인 확인은 최신 일정 예약 생성이며 투표와 별도다. 묶음 item B 완료로 A/C 시각을 이동하지 않는다. 기간은 하위 유효값 합계, 앱4와 게임8/단독8을 분리한다.

기존 로컬 F1/F2/F3 코드는 이전 후보이며 새 통합 모델 완료가 아니다. 원본 OpenAPI/main·실행 개발DB0016/API/이미지에는 모집 미반영이다. 기존 101/97/보존25 PASS를 새 초안의 구현 검증으로 쓰지 않는다. R1-A부터 새 모델/추가 DDL·격리 PostgreSQL 자동검증을 수행했다. 원본 OpenAPI/실행 서버·개발 DB/자료는 바꾸지 않았으며 실provider/Flutter·기기 시험은 미실행이다.

## 별도 보존

- #18 설계5fff83b와기록은활동브랜치89a3248에보존. [전체3번째Flutter](https://github.com/heo0328/lostparty-backend/issues/18#issuecomment-6264981603)는접수/별도소비검토대기이며승인아니다. 모집에자동활동추가를섞지않는다.
- #15 [전체9번째Flutter](https://github.com/heo0328/lostparty-backend/issues/15#issuecomment-6263145675) 화면수정8937445 dev/push·사용자기기3항목성공보고. 분쟁인수는별도보류다.
- G3완료구간dev/ce3064f통합·그룹브랜치정리상태유지. #16조건부해산은실제그룹모집원본/정합성후속이다. #17근거검토/#19통계는별도이슈로추적한다.


## 주간 사용횟수 통계 확인 — #19

2026-10-19 읽기확인: [#13전체7번째Flutter 원요구](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6232893737)는#19로이관됐으며아직통계구현/실제집계는없다. 실행DB0016에모집room/round/membership/application표와통계표·통계API가없다. 기존WeeklyState6행중manual완료4행·party완료/활성party는각0이며개인수동체크는모집이용/결과통계로전용하지않는다. 현재한도usage와주간누적이용도분리한다. 통합모집설계의실제생성/참가구간·결과/함께하기이력원천을확보하고#19귀속/마감/coverage정책확정뒤집계·조회로이어간다. 미지원자료는이용0으로보고하지않는다.
