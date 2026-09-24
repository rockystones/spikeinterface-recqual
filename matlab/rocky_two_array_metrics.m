function M = rocky_two_array_metrics(repoRoot, opts)
%ROCKY_TWO_ARRAY_METRICS Rocky I1 two-array comparison, one metric per figure.
%
%   M = ROCKY_TWO_ARRAY_METRICS()  loads the table written by
%   notebooks/scratch_two_array_metrics.py, rebuilds the figures
%   (17 total units, 18 mean max unit amplitude, 19 channel yield; each
%   as session-resolved AND month-post-implant-binned) under
%   figures/matlab_repro/rocky/, and returns every table so each plotted
%   point can be traced to its session in the Variable Editor.
%
%   M = ROCKY_TWO_ARRAY_METRICS([], excludeOutliers=false)  keeps the 27
%   flagged sessions in the plots (they are then ringed in red instead).
%   The curated flag list itself lives in the Python generator (single
%   source of truth) and arrives here as the is_outlier/outlier_reason
%   columns; M.outliers lists the flagged sessions with reasons.
%
%   Scope: Rocky implant 1 only (Anterior = L1-coated, Posterior =
%   uncoated control); the 2025 I2 pair is excluded upstream.
%
% DATA DICTIONARY - the input table and what one row means.
%   data/derived/rocky/two_array_metrics.parquet is LONG format:
%   ONE ROW = one (metric, method, session-array). Columns:
%     metric   "n_units" | "mean_max_amp" | "yield_pct"
%     method   which sorting chain produced the units:
%                ofs           human Plexon sort, ALL its units (~332 s-a)
%                resort_gated  full-data ISO-SPLIT + physics gate (~332)
%                isosplit/gmm_bic/kmeans_sil/hdbscan   the 60-session
%                              methods subset, gated (subsample-clustered)
%                mountainsort5/kilosort4/spykingcircus2/tridesclous2
%                              modern sorters on continuous ns5 -
%                              n_units ONLY (their unit->channel map was
%                              never stored, so the two channel-resolved
%                              metrics exclude them)
%     date     session date (datetime after fixdates below). Some dates
%              carry TWO sessions per array (Analog + Digital headstage
%              pairs, e.g. 2019-05-23) - stem, not date, is the session
%              identity; lines can double back on such dates.
%     array    "Anterior" | "Posterior" - the array LABEL (I1 pair).
%     stem     the exact session name (recording file basename) - THE
%              traceability column this function exists to expose.
%     value    the metric value. 0 means "the method ran on this session
%              and found no units" (owner spec: zero, never NaN); a
%              session absent for a method was never attempted by it.
%     is_outlier / outlier_reason
%              curated manual-examination flag (robust-z sweep + the S09
%              noise screen + owner-named sessions; see the OUTLIERS dict
%              in scratch_two_array_metrics.py for the full rationale).
%     month_post
%              months post implant: floor(days since surgery 2017-08-30
%              / 30.44). The binned figures group by this integer and
%              take the MEDIAN of the session values inside each bin
%              (zeros included).
%
% Metric definitions (mirrored from the Python generator):
%   n_units       count of the method's (gated where applicable) units
%   mean_max_amp  per active channel take max over its units of
%                 P2P = peak_uv - trough_uv of the unit MEAN waveform,
%                 then mean across active channels. CAVEAT: peak-trough
%                 under-reads the exact global range on ~25% of units
%                 (docs/notes/longitudinal_metrics.md); the exact NEV
%                 recompute exists for ofs only
%                 (cohort/mean_max_p2p.parquet).
%   yield_pct     100 * (channels with >= 1 unit) / 96 wired channels
%
% Returned struct:
%   M.long    the full long table (all metrics, all methods)
%   M.units, M.amp, M.yield
%             one table per figure, sorted (method, array, date) - the
%             SAME order the lines are drawn in, so for a line
%             (method, array) its k-th plotted point is the k-th row of
%             that (method, array) block, and .stem on that row names
%             the session. E.g. to identify a point on figure 18:
%               g = M.amp(M.amp.method=="ofs" & M.amp.array=="Posterior",:)
%               g([...k...], ["date","stem","value"])
%   M.monthly one row per (metric, method, array, month_post) bin of
%             the monthly figures; ragged per-bin members in cell
%             columns values/stems/dates (row-aligned within a bin),
%             plus n_sessions / median_value (= the plotted point) /
%             mean_value. See the inline comment where it is built.

