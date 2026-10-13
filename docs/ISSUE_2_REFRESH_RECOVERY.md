# Issue #2: refresh 제한된 재시도 복구 설계

상태: **TTL·복구 시간·횟수 사용자 확정, 나머지 세부 설계 제안·미구현**. 사용자는 로그인 TTL과 제한된 재시도 복구 방향, 최초 성공 commit 후 60초·추가 재시도 최대 2회를 확정했습니다. 보관 방식·오류 DTO 등은 Flutter 검토가 필요한 제안이며 실제 OpenAPI 계약은 변경하지 않습니다.

## 확정한 초기 기간

| 항목 | 기간 |
|---|---|
| Access | 10분, session 유효 기간을 넘지 않음 |
| 로그인 유지 선택 | 절대 30일 / 마지막 성공 로그인·refresh 이후 idle 7일 |
| 로그인 유지 미선택 | 절대 12시간 / idle 2시간, 앱 재실행 시 비로그인 |

절대 기간은 로그인부터 고정하고 idle은 성공한 새 refresh에서만 갱신합니다. 동일 결과의 재전송으로 만료를 연장하지 않습니다.

## 제안하는 요청과 처리

`POST /v1/auth/refresh`는 `{refresh_token, refresh_request_id}`를 받습니다. request ID는 앱이 갱신 작업마다 생성하는 32바이트 난수의 base64url 문자열이며 서버가 발급한 session ID와 다릅니다. credential과 함께 로그·Issue에 기록하지 않습니다.

1. Flutter는 single-flight로 작업을 시작하고 요청을 보내기 전에 old refresh와 request ID를 함께 보관합니다. 첫 요청과 재시도는 두 값을 그대로 사용합니다. 다른 request ID로 old refresh를 재제출하지 않습니다.
2. 서버는 refresh hash로 session을 식별하고 계정·session 상태와 만료를 검사합니다. session 잠금 아래 old refresh를 1회 소비하고 후속 refresh·access를 발급합니다.
3. 소비 기록에 request ID hash, 후속 generation, 최초 commit 기준 복구 만료 시각을 저장합니다. 동일 transaction에서 응답 전체를 암호화해 보관하고 commit합니다. 발급과 복구 기록을 서로 다른 commit으로 나누지 않습니다.
4. 같은 old refresh hash + 같은 request ID가 들어오면 최초 commit 후 **60초 미만, 추가 재전송 최대 2회**에 한해 최초 응답을 그대로 반환합니다. 최초 요청을 포함한 클라이언트 전송은 최대 3회입니다. `recovery_expires_at = 최초 성공 commit 시각 + 60초`로 정의하고 DB 처리 시각이 이 시각과 같거나 이후면 종료합니다. 동시 요청도 잠금 아래 재전송 횟수에 포함합니다.
5. 재전송 전 계정·session 유효성과 후속 refresh가 아직 소비되지 않았는지 검사합니다. 만료·로그아웃·정지 뒤에는 암호화 응답이 남아 있어도 반환하지 않습니다. 재전송은 새 token 발급·idle 연장·복구 기간 연장을 하지 않습니다.

서버가 첫 요청을 commit하지 않았으면 같은 요청으로 정상 발급할 수 있습니다. commit했으면 동일 결과만 반환합니다. 요청량 제한은 별도로 적용하고 복구 횟수 제한을 요청량 제한의 대체로 쓰지 않습니다.

## Flutter 통신 처리

- 네트워크 timeout·응답 유실·503에서만 같은 요청을 제한적으로 재시도합니다. 제안 backoff는 1초, 3초이며 서버 60초 제한을 넘지 않습니다. 429는 Retry-After와 전체 제한을 함께 적용합니다.
- 성공 시 새 access/refresh를 함께 교체하고 pending 요청을 제거합니다. 이전 refresh를 다시 사용하지 않습니다.
- remember=true는 pending old refresh·request ID를 secure storage에 함께 보관하여 앱 재시작 후 같은 작업을 복구할 수 있게 합니다. token 교체와 pending 제거가 중간 실패에 안전하도록 한 보관 객체의 교체 등 원자성 방안을 Flutter가 검증합니다.
- remember=false는 pending도 메모리에만 둡니다. 앱 재시작 시 credential을 복원하거나 Google silent login을 하지 않습니다.
- retry가 끝날 때는 일반 인터넷 장애와 서버의 복구 불가 응답을 구분합니다. 인터넷 장애만으로 계정 정지나 로그인 유지 설정 해제를 선언하지 않습니다. 복구 불가가 확정되면 재로그인을 안내합니다.

