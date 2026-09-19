%% rocky_outlier_inspect.m
% Interactive inspection of Rocky's potential-outlier sessions.
%
% WORKFLOW (the "decide" step lives here):
%   1. Browse the PNG previews in figures/rocky/outlier_preview/.
%   2. List the stems you want to look at closer in sessionsToInspect
%      below (or 'all'). Run this script.
%   3. Per chosen session it regenerates the figure as a NATIVE .fig
%      (zoomable, editable) in figures/rocky/outlier_inspect/ and
%      loads the unit + metric data into the workspace (struct M).
%
% DATA SOURCE: data/derived/rocky/outlier_inspect/<stem>/ written by
% notebooks/scratch_outlier_inspect.py from the sorted NEV (-01 chain
% where it exists, original otherwise). All parquet/JSON - no pickle.
%
% ===================== WORKSPACE DATA DICTIONARY =====================
% idx  : table, one row per exported candidate session -
%        stem / chain / date / array / reason / n_units. This is the
%        menu; copy stems from here into sessionsToInspect.
% M    : struct array, one element per INSPECTED session, fields:
%   .stem, .reason, .chain, .date, .array   identity (chain '-01' =
%        Plexon OFS automatic; '' = original unsorted file)
%   .units   table, ONE ROW PER SORTED UNIT. Columns:
%        channel_id  Blackrock electrode ID (NOT a matrix index; IDs
%                    can be non-contiguous)
%        col, row    physical CMP position, 0-BASED as Python wrote
%                    them; +1 wherever they index a MATLAB grid below
%        unit        Plexon unit class on that channel (1..N)
%        n_spikes    waveforms averaged into this unit
%        p2p_uv      max-min of the MEAN waveform (the owner's
%                    definition, D-013)
%        noise_uv    channel baseline noise (MAD-based, pre-trigger)
%   .wf_mean : [nUnits x nSamples] double, uV. ROW k IS units ROW k -
%        the alignment is positional, there is no key column; never
%        sort one without the other.
%   .wf_lo, .wf_hi : same shape - per-sample min/max ENVELOPE of the
%        unit's waveform cloud (not a std band).
%   .free : struct, sorting-free session metrics (crossing rate,
%        noise floor, amplitude percentiles) - no labels involved.
%   .geometry : table of ALL wired electrodes (channel_id, col, row,
%        label), including channels with zero units; grid cells
%        absent here are physically unconnected.
%   .metrics : long-format slice of two_array_metrics.parquet for
%        this stem - metric / method / value / is_outlier /
%        outlier_reason. One row per (metric, method).
%   .units_iso, .wf_mean_iso/.wf_lo_iso/.wf_hi_iso : the ISO-SPLIT
%        resort layer (gated units only, method 'resort_gated'), same
%        column meanings and the same POSITIONAL row alignment as the
%        ofs fields; [] where not yet exported. opts.method
%        ('ofs'|'isosplit') picks which layer the FIGURE draws - the
%        workspace always carries both. Isosplit waveforms are
%        trough-ALIGNED copies (the clusters were formed on them).
%   .t_ms : [1 x nSamples] time axis, ms relative to trigger
%        (sample nbefore+1 = trigger = 0 ms).
%
% FIGURE (per session, same panels as the Python preview 2-4):
%   left  : unit mean waveforms drawn AT PHYSICAL ARRAY POSITIONS
%           (10x10 CMP grid, wire bundle to the right), fixed
%           ylim [-200 200] uV so panels compare across sessions
%   right top    : units per electrode grid (hot, caxis [0 6])
%   right bottom : per-channel max p2p grid (hot, caxis [0 600])
%   Both grids: axis xy so row 0 is at the BOTTOM (CMP convention);
%   grey cells with X = unconnected positions; 0 = a real
%   measurement of nothing.
% =====================================================================

%% ------------------- EDIT THIS: sessions to inspect ----------------
% Stems exactly as in idx.stem / the preview filenames. 'all' takes
% every exported candidate (31 figures - browsable but slow).
% A sessionsToInspect variable ALREADY IN THE WORKSPACE wins over the
% default below, so you can also do:
%   >> sessionsToInspect = {'<stem1>', '<stem2>'}; rocky_outlier_inspect
if ~exist('sessionsToInspect', 'var')
    sessionsToInspect = { ...
        'Rocky_Posterior_05-23-2019_Baseline_AnalogHeadstage' ...
        };
    % sessionsToInspect = 'all';
end

