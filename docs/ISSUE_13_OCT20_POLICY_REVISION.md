# #13 10/20 정책 변경·Backend 계약 보완안

2026-10-20 KST / Backend / feat/raid-recruitment / 기준1ed098b. **요구 반영·설계 제안이며 구현/최종계약 확정이 아니다.** [기존 통합기획](ISSUE_13_INTEGRATED_BOUNDARY_PROPOSAL.md)의 상충 부분은 이 문서가 대체한다. 전원동의·회원시간배타/중복409·끝상한없는예약미생성·OFF강제갱신·명단변경시동의일괄무효화·미인증개인표확대는 최신 기준으로 사용하지 않는다.

근거(본문제외 전체순번, 모두Flutter): [34 기술보완접수](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6269403063), [35 번호별결정](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6270163272), [36 OFF/외부신청/동의집합정정](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6270650065), [37 동의수/기본예약/다음주개시](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6271031885), [38 확인대기·시간중복경고](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6271302986), [39 최종명료화](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6271448868).

공유: [#13 전체40번째 Backend 최신 보완](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6271452128), 최종39번째 요구 포함 **c47afef 로컬커밋·미push**. 다음 Backend 고정 계약 정리/Flutter 소비대조이며기획회신을실제API완료로안내하지않는다.

## 1. 확정 요구와 이전안의 교체

| 분야 | 최신 기준 |
|---|---|
| 마감 | 출발30분전까지 신청/즉시참가/수락·최종승인. 최초임계치09:10합류→09:30첫확정은성공후추가모집즉시마감. 첫확정부터now+30여유를강제하던Backend안미채택 |
| 점검/기간 | 수06~10 KST는제품불가창, 수동/자동공통. cycle키수06시유지. 개인1구간최대24h, 유한기간10분~24h/5분. 구간·타임개수상한미정 |
| 동의 | N=2→2표,3→2,4→2,5→3,6→3,7→4,8→4. 제안공대장1표포함. 무응답찬성아님/한명거절즉시전체취소아님. 미완료종료재개에도적용, 전체클리어공대장/클리어취소금지는별개 |
| 동의/합류 | 동일proposal/plan의기존개인동의보존, 신규는가입후변경안동의/탈퇴2응답. 기존은승낙/거절/탈퇴3응답. 명단revision만으로표를지우지않음. 제안내용변경은별개 |
| 가능표/중복 | 표밖본인명시참가/동의허용·개인표자동수정금지. 다른방시간중복도명시참가/승낙·예약거절금지/경고만. 겹친둘다보존. 동일캐릭터raid/cycle중복·완료가드등유지 |
| 미동의자 | 관계유지·초록‘참가 확인 대기’, 본인확인시참가확인+본인예약생성. 단순읽음아님. 빨강불참/자동추방·무응답찬성/다시전원동의아님 |
| 기본예약 | 기간미지정/클리어시까지: 1단계/normal10분,2단계/hard20분,3단계/nightmare30분. 출발미정은기간만/UTC예약없음. 게임최대시간·자동완료아님 |
| 혼합묶음 | 4/8게임레이드혼합묶음만앱공통일행최대4명. item게임정원4/8, 8인나머지인게임모집. 기존단일8인방은그대로 |
| 그룹왕복 | 공개접수외부pending은그룹전용복귀후에도유지/승인가능. 새외부신청과구분. 기존외부인접근유지/상세조회권한자모두에게그룹·비그룹배지 |
| 점수/OFF | 선택역할최근성공점수, 최고점아님. 빌드오류는표시/오류자체가입금지아님. OFF신청중강제갱신안함/새staleTTL우회차단금지. 점수누락과경고분리 |
| 공개조회 | 현재방제출표+다른예약익명점유·부분집합교집합범위채택. 개인전체표/다른방제목·raid비공개. 체크는명단/투표분모변경아님 |
| 인증/다음주 | 기존조회용미인증등록유지. 새개인표·모집은현재인증원정대있는회원필수. 다음주개인유지선택채택, 미래활성assignment/예약선생성안함. 수10시이후재개확정·체크자동/미체크공대장수동. checkbox기본값등만세부대조 |

이 표의 확정 요구와 아래 Backend 추천·미정 효과를 구분한다.

## 2. 시간 중복 경고형의 원자명령

명시 join/apply/approve/accept/예약변경은 시간중복·개인표밖만으로409/rollback하지 않는다. 기존 core.require_no_time_overlap은 이 경로의 차단가드로 재사용하지 않고 overlap detector를 분리한다. **현재 후보 모델에도 회원 시간배타 reservation 제약은 없으므로 지금 실제 DB 제약을 삭제할 것은 없다.** 기존 기획의 exclusion/btree_gist 예약배타 추가는 철회한다.

39번째에 따라 자동후보는 다른예약을 피하고 명시신청/승낙·확인은 겹침을 허용한다. 자동중복선택을 임의 추가하지 않는다. auto_no_candidate/search_limited는 ‘추천 실패/계산 한계’이지 명시행동 불가가 아니다. 조율형 임의시간 우회확정 API를 만들지 않고 리더제안→동의기준→최종검사 경로로 연결한다.

최종쓰기 제안: 세션/권한·proposal/plan/assignment CAS→캐릭터raid/cycle·정원/슬롯·한도/마감·점검/고정하한→정확귀속원예약해제/새예약→겹침현재요약→ACK 단일commit. 시간겹침만 실패사유에서 빠지고 다른방예약해제/이동은 하지 않는다. 원ACK는 효과를 재실행하지 않는다.

본인 전체현재예약 요약 GET 후보: {revision,evaluated_at,conflict_count,items:[{my_reservation_ref,room_id,item_id,round_id,session_id,character_display,raid_display,room_title,start,end,overlap_refs}],next_cursor}. 검출모집단은 현재 화면 필터/페이지와 독립한 회원 전체다. 제목/링크는 현재 본인 접근권한을 재검사하며 무권한·과거대상 원문을 공개하지 않는다. 상단고정은 후속UI, 푸시/반복모달은 아니다.

겹침은 [start,end), 끝=시작 허용/간격0. 동일session/participation/schedule_revision 자기예약 중복제거, 다른방의 두예약은 보존한다. 현재주차 활성예약의 회원별start 정렬+sweep 후보안이며 전역 모든회원 교차탐색은 안한다. 출력폭증 방지 범위/페이지·요약revision은 계약으로 정하고 부하를 측정한다. ‘참가 확인 대기’와 overlap_warning은 별도 필드라 경고가 있어도 대기글씨를 빨강으로 바꾸지 않는다.

## 3. 동의수·합류·내용확인의 최소 모델

proposal=(대상round/session집합,불변plan_revision,제안내용hash). 개인표는 proposal_id+plan_revision+membership_id/가입세대로 보존한다. members_revision을 표의 PK로 삼지 않아 같은안의 기존동의를 유지한다. 탈퇴한 표는 이력으로만 남고 현재표수에서 제외한다.

최종 DB시각의 현재대상 실참가집합N으로 문턱을 재계산한다. N>=3은ceil(N/2), N=2는2, 신청pending/그래프체크는제외. **단독N=1과 선택session별 정확한 대상 분모는 별도 확정**한다. 공대장찬성은 저장된1표다. 제안내용변경은새plan_revision이며 기존표를 재사용하지 않는다. 같은안 신규참가만으로 전부무효화하지 않는다.

신규참가 제안: 슬롯/이번주assignment·현재유효일정의예약+현proposal 응답pending을 같은명령에서 저장한다. 아직 변경안이므로 원일정과 새제안의 예약을 동시에 선점하지 않는다. 새회원은동의/탈퇴, 기존은3응답이다. 명단변경에 따른 문턱충족은 GET가 아니라 명시명령/응답transaction에서 최종평가한다. 확정후 입장자는 최신일정 가입조건으로 처리한다.

### 39번째 반영 — 확인은 본인 예약 생성

기존 A/B 미정 대조는 39번째로 대체한다. 미동의 기존참가자는 초록pending을 유지하고 본인이 확인하면 새일정 참가확인+본인예약을 처리한다. 단순 읽음이거나 미동의자에게 미리 새예약을 투영하는 추천A는 사용하지 않는다.

원자효과 제안: 문턱충족으로 새schedule_revision을확정할때 찬성자의새예약은생성하고, 미동의자는old schedule예약을해제/새예약없음pending으로둔다. 구일정예약해제는obsolete schedule효과로분리해사유를남긴다. pending개인확인명령은현재회원·cycle/round/session/schedule_revision과본인participation revision을재검사한뒤참가확인/confirmed_at+그schedule의본인예약+겹침경고+원ACK를같이commit한다. 새신청이아니므로마감후기존회원확인을막지않으며중복예약은경고만이다.

확인귀속=(회원,membership세대,cycle,session/schedule_revision,confirmed_at). 동일key원ACK는예약을다시생성하지않고다른key라도같은participant/schedule의예약unique로중복효과를막는다. 최신일정과다른revision은409/재조회해옛일정을최신으로확인하지않는다. 이미종료된session/assignment/방의참가를확인만으로부활시키지않는다. 종료후단순이력읽음은참가확인명령과분리한다. 같은안신규가입시기존표유지/명시신규동의와본인확인은별도액션이며권한/CAS/귀속은공유한다.

## 4. 마감·점검·기간·기본예약의 계약안

최초임계치09:10명령이 고정생성하한09:30을 만족하는 첫출발09:30을 확정하는 예외를 채택기준으로 반영한다. 일반명령이 client flag로 이예외를 위조하지 않도록 최초확정 내부명령에 묶는다. 확정후 deadline=start-30분, ‘까지’의 동일시각 포함 여부는 deadline 포함 비교를 추천하며 바로직후 거절하는 경계예시를 대조한다. 출발후 과거확정은 별도 현재시각 검사로 막는다.

수요일 KST 점검창 [06:00,10:00)과 **전체 실제진행구간**이 겹치면 수동/자동 모두 불가다. 05:55~06:05 불가,10:00시작은점검창밖. 05:50~06:00은점검창과 비중첩이지만 별도cycle귀속/종료경계 검사를 통과해야 한다. 기본/명시기간 모두 같고 출발시각만 검사하지 않는다.

명시기간10분~24h/5분이면 난이도default보다 우선한다. hard명시10분을20분최소로강제하지 않는다. 미지정/clear_until만 catalog_version+raid_id+difficulty_id→10/20/30 규칙을 사용하고 source=explicit|difficulty_default, policy_version을 snapshot한다. 현catalog에는 normal/hard/nightmare 및stage1/2/3가 있다. display_order는정렬값이므로 권위 규칙으로 쓰지 않고 현재13difficulty의 명시mapping을 검증한다. 알수없는4단계/새ID는10분fallback없이 규칙미지원으로 표시한다. 출발미정은reserved_duration만 있고 start/end=null, 확정때 UTC예약을 생성한다.

39번째의 기간대체/합산을 반영한다. duration_scope=item인 경우 각 item의 명시기간이 있으면그값, 없으면난이도default를사용하고순서대로합산한다. 미지정normal+hard+nightmare=60분, 명시hard40+미지정nightmare30=70분, nightmare명시30=30분(60분아님). 회원session 예약은 합산연속구간1개이며 item segment는 합산 범위에 귀속해중복계상하지않는다.

duration_scope=bundle_total 후보는 명시총기간을딱한번사용하며하위default를다시합치거나모든item에총기간을복제하지않는다. PUT는 item durations와bundle_total을배타입력으로검증해둘다입력하면400을제안한다. bundle_total에는근거없는item별시간을분배하지않고그룹session예약에item참조만보존한다. item순서/부분완료후잔여구간·합계24h상한의정확한범위는기술계약으로대조한다. 게임최대시간/자동완료를만들지않는다.

## 5. 혼합묶음·다음주 선택/재개

혼합묶음에만 app_capacity=4, item.game_party_size=4|8을 명시하며 단독8인방capacity8은 유지한다. ‘앱4/4·게임8인중4명/나머지인게임모집’을 구분한다. 기존8인2서폿/2파티 슬롯검사를 혼합일행4명에 그대로 적용하면 충돌하므로 item별역할·앱슬롯/완료대상을 확정한다. 공통catalog party_size를 덮지 않는다.

다음주선택은 intent이며 미래 active assignment/시간예약이 아니다. 제안 continuation_choice의 활성유일키=(회원,canonical character,raid,target_cycle), 참조room/item/membership/choice_revision·소유세대를 보존한다. 같은회원 다른캐릭터 선택과 room한회원한자리·한도를 함께 검토하며 추가 미래시간배타를 만들지 않는다.

- A이번주미완료종료는함께하기ON전제. B이번주참가를허용하되A다음주선택자동덮기안함. B유지선택때A유지/명시전환을표시한다.
- A→B는 expected_choice_id/revision과 양membership/현재소유/대상cycle을 한transaction에서 검사해구intent종료+새선택저장. 동시선택은unique/CAS409, 묶음여러raid선택은전체성공/rollback, 충돌선택상세는본인만본다.
- 캐릭터교체는해당raid choices도함께CAS변경/실패시전체rollback. 같은캐릭터다른raid는독립. 같은회원복수캐릭터/같은room자리·미완료종료선언권한/묶음종료scope는필수확정대상이다.
- 수06시cycle전환만으로 미래예약/active배정을자동생성하지않는다. 다음주개시의서버worker/리더명령은(item,cycle)unique로같은round를ensure한다. 재시도는기존개시시각을보존한다.
- 39번째로수10시이후재개는확정이다. 체크방자동/미체크공대장수동이며manual도10시이후를검사한다. checkbox기본값·재개시자격상실선택의처리는고정계약에서대조한다. 실제재개DB시각을불변recruitment_opened_at으로저장/+30분하한제안. 늦은worker가11시에열었다면11:30이며10시로위조하지않는다. 앱실행/로컬타이머전제안함.
- 지속membership은현재방한도에남는다. intent저장이새membership/생성실적을자동생성하지않고#19주간통계/함께하기마감snapshot과분리한다.

## 6. 점수·외부pending·인증

최근성공 선택역할 summary의 값/version/관측시각과 같은분석의 경고를 묶어 소비한다. 실패갱신이 이전성공을 지우거나 최고점으로 선택하지 않는다. OFF는앱실행/신청중 강제refresh예외를 유지하고 경고는 표시만 한다. missing_score와build_warning을다른reason으로둔다. 새stale만료규칙으로OFF를우회차단하지않고 observed_at/last_success_at/source/trust로관측상태를표시한다.

P1제출분석의 신뢰한계는남는다. 서버저장version/CAS검사는게임원값진위를증명하지않는다. 선택역할P1비교를받아들일지/다른검증원천과점수누락때문턱처리는제품결정이남았다. 기존P1 GET/PUT·소유/lifecycle/role version을재사용하고최종신청/승인에서현재성공버전을재검사한다. Flutter개별회원카드갱신복구는그쪽독립범위이며이를이유로새전체Armory API를만들지않는다.

공개접수 application에는 immutable admission_scope=public·room scope revision/접수시각/원actor·신청ID를 snapshot한다. 그룹복귀후승인은이원접수사실로외부예외판정하고현재그룹미가입만으로거절하지않는다. 새신청은현scope검사, 취소후재신청이원예외를승계하지않음. 현재정원/소유/역할·주간/시간/마감/한도는그대로최종검사한다.

신청전체목록은현재그룹A자격+기존관리권한. 외부신청자는본인최소상태만보고모든목록을열지않는다. 전체상세조회권한자는각카드그룹/비그룹배지를같은snapshot으로본다. 그룹왕복시연결그룹변경/비그룹리더권한등남은범위는별도확정한다.

새개인표/모집쓰기에는현재인증원정대소유를server판정하는안을반영한다. 기존D10조회등록·인증증거·원ACK복구최소자료는삭제하지않는다. 인증상실개인표자동삭제없음, 신규읽기/쓰기거절과기존참가정리/내용확인권한은분리한다. 새자동퇴장정책을추가하지않는다.

## 7. 일괄 공대원 그래프·익명busy 최소 계약

후보 schedule-context GET는 현재방membership 권한으로한 snapshot에서조회한다. {room_id,cycle_key,room/members/plan_revision,evaluated_at,members:[{membership_id,display,submission_revision,submission_state:missing|ready|unavailable,submitted_intervals,anonymous_busy_intervals,busy_revision}],...permissions} 응답안이다. 개인표원본/다른room·raid/예약ID는없으며busy구간은union해건수역추정을줄인다. 알려진빈[]과미제출/읽기실패를구분해실패를빈표로바꾸지않는다.

부분집합체크는같은snapshot의로컬비교이고투표분모/명단변경아님. no-store, membership상실시privatecache삭제/늦은응답무효, cycle/plan/submission/관련busy revision변경시재취득/명시갱신, 최종쓰기는모든현재대상재검사. 공개검색/비참가그룹원에게busy를노출하지않는다. HTTP는일괄1회, DBbulk조회·회원/시간인덱스·현재cycle범위로제한하고상한/응답시간은측정후계약화한다. 조회체크해제된인원도실제합의/최종검사에서제외하지않는다.

## 8. 남은 확정 게이트와 다음 단계

1. 확정된본인확인→참가확인/예약생성에따른old예약해제/pending/확인명령의고정DTO·귀속, 현재대상분모/session과N1·신규가입순서.
2. 다음주선택의회원복수캐릭터/한자리와명시전환·선언자격·묶음종료scope, 혼합4인role/슬롯/완료대상.
3. 자동재개기본·자격상실, 점수missing/신뢰, 확정된기간대체/합산의duration_scope/부분완료·전체상한, 구간·타임개수상한. 수10시이후/명시기간default중복가산금지는다시묻지않는다.
4. 익명busy고정DTO/권한·무효화경계, deadline동일시각, 고정계약/기존단독8인·개인완료guard의정합성.

이미확정된중복허용/자동회피·본인확인의예약효과·수10시재개·기간대체와합산·동의수·OFF·오류표시·점검정책을재질문하지않고고정계약과남은효과만대조한다. Backend회신→Flutter대조/필요사용자결정→계약확정→통합목표내부구현/검증순서다. 이번은문서/코드대조이며코드/migration/OpenAPI/DB/이미지·서버/시험/배포변경없다.

게시직전39번째최종명료화를추가확인해같은Backend40번째회신본문을최신화했다. 34f185e는38번째까지의중간설계이며확인효과A/B·자동회피/수10시미정표현은이후정정으로대체된다.
