<!-- doc-id: changelog -->
<!-- source-sha256: 9930a1753f1e4e5a94171237d41b14c6b97b512ad17e8ed41abfaee2ea416b6b -->
# 변경 기록

[English](CHANGELOG.md)

<a id="unreleased"></a>
## 미릴리스 — 2026-09-07

- setup-node는 npm cache 없이 실행합니다(T1.10). CI에서 `Dependencies lock file is not found`로
  실패했습니다. 기본으로 `package.json`의 `packageManager` 의존성을 cache하는데 저장소에 lock file이 없기 때문입니다.
  step은 `package-manager-cache: false`를 설정하고, `test_workflow_rules`는 이것이 없으면 실패합니다.
- `make ci`와 `make ci-summary`가 job을 해석합니다(T1.9). CI에서 두 step은
  `the following arguments are required: --job`로 실패했습니다. target의 remainder 인수가 `--job`까지 가져갔기 때문이며,
  보고서는 쓰이지 않았습니다. `scripts/ci_run.py`는 해석하기 전에 `--`에서 target을 떼어 냅니다. `test_ci_run`의 새 사례는
  변경 전에 그 error로 실패했고 변경 후 통과합니다.
- test가 모든 workflow의 규칙을 검사합니다(T1.8). `scripts/tests/test_workflow_rules.py`는 step이 make target 하나가 아닌
  것을 실행할 때, `make ci`를 실행하는 job에 `if: ${{ !cancelled() }}`인 summary나 report step이 없거나 실패 뒤에 실행되지
  않는 step이 있을 때, matrix에 `fail-fast: false`가 없을 때, `timeout-minutes`가 있을 때 file, job, step을 밝히며
  실패합니다. T1.4 이전의 `push-gate.yml`에 적용하면 `python3 scripts/push_gate.py`를 직접 실행한 step을 밝히고, 현재
  workflow는 통과합니다.
- hosted CI가 전체 suite를 실행합니다(T1.7). hosted CI는 push gate만 실행했으므로 commit의 전체 suite는 로컬 기계에서만
  실행됐습니다. `.github/workflows/ci.yml`은 `main`에 push된 모든 commit과 모든 pull request에서 Python 3.9가 있는
  `ubuntu-24.04`로 실행하며, job `suite`(`make pie-check`, `make check`)와 `docs`를 `fail-fast: false`인 matrix로
  실행합니다. 모든 step은 실패 뒤에도 make target을 실행하고, `make ci`(`scripts/ci_run.py`)는 target마다 log를 남기며
  모든 target을 끝까지 실행하고, `make ci-summary`는 상태, 시간, 실패한 target마다 첫 실패 줄을 담은 job summary를 쓰고
  기록을 복사하며, 보고서 `var/ci/<job>/`를 upload합니다. `test_ci_run`의 사례는 runner가 없을 때 실패했고 그 뒤 통과합니다.
- commit의 근거는 그 실행이며, 어떤 기록도 커밋하지 않습니다(T1.6). `docs/pie-verification.json`과
  `docs/verification.json`은 모든 추적 파일을 해시했으므로 commit마다 오래된 기록이 됐고, `make check`의 guard는 로컬의
  `make pie-check`와 `make check`가 이를 다시 만들어 커밋할 때까지 거부했으며, 전체 suite를 실행하는 hosted CI는 commit마다
  실패했을 것입니다. `make pie-check`와 `make check`는 Git이 무시하는 `var/records/pie-verification.json`과
  `var/records/verification.json`을 쓰고, 커밋된 기록은 제거합니다. `scripts/docs_check.py --records`는 체크아웃의 기록을
  검사하고, guard는 어떤 기록도 읽지 않으며, 기능은 근거로 검증 절차의 기록 절을 가리킵니다. `test_docs_check`와
  `test_full_run`의 바뀐 사례와 새 사례는 변경 전에 실패했고 변경 후 통과합니다.
- PHP는 minor release로 고정합니다(T1.5). 검사의 PHP를 적은 추적 파일이 없었으므로 다른 PHP에서의 실행은 어떤 고정값도
  적지 않은 PHP로 tree를 검증했습니다. `.php-version`은 8.5를 적고, `scripts/toolchains.py`는
  `php -n -r 'echo PHP_VERSION;'`의 major.minor를 그것과 비교해 기대값과 실제값을 출력하며, 기록은 실행 중인 patch
  release를 적습니다. `test_toolchains`의 바뀐 사례는 변경 전에 실패했고 변경 후 통과합니다.
- CI의 push gate는 make target으로 실행합니다(T1.4). `.github/workflows/push-gate.yml`의 step은
  `python3 scripts/push_gate.py commit`을 직접 실행했으므로 Makefile의 환경과 사전 검사가 적용되지 않았습니다.
  `make push-gate COMMIT=<commit>`이 gate를 실행하고 `COMMIT`이 없으면 실패하며, step은 이 target을 실행합니다.
  `test_push_gate`의 바뀐 사례와 새 사례는 변경 전에 실패했고 변경 후 통과합니다.
- 내려받지 않은 입력은 `make tools`를 안내합니다(T1.3). 검사가 offline이 되자 `make tools`가 내려받지 않은 crate는
  `--offline` 없이 다시 시도하라는 cargo의 안내로, 없는 PIE PHAR는 `make pie-check`의 `FileNotFoundError` traceback으로,
  없는 추가 사례는 `--suite must contain test_parsing/`나 `Supplementary suite is empty`로 실패했습니다. 모든 진입점은
  toolchain 검사 뒤 `rust/Cargo.lock`에 `cargo fetch --locked --offline`을 실행하고 lock file, cargo의 첫 error 줄,
  `run make tools, which downloads them`을 밝히며 실패합니다. `scripts/check_pie.py`와 `scripts/test.py`는 어떤 단계보다
  먼저 없는 PHAR나 추가 사례와 `make tools`를 밝힙니다. `test_toolchains`의 새 사례는 변경 전에 실패했고 변경 후
  통과합니다.
- 검사는 offline으로 실행하고 `make tools`만 내려받습니다(T1.2). cargo, go, npm, Composer는 모든 검사에서 online으로
  실행됐으므로 `cargo build --locked`가 `rust/Cargo.lock`의 crate를 필요할 때 내려받았고, PIE PHAR와 추가 사례는 손으로
  내려받았습니다. Makefile은 `CARGO_NET_OFFLINE=true`, `GOPROXY=off`, `npm_config_offline=true`,
  `COMPOSER_DISABLE_NETWORK=1`을 export하고, `scripts/toolchains.py`는 모든 진입점에 이를 설정하며, `make tools`는 이를
  제거한 채 실행합니다. `make tools`는 Rust toolchain, npm, crate, `.cache/pie/pie.phar`의 PIE PHAR,
  `.cache/JSONTestSuite`의 추가 사례를 설치하고 각각을 `external-inputs.json`과 대조합니다. `test_toolchains`의 새 사례는
  변경 전에 실패했고 변경 후 통과합니다.
