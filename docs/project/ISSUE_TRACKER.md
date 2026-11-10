# 이슈 주제별 추적표

2026-11-10 KST 기준 열린 이슈4개다. Backend는 현재 서버 코드/Git/실행 근거로 확인하고 Native 구현/잔여 판단은 담당자가 작성한 현재 코드 근거로 기록한다. Issue의 옛 미구현/OPEN 문구를 최신 코드나 종료 상태보다 우선하지 않는다.

## 열린 이슈

| 이슈 | 현재 상태 | 남은 작업·담당 |
|---|---|---|
| [#17](https://github.com/heo0328/lostparty-backend/issues/17) 누락/생명주기·기존 참가 복구 | 완료 오류/기존 계정 복구 인수·양측 dev 통합 완료. Native가 현재 경고/관리 왕복 연결과 별도 누락/부분 완료 기기 경계를 본문에 최신화 | 다음 순차 정리 대상. Backend 현재 구현과 Native 담당 근거로 완료/잔여 범위를 확정. 누락 자료/원복·기기 확인 착수는 별도 후속이며 현재 생성/DB 조정 요청 없음 |
| [#15](https://github.com/heo0328/lostparty-backend/issues/15) 소유권 최종이전 영향 | 기본 인증/분쟁 연결 완료. 활성 참가가 있으면 최종이전 보류, 영향 정리/복구 정책·adapter 미합의/미구현 | Native 소비검토5항목·사용자 제품 정책 결정, 합의 후 Backend 원자 설계. [검토 원본](../features/rosters/ownership/dispute-impact-review.md) |
| [#18](https://github.com/heo0328/lostparty-backend/issues/18) 활동 자동추가·명시제외 | 준비 설계/Native 접수, 영속/API 미합의·미구현 | 신규1700·설정 전 보류·제외/재등록·관찰/경합 기준 합의. [현재 제안](../features/rosters/activity-and-presentation/proposals.md). 옛5fff83b/브랜치 상태는 당시 보고이며 현재 로컬 존재로 단정하지 않음 |
| [#19](https://github.com/heo0328/lostparty-backend/issues/19) 주간 이용 통계 | Native 초안 검토 회신, 집계/조회 미구현 | Backend 확정/제안 분리 초안·집계 예시/원천 대조 보완, 양측·사용자 정책 합의. [현재 원본](../features/raids/statistics/README.md) |

#15/#18/#19의 다음 작업 선택은 전체 정리가 끝난 뒤로 보류한다. 이 표 갱신은 새 기능 구현·계약 확정·대량 회신 승인이 아니다.

<a id="completed"></a>

## 최근 완료·별도 후속

| 이슈/구간 | 완료 근거 | 별도 보존 |
|---|---|---|
| [#47 묶음 선택 완료](https://github.com/heo0328/lostparty-backend/issues/47) completed | 사용자 종료 지시·[전체13번째 Backend](https://github.com/heo0328/lostparty-backend/issues/47#issuecomment-6767992300). Backend44eb4ba/실제 dev·Native47a30dad 및 현재 담당 연결/잔여 없음 확인 | 미보고 기기 경계는 사실대로 보존. 후속 갱신/레드닷·웹소켓·누락 자료를 새 대기로 붙이지 않음 |
| [#48 복구 안내/일정 읽기](https://github.com/heo0328/lostparty-backend/issues/48) completed | 사용자 종료 지시·[전체3번째 Backend](https://github.com/heo0328/lostparty-backend/issues/48#issuecomment-6767764278). Native 현재 연결/추가 구현 없음·Backend 정책3항목 수용 | Native 미게시 후속·새 카드 세부 기기 미확인. Penpot은 Native 차후 후속이며 종료 보류 조건 아님 |
| #17 완료 오류/기존 계정 복구 구간 | [Native52 인수](https://github.com/heo0328/lostparty-backend/issues/17#issuecomment-6756433040)·[Native54 dev 통합](https://github.com/heo0328/lostparty-backend/issues/17#issuecomment-6756668809), Backend dev 통합 aa7058c/후행084a6af | Issue17 전체는 OPEN, 누락 자료/기기와 원래 생명주기 요구 구분 |

#46 백업 요청·#38 초대 검색·#34 릴리즈 협의·#42 활동 해제 참가 보존·#41 일괄 갱신 및 기존 #13 모집1차 등은 각각 사용자 승인 종료 근거를 유지한다. 이 문서 정리에서 재개하거나 새 시험을 요구하지 않는다.

## 코드·게시·실행은 별개

현재 Backend feat/raid-batch-completion/HEAD624ef00, 업무44eb4ba 게시/로컬 지원 완료다. 후행 설명·작업 문서는 미커밋·미push다. Native #47 게시47a30dad와 #48 후속 미게시 변경, #17 dev 통합f79443e2는 담당 보고 범위로 구분한다. 사용자 인수·Git 통합·운영 배포를 서로 대신하지 않는다.

[점검/정리 결과](OPEN_ISSUE_REVIEW.md) · [NEXT_WORK](NEXT_WORK.md) · [DEV_LOG](DEV_LOG.md) · [최신화 전 단계/댓글 순번 기록](../archive/project/status-before-refresh-20261110/ISSUE_TRACKER.md)
