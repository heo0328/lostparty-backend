> **보관된 작업 원문:** 아래 현재·다음·미구현 표기는 작성 당시 상태입니다. 현재 설명: [operations](../../../../../engineering/operations/README.md) · [weekly-cycles](../../../../../features/recruitment/weekly-cycles/README.md). [문서 대응표](../../../../../engineering/documentation/README.md). 원문 바이트와 근거는 기준 커밋 `7f7f767`에서 확인합니다.

# Issue #13 W5 — 실제 자료 영향·백업/복원 리허설

2026-10-22 / Backend / `feat/raid-recruitment` / 시작 `f276342`.

AGENTS → 협업 → NEXT_WORK → AI_CONTEXT → 계약3판 전환/4판/ACK와 Git·공식 Issue 본문/전체90댓글을 확인했다. [전체90번째 Backend · W5 결과](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6331483028) 이후 추가 요청/계약 변경·사용자 미커밋 변경은 없었다. 사용자 요청의 다음1구간인 실제 자료 영향·보존/복구 준비를 진행했다. **현재 개발 API/worker 정지·DB 이행·이미지 전환은 하지 않았다.**

## 수행과 근거

[공개 집계 proof](../../../../../engineering/operations/records/weekly-cycles-restore-preflight.json), [실행 도구](../../../../../../scripts/recruitment_restore_preflight.py), [스냅샷/읽기 검사](../../../../../../scripts/recruitment_snapshot.py), [격리 Compose](../../../../../../compose.preflight.yaml), [보호 시험](../../../../../../tests/test_recruitment_backup_guards.py).

1. 현재 개발 API/DB의 identity·이미지·0023을 확인하고, 별도 읽기 전용 source-reader(포트/worker 없음, 구 이미지/동일 환경·읽기 전용 키 mount)의 READ ONLY/REPEATABLE READ 연결의 `pg_export_snapshot()`을 유지하며 전체 테이블 지문과 같은 snapshot의 custom-format pg_dump를 확보했다. 개발 API는 실행을 유지했다. archive에는 원래 owner/ACL metadata도 보관하며, 격리 복원에서는 `--no-owner/--no-acl`로 app 역할에 객체 소유/필요 권한을 재구성했다. PostgreSQL 전체 global role/다른 서비스 권한의 재해 복구 시험으로 확대하지 않는다.
2. DB archive·인증 키 파일 전부·환경 파일·실행 설정은 Git/Docker build에서 제외된 `backups/`의0700 디렉터리/0600 파일로 보관했다. 실제 사용자 원본/토큰/비밀키·환경 값과 명령 원본 오류는 출력·커밋·Issue에 게시하지 않았다. 공개 proof는 집계·일치 여부/이미지ID·archive integrity hash만 포함한다.
3. 별도 `internal` 네트워크·tmpfs PostgreSQL17에 fresh DB를 만들고 `lostparty_app` 제한 LOGIN으로 표준입력 archive를 복원했다. 복원 후 DB/public schema 소유권은 postgres로 돌려 앱 객체 소유/USAGE·CREATE만 사용하는 실제 구성과 맞췄다. 앱은 NOSUPERUSER/NOCREATEDB/NOCREATEROLE·DB 비소유자이며 새 API/readiness·이행을 이 역할로 검사했다.
4. 별도 빌드한 후보 이미지에서 복원본만0023→0029로 이행했다. 복원본 앱 컨테이너는 포트/host volume 없이 read-only filesystem·capabilities 제거·tmpfs 키와 제한 네트워크를 사용했다. provider/기기 호출과 실제 명령은 수행하지 않았다.
5. 같은 archive를 **다른 fresh0023 DB**에 다시 복원하고 실제 구 이미지의 준비 검사/health 함수·조회와 원본 지문을 검증했다.0029→0023 downgrade나 기존 개발 DB overwrite를 복구로 사용하지 않았다.
6. 최종 코드 리허설 종료0을 확인하고 전용 컨테이너·tmpfs DB·네트워크를 정리했다. 원래 개발 컨테이너 identity·이미지·DB0023·키 일치/healthy를 재확인했다. 원본 개발 volume은 유지했다.

