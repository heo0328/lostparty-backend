# #13 R1-B 추가 원천·P1 최근 성공 보존

2026-10-20 / feat/raid-recruitment / 기준58abf9c. 구현 fbf1f2f 로컬커밋·미push.

공식 결과: [전체53번째 Backend / R1-B 구현](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6284451921). 다음 Backend R2이며 네이티브 시험 요청은 없다.

[설계 대조 완료51번째](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6283811575)와 [R1-A 구현52번째](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6284008917)에 이어지는 내부 구현 구간이다. **저장 원천과 P1 성공 보존까지 구현하며, 통합 모집 HTTP/Flutter 연결 완료가 아니다.** 기존 계약/제품 결정을 다시 요청하지 않는다.

## 구현 범위

- source_models.py의16개 원천: 방 설정, 일정 그룹/세션 연결/대안, 개인 가능표/방 제출표, 세션 참가/구간 예약, 변경 제안/세션별 대상/개인 응답, 다음주 choice/개시 이벤트, 신청 원본, item 설정/구간 기간 정책 출처.
- power_success.py의 역할 성공 snapshot1개를 포함해 신규17개 표를0020_recruitment_sources 추가 이행으로 만든다. R1-A7개와 합치면 통합 원천24개다. SQL은 고정하며0019 및 그 이전 migration을 재작성하지 않는다.
- 기존0019의 방 설정을 최소 기본값으로 연결한다. 숙련도null/문턱null/자동 개시OFF를 유지하고 개인표·제출표·일정/표·choice·개시 이벤트·참가/예약을 자동 생성하지 않는다. 이관된 legacy 방은 계속 검토 상태다.
- 원래 신청 원본의 ID/시각·기록시각/selection/표시·build(null 포함)를 보존한다. F1은 신청 당시 scope를 기록하지 않았으므로 current/creation scope로 접수 원인을 추정하지 않고 legacy_unknown/null로 이관한다. 새로운 신청만 검증된 origin을 기록한다. 기존 pending을 삭제/거절하거나 공개 승인 예외의 증거를 만들어내지 않는다.

## 저장 경계

- 추가0 자동확정 금지, one_of/each·전체주차/선택요일/수동·조율과 nullable 시각 의도를 서로 구분한다. 그룹의 선택 session은 같은 방/그룹의 binding으로만 연결된다.
- 원본 편집 intervals와 normalized_intervals는 별도로 보존한다. 구간 정규화·개인/방별 저장·조회 서비스는 R2에서 구현한다.
- 예약은 동일한 방/참가자/세션/segment/item/round/assignment/회원에 복합FK로 연결한다. 같은 참가/구간에 활성 예약을 중복시키지 않으며 과거 release 후 다른 schedule 버전은 구분해 저장한다. 회원 시간 겹침 배타 제약은 없다. 실제 경고/확정·교체 transaction은 R3/R4다.
- choice는(user,character,raid,target_cycle)와 같은 방/item의 본인 대표 선택을 활성 유일 관계로 유지한다. 다른 캐릭터를 다른 방에서 선택할 수 있고 명시 교체 이력을 보존한다. 미래 assignment/예약을 만들지 않는다.
- 자동 개시의 권위 시각은 대상 주차 수06시, 저장 floor는 그 시각+30분이다. event의 권위/설정 버전·floor는 업데이트로 바꿀 수 없다. 늦은 processed_at과 구분해 저장하며 worker/실제 주차 전환은 아직 구현하지 않는다.
- item의 현재 설정/기간 정책 버전과 segment에 적용한 설정/정책 버전을 분리한다. 설정 변경이 이미 저장한 segment의 기간/시각·출처 버전을 바꾸지 않는다. 실제 합계24h/점검/후보·투표/원장·모든 다중행 도메인 검사는 후속 쓰기 transaction에 추가한다.
- readiness는0018/0019/0020을 명시적으로 구분하고0020 통합 모드에서 모든 추가 원천을 읽기 전용 검사한다. FK의 ON DELETE도 확인해 퇴역 정리를 막는 잘못된 설정을 거절한다. 구조 준비 통과는 모집 활성화나 legacy 검토 완료가 아니다.

## P1 최근 성공값의 실제 보존

P1 put의 기존 공통 game 쓰기 잠금/CAS·idempotency transaction 안에서 head 저장 후 성공 snapshot을 함께 갱신한다. 기존 request/response·P1 GET·개인 표시/설정 payload에는 필드를 추가하지 않는다. 원본 OpenAPI의 API 객체/동작 경계는 유지한다.

성공은 서버가 P1 저장을 수락한 유효한 수치/UTC 관측 쌍이며 source=flutter_analysis의 client 제출값이다. 게임 서버 검증값이라는 뜻이 아니다. 역할/user/character/ownership_revision별로 정확한 문자열·관측·source_summary_version/source_saved_at·같은 관측의 전체 분석/경고를 묶는다.

