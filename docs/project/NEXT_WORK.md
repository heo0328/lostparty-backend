# 다음 실행

2026-10-20, **feat/raid-recruitment**. R3 일정/예약·미래주차, R4 완료/종료·권한/검색, R5 main/worker·OpenAPI/DB 통합을 구현하고 **로컬 API8000·DB0023에 반영**했다. [상세 구현·검증](../ISSUE_13_R3_R5_IMPLEMENTATION.md). commit/push·원격 확인과 네이티브 인계는 현재 마무리 중이며 게시 결과는 후행 기록을 따른다. main/dev·활동 브랜치는 보존한다.

## 다음 실행·완료 조건

1. Backend 최종 추가 회귀 결과 기록→작업 브랜치 commit/push·원격 SHA 확인→이슈13 인계. 기존 전체 실행1133PASS/1FAIL에서 과거 usage 기대값 실패를 수정했고 관련 최신75PASS/159.28초. 마지막 모델/계약·일정/관계·미래주차 추가54PASS/200.83초. 결과를 중복 합산하지 않는다.
2. **Flutter 입력 회신 필요**: [#13 전체57번째 Backend](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6286046186)의 기존 정렬·자리 필터 키/enum/기본·동률 매핑. 현재 raid/difficulty 및 그룹OR·회원AND·회원별캐릭터OR 검색은 구현/검증했으나 기존 정렬·자리 입력 매핑은 미확인이다. 이 항목을 전체 검색 인수 완료로 표시하지 않는다. 회신 시 같은 브랜치 보완·검증·게시한다.
3. 게시 후 Flutter는 원격 SHA/원본 OpenAPI 기준 실제 연동·변경 구간 확인 결과를 이슈13에 회신. Backend는 실제 회신을 조회하고 필요한 보완 결과를 같은 이슈에 답한다. 인계 게시와 Flutter 적용/실기기 인수는 별도다. 이슈 종료/merge/운영배포는 수행하지 않는다.

## 보존·검증 경계

추가 migration0016→0023 성공, 볼륨 초기화/기기·Firebase 삭제/실회원 모집 쓰기·provider 호출 없음. 기존49테이블 중48행수·지문 동일, 요청 메타데이터90행은 행수동일/지문차이(기존 만료정리 환경)로 원문 보존 증명 한계를 DEV_LOG에 남긴다. 실행 OpenAPI 전체일치·readiness0023·health200/공개 목록GET200 확인. 합성 자동 HTTP/DB 테스트와 실제 네이티브 인수는 구분한다.

## 별도 보존

- #18 설계5fff83b와기록은활동브랜치89a3248에보존. [전체3번째Flutter](https://github.com/heo0328/lostparty-backend/issues/18#issuecomment-6264981603)는접수/별도소비검토대기이며승인아니다. 모집에자동활동추가를섞지않는다.
- #15 [전체9번째Flutter](https://github.com/heo0328/lostparty-backend/issues/15#issuecomment-6263145675) 화면수정8937445 dev/push·사용자기기3항목성공보고. 분쟁인수는별도보류다.
- G3완료구간dev/ce3064f통합·그룹브랜치정리상태유지. #16조건부해산은실제그룹모집원본/정합성후속이다. #17근거검토/#19통계는별도이슈로추적한다.


## 주간 사용횟수 통계 확인 — #19

2026-10-19 읽기확인: [#13전체7번째Flutter 원요구](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6232893737)는#19로이관됐으며아직통계구현/실제집계는없다. 실행DB0016에모집room/round/membership/application표와통계표·통계API가없다. 기존WeeklyState6행중manual완료4행·party완료/활성party는각0이며개인수동체크는모집이용/결과통계로전용하지않는다. 현재한도usage와주간누적이용도분리한다. 통합모집설계의실제생성/참가구간·결과/함께하기이력원천을확보하고#19귀속/마감/coverage정책확정뒤집계·조회로이어간다. 미지원자료는이용0으로보고하지않는다.
