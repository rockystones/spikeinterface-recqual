function T = rocky_reproduce_figures(repoRoot)
%ROCKY_REPRODUCE_FIGURES Rebuild the figures/rocky analysis figures in MATLAB.
%
%   T = ROCKY_REPRODUCE_FIGURES()  loads every Rocky table (rocky_load_tables),
%   reproduces the derived-data figure families under
%   figures/matlab_repro/rocky/, and returns the table struct so the exact
%   data behind each panel stays in the workspace for inspection.
%
%   These are CONTENT reproductions: same tables, same groupings, same
%   quantities and statistics as the Python originals; styling differs.
%   The authoritative generator for each family is named in the console
%   output and in comments below. Statistics follow the project's
%   aggregation rule (CLAUDE.md; nav D-002): per-session ratios first,
%   medians across sessions, never pooled numerators/denominators.
%
%   Reproduced here (from Parquet/NPZ alone):
%     05 yield, 06 snr, 07 resort-vs-ofs, 08 impedance-vs-yield,
%     10 impedance QC, 11 spatial maps, 12 bank breakdown, 13 metric trends,
%     14 method agreement, 15 curation comparison, cohort C1-C3,
%     longitudinal L1-L5, sensitivity S1-S2, giants G1/G2/G5.
%   NOT reproduced (need the raw NEV/ns5 estate, not the derived tables):
%     deepdive T1-T3   -> notebooks/scratch_rocky_deepdive.py
%     evidence E1-E7   -> notebooks/scratch_rocky_evidence.py
%     session_preview  -> notebooks/scratch_session_preview.py

if nargin < 1
    repoRoot = fileparts(fileparts(mfilename("fullpath")));
end
T = rocky_load_tables(repoRoot);
outDir = fullfile(repoRoot, "figures", "matlab_repro", "rocky");
if ~isfolder(outDir), mkdir(outDir); end

fig05_06_yield_snr(T, outDir);        % scratch_rocky_longitudinal.py
fig07_resort_vs_ofs(T, outDir);       % scratch_rocky_longitudinal.py
fig08_impedance_vs_yield(T, outDir);  % scratch_rocky_longitudinal.py
fig10_impedance_qc(T, outDir);        % scratch_rocky_impedance_qc.py
fig11_spatial_maps(T, outDir);        % scratch_rocky_spatial.py
fig12_bank_breakdown(T, outDir);      % scratch_rocky_spatial.py
fig13_metric_trends(T, outDir);       % scratch_rocky_spatial.py
fig14_method_agreement(T, outDir);    % scratch_rocky_agreement.py
fig15_curation(T, outDir);            % scratch_rocky_curation.py
figC_cohort(T, outDir);               % scratch_cohort_figures.py
figL_longitudinal(T, outDir);         % scratch_rocky_longitudinal_metrics.py
figS_sensitivity(T, outDir);          % scratch_rocky_sensitivity.py
figG_giants(T, outDir, repoRoot);     % scratch_rocky_giants.py

fprintf("\nNot reproducible from derived tables (raw-estate figures):\n");
fprintf("  deepdive T1-T3, evidence E1-E7, session_preview (914 files)\n");
fprintf("Done. Output: %s\n", outDir);
end


% === helpers =============================================================
function done(f, outDir, name)
exportgraphics(f, fullfile(outDir, name), "Resolution", 150);
close(f);
fprintf("  wrote %s\n", name);
end

function [g, keys] = groupmedian(t, keyVars, valVar)
%GROUPMEDIAN median of one column per group, NaN-safe.
[gidx, keys] = findgroups(t(:, keyVars));
g = splitapply(@(x) median(x, "omitnan"), t.(valVar), gidx);
end


% === 05 / 06: yield and SNR over time (resort method) ====================
function fig05_06_yield_snr(T, outDir)
s = T.session_summary(T.session_summary.method == "resort", :);
specs = {"units_per_electrode", "sorted units per electrode", "05_yield_over_time.png"; ...
         "median_snr",          "median unit SNR",            "06_snr_over_time.png"};
for k = 1:size(specs, 1)
    f = figure(Visible="off", Position=[80 80 900 420]);
    hold on;
    arrays = unique(s.array);
    for a = arrays'
        g = sortrows(s(s.array == a, :), "date");
        plot(g.date, g.(specs{k, 1}), "-o", MarkerSize=3, DisplayName=a);
    end
    hold off; grid on; legend(Location="best");
    ylabel(specs{k, 2}); title(specs{k, 2} + ", Rocky I1 (resort)");
    done(f, outDir, specs{k, 3});
end
end


