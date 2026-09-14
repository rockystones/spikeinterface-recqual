function P = rocky_provenance(stem, opts)
%ROCKY_PROVENANCE Walk one session's full derivation chain, re-derived in MATLAB.
%
%   P = ROCKY_PROVENANCE()          default session (2018-02-22 Anterior)
%   P = ROCKY_PROVENANCE(stem)      any stem under data/derived/provenance/
%   P = ROCKY_PROVENANCE(stem, method="gmm_bic", channel=17, sorter="kilosort4")
%
%   Loads the provenance store written by notebooks/scratch_provenance_dump.py
%   (raw snippets, per-spike labels for every method, PCA features, per-unit
%   tables, sorting-free metrics, modern-pool spike trains and templates) and
%   RE-DERIVES the metrics in MATLAB with the same definitions:
%     noise    = MAD(pre-trigger samples, global median) / 0.6745
%     align    = circular shift so the trough sits at nbefore (+/-2 search)
%     unit     = mean-waveform trough amplitude, post-trough peak, SNR,
%                ISI violations (<1.5 ms), 10-bin presence, the physics gate
%     free     = per-event |trough| (official def); NumPy-style percentiles
%   then prints a comparison table against the Python-computed values so any
%   definitional drift is visible, not hidden.
%
%   Returned struct P holds every table plus the comparisons, for the
%   Variable Editor. Figures (channel waveforms by unit, PC scatter,
%   MATLAB-vs-Python amplitude, modern templates) go to
%   figures/matlab_repro/provenance/<stem>/.
%
%   All tunable constants come from the store's meta.json, not from this file.

arguments
    stem (1, 1) string = "Rocky_Anterior_02-22-2018_Baseline"
    opts.method (1, 1) string = "isosplit"
    opts.channel (1, 1) double = NaN      % NaN = channel with most gated units
    opts.sorter (1, 1) string = "mountainsort5"
    opts.makeFigures (1, 1) logical = true
end

repoRoot = fileparts(fileparts(mfilename("fullpath")));
root = fullfile(repoRoot, "data", "derived", "provenance", stem);
if ~isfolder(root)
    error("rocky_provenance:noStore", ...
        "no provenance store at %s - run scratch_provenance_dump.py", root);
end
suspendCreateFcnGuard = suspend_create_fcn();                %#ok<NASGU>

% --- load everything -----------------------------------------------------
P = struct();
P.stem = stem;
P.meta = jsondecode(fileread(fullfile(root, "meta.json")));
P.events        = parquetread(fullfile(root, "events.parquet"));
P.electrodes    = parquetread(fullfile(root, "electrodes.parquet"));
P.subsample     = parquetread(fullfile(root, "subsample.parquet"));
P.units_methods = parquetread(fullfile(root, "units_methods.parquet"));
P.units_full    = parquetread(fullfile(root, "units_full.parquet"));
P.free_python   = parquetread(fullfile(root, "free_electrode.parquet"));
P.official_events_electrode = parquetread( ...
    fullfile(root, "official_events_electrode.parquet"));
P.official_session_summary = parquetread( ...
    fullfile(root, "official_session_summary.parquet"));
mlPath = fullfile(root, "official_methods_long.parquet");
if isfile(mlPath), P.official_methods_long = parquetread(mlPath); end
P.waveforms = read_npy(fullfile(root, "waveforms.npy"));   % (n_events, 30) uV
fprintf("%s: %d events, %d electrodes, has_ofs=%d\n", stem, ...
    height(P.events), height(P.electrodes), P.meta.has_ofs);

sr = P.meta.sr; nbefore = P.meta.nbefore; dur = P.meta.duration_s;
G = P.meta.gate;

% --- 1. re-derive per-unit metrics in MATLAB for the chosen method -------
lcol = "label_" + opts.method;
assert(ismember(lcol, P.subsample.Properties.VariableNames), ...
    "method %s not in subsample table", opts.method);
