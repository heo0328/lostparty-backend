# F1 모집 내부 기반 구현

2026-10-19 / Backend / 현재 `feat/raid-recruitment`(로컬·미push). 기존 `feat/group-management`의 G3 기준349fb79에서 분기했고 G3 브랜치는 보존했다. F1 작성/검증 당시 브랜치 기록과 현재 모집 작업 위치를 구분한다.

[상세 계약 제안](ISSUE_13_R1_R2_CONTRACT_DRAFT.md)·[#13 전체12번째](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6259336924)에 따른 내부 구현 구간이다. **모집 HTTP/API 제공 또는 개발 DB 적용이 아니다.** 코드·migration·시험은 `9664fb4`로 로컬 커밋했고 문서는 후행 설계·진행 기록 커밋에 포함한다. 모두 미push다. G3의 게시 SHA/검증과 새 모집 기반 상태를 혼동하지 않는다.

## 구현 범위

- `app/raid_rooms/models.py`: room/현재 단일회차/membership/신청·directory/개인membership·신청head의6테이블. 같은방 현재회원/자리 unique, 같은방 회차/파티장 복합FK·지연제약, 현재/이력관계와UUID·생성scope/group·당시표시·공통시각을 보존한다. 물리삭제/과거 통계backfill은 없다.
- `commands.py`: HTTP로 공개하지 않은 strict 내부명령. 현재본인선택·source revision, room/round/member CAS, 유한 UTC 일정과 명시역할/당을 구분한다. raw수치/actor/display를 임의명령으로 받지 않는다.
- `core.py`: 현재자격/소유·활동·카탈로그 입장레벨, P1 source/version과 표시snapshot의 분리, 개인방수·한도3원인, 슬롯/당별직업·support상한, 동일회원시간중복/주간점유, usage/목록head와 관계종료 원자처리.
- `service.py`: 내부create, admit(apply/join), decide(approve/reject), withdraw, recover(leave/transfer/end), 본인관계가 있는 get/신청당사자·파티장의 application조회. 세션/현재역할·CAS/멱등lease/generation·원ACK를검사하고실패시전체rollback한다. 외부provider호출·기본허용callback·HTTP라우터는없다.
- `0017_raid_room_foundation`: 0016다음의고정DDL파일이며새6표·제약/인덱스·공통record시각trigger·directory초기head만추가한다. 모델에서DDL을추출해고정SQL로검토했고실행시현재ORM을읽어DDL을동적으로만들지않는다. downgrade는업무자료삭제대신거부한다. **격리테스트DB에만적용**한다.

새생성/참가/신청/승인에는명시policy callback이필수다. 테스트용callback을production기본값으로제공하지않으며고정소유/활동/입장레벨·주간/한도/슬롯검사는callback으로우회하지않는다. P1임의수치로provider입장레벨을덮지않고나이스단OFF/보석issue만으로금지정책을추가하지않는다.

F1내부경계는공개방·현재주차의유한단일회차·전투력문턱미설정부분이다. 미정일정/주차를넘는일정은거절,group생성/참가adapter는미지원이다. 역할별전투력문턱은내부명령자체에열지않았다. 이는Q1~Q3의제품정책확정/요구폐기가아니며F2에서확정된분기만공개한다. group한도3원인의평가원본은기존그룹/한도와대조하되grouproom소비/정리권한을이미연결했다고안내하지않는다.

## 원자성·회복

기존game-mutations-v1 락으로가입/한도변경과직렬화하고현재target User/원본을다시검사한다. 확정membership/slot·WeeklyState점유·본인방수/head·ACK는같은transaction이다. pending은예약이아니고복수신청의지연정리가추가확정을허용하지않는다. 최대8인·당별4자리/서포터1·dealer직업1을검사하고당/역할을자동교체하지않는다.

같은key/body의원성공만복원하고다른본문·24h만료·진행중lease/generation을기존멱등경계로다룬다. replay는현재정상회원/세션과원actor·room/회차/membership/신청참조를확인하며현재leader/재가입권한을옛ACK로복구하지않는다. 재가입은새membership이고옛leave key는새관계를끝내지않는다.

본인탈퇴/기존파티장지정이전/마지막1인종료는캐릭터소유상실·한도초과뒤에도기존회원권한으로정리한다. 해당관계의가입시각과room이일치하는주간점유만해제하며다른방/다른관계·과거완료는손대지않는다. 주차가바뀌어도회복은가능하며새회차/완료를가짜생성하지않는다. room종료의pending은논리cancelled,기한경과는논리expired로읽고GET은원본을쓰지않는다.

## 실행 결과

[#13 전체13번째 Backend — F1 내부 구현·자동 검증](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6259515470)에 결과를 회신했다. 다음 담당은 Backend F2 지원범위/HTTP 연결과 Flutter Q1~Q3 충돌 확인이다. Flutter의 현재 #15 우선작업을 유지하며 모집 API 구현 테스트를 요청하지 않았다.

- 최초F1/시각23 PASS/10.78초, 보강F1·G1/G2/G3·한도·개인주간/시각 회귀 **233 PASS/107.48초**.
- 한도영향 추가1 PASS/3.96초 뒤 최종F1 32개+공통시각3개 **35 PASS/14.99초**. 앞선시험과중복되므로합산하지않는다. 기존Starlette/AnyIO경고1개.
- 슬롯마지막자리/8인당별구성·같은캐릭터별도방동시승인·인접/겹치는일정·weekly/소유/활동/P1분리·정확한도/3원인 비전파/회복을확인했다. 그룹한도시험은격리fixture이며groupadapter완료가아니다.
- ACK실패/최종주차·신청기한변화의전체rollback, 탈퇴/재가입옛ACK·소유상실뒤회복·다른점유보존, GET SQL쓰기0·논리만료·DB unique/지연FK와54업무표공통시각을검증했다.
- 내부모델을포함한새코드의app.openapi()=원본·모집경로없음 자동검사PASS. 현재실행API의scripts/check_openapi.py도PASS지만이미지를새로교체한검사는아니다. 개발DB0016/raid_rooms없음(True)을읽기확인했고새migration은테스트DB만0017로올렸다.
- 전체Backend suite·실provider·실제개발회원쓰기·Flutter/실기기시험은미실행이다. 기존API/DB/자료/키·원격Git은변경하지않았고테스트DB만stop했다. Python컴파일/새파일공백·문서참조/git diff검사도수행한다.

검증명령:

```bash
docker compose -f compose.test.yaml up -d --wait test-db
docker compose -f compose.test.yaml run --rm -v "$PWD/app:/app/app:ro" -v "$PWD/tests:/app/tests:ro" -v "$PWD/alembic:/app/alembic:ro" tests pytest -q -p no:cacheprovider tests/test_raid_room_foundation.py tests/test_group_management.py tests/test_group_management_http.py tests/test_group_admissions.py tests/test_groups_http.py tests/test_group_foundation.py tests/test_member_limits.py tests/test_raid_weekly.py tests/test_record_timestamps.py
# 원인별한도시험추가후최종F1/시각:
docker compose -f compose.test.yaml run --rm -v "$PWD/app:/app/app:ro" -v "$PWD/tests:/app/tests:ro" -v "$PWD/alembic:/app/alembic:ro" tests pytest -q -p no:cacheprovider tests/test_raid_room_foundation.py tests/test_record_timestamps.py
```

## 검증·다음 구간

실행 결과/댓글 링크는 DEV_LOG/NEXT_WORK를 따른다. 테스트DB는 compose.test.yaml의 tmpfs PostgreSQL이며개발DB/기존자료와분리한다. 기존테스트이미지에현재app/tests/alembic을읽기전용mount해검증하므로개발API이미지교체가아니다.

다음F2는현재제안경로/DTO·permissions/페이지·admission-context/정책adapter를검토해확정범위만HTTP/OpenAPI로연결하는구간이다. F1의내부반환딕셔너리를그대로Flutter소비계약으로사용하지않는다. Q1~Q3확인전해당분기를활성화하지않으며G3해산/V2실제파티영향adapter·통계마감/집계/전체완료/반복·고급관리·운영배포는여전히미구현이다. #13전체기능완료/종료나Flutter재시험요청으로확대하지않는다.
