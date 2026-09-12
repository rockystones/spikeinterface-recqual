"""Is Fisk's `.ns3` just a band-limited copy of the `.ns6`? A sampled check.

CLAUDE.md records that Fisk's `.ns3` is **not LFP** -- it is high-passed at
300 Hz, a second spike-band stream at 2 kHz that exists for Fisk alone. The
open question was whether it carries anything its `.ns6` does not, i.e.
whether 140 sessions of `.ns3` deserve a place in the pipeline.

The test, on a spread of sessions: band-match the `.ns6` to the `.ns3`'s own
passband (band-pass to the corners read from the ns3 extended header, then
decimate to 2 kHz -- the band-pass is the anti-alias filter, as in the LFP
derivation), and compare per-channel MAD noise across the 96 channels. If the
two streams rank channels identically and sit at a fixed amplitude ratio, the
`.ns3` is redundant and stays out of the pipeline with a documented reason.

Bands are read from the extended header, never the suffix (CLAUDE.md).

Run from repo root:

    uv run python notebooks/scratch_fisk_ns3_check.py
"""

from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "notebooks"))

from scratch_cohort_io import banner  # noqa: E402

FISK = Path(r"D:\Claude Code\Monkey Data\Fisk")
SLICE_S = 30.0
N_SESSIONS = 6


def nsx_corners(path: Path, stream: str) -> tuple[float, float]:
    """(high-pass, low-pass) corner frequencies in Hz, from the header.

    Blackrock's field names invert the intuition: `hi_freq_corner` is the
    HIGH-PASS corner and `lo_freq_corner` the LOW-PASS one, both in
    millihertz ([[lfp_quality]]). load_nev=False sidesteps NEO's
    segment-count consistency check, which the band does not need.
    """
    from neo.rawio import BlackrockRawIO

    io = BlackrockRawIO(filename=str(path.with_suffix("")),
                        nsx_to_load=int(stream), load_nev=False)
    io.parse_header()
    h = io._nsx_ext_header[int(stream)][0]
    hp = float(h["hi_freq_corner"]) / 1000.0
    lp = float(h["lo_freq_corner"]) / 1000.0
    return hp, lp


def mad_noise(rec, n_ch: int) -> np.ndarray:
    """Per-channel MAD in uV over the first SLICE_S seconds."""
    import spikeinterface.core as sc

    end = min(int(SLICE_S * rec.get_sampling_frequency()),
              rec.get_num_samples(0))
    tr = rec.get_traces(segment_index=0, start_frame=0, end_frame=end,
                        return_scaled=True)
    return np.median(np.abs(tr - np.median(tr, axis=0)), axis=0) * 1.4826


def check_session(folder: Path) -> dict | None:
    """Compare ns3 noise against band-matched ns6 noise for one session."""
    import spikeinterface.extractors as se
    import spikeinterface.preprocessing as sp
    from scipy.stats import spearmanr

    ns3s = sorted(folder.glob("*.ns3"))
    ns6s = sorted(folder.glob("*.ns6"))
    if not ns3s or not ns6s:
        return None
    # the -002 file is the real recording where both exist; pair by stem
    stems6 = {p.stem for p in ns6s}
    pair = next((p for p in ns3s if p.stem in stems6), None)
    if pair is None:
        return None
    ns3_p, ns6_p = pair, folder / f"{pair.stem}.ns6"

    hp3, lp3 = nsx_corners(ns3_p, "3")
    r3 = se.read_blackrock(str(ns3_p), stream_id="3")
    r6 = se.read_blackrock(str(ns6_p), stream_id="6")
    keep = [c for c in r3.channel_ids if c in set(r6.channel_ids)]
    r3 = r3.select_channels(keep)
    r6 = r6.select_channels(keep)

    # band-match: the ns3's own corners, capped below its Nyquist; the
    # band-pass is the anti-alias filter for the decimation
    fs3 = r3.get_sampling_frequency()
    hi_eff = min(lp3 if lp3 > 0 else fs3 / 2 * 0.8, fs3 / 2 * 0.8)
    r6f = sp.bandpass_filter(r6, freq_min=max(hp3, 0.1), freq_max=hi_eff,
                             margin_ms=200.0)
    q = int(round(r6.get_sampling_frequency() / fs3))
    r6d = sp.decimate(r6f, decimation_factor=q)

    n3 = mad_noise(r3, len(keep))
    n6 = mad_noise(r6d, len(keep))
    rho, p = spearmanr(n3, n6)
    return dict(stem=ns3_p.stem, folder=folder.name,
                hp3=hp3, lp3=lp3, fs3=fs3, decim=q, n_ch=len(keep),
                rho=float(rho), p=float(p),
                ratio_med=float(np.median(n3 / n6)),
                ratio_iqr=float(np.subtract(*np.percentile(n3 / n6,
                                                           [75, 25]))))


def main() -> int:
    banner(f"Fisk .ns3 against band-matched .ns6, {N_SESSIONS} sessions")
    folders = sorted(FISK.glob("*/Recordings/*"))
    folders = [f for f in folders if f.is_dir() and list(f.glob("*.ns3"))
               and list(f.glob("*.ns6"))]
    print(f"  {len(folders)} sessions carry both streams")
    # an even spread across the record
    pick = [folders[i] for i in
            np.linspace(0, len(folders) - 1, N_SESSIONS).astype(int)]
    rows = []
    for f in pick:
        try:
            r = check_session(f)
        except Exception as exc:  # noqa: BLE001
            print(f"  ! {f.name}: {type(exc).__name__}: {exc}")
            continue
        if r:
            rows.append(r)
            print(f"  {r['folder']}: band {r['hp3']:.0f}-{r['lp3']:.0f} Hz, "
                  f"rho = {r['rho']:+.3f}, noise ratio ns3/ns6 = "
                  f"{r['ratio_med']:.3f} (IQR {r['ratio_iqr']:.3f})")
    if rows:
        d = pd.DataFrame(rows)
        print(f"\n  median rho {d.rho.median():+.3f}, "
              f"median ratio {d.ratio_med.median():.3f}")
        d.to_parquet(REPO / "data" / "derived" / "fisk"
                     / "ns3_redundancy_check.parquet", index=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
