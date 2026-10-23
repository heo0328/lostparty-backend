> **보관된 작업 원문:** 아래 현재·다음·미구현 표기는 작성 당시 상태입니다. 현재 설명: [weekly-cycles](../../../../../features/recruitment/weekly-cycles/README.md) · [creation-and-settings](../../../../../features/recruitment/creation-and-settings/README.md) · [participation](../../../../../features/recruitment/participation/README.md) · [scheduling](../../../../../features/recruitment/scheduling/README.md) · [completion-and-records](../../../../../features/recruitment/completion-and-records/README.md) · [membership-actions](../../../../../features/recruitment/membership-actions/README.md) · [search](../../../../../features/recruitment/search/README.md). [문서 대응표](../../../../../engineering/documentation/README.md). 원문 바이트와 근거는 기준 커밋 `7f7f767`에서 확인합니다.

# Issue #13 R3→R5 통합 작업 기록

2026-10-20, feat/raid-recruitment. **구현66244da push·원격확인/[전체58번째 Backend R5 인계](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6287055201) 완료·Flutter 확인 대기**다. 사용자 지시로 R3→R4→R5 네이티브 인계/확인까지 연속 진행한다. 이 문서는 완료 선언이 아니다.

## 구현한 범위

- R3 일정 의도/group/alternative/session, item별 segment·기간 출처, KST 수06시 주차/06~10시 점검·stored 개시+30분 floor, 정각 참가 마감, 본인 확인과 정확한 segment 예약. 명시 시간 중복은 허용+경고, 자동 후보만 busy 회피.
- 세션별 quorum, N1 명시 accept, 전체 대상 원자 적용, 신규 회원 pending 투표·개인표 명시 복사 시 최초 자동 후보 재평가. GET은 적용하지 않음.
- 미래 choice는 현재 assignment/원장을 만들지 않음. 기본 OFF 자동 개시·경계 효력, 권위 시각/worker 처리시각 분리. 지연 자동 개시에서도 floor 보존·동일 개시 noop. 지난 주 미완료는 완료를 만들지 않고 종료·해제.
- R4 AEAD 영향 context(원장·assignment·segment·duration evidence 집합 바인딩), 개인/item 완료·주간 미완료 종료, 명시 keep/release·공대장 해결, 전체 탈퇴/이전/마지막 종료, 원 ACK 우선. 완료한 다른 segment 시각 보존.
- 주간 재개 제안/명시 동의·새 round 세대와 중단 기록 보존. 중단된 일정 의도도 proposal content에 보존하고 새 세션으로 복구한다. null은 기존 의도 유지, []는 명시 미정, 새 groups는 재개 제안의 새 일정 내용이다. 비동의자는 확인 대기다.
- 설정/공개범위·그룹 연결 보존/원자 배치·추방/캐릭터 변경. 신규 문턱이 기존 회원을 소급 추방하지 않음.
- 권한 범위 복수그룹 필터 context·동일인 aliases/opaque member_ref, 그룹OR·회원AND·회원별캐릭터OR를 SQL에서 페이지 전 적용. 공개 요약/참가자 상세·개인목록·그룹 최소 projection/익명 busy·본인 겹침 조회.
- 0022 schedule heads(확정 그래프 이력 보존), 0023 재개 제안은 추가 migration 파일이다. main/준비검사/worker와 원본 OpenAPI를 연결하고 **실행 API8000/개발DB0023에 로컬 반영(2026-10-20 재개 후)**했다. 기존 70개 경로의 operation 계약은 그대로, 모집 44개 경로 추가를 대조했다.

## 확인된 검증

전용 tmpfs PostgreSQL 프로젝트 `lostparty-recruitment-integration-test`만 사용. 제한 LOGIN migration clone과 HTTP 검증이다. 실제 provider/실기기 검증과 다르다.

- typed DTO 포함 일정/완료·반복/검색/관리 24PASS /80.55초.
- 이후 member 읽기·늦은 자동 개시/개시 noop·미래 선택 4PASS /23.80초.
- 세부 실행은 중복 포함이므로 합산하지 않는다. 추가 경계/기존 회귀는 현재 진행 중.
- 테스트에서 발견한 SQL Date 비교, ACK resource enum, MemberHead 필드와 레거시 migration fixture의 원천 경계는 수정했다. 실제 DB 자료를 바꾼 것이 아니다.

## R5 종료 전 남은 조건