S = P.subsample;
rows = {};
for ch = unique(S.channel_id)'
    g = S(S.channel_id == ch, :);
    wf_raw = P.waveforms(g.event_idx + 1, :);      % event_idx is 0-based
    noise = P.electrodes.noise_uv(P.electrodes.channel_id == ch);
    wf = align_trough(wf_raw, nbefore, 2);
    t = P.events.t_s(g.event_idx + 1);
    for u = unique(g.(lcol))'
        sel = g.(lcol) == u;
        m = unit_metrics_ml(wf(sel, :), t(sel), noise, sr, nbefore, dur, G);
        rows{end + 1} = [table(ch, u, VariableNames=["channel_id", "unit_id"]), ...
                         struct2table(m)];         %#ok<AGROW>
    end
end
P.units_matlab = sortrows(vertcat(rows{:}), ["channel_id", "unit_id"]);

py = P.units_methods(P.units_methods.method == opts.method, :);
j = innerjoin(P.units_matlab, py, Keys=["channel_id", "unit_id"]);
metrics = ["n_spikes", "firing_rate_hz", "amplitude_uv", "snr", ...
           "peak_trough_ms", "isi_viol_rate", "presence_ratio"];
fprintf("\n=== MATLAB re-derivation vs Python, method %s (%d units) ===\n", ...
    opts.method, height(j));
cmp = table();
for m = metrics
    a = double(j.(m + "_left")); b = double(j.(m + "_right"));
    d = max(abs(a - b));
    cmp = [cmp; table(m, d, max(abs(b)), VariableNames= ...
        ["metric", "max_abs_diff", "max_abs_value"])];      %#ok<AGROW>
end
disp(cmp);
gateAgree = mean(j.pass_gate_left == j.pass_gate_right);
fprintf("gate decisions agree on %.1f%% of units\n", 100 * gateAgree);
P.compare_units = cmp; P.units_joined = j;

% --- 2. re-derive the sorting-free layer ---------------------------------
fr = {};
for ch = unique(P.events.channel_id)'
    % official pipeline: amp percentiles over |trough| (= |vmin|);
    % absamp_uv = max(|vmin|, vmax) is the giant/artifact amplitude
    a = abs(P.events.vmin_uv(P.events.channel_id == ch));
    fr{end + 1} = table(ch, numel(a), numel(a) / dur, ...
        np_prctile(a, 50), np_prctile(a, 90), np_prctile(a, 99), max(a), ...
        VariableNames=["channel_id", "n_events", "crossing_rate_hz", ...
                       "amp_p50", "amp_p90", "amp_p99", "amp_max"]); %#ok<AGROW>
end
P.free_matlab = vertcat(fr{:});
jf = innerjoin(P.free_matlab, P.free_python, Keys="channel_id");
fprintf("\n=== free layer, MATLAB vs Python (%d electrodes) ===\n", height(jf));
for m = ["n_events", "crossing_rate_hz", "amp_p50", "amp_p99", "amp_max"]
    fprintf("  %-18s max|diff| = %.6g\n", m, ...
        max(abs(double(jf.(m + "_left")) - double(jf.(m + "_right")))));
end
jo = innerjoin(P.free_matlab, P.official_events_electrode, Keys="channel_id");
fprintf("vs OFFICIAL events_electrode (stored pipeline):\n");
for m = ["n_events", "crossing_rate_hz", "amp_p50", "amp_p99"]
    fprintf("  %-18s max|diff| = %.6g\n", m, ...
        max(abs(double(jo.(m + "_left")) - double(jo.(m + "_right")))));
end

% --- 3. session aggregate vs the stored summary --------------------------
uf = P.units_full(P.units_full.method == "isosplit_full", :);
gated = uf(logical(uf.pass_gate), :);
fprintf("\n=== session aggregate ===\n");
fprintf("  this dump  (isosplit_full): %d units, %d gated, %.3f gated/elec\n", ...
    height(uf), height(gated), height(gated) / height(P.electrodes));
ss = P.official_session_summary;
if any(ss.method == "resort")
    s1 = ss(ss.method == "resort", :);
    fprintf("  stored     (resort)       : %d units, upe %.3f  " + ...
        "(pipeline twin; small diffs = resort-run particulars)\n", ...
        s1.n_units(1), s1.units_per_electrode(1));
end

