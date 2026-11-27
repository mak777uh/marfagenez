//! D-Q6: численные показатели полюса death-reset (PROP-EXPER-DQ6-20261126-2319 rev2).
//!
//! Q-023 закрыт аналитически: D* ~ x^(-1/2), |dD*/dh| ~ x^(-3/2), T_life ~ x^(1/2), x = 1-h.
//! Этот драйвер меряет числа: плато при h<1, рост при h=1, T_life по событиям reset.
//! Механика как в examples/organ_damage_drift.rs (FINDING-306/307), параметризована.
//!
//! Summary stdout сохраняет прежние пять колонок и добавляет шестую:
//! `h,seed,sample_step,Dbar,events_so_far,control`, где `seed` -- фактический seed
//! 4301..4312, а `control=death-reset|cap|sham`. По умолчанию выводятся только
//! death-reset строки; Dbar по-прежнему округляется до шести знаков.
//!
//! `--events <path>` включает потоковый CSV журнал всех reset-событий для dev-аудита.
//! `--event-histogram <path>` — production-представление: точные global interval
//! counts, сводка reset values и не-криптографический fingerprint последовательности
//! (step, reset value) для проверки yoking. Summary scope=global-only явно отмечает
//! компактный режим. `--histogram-organisms` добавляет per-organism bins для dev-аудита;
//! production не хранит их, чтобы уложиться в диск бюджета. Полный журнал и гистограмма
//! одновременно не запрашиваются.
//!
//! `cap` применяет D=min(D,1) после каждого шага, не отключая death-reset канал.
//! `sham` -- консервативный yoked-контроль: отдельный death-reset прогон того же
//! h/seed задаёт точные шаги, количества и значения resets; sham применяет их к
//! равномерно выбранным без повторов организмам независимым seeded RNG. Отбор не
//! использует D sham-траектории, а duty cycle и распределение reset values совпадают
//! с death-reset точно. Явный matching mode записывается в событийный CSV.
//!
//! `--derivative-neighbors` добавляет h±min(0.00025,(1-h)/4) для h<1 из `--h`,
//! если оба соседа остаются в [0,1]. Производную считает analysis-side по их данным.

use medium_core::organ::aging_mortality;
use medium_core::Rng;
use std::collections::BTreeMap;
use std::error::Error;
use std::fmt::Write as _;
use std::fs::File;
use std::io::{self, BufWriter, Write};

const Q: f64 = 0.5;
const RATE: f64 = 0.01;
const P: f64 = 2.0;
const FLOOR: f64 = 0.0002;
const LAMBDA: f64 = 0.001;
const DELTA: f64 = 0.001;
const DAMAGE_CAP: f64 = 1.0;
const SHAM_RNG_MULTIPLIER: u64 = 0x9e37_79b9_7f4a_7c15;
const SHAM_RNG_INCREMENT: u64 = 0xd1b5_4a32_d192_ed03;

pub const SUMMARY_HEADER: &str = "h,seed,sample_step,Dbar,events_so_far,control";
pub const EVENTS_HEADER: &str = "h,seed,control,matching_mode,event_index,event_step,organism,damage_before,mean_before,reset_value,interval_since_previous,organism_interval";

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Control {
    DeathReset,
    Cap,
    Sham,
}

impl Control {
    fn parse(value: &str) -> Option<Self> {
        match value {
            "death-reset" => Some(Self::DeathReset),
            "cap" => Some(Self::Cap),
            "sham" => Some(Self::Sham),
            _ => None,
        }
    }

    fn label(self) -> &'static str {
        match self {
            Self::DeathReset => "death-reset",
            Self::Cap => "cap",
            Self::Sham => "sham",
        }
    }

    fn matching_mode(self) -> &'static str {
        match self {
            Self::DeathReset => "state-dependent",
            Self::Cap => "state-dependent+cap",
            Self::Sham => "yoked-step-count-value",
        }
    }
}

#[derive(Clone, Debug)]
pub struct ResetEvent {
    pub index: usize,
    pub step: usize,
    pub organism: usize,
    pub damage_before: f64,
    pub mean_before: f64,
    pub reset_value: f64,
    pub interval: usize,
    pub organism_interval: usize,
}

pub trait EventSink {
    fn record(&mut self, event: ResetEvent) -> io::Result<()>;
}

struct CsvEventWriter<W: Write> {
    out: W,
    h: f64,
    seed: u64,
    control: Control,
}

impl<W: Write> CsvEventWriter<W> {
    fn new(mut out: W) -> io::Result<Self> {
        writeln!(out, "{EVENTS_HEADER}")?;
        Ok(Self {
            out,
            h: 0.0,
            seed: 0,
            control: Control::DeathReset,
        })
    }

    fn set_context(&mut self, h: f64, seed: u64, control: Control) {
        self.h = h;
        self.seed = seed;
        self.control = control;
    }
}