1. 최신 코드 회귀 통과, 정각·부분 완료 변경·재개 일정·busy/목록 개인정보/선택 교체 경계 보완. 미실행 부분을 완료로 표시하지 않는다.
2. 기존 정렬·자리 필터 입력 매핑: [#13 전체57번째 Backend 계약 자료 요청](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6286046186). 전체51번째가 요구한 기존 조건을 추정으로 생략/확정하지 않는다. 다음 Flutter는 현재 키/enum·기본/동률 조합을 회신, Backend는 매핑 반영. 아직 동작 테스트 요청이 아니다.
3. 전체 계약/기존 기능 회귀, context 크기/암호·후보 측정 근거 기록, 개발 DB 보존 이행과 이미지/실행 API 계약 확인.
4. 검증된 구간 commit→push→원격 SHA 확인→이슈13 인계/필요 네이티브 테스트 요청→실제 회신 조회. 인계 게시·Flutter 적용·실기기 인수는 별도 상태다.

원본 계약은 R0 기술경계 R4, R0 계약 R3 및 소비 보완서다. 개발 DB/실행 서버 반영·원격 게시·네이티브 인수 전까지 통합 완료로 읽지 않는다.

## 중단 복구 후 확인

중단 전 실행한 전체 회귀 결과를 회수: **1133PASS/1FAIL, 908.94초**. 실패한 과거 한도 사용량 기대값을 실제 집계 계약에 맞춰 수정했다. schedule-context/raid-schedule-overlaps와 다중그룹 projection·권한 회수·반복 each 중복생성 방지·방 제출에 따른 plan 갱신은 중단 직전 보완이므로 별도 최종 회귀에서 확인한다.

AEAD token 합성 실제 발급 크기는 **419 ASCII bytes**이며 내부 영향 집합은 고정길이 SHA-256 digest로 묶어 인원/세그먼트 수가 토큰을 증폭하지 않는다. token 입력 상한4096은 키 ID/인코딩 여유를 포함한 방어 상한이며 실제 최대 부하 측정치라는 뜻이 아니다. 유효시간120초는 사용자 확인 창의 서버 기술값이고 실제 확인 지연을 측정한 정책은 아니다. 만료/원천 변경 시 context 재조회, 같은 성공 key는 원 ACK를 먼저 반환한다. 후보는 현재 주차 최대2016개의 5분 tick을 완전 탐색하므로 이 구현에서 탐색 중단으로 `search_limited`를 반환하는 경우는 없다. `no_candidate`는 조회한 현재 집합에서 완전 탐색 결과다.

## R5 로컬 실행 반영

0016→0023 추가 이행 성공, 기존8000 API healthy·원본 OpenAPI와 실제 이미지 schema 전체 일치. 기존49테이블 중48은 전체 행수/행지문 일치, game_account_requests90행은 행수 동일/지문 차이로 원문 동등성을 증명하지 않는다. 기존30초 cleanup이 지난24시간 요청 결과를 expired로 만들며 record_updated_at도 변경할 수 있는 환경이고 migration은 이 표를 변경하지 않는다. DB 볼륨 초기화/기기·Firebase 삭제/실회원 모집 쓰기·provider 호출은 하지 않았다.

재개 후 최종 관련75PASS/159.28초. 추가 검증은 별도 실행으로 기록하며 이전1133PASS와 중복 합산하지 않는다. 합성키 context1000회 seal/unseal 측정0.0754초, 합성token410bytes(HTTP실제발급419bytes). 성능 숫자는 개발 환경 참고값이다.

최종 추가54PASS/200.83초: 단독 DB모델/DDL 일치·R2 생성/참가/계약·최신 일정 group가드·관계/원장·원천·미래주차. 이전75개와 중복되므로 합산하지 않는다. 전체 회귀1133PASS/1FAIL의 과거 사용량 기대값은 수정 후75개 실행에서 통과했다. 최종 코드 전체를1134PASS로 재표기하지 않는다. 실제8000 readiness0023/health200/공개목록200·원본 OpenAPI 전체일치 재확인, 실제모집 room/weekly occupancy는0으로 실회원 쓰기 없음. 남은 정렬·자리 필터 매핑/Flutter 적용·실기기는 회신 대기다.

## 게시·네이티브 확인 상태

66244da7201cb115a384f4b712fd56f01adfaed7, feat/raid-recruitment push·ls-remote 동일SHA 확인. [#13 전체58번째 Backend·R5 인계](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6287055201) 게시·실제순번조회 및 본문상단최신화완료. 게시후조회시 총58댓글로 Flutter 인계확인/입력매핑회신없음. 다음Flutter 원본계약연동/사용SHA·적용구간회신과 전체57번째정렬·자리wire입력회신, Backend 수신후보완/검증/게시·동일이슈결과답변. 이슈종료/main·dev merge/운영배포는없다. 후행문서기록은구현SHA와구분한다.
