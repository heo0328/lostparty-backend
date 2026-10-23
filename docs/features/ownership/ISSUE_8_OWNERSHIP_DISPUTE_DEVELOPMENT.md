# Issue #8 — V2 소유권 분쟁 구현

2026-10-18. 기준 [141번째 계약 보완](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6237543030) / [142번째 Flutter 최종검토](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6245421798). 현재 REST 계약 원본은 `openapi/openapi.yaml`, 설계 근거는 [V2 기술계약](ISSUE_8_OWNERSHIP_DISPUTE_V2_CONTRACT.md)이다. 구현/게시 SHA·실행 반영과 미확인은 DEV_LOG/결과 댓글로 구분한다.

## 구현 범위

`app/ownership_disputes`: 별도 typed proof/분쟁 모델·11동작·현재 회원의 proof/양측 분쟁 목록/상세·멱등 명령·장비 증거/현재 소유 검사·선택 캐릭터 방어·일괄 종료·기한/세대 fencing·만기 worker.

- 일반 원정대는 기존 서버 수집기와 엄격 receipt/고정 target/roster·6부위/1~3해제/비요청 장비 불변·10분 규칙을 재사용한다. V2는 trusted mock boolean만으로 proof를 발급하지 않는다.
- 타소유 안내 후 새 장비 확인 성공 transaction에서24시간 분쟁을 시작한다. account당 진행 최대3자리·같은 회원 중복·proof당1개를 DB 제약과 공통 game mutation lock으로 보장한다. 네번째 늦은 장비 성공은 passed/blocked이며 분쟁/소유 생성0이다.
- 기존 소유자는 동일 원정대의 현재 usable 캐릭터를 명시 선택한다. 활동/대표/1700/표시 조건은 붙이지 않는다. 방어 성공은 같은 account/owner/revision의 전체 진행 분쟁을 종료하고 방어 generation을 올려 옛 proof를 차단한다. 공통 가장 이른 기한을 넘어서 방어할 수 없고 발급 proof를 자동 연장하지 않는다.
- worker는 DB due scan/30초 lease/generation으로 먼저 성립한 분쟁부터 처리한다. 앞 분쟁 장애/검토필요를 뒤 분쟁으로 우회하지 않는다. provider I/O는 DB 변경 락 밖이며 최종 현재 회원/키·owner/revision·target claim/lifecycle/generation·등록/한도·파티영향을 재검사한다.
- 소유/새 등록/새 unconfigured 설정·이전 설정 종료/감사·그룹 대표 projection revision·분쟁/events/양측 feed/나머지 종료는 하나의 transaction이다. 실패·stale lease·최종 기한 초과는 부분 이전을 남기지 않는다. canonical UUID/claim·이전 개인자료/그룹 회원/그룹장 관계는 보존하며 새 owner에게 권한/자료를 복사하지 않는다.
- `settle`는200 DisputeOut 예약 ACK다. GET은 provider/쓰기 없이 현재 상태를 복원한다. 원명령 ACK와 현재 권한을 구분한다. worker는 새 요청/버튼 없이도 재시작 뒤 DB에서 미완료 건을 재획득한다.
- V1 공개 DTO/멱등형식은 보존한다. 기존 내부 binding을 통한 타인 owner 즉시 변경은 ACCOUNT_BINDING_EVIDENCE_PENDING으로 거절하며 V2 정책 경로를 우회하지 못한다.

## DB·실행 구성

0015_ownership_disputes는 기존표를 변경/삭제하지 않고 ownership_dispute_heads / ownership_member_heads / ownership_control_proofs / ownership_disputes / ownership_dispute_events 다섯 표와 제약/인덱스를 추가한다. slot1..3/현재slot unique·현재actor unique·정확한24h/상태/증거 FK·분쟁 sequence/event revision을 DB에서 보장한다. 모델의 향후 변경이 과거 migration을 바꾸지 않도록 고정 DDL이다.