% === 07: our resort against the Plexon reference =========================
function fig07_resort_vs_ofs(T, outDir)
rs = T.session_summary(T.session_summary.method == "resort", ...
                       ["date", "array", "n_units"]);
of = T.session_metrics_ofs(:, ["date", "array", "n_units"]);
of.Properties.VariableNames{"n_units"} = 'n_units_ofs';
j = innerjoin(rs, of, Keys=["date", "array"]);
f = figure(Visible="off", Position=[80 80 520 480]); hold on;
for a = unique(j.array)'
    g = j(j.array == a, :);
    scatter(g.n_units_ofs, g.n_units, 14, "filled", DisplayName=a);
end
lim = [0, max([j.n_units; j.n_units_ofs])];
plot(lim, lim, "k--", DisplayName="unity");
hold off; grid on; axis equal; xlim(lim); ylim(lim);
xlabel("Plexon OFS units / session"); ylabel("resort units / session");
r = corr(j.n_units_ofs, j.n_units, Type="Spearman", Rows="complete");
title(sprintf("resort vs Plexon reference (rho = %.2f, n = %d)", r, height(j)));
legend(Location="northwest");
done(f, outDir, "07_resort_vs_ofs.png");
end


% === 08: impedance against yield =========================================
function fig08_impedance_vs_yield(T, outDir)
% per array-date median log10 |Z| at 1 kHz, joined to the nearest resort
% session within 45 days (same nearest-date rule as the Python original)
imp = T.impedance;
imp.logz = log10(max(imp.z_1khz_ohm, 1));
[zmed, zk] = groupmedian(imp, ["date", "array"], "logz");
s = T.session_summary(T.session_summary.method == "resort", :);
rows = [];
for i = 1:height(zk)
    g = s(s.array == zk.array(i), :);
    [dmin, j] = min(abs(days(g.date - zk.date(i))));
    if dmin <= 45
        rows = [rows; table(zk.array(i), zmed(i), g.units_per_electrode(j), ...
            VariableNames=["array", "logz", "upe"])]; %#ok<AGROW>
    end
end
f = figure(Visible="off", Position=[80 80 560 460]); hold on;
for a = unique(rows.array)'
    g = rows(rows.array == a, :);
    scatter(g.logz, g.upe, 22, "filled", DisplayName=a);
end
hold off; grid on;
xlabel("median log_{10} |Z| at 1 kHz (array-date)");
ylabel("sorted units per electrode (nearest session)");
r = corr(rows.logz, rows.upe, Type="Spearman", Rows="complete");
title(sprintf("impedance vs yield, %d paired array-dates (rho = %.2f)", ...
    height(rows), r));
legend(Location="best");
done(f, outDir, "08_impedance_vs_yield.png");
end


% === 10: impedance QC ====================================================
function fig10_impedance_qc(T, outDir)
q = sortrows(T.impedance_qc, "date");
f = figure(Visible="off", Position=[80 80 900 420]); hold on;
for a = unique(q.array)'
    g = q(q.array == a, :);
    plot(g.date, g.z_median, "-o", MarkerSize=3, DisplayName=a);
    flagged = g(g.n_flags > 0, :);
    scatter(flagged.date, flagged.z_median, 60, "r", "x", ...
        DisplayName=a + " flagged", LineWidth=1.2);
end
hold off; grid on; set(gca, YScale="log");
ylabel("median |Z| at 1 kHz (ohm)");
title("potentiostat QC: level per array-date, flags marked");
legend(Location="best");
done(f, outDir, "10_impedance_qc.png");
end


% === 11: spatial yield maps ==============================================
function fig11_spatial_maps(T, outDir)
e = T.electrode_summary;
years = unique(e.year)'; arrays = unique(e.array)';
f = figure(Visible="off", Position=[60 60 170 * numel(years) 420]);
tl = tiledlayout(numel(arrays), numel(years), TileSpacing="compact");
for ai = 1:numel(arrays)
    for yi = 1:numel(years)
        g = e(e.array == arrays(ai) & e.year == years(yi), :);
        M = nan(10, 10);
        M(sub2ind([10 10], g.row + 1, g.col + 1)) = g.units_per_session;
        nexttile; imagesc(M, AlphaData=~isnan(M)); axis image; axis xy;
        set(gca, XTick=[], YTick=[]);
        if ai == 1, title(string(years(yi)), FontSize=8); end
        if yi == 1, ylabel(arrays(ai), FontSize=8); end
    end
end
cb = colorbar; cb.Layout.Tile = "east"; cb.Label.String = "units / session";
title(tl, "sorted yield per electrode (CMP position), by year");
done(f, outDir, "11_spatial_yield_maps.png");
end


