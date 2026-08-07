"""Evidence figures for the load-bearing steps in the Rocky analysis.

Each figure exists to make one conclusion checkable rather than trusted. They
are numbered E1..E6 and correspond to the claims in
`docs/session_plans/session04_rocky_resort.md` and `docs/notes/snippet_sorting.md`.

  E1  the data are snippets, so standard sorters cannot run
  E2  the noise gate separates spikes from threshold crossings on noise
  E3  the Oct-2017 event is a noise rise, not a gain change
  E4  Plexon units are subsets, not disagreements  (a corrected conclusion)
  E5  UnitRefine is saturated, not merely conservative  (a corrected conclusion)
  E6  NEO's segment durations are impossible and would corrupt every rate

Two of these — E4 and E5 — document conclusions that were initially reported
the wrong way round. They are included precisely because a reader should be
able to see the evidence that overturned the first reading.

Run from repo root:

    uv run python notebooks/scratch_rocky_evidence.py
"""

from __future__ import annotations

import warnings
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "data" / "derived" / "rocky"
FIG = REPO / "figures" / "rocky" / "evidence"
ARRAY_COLOR = {"Anterior": "#1f77b4", "Posterior": "#d62728"}
PASS_C, FAIL_C = "#2ca02c", "#d62728"


def banner(t: str) -> None:
    print()
    print("=" * 72)
    print(t)
    print("=" * 72)