impl<W: Write> EventSink for CsvEventWriter<W> {
    fn record(&mut self, event: ResetEvent) -> io::Result<()> {
        // Debug formatting is the shortest round-trip representation of f64.
        writeln!(
            self.out,
            "{},{},{},{},{},{},{},{:?},{:?},{:?},{},{}",
            self.h,
            self.seed,
            self.control.label(),
            self.control.matching_mode(),
            event.index,
            event.step,
            event.organism,
            event.damage_before,
            event.mean_before,
            event.reset_value,
            event.interval,
            event.organism_interval,
        )
    }
}

pub const EVENT_HISTOGRAM_HEADER: &str = "h,seed,control,matching_mode,record_type,scope,organism,interval,count,reset_value_sum,reset_value_sumsq,reset_value_min,reset_value_max,reset_schedule_hash";

/// Exact interval distributions and reset-value moments for one h×seed run.
/// This is the production artifact: unlike a row-per-event CSV, its size depends
/// on the number of distinct intervals, not on millions of reset events.
struct CsvIntervalWriter<W: Write> {
    out: W,
    global: BTreeMap<usize, usize>,
    by_organism: Vec<BTreeMap<usize, usize>>,
    include_organism_bins: bool,
    events: usize,
    reset_sum: f64,
    reset_sumsq: f64,
    reset_min: f64,
    reset_max: f64,
    schedule_hash_a: u64,
    schedule_hash_b: u64,
}

impl<W: Write> CsvIntervalWriter<W> {
    fn new(mut out: W, n: usize, include_organism_bins: bool) -> io::Result<Self> {
        writeln!(out, "{EVENT_HISTOGRAM_HEADER}")?;
        Ok(Self {
            out,
            global: BTreeMap::new(),
            by_organism: vec![BTreeMap::new(); n],
            include_organism_bins,
            events: 0,
            reset_sum: 0.0,
            reset_sumsq: 0.0,
            reset_min: f64::INFINITY,
            reset_max: f64::NEG_INFINITY,
            schedule_hash_a: 0xcbf2_9ce4_8422_2325,
            schedule_hash_b: 0x8422_2325_cbf2_9ce4,
        })
    }

    /// Non-cryptographic 128-bit FNV-1a schedule fingerprint. It lets the
    /// compressed artifact check exact step/reset-value yoking without storing
    /// millions of reset values. Collision resistance is not claimed.
    fn hash_bytes(mut hash: u64, bytes: &[u8]) -> u64 {
        for &byte in bytes {
            hash ^= u64::from(byte);
            hash = hash.wrapping_mul(0x0000_0100_0000_01b3);
        }
        hash
    }

    fn finish(&mut self, h: f64, seed: u64, control: Control) -> io::Result<()> {
        let mode = control.matching_mode();
        let detail_scope = if self.include_organism_bins { "" } else { "global-only" };
        if self.events == 0 {
            writeln!(
                self.out,
                "{h},{seed},{},{mode},summary,{detail_scope},,,0,0,0,0,,",
                control.label()
            )?;
        } else {
            writeln!(
                self.out,
                "{h},{seed},{},{mode},summary,{detail_scope},,,{},{},{:?},{:?},{:?},{:016x}{:016x}",
                control.label(),
                self.events,
                self.reset_sum,
                self.reset_sumsq,
                self.reset_min,
                self.reset_max,
                self.schedule_hash_a,
                self.schedule_hash_b
            )?;
        }
        for (&interval, &count) in &self.global {
            writeln!(
                self.out,
                "{h},{seed},{},{mode},interval,global,,{interval},{count},,,,,",
                control.label()
            )?;
        }
        if self.include_organism_bins {
            for (organism, histogram) in self.by_organism.iter().enumerate() {
                for (&interval, &count) in histogram {
                    writeln!(
                        self.out,
                        "{h},{seed},{},{mode},interval,organism,{organism},{interval},{count},,,,,",
                        control.label()
                    )?;
                }
            }
        }
        self.global.clear();
        for histogram in &mut self.by_organism {
            histogram.clear();
        }
        self.events = 0;
        self.reset_sum = 0.0;
        self.reset_sumsq = 0.0;
        self.reset_min = f64::INFINITY;
        self.reset_max = f64::NEG_INFINITY;
        self.schedule_hash_a = 0xcbf2_9ce4_8422_2325;
        self.schedule_hash_b = 0x8422_2325_cbf2_9ce4;
        Ok(())
    }
}

impl<W: Write> EventSink for CsvIntervalWriter<W> {
    fn record(&mut self, event: ResetEvent) -> io::Result<()> {
        *self.global.entry(event.interval).or_default() += 1;
        if self.include_organism_bins {
            *self.by_organism[event.organism]
                .entry(event.organism_interval)
                .or_default() += 1;
        }
        self.events += 1;
        self.reset_sum += event.reset_value;
        self.reset_sumsq += event.reset_value * event.reset_value;
        self.reset_min = self.reset_min.min(event.reset_value);
        self.reset_max = self.reset_max.max(event.reset_value);
        let step_bytes = (event.step as u64).to_le_bytes();
        let value_bytes = event.reset_value.to_bits().to_le_bytes();
        self.schedule_hash_a = Self::hash_bytes(self.schedule_hash_a, &step_bytes);
        self.schedule_hash_a = Self::hash_bytes(self.schedule_hash_a, &value_bytes);
        self.schedule_hash_b = Self::hash_bytes(self.schedule_hash_b, &step_bytes);
        self.schedule_hash_b = Self::hash_bytes(self.schedule_hash_b, &value_bytes);
        Ok(())
    }
}