검증된 로컬 비공개 archive 기준 디렉터리는 공개 proof의 `backup_relative_path`다(이번 `backups/lostparty-preflight-a0de630e7891`). `database.dump`, `auth-keys.tar`, 환경/실행 설정·원본 지문/결과 private metadata를 보관한다. 디렉터리0700·모든 파일0600, Git ignore·Docker ignore를 확인했다. 앞선 시도 디렉터리를 검증 기준으로 사용하지 않는다. 비공개 파일은 GitHub에 올라가지 않는다.

## 실제 자료 보존 결과

| 검증 | 확인 결과 |
|---|---|
| snapshot→첫 복원 |83개 테이블·414개 행의 모든 열/record 시각 지문·열 정의 일치 |
| 복원본0023→0029 |alembic_version의 의도된 값 변경을 제외한82개 기존 업무 테이블·413행의 원장/관계·ACK/시각·열 정의 일치 |
| 새 schema 준비 |제한 LOGIN/DB 비소유자로0029 전체 readiness 통과·factory OpenAPI167경로 생성 |
| 과거 분류 |실제 과거 RoomCycle7/참가 관계7을 legacy_unknown·generation null·review_required로 보존, assignment evidence7 |
| 권한/동의 임의 복원 |explicit cycle0·participating member0·새 consent0 |
| 추가 보존 |시퀀스1개 last_value/is_called·UTF8/en_US.utf8·인증 키4개 bytes 일치 |
| 조회·worker |실제 유효 세션2명의 읽기 투영과 worker 후0029 전체 테이블 지문 불변 |
| 구 버전 복구 |별도 fresh0023의83개 테이블/414행·시퀀스/encoding/collation·키 일치, 구 이미지114경로/준비 검사·health 함수 통과 |

이것은 실제 개발 자료 복원·이행 리허설이다. 이전 W5의 합성304고유 자동 시험을 다시 실행하거나 두 결과를 합산한 것으로 표시하지 않는다. 보존 실패/열 누락·행/시각 변경 감지와 키 archive overwrite/path traversal/absolute path/symlink 차단의 **합성 unittest7개 통과(0.002초)**도 별도로 확인했다. 신규 API/계약/DDL/기능 동작 변경은 없다.

예비 실행에서 Docker tmpfs archive 경로 접근은 stdin 복원으로 바꿨고, 구 이미지 health 함수가 사용하는 DB 이름/앱 credential 환경을 격리 역할에 맞췄다. DB/키/환경·시퀀스/정렬 규칙과 실제 읽기 영향을 포함한 최종 실행은 전부 통과했다. 원본 오류/자료는 private 진단으로 제한했고 최종 미해결 실패는 없다.

## 전환 시 실제 보이는 차이

기존 방/관계7개와 Assignment/Round7개는 삭제하지 않는다. Assignment/Round는 모두 `stopped_incomplete`이고 실제 주차는 모두 C/N 밖이다. 이 원천만으로 현재 주차·개방 세대·공대장/예약 동의를 추정하지 않는다.

- 구 이미지 기본 공개 검색은7건, 준비 앱의 현재 C/N 공개 검색은 각각0건이다. **과거7건을 현재 모집에서 제외하는 변화**를 Flutter/사용자 전환 인계에 명시한다.
- 유효 회원들의 persistent 관계는 C/N 목록에서 각각7건 유지되며 current target 상태는 `not_selected`다. 카드/현재 실참가·리더/명시 세대를 자동으로 생성하지 않는다. 현재 plan은7건 모두 TARGET_NOT_OPEN이다. 원본7개 과거 cycle은 계속 review로 보존한다.
- 본인 관계 정리용 leave-context7건은 allowed/impact_cycles=[]로 조회된다. 실제 leave/end 명령은 실행하지 않았고 관계·한도를 자동 회복하지 않았다.

이는 복원본의 **서비스 읽기 검사**다. 실제 모바일 UI·HTTP/JWT 재인수나 복구한 원 ACK의 실제 사용자 재전송·provider·기기 시험이 아니다. 실제 source backup의 ACK 저장 행은 지문으로 보존했고 원 ACK 동작의 합성 근거는 기존 W5 검증을 따른다.

## 다음 실제 전환 구간의 경계

현재 source는 계속 DB0023/API114경로/구 이미지 `efde69d…`로 healthy다. 로컬 후보 이미지 `lostparty-two-cycle-preflight:f276342` / image ID `ccc787c…`를 별도로 빌드·검증했으며 실제 개발 API tag/실행은 바꾸지 않았다. 전체 image ID는 공개 proof에 있다. [전환 override](../../../../../../compose.two-cycle.yaml)는 기존 검토 상태를 유지한다.