- 제품 기능이 아닌 작업은 실행 체크리스트 `docs/plans/execution-checklist.md`에서 추적합니다(T1.1). `make check`의
  guard, pre-push hook, push gate는 `docs/features.md`의 `partial` 기능만 읽었으므로, 그런 작업에는 전체 실행이나 push를 멈추는
  상태가 없었습니다. 각 작업은 `[ ]`, `[~]`, `[o]`, `[!] cause: <cause>; retry: <condition>` 중 하나의 상태를 가집니다.
  `scripts/docs_check.py`는 다른 상태, 작업 ID가 없는 행, 반복된 ID, 행이 없는 체크리스트, ID나 상태가 다른 번역을 거부하고,
  `scripts/full_run.py`와 `scripts/push_gate.py`는 작업이 `[~]`이거나 체크리스트를 읽을 수 없으면 거부합니다.
  `test_docs_check`, `test_full_run`, `test_push_gate`의 새 사례는 변경 전에 실패했고 변경 후 통과합니다.
- Python은 minor release로 고정합니다. `.python-version`은 3.9.6을 적었고 `scripts/toolchains.py`는 그 release를 정확히
  요구했지만, `actions/python-versions`가 `ubuntu-24.04`용 3.9.6을 build하지 않으므로 CI는 3.9.25를 실행합니다. 로컬 실행과 CI가 서로
  다른 규칙을 따랐습니다. 로컬과 CI에서 같은 patch release를 쓸 수 없는 interpreter는 minor release로 고정합니다. `.python-version`은
  3.9를 적고, 검사는 major.minor를 비교해 기대 버전과 실제 버전을 출력하며, 통합 기록과 PIE 기록은 실행 중인 patch release를
  `platform.python`에 적습니다. PHP patch release를 비교하는 검사는 없습니다. `scripts/tests/test_toolchains.py`의 새 case는 3.9.25
  interpreter가 검사에 실패했으므로 변경 전에 실패했고, 변경 후에는 통과합니다. 3.10 interpreter는 실패합니다.
- AGENTS.md에 멱등성 절이 있습니다. 같은 tree는 언제 어느 기계에서든 같은 결과를 내고, 한 polyspec 저장소에서 찾은 결함은 모든
  저장소에서 고치는 부류이며, 부류마다 규칙 하나가 이 저장소가 그것을 지키는 방법을 밝힙니다. registry 질의나 필요할 때의 설치 없이
  추적되는 버전의 도구, 자기 출력과 추적 파일만 읽는 test, 원자적 게시, 모으는 실패, 기대값, 실제값, 도구 오류를 담은 실패, 실패하는 빈
  선택, process group 회수와 `finally`의 디렉터리 제거, 사람이 읽는 도구 출력에 대한 단언 금지, 바뀐 모든 파일의 소유자, 공유 상태를 위한
  lease나 실행별 디렉터리입니다.
- PHP 확장의 build 사본은 Git이 추적하는 파일만 담습니다. `scripts/registry.py`는
  `git ls-files --cached --others --exclude-standard`를 복사했으므로, `php-extension/`의 추적되지 않은 파일이 어떤 기록에도 밝혀지지
  않은 채 `scripts/verify.py`, `make pie-check`, benchmark의 build에 들어갔습니다. 사본은 source manifest의 추적 목록을 사용하고, Git
  metadata가 없는 tree는 통째로 복사하며, 추적되는 symbolic link는 여전히 거부합니다. `scripts/tests/test_run_isolation.py`의 바뀐
  case는 추적되지 않은 파일이 복사되었으므로 변경 전에 실패했고, 변경 후에는 통과합니다.
- 모든 추적 경로는 그것을 소유한 검사에 대응됩니다. 새 `scripts/owner-checks.json`은 경로 glob을 검증기 unit test module,
  `scripts/verify.py --only`가 검사하는 구현, 검사 `docs`와 `benchmark`에 대응시키고, `make owner-check`가 실행하는 새
  `scripts/owner_check.py`는 이 대응을 검사한 뒤 커밋되지 않은 변경, `PATHS`, 또는 `BASE` 이후 바뀐 경로의 소유자를 각각 끝까지
  실행합니다. 새 pre-commit hook `.githooks/pre-commit`은 추적 경로가 어떤 규칙에도 맞지 않거나, glob이 어떤 경로에도 맞지 않거나,
  소유자가 존재하지 않으면 commit을 거부하고, `scripts/push_gate.py`는 이 hook을 pre-push hook처럼 요구합니다. `make hooks-check`는 이
  hook이 실행 가능하지 않으면 실패하고, CI는 mode 100755로 추적되지 않으면 실패합니다. 바뀐 파일을 소유한 test를 밝히는 것이 없었으므로,
  소유한 test만 실행하는 절차는 소스를 읽는 데 의존했습니다. 새 `scripts/tests/test_owner_check.py`의 case와
  `scripts/tests/test_push_gate.py`의 새 case는 대응, 검사, hook이 없었으므로 변경 전에 실패했고, 변경 후에는 통과합니다.
- 빌드 단계, 패키지 테스트 명령, 어댑터는 손자 process를 포함한 process group 전체와 함께 끝납니다. group은 직접 자식이 실행 중일
  때만 종료되었고 읽는 쪽은 end of file을 기다렸으므로, 명령이 background에서 시작한 process는 명령이 끝난 뒤에도 실행되었고, 빌드
  단계는 그 process를 제한 없이 기다렸으며, 패키지 테스트 실행은 케이스 기한에서 실패했습니다. `scripts/registry.py`는 명령이 끝나면
  group을 종료하는 `next_chunk`로 출력을 읽고, `end_group`은 모든 `finally`에서 group을 종료합니다.
  `scripts/tests/test_build_runs.py`와 `scripts/tests/test_comparison_runs.py`의 case는 어떤 코드에도 없는 `BUILD_SECONDS`,
  `PIE_SECONDS`, `timeout` 인자를 patch했으므로 patch가 아무것도 바꾸지 않았고, 이제 조용한 단계가 2 s 이상 실행되어 자기 종료로
  끝났다고 단언합니다. 새 `scripts/tests/test_process_groups.py`의 case는 빌드 단계가 test 기한까지 기다렸고, 패키지 테스트가 케이스
  기한에서 실패했고, 멈춘 어댑터의 손자 process가 살아남았으므로 변경 전에 실패했고, 변경 후에는 통과합니다.
- 케이스 목록은 선언된 기계 형식으로 읽습니다. 목록 parser는 모든 언어에서 사람이 읽는 text(`ok`, `?`, `running`, `test result:`,
  `FAIL`)로 줄을 건너뛰었으므로, 패키지 자신의 목록에서 `ok`로 시작하는 줄은 빠졌고, standard error의 어떤 알림이든 성공한 목록을
  실패시켰습니다. `implementations.json`의 `test_cases`는 `format`을 선언합니다. JavaScript, PHP, PHP 확장의 목록은 `lines`,
  `cargo test -- --list --format terse`는 `cargo-terse`, `go test -list .* -json`은 `go-test-json`이며, 그 output event는 test
  이름이나 자기 package의 요약 줄을 담습니다. 형식이 정의하지 않은 줄은 목록을 실패시키고, 0이 아닌 종료는 standard error와 함께 목록을
  실패시키며, 0으로 끝난 목록의 standard error는 도구 알림으로 출력합니다. `scripts/tests/test_full_run.py`와
  `scripts/tests/test_push_gate.py`의 `make -n` case는 모든 make에 flag와 makefile을 더하는 호출자의 `GNUMAKEFLAGS`와 `MAKEFILES`도
  제거합니다. 새 `scripts/tests/test_case_listings.py`의 case와 `scripts/tests/test_full_run.py`의 새 case는 형식이 선언되지 않았고,
  `ok` 줄이 통과했고, 알림이 목록을 실패시켰고, `MAKEFILES`의 makefile이 dry run에 출력했으므로 변경 전에 실패했고, 변경 후에는
  통과합니다.