arguments
    repoRoot = fileparts(fileparts(mfilename("fullpath")))
    opts.excludeOutliers (1, 1) logical = true
end
if isempty(repoRoot)
    repoRoot = fileparts(fileparts(mfilename("fullpath")));
end
suspendCreateFcnGuard = suspend_create_fcn();                %#ok<NASGU>

t = parquetread(fullfile(repoRoot, "data", "derived", "rocky", ...
    "two_array_metrics.parquet"));
% parquet date arrives as datetime or string depending on writer version
if ~isdatetime(t.date), t.date = datetime(string(t.date)); end
t.is_outlier = logical(t.is_outlier);
t = sortrows(t, ["metric", "method", "array", "date"]);

M = struct();
M.long = t;
% the flagged sessions, one row each, for manual examination
M.outliers = unique(t(t.is_outlier, ...
    ["stem", "date", "array", "outlier_reason"]), "rows");
if opts.excludeOutliers
    t = t(~t.is_outlier, :);       % the plots below use the CLEAN set
end
M.units = t(t.metric == "n_units", :);
M.amp   = t(t.metric == "mean_max_amp", :);
M.yield = t(t.metric == "yield_pct", :);

% --- M.monthly: the raw values inside every month bin ---------------
% One row per (metric, method, array, month_post) - the same bins the
% monthly figures draw. Bins hold DIFFERENT numbers of sessions, so
% the per-bin members live in cell columns (RAGGED, nothing padded):
%   values{i}  [n_sessions x 1] double, the bin's session values in
%              date order (zeros included, per the zero-fill spec)
%   stems{i}   matching session names   } row j of values{i} is the
%   dates{i}   matching session dates   } same session as stems{i}(j)
% plus scalars n_sessions / median_value / mean_value. median_value is
% exactly what the monthly figure plots. Built AFTER the outlier
% filter, so it always matches the drawn figures; rerun with
% excludeOutliers=false to get bins that include the flagged sessions.
% Inspect one bin:
%   b = M.monthly(M.monthly.metric=="mean_max_amp" & ...
%       M.monthly.method=="ofs" & M.monthly.array=="Posterior" & ...
%       M.monthly.month_post==15, :);
%   [b.stems{1}, string(b.values{1})]
[gid, monthly] = findgroups(t(:, ["metric", "method", "array", ...
                                  "month_post"]));
% splitapply keeps t's row order (sorted by date above) inside each bin
monthly.values = splitapply(@(v) {v}, t.value, gid);
monthly.stems  = splitapply(@(s) {s}, t.stem,  gid);
monthly.dates  = splitapply(@(d) {d}, t.date,  gid);
monthly.n_sessions   = cellfun(@numel,  monthly.values);
monthly.median_value = cellfun(@median, monthly.values);
monthly.mean_value   = cellfun(@mean,   monthly.values);
M.monthly = sortrows(monthly, ["metric", "method", "array", ...
                               "month_post"]);

outDir = fullfile(repoRoot, "figures", "matlab_repro", "rocky");
if ~isfolder(outDir), mkdir(outDir); end

% one fixed color per method so the three figures stay comparable;
% array is encoded by line style (Anterior solid, Posterior dashed)
methods = ["ofs", "resort_gated", "isosplit", "gmm_bic", "kmeans_sil", ...
           "hdbscan", "mountainsort5", "kilosort4", "spykingcircus2", ...
           "tridesclous2"];
cmap = lines(numel(methods));            % row k colors methods(k)
sty = dictionary(["Anterior", "Posterior"], ["-", "--"]);

