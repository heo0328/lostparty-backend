# 즉시가입 후보조회 확장 구현

2026-10-26 이후 [실제개발반영](../../../engineering/operations/join-candidates-rollout.md) 완료. source690f36f/이미지061dc562·DB0032, 서비스후보1/목록12·HTTP6와worker/healthy를확인했다. 아래구현시점의미반영/게시전설명과구분한다. 한도/조율제안은여전히별도대기다.

2026-10-26 / 작업 구간 **즉시가입 후보 계약·구현·직접검증·인계** / `feat/raid-recruitment`.

[전체167 Flutter 소비수용](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6410375489)에따라 기존 GET admission-character-candidates에 query/data.intent=join을 추가했다. direct_join만허용·409 ADMISSION_MODE_CHANGED·actor=null. 기존 apply/change_character·admission-eligibility-2/페이지·제외집계·snapshot/cursor의회원/세션/room/T/intent/profile 바인딩을유지한다. 새endpoint·DBmigration·회원자료변환은없다.

공통 evaluator의소유/레벨/역할전투력·완료/점유·정원/파티구성을재사용한다. 후보는권한토큰이아니며선택뒤기존join context/POST로한도/일정/최신자격을확정한다. 일반characters fallback·apply위장·캐릭터별context반복·앱계산우회는없다.

[실행 OpenAPI](../../../../openapi/two-cycle.openapi.yaml)는178경로/199operation이다. 기본앱116/133전체는불변. 이전611개 schema는그대로이며AdmissionCandidateData의intent enum만합의대로확장했다. [closed schema](examples/candidate-contract-v2.schema.json)·[대표예시23개](examples/candidate-contract-v2.examples.json)의join actor=null조건도동기화했다. 동결beta base-openapi.gz는보존하고wire생성/검증은합의된단일enum변경만명시적으로허용한다. 원ACK는변경하지않는다.

## 직접검증

신규join3개와기존apply/change/HTTP3개로 고유6개 PASS다. 레벨미달제외/context일치·자료쓰기없음, 페이지전수/회원·T cursor격리·모드불일치, beta profile/닫힌응답/unknown query·intent거절/no-store/기존join최신context·POST, 기존apply자격·change자기배치·원ACK를확인했다. 초기 authored schema의oneOf actor조건과테스트용no-store middleware 누락을정정한뒤실패3개/직접영향HTTP만재검증했다. 기능전체pytest는반복하지않았다.

두생성OpenAPI 전체일치·기본116/133/현재178/199, 후보작성23/거절16벡터·beta66operation/118fixture/원ACK32동일성·문서링크/diff 검증은별도로기록한다. 기존Starlette/AnyIO경고는유지한다. 합성계정/격리DB근거이며실제서버·사용자기기성공이아니다.

## 별도 합의·반영 경계

한도 제품기준은전체166의현재C/N활성방이다. 과거관계10을정상으로설명한부분을정정했고현재목록같은판정의READONLY기대값은3방이다. [전체169 상태표/조율 선택조회 제안](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6410756326)·[제안원문](../weekly-cycles/active-room-and-wait-proposal.md)은아직소비확인대기이며서버코드/실행계약에추가하지않았다. 이대기로수용된join구현을멈추지않는다.

사용자승인범위는join소스commit/push→개발API반영/실행검증→네이티브일반join시트연결인계까지다. 실제개발반영전후상태·정확소스/이미지/기록SHA는운영기록과Issue13을따른다. DB0032/환경/키·원ACK를유지하고기존사용자자료/미확인명령재실행·dev/main/AWS·초기화는없다. 한도/조율/원ACK키매칭·전체기기인수는별도미완료다.