% === 12: bank breakdown ==================================================
function fig12_bank_breakdown(T, outDir)
e = T.electrode_summary;
f = figure(Visible="off", Position=[80 80 760 380]);
tl = tiledlayout(1, 2, TileSpacing="compact");
for a = unique(e.array)'
    nexttile; hold on;
    for b = unique(e.bank)'
        g = e(e.array == a & e.bank == b, :);
        [m, k] = groupmedian(g, "year", "units_per_session");
        plot(k.year, m, "-o", DisplayName="bank " + b);
    end
    hold off; grid on; title(a); xlabel("year");
    ylabel("median units / session / electrode"); legend;
end
title(tl, "yield by connector bank (electrode medians per year)");
done(f, outDir, "12_bank_breakdown.png");
end


% === 13: metric trends ===================================================
function fig13_metric_trends(T, outDir)
L = sortrows(T.longitudinal, "date");
specs = {"units_per_electrode", "units / electrode"; ...
         "amp_med",             "median amplitude (uV)"; ...
         "noise_med_free",      "noise floor, free layer (uV)"; ...
         "crossing_rate_med",   "median crossing rate (Hz)"};
f = figure(Visible="off", Position=[60 60 980 620]);
tl = tiledlayout(2, 2, TileSpacing="compact");
for k = 1:size(specs, 1)
    nexttile; hold on;
    for a = unique(L.array)'
        g = L(L.array == a, :);
        plot(g.date, g.(specs{k, 1}), "-", DisplayName=a);
        tr = T.trends(T.trends.array == a & T.trends.column == specs{k, 1}, :);
        if ~isempty(tr)
            text(g.date(end), g.(specs{k, 1})(end), ...
                sprintf(" \\rho=%.2f", tr.rho(1)), FontSize=7);
        end
    end
    hold off; grid on; ylabel(specs{k, 2}); legend(Location="best");
end
title(tl, "longitudinal metrics, sorted + sorting-free layers");
done(f, outDir, "13_metric_trends.png");
end


% === 14: method agreement (ARI) ==========================================
function fig14_method_agreement(T, outDir)
ag = T.agreement;
methods = unique([ag.method_a; ag.method_b]);
n = numel(methods); M = nan(n);
for i = 1:n
    for j = 1:n
        m = ag.ari(ag.method_a == methods(i) & ag.method_b == methods(j) | ...
                   ag.method_a == methods(j) & ag.method_b == methods(i));
        if ~isempty(m), M(i, j) = median(m, "omitnan"); end
    end
end
f = figure(Visible="off", Position=[80 80 520 460]);
imagesc(M, [0 1]); colorbar; axis image;
set(gca, XTick=1:n, XTickLabel=methods, YTick=1:n, YTickLabel=methods, ...
    XTickLabelRotation=30);
for i = 1:n
    for j = 1:n
        if ~isnan(M(i, j))
            text(j, i, sprintf("%.2f", M(i, j)), HorizontalAlignment="center", ...
                FontSize=8, Color=[1 1 1] * (M(i, j) < 0.5));
        end
    end
end
title("median per-channel ARI between snippet-sorting methods");
done(f, outDir, "14_method_agreement.png");
end


% === 15: curation comparison =============================================
function fig15_curation(T, outDir)
% aggregation rule: per-session fractions first, then the median across
% sessions - never pooled unit counts (nav D-002)
c = T.curation;
c.ur_neural = logical(c.ur_neural);
c.pass_gate = logical(c.pass_gate);
methods = unique(c.method); nm = numel(methods);
gateMed = nan(nm, 1); urMed = nan(nm, 1);
for k = 1:nm
    g = c(c.method == methods(k), :);
    [gi, ~] = findgroups(g(:, ["date", "array"]));
    gateMed(k) = median(splitapply(@mean, double(g.pass_gate), gi));
    urMed(k)   = median(splitapply(@mean, double(g.ur_neural), gi));
end
f = figure(Visible="off", Position=[80 80 640 400]);
bar(categorical(methods), [gateMed, urMed]);
legend(["physics gate pass", "UnitRefine 'neural'"], Location="best");
ylabel("median per-session fraction of units");
title({"curation layers per method"; ...
    "(UR is documented unusable on snippets - shown for the record, nav D-004)"});
grid on;
done(f, outDir, "15_curation_comparison.png");
end


