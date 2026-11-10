# 2026-11-10 문서 최신화 직전 상태 기록

현재 정보는 [현재 진행 문서](../../../project/OPEN_ISSUE_REVIEW.md)를 따른다. 아래는 최신화 직전 내용을 보존한 이력이며 상대 링크만 보관 위치에 맞춰 조정했다.

---

# 열린 이슈 점검 — 2026-11-10

GitHub heo0328/lostparty-backend의 is:issue 검색 결과 열린6개/닫힌25개를 확인했다. 열린6개는 개별 본문·전체 댓글을 조회했고 닫힌25개는 검색 결과의 종료/이관 요약만 대조했다. PR은 제외했다. 이번은 현황 조사이며 Issue 본문/댓글/종료·상태 변경이나 코드/서버/DB 실행을 하지 않았다.

## 현재 변경 — Issue47도 종료, 열린4개

사용자 지시로 #47을 [전체13번째 Backend 종료 기록](https://github.com/heo0328/lostparty-backend/issues/47#issuecomment-6767992300)과 함께 completed 종료했다. #48도 completed이며 남은 열린 이슈는 #17/#15/#18/#19다. #47 양측 구현/연결·계약/지원 대기는 없고 별도 후속/미보고 기기·미게시 범위는 원래 사실대로 보존한다. 다음 #17 정리, #15/#18/#19 선택은 전체 정리 후다. 아래 열린6개/5개/마감 가능 표기는 각 당시 기록이다.

## 현재 변경 — Issue48 종료, 열린5개

사용자 명시 지시로 #48을 completed 종료했고 [전체3번째 Backend 종료 기록](https://github.com/heo0328/lostparty-backend/issues/48#issuecomment-6767764278)·closed/completed를 확인했다. Penpot 디자인은 Native 차후 후속이며 종료 보류 조건이 아니다. Native 미게시/새 카드 세부 기기 미확인은 별도로 보존하되 추가 수용 대기는 없다. 아래 최초 열린6개 표는 점검 당시 기록이며 #48은 현재 닫혔다. 다음 #47→#17 정리, #15/#18/#19 선택은 전체 정리 후다.

## 순차 정리 기준·현재 구간

사용자 정정: 최신 상태는 현재 코드에 근거한다. **Backend는 Backend 코드/정책만 확인하고 Native 구현/완료 여부는 Native가 작성한다.** Backend의 원격 Native 코드 대조로 담당 측 판정을 대신하지 않는다. Native 게시 기준과 미커밋 변경의 확인 범위를 분리한다. 아래 기존 점검의 Native 상태는 이슈에 기재된 담당 측 보고이며 독립 코드 검증 결론이 아니다.

#15·#18·#19의 다음 작업 선택은 정리가 모두 끝난 뒤로 보류한다. 순서는 #48→#47/#17의 완료/잔여 범위 정리다. Issue 종료는 별도 지시 대상으로 유지한다.

현재 #48의 최신 본문은 사용자 버그 해결 보고·카드 디자인의 차후 Penpot 분리·Native 미게시 변경을 명시한다. 앞선 점검의 즉시 카드 디자인 인수 대기는 최신 사용자 결정으로 대체됐다. Backend가 Native 완료를 판단하거나 재인수를 요구하지 않는다.