- `make check`와 `make rerun-failed`의 guard는 첫 검사부터 끝까지 `var/full-run.lock`을 배타적으로 잡고, 다른 guard가 이를 잡고
  있으면 그 holder를 밝히며 거부합니다. 동시에 시작한 두 guard는 둘 다 실행 중인 실행의 record를 읽지 못해 한 tree의 검증을 둘 다
  실행했습니다. Makefile을 읽는 것은 더 이상 `core.hooksPath`를 쓰지 않습니다. `make -n`을 포함한 모든 `make` 실행이 Makefile을 읽을 때
  이를 설정했습니다. `make hooks`는 새 `scripts/push_gate.py hooks-install`을 실행하고, 이 명령은 값이 다를 때만 설정을 쓴 뒤 hook을
  검사하며, guard는 여전히 hook이 없는 checkout을 거부합니다. `scripts/tests/test_full_run.py`의 새 case는 두 guard가 모두 target을
  실행했으므로, `scripts/tests/test_push_gate.py`의 바뀐 case는 `make -n docs-check`가 `core.hooksPath`를 썼으므로 변경 전에
  실패했고, 둘 다 변경 후에는 통과합니다.
- 실패는 무엇이 다른지 밝힙니다. PIE build나 도구 오류는 "위의 PIE 출력을 보라"고만 했고, 이제 일치한 줄을 나열합니다. 오래된 통합
  기록이나 PIE 기록, 실행 중에 바뀐 소스는 소스가 다르다고만 했고, 이제 바뀐 파일, 추가된 파일, 제거된 파일을 모두 나열합니다. 실패한
  runtime version 명령과 benchmark 명령은 도구의 standard error를 잃었고, 이제 둘 다 종료 상태와 그 오류를 포함합니다.
  `implementations.json`의 `extension_version` runtime 명령은 `phpversion('ordered_json')`이 `ORDERED_JSON_VERSION`과 다르면 메시지
  없이 status 1로 끝났고, 이제 두 값을 출력합니다. 거부된 push가 출력하는 규칙은 CI가 전체 검증을 실행한다고 적었지만 CI는 이를 실행하지
  않으며, 이제 CI가 검증을 실행하지 않는다고 적습니다. `js/package.json`과 `php/composer.json`의 `test` script는 존재하지 않는
  `scripts/check.py`를 실행했고, 이제 `../scripts/verify.py --only js`와 `--only php`를 실행합니다. 새
  `scripts/tests/test_failure_messages.py`의 case는 각 메시지에 해당 줄, 파일, 값, 오류가 없었으므로 변경 전에 실패했고, 변경 후에는
  통과합니다.
- `benchmarks/run.py`와 `scripts/compare_ojson.py`는 완성된 파일을 결과 위로 이름을 바꾸는 `write_record`로 결과를 게시합니다.
  두 script는 `benchmarks/results.json`, 검토용 사본 `.cache/benchmark.current.json`, `docs/reports/ojson-comparison.json`을
  제자리에서 썼으므로, 파일을 연 직후 멈춘 process는 잘린 파일을 남겼고 읽는 쪽은 파일의 일부를 볼 수 있었습니다. `write_record`는
  저장소 안의 파일을 `docs/`의 기록 옆 숨은 파일 대신 Git이 무시하고 어떤 manifest도 읽지 않는 `var/`에서 준비합니다. 새
  `scripts/tests/test_atomic_publish.py`의 중단 case 두 개는 연 직후 멈추면 빈 파일이 남았으므로 변경 전에 실패했고, 변경 후에는
  통과합니다.
- `make pie-check`는 PIE를 실행하기 전에 PHAR의 해시와 JSONTestSuite checkout을 `external-inputs.json`의 고정값과 비교하고,
  `make check`는 단위 테스트 전에 추가 사례를 비교합니다. 마지막의 문서 검사만 이를 비교했으므로, 고정값과 다른 PHAR나 추가 사례
  checkout은 검사가 결국 거부하는 기록을 위해 build와 실행 전체를 소모했습니다. 다른 필드마다 기대값과 실제값을 밝히며 명령이 실패합니다.
  고정값을 읽는 함수는 `scripts/docs_check.py`에서 새 `input_issues` 옆의 `scripts/verification_record.py`로 옮겼습니다. 새
  `scripts/tests/test_external_pins.py`의 case는 PIE가 고정되지 않은 PHAR와 추가 사례로 실행되고 전체 실행이 고정되지 않은 추가
  사례로 단위 테스트를 시작했으므로 변경 전에 실패했고, 변경 후에는 통과합니다.
- `scripts/test.py --unit`은 이름이 test를 하나도 고르지 않으면 어떤 test도 실행하기 전에 `selected 0 tests`와 그 이름을 출력하며
  실패하고, 전체 실행은 unit test를 하나도 찾지 못하면 실패합니다. `--unit registry`는 test가 없는 module `scripts/registry.py`를
  읽어 0개의 test를 실행하고 status 0으로 끝났으므로, 잘못 적은 선택이 test 실행으로 통과했습니다.
  `scripts/tests/test_unit_runner.py`의 새 case는 `--unit registry`가 status 0으로 끝났으므로 변경 전에 실패했고, 변경 후에는
  통과합니다.
- push gate와 guard는 기능 행을 내지 않는 tracker를 거부합니다. 둘 다 `| F-`로 시작하는 줄만 읽었으므로, 기능 표가 없거나, 표가
  비었거나, ID가 `F-...`가 아닌 행이 있는 `docs/features.md`에는 `partial` 행이 없었고 `scripts/push_gate.py hook`은 거부하지
  않았습니다. `scripts/docs_check.py`는 새 `feature_table`로 기능 표를 읽고, 이 함수는 표가 없거나, 행이 없거나, 기능이 아닌 행이
  있으면 예외를 던집니다. `scripts/full_run.py`와 `scripts/push_gate.py`도 이 함수로 행을 읽으며, push gate는 push를, guard는
  실행을 이유와 함께 거부합니다. `scripts/tests/test_push_gate.py`와 `scripts/tests/test_full_run.py`의 새 case는 hook, CI 명령,
  guard가 그런 tracker를 통과시켰으므로 변경 전에 실패했고, 변경 후에는 통과합니다.
