# 베타 모집 Backend 구현·격리검증

2026-10-25 / `feat/raid-recruitment` / 작업 구간 **베타 모집 구현·격리검증**.

기준은 [#13 전체151 Flutter 최종수용](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6394870853)의 `267afe5 / beta-recruitment-wire-2`다. [전체152 Flutter A 기반 구현](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6395265140)은 별도 앱 소스12cd2e9a의 보고이며, 이 문서의 Backend 검증과 합산하지 않는다.

## 구현과 보존

- `contract_profile=beta-recruitment-1`을 기존64 operation에서 명시적으로 선택한다. 새 config/조회 DTO는 기존 typed DTO에서 별도로 구성하며 기존612 schema 정의를 바꾸지 않았다. 생성·조율 입력을 새 closed 모델로 검증하고 기본/reader 응답의 정확한 층에서 metadata를 제공한다. profile 없이 새 beta 입력을 보내면400이다.
- 0032는 기존 자료를 자동변환하지 않는 추가 migration이다. 실제T의 기본약속/단일session·조율설정·전역증가번호/5자리문자열, 복사근거·신청메모·약속예약 표시, 본인계정프리셋을 추가 테이블로 저장한다. 기존 ORM/응답·기존 데이터·원ACK를 유지한다. DB sequence 결번을 허용하고 성공재송으로 번호를 다시 발급하지 않는다.
- 서명 컨텍스트는 개인표 revision뿐 아니라 본인 활성예약 ID/시각/revision도 결합해 오래된 예약근거의 새 명령을 막는다. 생성/실제가입/승인/N참가에서 개인표복사·참가·기존 예약표의 promise를 같은 트랜잭션에 저장한다. missing/정상빈표만 unset, 불량 저장/권한실패는 정상화하지 않는다. 미저장 개인표의 논리 버전은 기존 개인표 GET의 기본값1이며 개인표 row를 생성하지 않는다. pending은 복사/예약하지 않는다. 캐릭터 변경은 기존 복사표를 유지한다.
- 조기탐색은 현재 실제참가자/추가인원·주차/점검·부분표/타예약을 검사하고 정확한 자기 T/generation/session promise만 제외한다. OFF 기본값·ON 즉시효과 동의·단일명령 평가, 무후보 기본유지, 이미확정한시각 불변을 적용한다. 명시 개인표 갱신은 기존 CAS 경로다.
- 미확정 기본출발30분 전에는 서버가 원기본시간으로 확정한다. 지연돼 기본출발도 지났으면 needs_review로 남기고 기존 명시제안/동의분모로 미래시각을 복구한다. GET은 저장/확정하지 않는다. worker와 쓰기 진입의 독립 기한 트랜잭션이 같은 helper를 사용하며 실패한 가입이 기한 효과까지 롤백하지 않는다. 마지막 commit 시각의 마감 검사와 최초 임계합류 예외를 유지한다.
- 약속예약도 기존 TimeReservation을 사용하므로 이탈/추방/완료/해산의 기존 정리 경로와 원자성을 공유한다. 새 sidecar는 약속근거만 보존한다. 수동 일정제안/응답은 기존 표밖/타예약 중복 명시동의·quorum·참가확인 경로를 유지한다. 신청 후 시각이 바뀌면 공대장 승인을 신청자의 새시각 동의로 간주하지 않는다.
- identity는 해당T의 현재 participating CM/활성membership/접근권한에만 제공하고, record content=null은 그대로 유지한다. memo는 신청자/현재권한 리더의 기존 조회에만 snapshot으로 제공한다. public/검색/일반참가자 목록/ACK에 password/memo를 추가하지 않는다.
- NFC·제한문자·U+0020 trim·20코드포인트/byte 제한을 실제 신청·preset 저장에서 검사한다. 금칙어는 앱 로컬 책임이며 서버 API/사전 동기화를 추가하지 않는다. 프리셋 GET/PUT은 본인 계정/최대5/전체목록·CAS·원ACK·no-op을 유지한다.
- 새 요청은 profile·operation/경로대상과 정규화 전 JSON 원입력/키 존재·null·배열을 멱등 동일성에 포함한다. 구 namespace/원payload는 바꾸지 않는다. 원ACK 재생 후 구버전 위험한 새쓰기를 차단하며 안전관리/IF-001 보존 목록은 [계약](beta-contract-wire.md)을 따른다. ACK 후 조회실패로 명령을 다시 실행하지 않는다.
- UTC departure_windows·상태를 SQL에서 필터한 뒤 정렬/페이지를 적용한다. 반열린 구간·자정·기존 legacy 확정시각을 보존하며 profile/정규화조건/미처리 기한 집합도 cursor에 바인딩한다.

## 계약과 정적 원본

소스 실행 계약은 [two-cycle OpenAPI](../../../../openapi/two-cycle.openapi.yaml)의178경로/199 operation이며 presets GET/PUT 두 operation만 새 경로에 추가했다. 기본앱 OpenAPI116/133은 유지한다. 이 구현 구간 당시 실제 서버는87c2a0e/177/0031이었다. 이후 별도 승인된 [베타 개발 반영](../../../engineering/operations/beta-recruitment-rollout.md)으로 동일소스d95e382/이미지f458e6d5·178/199·DB0032를 적용하고 기존 자료 보존/실제HTTP16을 확인했다.

합의된 제안 bundle과 예시를 현재 실행 OpenAPI로 재생성하지 않는다. 계약 도구는 [합의 당시 실행 원본의 압축본](proposals/beta-recruitment-v2.base-openapi.json.gz)을 읽고 원 SHA256 `cc235345ff48726506389a4ba9dcd09ac7452206568a2a3bf2e905ff8412b1fb`와 대조한다. 이는267afe5의 실행 계약 원본을 그대로 압축한 것이다. 현재 실행계약 일치 검증은 `verify_isolated.py contracts`로 별도 수행한다.

## 검증과 다음 인계

베타21 전체 통합 PASS 후 본인 예약근거 서명 보강에 대한 신규1/직접영향6을 재검증해 **베타22 고유사례 PASS**를 확인했다. additive migration/기존표 보존·0032 startup readiness, 실제생성/promise/개인표복사·기본/조기/지연복구, C/N identity/권한, 메모 pending/승인, preset CAS/원본문 재생/동시수정, 구버전 차단, 검색 반열린 구간/페이지, 실패롤백/독립기한, 실제 HTTP/합의 closed reader matrix 및 누락/null 멱등 분리, 명시 N개방/N참가, 안전한 기존탈퇴/기록권한, 롤백번호 비재사용과 최종시각이 출발을 넘긴 기한 처리 롤백/재확인 전환을 확인했다.

관련 기존 회귀는 HTTP/신청20 PASS와 일정/멤버관리/원자이탈85 PASS다. 기존25건 묶음의 beta5, 이후99건 묶음의 beta14는 최종beta22과 중첩하므로 합산하지 않는다. 99건 묶음에서 발견된 실제 availability_copy.source_personal_version의 null 불일치는 기존 개인표 기본 논리버전1로 수정했고, 최종21의 전체 reader 대조가 통과했다. 초기 원ACK 렌더러 연결 범위와 N컨텍스트 서명 DB 전달 누락도 각각 수정 후 해당 전체/전용 경로를 재실행했다. 모두 합성 사용자·임시 PostgreSQL이며 실제 개발 서버/Flutter/실회원·기기 성공이 아니다.

기본116/133·two-cycle178/199 실행 OpenAPI 전체 객체 일치, 기존612 schema 보존, dependency lock·문서/링크·정적12검사·diff check, 동결 제안48/문자25/합성118 검증도 PASS다. 기존 Starlette/AnyIO 폐기예정 경고는 남아 있고 패키지 버전은 변경하지 않았다.

테스트는 `python3 scripts/verify_isolated.py all tests/test_beta_recruitment.py`로 실행한다. 기검증한 제안48/문자25·합성118은 API 기능시험 통과 수에 합산하지 않는다. 실제 개발 서버 변경/DB자료변경·dev/main통합/AWS배포는 이 구현 인계의 완료로 표시하지 않는다. 정확 소스 SHA·원격 게시 확인·실행계약 고정 링크와 다음 담당은 [전체153 Backend · 베타 구현/격리검증](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6395894539)에서 추적한다. 소스 구현/격리검증과 실제 서버 반영을 구분한다.