- [전체1번째 Backend Native 현황 작성 요청](https://github.com/heo0328/lostparty-backend/issues/48#issuecomment-6767533595): 실제 연결 위치·남은 코드·브랜치/게시 SHA와 미게시 범위·기존 검증/사용자 확인·잔여 완료 조건은 Native가 현재 코드 기준으로 작성한다. 기존 본문과 동일 시험 반복/자동 게시 요청이 아니다.
- [전체2번째 Backend 정책3항목 확인](https://github.com/heo0328/lostparty-backend/issues/48#issuecomment-6767569951): 현재 서버 업무44eb4ba/HEAD624ef00 기준 시간 마감과 기존 완료·탈퇴/해산·일정 제안/조회 구분, 실제 주차 독립/예외 상태와 plan 권한을 확인했다. 코드/시험 변경0, 새 시험/실자료 실행 없음. Backend 회신 완료.
- 다음 #48은 Native 담당 작성 결과를 받은 뒤 잔여 정리 범위를 확정한다. #47/#17도 Native 관련 판단은 담당 작성 결과에만 근거한다. #15/#18/#19 새 구현이나 정책 선택은 시작하지 않는다.

### Issue48 담당 확인 수신

[최신 Native 본문](https://github.com/heo0328/lostparty-backend/issues/48)에 현재 로컬 코드의 파일/함수·실제 연결·미게시 범위·검증과 잔여 조건이 작성됐다. 새 댓글 없이 전체2댓글 유지다. Native는 추가 구현/미연결·새 Backend 계약 대기 없음을 명시했고 Backend 정책3항목을 수용했다. 이번 양측 현황/정책 정리는 완료됐으며 Native 미커밋 코드 게시·새 카드 기기 미확인·차후 Penpot은 각각 별도다. 이 수신 후 사용자 명시 지시로 completed 종료했다. 위 작성 대기는 해소됐으며 다음 #47/#17로 이어간다.

### Issue47 현재 코드 정리 착수

[전체12번째 Backend](https://github.com/heo0328/lostparty-backend/issues/47#issuecomment-6767821672) 기준 현재 app/tests/openapi422파일은 구현44eb4ba와 동일, 실제 origin/HEAD624ef00·실행 ae6b3e0a healthy/앱288파일 일치를 확인했다. 기존 검증/전체 계약 근거는 재사용하고 새 시험은 없다. Native 최신 본문에 ACK 수용/추가 Backend 요청 없음은 이미 작성돼 있으므로 반복 대조를 요청하지 않았다. 묶음 고유 연결 위치·추가 구현/미연결 여부를 Native 담당이 보완하도록 요청했다. 수신 후 #47 범위를 마감 판단하며 #48/차후 Penpot을 보류 조건으로 붙이지 않는다. 다음 #17, #15/#18/#19 선택은 정리 완료 뒤다.

### Issue47 Native 보완 수신 — 마감 가능

[Native 본문](https://github.com/heo0328/lostparty-backend/issues/47)에 현재 코드의 전체 연결 위치와 잔여 구현/미연결 없음이 담당 작성됐고 Backend 현재 코드 확인도 수신했다. #48 미게시 후속과 #47 원명령/ACK 의미가 분리되며 핵심5파일 diff0은 Native 확인으로 기록한다. 새 댓글 없이 전체12개다. 양측 즉시 확인/구현 대기는 없고 별도 후속은 종료를 막지 않는다. 이후 사용자 지시로 #47 completed 종료를 확인했다. 다음 #17 정리다.

## 현재 남은 작업

| 이슈 | 실제 상태 | 남은 일·다음 담당 | 정리 판단 |
|---|---|---|---|
| [#48](https://github.com/heo0328/lostparty-backend/issues/48) 복구 안내·일정 읽기 | Native 카드/읽기 분리 구현·2913PASS/analyze0 보고. HEAD47a30dad 위 미커밋. 댓글0개이며 최신 근거는 본문 | 양측 담당 작성/정책 수용 완료. Native 미게시 코드·새 카드 기기 미확인·차후 Penpot은 별도. 종료/게시 지시는 별도 | 사용자 승인 completed 종료. 별도 Native 디자인 후속 보존 |
| [#47](https://github.com/heo0328/lostparty-backend/issues/47) 묶음 선택 완료 | 양측 구현/게시, Backend 실제 dev 지원. Native2911PASS·사용자 보고 범위 정상화. 전체11번째 Backend로 ACK 질문 답변 완료 | 미보고 제품 경계의 인수 범위를 구분해 마감 판단. 공통 복구 UX는 #48과 범위 구분 | 새 Backend 구현/계약 회신 대기는 없음. 전체 인수 완료 근거 없이 즉시 종료하지 않음 |
| [#17](https://github.com/heo0328/lostparty-backend/issues/17) 캐릭터 누락/복구 | 완료 오류·기존 계정 복구 구간은 사용자 인수/양측 dev 통합까지 완료. Native 최신54번째 통합 보고 | 누락 캐릭터/부분 완료의 개발 자료 준비·해당 기기 경계가 남음. 원래 소멸 확정 근거/이력·이름 재사용 계약과 완료된 복구 구간을 구분해 범위 확정 | 완료/미완료가 혼재. 묶음 완료 미구현 표기는 #47 구현으로 낡았으므로 링크/상태 정리 필요. 원요구 전체를 완료로 확대하지 않음 |
| [#15](https://github.com/heo0328/lostparty-backend/issues/15) 소유권 이전 영향 | 기본 인증/분쟁 연결 완료. 최종 소유권 이전 시 활성 레이드 영향 정책은 미합의/후처리 미구현 | Native: 영향/복구 소비 검토5항목. 사용자·양측: 자동정리 또는 영향참가 복구 정책 확정. Backend: 합의 후 원자 처리 설계 | 장기 계약 대기. 활성 참가가 있으면 PARTY_IMPACT_REVIEW_REQUIRED 보류 유지. 기초 인증 재개발 대상 아님 |
| [#18](https://github.com/heo0328/lostparty-backend/issues/18) 활동 자동추가·명시제외 | Backend 준비 설계, Native 접수까지. 영속 모델/API 미합의·미구현 | Native/사용자: 신규1700 기준·설정 전 보류·명시제외·관찰/경합·재등록5항목 결정. Backend: 최신 기준과 초안 재대조 후 구현 단위 확정 | 장기 계약 대기. 기존 수동 활동 설정은 완료 기능으로 구분 |
| [#19](https://github.com/heo0328/lostparty-backend/issues/19) 이용 통계 | Native가 초안에 대한 미확정 정책을 회신했고 Backend 후속 댓글 없음. 집계/조회 미구현 | Backend: 확정/제안 분리한 최종 초안·유형 변경/탈퇴/경계/복수회차 예시·실제 원천 범위 대조. 사용자·양측: 귀속/함께/평균분모/조회권한 확정 | Backend 쪽 초안 보완이 남음. 모집 #13 완료와 통계 완료를 구분 |

## 정리되지 않은 기록

1. ISSUE_TRACKER 상단은 #47 Native 연결 미완료 등 이전 상태를 최신으로 표시하고 #48이 없다. 이번 점검 색인을 최상단에 연결하고 이전 본문은 역사 기록으로 보존한다.
2. #17 본문 상단은 완료 복구와 별도 원요구가 함께 있고 묶음 완료를 미구현으로 적는다. #47의 최신 구현/게시 근거와 연결해야 한다. Native54 dev 통합도 기존53 게시 요약보다 뒤의 근거다.
3. #18 본문은 Backend 설계2번째 이후 Native3번째 접수를 반영하지 못한다. 또한 이슈의 docs/ISSUE_18_ACTIVITY_SELECTION_DESIGN.md 경로는 현재 정식 [활동 제안](../../../features/rosters/activity-and-presentation/proposals.md) 안내와 맞춰야 한다.
4. #19는 Native1번째가 Backend 최종 초안/예시를 요청했으므로 단순 Native 검토 대기로만 두면 담당이 뒤바뀐다. 이슈의 옛 통계 문서 경로도 [현재 통계 안내](../../../features/raids/statistics/README.md)와 연결이 필요하다.
5. #15의 옛 실행 이미지/DB0035 표기는 검토 당시 근거이며 현재 서버 정보로 쓰면 안 된다. 최신 소비 회신은 없는 상태다.
6. 즉시 종료가 확실한 이슈는 이번 근거만으로 확정하지 않았다. #47은 마감 검토에 가깝고, #17은 완료 복구 구간을 분리해 잔여 범위를 정리할 필요가 있다. #48/#15/#18/#19는 명시적인 미완료가 있다.

## 제안 순서

1. #48 Backend 정책 답변을 마무리한다. 사용자 화면 인수·Native 코드 게시 상태는 별도로 관리한다.
2. #47/#17은 완료 근거·이관 링크·잔여 완료 조건을 정리한 뒤 사용자 종료 지시 범위에서 마감 판단한다. 동일 정상 시험을 일괄 반복하지 않는다.
3. #15/#18/#19 중 다음 제품 우선순위를 선택해 계약 대기를 해소한다. 이 점검을 새 기능 구현/대량 회신 승인으로 해석하지 않는다.

## 조회 근거

- #48: 현재 본문/체크리스트, 댓글0.
- #47: [전체10번째 Native 보완/게시](https://github.com/heo0328/lostparty-backend/issues/47#issuecomment-6766130657), [전체11번째 Backend ACK 답변](https://github.com/heo0328/lostparty-backend/issues/47#issuecomment-6766235882).
- #17: [전체52번째 사용자 인수](https://github.com/heo0328/lostparty-backend/issues/17#issuecomment-6756433040), [전체54번째 Native dev 통합](https://github.com/heo0328/lostparty-backend/issues/17#issuecomment-6756668809).
- #15: [전체10번째 Backend 영향 소비검토 요청](https://github.com/heo0328/lostparty-backend/issues/15#issuecomment-6541847499), 후속 댓글 없음.
- #18: [전체3번째 Native 접수/검토 대기](https://github.com/heo0328/lostparty-backend/issues/18#issuecomment-6264981603).
- #19: [전체1번째 Native 미확정 정책/초안 요청](https://github.com/heo0328/lostparty-backend/issues/19#issuecomment-6259127594).

운영 반영·미보고 기기 경계를 개발 구현/자동 검증과 혼동하지 않는다. Git 변경은 기존 feat/raid-batch-completion의 후행 문서에 누적하며 commit/push는 하지 않았다.
