# Analysis 6 - stripe-conditioned (D-014 map)

Paired within-(array,month) contrasts, channel month-means; row-parity = known-null control on the same channels. TOST bounds: amplitude +/-0.041 and +/-0.10 log10 (R-017's smallest and legacy coating effects); yield +/-0.05 and +/-0.10 active-fraction.

- amplitude_log10 / stripe / Fisk SN1498: d=-0.0411 [-0.0504,-0.0318] (n=23 cells)  p_equiv(+/-0.041)=0.509, (+/-0.1)=1.24e-10
- amplitude_log10 / stripe / Fisk SN1504: d=-0.0403 [-0.0556,-0.0251] (n=23 cells)  p_equiv(+/-0.041)=0.47, (+/-0.1)=4.73e-07
- amplitude_log10 / stripe / Nigel Anterior: d=-0.0016 [-0.0146,+0.0114] (n=22 cells)  p_equiv(+/-0.041)=1.78e-05, (+/-0.1)=7.85e-12
- amplitude_log10 / stripe / Nigel Posterior: d=+0.0039 [-0.0049,+0.0127] (n=21 cells)  p_equiv(+/-0.041)=2.42e-07, (+/-0.1)=1.66e-14
- amplitude_log10 / row_control / Fisk SN1498: d=-0.0787 [-0.0877,-0.0696] (n=23 cells)  p_equiv(+/-0.041)=1, (+/-0.1)=0.000265
- amplitude_log10 / row_control / Fisk SN1504: d=+0.0042 [-0.0081,+0.0165] (n=23 cells)  p_equiv(+/-0.041)=1.87e-05, (+/-0.1)=2.37e-12
- amplitude_log10 / row_control / Nigel Anterior: d=-0.0139 [-0.0267,-0.0012] (n=22 cells)  p_equiv(+/-0.041)=0.000733, (+/-0.1)=6.5e-11
- amplitude_log10 / row_control / Nigel Posterior: d=+0.0220 [+0.0106,+0.0335] (n=21 cells)  p_equiv(+/-0.041)=0.00482, (+/-0.1)=9.73e-11

- yield_fraction / stripe / Fisk SN1498: d=-0.0121 [-0.0209,-0.0033] (n=23 cells)  p_equiv(+/-0.05)=1.02e-07, (+/-0.1)=1.54e-14
- yield_fraction / stripe / Fisk SN1504: d=+0.0060 [-0.0069,+0.0189] (n=23 cells)  p_equiv(+/-0.05)=3.32e-06, (+/-0.1)=8.62e-12
- yield_fraction / stripe / Nigel Anterior: d=+0.0009 [-0.0028,+0.0046] (n=22 cells)  p_equiv(+/-0.05)=1.44e-16, (+/-0.1)=7.68e-23
- yield_fraction / stripe / Nigel Posterior: d=+0.0015 [-0.0007,+0.0037] (n=21 cells)  p_equiv(+/-0.05)=2.19e-20, (+/-0.1)=1.69e-26
- yield_fraction / row_control / Fisk SN1498: d=-0.0081 [-0.0154,-0.0008] (n=23 cells)  p_equiv(+/-0.05)=7.84e-10, (+/-0.1)=1.3e-16
- yield_fraction / row_control / Fisk SN1504: d=+0.0105 [+0.0035,+0.0175] (n=23 cells)  p_equiv(+/-0.05)=1.06e-09, (+/-0.1)=9.28e-17
- yield_fraction / row_control / Nigel Anterior: d=+0.0020 [-0.0026,+0.0065] (n=22 cells)  p_equiv(+/-0.05)=1.34e-14, (+/-0.1)=6.67e-21
- yield_fraction / row_control / Nigel Posterior: d=+0.0108 [+0.0031,+0.0184] (n=21 cells)  p_equiv(+/-0.05)=1.19e-08, (+/-0.1)=4.82e-15

- condition-vs-tether (log10 amp, Nigel+Fisk): stripe-contrast SD 0.0386 vs between-array SD 0.1180 -> device axis 3.1x the treatment axis

- components (Nigel+Fisk subset), raw vs stripe-residualized: vS 0.0587 -> 0.0582, vE 0.0360 -> 0.0360, rho 0.390 -> 0.391

- spillover: stripes alternate single 400-um columns, so every control electrode neighbours a treated column; the stripe contrast estimates (treatment - spillover). phi needs the histology radial bins (cross-repo, parked).