- 모든 실행은 어떤 작업보다 먼저 도구를 추적되는 고정값과 비교합니다. 고정한 것이 없었습니다. 실행은 기계에 있는 Node.js, Rust, Go,
  Python, npm을 그대로 사용했고, go는 `go.mod`의 toolchain을 내려받을 수 있었고, rustup은 첫 cargo에서 toolchain을 설치할 수
  있었고, cargo는 `Cargo.lock`을 다시 쓸 수 있었으며, CI는 `ubuntu-latest`에서 움직이는 tag의 action으로 실행했습니다.
  `.node-version`은 Node.js 26.8.1, `rust-toolchain.toml`은 Rust 1.98.1, `go/go.mod`의 새 `toolchain` 줄은 Go 1.27.0,
  `.python-version`은 Python 3.9.6, `package.json`의 `packageManager`는 registry tarball의 SHA-512와 함께 npm 12.2.0을
  고정합니다. 새 `scripts/toolchains.py`는 각 도구를 고정값과 비교하고, `scripts/test.py`, `scripts/verify.py`,
  `scripts/check_pie.py`, `benchmarks/run.py`는 첫 단계 전에 이를 호출해 다른 도구마다 기대 버전과 실제 버전 또는 명령의 오류를 밝히며
  실패합니다. `GOTOOLCHAIN=local`과 `RUSTUP_AUTO_INSTALL=0`은 Makefile, registry, 검사가 설정하고, 모든 cargo 명령은
  `--locked`를 사용하며, runtime version은 rustup이 고정값을 읽는 저장소 디렉터리에서 읽습니다. `make tools`는 Rust toolchain을
  설치하고 npm tarball을 내려받아 hash가 일치하지 않으면 거부하며, `PATH`의 맨 앞에 오는 `.cache/tools/npm`에 link 없이 풉니다.
  기계의 npm은 사용하지도 바꾸지도 않습니다. GNU Make 3.81은 단순한 recipe 명령을 export한 `PATH`가 아니라 자기 `PATH`에서 찾으므로,
  어떤 recipe도 고정된 도구를 이름으로 실행하지 않습니다. CI는 `ubuntu-24.04`에서 commit에 고정한 `actions/checkout`,
  `actions/setup-python`과 `actions/python-versions`가 그 image용으로 build하는 마지막 3.9 release인 Python 3.9.25로 실행하며,
  `scripts/push_gate.py`만 실행합니다. 새 `scripts/tests/test_toolchains.py`의 case는 고정값과 검사가 없었고, cargo 명령에
  `--locked`가 없었고, workflow가 `ubuntu-latest`와 tag를 사용했으므로 변경 전에 실패했고, 변경 후에는 통과합니다.
- 검증은 모든 언어의 모든 단계를 끝까지 실행하고 모든 실패를 보고합니다. 첫 실패가 실행을 끝냈습니다. 실패한 prepare 단계는 예외를
  던졌고, package test는 처음 실패한 package에서 멈추었고, 공통 사례는 첫 불일치에서 멈추었으며, `scripts/test.py`는 단위 테스트가
  실패하면 build 전에 반환했습니다. 그래서 두 번째로 실패한 언어는 첫 언어를 고치고 전체 실행을 다시 시작할 때까지 보고되지 않았습니다.
  이제 `scripts/test.py`는 단위 테스트, 각 언어의 build, case와 symbol listing, package test, 모든 adapter의 모든 사례, runtime
  version을 끝까지 실행하고, 모든 실패를 나열하며, record를 쓰지 않고 1을 반환합니다. 실패한 build는 자기 언어의 이후 단계만
  건너뜁니다. `scripts/verify.py --only`는 모든 실패를 나열하고 status 1로 끝납니다. `scripts/tests/test_repositories.py`는 실패한
  package가 검증을 멈춘다고 단언했고, 이제 그 뒤의 package가 실행되고 실패한 두 package가 모두 보고된다고 단언합니다. 그 case와 새
  `scripts/tests/test_failure_collection.py`의 case는 실패한 두 언어 중 첫 언어만 보고되었으므로 변경 전에 실패했고, 변경 후에는
  통과합니다.
- 기록, 문서 검사, 공통 사례는 Git이 추적하는 파일만 읽습니다. `scripts/verification_record.py`의 source manifest는
  `git ls-files --cached --others --exclude-standard`를 나열하고 소스 pattern에 맞는 모든 파일을 더했으므로, 추적되지 않은 파일이
  record가 커밋된 tree로 밝히는 manifest를 바꾸었습니다. `scripts/docs_check.py`는 Markdown 문서와 JSON 보고서를 찾으려고
  디렉터리를 순회하고 디스크의 fixture를 셌으며, `scripts/verify.py`는 디스크의 모든 fixture 파일을 공통 사례로 실행했습니다.
  `scripts/registry.py`는 `git ls-files --cached`로 추적 파일을 나열하고, 이 읽기들은 모두 그 목록을 사용합니다. source archive처럼
  Git metadata가 없는 tree는 여전히 자기 파일을 읽습니다. guard `scripts/full_run.py`도 `.gitignore`가 무시하지 않는 파일이 추적되지
  않으면 build가 그 파일을 읽으므로 각각을 밝히며 전체 실행을 거부합니다. 새 `scripts/tests/test_tracked_inputs.py`의 case와
  `scripts/tests/test_full_run.py`의 새 case는 추적되지 않은 파일이 manifest, 문서, 보고서, fixture, guard 판단을 바꾸었으므로 변경
  전에 실패했고, 변경 후에는 통과합니다.
- 검증 실행의 모든 cargo 명령은 그 실행 안의 `CARGO_TARGET_DIR`에 빌드합니다. Rust probe는
  `rust/target/debug/examples/probe`였고 cargo는 환경이 지정한 target 디렉터리를 사용했으므로, 다른 체크아웃이나 이전 tree가
  빌드한 probe, test binary, API listing이 현재 소스를 대신해 답할 수 있었습니다. `implementations.json`은 `rust`에
  `"env": {"CARGO_TARGET_DIR": "{cache}/rust-target"}`를 선언하고, `scripts/registry.py`는 이를 그 구현의 모든 prepare 단계,
  listing, test, runtime 명령에 전달하며, probe는 `{cache}/rust-target/debug/examples/probe`입니다. `benchmarks/run.py`는 Rust
  benchmark의 `cargo run`을 실행 디렉터리 안의 `CARGO_TARGET_DIR`로 실행합니다. `scripts/tests/test_run_isolation.py`의 새 case
  두 개는 명령이 상속된 `CARGO_TARGET_DIR=/shared/target`을 유지했으므로 변경 전에 실패했고, 변경 후에는 통과합니다.
- push는 `docs/features.md`에 `partial` 기능이 없을 때만 합니다. pre-push hook `.githooks/pre-push`는
  `scripts/push_gate.py hook`을 실행하고, 이 명령은 push되는 commit이나 working tree에 `partial` 행이 있으면 각 ref, commit, ID,
  기능을 밝히며 push를 거부하고, push되는 commit의 `docs/features.md`를 읽을 수 없으면 거부합니다. 모든 `make` 실행은 Makefile을
  읽을 때 `core.hooksPath`를 `.githooks`로 설정합니다. `make hooks`는 이를 설정하고 검사하며, `make hooks-check`는 설정되지 않았거나
  hook이 실행 가능하지 않으면 실패합니다. guard `scripts/full_run.py`는 hook이 설치되지 않았으면 `make check`와 `make rerun-failed`를
  거부합니다. hook이 없는 checkout에서 한 push는 hook을 실행하지 않으므로, workflow `.github/workflows/push-gate.yml`이 모든 push된
  branch와 pull request에서 job `push-gate`로 `scripts/push_gate.py commit`을 실행합니다. 이 job은 기능이 `partial`이면 실패하고,
  `.githooks/pre-push`가 mode 100755로 추적되지 않으면 실패합니다. AGENTS는 이 저장소에 CI workflow가 없다고 적었고, 진행 중인 작업의
  push를 거부하는 것은 없었습니다. `scripts/tests/test_push_gate.py`와 `scripts/tests/test_full_run.py`의 새 case 두 개는 gate, hook,
  workflow가 없고 guard가 hook 상태를 받지 않았으므로 변경 전에 실패했고, 두 file의 20개 case는 변경 후에 모두 통과합니다.
