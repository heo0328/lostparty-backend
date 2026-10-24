# 신청자 아이템레벨 출처 보완 제안

2026-10-25 / **합의 구현·격리35PASS 및 실제 개발 반영 완료/보완 구간 인수 수용**. 작업 구간명: 신청자 아이템레벨 누락 보완. 브랜치: `feat/raid-recruitment`.

[#26 전체19번째 Flutter](https://github.com/heo0328/lostparty-backend/issues/26#issuecomment-6386174761)의 코드 경로와 사용자 관찰을 확인했다. API source06ea4b2는 Application.display를 공용 groups.admission_core.display로 생성해 서버/이름/직업만 저장한다. 목록은 그대로 반환한다. 실제 개발DB 읽기 집계에서도 저장 신청7개 모두 display.item_level이 없었다. 원본회원/신청 식별자·값은 공개하지 않았으며 DB수정은 하지 않았다.

작성 합성예시에는 item_level을 넣었지만 실제 snapshot 저장기에는 없었다. 예시만으로 실제 제공을 판단한 검증 누락이다. 정상 인수1/2의 나머지와 Flutter58600023 문구변경·분석0/게시 보고는 독립 실행/기기 확인과 구분한다.

[#26 전체21번째 Flutter · 아이템레벨 제안 수용/표시 기준 확정](https://github.com/heo0328/lostparty-backend/issues/26#issuecomment-6386405233)에서 sourceb97eee2의3키와신규snapshot/기존current_saved·소유/시각/조회불변 경계를수용했다. 기준da50f972의display동적map은기존closed top-level을완화하지않고소비가능하다. 현재UI는item_level만읽으며출처표시/3키정합성은Backend실행인계후좁은후속연결이다. 새기능/실서버·실기기 성공이아니다.

확정표시: application_snapshot→‘아이템 레벨 1700’, current_saved→‘아이템 레벨 1750 · 현재 저장 정보’, unavailable→‘아이템 레벨 조회 불가’. 사용자에게확인/갱신행동·0/최소조건/전투력대체를요구하지않는다. fetched_at은원본시각으로보존하되카드에새시각행/조작을추가하지않는다.

**전체21 수용 당시 다음 Backend:** 합의대로구현·신규POST→저장display→HTTP목록·기존누락/성장후snapshot보존·소유변경·nullable/시각·기존쓰기/조회불변을직접검증하고정확source/계약·원격게시/실제반영여부를인계한다. **다음 Flutter:** 인계후출처/누락표시·경계검증연결, 개발반영후레벨/문구만소수기기확인. 기존전체시험/사용자통과1·2전체반복은요청하지않는다.

## 최신 반영 상태

[전체23 Flutter](https://github.com/heo0328/lostparty-backend/issues/26#issuecomment-6386758343)의 source13fb5848 출처표시 연결·158PASS 자체보고/추가차이 없음을 확인했다. 사용자 서버반영 승인으로 sourcef471e31/이미지6d5857b3를 [실제개발에 반영](../../../engineering/operations/application-item-level-rollout.md)했고 기존108표893행·키/설정을 보존했다. 실제소스241파일/177·116전체OpenAPI/HTTP12PASS다. [전체25 Flutter 인수 결과](https://github.com/heo0328/lostparty-backend/issues/26#issuecomment-6386859737)에서 레벨 표시의 사용자 기기 통과를 확인했다. current_saved/unavailable은 구현·자동검증 근거로 사용자가 인수 수용했고 해당 분기의 실제 기기 관찰은 미수행이다. 추가 Backend 수정/재시험 요청은 없다. 네이티브 작업순서/시험 진행은 해당 측에서 관리하고 Backend는 구체차이에 대응한다. 아래 제안·구현 당시의 미반영 기록은 해당 시점 이력이다.

## 최소 호환 제안

기존 필드인 **display의 동적 `string|null` map** 안에 아래3키의 의미를 명시한다. 새로운 top-level 필드·쓰기입력·프로필2를 추가하지 않는다. `reader_profile=application-display-1`의 목록 item에는3키를 항상 제공하도록 보완한다. 기존 display의 서버/이름/직업은 신청 snapshot 그대로다.

| key | 필수/nullable·의미 |
|---|---|
| item_level | 필수 string\|null. 유한 비음수 decimal 문자열. unavailable일 때null. 0/최소조건/타역할·분석레벨로 대체하지 않음 |
| item_level_source | 필수 nonnull string. application_snapshot / current_saved / unavailable |
| item_level_fetched_at | 필수 UTC RFC3339 string\|null. 그 값의 저장된 원본확인 시각. 알 수 없으면null이며 신청시각으로 만들어 채우지 않음 |

item_level_source=application_snapshot이면 **Application.display에 실제 저장돼 있던 값**이다. 신청시각은 기존created_at이고 level의 원본시각은 별도fetched_at이다. current_saved이면 **해당 페이지 evaluated_at에 조회한 Character.summary의 현재 저장값**이며 신청 당시 값이 아니다. unavailable이면 값/시각 모두null이다. 다른 표시값과 출처·시각이 다른 것을 허용하고 UI가 당시 레벨/현재 저장 레벨을 혼동하지 않도록 소비한다.

기존 계약의 ‘display는 신청 snapshot’은 서버/이름/직업과 실제 저장레벨에 적용한다. 기존 누락 레벨의 읽기 보완값만 명시적으로current_saved로 구분하는 의미 보완이다. 이 차이와 동적map의 새3키 소비는 전체21에서 수용됐으며 합의 범위로 구현한다. profile1 실패를 기본조회로 fallback하는 정책은 추가하지 않는다.

## 저장·기존 신청·소유 경계

1. **새 신청:** raid Application 생성에서만 캐릭터의 검증된 summary.item_level·confirmed_at을 캡처해3키를 저장한다. 기존 공용 identity.display는 변경하지 않고 그룹·Assignment/기타 기능에 확대하지 않는다. confirmed_at은 기존 생명주기 코드에서도 item_level_fetched_at의 근거로 사용하는 원본확인시각이다. provider를 새로 호출하지 않는다. 기존POST본문/key·ACK를 변경하지 않는다.
2. **실제 저장 snapshot이 있는 신청:** 유효한 저장값을 우선하고 application_snapshot으로 제공한다. 캐릭터가 나중에 성장하거나 소유자가 달라져도 저장된 과거값을 현재값으로 덮어쓰지 않는다. 저장 metadata가 없는 과거값의 원본시각은null이다.
3. **과거값이 누락/null인 기존 신청:** 기존4bulk조회로 읽은 Character/Account에서 신청user/character·신청ownership_revision과 현재owner/revision이 같고 confirmed/active인 경우만 현재 저장level·confirmed_at을 current_saved로 제공한다. DB backfill·revision/created_at·원snapshot/ACK 수정은 하지 않는다. 기본프로필/본인신청목록/단건review의 기존 누락자료는 그대로 유지한다.
4. **연결불가·소유revision 변경·미확인/퇴역·현재레벨없음:** 저장snapshot이 없으면 unavailable이다. 새소유자의 자료나 임의정상값을 섞지 않는다. 기존 display_reason은 분석자료 연결 의미로 보존하고 아이템레벨 사유로 재해석하지 않는다.
5. **불량 저장값:** NaN/Infinity/음수/bool/비숫자 같은 레벨은 unavailable로 표현하고 0·다른자료로 숨기지 않는다. 실제 DB/조회실패는 기존503오류이며 정상unavailable로 바꾸지 않는다. 원본시각을 새로 만들지 않는다.

current_saved의 변경은 페이지별읽기시점 차이로서 기존 분석값과 같은 방식으로 소비한다. 신청revision이 아니므로 레벨갱신만으로 cursor를 stale로 만들지 않는다. 새예약·자리·주간점유·승인자격판정/동의는 없다. 추가SQL·카드별GET/provider/자동갱신·회원자료수정·migration은 추가하지 않는다.

## 대표 작성 예시

[합성fragment 예시](examples/application-item-level-proposal.examples.json)는 새3키만 보여주는 작성자료이며 전체API응답/실행성공 증거가 아니다. 원래display의 이름/서버/직업과 기타item필드는 기존계약대로 유지한다.

- 새신청 snapshot 1700, 원본확인시각과 신청created_at은 별개.
- 이후 현재level이1750이어도 저장snapshot1700 유지.
- 기존신청level없음→현재저장1750/current_saved.
- 과거snapshot1700/원본시각없음→시각null.
- 누락+소유변경/연결불가/미확인·퇴역/현재레벨없음→unavailable.

## 합의 후 구현·검증·인계

Flutter는새top-level모델없이 동적display3키를수용할수있는지, current_saved를당시snapshot과구분할표시에구체차이가있는지회신한다. 기존자격정책/정상1·2 전체재수용·전체413시험반복요청은아니다.

합의후Backend는신규snapshot/기존누락 읽기보완·정밀값/시각/소유변경·기존값보존·조회불변·일괄SQL/페이지·원ACK를직접시험한다. 특히 실제신청POST→저장display→HTTP목록까지연결해작성예시와생산자코드를대조한다. 기본/쓰기DTO·공용identity·그룹/참가기존동작·실행OpenAPI 전체를확인하고commit/push·원격확인후같은Issue에인계한다. 실제개발반영은별도구간이며현재서버/DB는변경하지않았다.

공식제안: [#26 전체20번째 Backend · 아이템레벨 출처/기존누락 보완 제안](https://github.com/heo0328/lostparty-backend/issues/26#issuecomment-6386261019). source `b97eee2aa813a330d740318026617005dbac1c5e` commit·push·원격일치 확인후 게시·댓글전문/실제전체순번 재조회 완료. 제안 당시 다음Flutter 소비검토였으며 전체21 수용후 다음Backend 구현이다. API/서버미변경·Issue OPEN이다.

## 실행 구현·검증 경계

application_display.snapshot_level을모집Application 생성에만연결했다. 공용identity는3필드그대로유지한다. 신규저장3키와원본confirmed_at을캡처하고, 목록4bulk조회에서level_display가새dict를만들어실제snapshot우선/기존누락current_saved·unavailable을투영한다. 원본Application.display/revision/시각/ACK를GET에서변경하지않는다. 저장값이있으면소유변경뒤에도과거값을보존하고새소유자현재값을읽기대체하지않는다.

기본/쓰기DTO·전체component는보존하며실행OpenAPI177/기본116전체비교를수행한다. 합의한Application GET/POST의description만출처와저장동작을명시한다. 기존default/본인목록/단건review에는과거누락읽기보완을확대하지않고신규저장snapshot은그대로보여준다. 기존profile1·cursor/추가SQL·승인자격/원명령은변경하지않는다.

[실행 검증 집계](validation/application-item-level-results.json)는작성fragment9개와구분한다. 신규시험은딜러/서포터의실제HTTP POST→저장display→HTTP목록→성장후snapshot/원ACK보존,기존누락의정밀current_saved·기본/단건응답/DB불변,owner/ownership/missing/suspect/retired·레벨없음·불량값/시각null·페이지/SQL을직접확인한다. 합성principal/격리DB이며실회원/기기인수아니다. 구현 검증 당시 실제개발source06ea4b2/이미지d24d7cbd의아이템레벨누락은미반영상태였으며코드완료와실제해결을구분한다.

최종 고유35PASS는신규18(97.96초)+직접회귀17(136.27초)의중복없는최종소스2회실행이다. 기존AnyIO경고1종외실패없음이며과거28/참조12/Flutter413·작성자료를합산하지않는다. 기본표시/권한·페이지/상한·실제합성Bearer/세션취소·기존신청/승인/거절/철회/원ACK를직접회귀했다. 후보이미지6d5857b3… 소스241파일과실제시험소스·3시험파일 바이트일치, 실행177/기본116전체계약/모든기존component·쓰기shape보존을확인했다. 시험용환경을정리했고실제개발d24d7cbd…미교체/healthy를읽기확인했다. 당시 실서버의레벨누락은미반영문제로남았으며새소스게시후네이티브는출처검증/확정문구를좁게연결한다. 실제개발반영·실회원/기기인수는별도구간이다.

구현공식인계: [#26 전체22번째 Backend · 아이템레벨 저장/기존누락 읽기 구현인계](https://github.com/heo0328/lostparty-backend/issues/26#issuecomment-6386634008). source `f471e3133ad60befcad77d7123e1107ba7501bb4` commit·push·원격일치 확인후게시·전문/실제전체순번재조회완료. 다음Flutter출처표시/검증연결·Backend직접차이대응/별도개발반영,Issue OPEN이다.
