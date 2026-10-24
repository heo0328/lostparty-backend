# Issue26 신청 구성검사 보완·후보계약 협의

2026-10-24 / Backend / feat/raid-recruitment. 원본 [#13 전체142](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6380773556)·[전체143](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6380816312)의 직접 요청은 [#26](https://github.com/heo0328/lostparty-backend/issues/26)에서 이어간다. [#13 전체145번째 Backend 요청 회신/후속 연결](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6381088415)을 게시했고 원본 통합 인수/요구는 유지한다.

## 구현 범위

pending도 기존 확정참가자의 슬롯/정원·직업/역할 제한을 읽기 검증한다. `cycle_admission.admit_bundle`의 pending 전용 `_slot` 생략 및 capacity 생략을 제거했고, `_slot`의 규칙을 read-only `composition_slot`로 분리해 후속 일괄조회에서도 동일 규칙을 재사용할 수 있게 했다. pending이 validate_only로 write phase 이전 반환하는 경계는 유지한다. 기존 context permissions.apply/실제 신청 POST 모두 같은 코어를 사용하며 승인시 최신 검사/잠금·8인 반대파티·C/N·거절/철회·원ACK는 유지한다.

API의 필드/상태코드/component는 불변이며 two-cycle OpenAPI의 기존 context/신청2동작 description만 검증 의미를 명시한다. 기본116·현재two-cycle176 경로,0031 DB 구조는 그대로다. 신규 migration·권한 token/POST 필드는 없다.

## 후보조회는 계약 제안

[읽기 계약 제안1](APPLICATION_CHARACTER_CANDIDATES_PROPOSAL.md)과 [closed schema](design/application-character-candidates.proposal.schema.json)·[합성 작성 예시3개](design/application-character-candidates.proposal.examples.json)를 #26 본문에 제안했다. 사용자 확정 목록 제외4기준을 따르며 전투력/한도 등을 후보정책으로 넓히지 않는다. 신규 endpoint는 합의 전 미구현·실행 OpenAPI에 없음이다. Flutter의 DTO/역할·페이지/빈화면/비동기 차이 회신 후 고정·구현한다.

## 검증과 인계

검증은 별도 internal network/tmpfs PostgreSQL·합성키에서 진행한다. 실제 개발DB/volume·인증키를 mount하지 않는다. 자동시험·전체실행계약/소스이미지 일치 결과와 게시 SHA는 아래 최종 기록을 따른다. 실제 개발 API/DB 반영·실회원 명령/기기 인수는 이번 구간에서 미실행이다. 실제 개발 서버는15e143a/67322372…·176/DB0031 기준이며 이번 코드가 적용된 것으로 표시하지 않는다.

다음 Backend는 합의된 검증 보완의 소스/격리검증 인계 및 후보계약 차이 대응, 다음 Flutter는 계약 제안 소비차이 검토다. 개발서버 반영은 별도 승인 후, 실회원/기기 인수는 반영 후다. IF-001·dev/main/운영·기존자료 보존 유지·Issue26 OPEN이다.

## 최종 검증

[집계](design/issue26-validation-results.json): 고유25PASS(신규16·기존9).0031 제한 LOGIN 격리 DB 신규16건 및 기존 두주차 신청/승인/거절/철회·참가/경쟁8건, legacy 구성/인증활동1건을 확인했다. 분할22PASS/199.37초 +3PASS/26.72초이며 중복 합산하지 않는다. HTTP는 synthetic principal dependency override를 사용하는 실제 FastAPI router에서 context200/구성불가 POST409·no-store와 기존 schema를 확인한 것이며 정상 로그인 HTTP 성공은 아니다.

최초 실행22ERROR는 격리 fixture가 허용하는 test-db 대신 임시 DB alias db를 지정한 환경 오류였다. 동일 임시 DB에 test-db alias/URL을 적용한 뒤 위25건을 통과했다. 제품 수정 실패와 구별하며 실패를 성공 수에 더하지 않는다. 기존 Starlette/AnyIO deprecation 경고1개가 남는다.

후보계약 작성 예시3개와 추가필드/필수누락/역할 reason 일관성·허용역할0/잘못 bool/cursor상한/nullable 금지8개 거절을 closed schema로 검증했다. 이는 제안 정적 검사이며 신규 endpoint 실행/실회원 자료가 아니다.

후보 API 이미지에서 app/alembic Python235파일이 workspace와 일치하고 기본116/두주차176 OpenAPI 전체 일치, 모든 기존 component/DTO 보존·기존2동작 description만 변경을 확인했다. 신규 후보GET은 runtime 계약/라우터에 없다. 실제 개발 API/DB는 교체/이행하지 않았으며 테스트환경 정리 후 실제 상태를 별도 읽기 확인한다.


게시 source `6e0063c7c5a3ff88612bbe1c9b01f50b7408ce2a` commit/push·원격 SHA 일치 확인 후 [#26 전체1번째 Backend · 구성검사 구현/검증·후보계약 인계](https://github.com/heo0328/lostparty-backend/issues/26#issuecomment-6381161170) 전문·전체 순번을 재조회했다. 다음 Flutter는 계약 소비차이 회신, Backend는 차이 대응/합의된 후보조회 구현이다. 기존 API67322372…·DB컨테이너 둘 다 healthy/health200·DB0031을 읽기 확인했고 미교체다. 시험용 runner/DB/internal network를 정리해 기존 API/DB만 남겼다. 새 구성검사 실서버/회원 인수는 별도 개발 반영 후다.