1. **대상/영향 확인**: 로컬 개발 DB0023→0029·API8000/worker를 함께 전환하는 대상과 위 과거7건 목록 차이를 확인한다. 기존 volume·환경·키·원본/ACK를 보존하고 임의 정리·세대/동의 복원은 하지 않는다. merge·운영배포·데이터 삭제와 구분한다.
2. **전환 직전 checkpoint**: 구 API와 모든 worker를 정지한 뒤 같은 방식의 새 DB/키/환경 백업과 복구 기준을 확정한다. 이번 snapshot은 서비스 실행 중 확보했으므로 **실제 전환 checkpoint가 아니다**. 이후 새 쓰기를 포함하지 않으며 sequence 상태도 MVCC snapshot과 독립적이다(이번에는 복원/이행/복구에서 엄격 일치를 확인했다).
3. **실제 이행/시작**: 검증한 소스/이미지·제한 app 역할로0029 이행/보존을 확인하고 factory와 새 worker를 함께 기동한다. schema23 이미지/구 worker 혼용을 막고 health·167경로 전체 계약·인증/회원 격리·v1 upgrade/안전 쓰기·C/N/주차 경계를 필요한 범위에서 확인한다.
4. **복구 조건**: 새 쓰기 허용 전 문제가 있으면 승인된 새 checkpoint를 **별도 DB에 복원**해 지문/키/구 이미지 readiness 확인 후 연결을 전환한다. 새 쓰기를 받은 뒤에는 snapshot 복원으로 새 데이터를 버리지 않으며 영향/보존 처리 범위를 다시 확인한다. 이번 구간에 실제 source overwrite/drop·downgrade는 없다.
5. **Flutter 인계**: 실제 사용 가능한 경로/실행 SHA·계약·확인/미확인 범위를 준비하고 commit/push·원격 확인 후 같은 Issue로 필요한 주차/summary·계정 캐시 격리 구간만 인계한다. 현재 소스 게시만으로 새 서버 시험을 요청하지 않는다.

첫 명령은 host 표준 Python/Docker CLI, 전환 직전에는 운영자가 구 API/모든 writer를 정지한 뒤 같은 도구에 `--quiesced-checkpoint`를 명시한다. API가 실행 중이면 이 모드를 거절한다. 실제 정지 구간/외부 writer 중단까지 이번에 실행한 것은 아니며, 이번 proof의 cutover_checkpoint=false를 유지한다. 둘째 unittest 명령은 앱 의존성이 설치된 Python 환경용이다. 이번7시험은 네트워크가 없는 read-only 후보 컨테이너에 공개 도구/시험 코드만 전달해 실행했다. 재현 도구는 source0023/개발 컨테이너명을 고정하고 source에는 snapshot/pg_dump/read만 한다. 실제 서버를 바꾸는 migration/restore는 새 임시 컨테이너에서만 수행한다.

```bash
python3 scripts/recruitment_restore_preflight.py --docker docker.exe \
  --image lostparty-two-cycle-preflight:f276342 \
  --report docs/features/recruitment/artifacts/issue13-restore-preflight.json
python -m unittest discover -s tests -p test_recruitment_backup_guards.py
```

다음 담당은 Backend의 실제 전환 대상/영향·승인 범위 확정과 개발 서버 전환이다. Flutter 적용/실회원·기기·운영 인수는 미완료다. 구현 `372988108b8e7054d76da94838162480c3a2c12c` commit/push·실제 원격 SHA 일치 확인·[전체91번째 Backend · W5 복원 준비 결과](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6332223435) 게시 완료. 게시 결과는 [DEV_LOG](../../../../../project/DEV_LOG.md)·[NEXT_WORK](../../../../../project/NEXT_WORK.md)에 이어 기록한다.

Issue 본문 상단은 실제 자료 영향/복구 준비 완료·다음 Backend 개발 DB/API 전환으로 갱신하고 이전 원문/합의 이력을 보존했다. 본문 제외 실제 전체 순번91·Backend 작성 측·W5 복원 준비 단계를 재조회했으며 OPEN을 유지했다. source 전환·Flutter 인수 완료로 확대하지 않는다.