- `scripts/docs_check.py`는 `docs/features.md`나 그 번역에서 기능 행의 구현 칸이 아닌 곳에 code span이나 표 칸으로 적힌 구현
  상태(`implemented`, `partial`, `planned`)와, 기능 표의 절에서 표가 아닌 줄에서 file, 줄, 열을 적으며 실패합니다.
  `docs/features.md`는 `scripts/full_run.py`가 읽는 tracker이고, 그 범례 문단이 각 상태를 그 절 안에 code span으로 적었으므로
  상태를 읽는 도구가 기능 행 밖의 상태를 보았습니다. 범례는 상태를 정의하는 AGENTS.md의 새 절 기능 상태로 옮겼습니다. 문장 속 상태 단어는 일반 영어이므로 검사하지
  않습니다. `scripts/tests/test_docs_check.py`의 새 case 두 개는 변경 전에 code span, 표 칸, 표 절의 문단이 검사를 통과했으므로
  실패했고, 변경 후에는 통과합니다. 범례를 옮기기 전에 검사는 `docs/features.md`의 9번째 줄과 번역의 10번째 줄을 보고했습니다.
- `make check`는 검증보다 먼저 guard `scripts/full_run.py`를 시작합니다. 개발 절차는 `make check`를 모든 활성 항목이 완료된 뒤 한
  번 실행하도록 하지만 이를 강제하는 것이 없었습니다. `make check`는 작업이 진행 중일 때, 커밋되지 않은 변경이 있을 때, 이미 검증한 tree에서도 검증을
  시작했습니다. guard는 판단을 이유와 함께 출력하고, `docs/features.md`의 기능이 `partial`이면 각 ID를 기능과 함께 나열하며 거부하고, 추적
  파일의 변경이 커밋되지 않았으면 거부하고, `var/full-run.json`이 현재 tree의 전체 실행을 기록하고 있으면 그 실행을 밝히며 거부합니다. 검증을 끝까지
  실행하고 그 앞뒤에 record를 쓰므로 멈춘 실행은 `incomplete`로 남습니다. `make rerun-failed`는 현재 tree의 전체 실행이 실패했거나 끝나지
  않았을 때만 검증을 다시 실행합니다. `docs/features.md`는 `partial`을 진행 중인 작업으로, `planned`를 시작하지 않은 작업으로 정의합니다.
  `scripts/tests/test_full_run.py`는 변경 전 `No module named 'full_run'`으로 실패했고 그때 `make -n check`는
  `scripts/test.py`만 출력했습니다. 변경 뒤 그 10개 case가 stub target으로 통과합니다.
- 각 검증 실행은 자신만의 임시 실행 디렉터리에서 빌드하고 끝나면 그 디렉터리를 제거합니다.
  `make check`, `scripts/verify.py`, PIE 검사, 벤치마크는 그 디렉터리에 복사한 `php-extension/`
  소스 파일로 PHP 확장을 빌드하고, Go probe는 그 디렉터리에 기록되며, PIE는 그 디렉터리에서
  작업하고, ojson 비교는 Erlang 모듈을 그 디렉터리에서 컴파일합니다. 확장은 `php-extension/src`
  에서 `make distclean`, `phpize`, `configure`로 빌드되었고 Go probe, PIE 작업 디렉터리, Erlang
  모듈은 `.cache/` 아래 고정 경로를 사용했기 때문에, 한 체크아웃의 두 실행이 다른 실행이 사용
  중인 빌드 출력을 지우거나 교체했습니다. registry 키 `build_in_copy`가 복사본 빌드를 선택하며,
  복사본은 추적 중이거나 무시되지 않은 파일을 담고 symbolic link를 거부합니다. PIE 기록은
  산출물을 실행 디렉터리 기준 경로로 명시합니다. 이전 제자리 빌드가 남긴 무시된 출력
  (`php-extension/src`의 `phpize`, `configure`, `make` 파일과 `modules/`, `.cache/probes`,
  `.cache/pie-check`)은 어떤 명령도 읽지 않으므로 체크아웃에서 제거했습니다.
- ojson 비교는 Erlang 컴파일 출력을 종료 상태, 경과 시간과 함께 흘려 보내고, 각 프로젝트에
  사례를 한 번에 하나씩 공통 60 s 응답 deadline으로 보내며 사례마다 경과 시간을 출력합니다.
  컴파일에는 45 s 한도, 프로젝트 실행마다 전체 사례에 60 s 한도 하나가 있어서, 느린 컴파일이나
  느린 전체 실행은 시계 때문에 실패했고 각 명령이 끝날 때까지 아무것도 출력되지 않았습니다.
- 빌드 단계 출력을 흘려 보냅니다. 각 `prepare` 단계와 PIE 명령은 시작 줄, 도착하는 대로의 출력
  줄, 종료 상태와 경과 시간을 출력합니다. 두 곳 모두 출력을 모았다가 명령이 끝난 뒤에 출력해서,
  PIE 빌드는 약 42 s 동안 아무것도 보이지 않았습니다.
- 빌드 단계와 PIE 명령에는 시간 한도가 없으며, 종료 상태와 출력이 결과를 결정합니다. `prepare`
  단계마다 1500 s, PIE 명령마다 4200 s였던 deadline은 그 시간 동안 출력 없이 진행하던 정상
  빌드를 종료하고 실행을 실패시켰습니다. 패키지 테스트 케이스와 어댑터 응답은 60 s deadline을
  유지합니다.
- 검증기는 각 어댑터에 공통 사례를 한 번에 하나씩 보내고 응답 하나를 60 s deadline으로 읽으며,
  사례마다 경과 시간과 함께 출력합니다. 응답하지 않는 어댑터는 종료되고 해당 사례 이름이
  보고됩니다. 이전에는 모든 사례를 한꺼번에 보내고 어댑터 실행 전체에 60 s 한도 하나를 두어서,
  느리거나 응답하지 않는 어댑터는 사례 이름 없이 실패했고 어댑터가 끝날 때까지 아무것도
  출력되지 않았습니다.
- 패키지 테스트 출력을 흘려 보냅니다. 각 케이스의 deadline은 직전 결과 줄 이후 60 s입니다.
  이를 넘긴 실행기는 process group과 함께 종료되고, 검증기는 실행 중이던 케이스와 경과 시간을
  보고합니다. 이전 검증기는 출력을 모두 모았다가 실행기가 끝난 뒤에만 보여 줘서, 멈춘 케이스는
  아무것도 보이지 않았고 실행은 끝나지 않았습니다. JavaScript와 PHP 실행기는 케이스마다
  `<id> ok|FAIL (<ms>)`를 출력합니다. Rust는 `--quiet` 없이 `--test-threads=1`로 실행해서 각
  test 이름을 실행 전에 출력하고, Go는 `-v -p 1`로 실행합니다. `go test`는 여러 package를
  병렬로 검사하면 package가 끝날 때까지 그 출력을 붙잡아 두기 때문입니다.
