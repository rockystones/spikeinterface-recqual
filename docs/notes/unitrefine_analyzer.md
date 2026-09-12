# UnitRefine works on recording-backed analyzers — the snippet failure was the input

`snippet_sorting.md` showed the pretrained UnitRefine classifiers label 99.98%
of snippet-cohort units as noise, with `P(neural)` never exceeding 0.604, and
hypothesised the cause was the seven features that need continuous traces.
That hypothesis is now tested: `notebooks/scratch_unitrefine_pilot.py` builds
proper `SortingAnalyzer`s on two retained Fisk `.ns6` stems (SpykingCircus2
sortings, 450 µm sparsity radius so multi-channel features see neighbouring
shanks) and computes **35 of 37 features for real** — only `velocity_above` /
`velocity_below` stay missing, since a Utah array has no vertical span.

**The saturation disappears.** 88/129 (68%) and 147/272 (54%) of units come
back `neural`, with a plausible SNR ordering, and the sua/mua model splits
27/129 and 50/272 as `sua`. The snippet-era failure is therefore the input
representation, not the classifier or the Utah geometry: with trace-backed
features the models are discriminative on this corpus.

Scope: this is a two-stem pilot, unvalidated against human labels. It
licenses UnitRefine as a *candidate* curation layer for the continuous-data
arm only; the snippet cohort verdict in [[snippet_sorting]] stands.

## API and version gotchas (SI 0.102.3, sklearn 1.8)

- The entry point in the pinned SI is **`auto_label_units`** /
  `load_model` (`spikeinterface.curation`); the `unitrefine_label_units` name
  in CLAUDE.md is from a later release and does not exist here.
- The HuggingFace pickles were written under sklearn 1.4; sklearn 1.8's
  `SimpleImputer.transform` reads a private `_fill_dtype` the old pickle
  lacks. Restore it from `statistics_.dtype` before predicting — the same
  patch `scratch_rocky_curation.py` documents.
- The PCA metric family (`d_prime`, `nn_*`, `isolation_distance`, `l_ratio`,
  `silhouette`) requires the `principal_components` extension; without it the
  models refuse with "missing metrics".
- `label_conversion` is `{'0': 'neural', '1': 'noise'}` — class 1 is noise;
  read it from the model card, never assume ([[snippet_sorting]]).

## Related

[[snippet_sorting]] for the negative snippet result this scopes,
[[robustness]] for the curation policy consequences,
[[multisorter_agreement]] for the consensus pilot on the same stems.