% --- 4. modern pool -------------------------------------------------------
mdir = fullfile(root, "modern", opts.sorter);
if isfolder(mdir)
    M = struct();
    M.spike_sample = read_npy(fullfile(mdir, "spike_sample_index.npy"));
    M.spike_unit   = read_npy(fullfile(mdir, "spike_unit_index.npy"));
    M.unit_ids     = read_npy(fullfile(mdir, "unit_ids.npy"));
    if isfile(fullfile(mdir, "templates.npy"))
        M.templates = read_npy(fullfile(mdir, "templates.npy")); % u x s x c
        M.peak_channel_index = read_npy(fullfile(mdir, "peak_channel_index.npy"));
        M.sample_wf = read_npz_array(fullfile(mdir, "sample_waveforms.npz"), "wf");
        M.sample_unit_index = read_npz_array( ...
            fullfile(mdir, "sample_waveforms.npz"), "unit_index");
    end
    P.modern = M;
    fprintf("\n=== modern pool: %s ===\n  %d units, %d spikes", ...
        opts.sorter, numel(M.unit_ids), numel(M.spike_sample));
    if isfield(M, "templates")
        fprintf(", templates %s", mat2str(size(M.templates)));
    end
    fprintf("\n");
else
    fprintf("\n(no modern/ layer for this stem or sorter)\n");
end

% --- figures --------------------------------------------------------------
if ~opts.makeFigures, return; end
outDir = fullfile(repoRoot, "figures", "matlab_repro", "provenance", stem);
if ~isfolder(outDir), mkdir(outDir); end

if isnan(opts.channel)
    gg = groupsummary(P.units_matlab(logical(P.units_matlab.pass_gate), :), ...
                      "channel_id");
    if isempty(gg), opts.channel = P.electrodes.channel_id(1);
    else, [~, i] = max(gg.GroupCount); opts.channel = gg.channel_id(i);
    end
end
ch = opts.channel;
g = S(S.channel_id == ch, :);
wf = align_trough(P.waveforms(g.event_idx + 1, :), nbefore, 2);
lab = g.(lcol);
uu = unique(lab)'; cmap = lines(numel(uu));

f = figure(Visible="off", Position=[60 60 1100 420]);
tiledlayout(1, 3, TileSpacing="compact");
nexttile; hold on;
for k = 1:numel(uu)
    sel = find(lab == uu(k));
    sel = sel(1:min(80, numel(sel)));
    plot(((0:size(wf, 2) - 1) - nbefore) / sr * 1e3, wf(sel, :)', ...
        Color=[cmap(k, :), 0.12]);
end
for k = 1:numel(uu)
    plot(((0:size(wf, 2) - 1) - nbefore) / sr * 1e3, ...
        mean(wf(lab == uu(k), :), 1), Color=cmap(k, :), LineWidth=2, ...
        DisplayName="unit " + uu(k));
end
hold off; grid on; xlabel("ms from trough"); ylabel("\muV");
title(sprintf("ch %d, %s: waveforms by assigned unit", ch, opts.method));

nexttile; hold on;
for k = 1:numel(uu)
    sel = lab == uu(k);
    scatter(g.pc1(sel), g.pc2(sel), 6, cmap(k, :), "filled", ...
        MarkerFaceAlpha=0.35);
end
hold off; grid on; xlabel("PC1"); ylabel("PC2");
title("the features the clusterer saw");

nexttile;
ju = j(j.channel_id == ch, :);
bar([ju.amplitude_uv_left, ju.amplitude_uv_right]);
legend(["MATLAB", "Python"], Location="best"); grid on;
set(gca, XTickLabel=ju.unit_id); xlabel("unit"); ylabel("amplitude (\muV)");
title("re-derived vs stored amplitude");
exportgraphics(f, fullfile(outDir, ...
    sprintf("P1_channel%02d_%s.png", ch, opts.method)), Resolution=150);
close(f);

if isfield(P, "modern") && isfield(P.modern, "templates")
    M = P.modern;
    nU = size(M.templates, 1);
    pick = round(linspace(1, nU, min(24, nU)));
    f = figure(Visible="off", Position=[60 60 950 640]);
    tl = tiledlayout(4, 6, TileSpacing="compact");
    for k = pick
        ax = nexttile;
        plot(ax, squeeze(M.templates(k, :, M.peak_channel_index(k) + 1)), ...
            "k-", LineWidth=1);
        axis(ax, "tight"); set(ax, XTick=[], YTick=[]); box(ax, "on");
        title(ax, "u" + M.unit_ids(k), FontSize=6);
    end
    title(tl, opts.sorter + ": peak-channel templates from the ns5");
    exportgraphics(f, fullfile(outDir, "P2_modern_templates_" + ...
        opts.sorter + ".png"), Resolution=150);
    close(f);