- 개발 절차는 변경을 진행하는 동안 그 변경을 소유한 테스트만 실행하고(`scripts/verify.py
  --only`, `scripts/test.py --unit`), `make check`는 활성 항목이 모두 끝난 뒤 한 번 실행합니다.
  이전 절차는 변경마다 `make check`를 요구해서 수정할 때마다 모든 패키지와 공통 사례를 다시
  실행했습니다. 기본적으로 `main`에서
  작업하고, 에이전트나 상황이 필요로 하는 브랜치나 워크트리는 합친 즉시 제거합니다.
- 검증기 unit test는 시작할 때 test 이름을 출력하고, 끝나면 상태와 경과 시간을 출력합니다. 각
  test에는 자기 deadline이 있으며, test가 따로 선언하지 않으면 60 s입니다. deadline을 넘긴
  test는 이름과 함께 실패합니다. 이전 runner는 test마다 점 하나만 출력해서, 멈춘 test는 아무것도
  출력하지 않았고 실행은 끝나지 않았습니다. `python3 scripts/test.py --unit TEST...`는
  지정한 test만 실행합니다.
- `make docs-check`는 문서만 검사합니다. 이 검사는 검증 기록을 현재 소스와 비교해서, 소스를
  하나라도 바꾸면 전체 suite를 실행할 때까지 "Verification is stale"로 실패했습니다. `make
  check`는 기록을 쓴 뒤 `--records`를 붙여 검사기를 실행하므로 오래된 검증 기록이나 PIE 기록은
  그 단계에서 여전히 실패합니다.
- root `Cargo.toml`을 제거합니다. 이 파일은 `rust/Cargo.toml` 옆에서 `ordered-json` 패키지를 한
  번 더 정의해서, 이 저장소에 의존하는 모든 Cargo 빌드가 "skipping duplicate package"를 경고했습니다.
  Cargo는 그 파일 없이도 Git 의존성에서 `rust/Cargo.toml`을 찾습니다. 저장소 테스트가 Cargo
  패키지마다 manifest 하나를 요구합니다.
- Rust 소스를 rustfmt로 정리하고 `make check`의 모든 Rust build 전에 형식을 확인합니다.
  `rust/src/lib.rs`와 `rust/tests/api.rs`는 rustfmt 형식이 아니었고, 이를 잡는 확인이 없었습니다.
- JavaScript 타입 선언에 `ParseError.kind`를 선언합니다. 파서는 모든 `ParseError`에 거부 종류를
  설정하지만, TypeScript 호출자는 형 변환 없이 그 값을 읽을 수 없었습니다.
- 모든 깊이에서 해석된 객체 키의 반복을 같은 위치 규칙과 UTF-16 단위로 거부하는 JavaScript
  `rejectDuplicates` 파싱 옵션을 추가합니다. 기본 파싱은 바뀌지 않습니다.
- 모든 깊이에서 해석된 객체 키의 반복을 거부하는 PHP 파싱을 Rust 엄격 바이트 파서와 같은
  위치 규칙으로 추가합니다. `Value::parse`는 문서화된 결과를 유지합니다.
- Rust 타입 바인딩 의존성을 검증한 버전으로 고정합니다. 바인딩은 Serde JSON 토큰 프로토콜로
  JSON 원문을 기록하므로 의존성 업데이트에는 해당 패키지 테스트가 필요합니다.
- 검증 기록에 구현의 테스트 결과가 있을 때 `package-tests` 기능 검증 상태를 허용합니다.
  현재 테스트 의존성이 요구하므로 Rust 최소 버전은 1.71입니다.
- Rust Serde 타입 인코딩·디코딩을 추가합니다. 구조체 필드는 선언 순서를 유지하고
  wire·manifest fixture가 출력 바이트를 고정하고 포함된 `Value` 필드는 객체 순서와 숫자 토큰을
  유지하며 잘못된 입력, 반복 입력, 알 수 없는 입력은 오류로 처리합니다.
- 모든 깊이에서 해석된 객체 키의 반복을 거부하는 Rust 바이트 파서를 추가합니다. 모든 입력
  멤버가 필요한 호출자는 이를 선택하고 일반 파서는 문서화된 결과를 유지합니다.
- Rust 패키지의 Cargo 레지스트리 게시를 비활성화합니다. Rust 패키지에 선언된 라이선스가
  없고 소스 체크아웃만 배포가 확인되었습니다.
- Go `Marshal`이 nil `*Value` 필드를 `expected orderedjson Value` 오류 대신 다른 nil 포인터와 같이 `null`로 기록하도록 수정했습니다. nil 검사가 `MarshalJSON` 경계보다 먼저 실행되므로 타입이 `MarshalJSON`을 구현하는 nil 포인터는 모두 `null`이며, 인터페이스는 그 안에 담긴 값으로 인코딩합니다.
- 벤치마크 실행기가 각 fixture에 선언된 객체·배열·스칼라·노드·최대 깊이
  수를 파싱한 입력과 대조하도록 수정했습니다. 올바른 메타데이터, 노드
  계산, 깊이 불일치 거부를 검사하는 회귀 테스트를 추가했습니다.
