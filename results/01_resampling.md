# Analysis 1 - sham-contrast resampling

seed 20260917; B=20/cell; outliers excluded=True; Fisk months anchored at first session (registry gap).
mmp2p: log10 uV primary, raw uV sensitivity. yield: raw
0/1 activity over all 96 sites, 708-session universe.
crossing_rate: log10 clean Hz, Rocky I1 only (no
between-subject level; the pair is coating-contaminated).

- mmp2p:logamp / realistic / within: SD=0.0585 [0.0547,0.0617] n_units=8  eff x1.00
- mmp2p:logamp / realistic / between_array: SD=0.1285 [0.0979,0.1371] n_units=4  eff x4.82
- mmp2p:logamp / realistic / between_array_cleanpairs: SD=0.0944 [0.0944,0.0944] n_units=1  eff x2.60
- mmp2p:logamp / realistic / between_subject: SD=0.2267 [0.1290,0.2662] n_units=3  eff x15.02

- mmp2p:logamp / matched / within: SD=0.0826 [0.0771,0.0872] n_units=8  eff x1.00
- mmp2p:logamp / matched / between_array: SD=0.1581 [0.1230,0.1653] n_units=4  eff x3.66
- mmp2p:logamp / matched / between_array_cleanpairs: SD=0.1133 [0.1133,0.1133] n_units=1  eff x1.88
- mmp2p:logamp / matched / between_subject: SD=0.2411 [0.1404,0.2745] n_units=3  eff x8.51

- mmp2p:max_p2p_uv / realistic / within: SD=15.8937 [13.6643,18.7099] n_units=8  eff x1.00
- mmp2p:max_p2p_uv / realistic / between_array: SD=24.5096 [16.2136,29.9062] n_units=4  eff x2.38
- mmp2p:max_p2p_uv / realistic / between_array_cleanpairs: SD=28.3799 [28.3799,28.3799] n_units=1  eff x3.19
- mmp2p:max_p2p_uv / realistic / between_subject: SD=42.8988 [20.3600,48.5890] n_units=3  eff x7.29

- mmp2p:max_p2p_uv / matched / within: SD=21.8487 [19.3047,25.0205] n_units=8  eff x1.00
- mmp2p:max_p2p_uv / matched / between_array: SD=29.3932 [22.3798,33.4418] n_units=4  eff x1.81
- mmp2p:max_p2p_uv / matched / between_array_cleanpairs: SD=33.8380 [33.8380,33.8380] n_units=1  eff x2.40
- mmp2p:max_p2p_uv / matched / between_subject: SD=48.5578 [30.6432,53.1240] n_units=3  eff x4.94

- yield:active / realistic / within: SD=0.0223 [0.0144,0.0303] n_units=8  eff x1.00
- yield:active / realistic / between_array: SD=0.1025 [0.0091,0.1562] n_units=4  eff x21.14
- yield:active / realistic / between_array_cleanpairs: SD=0.1681 [0.1681,0.1681] n_units=1  eff x56.81
- yield:active / realistic / between_subject: SD=0.1777 [0.0631,0.1872] n_units=3  eff x63.52

- yield:active / matched / within: SD=0.0343 [0.0212,0.0464] n_units=8  eff x1.00
- yield:active / matched / between_array: SD=0.0943 [0.0155,0.1382] n_units=4  eff x7.56
- yield:active / matched / between_array_cleanpairs: SD=0.1488 [0.1488,0.1488] n_units=1  eff x18.83
- yield:active / matched / between_subject: SD=0.1776 [0.0658,0.1862] n_units=3  eff x26.84

- crossing_rate:lograte / realistic / within: SD=0.0607 [0.0567,0.0645] n_units=2  eff x1.00
- crossing_rate:lograte / realistic / between_array: SD=0.1512 [0.1512,0.1512] n_units=1  eff x6.20
- crossing_rate:lograte / realistic / between_array_cleanpairs: SD=nan [nan,nan] n_units=0  eff xnan
- crossing_rate:lograte / realistic / between_subject: SD=nan [nan,nan] n_units=0  eff xnan

- crossing_rate:lograte / matched / within: SD=0.0888 [0.0842,0.0932] n_units=2  eff x1.00
- crossing_rate:lograte / matched / between_array: SD=0.1561 [0.1561,0.1561] n_units=1  eff x3.09
- crossing_rate:lograte / matched / between_array_cleanpairs: SD=nan [nan,nan] n_units=0  eff xnan
- crossing_rate:lograte / matched / between_subject: SD=nan [nan,nan] n_units=0  eff xnan
