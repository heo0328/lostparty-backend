# Issue #4 실제 siblings 응답 점검 안내

이 도구는 등록 관리 실연동 전에 provider 응답과 기존 parser가 맞는지 확인한다. [#4 계획](ISSUE_4_REGISTRATION_INTEGRATION_PLAN.md)의 실응답 관찰을 지원하며 실제 등록·소유권·Flutter 화면 인수를 대신하지 않는다.

## 키 발급·설정

필요한 값은 Google 인증 키가 아닌 **로스트아크 공식 Open API JWT**다. [공식 시작 안내](https://developer-lostark.game.onstove.com/getting-started)의 절차에 따라 사용자가 STOVE 계정으로 로그인하고 client를 생성해 발급 값을 확인한다. client 정보와 필수 약관은 사용자가 직접 확인·입력한다. 발급·동의 작업을 agent가 대신 수행하지 않는다.

Backend 로컬 `.env`에 변수 `LOSTARK_API_TOKEN`을 설정한다. 값은 JWT 자체이며 `Bearer ` 접두사를 넣지 않는다. transport가 Authorization 헤더의 접두사를 붙인다. 키 값/.env 본문은 채팅·Issue·앱에 전달하지 않는다. 기존 파일 권한을 유지한다.

앱의 실제 Backend 호출에도 설정을 반영하려면, 키 설정 후 API 환경만 재생성한다.

```bash
docker compose up -d --no-deps --force-recreate --wait --wait-timeout 180 api
```

key 유효성과 provider 성공은 health200으로 증명되지 않는다. 키가 준비되지 않은 동안 Flutter UI/Repository·503 처리는 기존 계약으로 구현할 수 있다.

## 한 번의 로컬 응답 점검

새 도구가 들어 있는 API 이미지를 빌드한 뒤, 사용자 로컬 터미널에서 실행한다.

```bash
docker compose build api
docker compose run --rm --no-deps api python -m app.game_accounts.diagnostics
```

캐릭터명은 숨김 입력 프롬프트에 직접 입력한다. command 인자/환경변수/Issue에 입력하지 않는다. 입력을 표시할 수 있는 비TTY 환경에서는 도구가 실행을 거절한다. agent가 임의 캐릭터를 선택하거나 개발DB fixture를 넣어 실행하지 않는다.

도구는 서버 환경의 key로 siblings를 **한 번만 호출**한다. 장비 Armory·auth/session·DB service를 호출하지 않으며 DB 등록/갱신/삭제·캐시/자료 저장·자동 재시도는 없다. 이것은 수동 운영 진단 호출이므로 반복 polling에 사용하지 않는다. 앱 요청의 기존 rate 제한은 별도로 유지된다.

결과는 다음 항목만 출력한다.

- success/failure와 공개 가능한 고정 reason
- 응답 root 타입,200개 이하의 캐릭터 수
- ServerName/CharacterName/CharacterClassName/CharacterLevel/ItemAvgLevel의 타입별 개수·missing/null 여부
- parser 통과 여부와 null item_level 개수
- ownership_proof=false, roster_completeness_proven=false

캐릭터/서버/클래스의 실제값, 숫자 원문, key, raw JSON, 요청URL, 예외문구/traceback은 출력하지 않는다. 임의 필드명도 복사하지 않는다. shape 성공은 장비 인증·영속ID·계정 전체성이나 등록 UI 성공 증거가 아니다.

| 종료 코드 | 의미·다음 작업 |
|---|---|
| 0 | 실제 호출을 실행했다면 현재 parser와 해당 관찰 응답이 일치. 이어서 사용자의 앱 등록관리 인수 |
| 1 | provider 호출 실패 또는 parser 불일치. 출력 reason/타입 근거로 영향부분만 조사. 실패를 빈 roster로 처리하지 않음 |
| 2 | key/interactive terminal 미준비 또는 사용자 취소. 외부 검증 완료로 표시하지 않음 |

Issue에는 식별정보가 없는 결과만 인계한다. 실패 이유가 schema 차이면 typed adapter/오류 처리를 대상 검증·보완하고 계약 변경 여부를 함께 기록한다. 새코드 게시가 필요하면 승인 범위를 따른다.

## 현재 실행 결과

도구/기존 parser 대상13개 테스트 통과, 기존 테스트 도구 경고1개. 데이터 형태·nullable·불량/중복/상한·개인정보 비노출·비TTY/키 미준비·private 예외 안전 처리를 모의 transport로 검증했다. 로컬 key 미설정 상태의 CLI는 종료2/UPSTREAM_NOT_CONFIGURED로 외부 호출 없이 종료했다. 최신 이미지 schema는 기존 원본 계약254cb5d와 동일하다.

사용자 키 설정 후 local/runtime 존재 true·Bearer 접두사 false·health200을 확인했다. 이미 실행 중인 API에 반영되어 재생성하지 않았다. 키 값은 출력하지 않았다. 이후 사용자가 로컬 숨김 입력으로 실제 siblings를 조회했고 `status=passed` 결과를 공유했다. 실제 호출 성공으로 해당 요청의 키/provider 접근과 기존 parser 호환성을 확인했다. **등록 성공·수정·갱신·제거의 업무 API/Flutter 인수는 미실행**이다. 이전 Backend114개·후속10개/이번13개는 별도 실행 결과이며 전체 누적 테스트가 모두 재실행된 것으로 표시하지 않는다. 현재 추가도구/문서는 미커밋·미push이며 원격 구현SHA가 아직 없다.

### 2026-10-14 사용자 실 siblings 관찰

사용자가 제공한 수동 CLI 실행 결과를 확인했다(agent 재호출 아님). root=array, character_count=4, non_object_items=0. ServerName/CharacterName/CharacterClassName/ItemAvgLevel은 각각 string 4개, CharacterLevel은 integer 4개이며 null_item_levels=0, status=passed다. 기존 parser의 수치·중복·입력존재·상한 검증을 통과했으므로 해당 관찰에서 수정할 차이는 없다.

ownership_proof=false, roster_completeness_proven=false는 진단 범위에 맞는 정상 결과다. 실제 nullable 사례/장비소유권/전체성까지 증명한 것으로 확대하지 않는다. 이제 Flutter 기존 계약의 검색→등록→두조회→표시명/main 변경→갱신→제거→재조회와 로컬 자료 보존을 시험하고 재현된 서버 차이만 보완한다.

## 2026-10-14 게시 상태

사용자 승인으로 `feat/4-registration-integration`에 구현/새 label 계약/진단도구/검증/문서를 커밋·push했다. 실제 구현·계약 SHA: `d3cb697bb6ebb988b63bd99c588bc1b64a93650d`. 앞선 미커밋/새SHA미발급 설명은 게시 전 이력이며 현재 소비 기준은 이 SHA다. dev/main 추가병합·실제 Flutter 인수는 후속이다. 기존 대상16개·진단13개/실 siblings 4개 근거를 유지하며 이번 게시에서 테스트를 반복하지 않았다.
