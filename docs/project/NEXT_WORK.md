# 현재 작업과 다음 실행

기준일 2026-10-17. 현재 사용하던 로컬 Docker/포트8000·개발자료로 개발을 계속한다. 기본 앱 실행·로그인·키·등록/갱신·인증 완료를 유지하며 새 환경·초기 설정·기본 기능 재인수로 되돌리지 않는다.

## 현재 완료 구간과 통합

- Backend #8의 대표/활동 정책, 캐릭터 생명주기·현재/이력 조회, 역할 요약·개인 설정/표시, 인증 실행 이력·서버 장비 증거, 본인 목록 갱신/조회 기준 복구, 인증 대상 선택, 장비 분류 호환, 현재 소유자 차단·같은 회원 재등록 연결까지 이번 구간 완료다.
- 최신 구현/계약은 `19c2dcc33630078fa0d88a1dd60e11857a44472b`. [105번째 Backend 인계](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6228173800), [현재 소유자 정책](../ISSUE_8_CURRENT_OWNER_POLICY_DEVELOPMENT.md)이 기준이다. 현재 본인 유효인증의 start/pending confirm은409 ALREADY_VERIFIED, 타회원/소유상실 도전은 허용·장비 확인 후 소유 연결 보류, 완료된 원명령 ACK/현재GET은 유지한다. 같은 회원의 삭제 후 재등록은 확인 가능한 기존 소유에 장비 재인증 없이 연결한다.
- 최종 관련 격리 PostgreSQL/모의HTTP **483PASS**와 실행 OpenAPI 일치가 검증 기준이다. 이번 문서·통합 작업은 기능 코드를 변경하지 않으며 동일 코드의 테스트를 반복하지 않는다.
- [98번째 실제1회 인증 성공](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6217275533)은 사용자 결과와 서버verified/현재소유/감사1개를 대조했다. 새 정책의 모든 기기 경합/삭제재등록·분쟁 인수까지 확인한 결과는 아니다.
- 사용자가 현재 구간의 문서 최신화·dev 병합/push·main 동기화·작업 브랜치 정리를 승인했다. 현재 `feat/representative-selection`을 PR로 dev에 통합하고 main을 같은 통합 HEAD로 맞추는 중이다. 최종 SHA/브랜치 정리 결과는 DEV_LOG와 Issue 통합 회신에 기록한다.

## Flutter 완료와 남은 후속

본문 제외 댓글 순번은 Backend 작업 단계 번호가 아니다.

| 댓글 | 작성 측·단계 | 상태 |
|---|---|---|
| [106번째](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6228427796) | Flutter 서버ALREADY/재등록201 owned 소비 | 전체1590PASS·분석0 보고, pending 실제상태/ACK복구·새등록ID·unconfigured 정상처리 |
| [107번째](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6228564592) | Flutter 상태/숫자 표시 | 최종전체1591PASS·분석0 보고. 정수부/쉼표는 표시만 변경·원본 소수/자격/정렬 보존 |
| [108번째](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6228832537) | 사용자 새 기기 확인 수신 | 같은 회원의 서버 원정대 목록·인증 상태와 표시 정상. 전체 캐릭터/활동·역할·자동상세 복원 인수와 구분 |
| [109번째](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6228853681) | Flutter dev 통합·후속 분석 | 기능209ce85/dev0a11b71 push/원격일치 보고. 기본flag OFF의 관리 진입/회원 캐릭터 로컬 복원 공백 확인 |

**다음 담당은 Flutter**다. 현재 추가 Backend 구현/재시험/회신 요청은 없다.

1. 기본 `BACKEND_LIFECYCLE_READS_ENABLED=false`에서 `MyAccountPage(basicOnly:true)`가 먼저 반환해 숨겨진 기존 이름 편집·활동 캐릭터 관리 진입을 노출한다. 기존 기능을 새로 만들지 않는다.
2. 이름 오른쪽 작은 인증 버튼·긴 이름 두 줄을 적용하고 서버 원정대→canonical 전체 목록→역할 요약/개인 설정의 회원·환경별 로컬 복원 연결을 보완한다. 저장 요약 복원과 새 Armory 상세 갱신을 구분한다.
3. 후속 구현/검증·실기기 확인을 Issue로 인계하면 Backend는 새 요청 범위만 검토한다. flag를 임의 전환하거나 반복 실인증·전체 기본 시험을 선행조건으로 요구하지 않는다.

활동/대표는 명시 저장이다. 대표는 기존 값 유지·없을 때만 유효 후보의 최고 아이템레벨로 초기 draft를 정하고 공통1700 기준을 적용한다. 전체 활동 자동추가/대표 자동저장·메인 자동전환은 하지 않는다.

## 남은 별도 범위와 실행 원칙

- 타회원 분쟁·소유권 이전/24시간 수동 방어·자동 소멸확정/퇴역은 별도 보류다. 현재 타인 챌린지/장비 제어 확인을 소유 이전 완료로 보지 않는다.
- 앱 프로세스 종료로 원 key/body가 소실된 미확정명령의 영속복구는 미제공이다. 앱 수명 내 동일명령 복구와 구분하며 새 journal/API를 임의 추가하지 않는다.
- Issue #8은 후속 추적을 위해 열린 상태를 유지한다. 현재 Backend 구간 완료가 Flutter 후속·Issue 전체·운영 완료를 뜻하지 않는다.
- 다음 Backend 변경이 필요하면 최신 dev에서 목적별 작업 브랜치를 만들고 같은 Issue의 최신 합의를 확인한다.
- 기존 DB0010·개발자료/키를 유지한다. 사용자 지시의 베타 직전 시점에만 DB 내용 초기화를 별도 수행한다. Firebase/기기자료 삭제·이름 기반 병합·이관, 별도8001 채택·백업/복원 마이그레이션은 하지 않는다.
- Lightsail 운영 배포는 별도다. 이번 Git 통합으로 서버/DB 재시작·배포·자료 삭제를 실행하지 않는다. 상세 검증/장애/결정은 [DEV_LOG](DEV_LOG.md), 기능별 기준은 [AI_CONTEXT](AI_CONTEXT.md)를 따른다.
