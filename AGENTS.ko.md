<!-- doc-id: development -->
<!-- source-sha256: e80ceff7a532cab2c4b779adf7c578bdfe2d72ebad7c896173cf46165ead88af -->
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

[기능 상태](docs/features.ko.md)는 이 저장소의 기능 기록입니다. `scripts/check-evidence.mts`는 각 기능 행의 구현 칸을 읽고, `make documents-check`는 그 값이 세 상태 중 하나이도록 요구합니다. 상태는 그 칸에만 둡니다. 기능 표의 절은 표만 담고, `scripts/check-evidence.mts`는 `docs/features.md`와 그 번역의 다른 곳에 code span이나 표 칸으로 적힌 상태와 그 절의 다른 줄에서 file, 줄, 열을 적으며 실패합니다. `scripts/check-evidence.mts`는 mdast로 행을 읽고, 기능 표가 없는 기록, 기능 행이 없는 표, ID가 기능 ID `F-...`가 아닌 행을 거부하므로, 행을 내지 않는 기록은 어떤 검사도 통과하지 못합니다. 이 절이 상태를 정의합니다.

`implemented`는 해당 동작이 구현됐다는 뜻입니다. `partial`은 구현이 진행 중인 기능을 표시합니다. `planned`는 구현을 시작하지 않은 기능을 표시합니다. `shared-suite`는 공통 JSON 테스트, `package-tests`는 구현 자체의 테스트, `docs-tests`는 문서 검사기 테스트, `benchmark`는 저장소 벤치마크 프로토콜과 커밋된 결과를 뜻합니다. 각 상태는 자신을 뒷받침하는 기록을 가리킵니다. 공통 스위트, 패키지 테스트, 검사기 테스트는 commit을 검증하는 실행의 [기록](docs/operations/validation.ko.md#records)을, 벤치마크는 [벤치마크 결과](benchmarks/results.json)를 가리킵니다. 검증 기록에는 실제 버전, 사례 수, 실행 시각, 소스 해시가 있습니다. 벤치마크 결과는 깨끗한 체크아웃에서 workload가 선언한 프로토콜과 입력으로 측정했을 때에만 근거가 됩니다. `source-only`는 확인된 배포 방식이며 레지스트리 게시는 검증되지 않았습니다. `published`로 표시한 기능 행은 릴리스 tag와 asset을 적으며, 그 형식은 `make evidence-check`가 검사합니다.

<a id="checklist"></a>
## 실행 체크리스트

[실행 체크리스트](docs/plans/execution-checklist.ko.md)는 검사, 도구, CI처럼 제품 기능이 아닌 이 저장소의 작업을 추적합니다. 각 작업은 ID `T<wave>.<task>`, 작업, 산출물, 그것을 검증하는 소유 명령, 마지막 칸의 상태를 가진 행입니다. 상태는 `[ ]` 대기, `[~]` 진행 중, `[o]` 완료, `[!] cause: <cause>; retry: <condition>` 우회입니다. `make documents-check`(`@polyspec/kit`의 check-documents)는 다른 상태를 받지 않고, 작업 ID가 없는 행, 반복된 ID, 행이 없는 체크리스트, 제목이나 작업 행이 아닌 줄, 작업 행의 마지막 칸 밖의 상태 표지, ID나 상태가 다른 번역을 거부합니다. 작업은 진행하는 동안 `[~]`이고 그것을 끝내는 commit에서 `[o]`가 됩니다. `make check`의 guard, pre-push hook, push gate(`@polyspec/kit`의 full-run과 push-gate)는 작업이 `[~]`이면 거부하고, 체크리스트를 읽을 수 없으면 거부합니다. `config/checklist.json`이 체크리스트와 Git hook을 선언합니다. 새 문제는 새 작업이 됩니다. `[o]`인 작업과 관련된 문제는 다음 파생 ID(`T1.1-1`)를 가진 하위 항목이 됩니다.

<a id="verification"></a>
## 필수 검사

각 구현 패키지는 자체 소스와 문서를 관리합니다. 명령은 저장소 루트에서 실행합니다.

개발 중에는 unit test만 실행합니다. 변경을 진행하는 동안 RED 사례와 같은 사례의 GREEN을 바뀐 것의 unit test, 곧 패키지의 native test나 도구 test(`make test-scripts`)로 실행합니다. `make pie-check`, `make check`, `make owner-check`, 어댑터 suite, 추가 사례 실행은 end-to-end 검사이며 hosted CI가 push 뒤에 실행합니다([hosted CI](docs/operations/validation.ko.md#ci)). 어떤 규칙도 commit이나 push 전에 로컬 실행을 요구하지 않습니다. pre-push hook은 체크리스트만 읽는 빠른 gate로 남습니다. 수정할 때마다 더 넓은 검사를 다시 실행하지 않습니다. [config/owner-checks.json](config/owner-checks.json)은 모든 추적 경로를 그것을 소유한 make target에 대응시킵니다(`test-scripts`는 도구 test를, `verify-<language>`는 구현 하나를 검증합니다). `make owner-check`(`@polyspec/kit`의 owner-check)는 커밋되지 않은 변경, `PATHS`, 또는 `BASE` 이후 바뀐 경로의 소유자를 각각 끝까지 실행하고, pre-commit hook `.githooks/pre-commit`은 `make owner-validate`를 실행하여 추적 경로가 어떤 규칙에도 맞지 않거나, glob이 어떤 경로에도 맞지 않거나, 소유자가 존재하지 않으면 commit을 거부합니다. 새 파일은 같은 commit에서 대응시킵니다.

~~~sh
make verify-js
make test-scripts TESTS=tests/scripts/evidence.test.mts
git diff --check
~~~

`make verify-<language>`(`scripts/verify.mts --only`)는 선택한 구현을 빌드하고 그 probe에 공통 사례를 보내며 기록을 쓰지 않습니다. `make test-scripts`는 `tests/scripts`의 도구 node:test test 또는 `TESTS`의 test 파일을 `@polyspec/kit`의 run-tests로 실행합니다. run-tests는 test마다 자기 시간 한도를 주고, test를 하나도 고르지 않는 실행을 실패시킵니다. `make typecheck`는 `scripts/`, `tests/scripts/`, `benchmarks/run.mts`의 TypeScript를 tsc로 검사합니다. Node는 type stripping으로 실행할 뿐 검사하지 않기 때문입니다. 저장소의 도구는 TypeScript이며(kit의 S9), 유일한 예외는 ojson 비교의 Python probe이고 그 이유는 `config/layout.yml`이 적습니다.

`make check`는 hosted CI가 모든 pull request와 모든 push to `main`에서 실행하는 전체 suite입니다. 로컬 실행은 선택이며, 활성 항목이 모두 끝난 뒤 tree마다 많아야 한 번 합니다. 추가 사례를 포함하면 그 실행은 다음과 같습니다.

~~~sh
make check JSON_TEST_SUITE=.cache/JSONTestSuite
~~~

`make check`는 어떤 target보다 먼저 guard인 `@polyspec/kit`의 full-run을 Makefile의 `CHECK_TARGETS` target과 함께 시작합니다. 이 저장소의 활성 작업은 [실행 체크리스트](docs/plans/execution-checklist.ko.md)에서 상태가 `[~]`인 작업입니다. guard는 판단을 이유와 함께 출력하고, 그런 작업이 있으면 각 ID를 작업과 함께 나열하며 거부하고, `make hooks-check`가 보고하듯 pre-push hook이 설치되지 않았으면 거부하고, 추적 파일의 변경이 커밋되지 않았거나 `.gitignore`가 무시하지 않는 파일이 추적되지 않으면 각각을 밝히며 거부합니다. 전체 실행은 커밋된 tree를 검증하고, build는 추적되지 않은 파일도 읽기 때문입니다. `var/full-run.json`이 현재 tree(`git rev-parse HEAD^{tree}`)의 전체 실행을 기록하고 있으면 그 실행을 commit, 시작 시각, 결과와 함께 밝히며 거부하고, `incomplete` record의 process가 아직 실행 중이면 거부합니다. guard는 첫 검사부터 끝까지 `var/full-run.lock`을 배타적으로 잡고, 다른 guard가 이를 잡고 있으면 그 holder를 밝히며 거부하므로, 동시에 시작한 두 guard가 모두 실행하지 않습니다. 각 target을 `make -k <target>`로 시간 제한 없이 끝까지 실행하고, 각 target의 log를 `var/report/full-run/targets/`에 쓰며, 각 target의 앞뒤에 record를 쓰므로, 멈춘 실행은 `incomplete`로 기록되어 남습니다. `make rerun-failed`는 현재 tree에서 통과하지 못한 target만 다시 실행하고, 그 밖에는 거부됩니다. `var/`는 Git이 무시하므로 checkout과 worktree마다 자기 record를 가집니다. hosted CI는 전체 suite를 실행합니다. `.github/workflows/ci.yml`은 모든 pull request, `main`의 모든 push, 모든 수동 실행(`workflow_dispatch`)에서 모든 실패를 지나 job마다 `make ci-targets TARGETS="..."`(`@polyspec/kit`의 ci-targets)로 `CHECK_TARGETS`의 target을 실행하고, 각 job의 보고서(`var/report/ci-targets/`)를 실행의 기록과 함께 upload합니다([hosted CI](docs/operations/validation.ko.md#ci)). `CHECK_TARGETS`의 모든 target은 `ci.yml`과 `push-gate.yml`의 job 하나에서만 실행됩니다(`tests/scripts/workflow-rules.test.mts`). commit의 근거는 그 실행입니다. workflow의 step은 script나 도구를 직접 실행하지 않고 make target을 실행합니다. 새 checkout에는 record가 없으므로, 그곳에서 `make check`는 `[~]` 작업이 없고 tree가 깨끗하면 실행됩니다.

push는 `[~]` 작업이 없을 때만 합니다. pre-push hook `.githooks/pre-push`는 `make push-gate-hook`을 실행합니다. 이 명령은 push되는 commit이나 working tree의 `docs/plans/execution-checklist.md`에 `[~]` 작업이 있으면 각 ref, commit, ID, 작업을 밝히며 push를 거부하고, 체크리스트를 읽을 수 없으면 거부합니다. Makefile을 읽는 것은 모든 make 호출이 `.githooks`로 설정하는 `core.hooksPath` 외에는 설정을 쓰지 않습니다. `make hooks`는 hook을 설치하고 검사하며, `make hooks-check`는 `core.hooksPath`가 `.githooks`가 아니거나 `config/checklist.json`의 hook이 없거나 실행 가능하지 않거나 바뀌었으면 실패합니다. hook이 없는 checkout에서 한 push는 hook을 실행하지 않으므로, `.github/workflows/push-gate.yml`의 job `push-gate`가 모든 branch에 push된 commit과 모든 pull request의 head commit에 `make ci-targets TARGETS="push-gate-commit documents-check evidence-check commits-check"`를 실행합니다. `make push-gate-commit`은 commit에 push gate를 실행하여 작업이 `[~]`이면 실패하고, `.githooks/pre-push`나 `.githooks/pre-commit`이 mode 100755로 추적되지 않으면 실패합니다. 다른 target은 gate가 실패해도 실행됩니다. 그래서 문서, 체크리스트, 기능 기록, 메시지가 자체 검사에 실패하는 commit은 release가 요구하는 check에 실패합니다. 이 job은 local checkout의 설정을 검사할 수 없습니다.

0.x 동안 변경은 소유 unit test가 로컬에서 통과한 뒤 `main`에 바로 commit합니다. pull request, merge queue, GitHub ruleset은 쓰지 않습니다. CI workflow는 `main`에 push될 때마다 전체 suite를 실행하며, 그 job `ci-passed`가 release workflow가 tag된 commit에 요구하는 check입니다. pre-push hook은 push 전에 push gate를 실행합니다.

0.x 버전의 작업 단위는 체크리스트 행 하나이고, 그 행의 `[o]`는 그 행을 끝내는 commit에 들어갑니다. 작업은 로컬에 commit하고, 체크리스트의 모든 행이 `[o]`일 때 `main`에 한 번 push합니다. 그러므로 진행 중인 행이 있는 push는 없습니다. 그 push의 CI 실행은 `ci-passed` 성공으로 끝나야 하며, 그 뒤에 버전 올림 commit을 `main`에 넣고 CI가 통과한 commit에만 tag `vX.Y.Z`를 붙입니다. 릴리스 archive의 이름은 `<package>-<language>-<version>.<ext>`입니다(`polyspec-ordered-json-npm-X.Y.Z.tgz`, `polyspec-ordered-json-php-X.Y.Z.zip`, `polyspec-ordered-json-extension-php-X.Y.Z.zip`), Python 패키지는 wheel `polyspec_ordered_json-X.Y.Z-py3-none-any.whl`로 릴리스합니다.



문서만 검토할 때는 `make documents-check`와 `make evidence-check`를 실행합니다. 이 검사들은 검증 기록을 소스와 비교하지 않습니다. commit의 근거는 커밋된 파일이 아니라 그것을 검증하는 실행입니다. `make pie-check`는 PIE 기록 `var/records/pie-verification.json`을, `make verify-all`은 통합 기록 `var/records/verification.json`을 쓰며 Git은 이를 무시하고, `make verify-all` 마지막의 근거 검사는 두 기록을 현재 소스와 대조합니다([기록](docs/operations/validation.ko.md#records)). 기록은 모든 추적 파일을 해시하므로 커밋된 기록은 commit마다 오래된 기록이 됩니다. 어떤 기록도 커밋하지 않으며, 어떤 guard도 기록이 없다는 이유로 거부하지 않습니다. 검사를 통과시키기 위해 검증 결과나 소스 해시를 직접 수정하지 않습니다.

[config/parity.json](config/parity.json)은 저장소 언어 집합의 유일한 출처인 구현과 각 구현의 디렉터리, 그리고 `@polyspec/kit`의 parity 검사에서 각 구현이 가지는 unit을 선언합니다: 공통 예제는 suite unit, 모든 패키지 테스트 케이스는 그것을 실행하는 native test에 묶인 feature unit, 그리고 공개 API입니다. `make parity-declarations-check`는 아무것도 실행하지 않고 선언을 검사하고, `make parity-check`는 binding을 실행하고 각 구현의 공개 심볼을 그 생태계의 표준 도구로 읽으므로, 빠진 케이스, 선언되지 않은 test, 선언되지 않은 공개 심볼은 실패합니다. 모든 구현보다 좁은 profile은 이유와 차이의 spec anchor를 적고, 구현이 아직 가지지 않은 unit은 그것을 제거하는 체크리스트 항목을 적은 exclusion이며, 그 항목이 끝날 때까지 검사를 실패시킵니다. 공통 검증기는 그 선언의 comparator입니다: `scripts/registry.mts`는 `config/parity.json`의 이름과 디렉터리를 읽고 각 구현의 빌드·probe·런타임 명령을 가지며, 다른 모든 도구는 패키지의 디렉터리를 그곳에서 얻습니다. 패키지 테스트는 `make parity-check`에서 각 언어의 native runner로 실행합니다. 공통 사례는 JSON 계약만 검사하므로 한 패키지에만 있는 API에는 닿지 않으며, 그런 API는 해당 패키지의 테스트가 필요합니다. 새 언어는 공통 JSON 비교 알고리즘을 변경하지 않고 `config/parity.json`, `scripts/registry.mts`의 명령, 패키지 디렉터리에 추가합니다. 계약 변경은 같은 저장소 리비전에서 검증기와 관련 패키지를 갱신합니다. [저장소 계약](docs/spec/repositories.ko.md)을 참조합니다.

모든 언어 probe는 [official.json](examples/official.json)과 [scripts/verify.mts](scripts/verify.mts)를 사용합니다. 공통 사례는 해당 파일이나 `contracts/fixtures/`에 추가합니다. 언어별로 다른 예제나 기대 결과를 만들지 않습니다.

Rust 코드는 `@polyspec/kit`의 lint인 `make lint-rust`(Cargo workspace마다 `-D warnings`의 cargo clippy)를, Go 코드는 `make lint-go`(`.golangci.yml`의 golangci-lint와 deadcode)를, PHP 코드는 `make lint-php`(`phpcs.xml.dist`의 phpcs와 `phpstan.dist.neon`의 PHPStan)를, Python 코드는 `make lint-python`(`ruff.toml`의 ruff와 vulture)을 통과합니다. 넷은 `CHECK_TARGETS`의 target이므로 hosted CI가 모든 pull request와 `main`의 모든 push에서 실행합니다. 네이티브 코드를 변경하면 PHP 확장을 다시 빌드합니다. 이전 바이너리나 이전 결과를 변경된 코드의 검증 근거로 사용하지 않습니다.

<a id="release"></a>
## 릴리스

릴리스는 CI 실행이 `ci-passed` 성공으로 끝난 `main`의 commit에 붙인 tag입니다. tag를 만들고 옮기고 push하는 것은 메인테이너뿐입니다.

1. 버전 올림 commit `Release X.Y.Z`는 `ci-passed`가 성공한 push 뒤에 오며 체크리스트 작업을 적고, 저장소의 모든 manifest(`package.json`, `packages/js/package.json`, `composer.json`, `packages/php/composer.json`, `packages/php-ext/composer.json`, `packages/rust/Cargo.toml`, `packages/python/pyproject.toml`, `package-lock.json`의 루트 항목, `packages/rust/Cargo.lock`의 package 항목)의 버전을 X.Y.Z로 정하고, 검토 기록이 각 lock의 hash를 담으므로 `make dependency-review RECORD=1`로 의존성 검토를 다시 기록하고, `make release-consumer-lock TAG=vX.Y.Z`로 그 버전의 consumer lock을 쓰며, 모든 changelog의 `## Unreleased`를 `## X.Y.Z`로 바꾸고 그 위에 비어 있는 새 `## Unreleased`를 둡니다.
2. 메인테이너는 `ci-passed`가 성공으로 끝난 `main`의 commit 하나에 두 tag를 붙입니다. `packages/go/`의 Go 모듈에는 `packages/go/vX.Y.Z`, 그리고 `vX.Y.Z`입니다. `vX.Y.Z`의 실행이 검증하기 전에 두 tag가 GitHub에 있어야 하며, 그 실행이 그 commit의 Go tag를 요구하기 때문입니다(`make release-go-tags`). 메인테이너는 Go tag를 자체 `git push`로 먼저 push하고, 그 push가 성공한 뒤에만 `vX.Y.Z`를 push합니다. 첫 push 전에 `git rev-parse --verify 'vX.Y.Z^{commit}' 'packages/go/vX.Y.Z^{commit}'`가 같은 commit을 두 번 출력해야 합니다. Go tag의 실행은 archive를 만들지 않고 archive 없는 release를 만듭니다. GitHub에 Go tag가 없는 상태로 push된 `vX.Y.Z`는 검증에 실패합니다.
3. tag push는 `.github/workflows/release.yml`을 실행합니다. 이 workflow는 tag된 commit이 `main`에 있고 check `push-gate`와 `ci-passed`를 통과했는지, 모든 manifest에 tag의 버전이 있고 `CHANGELOG.md`에 section `## X.Y.Z`가 있는지 확인하고, 패키지 archive와 Python wheel을 만들어 GitHub Release를 생성합니다([tag 릴리스](docs/operations/distribution.ko.md#tag-release)).

이 저장소의 package가 다른 저장소의 package를 고정할 때(`git+https://github.com/polyspec/<repository>@vX.Y.Z`)는 GitHub에 실제로 존재하는 tag만 씁니다. 그 tag를 push한 뒤에 고정하며, 아직 release되지 않은 tag를 가리키는 고정은 쓰지 않습니다.

<a id="tools"></a>
## 공유 도구

모든 polyspec 저장소가 공유하는 도구는 package `@polyspec/kit`이며, `package.json`의 devDependency로서 `package-lock.json`에 release asset의 URL과 integrity로 고정됩니다. 새 checkout은 `scripts/kit/bootstrap/`의 복사된 installer로 `packageManager`의 npm을 `var/tools`에 설치하는 `make install-tools TOOLS=npm`과, 그 npm으로 `package-lock.json`을 설치하는 `make install-packages`를 실행합니다. Makefile은 설치된 package의 `kit.mk`를 include하는 `scripts/kit/kit-bootstrap.mk`를 include하므로, kit의 target은 `node_modules/@polyspec/kit/dist`의 빌드된 도구를 실행합니다. package의 `kit.copies`가 나열한 파일은 `make kit-sync`가 설치된 package에서 쓰는 byte 단위 사본입니다: `scripts/kit/kit-bootstrap.mk`, `scripts/kit/bootstrap/`, `.github/workflows/release.yml`, [PRINCIPLES.ko.md](PRINCIPLES.ko.md), 공통 layout 규칙 `config/layout.kit.yml`, lint 설정(`ruff.toml`, `phpcs.xml.dist`, `phpstan.dist.neon`, `.golangci.yml`, `.oxlintrc.json`, `knip.json`, `config/api-extractor.kit.json`, `.editorconfig`), `config/`와 `config/php-lint/`의 manifest schema. 공유 도구나 사본의 변경은 polyspec/kit에서 하고, `package-lock.json`의 `@polyspec/kit`을 갱신한 뒤 `make install-packages`와 `make kit-sync`로 받아들입니다. 설치된 package가 `package-lock.json`이 해석하는 version이 아니거나, 사본이 package와 다르거나, `config/*.json`의 설정이 schema를 어기면 `make kit-check`가 실패하며, 사본은 이 저장소에서 수정하거나, 다른 이름으로 복사하거나, 끄지 않습니다. [PRINCIPLES.ko.md](PRINCIPLES.ko.md)는 모든 polyspec 저장소의 작업 원칙을 담고, 이 문서는 이 저장소의 규칙을 적습니다. 이 저장소가 다른 polyspec 저장소와 다른 곳은 `config/*.json`(checklist, commits, 의존성 정책과 검토, documents, owner 검사, release, toolchain), `config/layout.kit.yml`을 확장하고 `make layout-check`가 alint로 검사하는 폴더 지도 `config/layout.yml`, 그리고 이 저장소 고유의 제품 코드(`packages/`의 패키지, `scripts/*.py`의 검증기, benchmark)뿐입니다.

<a id="dependencies"></a>
## 의존성

의존성은 선언된 runtime 범위를 지원하는 최신 stable release를 씁니다. 의존성을 고르거나 갱신할 때 알려진 최신 release입니다. 시험판은 stable이 아닙니다. 의존성은 `make dependency-review UPDATE=1`로 고르고 갱신하며, 바뀐 manifest나 lock은 `make dependency-review RECORD=1`이 쓰는 검토 기록 `config/dependency-review.json`과 함께 commit합니다. `make dependency-policy-check`(`@polyspec/kit`의 check-dependency-policy)는 manifest와 lock을 그 기록 및 `config/dependency-policy.json`과 비교하며 registry를 질의하지 않으므로, 한 tree는 언제나 한 결과를 냅니다. `make dependency-policy-mutation-check`는 gate가 checkout의 알려진 변형을 각각 거부함을 보입니다. 더 오래된 release는 재현 가능한 사유, pin을 없애는 조건, 검증 명령을 적은 `config/dependency-policy.json`의 예외로만 고정합니다. 검토 시점에 advisory가 있는 lock은 gate에 실패합니다. polyspec 버전이 0.0.x인 동안 개발 checkout은 kit `docs/plans/local-links.md`가 설명하는 대로 설치된 polyspec package를 그 source에 link하며, link는 commit하지 않습니다.

<a id="idempotency"></a>
## 멱등성

같은 tree는 언제 어느 기계에서든 같은 결과를 냅니다. 한 polyspec 저장소에서 찾은 결함은 하나의 부류입니다. 모든 저장소에서 고치고 그 규칙을 여기에 적습니다. 각 규칙은 이 저장소가 그것을 지키는 방법을 밝힙니다.

- 검사는 결과가 시간에 따라 달라지는 registry 질의를 하지 않습니다. 최신 조회나 `@latest`, 버전 범위의 해석, 오래된 package나 새 release에 대한 질의가 없습니다. lock 파일이 정확한 버전과 integrity hash로 고정한 package를 내려받는 것은 그런 질의가 아니라 설치이며, `npm ci`와 `composer install`처럼 허용됩니다. 릴리스 archive의 consumer 설치(`make release-consumer`, `@polyspec/kit`의 release-consumer)는 `tests/release-consumer`의 커밋된 lock으로 offline 설정 없이 `npm ci`와 `composer install`을 실행합니다. 그 lock을 해석하는 `make release-consumer-lock`은 검사가 아닙니다.
- 어떤 명령도 도구를 필요할 때 설치하지 않으며, 모든 도구는 추적되는 버전으로 실행합니다. 추적 파일이 Node.js, Rust, Go, Python, PHP, npm을 고정합니다. Go, Python, Composer와 mise가 설치하는 다른 도구는 `mise.toml`의 정확한 release이며 `mise.lock`이 그 digest로 잠급니다. 로컬과 CI에서 같은 patch release를 쓸 수 없는 PHP는 `.php-version`이 minor release(8.5)로 고정하고, 검사는 major.minor를 비교하며, 각 기록은 실행 중인 patch release를 적습니다. setup-php는 minor의 최신 patch release를 설치하기 때문입니다. 그리고 `make toolchain-check`(`@polyspec/kit`의 check-toolchain)는 각 도구를 선언과 비교하고 도구를 실행하는 모든 target이 이에 의존하며, `GOTOOLCHAIN=local`과 `RUSTUP_AUTO_INSTALL=0`은 go와 rustup이 다른 toolchain을 가져오지 못하게 하고, cargo는 `--locked`로 실행하며, `make install-tools TOOLS=npm`, `make install-packages`, `make install`만 내려받는 단계로서 첫째는 tarball hash와 대조한 npm을 `var/tools`에, 둘째는 integrity와 대조한 `package-lock.json`의 package(`@polyspec/kit` 포함)를, `make install`은 `mise.lock`의 도구(`var/tools/mise`), Rust toolchain, `packages/rust/Cargo.lock`의 crate, `external-inputs.json`과 대조한 PIE PHAR와 추가 사례(`scripts/external-inputs.mts`)를 설치하고, 릴리스 archive의 consumer 설치를 뺀 다른 모든 명령은 cargo, go, npm, Composer를 offline으로 실행하며(Makefile이 export하는 `CARGO_NET_OFFLINE`, `GOPROXY=off`, `npm_config_offline`, `COMPOSER_DISABLE_NETWORK`), 내려받지 않은 입력은 `run make install`로 실패하고(`make cargo-downloads-check`는 `cargo fetch --locked --offline`을 실행해 lock file을 밝히고, `make pie-check`와 `make verify-all`은 없는 PIE PHAR나 추가 사례를 밝힙니다), CI는 image와 action을 고정하고, `make pie-check`와 `make verify-all`은 PIE PHAR와 추가 사례를 먼저 `external-inputs.json`과 비교합니다.
- 기존 외부 도구나 라이브러리가 이미 하는 일을 다시 만들지 않습니다. 그 생태계의 표준 도구를 있는 그대로 사용하고(예: Python interpreter, 환경, lock에는 uv, PHP 의존성에는 Composer), 그 도구 자신의 동작, 예를 들어 그 도구가 만드는 symbolic link를 받아들입니다. 우리 규칙은 우리가 만드는 것을 규율합니다.
- 이 저장소의 규칙이 symbolic link를 거부하거나 경로를 디렉터리 기준 상대 경로로 정하는 곳에서는, 예를 들어 symbolic link를 거부하는 build 사본([저장소 계약](docs/spec/repositories.ko.md))처럼, 그 규칙은 이 저장소가 만드는 것을 규율하며 외부 도구가 만드는 것을 규율하지 않습니다. 경로는 추적되는 파일의 이름으로 선언적으로 정하거나, 명시된 발견 규칙에 따른 발견으로 정합니다.
- test는 자기가 만든 출력만 읽고 추적되지 않은 상태에 의존하지 않습니다. 기록, 문서 검사, 공통 사례, build 사본은 Git이 추적하는 파일을 읽고, guard는 추적되지 않은 파일을 거부하며, 각 실행은 자기 `CARGO_TARGET_DIR`를 가진 자기 실행 디렉터리에서 빌드하고, test는 자기 파일을 자기 임시 디렉터리에만 씁니다.
- 공유 출력은 원자적으로 게시합니다. `var/`의 파일에 끝까지 쓴 뒤 그 경로 위로 이름을 바꿉니다(`write_record`).
- 검사는 실패를 모으고 첫 실패에서 멈추지 않습니다. 모든 언어, 단계, 사례가 끝까지 실행되고, 실행은 status 1로 끝나기 전에 모든 실패를 나열합니다.
- 검사는 사용자 로캘의 메시지를 판정하지 않습니다. 출력 텍스트를 비교하는 명령은 `LC_ALL=C`로 실행하고, `scripts/registry.mts`가 `git ls-files`를 그렇게 실행합니다.
- 실패는 기대값, 실제값, 도구 자신의 오류를 출력합니다. 일치한 줄, 다른 파일, 두 버전이나 hash, 종료 상태와 standard error입니다.
- 빈 선택은 실패합니다. test를 고르지 않는 unit test 이름, 기능 행이 없는 기록, test를 찾지 못한 실행은 이름을 밝히며 실패합니다.
- 자식 process는 명령이 끝나거나 호출자가 멈출 때 손자를 포함한 process group 단위로 회수하고(`end_group`), 임시 디렉터리는 `finally`나 context manager에서 제거합니다.
- 어떤 검사도 사람이 읽는 도구 출력을 단언하지 않습니다. parity 검사는 각 native test runner의 기계 출력을 읽고, standard error의 도구 알림은 출력하되 판단하지 않으며, `make`를 실행하는 test는 호출자의 make 변수를 제거합니다.
- 바뀐 모든 파일은 소유한 검사에 대응됩니다. `config/owner-checks.json`이 모든 추적 경로를 소유하고, `make owner-check`가 변경의 소유자를 실행하며, pre-commit hook은 대응되지 않은 경로를 거부합니다.
- 공유 디렉터리, port, fixture는 lease나 실행별 디렉터리를 거칩니다. 각 실행, test, build는 자기 임시 디렉터리를 사용하고, guard는 `var/full-run.lock`을 잡아 한 checkout의 전체 실행이 한 번에 하나씩 실행되게 합니다.

<a id="completion"></a>
## 완료

코드와 테스트를 읽고 문서의 정확성을 확인합니다. 자동 링크, 개정본, 상태 검사는 문장 내용의 정확성을 증명하지 않습니다. 테스트와 실제 게시를 별도로 확인하고 관측한 근거로만 [배포 상태](docs/operations/distribution.ko.md)를 갱신합니다.

Git 메시지는 사실대로 간단하게 작성합니다. 관련 없는 변경은 가능하면 분리합니다.
