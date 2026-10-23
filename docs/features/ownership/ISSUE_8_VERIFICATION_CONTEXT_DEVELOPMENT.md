# Issue #8 — 소유 인증 대상·관찰 목록 고정 검사

2026-10-16. 63번째 Backend 검토 이후 사용자 진행 지시에 따른 서버 보완이다. [64번째 Backend 착수 댓글](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6210224869)에 범위를 공유했다. 댓글순번은개발단계번호가아니다.

## 실제 변경

인증 시작 시 조회한 서버/캐릭터명 쌍과 관찰 목록 주소의 정렬 digest를 기존 Verification.identity_snapshot JSON에 고정한다. 확인 시 지정 장비의 해제/비요청장비유지가 일치하더라도 이 대상/주소 집합이 달라졌으면 기존 `ROSTER_EVIDENCE_PENDING` 결과로 보류한다. 새 이름추가·누락·조회이름의서버변경·중복/불명확주소도소유생성/이전으로이어지지않는다. 순서·아이템/캐릭터레벨변화는동일주소의표시변경이므로목록동일성비교에서제외한다.

대상고정정보가없는옛challenge는 `PROVIDER_EVIDENCE_PENDING`으로유지한다. 기존취소/만료/새시작경로를사용하며새복구화면·DTO필드를추가하지않는다. 내부adapter의 proof_validated 표식은엄격한boolean True만인정하며1/문자열/객체등truthy값을검증완료로취급하지않는다.

기존회원/세션·키version·등록/소유/roster snapshot·canonical충돌검사·장비비교·감사/소유연결transaction은유지한다. 대상고정은이기존검사에추가되는필요조건이며권한을생성하는증거발급기가아니다. HTTP입력에서proof/binding을받지않는다. 원본대상/장비/키를로그/Issue/출력에추가하지않는다.

endpoint/DTO/enum/DB구조불변, 기존결과code재사용·OpenAPI challenge_context 정책설명만추가했다. 비교에서보류된명령은현재challenge의pending결과를기록할수있으나소유/account/canonical/감사권한자료를생성·이전하지않는다. 같은key의과거관찰결과는멱등계약대로역사응답이며새관찰은새명시명령이다.

## 완료와 남은 구현의 구분

| 항목 | 상태 |
|---|---|
| 시작/확인 관찰의 대상/목록 변경 차단 | 이번 서버 구현/격리 검증 대상 |
| 장비가 실제로 어떻게 해제/원복 응답에 반영되는지 | 사용자 실제 관찰은 나중, 미확인 |
| live 장비 증거의 수용/발급 및 proof_validated 생성 | 미완료. live adapter는 여전히 false |
| 기존 원정대/캐릭터 세대의 연결 근거 | 미완료. live binding=None, 이름 동일/목록 동일은 연결 증거 아님 |
| 소멸 확정·퇴역/claim 해제 | 계속 보류. 이번 검사/장비 관찰로 전체성·영구동일성을 보장하지 않음 |

즉이번완료를실제소유인증가능상태로보고하지않는다. 다음실제활성단계에는관찰결과에대한수용근거와서버증거발급연결이필요하며, 기존원정대재연결은별도연속성근거가필요하다. 사용자게임관찰나중지시는유지한다. Flutter의기존관리/초기대표/인증전환1560PASS보고·현재개발환경/자료도유지한다.

## 공식 근거 재확인

공개 [characters schema](https://developer-lostark.game.onstove.com/swagger-doc/endpoints/characters) SHA256 `ae8f0c0f6155098f54d025f678518b913de286438602974a881f957790c294eb`, [armories schema](https://developer-lostark.game.onstove.com/swagger-doc/endpoints/armories) SHA256 `eb8f293aa2f70362e3dee9125755162c07aa52f671561b4ce8a6c78bdafe6893`로기존조사와동일했다. [공식 FAQ](https://developer-lostark.game.onstove.com/faq)의지연안내도재확인했다. 추가안정식별자/장비누락의전체성보장을이자료에서확보한것은아니다. 실사용자JWT/캐릭터·provider장비조회는수행하지않았다.

실제검증/초기실패·실행반영·원격게시정보는DEV_LOG와결과댓글을따른다. 내용이같다는digest는관찰비교용이지영구원정대ID/소유증거가아니다.

최종격리검증 **250PASS·기존경고1·122.88초**, 초기실패없음. 신규16경계와계정/생명주기/역할/개인설정/회원키·관찰도구·모델/계약회귀를확인했다. 기존8000에반영하고실행소스/전체OpenAPI/health·DB0009유지를확인한다. 기본관리/소유인증실제성공·실기기테스트는수행하지않았다.