specs = {M.units, "total sorted units per array",              "units", ...
         "17_n_units_by_method.png"; ...
         M.amp,   "mean max unit amplitude over active channels", ...
         "P2P of unit mean waveform (\muV)", "18_mean_max_amp_by_method.png"; ...
         M.yield, "channel yield",  "% of 96 channels with a unit", ...
         "19_channel_yield_by_method.png"};

excl = "outliers excluded";
if ~opts.excludeOutliers, excl = "red rings = flagged sessions"; end

for k = 1:size(specs, 1)
    d = specs{k, 1};

    % --- session-resolved figure ------------------------------------
    f = figure(Visible="off", Position=[60 60 1150 470]); hold on;
    for mi = 1:numel(methods)
        for arr = ["Anterior", "Posterior"]
            % g holds this line's points in DRAW ORDER (sorted by date
            % above); g.stem(j) names the session behind point j
            g = d(d.method == methods(mi) & d.array == arr, :);
            if isempty(g), continue; end
            plot(g.date, g.value, sty(arr), Color=cmap(mi, :), ...
                LineWidth=0.9, DisplayName=methods(mi) + " " + arr);
            if ~opts.excludeOutliers
                o = g(g.is_outlier, :);      % ring the flagged sessions
                plot(o.date, o.value, "o", MarkerSize=5, ...
                    MarkerEdgeColor="r", HandleVisibility="off");
            end
        end
    end
    hold off; grid on; ylabel(specs{k, 3});
    title({"Rocky I1: " + specs{k, 2}; ...
        "solid = Anterior (coated), dashed = Posterior (uncoated); " + excl});
    legend(Location="northeast", FontSize=6, NumColumns=4);
    export_png(f, fullfile(outDir, specs{k, 4}));
    close(f);
    fprintf("  wrote %s\n", specs{k, 4});

    % --- month-post-implant binned figure ---------------------------
    % per (method, array): groupsummary collapses each month_post bin
    % to the MEDIAN of its session values (zeros included); the bin's
    % member sessions remain traceable by filtering the per-metric
    % table on month_post
    f = figure(Visible="off", Position=[60 60 1150 470]); hold on;
    for mi = 1:numel(methods)
        for arr = ["Anterior", "Posterior"]
            g = d(d.method == methods(mi) & d.array == arr, :);
            if isempty(g), continue; end
            b = groupsummary(g, "month_post", "median", "value");
            plot(b.month_post, b.median_value, sty(arr), ...
                Color=cmap(mi, :), LineWidth=0.9, Marker="o", ...
                MarkerSize=2.5, DisplayName=methods(mi) + " " + arr);
        end
    end
    hold off; grid on; ylabel(specs{k, 3});
    xlabel("months post implant (30.44-day bins from 2017-08-30)");
    title({"Rocky I1: " + specs{k, 2} + ", monthly bins"; ...
        "solid = Anterior (coated), dashed = Posterior (uncoated); " + ...
        excl + "; median per bin"});
    legend(Location="northeast", FontSize=6, NumColumns=4);
    name = replace(specs{k, 4}, ".png", "_monthly.png");
    export_png(f, fullfile(outDir, name));
    close(f);
    fprintf("  wrote %s\n", name);
end
fprintf("tables in M.long / M.units / M.amp / M.yield (stem = session); " + ...
    "M.outliers = flagged sessions; M.monthly = per-bin raw values\n");
end


function export_png(f, path)
%EXPORT_PNG exportgraphics with retries - an AV/indexer scan can hold a
% freshly written PNG open for a moment and make the next write fail
% with "PNG library failed: Could not open file".
for attempt = 1:4
    try
        exportgraphics(f, path, Resolution=150);
        return
    catch err
        if attempt == 4, rethrow(err); end
        pause(1.5 * attempt);
    end
end
end


function c = suspend_create_fcn()
%SUSPEND_CREATE_FCN Neutralize startup-installed figure CreateFcns for the run.
try, prev = get(groot, "defaultFigureCreateFcn"); catch, prev = "remove"; end
if isempty(prev), prev = "remove"; end
set(groot, "defaultFigureCreateFcn", "");
c = onCleanup(@() set(groot, "defaultFigureCreateFcn", prev));
end