% === cohort C1-C3 ========================================================
function figC_cohort(T, outDir)
co = T.cohort(T.cohort.subject == "Rocky", :);
for imp = ["I1", "I2"]
    g = sortrows(co(co.implant == imp, :), "date");
    if isempty(g), continue; end
    f = figure(Visible="off", Position=[80 80 860 420]); hold on;
    for a = unique(g.array)'
        gg = g(g.array == a, :);
        plot(gg.date, gg.units_per_electrode, "-o", MarkerSize=3, DisplayName=a);
    end
    hold off; grid on; ylabel("units per electrode"); legend;
    title("cohort yield, Rocky " + imp);
    done(f, outDir, "C1_yield_Rocky_" + imp + ".png");

    f = figure(Visible="off", Position=[60 60 980 620]);
    tl = tiledlayout(2, 2, TileSpacing="compact");
    specs = {"noise_med", "noise (uV)"; "amp_med", "amplitude (uV)"; ...
             "snr_med", "SNR"; "elec_coverage", "electrode coverage"};
    for k = 1:4
        nexttile; hold on;
        for a = unique(g.array)'
            gg = g(g.array == a, :);
            plot(gg.date, gg.(specs{k, 1}), "-", DisplayName=a);
        end
        hold off; grid on; ylabel(specs{k, 2}); legend(Location="best");
    end
    title(tl, "cohort metrics, Rocky " + imp);
    done(f, outDir, "C2_metrics_Rocky_" + imp + ".png");

    f = figure(Visible="off", Position=[80 80 860 380]); hold on;
    ok = g(~g.high_noise, :); bad = g(logical(g.high_noise), :);
    scatter(ok.date, ok.noise_med, 16, "filled", DisplayName="kept");
    scatter(bad.date, bad.noise_med, 30, "r", "x", DisplayName="high-noise screened");
    hold off; grid on; ylabel("session noise median (uV)");
    title("acquisition screen, Rocky " + imp); legend;
    done(f, outDir, "C3_screen_Rocky_" + imp + ".png");
end
end


% === longitudinal L1-L5 ==================================================
function figL_longitudinal(T, outDir)
L = sortrows(T.longitudinal, "date");
arrays = unique(L.array)';

    function panelset(specs, name, ttl)
        f = figure(Visible="off", Position=[60 60 980 320 * size(specs, 1)]);
        tl = tiledlayout(size(specs, 1), 1, TileSpacing="compact");
        for k = 1:size(specs, 1)
            nexttile; hold on;
            for a = arrays
                g = L(L.array == a, :);
                plot(g.date, g.(specs{k, 1}), "-", DisplayName=a);
            end
            hold off; grid on; ylabel(specs{k, 2}); legend(Location="best");
        end
        title(tl, ttl);
        done(f, outDir, name);
    end

panelset({"n_units", "units"; "amp_med", "amp med (uV)"; "snr_med", "SNR med"}, ...
    "L1_sorted_metrics.png", "sorted layer");
panelset({"crossing_rate_med", "crossing rate (Hz)"; ...
          "noise_med_free", "noise, free (uV)"; ...
          "peak_snr_clean_med", "peak SNR (clean)"}, ...
    "L2_free_metrics.png", "sorting-free layer");
panelset({"free_amp_p99_clean", "free p99 clean (uV)"; ...
          "free_amp_max_clean", "free max clean (uV)"}, ...
    "L3_amplitude_tail.png", "amplitude tail");

f = figure(Visible="off", Position=[60 60 900 380]);
tl = tiledlayout(1, 2, TileSpacing="compact");
for a = arrays
    g = L(L.array == a, :);
    nexttile; hold on;
    fill([g.date; flipud(g.date)], [g.amp_p10; flipud(g.amp_p90)], ...
        [0.6 0.7 0.9], FaceAlpha=0.4, EdgeColor="none", DisplayName="p10-p90");
    plot(g.date, g.amp_med, "b-", DisplayName="median");
    plot(g.date, g.amp_p99, "r-", DisplayName="p99");
    hold off; grid on; title(a); ylabel("unit amplitude (uV)");
    legend(Location="best");
end
title(tl, "sorted amplitude distribution over time");
done(f, outDir, "L4_amplitude_distribution.png");

f = figure(Visible="off", Position=[80 80 520 460]); hold on;
for a = arrays
    g = L(L.array == a, :);
    scatter(g.crossing_rate_med, g.units_per_electrode, 16, "filled", DisplayName=a);
end
hold off; grid on;
xlabel("median crossing rate (Hz, sorting-free)");
ylabel("units per electrode (sorted)");
r = corr(L.crossing_rate_med, L.units_per_electrode, ...
    Type="Spearman", Rows="complete");
