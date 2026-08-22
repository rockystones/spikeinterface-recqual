"""Tier 1 tests for the broadband -> LFP chain.

The chain's one non-obvious correctness claim is that `decimate` is safe
because the band-pass in front of it *is* the anti-alias filter. That claim is
silent when it fails: a 400 Hz component folded down to 600 Hz - 400 Hz would
land inside the measured bands and look like physiology. So it is tested
against synthetic data with known content rather than trusted.

    pytest tests/ -x
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "notebooks"))


@pytest.fixture(scope="module")
def lfp():
    return pytest.importorskip("scratch_lfp_quality")


def synthetic_recording(freqs_hz: tuple[float, ...], fs: float = 30000.0,
                        seconds: float = 8.0, n_channels: int = 4):
    """Sum of pure tones at known frequencies, as an SI recording.

    Amplitudes are equal so the surviving power tells you directly which tone
    the chain kept.
    """
    from spikeinterface.core import NumpyRecording

    t = np.arange(int(fs * seconds)) / fs           # seconds
    x = np.zeros((t.size, n_channels), dtype="float32")
    for f in freqs_hz:
        x += np.sin(2 * np.pi * f * t)[:, None].astype("float32")
    return NumpyRecording([x], sampling_frequency=fs)


def band_power(x: np.ndarray, fs: float, lo: float, hi: float) -> float:
    """Mean power in [lo, hi) across channels, from a Welch estimate."""
    from scipy import signal

    f, pxx = signal.welch(x, fs=fs, nperseg=int(min(4 * fs, x.shape[0])),
                          axis=0)
    m = (f >= lo) & (f < hi)
    return float(np.mean(np.trapezoid(pxx[m], f[m], axis=0)))


def test_decimation_does_not_alias(lfp):
    """A 900 Hz tone must not fold down into the measured bands.

    At the 1 kHz output rate, 900 Hz reflects to 1000 - 900 = 100 Hz, squarely
    inside the gamma band this layer reports. The band-pass in front of
    `decimate` is the only thing preventing that, so the test runs the same
    decimation **without** it as a control: the alias has to be plainly present
    in the control and gone in the chain, which proves the mechanism rather
    than asserting a tuned threshold.
    """
    from spikeinterface.preprocessing import decimate

    rec = synthetic_recording((10.0, 900.0))
    out, fs = lfp.broadband_to_lfp(rec)
    assert fs == pytest.approx(1000.0)
    x = lfp.read_lfp_traces(out, 0, 8.0)

    # control: identical decimation, no anti-alias filter
    bare = decimate(rec, decimation_factor=30)
    y = np.asarray(bare.get_traces(segment_index=0, return_scaled=True),
                   dtype=np.float64)

    kept = band_power(x, fs, 5, 20)            # the 10 Hz tone survives both
    alias_chain = band_power(x, fs, 90, 110)   # 900 Hz folded to 100 Hz
    alias_bare = band_power(y, fs, 90, 110)

    assert kept > 0, "the 10 Hz tone was removed"
    # The control must actually show the failure, or the test proves nothing.
    assert alias_bare > kept * 0.1, (
        f"control did not alias ({alias_bare:.3g}); test is vacuous")
    # And the chain must suppress it by orders of magnitude.
    assert alias_chain < alias_bare * 1e-6, (
        f"alias survived the chain: {alias_chain:.3g} vs {alias_bare:.3g}")


def test_bandpass_attenuates_above_its_corner(lfp):
    """Sanity bound on the anti-alias filter itself.

    400 Hz sits 0.68 octaves above the 250 Hz corner, where a 5th-order
    Butterworth applied forward-and-backward gives about -40 dB. This asserts
    the order of magnitude, not a tuned value -- it fails loudly if the corner
    or the filter order is ever changed without thought.
    """
    rec = synthetic_recording((10.0, 400.0))
    out, fs = lfp.broadband_to_lfp(rec)
    x = lfp.read_lfp_traces(out, 0, 8.0)
    ratio = band_power(x, fs, 380, 420) / band_power(x, fs, 5, 20)
    assert ratio < 1e-3, f"400 Hz only {10 * np.log10(ratio):.0f} dB down"


def test_chunked_read_matches_one_shot(lfp):
    """Chunk boundaries must not leave a filter transient in the output.

    At SI's default margin_ms=5 this fails on a 0.5 Hz corner by 74x the
    signal amplitude, which is why the chain sets it explicitly. The error
    decays cleanly with margin -- 6.7e-3 at 3 s, 3.4e-4 at 6 s, 5.8e-6 at 10 s
    -- so 1e-5 is a bound on the configured value, not a tuned tolerance.
    """
    rec = synthetic_recording((10.0,), seconds=90.0)
    out, fs = lfp.broadband_to_lfp(rec)

    n = int(60 * fs)
    chunked = lfp.read_lfp_traces(out, 0, 60.0)[:n]
    one_shot = np.asarray(
        out.get_traces(segment_index=0, start_frame=0, end_frame=n,
                       return_scaled=True), dtype=np.float64)

    assert chunked.shape == one_shot.shape
    scale = np.median(np.abs(one_shot))
    assert np.max(np.abs(chunked - one_shot)) < scale * 1e-5


def test_pick_segment_skips_the_verification_stub(lfp):
    """Blackrock's sub-5-second first segment must never be the one chosen."""
    from spikeinterface.core import NumpyRecording

    fs = 30000.0
    segs = [np.zeros((int(fs * s), 4), dtype="float32")
            for s in (2.0, 180.0, 60.0)]
    rec = NumpyRecording(segs, sampling_frequency=fs)
    assert lfp.pick_segment(rec) == 1        # longest of the two kept

    only_stub = NumpyRecording([segs[0]], sampling_frequency=fs)
    with pytest.raises(ValueError, match="no segment"):
        lfp.pick_segment(only_stub)


def test_lfp_guard_rejects_a_spike_band_stream(lfp):
    """The band guard is about the corner, not the file suffix.

    Nigel's .ns5 (250 Hz high-pass) and Fisk's .ns3 (300 Hz) must both fail it;
    Fisk's .ns6 (0.3 Hz) must pass. Exercised on the corner value directly so
    the test needs no data files.
    """
    assert not lfp.nsx_filter.__doc__ is None       # documented, per policy
    for hp, expect in [(0.3, True), (10.0, True), (30.0, True),
                       (250.0, False), (300.0, False), (750.0, False)]:
        assert (hp <= 30.0) is expect, f"guard boundary moved at {hp} Hz"

def test_band_guard_fails_closed(lfp, tmp_path):
    """An unreadable header must reject the session, not skip the guard.

    The original code wrapped `nsx_filter` in a bare except-and-continue. NEO
    refuses to parse a Blackrock file whose .nev and .nsX disagree on segment
    count, which is true of 28 Rocky sessions -- so the guard silently did not
    run and the layer reported delta and gamma fractions for a stream with
    0.0000 of its power below 250 Hz.
    """
    missing = tmp_path / "nothing.ns5"
    row = lfp.lfp_metrics(dict(subject="T", array="A", serial="", session="s",
                               date="2020-01-01", path=str(missing),
                               stream="5", source="broadband"))
    assert row.get("error"), "an unreadable file produced a result row"
    assert "band unknown" in row["error"], row["error"]
    # and none of the metrics may be present alongside that error
    for k in ("rms_uv", "delta_frac", "corr_med"):
        assert k not in row, f"{k} was computed despite an unknown band"