if ~exist('opts', 'var'), opts = struct(); end
if ~isfield(opts, 'saveFig'),   opts.saveFig = true;    end % write .fig
if ~isfield(opts, 'closeFigs'), opts.closeFigs = false; end % keep windows
% Which sorting layer drives the FIGURE: 'ofs' = Plexon unit labels
% from the -01 NEV; 'isosplit' = the project's resort (gated units
% only, method resort_gated). BOTH layers are always loaded into M
% when their files exist (.units/.wf_* = ofs, .units_iso/.wf_*_iso =
% isosplit); the option only picks what gets drawn.
if ~isfield(opts, 'method'),    opts.method = 'ofs';    end

%% ------------------------------ setup ------------------------------
thisDir  = fileparts(mfilename('fullpath'));
repoRoot = fileparts(thisDir);
dataDir  = fullfile(repoRoot, 'data', 'derived', 'rocky', 'outlier_inspect');
figDir   = fullfile(repoRoot, 'figures', 'rocky', 'outlier_inspect');
if ~exist(figDir, 'dir'), mkdir(figDir); end

idx = struct2table(jsondecode(fileread(fullfile(dataDir, 'index.json'))));
fprintf('%d candidate sessions exported (see idx)\n', height(idx));

% full metrics table once; sliced per stem below
allMetrics = parquetread(fullfile(repoRoot, 'data', 'derived', ...
    'rocky', 'two_array_metrics.parquet'));

if ischar(sessionsToInspect) && strcmp(sessionsToInspect, 'all')
    sessionsToInspect = cellstr(idx.stem);
end

