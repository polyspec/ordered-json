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

struct Stats {
    median: f64,
    p95: f64,
    samples: Vec<f64>,
}
fn setting(name: &str, fallback: usize) -> usize {
    env::var(name)
        .ok()
        .and_then(|v| v.parse().ok())
        .filter(|v| *v > 0)
        .unwrap_or(fallback)
}
fn measure<F: FnMut() -> Vec<u8>>(
    mut f: F,
    count: usize,
    warmup: usize,
    sample_count: usize,
) -> (Stats, Vec<u8>) {
    for _ in 0..warmup {
        f();
    }
    let mut values = Vec::with_capacity(sample_count);
    let mut output = Vec::new();
    for _ in 0..sample_count {
        let start = Instant::now();
        for _ in 0..count {
            output = f();
        }
        values.push(start.elapsed().as_secs_f64() * 1e9 / count as f64);
    }
    values.sort_by(f64::total_cmp);
    let p95 = values[((values.len() as f64 * 0.95).ceil() as usize)
        .saturating_sub(1)
        .min(values.len() - 1)];
    let median = values[values.len() / 2];
    (
        Stats {
            median,
            p95,
            samples: values,
        },
        output,
    )
}

fn digest(bytes: &[u8]) -> String {
    let mut hasher = Sha256::new();
    hasher.update(bytes);
    format!("{:x}", hasher.finalize())
}

fn main() {
    let count = iterations();
    let warmup = setting("OJ_BENCH_WARMUP", 1000);
    let sample_count = setting("OJ_BENCH_SAMPLES", 9);
    for file in env::args().skip(1) {
        let source = fs::read(&file).expect("cannot read benchmark fixture");
        let parse_ordered = || parse_bytes(&source).expect("ordered-json parse failed");
        let (parse_stats, _) = measure(
            || {
                black_box(parse_ordered());
                Vec::new()
            },
            count,
            warmup,
            sample_count,
        );
        let value = parse_ordered();
        let (stringify_stats, output) = measure(
            || stringify(&value).into_bytes(),
            count,
            warmup,
            sample_count,
        );
        let (roundtrip_stats, _) = measure(
            || stringify(&parse_ordered()).into_bytes(),
            count,
            warmup,
            sample_count,
        );

        let (native_parse_stats, _) = measure(
            || {
                serde_json::from_slice::<NativeValue>(&source).unwrap();
                Vec::new()
            },
            count,
            warmup,
            sample_count,
        );
        let native_value: NativeValue = serde_json::from_slice(&source).unwrap();
        let (native_stringify_stats, native_output) = measure(
            || serde_json::to_vec(&native_value).unwrap(),
            count,
            warmup,
            sample_count,
        );
        let (native_roundtrip_stats, _) = measure(
            || {
                let value: NativeValue = serde_json::from_slice(&source).unwrap();
                serde_json::to_vec(&value).unwrap()
            },
            count,
            warmup,
            sample_count,
        );
        let sample_json = |p: &Stats, s: &Stats, r: &Stats| {
            serde_json::json!({"parse": p.samples, "stringify": s.samples, "roundtrip": r.samples})
                .to_string()
        };
        let ordered_samples = sample_json(&parse_stats, &stringify_stats, &roundtrip_stats);
        let native_samples = sample_json(
            &native_parse_stats,
            &native_stringify_stats,
            &native_roundtrip_stats,
        );
        println!(
            "{file}\tordered-json\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}",
            parse_stats.median,
            stringify_stats.median,
            roundtrip_stats.median,
            parse_stats.p95,
            stringify_stats.p95,
            roundtrip_stats.p95,
            ordered_samples,
            digest(&output),
            source.len(),
            output.len()
        );
        println!(
            "{file}\tnative-json\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}",
            native_parse_stats.median,
            native_stringify_stats.median,
            native_roundtrip_stats.median,
            native_parse_stats.p95,
            native_stringify_stats.p95,
            native_roundtrip_stats.p95,
            native_samples,
            digest(&native_output),
            source.len(),
            native_output.len()
        );
    }
}
