# 신청자 아이템레벨 출처 보완 제안

2026-10-25 / **협의 제안·미합의·미구현**. 작업 구간명: 신청자 아이템레벨 누락 보완. 브랜치: `feat/raid-recruitment`.

[#26 전체19번째 Flutter](https://github.com/heo0328/lostparty-backend/issues/26#issuecomment-6386174761)의 코드 경로와 사용자 관찰을 확인했다. API source06ea4b2는 Application.display를 공용 groups.admission_core.display로 생성해 서버/이름/직업만 저장한다. 목록은 그대로 반환한다. 실제 개발DB 읽기 집계에서도 저장 신청7개 모두 display.item_level이 없었다. 원본회원/신청 식별자·값은 공개하지 않았으며 DB수정은 하지 않았다.

작성 합성예시에는 item_level을 넣었지만 실제 snapshot 저장기에는 없었다. 예시만으로 실제 제공을 판단한 검증 누락이다. 정상 인수1/2의 나머지와 Flutter58600023 문구변경·분석0/게시 보고는 독립 실행/기기 확인과 구분한다.

## 최소 호환 제안

기존 필드인 **display의 동적 `string|null` map** 안에 아래3키의 의미를 명시한다. 새로운 top-level 필드·쓰기입력·프로필2를 추가하지 않는다. `reader_profile=application-display-1`의 목록 item에는3키를 항상 제공하도록 보완한다. 기존 display의 서버/이름/직업은 신청 snapshot 그대로다.

| key | 필수/nullable·의미 |
|---|---|
| item_level | 필수 string\|null. 유한 비음수 decimal 문자열. unavailable일 때null. 0/최소조건/타역할·분석레벨로 대체하지 않음 |
| item_level_source | 필수 nonnull string. application_snapshot / current_saved / unavailable |
| item_level_fetched_at | 필수 UTC RFC3339 string\|null. 그 값의 저장된 원본확인 시각. 알 수 없으면null이며 신청시각으로 만들어 채우지 않음 |

item_level_source=application_snapshot이면 **Application.display에 실제 저장돼 있던 값**이다. 신청시각은 기존created_at이고 level의 원본시각은 별도fetched_at이다. current_saved이면 **해당 페이지 evaluated_at에 조회한 Character.summary의 현재 저장값**이며 신청 당시 값이 아니다. unavailable이면 값/시각 모두null이다. 다른 표시값과 출처·시각이 다른 것을 허용하고 UI가 당시 레벨/현재 저장 레벨을 혼동하지 않도록 소비한다.

기존 계약의 ‘display는 신청 snapshot’은 서버/이름/직업과 실제 저장레벨에 적용한다. 기존 누락 레벨의 읽기 보완값만 명시적으로current_saved로 구분하는 의미 보완이다. 이 차이와 동적map의 새 metadata3키 소비를 Flutter와 확인한 뒤 구현한다. profile1 실패를 기본조회로 fallback하는 정책은 추가하지 않는다.

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