%% --------------------------- inspection ----------------------------
M = struct([]);
for k = 1:numel(sessionsToInspect)
    stem = sessionsToInspect{k};
    sdir = fullfile(dataDir, stem);
    assert(isfolder(sdir), 'not exported: %s (check idx.stem)', stem);

    meta  = jsondecode(fileread(fullfile(sdir, 'session.json')));
    if meta.n_units > 0
        units = parquetread(fullfile(sdir, 'units.parquet'));
        % table2array: parquet columns s000..sNNN in order -> matrix
        % whose row k is unit row k of `units` (positional alignment)
        wfM = table2array(parquetread(fullfile(sdir, 'wf_mean.parquet')));
        wfL = table2array(parquetread(fullfile(sdir, 'wf_lo.parquet')));
        wfH = table2array(parquetread(fullfile(sdir, 'wf_hi.parquet')));
    else
        % the two Dec-2018 blowup stems exist only UNSORTED (no -01
        % NEV), so they carry crossings but zero Plexon units
        units = table('Size', [0 7], 'VariableTypes', ...
            repmat("double", 1, 7), 'VariableNames', ...
            {'channel_id','col','row','unit','n_spikes', ...
             'p2p_uv','noise_uv'});
        wfM = zeros(0, max(meta.n_samples, 1));
        wfL = wfM; wfH = wfM;
    end
    geo = struct2table(meta.geometry);

    % time axis: sample nbefore+1 is the trigger (0 ms)
    sr  = meta.free.sr;                 % Hz, from the NEV header
    t_ms = ((0:meta.n_samples-1) - meta.free.nbefore) / sr * 1e3;
    if isempty(t_ms), t_ms = [0 1]; end   % zero-unit sessions

    M(k).stem = stem;            M(k).reason = meta.reason;
    M(k).chain = meta.chain;     M(k).date = meta.date;
    M(k).array = meta.array;     M(k).units = units;
    M(k).wf_mean = wfM; M(k).wf_lo = wfL; M(k).wf_hi = wfH;
    M(k).free = meta.free;       M(k).geometry = geo;
    M(k).metrics = allMetrics(strcmp(allMetrics.stem, stem), :);
    M(k).t_ms = t_ms;

    % ISO-SPLIT resort layer (written by scratch_outlier_isosplit.py;
    % gated units only, same row alignment rules as the ofs files)
    isoFile = fullfile(sdir, 'units_iso.parquet');
    if isfile(isoFile)
        M(k).units_iso = parquetread(isoFile);
        M(k).wf_mean_iso = table2array(parquetread( ...
            fullfile(sdir, 'wf_mean_iso.parquet')));
        M(k).wf_lo_iso = table2array(parquetread( ...
            fullfile(sdir, 'wf_lo_iso.parquet')));
        M(k).wf_hi_iso = table2array(parquetread( ...
            fullfile(sdir, 'wf_hi_iso.parquet')));
    else
        M(k).units_iso = []; M(k).wf_mean_iso = [];
        M(k).wf_lo_iso = []; M(k).wf_hi_iso = [];
    end

    % pick the layer the FIGURE draws (workspace keeps both)
    if strcmp(opts.method, 'isosplit')
        assert(isfile(isoFile), ...
            'no isosplit layer exported yet for %s', stem);
        unitsPlot = M(k).units_iso; wfPlot = M(k).wf_mean_iso;
        layerLabel = 'ISO-SPLIT resort (gated)';
    else
        unitsPlot = units; wfPlot = wfM;
        layerLabel = sprintf('Plexon OFS (%s)', meta.chain);
    end

    % ------------------------------ figure --------------------------
    fig = figure('Name', stem, 'Position', [40 40 1500 860], ...
                 'Color', 'w');
    colors = lines(10);   % unit color = unit class (1..N -> row)

    % left: waveforms at physical positions. One small axes per wired
    % electrode; position from 0-based (col,row), +1 into a 10x10
    % normalized layout, wire bundle side (col 9) at the right.
    for e = 1:height(geo)
        c = geo.col(e); r = geo.row(e);      % 0-based CMP coords
        ax = axes('Position', ...
            [0.03 + c*0.052, 0.06 + r*0.092, 0.048, 0.086]);
        hold(ax, 'on');
        sel = find(unitsPlot.channel_id == geo.channel_id(e));
        for uu = sel'  % rows of unitsPlot == rows of wfPlot (positional)
            plot(ax, t_ms(1:size(wfPlot,2)), wfPlot(uu, :), '-', ...
                 'LineWidth', 0.8, ...
                 'Color', colors(mod(unitsPlot.unit(uu)-1, 10)+1, :));
        end
        ylim(ax, [-200 200]);                 % fixed, never autoscaled
        xlim(ax, [t_ms(1) t_ms(end)]);
        set(ax, 'XTick', [], 'YTick', [], 'Box', 'on');
        text(ax, t_ms(1), 175, sprintf('%d', geo.channel_id(e)), ...
             'FontSize', 5, 'Color', [0.4 0.4 0.4]);
    end
    annotation('textbox', [0.03 0.965 0.75 0.03], 'String', ...
        sprintf('%s   [%s]   reason: %s', stem, layerLabel, ...
                meta.reason), 'EdgeColor', 'none', ...
        'Interpreter', 'none', 'FontWeight', 'bold');

    % right: grids at physical positions. sub2ind with 0-based
    % row/col +1; NaN = unconnected (drawn grey), 0 = real zero.
    nGrid = nan(10, 10); aGrid = nan(10, 10);
    for e = 1:height(geo)
        nGrid(geo.row(e)+1, geo.col(e)+1) = 0;
        aGrid(geo.row(e)+1, geo.col(e)+1) = 0;
    end
    for uu = 1:height(unitsPlot)
        rr = unitsPlot.row(uu)+1; cc = unitsPlot.col(uu)+1;
        nGrid(rr, cc) = nGrid(rr, cc) + 1;
        aGrid(rr, cc) = max(aGrid(rr, cc), unitsPlot.p2p_uv(uu));
    end
    for panel = 1:2
        ax = axes('Position', [0.62, 0.55 - (panel-1)*0.49, ...
                               0.30, 0.40]);
        if panel == 1, G = nGrid; cl = [0 6];
            ttl = sprintf('units / electrode (total %d)', ...
                          height(unitsPlot));
        else, G = aGrid; cl = [0 600];
            ttl = 'max unit p2p per electrode (uV)';
        end
        im = imagesc(ax, G, 'AlphaData', ~isnan(G)); %#ok<NASGU>
        axis(ax, 'xy');            % CMP row 0 at the BOTTOM
        colormap(ax, 'hot'); caxis(ax, cl); colorbar(ax);
        set(ax, 'Color', [0.85 0.85 0.85]);   % grey = unconnected
        title(ax, ttl, 'Interpreter', 'none');
        for rr = 1:10, for cc = 1:10
            if isnan(G(rr, cc))
                text(ax, cc, rr, 'x', 'Color', [0.6 0 0], ...
                     'HorizontalAlignment', 'center', 'FontSize', 7);
            elseif G(rr, cc) > 0
                text(ax, cc, rr, sprintf('%.0f', G(rr, cc)), ...
                     'Color', [0.2 0.6 1], 'FontSize', 6, ...
                     'HorizontalAlignment', 'center');
            end
        end, end
    end

    if opts.saveFig
        % layer in the filename so ofs and isosplit never overwrite
        if strcmp(opts.method, 'isosplit')
            figName = [stem '__isosplit.fig'];
        else
            figName = [stem '.fig'];
        end
        savefig(fig, fullfile(figDir, figName));
        fprintf('saved %s  (%d units, %s)\n', figName, ...
                height(unitsPlot), layerLabel);
    end
    if opts.closeFigs, close(fig); end
end

fprintf(['\n%d session(s) in M; idx lists all candidates; ' ...
         'allMetrics holds the full metric table.\n'], numel(M));
