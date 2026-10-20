# 다음 실행

2026-10-20. 현재 **feat/raid-recruitment**, 기존 초안35dd5f9/보완 본문 **e806ee4 로컬 커밋·미push**. main77a1fe5/dev ce3064f 유지. 별도 활동 브랜치 feat/activity-selection/89a3248 보존. 미커밋 변경을 다른 브랜치로 옮기지 않는다.

## 현재 — #13 Flutter46/47번째 수신 / Backend 최종 소비 계약 보완

[계약 고정 초안](../ISSUE_13_FIXED_CONTRACT_DRAFT.md)을 [전체43번째 Backend 회신](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6271860507)에 본문 전체로 게시했다. [Flutter41번째 정정](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6271510136)·[42번째 대조](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6271574011)에 대한 기술 답변이다. 완료는 검토 초안 작성/게시이며 최종 계약·통합 구현·Flutter 적용은 미완료다.

### 다음 담당·완료 조건 — Flutter46/47번째 수신

[46번째 소비 보완](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6282880292)와 [47번째 사용자 결정](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6283062852)을 확인했다. [정책 문서12절](../ISSUE_13_OCT20_POLICY_REVISION.md)에 확정10항목/남은 소비 보완을 기록했다. **다음 담당 Backend**이며 Flutter의 전체 회신 대기는 해소됐다. 이번은 수신/작업 순서 정리로 실제 계약 보완·기술 답변 완료는 아니다.

1. 47번째 확정 정책부터 R2/최종 schema·권한/정족수·효과표에 반영한다. 방 구성원의 레이드 자체 불참 모드를 철회하고 필수/선택 타임과 분리한다. 세션별 정족수 모두 충족 후 원자 적용, 정각부터 마감, 혼합4인 규칙, A완료 상태 표시/B,C 유지, item 단독 탈퇴 금지/묶음 전체 탈퇴를 반영한다.
2. 마지막 개인 완료의 ON/OFF·choice/위임·종료, 방 전체 이번주 미완료 중단·실제 참가자 선언, 자동OFF/06이전·이후 설정 효력, 타임별 묶음 합계24시간을 명시한다. 기존 G를 전부 미정으로 유지하거나 다시 사용자에게 묻지 않는다.
3. 46번째의 nullable 숙련도 실제5종/null, personal-profile 역할 버전 출처 정정, 완전 미정/요일만/요일무제한 조율의 전체 생성 예시, 참가 전 그룹권한 내 필터·최소 projection/공개식별자 대응, 최종 CreateItem·생성/신청/승인 예시와0→1 좌석 adapter를 보완한다. 표 밖 명시참가 허용과 context 밖 조합 거절을 구분한다.
4. N1 변경 제안은 아직 미확정이다. 생성자 수동지정/자동조율 추가인원 최소1과 구분해 필요한 기술 사례만 제시한다. 추가0 채택으로 해석하지 않는다. 기술 상한은 측정/근거로 제안한다.
5. 보완 전문을 #13 게시→Flutter 소비 재대조→정확한 schema/OpenAPI와 통합 구현 R1~R5로 연결한다. 새 서버 테스트/배포 요청은 없다.

P1 최근 성공 snapshot 방향은46번째에서 요구 부합으로 확인했으나 구현/이행·경합 검증은 미완료다. 모집 adapter/route도 여전히 pending이다. 네이티브 소스는 직접 읽지 않는다.

### 보존할 확정 경계·실제 상태

시간 중복은 명시 행동 성공+경고/예약 보존, 자동 후보만 회피한다. 기존 동일 캐릭터 raid/cycle 원장·슬롯/한도/소유·CAS/원 ACK 가드를 유지한다. 초록 pending의 본인 확인은 최신 일정 예약 생성이며 투표와 별도다. 묶음 item B 완료로 A/C 시각을 이동하지 않는다. 기간은 하위 유효값 합계, 앱4와 게임8/단독8을 분리한다.

기존 로컬 F1/F2/F3 코드는 이전 후보이며 새 통합 모델 완료가 아니다. 원본 OpenAPI/main·실행 개발DB0016/API/이미지에는 모집 미반영이다. 기존 101/97/보존25 PASS를 새 초안의 구현 검증으로 쓰지 않는다. 이번은 문서·설계 예시 검사뿐이며 코드/DDL/OpenAPI·서버/자료 변경·앱/DB/provider/Flutter/기기 시험은 없었다. 설계 검토 회신이므로 미push 상태를 명시하고 댓글 전체로 산출물을 제공했다.

## 별도 보존

- #18 설계5fff83b와기록은활동브랜치89a3248에보존. [전체3번째Flutter](https://github.com/heo0328/lostparty-backend/issues/18#issuecomment-6264981603)는접수/별도소비검토대기이며승인아니다. 모집에자동활동추가를섞지않는다.
- #15 [전체9번째Flutter](https://github.com/heo0328/lostparty-backend/issues/15#issuecomment-6263145675) 화면수정8937445 dev/push·사용자기기3항목성공보고. 분쟁인수는별도보류다.
- G3완료구간dev/ce3064f통합·그룹브랜치정리상태유지. #16조건부해산은실제그룹모집원본/정합성후속이다. #17근거검토/#19통계는별도이슈로추적한다.


## 주간 사용횟수 통계 확인 — #19

2026-10-19 읽기확인: [#13전체7번째Flutter 원요구](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6232893737)는#19로이관됐으며아직통계구현/실제집계는없다. 실행DB0016에모집room/round/membership/application표와통계표·통계API가없다. 기존WeeklyState6행중manual완료4행·party완료/활성party는각0이며개인수동체크는모집이용/결과통계로전용하지않는다. 현재한도usage와주간누적이용도분리한다. 통합모집설계의실제생성/참가구간·결과/함께하기이력원천을확보하고#19귀속/마감/coverage정책확정뒤집계·조회로이어간다. 미지원자료는이용0으로보고하지않는다.
