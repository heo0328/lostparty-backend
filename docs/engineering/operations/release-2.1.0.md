# Backend 2.1.0 공동 릴리즈

2026-11-11 / Issue49 / 사용자 승인 6단계 실행 원본. 현재 상태는 [NEXT_WORK](../../project/NEXT_WORK.md), 실행별 근거는 [DEV_LOG](../../project/DEV_LOG.md)에 기록한다.

## 기준과 책임

- 운영 v2.0.0/source51b1cb3/imagef33f4c6c/DB0035, 후보는 DB0036·기본125/142·two-cycle192/213. Backend 버전2.1.0/full 검증, 과거 reuse 예외는 재사용하지 않는다.
- [합의/실물 인계](https://github.com/heo0328/lostparty-backend/issues/49#issuecomment-6793794562)와 [독립 수령](records/web-handoff-2.1.0.json)을 기준으로 Native는 웹 build/manifest·APK·서명/기기 인수, Backend는 산출물 검증/서버배치·API/DB·백업/동결구성을 담당한다. 최종 공개는 함께 진행한다.
- 웹 원3파일은 ignored backups/web-handoff/artifact-13849320316에 보존했다. 수령 검증/로컬비활성만 완료, AWS전송/활성화·실브라우저/운영기기 인수는 미완료다. 재빌드/재압축/다른artifact 묵시대체 금지.
- 서비스키4개·관리자/제한배포SSH는 재사용한다. 새Android client 1개를 기존azp2개에 추가하되 Web audience·서명/nonce 검증을 유지한다. Native 백업을 Backend의 새 선행작업으로 만들지 않는다.

## 단계와 완료 조건

| 단계 | 작업·완료 조건 |
|---|---|
| 1 현재변경 정리 | CORS·W3/W4·백업 근거와 이 설계를 기록하고 CORS/두계약/문서/JSON/diff 확인. 미완료를 구분 |
| 2 첫 통합 | 최신원격확인→현재변경커밋→dev 이력보존병합→main 동일SHA→두원격push/일치→release/2.1.0 생성. 태그/운영변경 없음 |
| 3 로컬 준비 | 웹수령/안전검증/inactive/활성화·Caddy·동결구성·maintenance 전환·OAuth변경안·복귀를 구현/격리검증 |
| 4 후보 고정 | VERSION2.1.0/full 계획·Backend소스/image/계약/DB/설정·웹/APK 식별 고정→회귀/전체계약/도구검증→dev/main 재통합/push→CI·불변이미지 확보 |
| 5 운영 적용 | 최신DB/환경·키/동결구성·복구도구를 기존PC폴더 새날짜 사본으로 보관/무결성확인→잠금/점검/쓰기중지→0036 migration→환경/Backend/웹구성→정상확인 |
| 6 공동 공개 | 점검접근으로 Backend/Native 담당별 인수→조정된 점검해제/Native Release 공개→Issue 결과/미확인/실제공개 기록. 종료는 별도판단 |

## 배포 구현 계약

일반 릴리즈의 기존 자동 검증/이미지게시/API교체 경로를 유지한다. 이번 릴리즈는 명시적인 maintenance 계획으로 자동 API교체를 보류하고 불변이미지 확보 후 관리자가 승인된 전환도구를 실행한다. 제한SSH의 DB/인프라 보호나 shell 제한을 완화하지 않는다. DB revision/설정이 다른 상태에서 일반배포를 강행하지 않는다.

웹수령은 고정 run/artifact ID/name/만료/fullsource/ZIP SHA256과 root3파일·내외manifest바이트·filehash·POSIX안전경로/중복/링크거절을 검증한다. 검증된 site만 고정parent/releases 아래 readonly 제공, 상대 current로 교체한다. manifest/zip/checksum은 공개root 밖에 보존한다. 실패시 기존current를 유지한다.

Caddy는 /v1·/v2·/health 정확경로/하위를 API에 우선 전달한다. 화면만 index fallback, 누락자산404, wasm MIME과 실행/bootstrap 캐시재검증을 검증한다. 점검상태는 API와웹의 공개요청을503으로 제한하되 내부검증 경로를 남긴다. 인증서volume/네트워크/DBvolume 보존. 새탭/재접속 인수이며 구탭 무중단/미전송작업 자동이전은 지원하지 않는다.

환경/Compose/Caddy와 실제 current/previous의 동결구성/configuration revision을 함께 정렬하고 다음 API배포에서도 웹mount와환경을 보존한다. 동일릴리즈 조합에 Backend/image/계약hash/DB/configrevision·웹source/hash·APKsource/hash·인수결과를 기록한다.

## 검증·운영·복귀

- 로컬: 원구프로필/단건GET·POST/원query·원ACK와 신규/pending 차이, capability/group_policy 업그레이드거절·CONTEXT_INVALID, 신규4묶음경로·캐릭터문제 경로·두전체계약을 확인한다. 실패를 skip/과거PASS로 대체하지 않는다.
- 도구: 위조zip/hash·탈출/중복/링크·source불일치/만료/묵시대체거절, 원3파일보존·활성화실패시기존current·웹복귀·실정적HTTP/SPA/404/cache/MIME 검증.
- 운영직전: 기존백업준비는 재사용하되 최신dump/변경대상설정만 갱신한다. 실제PC폴더 접근을 확인하고 사본검증 후 쓰기를 중지한다. 이미지사전확보·배포잠금·DB/키/설정 보존비교를 준비한다.
- DB0036 전 실패는 기존구성복귀. 적용후 구0035전용이미지/DB downgrade 자동복귀 금지, 점검을 유지하고 전진수정한다. 백업복원은 자료영향이 있는 별도 결정이다.
- 정상Backend+웹실패는 웹만 이전/current없음(API-only)으로 복귀한다. 공개전 실패는 점검유지, 자동공개하지 않는다. API/DB/전체계약/정적HTTP는Backend, 로그인·보호조회·모집생성/재조회/재로드/로그아웃·새APK로그인은Native/사용자가 확인한다.

기존 배포·백업 기준은 [배포 안내](backend-release.md)와 [백업 원장](backup-and-recovery.md)을 따른다. 현재 설계의 작성/통합은 도구구현·운영검증 완료를 뜻하지 않는다.

## 실제 준비 결과와 명령

첫 통합은 `ba5b0fb`를 이력 보존 병합한 `09b46f991dc18538a8b3995d6cd310d0fee4c003`이다. 원격 dev/main 일치를 확인하고 release/2.1.0을 생성했다. 현재 다음 도구는 로컬 구현이며 후보 고정/두 번째 통합 전이다.

- `scripts/deployment/web_release.py`: receive/verify/stage/activate/rollback. receive는 고정 GitHub artifact 메타·만료/run/source/digest를 확인하고, stage는 원3파일 보존과 안전경로·manifest·개별hash를 검증한다. activate는 Backend 호환 확인이 있어야 동작한다.
- `scripts/deployment/backup.py`: capture/copy-confirm. 기존 키를 생성하지 않고 운영 dump/환경/4키/동결상태·복구도구를 보관한다. PC 사본 SHA256을 독립 비교한 뒤 확인 결과를 기록한다. 실제 복원 검증과 구분한다.
- `scripts/deployment/maintenance.py`: preflight/apply/open. 기존 제한 SSH에는 추가하지 않는 관리자 전용 도구다. clean 고정소스/manifest·이미지/DB/backup을 확인하고 전환한다. apply 완료도 public_open=false이며 open은 같은 조합의 양측 인수/공개 확인이 있어야 동작한다.
- `release-deployment.json`: 2.1.0만 maintenance로 명시한다. 기존 workflow는 full 검증/이미지게시를 유지하고 이 릴리즈의 자동 deploy만 건너뛴다. 다음 일반 릴리즈에서는 이 파일을 제거해 standard 경로로 돌아간다. 누락된 mode를 maintenance로 추정하지 않는다.

로컬 수령/검증 예시(실제 수령물은 이미 있으므로 반복 다운로드 불필요):

```bash
python3 scripts/deployment/web_release.py verify \
  --handoff backups/web-handoff/artifact-13849320316 \
  --receipt docs/engineering/operations/records/web-handoff-2.1.0.json
```

운영 명령은 검증된 소스를 별도 clean checkout으로 확보한 뒤 실행한다. `$release_root`는 manifest source와 같은 commit의 checkout, `$handoff`는 검증 원3파일, `$manifest`는 CI에서 생성된 불변 release.json이다. 운영 루트는 기존 `/home/ubuntu/lostparty-backend`, 상태는 `/var/lib/lostparty-deploy`, 웹은 `/var/lib/lostparty-web`을 유지한다. 아래 명령은 실행 예시이며 현재 운영에서 수행하지 않았다.

```bash
sudo python3 "$release_root/scripts/deployment/maintenance.py" preflight \
  --release-root "$release_root" --manifest "$manifest" --handoff "$handoff"
sudo python3 "$release_root/scripts/deployment/backup.py" capture --directory "$backup_dir"
# 생성된 archive를 기존 PC 폴더의 새 날짜 폴더로 전송하고 PC에서 SHA256 계산.
sudo python3 "$release_root/scripts/deployment/backup.py" copy-confirm \
  --receipt "$backup_dir/receipt.json" --pc-sha256 "$pc_sha256"
sudo python3 "$release_root/scripts/deployment/maintenance.py" apply \
  --release-root "$release_root" --manifest "$manifest" --handoff "$handoff" \
  --backup-receipt "$backup_dir/receipt.json" --probe-ip "$test_ip"
```

backup receipt는 1시간 이내이고 현재 source/image/DB·환경/키와 일치해야 한다. 경과하면 기존 사본을 지우지 않고 새 사본을 확보한다. 전송 위치는 ignored private 기록만 사용하며 공개 문서/Issue에 개인 경로를 복제하지 않는다.

apply는 Caddy 설정을 사전 validate한 뒤 marker로 공개503을 확인하고 API/worker를 중지한다. 앱 역할로0036을 적용하고 후보API 시작·DB/키보존·두전체계약·내부edge health/index를 비교한다. 안정된 호스트 Caddyfile 경로와 기존 `.env.lightsail`을 새 azp 값으로 맞추고 동결 Compose/configrevision 및 배포제어기 코드를 정렬한다. 웹 parent read-only mount는 유지한다. 후보 확인용 `127.0.0.1:8081`은 Caddy 컨테이너 loopback에만 bind하며 호스트 포트를 추가 공개하지 않는다.

운영 브라우저/새 APK 인수는 승인된 시험 네트워크의 정확한 공인 IP 한 개를 test_ip로 받아 Caddy의 실제 remote_ip로만 제한 허용한다. CIDR/클라이언트 전달 헤더/임의 비밀헤더로 우회하지 않는다. PC와 휴대폰은 같은 승인 시험 네트워크를 사용하고 다른 접속자는 계속503이다. 이 값은 실제 적용 직전 확인하며 private 환경/동결 구성에만 기록한다. 공개503에 대한 웹 헤더 우회 키를 만들지 않는다. `joint-acceptance.json`에는 backend_source, web_sha256, backend_checks/native_checks/joint_publication_authorized의 실제 확인 결과를 기록한다. 추측이나 CI 성공으로 true를 채우지 않는다.

```bash
sudo python3 "$release_root/scripts/deployment/maintenance.py" open \
  --release-root "$release_root" --manifest "$manifest" --handoff "$handoff" \
  --joint-acceptance "$acceptance_record"
```

실제 전환 결과는 private journal에 남고 공개 기록에는 상태/버전/해시·보존/검증 결과만 옮긴다. 환경/키/백업 archive는 GitHub artifact나 Issue로 게시하지 않는다.

### 실패 후 관리 기준

`/var/lib/lostparty-deploy/maintenance-2.1.0/result.json`의 phase와 실제 DB revision을 먼저 확인한다. 입력/사전검증 실패는 서비스 교체를 시작하지 않는다. migration 시작 전 실패는 기존 Caddyfile·API 구성을 복원하며, migration 시작 뒤 실패는 marker를 유지하고 자동 구이미지 복귀를 하지 않는다. 기록의 phase만 보고 DB를0035로 추정하지 않는다.

0036 적용 후 복구가 필요하면 현재/직전 이미지와 backup을 보존하고 결함을 로컬 재현·수정한 새 버전/불변 이미지를 확보한다. 기존 태그/이미지를 덮어쓰지 않는다. 새0036 호환 이미지와 현재 웹/환경을 고정한 복구 Compose를 별도 파일로 준비하고 보호자료·DB0036·전체계약·Caddy 점검을 확인한 뒤 **API만** 교체한다. 정상화 후 current.json/source/image/compose와 실제 실행을 정렬하고 담당별 인수를 다시 확인한다. 이 경로에서는 maintenance apply를0035인 것처럼 재실행하거나 SQL downgrade/자료삭제를 하지 않는다. 백업 복원이 필요한 상황은 데이터 영향과 복원 시점을 명시해 별도 결정한다.

정상 Backend에 웹만 문제가 있으면 다음 명령으로 웹만 복귀하고 marker를 유지한다. 첫 공개는 current가 없어져 API-only로 돌아간다. 기존 APK를 원격 회수할 수 있다고 가정하지 않는다.

```bash
sudo python3 "$release_root/scripts/deployment/web_release.py" rollback --root /var/lib/lostparty-web
```

반영 후 변경된 환경/동결구성·웹배포 식별을 보존할 때는 backup capture를 새 폴더에 실행한다(DB0036 지원). 이미 보관한 직전 사본을 덮어쓰지 않으며 실제PC전송/해시와 복원검증은 구분해 기록한다.

## 구 APK·신 Backend 호환 경계

고정 후보의 결과는 [준비 검증 기록](records/release-2.1.0-preparation.json)에 누적한다. 로컬 전체1968고유사례와도구80검사·두전체계약·격리전환검증을통과했다. 최초기대값실패/정정·분할중복제외 근거는검증기록에남겼으며 고정후보CI/full은별도필수다. 아래 표는 코드/계약으로 정한 검증 범위다. 실제 구 APK 기기에서 신서버를 전수 인수했다고 표시하지 않는다.

| 요청/조합 | 유지/제한 기준 |
|---|---|
| 새 APK·웹 + 구0035 | 이번 지원 조합에서 제외. 새5경로/참가profile를 제공하지 않음 |
| 새 APK·웹 + 신0036 | 이번 자동/운영 인수 대상. CI/파일검증과 실제 Google/기기를 구분 |
| 구 APK의 기존 로그인·개인 API | 기존 계약/2개azp/Webaudience 보존. 새 서비스키·세션정책 없음 |
| 구프로필 모집 조회·원단건 context/command 쌍 | 원경로/DTO/쿼리 opt-in 보존. capability가 없는 대상과 현재권한/그룹정책·context조건에서만 정상범위 |
| capability 활성 대상/세대의 영향조회·명령 | participation_profile 없는 요청은 CLIENT_UPGRADE_REQUIRED. 목록의 영향항목 제한과 전체실패를 혼동하지 않음 |
| group_policy_version 없는 신규쓰기 | 기존0035 이후 정책대로 CLIENT_UPGRADE_REQUIRED, 구 APK 전체쓰기 호환을 위해 완화하지 않음 |
| context/profile 불일치 | CONTEXT_INVALID, 최신 context를 명시적으로 다시 확인 |
| 원성공 ACK 재전송 | 동일actor/operation/key/body·현재권한/보관조건 내 원결과 복구. pending·새key·만료context는 별도이며 성공을 합성하지 않음 |

Native 전체16 코드 근거에 따르면 구 APK 상세/생성은 업그레이드 안내가 있지만 주간 화면은 일반오류로 표시될 수 있다. 따라서 모든 화면에서 명확한 업데이트 안내를 보장하지 않으며 Native가 확인한2.1.0 배포 안내와 연결한다.