- 더 최근 관측이면 값이 낮아져도 교체한다. 같은 관측 시각은 더 높은 수락된 head 버전으로 교체한다. 지연된 더 오래된 관측은 head의 기존 저장 의미를 유지하되 성공 snapshot을 과거로 되돌리지 않는다.
- NULL/분석 실패·요청 실패는 직전 성공값을 지우지 않는다. 빌드 경고/오류 자체로 유효 숫자를 버리지 않는다. 정수/double/표시 반올림·역할 대체·과거 최고값 검색·OFF 강제갱신·새 TTL은 없다.
- head CAS 동시 요청은 한 명만 성공한다. commit/lease 실패면 head와 snapshot 모두 rollback하고 같은 key 재시도/원 ACK 복구는 중복 갱신하지 않는다. source/power 버전·관측을 후퇴시키는 snapshot UPDATE도 DB trigger로 거절한다.
- 기존 head만 검증해 유효한 성공 쌍을 초기화한다. 고정 P1 v1 검증으로 NULL/불완전 JSON·불명 시각은 건너뛰고 증명할 수 없는 과거 성공은 복원하지 않는다. 원본 head/기존 모든 자료는 변경하지 않는다.
- 기존 내부 퇴역이 head를 정리할 때 그 head에 종속된 snapshot도 정확히 함께 정리한다(ON DELETE CASCADE). 다른 캐릭터와 거래 rollback은 보존한다. 원래 없던 퇴역 실행 경로를 활성화하거나 실제 자료를 삭제한 것은 아니다.

## 검증 상태

두 실행 모두 통과했다(일부 중복이 있으므로 건수를 합산하지 않는다).

| 실행 | 결과 | 실제 확인 |
|---|---|---|
| 신규 원천/P1 성공·기존 P1/개인표시·R1-A/기존 이행·준비·기록시각 회귀 | 183 PASS / 146.04초 | nullable/역할·소유 세대/더 낮은 최신관측·지연·재송·동시성/commit실패 rollback/퇴역·타 캐릭터 보존·기존 API |
| 최종 source/P1 성공·준비·기록시각 재검증 | 45 PASS / 48.93초 | 기간 정책 출처2개 표 추가 후 최초 이행, seed 시각/ON DELETE 준비 검사·위반 거절, 신규 source 및 원본 OpenAPI 전체 객체 일치 |

새 source 이행은 NOSUPERUSER/NOCREATEDB/NOCREATEROLE LOGIN이 수행하고0020 전 모든 기존 표의 전체행·시각 hash가 이후와 같음을 확인했다. 잘못된 귀속/설정·슬롯/기간·활성예약/choice 충돌은 savepoint rollback으로 검증했다. GET 대신 내부 schema 검사를 SET TRANSACTION READ ONLY로 실행했다. 역할/정밀 문자열·같은 관측의 경고/버전, NULL·실패 보존, 퇴역 cascade와 rollback의 실제 P1 호출도 검증했다.

초기 검증에서 선택 교체 fixture의 중간 autoflush를 수정했다. 넓힌 회귀에서 퇴역 head 정리를 막는 snapshot FK를 발견해 부모와 같은 수명으로 정리되도록 수정하고, cascade 누락 준비 검사/대상 한정·rollback 검증을 추가한 뒤 통과했다. 기존 Starlette DeprecationWarning1건은 남아 있다. 전용 tmpfs PostgreSQL17/제한 LOGIN/합성 자료와 OAuth·provider 모의를 사용하며 원본 데이터/키는 출력하지 않는다. 격리 TestClient·DB 검증은 실행 API/실provider·Flutter/기기 인수와 다르다.

개발 DB0016/실행 API8000·이미지를 이행/재시작하지 않는다.0020은 로컬 코드·격리 이행이며 현재 서버에 새 저장을 반영했다는 뜻이 아니다. 신규 P1 코드의 실제 적용은0020 준비와 묶어야 하며 이미지를 먼저 바꾸고 schema 누락을 무시하지 않는다.

## 다음

R2에서 개인표/제출표와 참가 관계·캐릭터 선택·주간 원장 연결/정확한 HTTP 계약을 구현한다. R3 예약·제안/확인·다음주/R4 완료·전체종료/암호화 context·권한/검색·원자성은 별도 구현·실증 단계다. 같은 설계를 다시 요구하지 않으며 실제 소비 가능한 구간을 commit/push·원격/앱/API/DB 준비 확인 후 필요한 테스트로 인계한다. 이번에는 네이티브 동작 테스트를 요청하지 않는다.
