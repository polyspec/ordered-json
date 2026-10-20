<!-- doc-id: rebuild-json-rust -->
<!-- source-sha256: 2a356b266e98671fbd441ca54df15e152e47f1f6cbf3f31b2503c63f704ecb62 -->
# 재구현 기록: Rust JSON parser

[English](json-rust.md)

판정: **맞는 도구 없음.** Rust package는 자체 parser를 유지합니다. 2026-10-20에 측정했습니다.

## 대상

- `packages/rust/src/lib.rs`

## 요구사항

parser는 문서를 손실 없는 순서 값으로 읽습니다: 모든 깊이의 key 순서, 반복된 key의 첫 위치와 마지막 값, 모든 number
token의 표기, `{}`와 `[]`의 구분, 첫 잘못된 byte의 byte offset과 공통 목록의 kind로 하는 거부, 256의 nesting 한도
(`docs/spec/json-contract.md`의 RQ-001부터 RQ-024).

## 평가한 도구

| 도구 | 결과 |
|---|---|
| `preserve_order`와 `arbitrary_precision`을 켠 serde_json | `examples/official.json`과 `contracts/fixtures`의 105 of 115 case(받아들인 tree 또는 거부)가 성립합니다 |

| 요구사항 | 실패 이유 | 실패한 case |
|---|---|---|
| RQ-010 | exponent 표기가 정규화됩니다(`1.2300E+04`가 `1.2300e+04`, `1e9999`가 `1e+9999`) | `official/exact-number-tokens`, `valid/exponent.json`, `valid/tiny-exponent.json` |
| RQ-009 | 이스케이프된 짝 없는 surrogate를 거부합니다 | `official/escaped-surrogates`, `official/unicode-key-overwrite`, `valid/lone-high-surrogate.json`, `valid/lone-low-surrogate.json`, `valid/mixed-surrogates.json`, `valid/surrogate-key.json` |
| RQ-006 | nesting 한도가 256이 아니라 128입니다 | `valid/container-depth-limit.json` is rejected |
| RQ-004, RQ-005 | 줄과 열을 보고하며 contract의 byte offset은 63개 거부 중 9개에서만 같고 공통 kind가 없습니다 | the other 54 rejections |

## 맞는 도구가 없는 이유

생태계의 표준 reader는 native 값으로 decode하도록 만들어져 위의 offset, kind, 한도, 표기를 줄 수 없습니다. 유효한
문서에는 그것을 감싸고 오류에는 자체 scanner를 두면 하나의 contract 뒤에 parser가 둘이 됩니다.

## 재시도 조건

reader가 첫 잘못된 byte의 byte offset을 보고하고 token 표기를 보존할 때 다시 검토합니다.