FastAPI lifespan은 기존 auth cleanup과 별도로5초 주기의 만기 worker를 시작한다. 여러 프로세스에서도 DB lease와 최종 generation이 중복 이전을 차단한다. 격리 테스트는 OWNERSHIP_WORKER_ENABLED=0으로 배경 외부호출을 막고 worker tick/중단·재획득을 직접 검증한다. 로컬 API의 기본 worker는 활성이다. 별도 Redis/새환경·운영배포를 요구하지 않는다.

## 의도한 보류·범위 밖

- 현재 파티 active 관계가 있는데 실제 room 후처리 adapter가 없으면 PARTY_IMPACT_REVIEW_REQUIRED다. 이 범위의 자동 이전은 완료로 보고하지 않는다. 단순 개인manual 완료/과거 완료만으로 현재 참가라 보지 않는다.
- 삭제된 등록을 자동 부활시키지 않는다. direct 등록 한도 초과는 기존 소유 유지·REGISTRATION_LIMIT/재시도이며 등록 공간 회복 뒤 같은 분쟁을 이어간다.
- 운영자 귀속 고정/운영자 도구·Discord·외부push는 후속이다. 상단 방어 안내는 기존 owner/active 조회를 Flutter가 소비하며 새 배너 API/읽음/닫기/상시polling을 추가하지 않았다.
- **V2 자동 자료 정리는 미추가다.** 자동 승인 검토가 종료24h 장비기준 비우기/종료90일 메타데이터 삭제 코드의 추가를 별도 삭제 승인 부재로 거절했다. 사용자에게 대상/영향을 설명했으나 승인 답변은 아직 없다. 핵심 구현을 중단하지 않고 새 V2 자료를 보존한다. 기존 V1 cleanup 정책/기존 회원·원정대·개인자료를 변경하거나 삭제하지 않았다. 설계/초안의90일/24h 정리 제안은 현재 실행 기능으로 읽지 않는다.

## 검증 구분

최종 실행 수치/장애/보완·게시/로컬 반영은 [DEV_LOG](../../project/DEV_LOG.md)를 따른다. 새 V2는 실제 collector/parser를 모의 HTTP와 격리 PostgreSQL로 검증한다. 실제 사용자의 게임 장비 조작/24시간 실경과·Flutter UI/다른기기·운영 인수는 자동검증과 구분한다. 기존 사용자 최초 인증 성공/영어 검색 성공을 미확인으로 되돌리지 않는다.


## 2026-10-18 최종 실행 근거

- 관련194PASS·권한/그룹/주간333PASS 이후 최종 가드21PASS/29.43초. 공통 날짜 기록을 포함한 전체 회귀845건은844PASS/오래된 전체API개수 검사1FAIL/371.47초였다. 검사 수정 후 인증·공통날짜·V2 **58PASS/41.65초**다. 범위 중복을 합산하지 않는다.
- 최종 이미지와 추가 날짜 기록0016을 기존로컬에 반영했다. DB업무48표 공통시각/trigger,실행OpenAPI전체일치,공개HTTP4개200/비로그인V2 11개401을 확인했다. 개발회원 인증쓰기/실게임장비변경·실제24h인수는 수행하지 않았다.
- 0016은V2삭제정책과별개의 [공통날짜기록](../../reference/DATABASE_RECORD_TIMESTAMPS.md)이다. 기존49표행수유지·48표업무내용지문일치이며,검증중기존멱등요청표1곳은적용전변화가있어전체내용동일로보고하지않는다. migration은관리필드외값을갱신하지않는다. 원인·비교한계는DEV_LOG기록을따른다.

구현/계약 SHA `7ba6297c5a574aa14c214bb9d3bf30edb692fc8f` / feat/raid-services push·원격확인완료. [#8 전체144번째 Backend 구현인계](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6245920315) 후 다음담당은Flutter V2 소비/최소UI 연결이다. Backend 완료와 실제기기·운영완료는 구분한다.
