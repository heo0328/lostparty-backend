# 초기 자동 갱신 일괄 처리

기준: [Issue 41](https://github.com/heo0328/lostparty-backend/issues/41), [전체2번째 Backend 계약](https://github.com/heo0328/lostparty-backend/issues/41#issuecomment-6601566667). 초기 갱신의 반복 Backend GET/PUT을 줄이는 추가 API다. 기존 단건·bootstrap·게시 앱 계약은 유지한다. Backend 구현/검증·로컬 반영, Flutter 연결, 사용자 실기기 인수, 운영 반영은 각각 구분한다. 구현/실행 근거는 [DEV_LOG](../../../project/DEV_LOG.md#startup-batches)를 따른다.

## 조회

`GET /v2/me/characters/personal-profiles?character_id={UUID}&character_id={UUID}`

- UUID 1~50개. UUID 값 기준 중복·추가 query·본문·형식 오류는 전체 `400 INVALID_REQUEST`. 입력 순서를 보존하되 식별자로 대응한다.
- `200 {evaluated_at,items:[{character_id,status,profile,error}]}`. 성공은 status=200/profile=기존 PersonalProfileOut/error=null. 실패는 profile=null/error=아래 공통 항목 오류다.
- 기본 역할 version=1/summary=null/saved_at=null 및 preferences 기본값은 단건과 같다. 등록·현재 소유·active/suspect·현재 NameClaim을 단건과 동일하게 판정한다. 활동 선택 여부는 제한하지 않는다.
- 미존재·다른 회원·등록 삭제는 `404 CHARACTER_NOT_FOUND`, 본인 등록이나 소유 상실은 `403 OWNERSHIP_REQUIRED`, retired는 `409 CHARACTER_UNUSABLE`, claim 불일치는 `409 IDENTITY_CONFLICT`다. 다른 회원의 계정·revision·profile은 반환하지 않는다.
- REPEATABLE READ/READ ONLY 한 snapshot, no-store. 준비 조회 성공은 쓰기 권한이 아니다. 외부 호출·키 접근·DB 쓰기 없음. 개인 자료는 현재 소유 revision에 한정해 일괄 로딩한다. 권한 검사를 포함한 SELECT 수는 비어 있지 않은 정상 대상 1/9/50개에서 일정하다.
- 저장된 profile의 DTO 불일치는 전체 `503 PERSONAL_PROFILES_DATA_UNAVAILABLE`이며 초기값이나 성공 null로 숨기지 않는다.

## 저장과 크기

`POST /v2/me/role-summary-batches`

```json
{
  "items": [{
    "character_id": "00000000-0000-4000-8000-000000000001",
    "role": "dealer",
    "command_id": "00000000-0000-4000-8000-000000000002",
    "expected_version": 1,
    "expected_ownership_revision": 1,
    "expected_lifecycle_revision": 1,
    "summary": {
      "source": "flutter_analysis",
      "analysis_rules_version": "flutter-v1",
      "analyzed_at": "2026-11-03T09:00:00Z",
      "combat_power": "12345.00",
      "combat_power_observed_at": "2026-11-03T09:00:00Z",
      "item_level": "1700",
      "item_level_observed_at": "2026-11-03T09:00:00Z",
      "integrity_status": "clean",
      "issues": [],
      "catalog_version": null,
      "observed_lifecycle_revision": 1
    }
  }]
}
```

1~50개 항목이다. `command_id`는 단건 Idempotency-Key와 같은 UUID4이며 batch 자체 키는 없다. `character_id/role/command_id` 외의 필드는 기존 RoleSummaryIn 그대로다. 추가 필드와 느슨한 revision 자료형을 허용하지 않는다.

전체 수신 본문은 공백·외곽을 포함한 UTF-8 **524288바이트**까지 허용한다. chunked도 JSON 파싱 전에 제한한다. 항목은 **입력 JSON**에서 다음 네 필드만 뽑아 `ensure_ascii=false`, 구분자 `(',', ':')`, 들여쓰기 없이 직렬화한 UTF-8 **32768바이트**까지다. 문자열의 날짜/소수 표현을 먼저 정규화하지 않는다. 순서는 바이트 수에 영향을 주지 않는다.

```python
fields = ('expected_version', 'expected_ownership_revision',
          'expected_lifecycle_revision', 'summary')
command_body = {k: item[k] for k in fields}
size = len(json.dumps(command_body, ensure_ascii=False,
                      separators=(',', ':')).encode('utf-8'))
```

Flutter는 실제 전송할 JSON의 UTF-8 크기와 항목 수로 분할한다. 한도 초과는 `413 REQUEST_TOO_LARGE`. 빈 배열/51개, 중복 JSON 속성(중첩 포함), 중복 command_id 또는 (UUID,role), 필수 누락·DTO 오류는 전체 `400 INVALID_REQUEST`이며 멱등 예약을 포함한 쓰기가 없다. role은 문자열이어야 하며 미지원 문자열만 항목별 `400 INVALID_ROLE`다. POST query는 허용하지 않는다.

## 결과와 복구

정상 envelope는 전부 성공/부분 성공/전부 업무 실패 모두 HTTP 200이며 입력마다 정확히 한 결과가 있다.

```json
{
  "items": [{
    "character_id": "00000000-0000-4000-8000-000000000001",
    "role": "dealer",
    "command_id": "00000000-0000-4000-8000-000000000002",
    "status": 409,
    "result": null,
    "error": {
      "code": "REVISION_CONFLICT",
      "message": "REVISION_CONFLICT",
      "request_id": "synthetic-request",
      "retry_after_seconds": null
    }
  }]
}
```

성공은 status=200/result=기존 RoleSummaryOut/error=null. 오류의 네 필드는 필수이며 대기시간이 없으면 null이다. GET도 같은 항목 오류 형태를 쓴다. 외곽 오류는 기존 `{error:{code,message,request_id}}`와 기존 인증 헤더를 유지한다. 모든 응답은 no-store다. HTTP 200만으로 성공 처리하지 않고 세 식별자 `(character_id,role,command_id)`로 대응한다. 누락·중복 결과를 성공으로 합성하지 않는다.

| 항목 오류 | 상태 | 다음 행동 |
|---|---|---|
| CHARACTER_NOT_FOUND / OWNERSHIP_REQUIRED | 404 / 403 | 대상·회원·소유 변경 확인, 자동 재작성 금지 |
| CHARACTER_UNUSABLE / IDENTITY_CONFLICT / REVISION_CONFLICT | 409 | 최신 상태 확인, 원 pending/새 초안 보존 |
| INVALID_ROLE | 400 | 명령 생성 오류 확인 |
| IDEMPOTENCY_CONFLICT / IDEMPOTENCY_EXPIRED | 409 | 기존 단건 복구 정책, 새 키로 강제 적용 금지 |
| REQUEST_IN_PROGRESS | 409 | retry_after_seconds=2 이후 원키·원본문으로 재시도 |
| SERVICE_UNAVAILABLE | 503 | commit 여부 불명확할 수 있음. 원키·원본문으로 복구 |
| BATCH_NOT_PROCESSED | 503 | 해당 항목 미시도. 원키·원본문으로 재시도 |

항목마다 기존 단건 서비스를 호출해 독립 commit한다. 기존 game mutation 잠금 순서와 DB timeout을 유지하며 batch 전체 잠금/선예약/병렬 쓰기를 추가하지 않는다. 소유·현재 세션·active/confirmed·NameClaim·ownership/lifecycle·역할 CAS를 재확인한다. 활동 선택·nice_group은 저장 자격 조건이 아니다. 반대 역할/preferences는 불변이며 전투력 성공 이력과 성공 응답 journal을 같은 트랜잭션에서 확정한다. 쓰기 SQL은 기존 검증 때문에 항목별 발생하며 SQL 1회 저장으로 표현하지 않는다.

업무 실패는 다음 항목을 처리한다. DB 장애/중간 인증 상실 시 확인된 결과를 보존하고 중단하며 뒤 항목은 BATCH_NOT_PROCESSED다. 최초 전체 인증 실패는 어떤 예약/쓰기 전 기존 외곽 오류다. 예상하지 못한 프로그램 오류나 연결 단절은 완전한 결과 envelope를 보장할 수 없으므로 기존 원명령 재전송으로 복구한다.

처리 시작부터 **20초 예산을 항목 사이에서 확인**한다. 실행 중 트랜잭션을 강제 취소하지 않아 전체 응답 20초 보장은 아니다. client 응답 대기 **60초** 권고. 예산 소진 뒤 미시도 항목은 BATCH_NOT_PROCESSED다.

단건과 동일한 `role-summary` 영역에 회원/command_id를 사용하고 digest는 기존 단건과 동일한 `character_id/role/정규화된 RoleSummaryIn`이다. batch metadata는 본문 digest에 넣지 않는다. 단건↔batch 또는 부분집합 재송신 모두 원키·원본문으로 재생 가능하다. lease 30초, 성공 24시간 재생, 이후 만료 기록을 유지하다 기존 cleanup이 48시간 이후 삭제한다. 영구 중복 방지 보장은 아니며 Flutter의 기존 보수적인 pending 수명 규칙을 유지한다.

성공 ACK는 historical이며 현재 role version을 나타내지 않을 수 있다. 최종 현재 상태는 기존 `GET /v2/me/account-bootstrap` 한 번으로 확인한다. 저장 실패를 LostArk 재조회로 대체하거나 충돌 버전을 자동 보정하지 않는다. 정상 9개는 준비 GET1+LostArk9+batch POST1+최종 bootstrap1=12회이며 로그인·목록 갱신은 별도다.

## 인계 경계

구현 `b1f11bb5011056ce5dd655efe7c8efe2765960e3` 원격 게시·로컬 반영을 [전체3번째 Backend 인계](https://github.com/heo0328/lostparty-backend/issues/41#issuecomment-6602009469)에서 확인한다. 문서 후행 마감 SHA와 실행 업무 소스 SHA를 구분한다.

기본/two-cycle OpenAPI에 동일한 추가 계약을 제공한다. migration·새 provider 호출·새 DB표는 없다. Backend 고정 SHA/실제 로컬 반영을 확인한 뒤 Flutter가 DTO·durable 원명령·유한 큐·일괄 전송/복구·최종 bootstrap을 연결한다. Flutter의 기존 commit/push/merge 보류는 별도 사용자 결정 사항이다. 운영 배포·태그·merge·APK 게시·자료 초기화·Issue 종료는 포함하지 않는다.
