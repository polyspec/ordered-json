<!-- doc-id: development -->
<!-- source-sha256: 980416c3b2b28b9218c6d9b4560b06160db0067206e63e6204bab1764f9653a2 -->
# 개발 절차

[English](AGENTS.md)

<a id="workflow"></a>
## 필수 작업 절차

수정 전에 [문서 관리](docs/documentation-plan.ko.md), 관련 [명세](docs/spec/json-contract.ko.md), [기능 상태](docs/features.ko.md)를 읽습니다. 동작을 변경하기 전에 명세를 갱신합니다. 완료하지 않은 기능은 기능 기록에, 진행 중인 작업은 [실행 체크리스트](docs/plans/execution-checklist.ko.md)에 표시합니다.

올바른 코드와 사실에 맞는 이력을 유지합니다. 실제 원인을 직접 설명합니다. 코드 변경에 관련 문서, 기능 상태, 변경 기록을 포함합니다. 개인 선호, 대화 맥락, 인증 정보, 백업 위치는 Git 외부에서 관리합니다.

관측된 결함은 추적되는 RED 테스트로 재현합니다. 아직 관측되지 않았지만 발생 가능한 결함은 그 문제를 드러낼 입력과 요구 결과를 가진 결정적인 RED 사례를 먼저 작성합니다. 구현 전에 의도한 실패를 확인하고 원인을 고친 뒤 같은 사례와 관련 패키지 사용 테스트를 GREEN으로 검증합니다. 사례가 문제를 드러내지 못하면 기준을 낮추지 말고 조사합니다.

영어가 정본입니다. 같은 정보로 한국어 문서를 함께 갱신합니다. 번역 전체를 비교한 후에만 `source-sha256`을 갱신합니다. 문서, 주석, 커밋 메시지, 번역에는 주체와 동작을 명시한 직접적인 기술 표현을 사용합니다.

메시지 전송, 산출물 게시, 접근 제어 변경, 이력 재작성 권한을 임의로 해석하지 않습니다. 해당 작업에 이미 제공된 권한을 따릅니다.

기본적으로 `main`에서 작업합니다. 에이전트가 작업하거나 상황상 브랜치나 워크트리가 필요하면 브랜치는 `{type}/{shortname}-{체크리스트 ID}`, 워크트리는 `{프로젝트}-{shortname}-{체크리스트 ID}`로 만들고, `main`에 합친 즉시 둘 다 제거합니다. 브랜치를 `main`에 통합한 뒤 커밋이나 동등한 변경이 반영됐고 워크트리가 깨끗한지 확인합니다. 삭제할 워크트리에만 있는 `.gitignore` 제외 파일 중 계속 필요한 파일은 먼저 다른 곳에 보존합니다. 그런 다음 워크트리와 로컬 브랜치를 제거합니다. 미통합 작업이나 진행 중인 작업은 보존합니다.

`main`에 통합할 수 없는 테스트 전용 브랜치의 의미 있는 커밋은 관련 기능을 커밋하기 전에 체리픽하고, 나머지 테스트 전용 변경은 폐기한 뒤 워크트리와 브랜치를 제거합니다. 제거할 수 없다면 먼저 소유 체크리스트에 번호가 붙은 하위 항목을 추가하고 원인과 정확한 제거 조건을 기록합니다.

<a id="feature-state"></a>
## 기능 상태

[기능 상태](docs/features.ko.md)는 이 저장소의 tracker입니다. `scripts/full_run.py`는 각 기능 행의 구현 칸을 읽습니다. 상태는 그 칸에만 둡니다. 기능 표의 절은 표만 담고, `scripts/docs_check.py`는 `docs/features.md`와 그 번역의 다른 곳에 code span이나 표 칸으로 적힌 상태와 그 절의 다른 줄에서 file, 줄, 열을 적으며 실패합니다. tracker를 읽는 모든 도구(`scripts/docs_check.py`, `scripts/full_run.py`, `scripts/push_gate.py`)는 하나의 parser로 행을 읽고, 기능 표가 없는 tracker, 기능 행이 없는 표, ID가 기능 ID `F-...`가 아닌 행을 거부하므로, 행을 내지 않는 tracker는 어떤 검사도 통과하지 못합니다. 이 절이 상태를 정의합니다.