end
fprintf("figures -> %s\n", outDir);
end


% === the mirrored definitions ===========================================
function noise = baseline_noise_ml(wf, nbefore)
%BASELINE_NOISE_ML MAD of pre-trigger samples (global median) / 0.6745.
stop = max(1, nbefore - 2);
base = wf(:, 1:stop);
if numel(base) < 32, base = wf; end
med = median(base(:));
madv = median(abs(base(:) - med));
if madv > 0, noise = madv / 0.6745;
else, noise = max(std(base(:)), 1);
end
end %#ok<DEFNU>  (kept for standalone use; the dump ships noise per electrode)

function out = align_trough(wf, nbefore, window)
%ALIGN_TROUGH Circular-shift each row so its trough sits at nbefore (0-based).
% Mirrors align_on_trough: search in [nbefore-window, nbefore+window],
% np.roll semantics (wrap-around) == circshift.
n1 = nbefore + 1;                              % MATLAB is 1-based
lo = max(1, n1 - window); hi = min(size(wf, 2), n1 + window);
[~, rel] = min(wf(:, lo:hi), [], 2);
shifts = rel + lo - 1 - n1;                    % samples to the right of target
out = zeros(size(wf), "like", wf);
for s = unique(shifts)'
    r = shifts == s;
    out(r, :) = circshift(wf(r, :), -s, 2);
end
end

function m = unit_metrics_ml(wf, t, noise, sr, nbefore, dur, G)
%UNIT_METRICS_ML Mirror of scratch_rocky_resort.unit_metrics.
n = size(wf, 1);
tmpl = mean(wf, 1);
[trough_uv, ti] = min(tmpl);                   % ti is 1-based
post = tmpl(ti:end);
if numel(post) > 1, [peak_uv, pr] = max(post); pr = pr - 1;
else, peak_uv = 0; pr = 0;
end
pt_ms = pr / sr * 1e3;
trough_offset_ms = ((ti - 1) - nbefore) / sr * 1e3;
snr = abs(trough_uv) / max(noise, eps);
isi = diff(sort(t));
if isempty(isi), isi_viol = 0;
else, isi_viol = mean(isi < G.ISI_REFRACTORY_MS / 1e3);
end
edges = linspace(0, dur, 11);
presence = mean(histcounts(t, edges) > 0);
pass = n >= G.MIN_SPIKES && snr >= G.MIN_SNR && ...
    pt_ms >= G.PT_MS_MIN && pt_ms <= G.PT_MS_MAX && ...
    abs(trough_offset_ms) <= G.TROUGH_TOL_MS;
m = struct("n_spikes", n, "firing_rate_hz", n / dur, "snr", snr, ...
    "trough_uv", trough_uv, "peak_uv", peak_uv, ...
    "amplitude_uv", abs(trough_uv), "peak_trough_ms", pt_ms, ...
    "trough_offset_ms", trough_offset_ms, "isi_viol_rate", isi_viol, ...
    "presence_ratio", presence, "noise_uv", noise, "pass_gate", pass);
end

function v = np_prctile(a, p)
%NP_PRCTILE NumPy default ('linear') percentile: idx = (n-1)*p/100.
a = sort(double(a(:)));
n = numel(a);
if n == 1, v = a; return; end
x = (n - 1) * p / 100;
i = floor(x); fmid = x - i;
v = a(i + 1) * (1 - fmid) + a(min(i + 2, n)) * fmid;
end

function c = suspend_create_fcn()
%SUSPEND_CREATE_FCN Neutralize startup-installed figure CreateFcns for the run.
try, prev = get(groot, "defaultFigureCreateFcn"); catch, prev = "remove"; end
if isempty(prev), prev = "remove"; end
set(groot, "defaultFigureCreateFcn", "");
c = onCleanup(@() set(groot, "defaultFigureCreateFcn", prev));
end
