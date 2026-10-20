# 다음 실행

2026-10-20. 현재 **feat/raid-recruitment**, 최신 구현 **fbf1f2f 로컬 커밋·미push**. main77a1fe5/dev ce3064f 유지. 별도 활동 브랜치 feat/activity-selection/89a3248 보존. 미커밋 변경을 다른 브랜치로 옮기지 않는다.

## 현재 — #13 R2-A 개인 가능표·방 제출표 구현 / 다음 Backend R2-B

[R2-A 구현기록](../ISSUE_13_R2A_AVAILABILITY_IMPLEMENTATION.md). 개인 가능표·방 제출표의 strict DTO/정규화·편집 원본 보존/변경 시에만 버전 증가·명시 snapshot 복사·세 CAS·원 ACK·권한/재가입 세대·읽기 무쓰기와 미활성 HTTP 4동작을 구현했다. 기존 R1-B/0020을 사용한다. [미활성 정확한 OpenAPI](../../openapi/recruitment-availability.draft.json)는 구현과 대조하며 원본 OpenAPI/main·API8000/개발DB0016은 그대로다. 구현·최종 검증/Git 상태는 DEV_LOG에 기록한다.

### 다음 담당·완료 조건 — Backend R2-B

1. 지속 membership/캐릭터 선택·item/round/assignment와 WeeklyState를 정확한 세대에 연결한다. 현재 슬롯·한도/소유/CAS·정밀 역할 점수와 P1 최근 성공 값·관측/경고/버전을 함께 검증한다. 구 assignment 해제로 다른 방의 새 점유가 사라지지 않게 한다.
2. 개인표 밖 명시 참여/시간 중복은 허용+경고를 유지한다. R3 일정/예약 응답에서 새 제출표와 기존 일정의 불일치를 표시하고 저장 자체로 일정 동의를 추정하지 않는다. 레거시 검토 전 방/원본 출처 불명 신청을 자동 승격하지 않는다.
3. R2의 나머지 HTTP·오류/ACK를 정확한 draft 계약과 함께 고정한다. 기존 후보 서비스는 이전 표만 쓰므로 이중 집계/이중 쓰기·일부 라우터 실제 활성화는 하지 않는다. 구간/페이지/탐색 상한은 실제 측정 근거로 정한다.
4. R3 예약·후보/제안/정족수·확인·다음주, R4 부분완료/전체종료·암호화context/가시검색·원자성, R5 실제앱/DB·원본계약 통합검증→구현구간commit/push/원격확인→필요 Flutter 인계를 진행한다. 현재 네이티브 설계 재협의/시험 대기가 아니다.

R2 전체·새 모집 통합 기능·Flutter 연결은 미완료다. 실제 DB0020 이행/서버 재시작·provider/Flutter·기기 검증은 미실행이며 별도 회신/동작 시험 요청은 없다.

### 보존할 확정 경계·실제 상태

시간 중복은 명시 행동 성공+경고/예약 보존, 자동 후보만 회피한다. 기존 동일 캐릭터 raid/cycle 원장·슬롯/한도/소유·CAS/원 ACK 가드를 유지한다. 초록 pending의 본인 확인은 최신 일정 예약 생성이며 투표와 별도다. 묶음 item B 완료로 A/C 시각을 이동하지 않는다. 기간은 하위 유효값 합계, 앱4와 게임8/단독8을 분리한다.

기존 로컬 F1/F2/F3 코드는 이전 후보이며 새 통합 모델 완료가 아니다. 원본 OpenAPI/main·실행 개발DB0016/API/이미지에는 모집 미반영이다. 기존 101/97/보존25 PASS를 새 초안의 구현 검증으로 쓰지 않는다. R1-A부터 새 모델/추가 DDL·격리 PostgreSQL 자동검증을 수행했다. 원본 OpenAPI/실행 서버·개발 DB/자료는 바꾸지 않았으며 실provider/Flutter·기기 시험은 미실행이다.

## 별도 보존

- #18 설계5fff83b와기록은활동브랜치89a3248에보존. [전체3번째Flutter](https://github.com/heo0328/lostparty-backend/issues/18#issuecomment-6264981603)는접수/별도소비검토대기이며승인아니다. 모집에자동활동추가를섞지않는다.
- #15 [전체9번째Flutter](https://github.com/heo0328/lostparty-backend/issues/15#issuecomment-6263145675) 화면수정8937445 dev/push·사용자기기3항목성공보고. 분쟁인수는별도보류다.
- G3완료구간dev/ce3064f통합·그룹브랜치정리상태유지. #16조건부해산은실제그룹모집원본/정합성후속이다. #17근거검토/#19통계는별도이슈로추적한다.


## 주간 사용횟수 통계 확인 — #19

2026-10-19 읽기확인: [#13전체7번째Flutter 원요구](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6232893737)는#19로이관됐으며아직통계구현/실제집계는없다. 실행DB0016에모집room/round/membership/application표와통계표·통계API가없다. 기존WeeklyState6행중manual완료4행·party완료/활성party는각0이며개인수동체크는모집이용/결과통계로전용하지않는다. 현재한도usage와주간누적이용도분리한다. 통합모집설계의실제생성/참가구간·결과/함께하기이력원천을확보하고#19귀속/마감/coverage정책확정뒤집계·조회로이어간다. 미지원자료는이용0으로보고하지않는다.