## 오류와 replay 구분

| 상태 | 결과 후보 |
|---|---|
| 같은 old hash·request ID, 유효 복구 범위 | 최초 200 응답 재전송 |
| 같은 요청이지만 60초/횟수 종료 | 409 REFRESH_RECOVERY_EXPIRED 또는 REFRESH_RECOVERY_LIMITED. 결과 재발급 없음, 해당 이유만으로 family 폐기하지 않음. 앱은 재로그인 안내 |
| 같은 요청이지만 후속 refresh가 이미 소비됨 | 409 REFRESH_RESULT_SUPERSEDED. 이전 credential 재전송 없음; 앱이 이미 보유한 더 최신 상태를 덮어쓰지 않음 |
| 소비된 old hash를 다른 request ID로 제출 | 401 REFRESH_REUSED, 해당 family 폐기 후보. 다른 기기는 유지 |
| 모르는 hash | 401 REFRESH_INVALID |
| 식별 가능한 만료 / 폐기 | 401 REFRESH_EXPIRED / SESSION_REVOKED |
| 정지 회원 | 403 ACCOUNT_DISABLED |
| 암호화 응답 키·복호화 장애 | 503 SERVICE_UNAVAILABLE, raw credential 재생성·새 token 발급으로 우회하지 않음 |

request ID는 credential 보유자를 거래에 묶는 재시도 식별자이며 하드웨어 기기 증명이 아닙니다. old token과 request ID가 모두 유출되면 복구 범위 내 정상 재시도와 공격을 구별할 수 없습니다. 보관 시간을 제한하고 TLS·secure storage·로그 제외를 적용합니다. 더 강한 sender-constrained 인증이 필요하면 별도 설계합니다.

## 저장과 정리

refresh 자체는 계속 hash만 저장합니다. 복구 응답은 access/refresh가 포함된 **암호화된 단기 데이터**이며 raw credential 저장 금지와 구분해 검토합니다. 별도 서버 암호화 키로 인증된 암호화를 적용하고 DB에 키·평문 token을 저장하지 않습니다. 키 ID와 랜덤 nonce, session/generation/request hash를 연결한 인증 데이터를 사용합니다.

PostgreSQL에 복구 자료를 보관하고 Redis는 도입하지 않는 후보입니다. 복구 암호문은 요청 시 만료를 검사하고 주기적으로 삭제합니다. 물리 삭제가 지연돼도 60초 이후 복호화·반환하지 않습니다. request hash·소비 이력은 replay 구분에 필요한 기간까지 별도로 보관합니다. logout은 기존 absolute 만료까지 반복 안전성 제안을 유지하며 관련 암호문은 즉시 무효화합니다.

암호화 키는 런타임 비밀로 주입하고 로그·Git에 저장하지 않습니다. 키 교체 시 유효한 단기 응답의 구키를 복구 기간 동안 유지하는 절차가 필요합니다. DB 백업에는 단기 암호문이 포함될 수 있으므로 백업 보관과 키 관리도 함께 검토합니다. 현재 키나 청소 작업은 구성하지 않았습니다.

## 검증과 다음 합의

PostgreSQL에서 동시 동일 요청·다른 요청 ID replay, commit 전 실패·commit 후 응답 유실, 60초 경계·재전송 횟수, 후속 token 사용 뒤 지연 응답, logout·정지·만료 후 재전송 거절, 암호화 키 실패·청소 지연·rollback을 검증합니다. Flutter는 재시도 값 유지와 single-flight, secure storage 교체, 재시작 복구, 오래된 응답으로 최신 token을 덮어쓰지 않는 동작을 검증합니다.

60초·추가 2회는 사용자 확정값으로 Flutter에 인계합니다. Flutter에는 pending 보관 지원과 오류 처리 등 구현 가능 여부를 확인 요청합니다. 서버 암호화 보관·키 관리와 테스트 설계를 검토한 뒤 API 구현과 OpenAPI를 반영합니다. 이 문서 작성은 구현·실인증·배포 완료가 아닙니다.

회전과 replay 탐지는 [RFC 9700 §4.14](https://www.rfc-editor.org/rfc/rfc9700.html#section-4.14)를 참고합니다. 60초·추가 2회는 RFC가 정한 값이 아니라 사용자가 확정한 프로젝트 정책입니다.
