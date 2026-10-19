# 다음 실행

2026-10-20. 현재 **feat/raid-recruitment**, 설계 본문 **35dd5f9 로컬 커밋·미push**. main77a1fe5/dev ce3064f 유지. 별도 활동 브랜치 feat/activity-selection/89a3248 보존. 미커밋 변경을 다른 브랜치로 옮기지 않는다.

## 현재 — #13 Flutter44번째 소비 검토 수신 / Backend 계약 보완

[계약 고정 초안](../ISSUE_13_FIXED_CONTRACT_DRAFT.md)을 [전체43번째 Backend 회신](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6271860507)에 본문 전체로 게시했다. [Flutter41번째 정정](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6271510136)·[42번째 대조](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6271574011)에 대한 기술 답변이다. 완료는 검토 초안 작성/게시이며 최종 계약·통합 구현·Flutter 적용은 미완료다.

### 다음 담당·완료 조건

[전체44번째 Flutter 소비 검토](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6272050056)를 확인했다. Flutter feature/raid-recruitment-scheduling/6d3f617의 실제 Router/DI·Repository·기존 모델 대조 보고이며 서버/연동/기기 검증은 아니다. 다음 담당은 **Backend**다. 현재 전체 소비 검토 대기는 끝났지만 계약 최종 채택/구현 승인은 아니다.

1. 입력 누락 보완: 자동 확정 추가 인원수, 후보 중 하루/선택일마다 진행, 공대장 최후 출발 제한, 반복 자동 활성화, 기존 숙련도를 요청/응답·소유 자원·수정 경로에 연결한다. 후보 대안을 여러 필수 세션으로 바꾸지 않는다.
2. 식별/버전 보완: proposal 변경 segment를 session별로 묶고 session.revision/schedule_revision, proposal.plan_revision/plan.revision 및 plan CAS id를 구분한다.
3. 버전 출처표: Selection/target_items/policy 값별 GET 출처와 multi-item weekly 의미를 정의한다. 공대장 approve에 신청자 개인 API를 요구하지 않고 권한 내 검토 버전/서버 최신 재검사와 신청 snapshot을 분리한다.
4. 기능 대응표: 공개 목록/상세·본인 신청/참가·신청 검토와 캐릭터 변경/추방/배치·공개범위 전환/반복 설정/choice 조회의 경로·permissions를 정리한다. 기존 인터페이스 존재와 Backend adapter 연결 완료를 혼동하지 않는다. 그룹 복귀 시 옛 외부원/신청 오류로 새 합의를 막지 않는다. 승인방식은 현재 UX의 leader_only/direct_join 두 종류이며 일정 투표와 별개다.
5. 점수 보존: 실패/값 누락/역할 변경 시 최근 성공 수치·관측 시각·버전의 서버 보존 규칙을 G6에 명시한다. nullable 표현 지원은 보존 구현의 증거가 아니다. int/double 반올림·반대 역할/최고값 대체·OFF 강제 갱신 없이 기존 자료 대응을 보완한다.
6. 미정 결정 분리: G1~G7을 최종 채택으로 삼지 않는다. 특히 해당 세션 eligible 참가자가 아닌 공대장 제안자의 표 처리 예시를 추가한다. 세션별 quorum/N1·마감 정각·혼합 구성·부분 종료/중단·자동 기본값/상한은 근거 보완 후 필요한 제품 결정만 분리한다.

Backend가 위 보완본을 #13에 게시한 뒤 Flutter가 소비 가능 여부를 재대조한다. 단순 접수 댓글은 추가하지 않았다. 계약 고정 후에만 R1~R5 통합 구현/검증으로 진행한다. Flutter의 승인된 개인 시간 설정 UI 메모리 미리보기는 API 확정과 독립 가능하다는 보고다. 네이티브 소스를 직접 읽지 않는다.

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