- 모든 벤치마크 하니스가 선언된 반복 횟수뿐 아니라 선언된 시간만큼도 워밍업하며, 러너는 실패한 측정을 커밋된 결과에 반영하지 않았을 때 저장했다고 출력하지 않습니다. 횟수로만 정의한 워밍업은 작은 fixture에서 수 마이크로초 만에 끝나서, 프로세스가 먼저 측정한 fixture가 1.5~1.7배 느리게 나왔고 `serde_json`도 마찬가지였습니다. fixture 순서를 뒤집으면 느려지는 대상이 fixture가 아니라 위치를 따라 옮겨갔습니다. 기록된 프로토콜에 워밍업 시간이 들어가므로 이전 프로토콜로 측정한 결과는 비교 대상이 아니며, 기준을 다시 측정했습니다.
- 등록 정보가 저장소 URL을 한 번만 선언합니다. 같은 값이 `implementations.json`에 패키지마다 하나씩 다섯 벌, 레지스트리 로더와 문서 검사기에 리터럴로 두 벌 더 있었고, 그래서 소스 관찰은 선언이 아니라 상수와 대조되고 있었습니다. 이제 등록 정보가 선언한 하나와 대조합니다.
- 기능은 자신이 주장하는 상태를 뒷받침하는 기록을 가리키며, 벤치마크 결과는 깨끗한 체크아웃에서 `workload.json`이 선언한 프로토콜과 입력으로 측정했을 때에만 근거가 됩니다. 이전 규칙은 검증된 기능이면 무조건 `verification.json`을 걸도록 요구했는데 그 기록에는 벤치마크 내용이 한 줄도 없어서, `F-BENCHMARK`는 측정값이 전혀 없는 파일을 근거로 달고 있었습니다. 커밋된 결과는 60커밋 전 더러운 트리에서 측정된 것이라 어떤 소스를 설명하는지 특정할 수 없었고, 그래서 다시 측정했습니다. 결과는 소스가 아니라 기록이므로, 재측정이 통합 검증 기록을 낡은 것으로 만들지 않습니다.
- 검증 기록은 무언가로 검사할 수 있는 값만 남깁니다. 외부 입력인 PIE 도구와 추가 입력 모음은 `external-inputs.json`에 고정하고 기록과 대조합니다. 기록하던 확장 산출물 해시는 제거했습니다. 링크된 모듈은 매번 새 식별자와 서명을 받아 어떤 재빌드도 같은 해시를 만들지 못했고, 그래서 그 값은 틀릴 수조차 없었으며, `make pie-check`는 실행할 때마다 커밋된 기록을 다시 썼습니다. 이제 기록은 등록 정보가 선언한 경로로 산출물을 명시합니다. 그 선언은 지금까지 아무도 읽지 않던 것입니다. 테스트가 기록된 모든 해시를 하나씩 바꾸고 검사가 실패하기를 요구하므로, 반증할 수 없는 값은 다시 들어올 수 없습니다.
- 파싱 오류가 공통 목록에서 고른 거부 종류를 함께 전하며, 공통 검사가 같은 문서에 대해 모든 구현이 같은 종류를 알리도록 요구합니다. 메시지 문구는 언어별 관습을 그대로 둡니다. Go와 Rust는 소문자 문장을, JavaScript는 숫자 오류의 세분된 표현을 유지합니다.
- 각 패키지가 공개 심볼을 보고하고, 표준은 심볼마다 그것을 검증하는 케이스를 적습니다. 이 대조로 네 곳을 찾았습니다. Go `ParseBytesBorrowed`에는 테스트가 없었고, Rust `OrderedMap::iter`와 `stringify`는 어떤 케이스도 호출하지 않았으며, JavaScript 타입 선언은 `stringify`에 없는 옵션 인자를 설명하고 있었습니다.
- 공통 검사가 각 구현이 입력을 어디에서 거부하는지 비교하며, 모든 구현이 문서를 무효로 만든 첫 바이트를 보고합니다. 이 비교로 위치가 달랐던 문서 5건을 찾았습니다. JavaScript, Go와 두 PHP 백엔드는 이스케이프하지 않은 제어 문자보다 한 바이트 뒤를, 순수 PHP는 잘못된 Unicode 이스케이프에서 문제 자리가 아니라 시작 위치를 가리켰습니다.
- 패키지 테스트 표준과 이를 강제하는 검사를 추가했습니다. 각 구현이 실행하는 케이스를 보고하고, 필수 케이스가 빠지거나 선언되지 않은 케이스가 보고되면 `make check`가 실패합니다. 언어 간 커버리지는 검토가 아니라 도구가 판정합니다.
- 잘못된 UTF-8 오류가 모든 구현에서 첫 잘못된 바이트를 보고합니다. JavaScript와 Go는 0을, Rust와 두 PHP 백엔드는 해당 바이트를 보고했고 공통 사례는 위치를 비교하지 않았습니다. 이제 패키지 테스트가 모든 구현에 이 규칙을 요구합니다.
- JavaScript 패키지가 공통 사례로는 닿을 수 없는 값 API의 자체 테스트를 선언합니다. 이제 모든 구현 패키지가 패키지 테스트를 선언합니다.
- Rust 패키지가 공통 사례로는 닿을 수 없는 값 API의 자체 테스트를 선언합니다.
- PHP의 짝 없는 서로게이트 오류를 고쳤습니다. 네임스페이스 안에서 예외 이름을 수식하지 않아 `UnexpectedValueException` 대신 클래스를 찾을 수 없다는 오류가 났습니다. 이제 PHP 패키지가 자체 테스트를 선언하며, 그 테스트가 이 결함을 찾았습니다.
- PHP 확장 패키지가 공통 사례로는 닿을 수 없는 디스크립터 API의 자체 테스트를 선언합니다.
- 한 바인딩에만 있는 API의 규칙을 API 계약에 적었습니다. 공유 parser와 serializer를 사용하고, 결과·오류·위치를 바꾸지 않으며, 바인딩 확장 절에 적고, 해당 패키지가 선언한 테스트로 검증합니다. Go `Marshal`을 그 절에 문서화했습니다.
- 구현 등록 정보가 패키지별 테스트 명령을 선언하고, `make check`가 그 명령을 실행하며, 검증 기록이 결과를 요구합니다. 공통 사례는 어댑터를 통해서만 실행되어 언어 전용 API에 닿지 못했고, 그래서 모든 공통 사례가 통과하는 동안에도 결함이 남아 있었습니다.
- Go `Marshal`의 생략 규칙과 오류 보고를 바로잡았습니다. `omitempty`와 `omitzero`는 별개 규칙이고, 유한하지 않은 부동소수점은 해당 필드를 지목하며, 도달하지 않던 `time.Time` 분기를 제거했습니다. 시드 기반 무작위 테스트가 값 20,000개를 host 인코더의 해석된 구조와 비교합니다.
- Go `Marshal`을 고쳤습니다. 익명 구조체 필드가 아무 필드도 넣지 못했고, 이름이 겹치는 필드는 조용히 사라졌으며, 순환 참조 값은 프로세스가 죽을 때까지 재귀했습니다. 이제 Go의 필드 승격과 같게 펼쳐 넣고, 겹치는 이름과 파서 한도보다 깊은 값은 오류입니다.
- PHP 객체 하이드레이션이 멤버마다 값을 두 개가 아니라 하나만 만들고, 직렬화는 키 토큰을 디스크립터에서 읽습니다. 파싱 후 전체 조회 시간은 확장에서 이전의 0.85~0.99, 순수 PHP에서 0.90~1.00이었고 결과는 같습니다.
- Go typed 구조체·map·slice·스칼라·시간·바이트 값을 위한 `Marshal` 바인딩을 추가했습니다. 사용자 정의 marshaler 결과를 ordered-json으로 검증하고 host JSON 인코더를 사용하지 않고 compact JSON을 생성합니다.
- PHP 컨테이너 직렬화를 `compact()` 밖으로 옮겼습니다. 조회 함수 변경 후 커진 호출 프레임 때문에 확장 직렬화가 약 1ns 느려졌던 문제이며, 이제 확장 직렬화 시간은 그 변경 전의 0.92~0.95입니다.
- PHP 확장은 자식 `Value` 객체를 PHP 루프 대신 C의 `ordered_json_hydrate()`로 만듭니다. 확장 사용 시 파싱 후 전체 조회 시간은 이전의 0.65~0.99였고, 파싱·직렬화·왕복은 0.99~1.02 범위였으며 결과는 같습니다.
- Rust 루트 배열은 모든 항목을 복사하지 않고 파서의 대기 항목 스택을 그대로 사용하며, 길이의 1/4을 넘는 여유 용량은 해제합니다. 숫자 90개와 110,000개로 된 루트 배열의 파싱 시간은 이전의 0.84~0.85였고 결과는 같습니다.
- PHP 값 조회 비용을 줄였습니다. 조회 함수는 보조 메서드를 연쇄 호출하지 않고 디스크립터 테이프를 직접 읽고, 자식 값은 생성자 승격 없이 만들며, escape 문자열은 중간 UTF-16 단위 배열 없이 UTF-8로 해석합니다. 파싱 후 전체 조회 시간은 확장 사용 시 이전의 0.43~0.89, 순수 PHP에서 0.60~0.97이었고 결과는 같습니다.
- JavaScript `Value` 객체를 파싱 중에 freeze하지 않도록 변경했습니다. 값의 상태는 private field에 있으므로 여전히 라이브러리 API로 변경할 수 없으며, 반환하는 항목 배열과 키 배열은 계속 freeze합니다. API 계약에 이 보장을 명시했습니다.
- PHP `useNative` 파싱 옵션, `parseNative()`, 사용하지 않는 PHP `stringify()` compact 인자, 사용하지 않는 JavaScript `stringify()` options 인자, 네이티브 `ordered_json_compact()` 함수를 제거했습니다. PHP는 확장이 로드돼 있으면 확장을, 그렇지 않으면 순수 구현을 사용합니다.
- PCRE backtrack 또는 recursion 한계가 매우 낮으면 올바른 입력을 거부하던 순수 PHP UTF-8 검증을 수정하고, 오프셋을 지역 변수로 전달하여 순수 PHP 파서 부담을 줄였습니다.
- 문서 검사가 오래된 PIE 기록을 거부하므로 소스 변경 후 `make check`보다 `make pie-check`를 먼저 실행하도록 문서화했습니다.
- 결과, 오류, 오프셋을 바꾸지 않고 모든 구현에서 값마다 수행하던 파싱과 직렬화 작업을 줄였습니다. JavaScript는 `WeakSet` 등록 대신 private field brand로 값을 검사하고, escape가 없는 문자열을 원문에서 잘라 쓰며, 객체 키 토큰을 조회할 때 생성합니다. Go는 값을 묶음 단위로 할당하고 문자열 UTF-16 단위를 조회할 때 해석합니다. Rust는 값마다 빈 해시 맵, 항목 벡터, 단위 벡터를 두는 대신 종류별 payload를 저장합니다. PHP 라이브러리와 확장은 정수 디스크립터 테이프를 사용하며 확장은 별도 선검증 대신 문자열을 검사하면서 UTF-8을 검증합니다. 무의미한 공백과 중복 키가 없는 값은 원문 토큰을 복사하여 직렬화합니다. 이전 구현과 파싱 결과, 오류, 오프셋, 조회 API, 생성 API, 직렬화를 비교하는 차등 테스트를 수행했습니다. PHP 디스크립터 형식은 [API 계약](docs/spec/api.ko.md#php)에 설명합니다.
- 벤치마크가 Rust release 빌드, 고정 workload 입력 digest, 반복 샘플, median/p95 통계, 실행 환경 fingerprint, 커밋된 결과를 사용하도록 수정했습니다.
- 비교 가능한 실행이 허용오차를 초과할 때 커밋된 벤치마크 기준을 보존하고 실패한 측정값을 검토용으로 별도 기록하도록 수정했습니다.
- 네이티브 macOS 배포 대상과 번들 설정을 수정하여 오래된 `-single_module` 및 `-undefined suppress` 링커 경고를 해결했습니다.
- 같은 공통 JSON 사례로 PIE 산출물을 검사하고 PHP 버전과 확장 버전을 별도로 기록하도록 추가했습니다.
- Go 모듈을 `github.com/polyspec/ordered-json/go`로 변경했습니다.
- 이동한 의존성 파일에 이전 빌드 경로가 남아 반복 네이티브 설정 전에 `make distclean`을 추가했습니다.
- 구현 빌드·어댑터·런타임 명령 등록 정보를 추가했습니다.
- PHP 확장 소스를 `php-extension/src`로 분리하고 단독 빌드를 기본 활성화하는 PIE 패키지 메타데이터를 추가했습니다.
- 핵심 값 생성과 문자열 처리에서 host JSON parser와 serializer 의존성을 제거하고 모든 구현에 공통 반복 round-trip 검증을 추가했습니다.
- 런타임 네이티브 JSON API와 비교하는 재현 가능한 다언어 성능 벤치마크를 추가했습니다.
- 고정 workload manifest와 엄격한 벤치마크 행·입력 크기·출력 크기 검사를 추가했습니다.
- PHP 네이티브 확장의 직렬화 중 재파싱을 제거하고 Go와 Rust 구현의 반복 순서 맵 조회를 줄였습니다.
- JavaScript 직렬화와 유니코드 escape 파싱을 최적화하고 PHP 디스크립터 자식 값 생성을 지연했습니다. Rust 직렬화의 불필요한 캐시 할당을 제거하고 명시적인 zero-copy Go `ParseBytesBorrowed` API를 추가했습니다.
- 미릴리스 패키지와 확장 버전을 `0.0.1`로 설정했으며 릴리스나 자동화는 구성하지 않았습니다.

- 언어별 패키지, 네임스페이스, 가져오기, 네이티브 심볼, 빌드 출력을 [API 계약](docs/spec/api.ko.md)의 ordered-json 식별자로 변경했습니다.
- 명세, API, 기능 상태, 운영, 예제, 개발 절차에 영어 정본과 한국어 번역을 추가했습니다.
- `make check`와 `make docs-check`를 추가했습니다. 문서 등록, 링크, 번역 개정본, 섹션·코드 일치, 기능 상태, 현재 검증 근거를 검사합니다. 검증 기록에 실제 소스 해시, 런타임 버전, 공통 테스트 결과를 포함합니다.
- 복사된 읽기 전용 빌드 파일이 반복 설정을 방해하여 PHP 확장을 phpize 생성 파일 정리 후 다시 빌드합니다. 도구의 종료 상태가 0이어도 빌드 오류 진단이 있으면 검증을 중단합니다.
- 요청된 ojson 비교를 `docs/reports/`로 이동하고 컴파일 진단 경로를 소스 기준 상대 경로로 변경했습니다.
- JSON 객체를 순서 있는 연관배열로 변경했습니다. 중복 키는 최초 키 위치를 유지하면서 값을 덮어쓰므로 디코딩한 키마다 값이 하나입니다. 중복 조회와 멤버 목록 API를 제거했습니다. 기본 직렬화는 연관배열 객체를 출력하며 원문 조회는 별도로 제공합니다.
- 엄격한 파싱, 재귀 문서 순서, 정확한 숫자 토큰, 생성 API를 제공하는 JavaScript, Rust, Go, 순수 PHP, PHP 확장 구현을 추가했습니다.
- 공식 입력과 기대 결과를 [official.json](examples/official.json)으로 통합하고 공통 문법 사례와 선택적 추가 입력을 제공합니다.
- 모든 구현을 공통 사례 433개로 검증했습니다. PIE 빌드 산출물도 같은 433개를 통과했으며 검사기 테스트 42개가 통과했습니다. 당시 PHP 빌드 도구의 링커 옵션 사용 중단 경고 두 건은 해당 검증 기록에 기록했습니다.

현재 검증 기록은 검사한 소스와 다섯 구현 및 문서 검사기 테스트의 결과를 명시합니다. [배포 확인 결과](docs/distribution.json)는 별도입니다. 이 항목은 개발 변경을 기록하며 패키지 릴리스를 선언하지 않습니다.
