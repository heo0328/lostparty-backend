# 다음 실행

2026-10-20. 현재 **feat/raid-recruitment**, 최신 계약 보완 본문 **7e9c2f2 로컬 커밋·미push**. main77a1fe5/dev ce3064f 유지. 별도 활동 브랜치 feat/activity-selection/89a3248 보존. 미커밋 변경을 다른 브랜치로 옮기지 않는다.

## 현재 — #13 Flutter49번째 수신 / Backend 필터·명령 context 보완

[계약 고정 초안](../ISSUE_13_FIXED_CONTRACT_DRAFT.md)을 [전체43번째 Backend 회신](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6271860507)에 본문 전체로 게시했다. [Flutter41번째 정정](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6271510136)·[42번째 대조](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6271574011)에 대한 기술 답변이다. 완료는 검토 초안 작성/게시이며 최종 계약·통합 구현·Flutter 적용은 미완료다.

### 다음 담당·완료 조건 — Flutter49번째 최종 소비 대조

[전체49번째 Flutter](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6283395513)를 확인했다. R3의 JSON9개/제품정책/기본상태·숙련도/출처·좌석/승인입력 소비 대조는 완료됐으며 최종API인수/실행코드연결은 아니다. 다음 담당은 **Backend 기술계약 보완**이다. 현재 제시된 제품 선택은 정리됐고 같은 결정을 다시 묻지 않는다.

1. N1 확정 반영: 기존 일정이 있는1인 방 공대장의 명시 본인 확인1표로 변경/예약 원자 적용. 자동조율 추가인원 최소1은 유지하고 추가0 금지. 타인 합류 경합은 잠금 내 현재 대상/N2~8로 재검사한다. GET/무응답/시간경과는 확인이 아니다.
2. 필터 기술계약: 회원 사이AND/회원별 선택캐릭터 내부OR를 보존한다. A:A1/B:B1 선택에 A1+B2 방은 불일치다. 평면 character_ids로 대체하거나 페이지 뒤 로컬 재필터하지 않는다. 복수 groupIds OR·여러그룹 동일회원 합침·그룹권한내 식별/중복·커서와 scope 의미를 명시한다. 그룹 연결과 입장 공개범위를 분리하고 그룹연결 공개방의 group_id/이름/필터를 보존한다.
3. 명령 영향context: 일반 참가자의 방전체주간종료/공대장item전체완료에 타인 개인원장revision 입력을 요구하지 않는다. 권한내 읽기전용 명령context/서명snapshot으로 영향집합을 제공하고 서버가 내부원장 잠금검사, 변경시409전체rollback한다. 개인완료/위임resolution도 정확한GET출처/permissions에 연결한다.
4. 위 보완분 schema/context·예시를#13 인계→Flutter 해당부분만 재대조→원본OpenAPI/구현계약 동시고정/통합R1~R5. 기술상한·측정/저장·이행·동시성 검증은Backend 담당이다.

이번은49번째 수신/작업정리이며 R3를 실제 수정하거나 기술답변을 게시한 상태가 아니다. Flutter 보고는문서예시/소비조사이며 기능코드작업·서버/기기시험이아니다. HEAD6d3f617/문서미커밋·미push 보고, 모집adapter/route연결은미완료다. 변화없는접수댓글은추가하지않고실제기술보완과함께회신한다.

### 보존할 확정 경계·실제 상태

시간 중복은 명시 행동 성공+경고/예약 보존, 자동 후보만 회피한다. 기존 동일 캐릭터 raid/cycle 원장·슬롯/한도/소유·CAS/원 ACK 가드를 유지한다. 초록 pending의 본인 확인은 최신 일정 예약 생성이며 투표와 별도다. 묶음 item B 완료로 A/C 시각을 이동하지 않는다. 기간은 하위 유효값 합계, 앱4와 게임8/단독8을 분리한다.

기존 로컬 F1/F2/F3 코드는 이전 후보이며 새 통합 모델 완료가 아니다. 원본 OpenAPI/main·실행 개발DB0016/API/이미지에는 모집 미반영이다. 기존 101/97/보존25 PASS를 새 초안의 구현 검증으로 쓰지 않는다. 이번은 문서·설계 예시 검사뿐이며 코드/DDL/OpenAPI·서버/자료 변경·앱/DB/provider/Flutter/기기 시험은 없었다. 설계 검토 회신이므로 미push 상태를 명시하고 댓글 전체로 산출물을 제공했다.

## 별도 보존

- #18 설계5fff83b와기록은활동브랜치89a3248에보존. [전체3번째Flutter](https://github.com/heo0328/lostparty-backend/issues/18#issuecomment-6264981603)는접수/별도소비검토대기이며승인아니다. 모집에자동활동추가를섞지않는다.
- #15 [전체9번째Flutter](https://github.com/heo0328/lostparty-backend/issues/15#issuecomment-6263145675) 화면수정8937445 dev/push·사용자기기3항목성공보고. 분쟁인수는별도보류다.
- G3완료구간dev/ce3064f통합·그룹브랜치정리상태유지. #16조건부해산은실제그룹모집원본/정합성후속이다. #17근거검토/#19통계는별도이슈로추적한다.


## 주간 사용횟수 통계 확인 — #19

2026-10-19 읽기확인: [#13전체7번째Flutter 원요구](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6232893737)는#19로이관됐으며아직통계구현/실제집계는없다. 실행DB0016에모집room/round/membership/application표와통계표·통계API가없다. 기존WeeklyState6행중manual완료4행·party완료/활성party는각0이며개인수동체크는모집이용/결과통계로전용하지않는다. 현재한도usage와주간누적이용도분리한다. 통합모집설계의실제생성/참가구간·결과/함께하기이력원천을확보하고#19귀속/마감/coverage정책확정뒤집계·조회로이어간다. 미지원자료는이용0으로보고하지않는다.