`implemented`는 해당 동작이 구현됐다는 뜻입니다. `partial`은 구현이 진행 중인 기능을 표시합니다. 이것이 이 저장소의 활성 작업이며, `partial`인 행이 있는 동안 `make check`는 실행을 거부합니다. `planned`는 구현을 시작하지 않은 기능을 표시합니다. `shared-suite`는 공통 JSON 테스트, `package-tests`는 구현 자체의 테스트, `docs-tests`는 문서 검사기 테스트, `benchmark`는 저장소 벤치마크 프로토콜과 커밋된 결과를 뜻합니다. 각 상태는 자신을 뒷받침하는 기록을 가리킵니다. 공통 스위트, 패키지 테스트, 검사기 테스트는 commit을 검증하는 실행의 [기록](docs/operations/validation.ko.md#records)을, 벤치마크는 [벤치마크 결과](benchmarks/results.json)를 가리킵니다. 검증 기록에는 실제 버전, 사례 수, 실행 시각, 소스 해시가 있습니다. 벤치마크 결과는 깨끗한 체크아웃에서 workload가 선언한 프로토콜과 입력으로 측정했을 때에만 근거가 됩니다. `source-only`는 확인된 배포 방식이며 레지스트리 게시는 검증되지 않았습니다. 게시 확인 결과는 [distribution.json](docs/distribution.json)에서 별도로 관리합니다.

<a id="checklist"></a>
## 실행 체크리스트

[실행 체크리스트](docs/plans/execution-checklist.ko.md)는 검사, 도구, CI처럼 제품 기능이 아닌 이 저장소의 작업을 추적합니다. 각 작업은 ID `T<wave>.<task>`, 작업, 산출물, 그것을 검증하는 소유 명령, 마지막 칸의 상태를 가진 행입니다. 상태는 `[ ]` 대기, `[~]` 진행 중, `[o]` 완료, `[!] cause: <cause>; retry: <condition>` 우회입니다. `scripts/docs_check.py`는 다른 상태를 받지 않고, 작업 ID가 없는 행, 반복된 ID, 행이 없는 체크리스트, ID나 상태가 다른 번역을 거부합니다. 작업은 진행하는 동안 `[~]`이고 그것을 끝내는 commit에서 `[o]`가 됩니다. `make check`의 guard, pre-push hook, push gate는 `partial` 기능과 마찬가지로 작업이 `[~]`이면 거부하고, 체크리스트를 읽을 수 없으면 거부합니다. 새 문제는 새 작업이 됩니다. `[o]`인 작업과 관련된 문제는 다음 파생 ID(`T1.1-1`)를 가진 하위 항목이 됩니다.

<a id="verification"></a>
## 필수 검사

각 구현 패키지는 자체 소스와 문서 목록을 관리합니다. 명령은 저장소 루트에서 실행합니다.

개발 중에는 unit test만 실행합니다. 변경을 진행하는 동안 RED 사례와 같은 사례의 GREEN을 검증기 unit test(`python3 scripts/test.py --unit`)로 실행합니다. `make pie-check`, `make check`, `make owner-check`, 어댑터 suite, 추가 사례 실행은 end-to-end 검사이며 hosted CI가 push 뒤에 실행합니다([hosted CI](docs/operations/validation.ko.md#ci)). 어떤 규칙도 commit이나 push 전에 로컬 실행을 요구하지 않습니다. pre-push hook은 tracker와 체크리스트만 읽는 빠른 gate로 남습니다. 수정할 때마다 더 넓은 검사를 다시 실행하지 않습니다. [scripts/owner-checks.json](scripts/owner-checks.json)은 모든 추적 경로를 그것을 소유한 검증기 unit test module, 구현, 검사에 대응시킵니다. `make owner-check`는 커밋되지 않은 변경, `PATHS`, 또는 `BASE` 이후 바뀐 경로의 소유자를 각각 끝까지 실행하고, pre-commit hook `.githooks/pre-commit`은 추적 경로가 어떤 규칙에도 맞지 않거나, glob이 어떤 경로에도 맞지 않거나, 소유자가 존재하지 않으면 commit을 거부합니다. 새 파일은 같은 commit에서 대응시킵니다.

~~~sh
python3 scripts/verify.py --only js
python3 scripts/test.py --unit test_docs_check.DocumentationChecks.test_missing_anchor_fails
git diff --check
~~~

`scripts/verify.py --only`는 선택한 구현을 빌드하고 그 구현의 케이스·심볼 목록, 선언된 패키지 테스트, 공통 사례를 실행하며 기록을 쓰지 않습니다. `scripts/test.py --unit`은 지정한 검증기 unit test를 실행하며 기록을 쓰지 않습니다. test가 없는 module처럼 test를 하나도 고르지 않는 이름은 어떤 test도 실행하기 전에 `selected 0 tests`와 그 이름을 출력하며 실패합니다.

`make check`는 hosted CI가 모든 pull request와 merge queue의 모든 merge group에서 실행하는 전체 suite입니다. 로컬 실행은 선택이며, 활성 항목이 모두 끝난 뒤 tree마다 많아야 한 번 합니다. 추가 사례를 포함하면 그 실행은 다음과 같습니다.

~~~sh
make check JSON_TEST_SUITE=.cache/JSONTestSuite
~~~

`make check`는 검증보다 먼저 guard `scripts/full_run.py`를 시작합니다. 이 저장소의 활성 작업은 [기능 상태](docs/features.ko.md)에서 구현 상태가 `partial`인 기능 행과 [실행 체크리스트](docs/plans/execution-checklist.ko.md)에서 상태가 `[~]`인 작업입니다. guard는 판단을 이유와 함께 출력하고, 그런 행이 있으면 각 ID를 기능이나 작업과 함께 나열하며 거부하고, `make hooks-check`가 보고하듯 pre-push hook이 설치되지 않았으면 거부하고, 추적 파일의 변경이 커밋되지 않았거나 `.gitignore`가 무시하지 않는 파일이 추적되지 않으면 각각을 밝히며 거부합니다. 전체 실행은 커밋된 tree를 검증하고, build는 추적되지 않은 파일도 읽기 때문입니다. `var/full-run.json`이 현재 tree(`git rev-parse HEAD^{tree}`)의 전체 실행을 기록하고 있으면 그 실행을 commit, 시작 시각, 결과와 함께 밝히며 거부하고, `incomplete` record의 process가 아직 실행 중이면 거부합니다. guard는 첫 검사부터 끝까지 `var/full-run.lock`을 배타적으로 잡고, 다른 guard가 이를 잡고 있으면 그 holder를 밝히며 거부하므로, 동시에 시작한 두 guard가 모두 실행하지 않습니다. 검증 명령을 시간 제한 없이 끝까지 실행하고 그 앞뒤에 record를 쓰므로, 멈춘 실행은 `incomplete`로 기록되어 남습니다. `make rerun-failed`는 현재 tree의 전체 실행이 실패했거나 끝나지 않았을 때만 검증을 다시 실행하고, 그 밖에는 거부됩니다. 검증은 target 하나이므로 전체가 다시 실행됩니다. `var/`는 Git이 무시하므로 checkout과 worktree마다 자기 record를 가집니다. hosted CI는 전체 suite를 실행합니다. `.github/workflows/ci.yml`은 모든 pull request, merge queue의 모든 merge group, 모든 수동 실행(`workflow_dispatch`)에서 모든 실패를 지나 `make pie-check`와 `make check`를 실행하고, 각 job의 보고서를 실행의 기록과 함께 upload합니다([hosted CI](docs/operations/validation.ko.md#ci)). commit의 근거는 그 실행이며, merge group의 실행은 `main`이 받는 commit의 근거입니다. workflow의 step은 script나 도구를 직접 실행하지 않고 make target을 실행합니다. 새 checkout에는 record가 없으므로, 그곳에서 `make check`는 `partial` 기능이 없고 tree가 깨끗하면 실행됩니다.

push는 `partial` 기능과 `[~]` 작업이 없을 때만 합니다. pre-push hook `.githooks/pre-push`는 `scripts/push_gate.py hook`을 실행합니다. 이 명령은 push되는 commit이나 working tree의 `docs/features.md`에 `partial` 행이 있거나 `docs/plans/execution-checklist.md`에 `[~]` 작업이 있으면 각 ref, commit, ID, 기능이나 작업을 밝히며 push를 거부하고, 두 file 중 하나를 읽을 수 없으면 거부합니다. Makefile을 읽는 것은 설정을 쓰지 않습니다. `make hooks`는 값이 다를 때만 `core.hooksPath`를 `.githooks`로 설정하고 hook을 검사하며, `make hooks-check`는 `core.hooksPath`가 `.githooks`가 아니거나 `.githooks/pre-push`나 `.githooks/pre-commit`이 실행 가능하지 않으면 실패합니다. hook이 없는 checkout에서 한 push는 hook을 실행하지 않으므로, `.github/workflows/push-gate.yml`의 job `push-gate`가 모든 branch에 push된 commit과 모든 pull request의 head commit에 `scripts/push_gate.py commit`을 실행하는 `make push-gate COMMIT=<commit>`을 실행합니다. 이 job은 기능이 `partial`이거나 작업이 `[~]`이면 실패하고, `.githooks/pre-push`나 `.githooks/pre-commit`이 mode 100755로 추적되지 않으면 실패합니다. 같은 job은 이어서 `make docs-check`를 실행하고, gate가 실패해도 실행합니다. 그래서 문서, 기능 tracker, 체크리스트가 자체 검사에 실패하는 commit은 `main`이 요구하는 check에 실패합니다. 이 job은 local checkout의 설정을 검사할 수 없습니다.

모든 변경은 owner의 변경이든 agent의 변경이든 pull request와 merge queue를 거쳐 `main`에 들어갑니다. 이 저장소의 어떤 명령도 `main`을 push하지 않습니다. branch는 GitHub의 표준 명령이나 GitHub UI로 공개합니다.

~~~sh
git push origin HEAD:refs/heads/<branch>
gh pr create --base main --head <branch> --fill
gh pr merge <branch> --auto --rebase
~~~

`.github/ruleset.json`에 선언된 GitHub ruleset `main`은 pull request(승인 없음), merge method `REBASE`인 merge queue, linear history, 정확히 GitHub Actions의 check `push-gate`와 `ci-passed`(`.github/workflows/ci.yml`의 마지막 job으로, 그 workflow의 다른 모든 job이 통과했을 때만 통과)를 요구하고, `main`의 force-push와 삭제를 거부하며, bypass actor가 없습니다. 그래서 GitHub는 관리자의 push도 포함해 `main`으로의 직접 push를 거부합니다. merge queue는 queue에 들어간 pull request를 `main` 위에 rebase해 merge group을 만들고, 그 commit에서 필수 check를 실행해 통과하면 `main`을 그 commit으로 옮깁니다. check가 실패하면 pull request를 queue에서 뺍니다. branch push에서 pre-push hook이 실행되고, job `push-gate`는 pull request와 merge group에서 `[~]` 작업을 거부합니다. rebase는 merge된 commit에 새 hash를 주므로, `git pull --rebase`가 queue가 merge한 local commit을 버립니다. `make github-ruleset`은 ruleset과 선언된 저장소 설정을 만들거나 갱신하고, `make github-ruleset-check`는 둘이 선언과 다르면 실패합니다([main 공개](docs/operations/validation.ko.md#publish)).

문서만 검토할 때는 `make docs-check`를 실행합니다. 이 검사는 검증 기록을 소스와 비교하지 않습니다. commit의 근거는 커밋된 파일이 아니라 그것을 검증하는 실행입니다. `make pie-check`는 PIE 기록 `var/records/pie-verification.json`을, `make check`는 통합 기록 `var/records/verification.json`을 쓰며 Git은 이를 무시하고, `make check` 마지막의 문서 검사는 두 기록을 현재 소스와 대조합니다([기록](docs/operations/validation.ko.md#records)). 기록은 모든 추적 파일을 해시하므로 커밋된 기록은 commit마다 오래된 기록이 됩니다. 어떤 기록도 커밋하지 않으며, 어떤 guard도 기록이 없다는 이유로 거부하지 않습니다. 검사를 통과시키기 위해 검증 결과나 소스 해시를 직접 수정하지 않습니다.

[구현 등록 정보](implementations.json)는 패키지 경로·빌드·어댑터·패키지 테스트·런타임 명령을 정의합니다. `make check`는 선언된 패키지 테스트 명령을 모두 실행합니다. 공통 사례는 JSON 계약만 검사하므로 한 패키지에만 있는 API에는 닿지 않으며, 그런 API는 해당 패키지의 테스트가 필요합니다. [package-tests.json](package-tests.json)은 모든 구현이 실행하는 케이스, 사유를 적은 면제, 패키지 고유 케이스, 그리고 공개 심볼마다 그것을 검증하는 케이스를 정의합니다. `make check`는 이 표준과 각 패키지가 보고한 케이스·심볼을 대조해 누락된 케이스, 선언되지 않은 케이스, 검증되지 않는 심볼, 더 이상 내보내지 않는 심볼 선언이 있으면 실패합니다. 각 케이스 목록은 출력의 기계 형식을 선언합니다(`test_cases`의 `format`). 패키지 자신의 케이스 ID 목록은 `lines`, `cargo test -- --list --format terse`는 `cargo-terse`, `go test -list .* -json`의 event는 `go-test-json`입니다. 형식이 정의하지 않은 줄은 목록을 실패시키고, 0이 아닌 status로 끝난 목록은 standard error와 함께 실패하며, 성공한 목록의 standard error는 도구 알림으로 출력합니다. 공통 JSON 비교 알고리즘을 변경하지 않고 해당 등록 정보와 패키지 디렉터리로 새 언어를 추가합니다. 계약 변경은 같은 저장소 리비전에서 검증기와 관련 패키지를 갱신합니다. [저장소 계약](docs/spec/repositories.ko.md)을 참조합니다.

모든 언어 어댑터는 [official.json](examples/official.json)과 [scripts/verify.py](scripts/verify.py)를 사용합니다. 공통 사례는 해당 파일이나 `fixtures/`에 추가합니다. 언어별로 다른 예제나 기대 결과를 만들지 않습니다.

Rust 코드는 `rust/`에서 `cargo clippy --all-targets -- -D warnings`를, Go 코드는 `go/`에서 `go vet ./...`을 통과합니다. `make check`는 검증 뒤에 둘을 각각의 target으로 실행하므로(`scripts/lint.py`, `make clippy`와 `make go-vet`으로도 실행) hosted CI가 모든 pull request와 모든 merge group에서 이를 실행합니다. 네이티브 코드를 변경하면 PHP 확장을 다시 빌드합니다. 이전 바이너리나 이전 결과를 변경된 코드의 검증 근거로 사용하지 않습니다.

<a id="release"></a>
## 릴리스

모든 변경은 필수 check와 함께 merge queue로 `main`에 도달하므로, `main`의 모든 commit은 전체 suite를 통과했습니다. 릴리스는 `main`의 commit에 붙인 tag이고, tag를 만들고 옮기고 push하는 것은 메인테이너뿐입니다. tag는 pull request로 올리지 않습니다.

1. 버전 올림 pull request `Release X.Y.Z`는 commit에 체크리스트 작업을 적고, 저장소의 모든 manifest(`package.json`, `js/package.json`, `composer.json`, `php/composer.json`, `php-extension/composer.json`, `rust/Cargo.toml`, `rust/Cargo.lock`의 package 항목)의 버전을 X.Y.Z로 정하고, `make install-fixtures`로 그 버전의 설치 fixture를 쓰며, 모든 changelog의 `## Unreleased`를 `## X.Y.Z`로 바꾸고 그 위에 비어 있는 새 `## Unreleased`를 둡니다.
2. 메인테이너는 merge된 `main`의 commit에 `vX.Y.Z` tag를, `go/`의 Go 모듈에는 `go/vX.Y.Z` tag를 붙이고 tag를 push합니다.
3. tag push는 `.github/workflows/release.yml`을 실행합니다. 이 workflow는 tag된 commit이 `main`에 있고 check `push-gate`와 `ci-passed`를 통과했는지, 모든 manifest에 tag의 버전이 있고 `CHANGELOG.md`에 section `## X.Y.Z`가 있는지 확인하고, 패키지 archive를 만들어 GitHub Release를 생성합니다([tag 릴리스](docs/operations/distribution.ko.md#tag-release)).

<a id="idempotency"></a>
## 멱등성

같은 tree는 언제 어느 기계에서든 같은 결과를 냅니다. 한 polyspec 저장소에서 찾은 결함은 하나의 부류입니다. 모든 저장소에서 고치고 그 규칙을 여기에 적습니다. 각 규칙은 이 저장소가 그것을 지키는 방법을 밝힙니다.

- 검사는 결과가 시간에 따라 달라지는 registry 질의를 하지 않습니다. 최신 조회나 `@latest`, 버전 범위의 해석, 오래된 package나 새 release에 대한 질의가 없습니다. lock 파일이 정확한 버전과 integrity hash로 고정한 package를 내려받는 것은 그런 질의가 아니라 설치이며, `npm ci`와 `composer install`처럼 허용됩니다. `scripts/tests/test_release.py`의 릴리스 asset 설치 테스트는 `scripts/tests/install`의 커밋된 lock으로 offline 설정 없이 `npm ci`와 `composer install`을 실행합니다. 그 lock을 해석하는 `make install-fixtures`는 검사가 아닙니다.
- 어떤 명령도 도구를 필요할 때 설치하지 않으며, 모든 도구는 추적되는 버전으로 실행합니다. 추적 파일이 Node.js, Rust, Go, Python, PHP, npm을 고정합니다. 로컬과 CI에서 같은 patch release를 쓸 수 없는 interpreter는 minor release로 고정하므로, Python은 `.python-version`이 3.14를, PHP는 `.php-version`이 8.5를 적고, 검사는 major.minor를 비교하며, 각 기록은 실행 중인 patch release를 적습니다. setup-python과 setup-php는 minor의 최신 patch release를 설치하기 때문입니다. 그리고 `scripts/toolchains.py`는 어떤 작업보다 먼저 각 도구를 고정값과 비교하며, `GOTOOLCHAIN=local`과 `RUSTUP_AUTO_INSTALL=0`은 go와 rustup이 다른 toolchain을 가져오지 못하게 하고, cargo는 `--locked`로 실행하며, `make tools`가 내려받는 유일한 단계로서 Rust toolchain, tarball hash와 대조한 npm, `rust/Cargo.lock`의 crate, `external-inputs.json`과 대조한 PIE PHAR와 추가 사례를 설치하고, 그 설치 테스트를 뺀 다른 모든 명령은 cargo, go, npm, Composer를 offline으로 실행하며(Makefile이 export하고 `scripts/toolchains.py`가 설정하는 `CARGO_NET_OFFLINE`, `GOPROXY=off`, `npm_config_offline`, `COMPOSER_DISABLE_NETWORK`), 내려받지 않은 입력은 `run make tools`로 실패하고(모든 진입점은 첫 단계 전에 `cargo fetch --locked --offline`을 실행해 lock file을 밝히고, `make pie-check`와 `make check`는 없는 PIE PHAR나 추가 사례를 밝힙니다), CI는 image, action, Python을 고정하고, `make pie-check`와 `make check`는 PIE PHAR와 추가 사례를 먼저 `external-inputs.json`과 비교합니다.
- test는 자기가 만든 출력만 읽고 추적되지 않은 상태에 의존하지 않습니다. 기록, 문서 검사, 공통 사례, build 사본은 Git이 추적하는 파일을 읽고, guard는 추적되지 않은 파일을 거부하며, 각 실행은 자기 `CARGO_TARGET_DIR`를 가진 자기 실행 디렉터리에서 빌드하고, test는 자기 파일을 자기 임시 디렉터리에만 씁니다.
- 공유 출력은 원자적으로 게시합니다. `var/`의 파일에 끝까지 쓴 뒤 그 경로 위로 이름을 바꿉니다(`write_record`).
- 검사는 실패를 모으고 첫 실패에서 멈추지 않습니다. 모든 언어, 단계, 사례가 끝까지 실행되고, 실행은 status 1로 끝나기 전에 모든 실패를 나열합니다.
- 검사는 사용자 로캘의 메시지를 판정하지 않습니다. 출력 텍스트를 비교하는 명령은 `LC_ALL=C`로 실행하고, `scripts/registry.py`가 `git rev-parse --is-inside-work-tree`를 그렇게 실행하므로 다른 언어로 보고하는 git도 work tree가 아님으로 읽힙니다.
- 실패는 기대값, 실제값, 도구 자신의 오류를 출력합니다. 일치한 줄, 다른 파일, 두 버전이나 hash, 종료 상태와 standard error입니다.
- 빈 선택은 실패합니다. test를 고르지 않는 unit test 이름, 기능 행이 없는 tracker, test를 찾지 못한 실행은 이름을 밝히며 실패합니다.
- 자식 process는 명령이 끝나거나 호출자가 멈출 때 손자를 포함한 process group 단위로 회수하고(`end_group`), 임시 디렉터리는 `finally`나 context manager에서 제거합니다.
- 어떤 검사도 사람이 읽는 도구 출력을 단언하지 않습니다. 케이스 목록은 기계 형식을 선언하고, standard error의 도구 알림은 출력하되 판단하지 않으며, `make`를 실행하는 test는 호출자의 make 변수를 제거합니다.
- 바뀐 모든 파일은 소유한 test에 대응됩니다. `scripts/owner-checks.json`이 모든 추적 경로를 소유하고, `make owner-check`가 변경의 소유자를 실행하며, pre-commit hook은 대응되지 않은 경로를 거부합니다.
- 공유 디렉터리, port, fixture는 lease나 실행별 디렉터리를 거칩니다. 각 실행, test, build는 자기 임시 디렉터리를 사용하고, guard는 `var/full-run.lock`을 잡아 한 checkout의 전체 실행이 한 번에 하나씩 실행되게 합니다.

<a id="completion"></a>
## 완료

코드와 테스트를 읽고 문서의 정확성을 확인합니다. 자동 링크, 개정본, 상태 검사는 문장 내용의 정확성을 증명하지 않습니다. 테스트와 실제 게시를 별도로 확인하고 관측한 근거로만 [배포 상태](docs/operations/distribution.ko.md)를 갱신합니다.

Git 메시지는 사실대로 간단하게 작성합니다. 관련 없는 변경은 가능하면 분리합니다.
