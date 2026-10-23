# Issue #8 — 실제 장비 관찰 준비

2026-10-16. 사용자 결정은 **도구를 준비하고 실제 게임 검증은 나중에 진행**이다. 이번 구간은 관찰 CLI/자동 검증까지이며 실제 사용자 JWT·캐릭터 입력, provider 호출, 소유 확정은 수행하지 않았다.

## 준비한 도구

`app/game_accounts/ownership_diagnostics.py`는 DB 없이 실행하는 수동 CLI다. 로컬 터미널에서 JWT와 캐릭터명을 숨김 입력하고 장비 6부위 기준 → 무작위 1~3부위 직접 해제 → 모두 재장착을 각각 Enter로 관찰한다. 정상 완료 시 API 호출은 총 3회이며 자동 재시도/폴링은 없다. 기준 관찰 후 유효시간은 10분이다. 장비 반영을 기다린 후 다음 Enter를 누르며, 취소/실패 시 장비는 사용자가 직접 원복한다.

```bash
docker run --rm -it lostparty-backend-api:latest python -m app.game_accounts.ownership_diagnostics
```

현재 로컬 이미지에 포함했다. 다른 환경에서는 저장소에서 `docker build -t lostparty-backend-api:latest .`로 먼저 빌드한다. 키·캐릭터명은 채팅/Issue/명령 인수에 넣지 않는다. 도구는 원본 응답·장비명·캐릭터명·서버명·키를 출력/파일 저장하지 않는다. 출력은 단계·요청 부위·비교 결과·호출 횟수다.

`ready_for_review`는 요청 부위 해제/나머지 동일/원복의 관찰이 일치했다는 뜻이다. 모든 단계의 `ownership_proof`, `canonical_binding`, `retirement_proof`는 false다. 결과는 서버 인증/claim/퇴역 근거를 자동 생성하지 않는다. 실제 관찰 결과를 검토한 뒤 서버에서 검증 가능한 소유 증거와 canonical 연결 규칙을 별도 구현·합의해야 한다. 이름 일치나 장비 관찰만으로 원정대 전체의 영구 식별을 확정하지 않는다.

## 증거와 검증

공식 characters/armories Swagger를 재확인했다. 기존 [증거 검토](ISSUE_8_PROVIDER_EVIDENCE_REVIEW.md)의 보류를 해제할 새 안정 식별자·장비 미장착/전체성 보장은 확인하지 못했다.

- characters 원문 SHA256 `ae8f0c0f6155098f54d025f678518b913de286438602974a881f957790c294eb`
- armories 원문 SHA256 `eb8f293aa2f70362e3dee9125755162c07aa52f671561b4ce8a6c78bdafe6893`
- [공식 문서](https://developer-lostark.game.onstove.com/getting-started)·[FAQ](https://developer-lostark.game.onstove.com/faq)·[characters](https://developer-lostark.game.onstove.com/swagger-doc/endpoints/characters)·[armories](https://developer-lostark.game.onstove.com/swagger-doc/endpoints/armories)

격리 PostgreSQL에서 도구/기존 진단/장비 parser/모델-DB 일치 검증 **65 PASS**. 최초 실행은 63 PASS/1 FAIL: 기존 모델 대조 시험이 API client 없이 실행되면 일부 모델을 등록하지 않는 순서 의존이 있었다. 시험에 전체 모델 import를 명시한 후 동일 구간64PASS, 숨김 입력 실패 검증 추가 후 최종65PASS였다. Starlette의 기존 deprecation warning 1건이다. 실제 provider·게임 해제/원복·소유 인증 성공·전체 저장/자동갱신/복원은 미확인이다.

다음 Backend 작업은 사용자 준비 시 이 도구로 실제 반영 형태를 확인하고 소유/연결 근거의 충족 여부를 검토하는 것이다. Flutter는 [D 완료 회신](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6207225790)을 보냈으며 이 관찰을 대신할 필요가 없다.

현재 개발 순서는 [최신 정정](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6207542428)을 따른다. 실제 게임 관찰은 사용자 결정대로 나중이며 현재 환경에서 진행 가능한 미완료 기능 개발을 막지 않는다. 도구 준비를 별도8001 환경 채택이나 기본 기능 재인수 조건으로 사용하지 않는다. Flutter 최종 결과는 별도저장 연결 복구 후1524PASS다.
