function M = rocky_two_array_metrics(repoRoot)
%ROCKY_TWO_ARRAY_METRICS Rocky I1 two-array comparison, one metric per figure.
%
%   M = ROCKY_TWO_ARRAY_METRICS()  loads the table written by
%   notebooks/scratch_two_array_metrics.py, rebuilds the three figures
%   (17 total units, 18 mean max unit amplitude, 19 channel yield) under
%   figures/matlab_repro/rocky/, and returns every table so each plotted
%   point can be traced to its session in the Variable Editor.
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

if nargin < 1
    repoRoot = fileparts(fileparts(mfilename("fullpath")));
end
suspendCreateFcnGuard = suspend_create_fcn();                %#ok<NASGU>

t = parquetread(fullfile(repoRoot, "data", "derived", "rocky", ...
    "two_array_metrics.parquet"));
% parquet date arrives as datetime or string depending on writer version
if ~isdatetime(t.date), t.date = datetime(string(t.date)); end
t = sortrows(t, ["metric", "method", "array", "date"]);

M = struct();
M.long  = t;
M.units = t(t.metric == "n_units", :);
M.amp   = t(t.metric == "mean_max_amp", :);
M.yield = t(t.metric == "yield_pct", :);

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

for k = 1:size(specs, 1)
    d = specs{k, 1};
    f = figure(Visible="off", Position=[60 60 1150 470]); hold on;
    for mi = 1:numel(methods)
        for arr = ["Anterior", "Posterior"]
            % g holds this line's points in DRAW ORDER (sorted by date
            % above); g.stem(j) names the session behind point j
            g = d(d.method == methods(mi) & d.array == arr, :);
            if isempty(g), continue; end
            plot(g.date, g.value, sty(arr), Color=cmap(mi, :), ...
                LineWidth=0.9, DisplayName=methods(mi) + " " + arr);
        end
    end
    hold off; grid on; ylabel(specs{k, 3});
    title({"Rocky I1: " + specs{k, 2}; ...
        "solid = Anterior (coated), dashed = Posterior (uncoated); " + ...
        "0 = attempted, no units"});
    legend(Location="northeast", FontSize=6, NumColumns=4);
    exportgraphics(f, fullfile(outDir, specs{k, 4}), Resolution=150);
    close(f);
    fprintf("  wrote %s\n", specs{k, 4});
end
fprintf("tables in M.long / M.units / M.amp / M.yield (stem = session)\n");
end


function c = suspend_create_fcn()
%SUSPEND_CREATE_FCN Neutralize startup-installed figure CreateFcns for the run.
try, prev = get(groot, "defaultFigureCreateFcn"); catch, prev = "remove"; end
if isempty(prev), prev = "remove"; end
set(groot, "defaultFigureCreateFcn", "");
c = onCleanup(@() set(groot, "defaultFigureCreateFcn", prev));
end
