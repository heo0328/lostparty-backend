# 2026-11-17 Backend 작업 통합 기록

사용자 지시: 작업 내역을 문서에 정리하고 현재 목적 브랜치를 dev에 병합·commit/push하며 main도 같은 시점으로 최신화한다. 기준 dev/main은 cda4db3, 통합 대상 refactor/lostark-server-processing의 게시 tip은2d96eed다. 배포·태그 생성·Issue 종료는 이번 범위가 아니다.

## 변경과 검증 원본

| 구간 | 결과·고정 구현 | 근거 |
|---|---|---|
| Issue55 서버 수집·분석 단일화 | b95cff5. 서버 token·공유 제한/장애 억제, 순수 분석·fresh 관찰/항목 ledger·CAS·최신 summary/detail head와 소비 전환. 개인키/클라이언트 업로드·성공값 fallback·과거 실행 제거 | [구현 기록](../features/rosters/power-and-profiles/server-processing-implementation.md), [시험 정리](../engineering/development/current-test-consolidation.md) |
| Issue55 실제 개발 전환 | 사용자 token 공급 확인 및 로컬 lostparty DB 삭제 명시 승인 후0037·개발 API 반영. 기존 볼륨·역할·환경/키·운영 보존. 같은 초기화는 반복하지 않는다 | [실제 준비·반영 기록](../engineering/development/server-analysis-dev-preparation.md), [Backend 전체15](https://github.com/heo0328/lostparty-backend/issues/55#issuecomment-6921019988) |
| 개발용 수동 인증 | 사용자 지정 로컬 등록1건을 저장된 원정대 목록 기준 소유/인증·캐릭터10개/설정 관계로 준비했다. 실제 장비 인증 성공/증거를 생성한 것은 아니다. 운영 영향 없음 | 사용자 요청에 따른 해당 DB 트랜잭션, 코드/제품 인증 정책 변경 없음 |
| Issue56 개인 가능시간1분 | 5172c75. AvailabilityClock1분/ScheduleClock5분·BInterval 공통 참조. 원값/정규화·제출/복사·ACK 보존. 후보/예약·진행시간 정책 재사용 | [변경·검증](../features/recruitment/scheduling/personal-availability-minute-plan.md), [Backend 전체3](https://github.com/heo0328/lostparty-backend/issues/56#issuecomment-6924012652) |

Issue55 최종 수집1,889항목의 분할/재검증 통과 근거와 Issue56 고유122항목 통과는 각각의 범위이며 합산하지 않는다. 도구87PASS·계약 생성 객체 전체 비교·문서/동결자료·compile/diff 검증을 보존한다. 이번 통합 문서 정리에는 문서·diff/병합 일치 검사를 적용하며 관련 변화 없는 서버/DB/전체 시험은 반복하지 않는다.

현재 OpenAPI191경로/211동작, 원본 SHA256 `2f0ae34849e99618e194ad158383091f71967d3c41083d17dfee32a175fd9c9f`。실제 로컬 API는 image `sha256:c720c4388ad15855bb5316baf0b6ff7c91d8981a4e4bca0427b75eb4e4d66013`/DB0037로 지원 완료다. Issue56 반영 시 회원/세션·계정/등록·개인표 전후 행 수와 실제 계약 일치를 확인했다. 운영은 기존v2.3.0/source05daa42/DB0036이며 이번 통합과 구분한다.

## Native 회신과 남은 확인

Native [Issue55 전체22](https://github.com/heo0328/lostparty-backend/issues/55#issuecomment-6924581088)·[Issue56 전체5](https://github.com/heo0328/lostparty-backend/issues/56#issuecomment-6924582578)는901de262 게시·원격 일치·clean, 최종2863PASS/analyze0과 사용자 분 단위 지정 정상 보고다. [Issue56 전체4](https://github.com/heo0328/lostparty-backend/issues/56#issuecomment-6924186599)는 Backend5172c753 명세 고정 hash·현재 wire583정의·직접82PASS 소비 확인이다. Native 결과를 Backend 직접 검증으로 표시하지 않는다.

추가 Backend 변경/반복시험 요청은 없다. 다음 Native/사용자는 실제 저장·제출/복사·야간·상세/교차탭·웹/Android의 미확인 경계를 확인하고 오류 근거를 같은 Issue에 전달한다. Backend는 결과에 대응한다. 분 지정 정상 확인을 실제 provider/저장·기기 전수 인수로 확대하지 않는다. Issue55/56은 OPEN을 유지한다.

## Git 통합 방식

현재 목적 브랜치에 이 기록을 먼저 commit하고 dev에 no-ff merge한다. main은 dev로 ff-only 전진해 두 브랜치를 동일 커밋으로 유지한다. 원격 dev/main도 동일 SHA를 확인하고 완료 목적 브랜치를 로컬·원격에서 정리한다. 공유 이력 재작성/force push는 하지 않으며 다른 미통합 브랜치는 보존한다. 정확한 통합 SHA·게시 결과는 후행 통합 기록에 남긴다.