# === E1: the data are snippets ===
def e1_snippets() -> None:
    """Show what a snippet is, and that no continuous data exists."""
    import sys

    sys.path.insert(0, str(REPO / "notebooks"))
    from scratch_rocky_resort import align_on_trough, open_nev, read_electrode

    idx = pd.read_parquet(OUT / "session_index.parquet")
    row = idx[(idx["date"] == "2018-04-26") & (idx["array"] == "Anterior")
              & (idx["kind"] == "OFS")]
    if not len(row):
        row = idx[idx["kind"] == "OFS"].iloc[[0]]
    raw, meta, cbe = open_nev(Path(row.iloc[0]["path"]))
    sr, nbefore = meta["sr"], meta["nbefore"]

    # An electrode with real units, and one that is mostly noise
    picks = []
    for elec in sorted(cbe)[:40]:
        e = read_electrode(raw, meta, cbe[elec])
        if e is None or len(e["t"]) < 200:
            continue
        wf = align_on_trough(e["wf"], nbefore)
        amp = np.abs(wf.mean(axis=0).min())
        picks.append((amp, elec, wf))
    picks.sort(key=lambda x: -x[0])
    best, worst = picks[0], picks[-1]

    fig, axes = plt.subplots(1, 3, figsize=(16, 4.6))
    t_ms = (np.arange(best[2].shape[1]) - nbefore) / sr * 1000.0
    rng = np.random.default_rng(0)
    for ax, (_amp, _elec, wf), title in (
        (axes[0], best, f"electrode {best[1]} — real units"),
        (axes[1], worst, f"electrode {worst[1]} — threshold noise"),
    ):
        sub = wf[rng.choice(len(wf), min(300, len(wf)), replace=False)]
        ax.plot(t_ms, sub.T, color="0.6", lw=0.3, alpha=0.35)
        ax.plot(t_ms, wf.mean(axis=0), color="black", lw=2.0)
        ax.set_title(f"{title}\n{len(wf)} snippets, {wf.shape[1]} samples each",
                     fontsize=10)
        ax.set_xlabel("time from threshold crossing (ms)")
        ax.set_ylabel("uV")
        ax.grid(alpha=0.3)

    ax = axes[2]
    ax.axis("off")
    n_nev = int((idx["kind"].notna()).sum())
    txt = (
        "WHY STANDARD SORTERS CANNOT RUN\n\n"
        f"cohort:  {n_nev} .nev files\n"
        "         0 .ns5 / .ns6 files\n\n"
        "a NEV stores only what the NSP already\n"
        "detected: a timestamp plus a 30-sample\n"
        "clip, on ONE channel.\n\n"
        "MountainSort5, Kilosort4, Tridesclous2,\n"
        "SpykingCircus2 all begin by detecting\n"
        "spikes in a continuous trace and\n"
        "extracting their own waveforms.\n\n"
        "There is no trace here to detect from.\n\n"
        "At 400 um Utah pitch a neuron appears on\n"
        "one electrode only, so per-electrode\n"
        "clustering is the correct method, not a\n"
        "fallback — it is what Plexon OFS does too."
    )
    ax.text(0.0, 0.98, txt, va="top", ha="left", fontsize=9.5, family="monospace")
    fig.suptitle("E1  The constraint that shaped everything: this is snippet data",
                 fontsize=13)
    fig.tight_layout(rect=[0, 0, 1, 0.92])
    fig.savefig(FIG / "E1_snippet_constraint.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


# === E2: the gate separates signal from noise ===
def e2_gate(u: pd.DataFrame) -> None:
    """Show the gate's decision boundary and what falls on each side."""
    r = u[u["method"] == "resort"].copy()
    r["pass_gate"] = r["pass_gate"].fillna(False).astype(bool)
    p, f = r[r["pass_gate"]], r[~r["pass_gate"]]

    fig, axes = plt.subplots(1, 3, figsize=(17, 5))

    bins = np.logspace(np.log10(0.5), np.log10(60), 60)
    axes[0].hist(f["snr"].dropna(), bins=bins, color=FAIL_C, alpha=0.6,
                 label=f"rejected (n={len(f):,})")
    axes[0].hist(p["snr"].dropna(), bins=bins, color=PASS_C, alpha=0.6,
                 label=f"kept (n={len(p):,})")
    axes[0].axvline(4.0, color="black", ls="--", lw=1.6)
    axes[0].text(4.2, axes[0].get_ylim()[1] * 0.85, "SNR = 4\ngate", fontsize=9)
    axes[0].set_xscale("log")
    axes[0].set_xlabel("SNR  (|trough| / baseline MAD)")
    axes[0].set_ylabel("clusters")
    axes[0].set_title("the SNR cut does most of the work")
    axes[0].legend(fontsize=9)

    # Amplitude against the noise floor it must beat
    s = r.sample(min(12000, len(r)), random_state=0)
    axes[1].scatter(s.loc[~s["pass_gate"], "noise_uv"],
                    s.loc[~s["pass_gate"], "amplitude_uv"],
                    s=3, alpha=0.18, color=FAIL_C, label="rejected")
    axes[1].scatter(s.loc[s["pass_gate"], "noise_uv"],
                    s.loc[s["pass_gate"], "amplitude_uv"],
                    s=3, alpha=0.30, color=PASS_C, label="kept")
    xs = np.linspace(5, 90, 50)
    axes[1].plot(xs, 4 * xs, "k--", lw=1.6, label="amplitude = 4 x noise")
    axes[1].set_xlabel("electrode noise floor (uV)")
    axes[1].set_ylabel("unit amplitude (uV)")
    axes[1].set_yscale("log")
    axes[1].set_title("kept units sit above the noise floor by construction")
    axes[1].legend(fontsize=8, markerscale=3)
    axes[1].grid(alpha=0.3)

    # Physiological window on waveform width
    axes[2].hist(f["peak_trough_ms"].dropna(), bins=np.linspace(0, 1.6, 60),
                 color=FAIL_C, alpha=0.6, density=True, label="rejected")
    axes[2].hist(p["peak_trough_ms"].dropna(), bins=np.linspace(0, 1.6, 60),
                 color=PASS_C, alpha=0.6, density=True, label="kept")
    axes[2].axvspan(0.15, 1.20, color="green", alpha=0.07)
    axes[2].axvline(0.15, color="black", ls="--", lw=1.2)
    axes[2].axvline(1.20, color="black", ls="--", lw=1.2)
    axes[2].set_xlabel("peak-to-trough duration (ms)")
    axes[2].set_ylabel("density")
    axes[2].set_title("shaded = physiological window")
    axes[2].legend(fontsize=9)

    fig.suptitle("E2  What the noise gate keeps and rejects  "
                 f"({len(r):,} ISO-SPLIT clusters, full cohort)", fontsize=13)
    fig.tight_layout(rect=[0, 0, 1, 0.92])
    fig.savefig(FIG / "E2_gate_decision.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


# === E3: the Oct-2017 event is noise, not gain ===
def e3_noise_event(u: pd.DataFrame, s: pd.DataFrame) -> None:
    """Amplitude and noise decouple: the signature of a real noise rise."""
    r = u[u["method"] == "resort"].copy()
    r["date_dt"] = pd.to_datetime(r["date"])
    bad_dates = ["2017-09-29", "2017-10-03", "2017-10-04", "2017-10-05",
                 "2017-10-06", "2017-10-09", "2017-10-11", "2017-10-12"]
    good_dates = ["2017-09-21", "2017-09-22", "2017-09-25", "2017-09-27",
                  "2017-09-28"]
    bad = r[r["date"].isin(bad_dates)]
    good = r[r["date"].isin(good_dates)]

    fig, axes = plt.subplots(1, 3, figsize=(17, 5))

    ss = s[s["method"] == "resort"].copy()
    ss["date_dt"] = pd.to_datetime(ss["date"])
    early = ss[ss["date_dt"] < "2018-01-01"].sort_values("date_dt")
    for arr, g in early.groupby("array"):
        axes[0].plot(g["date_dt"], g["median_noise_uv"], "-o", ms=4,
                     color=ARRAY_COLOR.get(arr, "0.4"), label=arr)
    axes[0].axhline(15, color="0.5", ls=":", lw=1)
    axes[0].set_ylabel("median noise floor (uV)")
    axes[0].set_title("noise floor, autumn 2017")
    axes[0].legend(fontsize=9)
    axes[0].grid(alpha=0.3)
    axes[0].tick_params(axis="x", rotation=30)
    axes[0].xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))

    # The decisive panel: if this were a gain change both would scale together
    cats = ["noise floor", "unit amplitude", "SNR"]
    gvals = [good["noise_uv"].median(), good["amplitude_uv"].median(),
             good["snr"].median()]
    bvals = [bad["noise_uv"].median(), bad["amplitude_uv"].median(),
             bad["snr"].median()]
    xs = np.arange(3)
    axes[1].bar(xs - 0.2, gvals, 0.4, color="#2ca02c", label="healthy sessions")
    axes[1].bar(xs + 0.2, bvals, 0.4, color="#d62728", label="elevated-noise")
    for i, (g_, b_) in enumerate(zip(gvals, bvals, strict=True)):
        axes[1].text(i - 0.2, g_ * 1.03, f"{g_:.1f}", ha="center", fontsize=9)
        axes[1].text(i + 0.2, b_ * 1.03, f"{b_:.1f}", ha="center", fontsize=9)
        axes[1].text(i, max(g_, b_) * 1.22, f"x{b_ / g_:.2f}", ha="center",
                     fontsize=10, fontweight="bold")
    axes[1].set_xticks(xs, cats)
    axes[1].set_ylabel("median across clusters")
    axes[1].set_title("noise tripled; amplitude did NOT scale\n"
                      "a gain error would move both equally", fontsize=10)
    axes[1].legend(fontsize=9)
    axes[1].grid(alpha=0.3, axis="y")

    axes[2].scatter(good["noise_uv"], good["amplitude_uv"], s=4, alpha=0.25,
                    color="#2ca02c", label="healthy")
    axes[2].scatter(bad["noise_uv"], bad["amplitude_uv"], s=4, alpha=0.25,
                    color="#d62728", label="elevated-noise")
    xs2 = np.linspace(5, 100, 50)
    axes[2].plot(xs2, 4 * xs2, "k--", lw=1.4, label="SNR = 4")
    axes[2].set_xlabel("noise floor (uV)")
    axes[2].set_ylabel("amplitude (uV)")
    axes[2].set_yscale("log")
    axes[2].set_xscale("log")
    axes[2].set_title("the cloud shifts right, not up")
    axes[2].legend(fontsize=8, markerscale=3)
    axes[2].grid(alpha=0.3)

    fig.suptitle("E3  October 2017 was a recording fault, not a scaling artefact  "
                 "— and OFS reported ~190 units straight through it", fontsize=13)
    fig.tight_layout(rect=[0, 0, 1, 0.91])
    fig.savefig(FIG / "E3_noise_event.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


# === E4: Plexon units are subsets (corrected conclusion) ===
def e4_containment(j: pd.DataFrame) -> None:
    """Jaccard said 'disagree'; containment says 'subset'. Show both."""
    fwd = j[(j["method_a"] == "isosplit") & (j["method_b"] == "ofs")]
    rev = j[(j["method_a"] == "ofs") & (j["method_b"] == "isosplit")]
    auto = j[(j["method_a"] == "isosplit") & (j["method_b"] == "kmeans_sil")]

    fig, axes = plt.subplots(1, 3, figsize=(17, 5))

    bins = np.linspace(0, 1, 26)
    axes[0].hist(rev["best_jaccard"].dropna(), bins=bins, alpha=0.65,
                 color="#d62728", label="Jaccard", density=True)
    axes[0].hist(rev["best_containment"].dropna(), bins=bins, alpha=0.65,
                 color="#2ca02c", label="containment", density=True)
    axes[0].set_xlabel("score of each OFS unit vs its best ISO-SPLIT match")
    axes[0].set_ylabel("density")
    axes[0].set_title("same units, two metrics, opposite stories\n"
                      f"Jaccard med {rev['best_jaccard'].median():.2f}  |  "
                      f"containment med {rev['best_containment'].median():.2f}",
                      fontsize=10)
    axes[0].legend(fontsize=9)

    axes[1].scatter(rev["n_spikes_a"], rev["matched_b_size"], s=6, alpha=0.25,
                    color="#d62728", label="OFS unit vs matched ISO-SPLIT")
    lim = [1, max(rev["matched_b_size"].max(), rev["n_spikes_a"].max()) * 1.1]
    axes[1].plot(lim, lim, "k--", lw=1.4, label="equal size")
    axes[1].set_xscale("log")
    axes[1].set_yscale("log")
    axes[1].set_xlabel("spikes in the OFS unit")
    axes[1].set_ylabel("spikes in the matched ISO-SPLIT cluster")
    axes[1].set_title("the matched cluster is ~6.9x larger\n"
                      "which is exactly what deflates Jaccard", fontsize=10)
    axes[1].legend(fontsize=8, markerscale=2)
    axes[1].grid(alpha=0.3)

    pairs = [("ofs -> isosplit", rev), ("isosplit -> ofs", fwd),
             ("isosplit -> kmeans", auto)]
    xs = np.arange(len(pairs))
    jac = [p["best_jaccard"].median() for _, p in pairs]
    con = [p["best_containment"].median() for _, p in pairs]
    axes[2].bar(xs - 0.2, jac, 0.4, color="#d62728", label="Jaccard")
    axes[2].bar(xs + 0.2, con, 0.4, color="#2ca02c", label="containment")
    for i, (a, b) in enumerate(zip(jac, con, strict=True)):
        axes[2].text(i - 0.2, a + 0.02, f"{a:.2f}", ha="center", fontsize=9)
        axes[2].text(i + 0.2, b + 0.02, f"{b:.2f}", ha="center", fontsize=9)
    axes[2].set_xticks(xs, [p for p, _ in pairs], fontsize=9)
    axes[2].set_ylim(0, 1.15)
    axes[2].set_ylabel("median score")
    axes[2].set_title("direction matters: containment is not symmetric",
                      fontsize=10)
    axes[2].legend(fontsize=9)
    axes[2].grid(alpha=0.3, axis="y")

    fig.suptitle("E4  CORRECTED: Plexon is not disagreeing, it is finding subsets "
                 "— every OFS spike lands inside an ISO-SPLIT cluster",
                 fontsize=13)
    fig.tight_layout(rect=[0, 0, 1, 0.91])
    fig.savefig(FIG / "E4_containment_correction.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


# === E5: UnitRefine is saturated (corrected conclusion) ===
def e5_unitrefine(c: pd.DataFrame) -> None:
    """The classifier never crosses its own decision boundary."""
    c = c.copy()
    c["pass_gate"] = c["pass_gate"].fillna(False).astype(bool)
    has_p = "ur_p_neural" in c.columns and c["ur_p_neural"].notna().any()

    fig, axes = plt.subplots(1, 3, figsize=(17, 5))

    if has_p:
        axes[0].hist(c["ur_p_neural"].dropna(), bins=60, color="#7f7f7f")
        axes[0].axvline(0.5, color="red", ls="--", lw=2)
        mx = float(c["ur_p_neural"].max())
        axes[0].axvline(mx, color="black", ls=":", lw=1.6)
        axes[0].text(mx, axes[0].get_ylim()[1] * 0.75,
                     f"  max = {mx:.3f}", fontsize=10)
        axes[0].text(0.52, axes[0].get_ylim()[1] * 0.9, "decision\nboundary",
                     color="red", fontsize=9)
        axes[0].set_xlabel("P(neural) from UnitRefine")
        axes[0].set_ylabel("units")
        axes[0].set_title("the probability never reaches the boundary\n"
                          "no threshold choice rescues this", fontsize=10)

        s = c.sample(min(15000, len(c)), random_state=0)
        axes[1].scatter(s["snr"], s["ur_p_neural"], s=3, alpha=0.15,
                        color="#1f77b4")
        axes[1].axhline(0.5, color="red", ls="--", lw=1.6)
        axes[1].axvline(4.0, color="black", ls="--", lw=1.4)
        axes[1].set_xscale("log")
        axes[1].set_xlabel("SNR (log)")
        axes[1].set_ylabel("P(neural)")
        axes[1].set_title("high-SNR units get low P(neural):\n"
                          "the labels are not tracking quality", fontsize=10)
        axes[1].grid(alpha=0.3)

    kept_by_gate = c[c["pass_gate"]]
    disc = kept_by_gate[~kept_by_gate["ur_neural"].fillna(False)]
    bins = np.logspace(np.log10(0.5), np.log10(60), 50)
    axes[2].hist(c.loc[~c["pass_gate"], "snr"].dropna(), bins=bins, alpha=0.5,
                 color="0.7", label="gate rejects")
    axes[2].hist(disc["snr"].dropna(), bins=bins, alpha=0.75, color="#d62728",
                 label=f"gate KEEPS, UnitRefine discards (n={len(disc):,})")
    axes[2].axvline(4.0, color="black", ls="--", lw=1.5)
    axes[2].set_xscale("log")
    axes[2].set_xlabel("SNR (log)")
    axes[2].set_ylabel("units")
    axes[2].set_title(f"discarded units have median SNR "
                      f"{disc['snr'].median():.2f}\nthese are real units",
                      fontsize=10)
    axes[2].legend(fontsize=8)

    n_neural = int(c["ur_neural"].fillna(False).sum())
    fig.suptitle("E5  CORRECTED: UnitRefine labels "
                 f"{len(c) - n_neural:,} of {len(c):,} units NOISE (keeps {n_neural}) "
                 "— saturated, not conservative", fontsize=13)
    fig.tight_layout(rect=[0, 0, 1, 0.91])
    fig.savefig(FIG / "E5_unitrefine_saturation.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


# === E6: NEO's segment durations are impossible ===
def e6_segments(idx: pd.DataFrame) -> None:
    """The bug that silently corrupted every rate before it was caught."""
    d = idx[idx["duration_s"].notna()].copy()
    fig, axes = plt.subplots(1, 3, figsize=(17, 4.8))

    axes[0].hist(np.log10(d["duration_s"].clip(lower=1)), bins=60,
                 color="#1f77b4")
    for v, lab in ((180, "180 s\n(2018+)"), (3000, "~50 min\n(2017)")):
        axes[0].axvline(np.log10(v), color="green", ls="--", lw=1.4)
        axes[0].text(np.log10(v), axes[0].get_ylim()[1] * 0.7, "  " + lab,
                     fontsize=8, color="green")
    axes[0].axvline(np.log10(3600), color="red", ls="-", lw=2)
    axes[0].text(np.log10(3600), axes[0].get_ylim()[1] * 0.9, "  3600 s cutoff",
                 fontsize=9, color="red")
    axes[0].set_xlabel("log10 summed segment duration (s)")
    axes[0].set_ylabel("files")
    axes[0].set_title("summing NEO's segments gives impossible durations")

    over = d[d["duration_s"] > 3600]
    axes[1].scatter(d["n_segments"], d["duration_s"], s=10, alpha=0.4,
                    color="#1f77b4")
    axes[1].axhline(3600, color="red", ls="-", lw=1.6)
    axes[1].set_yscale("log")
    axes[1].set_xlabel("segments NEO reports per file")
    axes[1].set_ylabel("summed duration (s, log)")
    axes[1].set_title(f"{len(over)} files exceed one hour\n"
                      f"worst: {d['duration_s'].max():,.0f} s "
                      f"({d['duration_s'].max() / 3600:.0f} h)", fontsize=10)
    axes[1].grid(alpha=0.3)

    ax = axes[2]
    ax.axis("off")
    ax.text(0.0, 0.98,
            "WHY THIS MATTERED\n\n"
            "firing_rate = n_spikes / duration\n"
            "presence_ratio bins over duration\n\n"
            "A 180 s recording reported as\n"
            "143,119 s understates every rate\n"
            "by ~800x — and NOTHING crashes.\n\n"
            "The fix selects ONE plausible\n"
            "segment: >= 5 s (project policy)\n"
            "and <= 3600 s.\n\n"
            "The upper bound needed care:\n"
            "2017 sessions really are ~50 min\n"
            "while 2018+ are 180 s. A tighter\n"
            "cutoff would have silently deleted\n"
            "the entire 2017 era.\n\n"
            "Real protocol change sitting right\n"
            "next to an artefact.",
            va="top", ha="left", fontsize=9.5, family="monospace")

    fig.suptitle("E6  NEO's segment splitting would have corrupted every rate "
                 "without raising an error", fontsize=13)
    fig.tight_layout(rect=[0, 0, 1, 0.91])
    fig.savefig(FIG / "E6_segment_bug.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def main() -> int:
    """Render every evidence figure."""
    FIG.mkdir(parents=True, exist_ok=True)
    idx = pd.read_parquet(OUT / "session_index.parquet")
    u = pd.read_parquet(OUT / "units_long.parquet")
    s = pd.read_parquet(OUT / "session_summary.parquet")
    j = pd.read_parquet(OUT / "method_jaccard.parquet")
    c = pd.read_parquet(OUT / "curation_labels.parquet")

    banner("Rendering evidence figures")
    for name, fn in (
        ("E1 snippet constraint", lambda: e1_snippets()),
        ("E2 gate decision", lambda: e2_gate(u)),
        ("E3 noise event", lambda: e3_noise_event(u, s)),
        ("E4 containment correction", lambda: e4_containment(j)),
        ("E5 UnitRefine saturation", lambda: e5_unitrefine(c)),
        ("E6 segment bug", lambda: e6_segments(idx)),
    ):
        try:
            fn()
            print(f"  ok   {name}")
        except Exception as e:  # noqa: BLE001
            print(f"  FAIL {name}: {type(e).__name__}: {e}")
    print(f"\n  -> {FIG}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