struct EventRecorder<'a> {
    sink: Option<&'a mut dyn EventSink>,
    events: usize,
    last_step: usize,
    last_by_organism: Vec<Option<usize>>,
}

impl<'a> EventRecorder<'a> {
    fn new(n: usize, sink: Option<&'a mut dyn EventSink>) -> Self {
        Self {
            sink,
            events: 0,
            last_step: 0,
            last_by_organism: vec![None; n],
        }
    }

    fn reset(
        &mut self,
        step: usize,
        organism: usize,
        damage_before: f64,
        mean_before: f64,
        reset_value: f64,
    ) -> io::Result<()> {
        self.events += 1;
        let event = ResetEvent {
            index: self.events,
            step,
            organism,
            damage_before,
            mean_before,
            reset_value,
            interval: step - self.last_step,
            organism_interval: step - self.last_by_organism[organism].unwrap_or(0),
        };
        self.last_step = step;
        self.last_by_organism[organism] = Some(step);
        if let Some(sink) = self.sink.as_mut() {
            sink.record(event)?;
        }
        Ok(())
    }
}

#[derive(Clone, Copy)]
struct PlannedResetStep {
    step: usize,
    count: usize,
    value: f64,
}

/// Шаги измерений: steps/8, steps/4, steps/2, steps; нулевые шаги отбрасываются,
/// результат сортируется и дедуплицируется. Для 800000 это 100000..800000.
pub fn sample_schedule(steps: usize) -> Vec<usize> {
    let mut out: Vec<usize> = [steps / 8, steps / 4, steps / 2, steps]
        .into_iter()
        .filter(|&step| step > 0 && step <= steps)
        .collect();
    out.sort_unstable();
    out.dedup();
    out
}

/// Шаг центральной производной из task; вычисление самой производной -- analysis-side.
pub fn derivative_step(h: f64) -> f64 {
    0.00025_f64.min((1.0 - h) / 4.0)
}

/// Добавляет соседние h для центральной производной внутри [0,1]; h=1 исключён.
pub fn with_derivative_neighbors(h_values: &[f64]) -> Vec<f64> {
    let mut out = h_values.to_vec();
    for &h in h_values {
        if h > 0.0 && h < 1.0 {
            let step = derivative_step(h);
            let lower = h - step;
            let upper = h + step;
            if lower >= 0.0 && upper <= 1.0 {
                out.push(lower);
                out.push(upper);
            }
        }
    }
    out.sort_by(f64::total_cmp);
    out.dedup();
    out
}

/// Совместимый wrapper: прежний state-dependent death-reset прогон без журнала.
pub fn run(
    h: f64,
    n: usize,
    steps: usize,
    seed: u64,
    sample_steps: &[usize],
) -> (Vec<(usize, f64, usize)>, usize) {
    run_controlled(h, n, steps, seed, Control::DeathReset, sample_steps, None)
        .expect("death-reset run without an event writer cannot fail")
}

/// Один прогон выбранного control. Возвращает (шаг, Dbar, events_so_far) и total events.
pub fn run_controlled(
    h: f64,
    n: usize,
    steps: usize,
    seed: u64,
    control: Control,
    sample_steps: &[usize],
    sink: Option<&mut dyn EventSink>,
) -> io::Result<(Vec<(usize, f64, usize)>, usize)> {
    assert!(n > 0, "n must be positive");

    // Sham сначала получает точный yoked-график из отдельного death-reset прогона.
    // В обычном режиме журнал потоковый; sham держит в памяти только один пункт
    // на шаг с событиями (count + значение), а не отдельную запись на каждый reset.
    let reference = if control == Control::Sham {
        let mut collected = ReferenceSchedule(Vec::new());
        simulate(
            h,
            n,
            steps,
            seed,
            Control::DeathReset,
            &[],
            None,
            Some(&mut collected),
        )?;
        Some(collected.0)
    } else {
        None
    };

    simulate(
        h,
        n,
        steps,
        seed,
        control,
        sample_steps,
        reference.as_deref(),
        sink,
    )
}