title(sprintf("layer agreement (rho = %.2f, n = %d sessions)", r, height(L)));
legend(Location="best");
done(f, outDir, "L5_layer_agreement.png");
end


% === sensitivity S ======================================================
function figS_sensitivity(T, outDir)
s = sortrows(T.sens_sweep, "date");
f = figure(Visible="off", Position=[60 60 980 400]);
tl = tiledlayout(1, 2, TileSpacing="compact");
for a = unique(s.array)'
    nexttile; hold on;
    for v = unique(s.variant)'
        g = s(s.array == a & s.variant == v, :);
        plot(g.date, g.units_per_electrode, "-", DisplayName=v);
    end
    hold off; grid on; title(a); ylabel("units / electrode");
    legend(Location="best", FontSize=6);
end
title(tl, "gate-sensitivity sweep: yield under each variant");
done(f, outDir, "S1_gate_sweep.png");

r = T.sens_rho(T.sens_rho.column == "units_per_electrode", :);
f = figure(Visible="off", Position=[80 80 760 380]); hold on;
arrays = unique(r.array)';
for ai = 1:numel(arrays)
    g = r(r.array == arrays(ai), :);
    scatter(ai * ones(height(g), 1) + 0.12 * randn(height(g), 1), g.rho, ...
        26, "filled", DisplayName=arrays(ai));
end
hold off; grid on; xlim([0.5, numel(arrays) + 0.5]);
set(gca, XTick=1:numel(arrays), XTickLabel=arrays);
ylabel("Spearman \rho of the yield trend");
title("trend stability across gate variants (each dot = one variant)");
done(f, outDir, "S2_trend_stability.png");
end


% === giants G ============================================================
function figG_giants(T, outDir, repoRoot)
g = T.giants;
% G1 taxonomy: per-session class shares, then the median across sessions
classes = unique(g.klass); arrays = unique(g.array)';
M = nan(numel(classes), numel(arrays));
for ai = 1:numel(arrays)
    ga = g(g.array == arrays(ai), :);
    [gi, keys] = findgroups(ga(:, "stem"));           %#ok<ASGLU>
    for ci = 1:numel(classes)
        share = splitapply(@(k) mean(k == classes(ci)), ga.klass, gi);
        M(ci, ai) = median(share);
    end
end
f = figure(Visible="off", Position=[80 80 700 400]);
bar(categorical(classes), M);
legend(arrays, Location="best"); grid on;
ylabel("median per-session share of giant events");
title("giant-event taxonomy (aggregation rule: per-session, then median)");
done(f, outDir, "G1_taxonomy.png");

% G5 where/when: recurring sites
st = T.giant_sites;
f = figure(Visible="off", Position=[60 60 900 420]);
tl = tiledlayout(1, 2, TileSpacing="compact");
for a = unique(st.array)'
    s = sortrows(st(st.array == a, :), "channel_id");
    ch = double(s.channel_id);            % parquet int64 resists double math
    nexttile; hold on;
    for i = 1:height(s)
        plot(datetime([s.first(i), s.last(i)]), ch(i) * [1 1], ...
            "-", Color=[0.3 0.3 0.8], LineWidth=0.8);
    end
    scatter(datetime(s.first), ch, 8 + 2 * sqrt(double(s.n_events)), ...
        "filled", MarkerFaceAlpha=0.6);
    hold off; grid on; title(a); ylabel("channel id");
    xlabel("site active span (dot size ~ events)");
end
title(tl, "recurring giant-event sites: where and when");
done(f, outDir, "G5_where_when.png");

% G2 gallery: waveforms from the npz shard holding the largest event
[~, imax] = max(abs(g.abs_amp_uv));
shard = fullfile(repoRoot, "data", "derived", "rocky", "giant_wf_shards", ...
    string(g.date(imax), "yyyy-MM-dd") + "_" + g.array(imax) + ".npz");
try
    wf = read_npz_array(shard, "wf");
    f = figure(Visible="off", Position=[60 60 900 620]);
    tl = tiledlayout(4, 6, TileSpacing="compact");
    for k = 1:min(24, size(wf, 1))
        ax = nexttile; plot(ax, wf(k, :), "k-", LineWidth=1);
        axis(ax, "tight"); set(ax, XTick=[], YTick=[]); box(ax, "on");
    end
    title(tl, "giant-event waveform gallery, session " + ...
        string(g.date(imax), "yyyy-MM-dd") + " " + g.array(imax));
    done(f, outDir, "G2_gallery.png");
catch err
    fprintf("  ! G2 gallery skipped (%s)\n", err.message);
end
end
