> **보관된 작업 원문:** 아래 현재·다음·미구현 표기는 작성 당시 상태입니다. 현재 설명: [ownership](../../../../features/rosters/ownership/README.md) · [registration](../../../../features/rosters/registration/README.md). [문서 대응표](../../../../engineering/documentation/README.md). 원문 바이트와 근거는 기준 커밋 `7f7f767`에서 확인합니다.

# Issue #8 — 인증 도전 실행 이력

2026-10-16. [67번째 Flutter 과거 장비 인증 자료](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6210605354)와 [68번째 Backend 검토](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6211222550)에 따른 타소유 도전 기록 보완이다. [착수/최소 설계](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6211452444)를 공유했다. 기존 장비 흐름의 근거는 Flutter `8f4209deb980660e227134bf1241677875d02e06`이며 과거 Android 성공 경험과 현재 Backend live 결과를 구별한다.

## 기록하는 범위

내부 `verification_executions`에 멱등 예약을 통과한 start/confirm/cancel 실행을 기록한다. PK는 기존 명령 ID와 실행 generation이다. 회원 ID·operation·요청 target UUID·인가된 조회 이름·challenge UUID·시작/종료 서버시각·실행 상태·HTTP 상태·결과 code를 보관한다. 등록/기존 challenge에서 읽은 대상 문맥과 그때 연결된 account/owner/revision은 `stored_registration`/`stored_challenge`로, 새 provider 관찰 후 이름 claim에 충돌하는 account/owner/revision은 `provider_observation`으로 출처를 구분한다. 대상 snapshot은 내부 참고 정보이며 이름의 동일성이나 소유권 증거가 아니다. 원본 장비·키·토큰·민감 provider 응답/예외 문구는 저장하지 않는다. 대상 이름 등 이력 정보는 보호되는 DB 안에만 두며 로그/공개 응답에 추가하지 않는다.

성공과 보류/불일치 정상 응답은 업무 변경·명령 결과·이력 종료를 같은 transaction으로 확정한다. 예외로 업무가 rollback되면 별도 transaction에서 해당 실행의 실패 code를 남긴다. 따라서 타소유 이름 claim/binding 보류가 challenge 생성 전에 발생해도 요청/관찰/당시 소유관계·실패 결과가 남는다. 성공 Audit만으로 전체 도전 기록을 대체하지 않는다.

완료 replay·진행 중 동일 명령은 이력을 추가하지 않는다. 실패 후 같은 명령 재실행은 동일 command_id의 다음 generation으로 저장해 이전 실패를 덮지 않는다. 새 generation과 옛 실행은 서로 다른 행이므로 늦은 실패가 새 실행 결과를 덮지 않는다. 요청 target만으로 타회원의 등록/challenge 내부 정보를 복사하지 않으며 이름/문맥 수집 전에 소유 회원을 확인한다.

## 의도한 경계

- 인증/HTTP 입력 검증/멱등 예약 전에 거절된 요청은 기록 대상이 아니다. provider/인가/키/쿼터 등 그 이후 실패는 기록된다. 아직 새 관찰이 없으면 최신 서버/소유자를 추측하지 않는다.
- 이력의 `running`은 실행 결과 미확정이다. 프로세스 종료/DB 자체 장애로 완료 기록을 쓰지 못하면 그대로 남을 수 있고, 실패/성공으로 추정하지 않는다. DB를 쓸 수 없는 상황까지 이력 보존을 보장하는 외부 내구성 시스템은 이번 범위가 아니다.
- 이력은 실행 결과를 나타낸다. `CANCEL_ACKNOWLEDGED`는 취소 API의204 수신 경계를 뜻하며 이미 끝난 challenge를 새로 취소했다고 주장하지 않는다. 이력 시작시각은 명령 실행시각이며 challenge의10분 만료시각을 대신하지 않는다.
- 공개 이력 조회/분쟁 API, 통지·24시간 수동 방어/자동 이전은 추가하지 않는다. 운영 보관/탈퇴 정책은 후속이며 이번에 새로운 자동 삭제 작업을 만들지 않는다.
- live 장비 증거 발급·기존 ID 연결/소유 이전·소멸 확정은 활성화하지 않는다. 사용자 실제 장비 관찰은 나중이며 현재 개발환경/기존자료를 유지한다.

## 구조와 검증

migration `0010_verification_executions`는 테이블/인덱스만 추가하고 기존 행 backfill/삭제는 없다. challenge와 멱등 결과가 기존 정책으로 정리돼도 연결 UUID를 유지하도록 해당 두 자료에는 FK를 두지 않는다. 기존 표식/HTTP path/DTO/code 및 OpenAPI는 불변이다. migration downgrade는 이력 삭제를 막으며 실제 복구는 별도 승인된 범위에서 수행한다.

검증은 격리 PostgreSQL에서 타소유 거절의 기록/이전0·provider 실패/동일명령 재시도·정상 replay/동시중복·장비불일치/증거보류/성공/만료/취소·타회원 대상 비노출·업무 rollback/이력 보존·기존 challenge/명령 정리 후 이력 유지를 확인한다. 실제 실행 수와 이미지/개발 API 반영·원격 게시 여부는 DEV_LOG와 결과 댓글을 따른다. 현재 서버의 실제 장비 인증 성공 테스트와 다르다.

다음 Backend 구간은 기존6부위/1~3해제·Type/Name/Grade·10분 기준을 활용한 live 증거 발급 연결이다. 기존 원정대/캐릭터 ID 연속성과 타소유 이전의 판단은 별도로 유지한다. 추가 Flutter 자료 회신을 기다리지 않는다.

최종 격리 검증300PASS·기존경고1·139.09초. 기존8000/DB0010 적용·기존33테이블 원래 자료 동일/모델정합·실행API healthy/전체OpenAPI 일치 확인. 실제 장비/소유 성공 인수는 미실행이다.

구현 `ccd2e6a28dfb4295dc3f36be972111d4228eeb69`, feat/representative-selection push·원격일치 확인, dev/main 미통합. [70번째 Backend 결과 인계](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6211581766).