#[allow(clippy::too_many_arguments)]
fn simulate(
    h: f64,
    n: usize,
    steps: usize,
    seed: u64,
    control: Control,
    sample_steps: &[usize],
    reference: Option<&[PlannedResetStep]>,
    sink: Option<&mut dyn EventSink>,
) -> io::Result<(Vec<(usize, f64, usize)>, usize)> {
    let mut rng = Rng::new(seed);
    let mut target_rng = Rng::new(
        seed.wrapping_mul(SHAM_RNG_MULTIPLIER)
            .wrapping_add(SHAM_RNG_INCREMENT),
    );
    let mut damage = vec![0.0_f64; n];
    let mut recorder = EventRecorder::new(n, sink);
    let mut out = Vec::new();
    let mut si = 0_usize;
    let mut reference_index = 0_usize;

    for step in 1..=steps {
        let mean = damage.iter().sum::<f64>() / n as f64;
        match control {
            Control::DeathReset | Control::Cap => {
                for organism in 0..n {
                    let before = damage[organism];
                    let mu = aging_mortality(Q, RATE, P, FLOOR, LAMBDA, before);
                    let survive = (-mu).exp();
                    if rng.uniform() > survive {
                        let reset_value = h * mean;
                        damage[organism] = reset_value;
                        recorder.reset(step, organism, before, mean, reset_value)?;
                    } else {
                        damage[organism] += DELTA;
                    }
                }
                if control == Control::Cap {
                    for d in damage.iter_mut() {
                        *d = d.min(DAMAGE_CAP);
                    }
                }
            }
            Control::Sham => {
                let reference = reference.expect("sham requires a yoked reference schedule");
                let (count, reset_value) = reference
                    .get(reference_index)
                    .filter(|planned| planned.step == step)
                    .map(|planned| {
                        reference_index += 1;
                        (planned.count, planned.value)
                    })
                    .unwrap_or((0, 0.0));
                let targets = uniform_targets(n, count, &mut target_rng);
                let before: Vec<f64> = targets.iter().map(|&organism| damage[organism]).collect();

                // Exogenous resets replace, rather than supplement, state-dependent resets.
                for d in damage.iter_mut() {
                    *d += DELTA;
                }
                for (organism, before) in targets.into_iter().zip(before) {
                    damage[organism] = reset_value;
                    recorder.reset(step, organism, before, mean, reset_value)?;
                }
            }
        }

        while si < sample_steps.len() && step == sample_steps[si] {
            let dbar = damage.iter().sum::<f64>() / n as f64;
            out.push((step, dbar, recorder.events));
            si += 1;
        }
    }
    debug_assert!(reference.is_none() || reference_index == reference.unwrap().len());
    Ok((out, recorder.events))
}

/// Первые count индексов равномерной перестановки без повторов; D не передаётся.
fn uniform_targets(n: usize, count: usize, rng: &mut Rng) -> Vec<usize> {
    let count = count.min(n);
    let mut indices: Vec<usize> = (0..n).collect();
    for i in 0..count {
        let remaining = n - i;
        let j = i + (rng.uniform() * remaining as f64).floor() as usize;
        let j = j.min(n - 1);
        indices.swap(i, j);
    }
    indices.truncate(count);
    indices
}

struct ReferenceSchedule(Vec<PlannedResetStep>);

impl EventSink for ReferenceSchedule {
    fn record(&mut self, event: ResetEvent) -> io::Result<()> {
        if let Some(last) = self.0.last_mut().filter(|last| last.step == event.step) {
            debug_assert_eq!(last.value.to_bits(), event.reset_value.to_bits());
            last.count += 1;
        } else {
            self.0.push(PlannedResetStep {
                step: event.step,
                count: 1,
                value: event.reset_value,
            });
        }
        Ok(())
    }
}

#[cfg(test)]
struct CollectedEvents(Vec<ResetEvent>);

#[cfg(test)]
impl EventSink for CollectedEvents {
    fn record(&mut self, event: ResetEvent) -> io::Result<()> {
        self.0.push(event);
        Ok(())
    }
}

fn summary_row(
    h: f64,
    seed: u64,
    control: Control,
    step: usize,
    dbar: f64,
    events: usize,
) -> String {
    let mut row = String::new();
    writeln!(
        row,
        "{h},{seed},{step},{dbar:.6},{events},{}",
        control.label()
    )
    .expect("writing to String cannot fail");
    row
}

