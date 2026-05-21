# Testing policy

## The failure mode this addresses

Scientific analysis pipelines do not usually fail by crashing. Crashes are caught immediately. They fail by producing plausible-looking but wrong results: a channel-mapping swap that produces a sensible template plot at the wrong location, an off-by-one in segment indexing that drops one spike per segment, a sign flip in MAD that makes everything appear saturated, a sampling-rate confusion that compresses time by 22%. These errors are silent and propagate through entire pipelines undetected.

Tests exist to catch this class of error. The test suite is not a check on correctness of `if` statements; it is a check on whether the code does what its name says it does.

## Three tiers, ordered by value

### Tier 1: synthetic-data tests for core algorithms

For each algorithm in `quality/`, `sorting/`, and `io/`, write a test that builds synthetic data with known properties and verifies the algorithm recovers them.

Concrete examples for this project:

- **Threshold-crossing detector.** Inject N spikes at known amplitudes into white noise of known std. Verify N crossings detected at the right threshold factor. Verify polarity (negative-going by extracellular convention).
- **MAD noise estimator.** Pure Gaussian noise of known std. `MAD * 1.4826` should approximate std within a tolerance of a few percent.
- **Probe geometry parsing.** Parse a synthetic `.cmp` file with handcrafted electrode/bank assignments. Verify electrode IDs compute correctly via `(bank - 'A') * 32 + elec`.
- **Channel mapping validation.** Given a recording with channel_ids `['3', '1', '2']` and a probe with electrode IDs `[1, 2, 3]`, verify the mapping function correctly identifies the permutation.
- **Segment filtering.** Given a recording with segments of `[2 s, 180 s, 60 s]` and the 5 s threshold, verify the kept indices are `[1, 2]` and the dropped index is `[0]`.

Tier 1 tests are written for every module promoted from `notebooks/scratch/` to `src/`. They pay back forever; the cost of writing them is small relative to the cost of one silent error.

### Tier 2: invariant checks

Properties that must hold regardless of input, embedded as `assert` statements in pipeline code or as light pytest tests.

Examples:

- After loading a recording with a probe attached, `recording.get_num_channels() == probe.get_contact_count()`.
- Crossings at threshold `5 x MAD` are less than or equal to crossings at threshold `4 x MAD` (monotonic).
- After segment filtering, all kept segments have duration above the policy threshold.
- Per-unit assigned electrode (from `chN#U` name in nev) matches the electrode with peak template amplitude. This last one is real scientific validation, not just a software test; it catches Plexon-to-SI channel mapping errors that no synthetic test would find, because it operates on real data and on the chain end-to-end.

Invariants are cheap and catch a lot. They run on real data, not synthetic, so they validate the chain end-to-end rather than the algorithm in isolation. Treat them as a complement to Tier 1, not a substitute.

### Tier 3: regression / snapshot tests at milestones

Once the pipeline runs end-to-end on the demo session, store key outputs (unit count, mean MAD per channel, template peak amplitudes for a handful of units) in a fixture file. A regression test loads the fixture and verifies current outputs match within tolerance.

Catches "I refactored and changed behavior I didn't intend to change." Write only at milestones, not per session. Update the fixture when an intended behavior change occurs, and note the update in the corresponding session_plan.

Milestones to target:

- After threshold-crossing module is stable on the demo session.
- After one full sorter run is stable end-to-end.
- After multi-sorter consensus produces a reproducible agreement matrix on the demo session.
- Before scaling to the longitudinal cohort.

## What not to test

- **SpikeInterface itself.** SI has its own test suite. Do not duplicate.
- **Plotting code.** Visual outputs are validated by eye, against the validation figures from session 2 onward.
- **Trivial glue code.** Tests should cover logic, not plumbing. A function that calls `recording.get_traces()` and returns the result does not need a test.

## When to write tests

- Tier 1 tests ship with the code being promoted to `src/`, not after. The PR that adds the module also adds the test.
- Tier 2 invariants are embedded throughout, both as runtime `assert` statements in pipeline code and as light tests in `tests/`.
- Tier 3 regression tests are written at the milestones above. Each new milestone adds one fixture, not many.

## File layout and execution

- Test files: `tests/test_<module>.py`. One test file per source module is the default; split if test files exceed ~300 lines.
- Synthetic data generators: `tests/fixtures/synthetic.py` for shared generators (white noise + injected events, synthetic `.cmp` files, etc.).
- Regression snapshots: `tests/snapshots/<milestone>/` as NPZ or JSON files. Treat as data; check into git if small (< 1 MB), Git-LFS or external storage if larger.
- Run all tests: `pytest tests/ -x` (stop on first failure during development).
- Run one module: `pytest tests/test_threshold_crossing.py -v`.
- Run only fast tests in CI: `pytest tests/ -m "not slow"` (use the `slow` marker from `pyproject.toml`).

## A worked example: threshold-crossing detector

```python
# tests/test_threshold_crossing.py
import numpy as np
import pytest
from recqual.quality.threshold_crossing import detect_crossings

def test_detects_known_events_above_threshold():
    """White noise plus injected events at -6x MAD. Detector must find them."""
    rng = np.random.default_rng(seed=42)  # rng: seeded generator for reproducibility
    fs = 30000                            # fs: sampling rate, Hz
    n_samples = fs * 10                   # 10 s of synthetic data

    # Pure Gaussian noise, std = 10 uV. Then inject 50 events at -60 uV.
    noise: np.ndarray = rng.normal(0, 10, n_samples).astype(np.float32)
    event_times = rng.integers(100, n_samples - 100, size=50)  # avoid edges
    signal = noise.copy()
    signal[event_times] = -60.0  # negative-going by extracellular convention

    crossings = detect_crossings(signal, fs=fs, threshold_factor=4.0)

    # All 50 events should be detected (with margin for rare double-counts at edges)
    assert 48 <= len(crossings) <= 52


def test_monotonic_in_threshold_factor():
    """Stricter threshold returns equal or fewer crossings. Invariant."""
    rng = np.random.default_rng(seed=42)
    signal = rng.normal(0, 10, 30000 * 10).astype(np.float32)

    c4 = detect_crossings(signal, fs=30000, threshold_factor=4.0)
    c5 = detect_crossings(signal, fs=30000, threshold_factor=5.0)
    c6 = detect_crossings(signal, fs=30000, threshold_factor=6.0)

    assert len(c4) >= len(c5) >= len(c6)
```

These two tests together cover (1) the algorithm recovers known ground truth and (2) an invariant that must hold. The cost is roughly 30 lines and runs in under a second. The benefit is that any future change to `detect_crossings` that breaks either property fails CI before it reaches the longitudinal cohort.

## Reference

- Policy decided: between session 2 and session 3, before threshold-crossing module is built.
- Inspiration: the test-pyramid model (unit tests cheap and many, integration tests rarer, end-to-end tests rarest). Tier 1 corresponds to unit tests of algorithms, Tier 2 to lightweight integration tests, Tier 3 to end-to-end snapshots.
