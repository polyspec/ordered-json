use ordered_json::{parse_bytes, stringify};
use serde_json::Value as NativeValue;
use sha2::{Digest, Sha256};
use std::{env, fs, hint::black_box, time::Instant};

fn iterations() -> usize {
    env::var("OJ_BENCH_ITERATIONS")
        .ok()
        .and_then(|value| value.parse().ok())
        .filter(|value| *value > 0)
        .unwrap_or(1000)
}

fn measure<F: FnMut() -> Vec<u8>>(mut f: F, count: usize) -> (f64, Vec<u8>) {
    let start = Instant::now();
    let mut output = Vec::new();
    for _ in 0..count {
        output = f();
    }
    (start.elapsed().as_secs_f64() * 1e9 / count as f64, output)
}

fn digest(bytes: &[u8]) -> String {
    let mut hasher = Sha256::new();
    hasher.update(bytes);
    format!("{:x}", hasher.finalize())
}

fn main() {
    let count = iterations();
    for file in env::args().skip(1) {
        let source = fs::read(&file).expect("cannot read benchmark fixture");
        let parse_ordered = || parse_bytes(&source).expect("ordered-json parse failed");
        let (parse_ns, _) = measure(
            || {
                black_box(parse_ordered());
                Vec::new()
            },
            count,
        );
        let value = parse_ordered();
        let (stringify_ns, output) = measure(|| stringify(&value).into_bytes(), count);
        let (roundtrip_ns, _) = measure(|| stringify(&parse_ordered()).into_bytes(), count);

        let (native_parse_ns, _) = measure(
            || {
                serde_json::from_slice::<NativeValue>(&source).unwrap();
                Vec::new()
            },
            count,
        );
        let native_value: NativeValue = serde_json::from_slice(&source).unwrap();
        let (native_stringify_ns, native_output) =
            measure(|| serde_json::to_vec(&native_value).unwrap(), count);
        let (native_roundtrip_ns, _) = measure(
            || {
                let value: NativeValue = serde_json::from_slice(&source).unwrap();
                serde_json::to_vec(&value).unwrap()
            },
            count,
        );
        println!(
            "{file}\tordered-json\t{parse_ns}\t{stringify_ns}\t{roundtrip_ns}\t{}\t{}\t{}",
            digest(&output), source.len(), output.len()
        );
        println!(
            "{file}\tnative-json\t{native_parse_ns}\t{native_stringify_ns}\t{native_roundtrip_ns}\t{}\t{}\t{}",
            digest(&native_output), source.len(), native_output.len()
        );
    }
}
