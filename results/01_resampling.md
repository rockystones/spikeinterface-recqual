# Analysis 1 - sham-contrast resampling

seed 20260917; B=20/cell; outliers excluded=True; Fisk months anchored at first session (registry gap).
mmp2p: log10 uV primary, raw uV sensitivity. yield: raw
0/1 activity over all 96 sites, 708-session universe.
crossing_rate: log10 clean Hz, Rocky I1 only (no
between-subject level; the pair is coating-contaminated).

- mmp2p:logamp / realistic / within: SD=0.0591 [0.0549,0.0624] n_units=8  eff x1.00
- mmp2p:logamp / realistic / between_array: SD=0.1282 [0.1001,0.1369] n_units=4  eff x4.70
- mmp2p:logamp / realistic / between_array_cleanpairs: SD=0.0944 [0.0944,0.0944] n_units=1  eff x2.55
- mmp2p:logamp / realistic / between_subject: SD=0.2273 [0.1311,0.2665] n_units=3  eff x14.77

- mmp2p:logamp / matched / within: SD=0.0810 [0.0740,0.0873] n_units=8  eff x1.00
- mmp2p:logamp / matched / between_array: SD=0.1425 [0.1182,0.1505] n_units=4  eff x3.10
- mmp2p:logamp / matched / between_array_cleanpairs: SD=0.1213 [0.1213,0.1213] n_units=1  eff x2.24
- mmp2p:logamp / matched / between_subject: SD=0.2373 [0.1354,0.2837] n_units=3  eff x8.58

- mmp2p:max_p2p_uv / realistic / within: SD=15.9559 [13.9391,18.1900] n_units=8  eff x1.00
- mmp2p:max_p2p_uv / realistic / between_array: SD=24.8928 [16.8514,29.9062] n_units=4  eff x2.43
- mmp2p:max_p2p_uv / realistic / between_array_cleanpairs: SD=28.3799 [28.3799,28.3799] n_units=1  eff x3.16
- mmp2p:max_p2p_uv / realistic / between_subject: SD=43.0322 [20.2539,48.6433] n_units=3  eff x7.27

- mmp2p:max_p2p_uv / matched / within: SD=21.6358 [18.6618,24.3409] n_units=8  eff x1.00
- mmp2p:max_p2p_uv / matched / between_array: SD=28.9982 [21.2923,36.1736] n_units=4  eff x1.80
- mmp2p:max_p2p_uv / matched / between_array_cleanpairs: SD=37.0123 [37.0123,37.0123] n_units=1  eff x2.93
- mmp2p:max_p2p_uv / matched / between_subject: SD=45.1846 [26.3652,50.8116] n_units=3  eff x4.36

- yield:active / realistic / within: SD=0.0234 [0.0140,0.0321] n_units=8  eff x1.00
- yield:active / realistic / between_array: SD=0.0885 [0.0091,0.1562] n_units=4  eff x14.36
- yield:active / realistic / between_array_cleanpairs: SD=0.1681 [0.1681,0.1681] n_units=1  eff x51.74
- yield:active / realistic / between_subject: SD=0.1709 [0.0369,0.1861] n_units=3  eff x53.48

- yield:active / matched / within: SD=0.0332 [0.0193,0.0473] n_units=8  eff x1.00
- yield:active / matched / between_array: SD=0.0921 [0.0128,0.1600] n_units=4  eff x7.69
- yield:active / matched / between_array_cleanpairs: SD=0.1721 [0.1721,0.1721] n_units=1  eff x26.83
- yield:active / matched / between_subject: SD=0.1697 [0.0385,0.1864] n_units=3  eff x26.08

- crossing_rate:lograte / realistic / within: SD=0.0616 [0.0610,0.0621] n_units=2  eff x1.00
- crossing_rate:lograte / realistic / between_array: SD=0.0656 [0.0656,0.0656] n_units=1  eff x1.13
- crossing_rate:lograte / realistic / between_array_cleanpairs: SD=nan [nan,nan] n_units=0  eff xnan
- crossing_rate:lograte / realistic / between_subject: SD=nan [nan,nan] n_units=0  eff xnan

- crossing_rate:lograte / matched / within: SD=0.0937 [0.0849,0.1024] n_units=2  eff x1.00
- crossing_rate:lograte / matched / between_array: SD=0.1002 [0.1002,0.1002] n_units=1  eff x1.14
- crossing_rate:lograte / matched / between_array_cleanpairs: SD=nan [nan,nan] n_units=0  eff xnan
- crossing_rate:lograte / matched / between_subject: SD=nan [nan,nan] n_units=0  eff xnan
