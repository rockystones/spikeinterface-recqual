# Analysis 1 - sham-contrast resampling

seed 20260917; B=20/cell; outliers excluded=True; Fisk months anchored at first session (registry gap).
mmp2p: log10 uV primary, raw uV sensitivity. yield: raw
0/1 activity over all 96 sites, 708-session universe.
crossing_rate: log10 clean Hz, Rocky I1 only (no
between-subject level; the pair is coating-contaminated).

- mmp2p:logamp / realistic / within: SD=0.0585 [0.0547,0.0617] n_units=8  eff x1.00
- mmp2p:logamp / realistic / between_array: SD=0.1284 [0.0979,0.1370] n_units=4  eff x4.82
- mmp2p:logamp / realistic / between_array_cleanpairs: SD=0.0944 [0.0944,0.0944] n_units=1  eff x2.60
- mmp2p:logamp / realistic / between_subject: SD=0.2268 [0.1291,0.2663] n_units=3  eff x15.04

- mmp2p:logamp / matched / within: SD=0.0827 [0.0771,0.0872] n_units=8  eff x1.00
- mmp2p:logamp / matched / between_array: SD=0.1578 [0.1230,0.1649] n_units=4  eff x3.64
- mmp2p:logamp / matched / between_array_cleanpairs: SD=0.1133 [0.1133,0.1133] n_units=1  eff x1.88
- mmp2p:logamp / matched / between_subject: SD=0.2418 [0.1404,0.2752] n_units=3  eff x8.56

- mmp2p:max_p2p_uv / realistic / within: SD=16.1211 [13.7639,18.7882] n_units=8  eff x1.00
- mmp2p:max_p2p_uv / realistic / between_array: SD=24.4479 [16.2399,29.9062] n_units=4  eff x2.30
- mmp2p:max_p2p_uv / realistic / between_array_cleanpairs: SD=28.3799 [28.3799,28.3799] n_units=1  eff x3.10
- mmp2p:max_p2p_uv / realistic / between_subject: SD=43.1326 [20.7631,48.7825] n_units=3  eff x7.16

- mmp2p:max_p2p_uv / matched / within: SD=22.1934 [19.4887,25.1416] n_units=8  eff x1.00
- mmp2p:max_p2p_uv / matched / between_array: SD=29.3932 [22.3798,33.4418] n_units=4  eff x1.75
- mmp2p:max_p2p_uv / matched / between_array_cleanpairs: SD=33.8380 [33.8380,33.8380] n_units=1  eff x2.32
- mmp2p:max_p2p_uv / matched / between_subject: SD=48.5578 [30.6432,53.1240] n_units=3  eff x4.79

- yield:active / realistic / within: SD=0.0223 [0.0144,0.0303] n_units=8  eff x1.00
- yield:active / realistic / between_array: SD=0.1123 [0.0091,0.1562] n_units=4  eff x25.35
- yield:active / realistic / between_array_cleanpairs: SD=0.1681 [0.1681,0.1681] n_units=1  eff x56.82
- yield:active / realistic / between_subject: SD=0.1824 [0.0785,0.1907] n_units=3  eff x66.89

- yield:active / matched / within: SD=0.0343 [0.0212,0.0464] n_units=8  eff x1.00
- yield:active / matched / between_array: SD=0.1048 [0.0155,0.1382] n_units=4  eff x9.35
- yield:active / matched / between_array_cleanpairs: SD=0.1488 [0.1488,0.1488] n_units=1  eff x18.84
- yield:active / matched / between_subject: SD=0.1830 [0.0854,0.1914] n_units=3  eff x28.50

- crossing_rate:lograte / realistic / within: SD=0.0607 [0.0567,0.0645] n_units=2  eff x1.00
- crossing_rate:lograte / realistic / between_array: SD=0.1512 [0.1512,0.1512] n_units=1  eff x6.20
- crossing_rate:lograte / realistic / between_array_cleanpairs: SD=nan [nan,nan] n_units=0  eff xnan
- crossing_rate:lograte / realistic / between_subject: SD=nan [nan,nan] n_units=0  eff xnan

- crossing_rate:lograte / matched / within: SD=0.0888 [0.0842,0.0932] n_units=2  eff x1.00
- crossing_rate:lograte / matched / between_array: SD=0.1561 [0.1561,0.1561] n_units=1  eff x3.09
- crossing_rate:lograte / matched / between_array_cleanpairs: SD=nan [nan,nan] n_units=0  eff xnan
- crossing_rate:lograte / matched / between_subject: SD=nan [nan,nan] n_units=0  eff xnan