fn main() -> Result<(), Box<dyn Error>> {
    let args: Vec<String> = std::env::args().collect();
    let mut h_list = vec![0.99_f64, 0.995, 0.998, 0.999, 0.9995];
    let mut controls = vec![0.9_f64, 0.95, 0.98, 1.0];
    let mut n = 100_usize;
    let mut steps = 800_000_usize;
    let mut seed_base = 4301_u64;
    let mut seeds = 12_usize;
    let mut control = Control::DeathReset;
    let mut events_path: Option<String> = None;
    let mut event_histogram_path: Option<String> = None;
    let mut include_histogram_organisms = false;
    let mut derivative_neighbors = false;
    let mut i = 1;
    while i < args.len() {
        match args[i].as_str() {
            "--h" => {
                i += 1;
                h_list = args[i].split(',').filter_map(|s| s.parse().ok()).collect();
            }
            "--controls" => {
                i += 1;
                controls = args[i].split(',').filter_map(|s| s.parse().ok()).collect();
            }
            "--n" => {
                i += 1;
                n = args[i].parse().unwrap();
            }
            "--steps" => {
                i += 1;
                steps = args[i].parse().unwrap();
            }
            "--seed-base" => {
                i += 1;
                seed_base = args[i].parse().unwrap();
            }
            "--seeds" => {
                i += 1;
                seeds = args[i].parse().unwrap();
            }
            "--control" => {
                i += 1;
                control = Control::parse(&args[i]).unwrap_or_else(|| {
                    eprintln!("--control must be death-reset, cap, or sham");
                    std::process::exit(2);
                });
            }
            "--events" => {
                i += 1;
                events_path = Some(args[i].clone());
            }
            "--event-histogram" => {
                i += 1;
                event_histogram_path = Some(args[i].clone());
            }
            "--histogram-organisms" => include_histogram_organisms = true,
            "--derivative-neighbors" => derivative_neighbors = true,
            other => {
                eprintln!("unknown arg: {other}");
                std::process::exit(2);
            }
        }
        i += 1;
    }
    if n == 0 || steps == 0 {
        eprintln!("--n and --steps must be positive");
        std::process::exit(2);
    }
    if events_path.is_some() && event_histogram_path.is_some() {
        eprintln!("--events and --event-histogram are mutually exclusive");
        std::process::exit(2);
    }
    if h_list
        .iter()
        .chain(controls.iter())
        .any(|h| !h.is_finite() || !(0.0..=1.0).contains(h))
    {
        eprintln!("--h and --controls values must be finite and in [0,1]");
        std::process::exit(2);
    }
    if derivative_neighbors {
        h_list = with_derivative_neighbors(&h_list);
    }
    let sample_steps = sample_schedule(steps);

    let mut event_file = events_path.as_ref().map(File::create).transpose()?;
    let mut event_writer = event_file
        .as_mut()
        .map(|file| CsvEventWriter::new(BufWriter::new(file)))
        .transpose()?;
    let mut histogram_file = event_histogram_path.as_ref().map(File::create).transpose()?;
    let mut histogram_writer = histogram_file
        .as_mut()
        .map(|file| CsvIntervalWriter::new(BufWriter::new(file), n, include_histogram_organisms))
        .transpose()?;

    println!("{SUMMARY_HEADER}");
    for &h in h_list.iter().chain(controls.iter()) {
        for s in 0..seeds {
            let seed = seed_base + s as u64;
            let (rows, _events) = if let Some(writer) = histogram_writer.as_mut() {
                let result = run_controlled(
                    h,
                    n,
                    steps,
                    seed,
                    control,
                    &sample_steps,
                    Some(writer),
                )?;
                writer.finish(h, seed, control)?;
                result
            } else {
                if let Some(writer) = event_writer.as_mut() {
                    writer.set_context(h, seed, control);
                }
                let sink = event_writer
                    .as_mut()
                    .map(|writer| writer as &mut dyn EventSink);
                run_controlled(h, n, steps, seed, control, &sample_steps, sink)?
            };
            for (step, dbar, ev) in rows {
                print!("{}", summary_row(h, seed, control, step, dbar, ev));
            }
        }
    }
    if let Some(writer) = event_writer.as_mut() {
        writer.out.flush()?;
    }
    if let Some(writer) = histogram_writer.as_mut() {
        writer.out.flush()?;
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn sample_schedule_is_eighth_quarter_half_full_and_deduplicated() {
        assert_eq!(
            sample_schedule(800_000),
            vec![100_000, 200_000, 400_000, 800_000]
        );
        assert_eq!(sample_schedule(7), vec![1, 3, 7]);
        assert_eq!(sample_schedule(1), vec![1]);
        assert_eq!(sample_schedule(0), Vec::<usize>::new());
    }

    #[test]
    fn derivative_neighbors_use_task_step_and_exclude_h_one() {
        assert_eq!(derivative_step(0.99), 0.00025);
        assert!((derivative_step(0.9995) - 0.000125).abs() < 1e-15);
        let expanded = with_derivative_neighbors(&[0.9995, 1.0]);
        assert_eq!(expanded.len(), 4);
        assert!(expanded.iter().any(|&h| (h - 0.9995).abs() < 1e-15));
        assert!(expanded.iter().any(|&h| (h - 0.999375).abs() < 1e-15));
        assert!(expanded.iter().any(|&h| (h - 0.999625).abs() < 1e-15));
        assert!(expanded.contains(&1.0));
        assert!(expanded.iter().all(|&h| h <= 1.0));
        assert_eq!(with_derivative_neighbors(&[0.00001]), vec![0.00001]);
    }

    #[test]
    fn summary_is_additive_and_seed_marker_is_actual() {
        assert_eq!(
            SUMMARY_HEADER,
            "h,seed,sample_step,Dbar,events_so_far,control"
        );
        let row = summary_row(0.99, 4312, Control::DeathReset, 800_000, 4.0, 123);
        assert_eq!(row, "0.99,4312,800000,4.000000,123,death-reset\n");
        let seeds: Vec<u64> = (0..12).map(|s| 4301 + s as u64).collect();
        assert_eq!(seeds.first(), Some(&4301));
        assert_eq!(seeds.last(), Some(&4312));
    }

    #[test]
    fn default_run_preserves_base_dynamics() {
        // Golden values from the committed base driver; only its schedule/seed marker change.
        let (rows, events) = run(0.99, 20, 5_000, 3, &[1_250, 2_500, 5_000]);
        assert_eq!(
            rows.iter().map(|row| row.0).collect::<Vec<_>>(),
            vec![1_250, 2_500, 5_000]
        );
        assert_eq!(
            rows.iter().map(|row| row.2).collect::<Vec<_>>(),
            vec![91, 207, 502]
        );
        for (row, expected) in rows.iter().zip([1.212545_f64, 2.332384, 4.311709]) {
            assert!(
                (row.1 - expected).abs() < 5e-7,
                "base drift changed: {row:?}"
            );
        }
        assert_eq!(events, 502);
    }

    #[test]
    fn plateau_at_h_below_one() {
        let steps = 60_000_usize;
        let (rows, _) = run(0.9, 100, steps, 7, &[steps / 2, steps]);
        let (d_mid, d_end) = (rows[0].1, rows[1].1);
        assert!(d_end > 0.0, "no damage accumulated");
        assert!(
            d_end - d_mid <= 0.05 * d_end.max(0.01),
            "no plateau: {d_mid} -> {d_end}"
        );
    }

    #[test]
    fn death_reset_grows_at_h_one() {
        let steps = 60_000_usize;
        let (rows9, _) = run(0.9, 100, steps, 7, &[steps]);
        let (rows1, _) = run(1.0, 100, steps, 7, &[steps]);
        assert!(
            rows1[0].1 > 2.0 * rows9[0].1,
            "h=1.0 must outgrow h=0.9: {} vs {}",
            rows1[0].1,
            rows9[0].1
        );
    }

    #[test]
    fn cap_at_h_one_bounds_damage_and_returns_to_plateau() {
        let steps = 60_000_usize;
        let schedule = sample_schedule(steps);
        let (uncapped, _) = run(1.0, 100, steps, 7, &schedule);
        let (capped, _) =
            run_controlled(1.0, 100, steps, 7, Control::Cap, &schedule, None).unwrap();
        assert!(
            uncapped.last().unwrap().1 > DAMAGE_CAP,
            "control did not fire: {:?}",
            uncapped.last()
        );
        assert!(
            capped.iter().all(|row| row.1 <= DAMAGE_CAP),
            "cap exceeded: {capped:?}"
        );
        assert!(
            capped.last().unwrap().1 < uncapped.last().unwrap().1,
            "cap did not reduce divergence"
        );
        let d_mid = capped[1].1;
        let d_end = capped[2].1;
        assert!(
            d_end - d_mid <= 0.05 * d_end.max(0.01),
            "cap has no plateau: {d_mid} -> {d_end}"
        );
    }

    #[test]
    fn deterministic_by_seed_for_every_control() {
        for control in [Control::DeathReset, Control::Cap, Control::Sham] {
            let a = run_controlled(0.995, 30, 4_000, 11, control, &[1_000, 4_000], None).unwrap();
            let b = run_controlled(0.995, 30, 4_000, 11, control, &[1_000, 4_000], None).unwrap();
            assert_eq!(a.0, b.0, "{control:?} summary differs");
            assert_eq!(a.1, b.1, "{control:?} event count differs");
        }
    }

    #[test]
    fn event_journal_preserves_reset_geometry_intervals_and_counts() {
        let h = 0.99;
        let schedule = [625, 1_250, 2_500, 5_000];
        let mut events = CollectedEvents(Vec::new());
        let (rows, total) = run_controlled(
            h,
            20,
            5_000,
            3,
            Control::DeathReset,
            &schedule,
            Some(&mut events),
        )
        .unwrap();
        assert_eq!(total, 502);
        assert_eq!(events.0.len(), total);
        let mut previous_step = 0;
        let mut previous_by_organism = vec![0_usize; 20];
        for (i, event) in events.0.iter().enumerate() {
            assert_eq!(event.index, i + 1);
            assert_eq!(event.interval, event.step - previous_step);
            assert_eq!(
                event.organism_interval,
                event.step - previous_by_organism[event.organism]
            );
            assert_eq!(
                event.reset_value.to_bits(),
                (h * event.mean_before).to_bits()
            );
            previous_step = event.step;
            previous_by_organism[event.organism] = event.step;
        }
        for row in rows {
            let count = events.0.iter().filter(|event| event.step <= row.0).count();
            assert_eq!(row.2, count);
        }
    }

    #[test]
    fn sham_exactly_yokes_steps_counts_intervals_and_reset_values() {
        let h = 0.999;
        let schedule = [1_000, 2_000, 4_000];
        let mut reference = CollectedEvents(Vec::new());
        let (reference_rows, reference_total) = run_controlled(
            h,
            20,
            4_000,
            4312,
            Control::DeathReset,
            &schedule,
            Some(&mut reference),
        )
        .unwrap();
        let mut sham = CollectedEvents(Vec::new());
        let (sham_rows, sham_total) = run_controlled(
            h,
            20,
            4_000,
            4312,
            Control::Sham,
            &schedule,
            Some(&mut sham),
        )
        .unwrap();
        assert!(reference_total > 0);
        assert_eq!(Control::Sham.matching_mode(), "yoked-step-count-value");
        assert_eq!(sham_total, reference_total);
        assert_eq!(
            sham_rows.iter().map(|row| row.2).collect::<Vec<_>>(),
            reference_rows.iter().map(|row| row.2).collect::<Vec<_>>()
        );
        assert_eq!(sham.0.len(), reference.0.len());
        for (sham_event, reference_event) in sham.0.iter().zip(&reference.0) {
            assert_eq!(sham_event.step, reference_event.step);
            assert_eq!(sham_event.interval, reference_event.interval);
            assert_eq!(
                sham_event.reset_value.to_bits(),
                reference_event.reset_value.to_bits()
            );
        }
    }

    #[test]
    fn sham_target_selection_is_seeded_without_replacement() {
        let mut a = Rng::new(4312);
        let mut b = Rng::new(4312);
        let first = uniform_targets(20, 12, &mut a);
        let second = uniform_targets(20, 12, &mut b);
        assert_eq!(first, second);
        assert_eq!(first.len(), 12);
        let mut unique = first.clone();
        unique.sort_unstable();
        unique.dedup();
        assert_eq!(unique.len(), first.len());
        assert!(first.iter().all(|&organism| organism < 20));
    }

    #[test]
    fn interval_histogram_is_exact_and_matches_event_journal() {
        let h = 0.99;
        let n = 20_usize;
        let steps = 5_000_usize;
        let seed = 4301_u64;
        let schedule = [625, 1_250, 2_500, 5_000];
        let mut journal = CollectedEvents(Vec::new());
        let (_, total) = run_controlled(
            h,
            n,
            steps,
            seed,
            Control::DeathReset,
            &schedule,
            Some(&mut journal),
        )
        .unwrap();
        let mut writer = CsvIntervalWriter::new(Vec::<u8>::new(), n, true).unwrap();
        run_controlled(
            h,
            n,
            steps,
            seed,
            Control::DeathReset,
            &schedule,
            Some(&mut writer),
        )
        .unwrap();
        writer.finish(h, seed, Control::DeathReset).unwrap();
        let csv = String::from_utf8(writer.out).unwrap();

        let mut expected_global = BTreeMap::<usize, usize>::new();
        let mut expected_organism = vec![BTreeMap::<usize, usize>::new(); n];
        let mut expected_sum = 0.0_f64;
        let mut expected_sumsq = 0.0_f64;
        let mut expected_min = f64::INFINITY;
        let mut expected_max = f64::NEG_INFINITY;
        let mut expected_hash_a = 0xcbf2_9ce4_8422_2325_u64;
        let mut expected_hash_b = 0x8422_2325_cbf2_9ce4_u64;
        for event in &journal.0 {
            *expected_global.entry(event.interval).or_default() += 1;
            *expected_organism[event.organism]
                .entry(event.organism_interval)
                .or_default() += 1;
            expected_sum += event.reset_value;
            expected_sumsq += event.reset_value * event.reset_value;
            expected_min = expected_min.min(event.reset_value);
            expected_max = expected_max.max(event.reset_value);
            let step_bytes = (event.step as u64).to_le_bytes();
            let value_bytes = event.reset_value.to_bits().to_le_bytes();
            expected_hash_a = CsvIntervalWriter::<Vec<u8>>::hash_bytes(expected_hash_a, &step_bytes);
            expected_hash_a = CsvIntervalWriter::<Vec<u8>>::hash_bytes(expected_hash_a, &value_bytes);
            expected_hash_b = CsvIntervalWriter::<Vec<u8>>::hash_bytes(expected_hash_b, &step_bytes);
            expected_hash_b = CsvIntervalWriter::<Vec<u8>>::hash_bytes(expected_hash_b, &value_bytes);
        }

        let mut lines = csv.lines();
        assert_eq!(lines.next(), Some(EVENT_HISTOGRAM_HEADER));
        let summary = lines.next().unwrap().split(',').collect::<Vec<_>>();
        assert_eq!(summary.len(), 14);
        assert_eq!(summary[4], "summary");
        assert_eq!(summary[8].parse::<usize>().unwrap(), total);
        assert_eq!(summary[9].parse::<f64>().unwrap().to_bits(), expected_sum.to_bits());
        assert_eq!(
            summary[10].parse::<f64>().unwrap().to_bits(),
            expected_sumsq.to_bits()
        );
        assert_eq!(
            summary[11].parse::<f64>().unwrap().to_bits(),
            expected_min.to_bits()
        );
        assert_eq!(
            summary[12].parse::<f64>().unwrap().to_bits(),
            expected_max.to_bits()
        );
        assert_eq!(summary[13], format!("{expected_hash_a:016x}{expected_hash_b:016x}"));

        let mut actual_global = BTreeMap::<usize, usize>::new();
        let mut actual_organism = vec![BTreeMap::<usize, usize>::new(); n];
        for line in lines {
            let fields = line.split(',').collect::<Vec<_>>();
            assert_eq!(fields.len(), 14);
            assert_eq!(fields[4], "interval");
            let interval = fields[7].parse::<usize>().unwrap();
            let count = fields[8].parse::<usize>().unwrap();
            if fields[5] == "global" {
                *actual_global.entry(interval).or_default() += count;
            } else {
                assert_eq!(fields[5], "organism");
                let organism = fields[6].parse::<usize>().unwrap();
                *actual_organism[organism].entry(interval).or_default() += count;
            }
        }
        assert_eq!(actual_global, expected_global);
        assert_eq!(actual_organism, expected_organism);
        assert_eq!(
            actual_global.values().sum::<usize>(),
            journal.0.len()
        );
    }

    #[test]
    fn compact_histogram_keeps_global_intervals_and_explicit_detail_contract() {
        let n = 20_usize;
        let schedule = [1_000, 2_000, 4_000];
        let mut detailed = CsvIntervalWriter::new(Vec::<u8>::new(), n, true).unwrap();
        let mut compact = CsvIntervalWriter::new(Vec::<u8>::new(), n, false).unwrap();
        for writer in [&mut detailed, &mut compact] {
            run_controlled(0.999, n, 4_000, 4312, Control::DeathReset, &schedule, Some(writer)).unwrap();
            writer.finish(0.999, 4312, Control::DeathReset).unwrap();
        }
        let global_lines = |csv: String| -> Vec<String> {
            csv.lines().filter(|line| line.contains(",interval,global,")).map(str::to_owned).collect()
        };
        assert_eq!(global_lines(String::from_utf8(detailed.out).unwrap()),
                   global_lines(String::from_utf8(compact.out.clone()).unwrap()));
        let compact = String::from_utf8(compact.out).unwrap();
        assert!(compact.lines().nth(1).unwrap().contains(",summary,global-only,,,"));
        assert!(!compact.contains(",interval,organism,"));
        assert!(compact.lines().all(|line| line.split(',').count() == 14));
    }

    #[test]
    fn interval_histogram_schedule_hash_verifies_sham_yoking() {
        let h = 0.999;
        let n = 20_usize;
        let steps = 4_000_usize;
        let seed = 4312_u64;
        let schedule = [1_000, 2_000, 4_000];
        let mut hashes = Vec::new();
        for control in [Control::DeathReset, Control::Sham] {
            let mut writer = CsvIntervalWriter::new(Vec::<u8>::new(), n, true).unwrap();
            run_controlled(h, n, steps, seed, control, &schedule, Some(&mut writer)).unwrap();
            writer.finish(h, seed, control).unwrap();
            let csv = String::from_utf8(writer.out).unwrap();
            let summary = csv.lines().nth(1).unwrap().split(',').collect::<Vec<_>>();
            assert_eq!(summary.len(), 14);
            hashes.push((
                summary[8].to_owned(),
                summary[9].to_owned(),
                summary[10].to_owned(),
                summary[13].to_owned(),
            ));
        }
        assert_eq!(hashes[0], hashes[1], "compressed sham schedule differs");
    }

    #[test]
    fn interval_histogram_empty_run_has_explicit_zero_summary() {
        let mut writer = CsvIntervalWriter::new(Vec::<u8>::new(), 3, false).unwrap();
        writer.finish(0.99, 4312, Control::Sham).unwrap();
        let csv = String::from_utf8(writer.out).unwrap();
        let mut lines = csv.lines();
        assert_eq!(lines.next(), Some(EVENT_HISTOGRAM_HEADER));
        assert_eq!(
            lines.next(),
            Some("0.99,4312,sham,yoked-step-count-value,summary,global-only,,,0,0,0,0,,")
        );
        assert!(lines.next().is_none());
    }

    #[test]
    fn event_csv_has_explicit_control_and_matching_contract() {
        let mut writer = CsvEventWriter::new(Vec::<u8>::new()).unwrap();
        writer.set_context(1.0, 4301, Control::Cap);
        run_controlled(
            1.0,
            20,
            5_000,
            4301,
            Control::Cap,
            &[5_000],
            Some(&mut writer),
        )
        .unwrap();
        let csv = String::from_utf8(writer.out).unwrap();
        let mut lines = csv.lines();
        assert_eq!(lines.next(), Some(EVENTS_HEADER));
        let mut event_count = 0;
        for line in lines {
            let fields: Vec<&str> = line.split(',').collect();
            assert_eq!(fields.len(), 12);
            assert_eq!(fields[1], "4301");
            assert_eq!(fields[2], "cap");
            assert_eq!(fields[3], "state-dependent+cap");
            assert!(fields[9].parse::<f64>().unwrap() <= DAMAGE_CAP);
            event_count += 1;
        }
        assert!(event_count > 0);
    }
}
