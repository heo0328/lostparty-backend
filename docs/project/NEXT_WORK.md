# 다음 실행

2026-10-20. 현재 **feat/raid-recruitment**, 최신 구현 **fdf2f58 로컬 커밋·미push**. main77a1fe5/dev ce3064f 유지. 별도 활동 브랜치 feat/activity-selection/89a3248 보존. 미커밋 변경을 다른 브랜치로 옮기지 않는다.

## 현재 — #13 R1-A 통합 원천·보존 이행 구현 / Backend 후속 구현

[계약 고정 초안](../ISSUE_13_FIXED_CONTRACT_DRAFT.md)을 [전체43번째 Backend 회신](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6271860507)에 본문 전체로 게시했다. [Flutter41번째 정정](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6271510136)·[42번째 대조](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6271574011)에 대한 기술 답변이다. 완료는 검토 초안 작성/게시이며 최종 계약·통합 구현·Flutter 적용은 미완료다.

### 다음 담당·완료 조건 — R1-A 실제 구현 완료

[51번째 Flutter 설계대조완료](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6283811575) 이후 [R1-A 통합원천/보존이행](../ISSUE_13_R1_STORAGE_IMPLEMENTATION.md) **fdf2f58 로컬커밋·미push**를 구현했다. [전체52번째 Backend](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6284008917)에 결과/미완료를 기록했다. 다음 담당은 계속 **Backend 구현**이며 네이티브 테스트/재설계 회신 대기가 아니다.

1. R1-B: 설정/일정그룹·참여/예약/제안/choice/개시이벤트·P1최근성공 snapshot 등 나머지 원천/보존을 구현한다. 이번7개 표는 R1-A이며 R1 전체 완료가 아니다.
2. R2: 개인표/제출표·관계/캐릭터선택·WeeklyState의 정확한 귀속/증가한도·원 ACK를 새 원천에 연결한다. legacy 후보 서비스는 아직 기존 표만 쓰므로 원천전환 전 이중쓰기/이중집계하지 않는다. 이전 일정은 legacy_review_required/예약없음이며 근거 없는 동의·완료를 만들지 않는다.
3. R3/R4: 예약·정족수/확인·다음주, 부분완료/방전체종료·권한·암호화context·필터/원자성을 구현한다. 51번째에서 확인한 두 경계의 설계를 다시 요청하지 않는다.
4. HTTP 구간에서 정확한 required/null/권한·거절/오류/ACK·기존raid/difficulty·정렬/자리필터와 측정상한을 OpenAPI/구현에 함께 고정한다. R5 실제앱/DB·계약 검증→구현구간 commit/push/원격확인→필요한Flutter동작 인계를 한다.

실제검증: 격리tmpfs PostgreSQL17·제한LOGIN 계정의0018→0019/전체기존행·시각hash보존/표시·빌드snapshot·잘못된귀속/슬롯/기간rollback·읽기전용구조검사/기존준비회귀 **33PASS/28.78초**. 모의provider/합성자료이며 실행서버·실provider/Flutter/기기검증은 아니다. 사용한 전용테스트환경은정리하고원래테스트DB는중지상태로돌렸다.

실행 main/API8000·개발DB0016·이미지/자료와 원본OpenAPI는미변경/모집미활성이다. 새0019는로컬migration/격리검증만완료했다. 구조검사통과가데이터확인/통합서비스활성화를뜻하지않는다. 해당작업의commit/push/실제API시험인계는묶은소비가능구간에서진행한다.

### 보존할 확정 경계·실제 상태

시간 중복은 명시 행동 성공+경고/예약 보존, 자동 후보만 회피한다. 기존 동일 캐릭터 raid/cycle 원장·슬롯/한도/소유·CAS/원 ACK 가드를 유지한다. 초록 pending의 본인 확인은 최신 일정 예약 생성이며 투표와 별도다. 묶음 item B 완료로 A/C 시각을 이동하지 않는다. 기간은 하위 유효값 합계, 앱4와 게임8/단독8을 분리한다.

기존 로컬 F1/F2/F3 코드는 이전 후보이며 새 통합 모델 완료가 아니다. 원본 OpenAPI/main·실행 개발DB0016/API/이미지에는 모집 미반영이다. 기존 101/97/보존25 PASS를 새 초안의 구현 검증으로 쓰지 않는다. R1-A부터 새 모델/추가 DDL·격리 PostgreSQL 자동검증을 수행했다. 원본 OpenAPI/실행 서버·개발 DB/자료는 바꾸지 않았으며 실provider/Flutter·기기 시험은 미실행이다.

## 별도 보존

- #18 설계5fff83b와기록은활동브랜치89a3248에보존. [전체3번째Flutter](https://github.com/heo0328/lostparty-backend/issues/18#issuecomment-6264981603)는접수/별도소비검토대기이며승인아니다. 모집에자동활동추가를섞지않는다.
- #15 [전체9번째Flutter](https://github.com/heo0328/lostparty-backend/issues/15#issuecomment-6263145675) 화면수정8937445 dev/push·사용자기기3항목성공보고. 분쟁인수는별도보류다.
- G3완료구간dev/ce3064f통합·그룹브랜치정리상태유지. #16조건부해산은실제그룹모집원본/정합성후속이다. #17근거검토/#19통계는별도이슈로추적한다.


## 주간 사용횟수 통계 확인 — #19

2026-10-19 읽기확인: [#13전체7번째Flutter 원요구](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6232893737)는#19로이관됐으며아직통계구현/실제집계는없다. 실행DB0016에모집room/round/membership/application표와통계표·통계API가없다. 기존WeeklyState6행중manual완료4행·party완료/활성party는각0이며개인수동체크는모집이용/결과통계로전용하지않는다. 현재한도usage와주간누적이용도분리한다. 통합모집설계의실제생성/참가구간·결과/함께하기이력원천을확보하고#19귀속/마감/coverage정책확정뒤집계·조회로이어간다. 미지원자료는이용0으로보고하지않는다.
