%% Plot the spikes

Color_book=[158 001 066; 078 098 171;135 207 164;214 064 078; 245 117 071; 253 185 106; 254 232 154; 245 251 177;203 233 157;070 158 180]./255;

waveform_start_indx=12;
Min_P2P_exclusion=0;
Num_ch=96;
Grid_num=ceil(sqrt(Num_ch));
sampling_rate=30000;
plot_status=true;% plot figures or not

file_list={
    % Sorted files
% Posterior Posterior Ctrl, Anterior L1
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_01-02-2020_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_01-03-2019_Baseline_AnalogHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_01-03-2019_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_01-08-2018_Baseline_Cui-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_01-08-2018_Baseline_Schwartz-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_01-09-2020_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_01-10-2019_Baseline_AnalogHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_01-10-2019_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_01-16-2020_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_01-17-2019_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_01-24-2019_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_01-26-2018_Baseline-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_01-30-2020_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_01-31-2019_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_02-01-2018_Baseline-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_02-07-2019_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_02-08-2018_Baseline-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_02-13-2020_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_02-14-2019_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_02-15-2018_Baseline-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_02-19-2020_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_02-21-2019_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_02-22-2018_Baseline-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_02-26-2020_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_02-28-2019_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_03-01-2018_Baseline-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_03-04-2020_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_03-08-2018_Baseline-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_03-09-2019_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_03-14-2020_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_03-15-2018_Baseline-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_03-15-2019_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_03-21-2019_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_03-22-2018_Baseline-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_03-28-2019_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_03-29-2018_Baseline-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_04-04-2019_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_04-05-2018_Baseline-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_04-12-2018_Baseline-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_04-15-2019_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_04-19-2018_Baseline-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_04-22-2019_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_04-26-2018_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_04-26-2019_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_05-02-2019_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_05-03-2018_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_05-10-2018_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_05-10-2019_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_05-17-2018_Baseline_AnalogHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_05-17-2018_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_05-17-2019_Baseline_AnalogHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_05-17-2019_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_05-23-2019_Baseline_AnalogHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_05-23-2019_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_05-24-2018_Baseline_AnalogHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_05-24-2018_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_05-30-2019_Baseline_AnalogHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_05-30-2019_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_05-31-2018_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_06-06-2019_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_06-07-2018_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_06-13-2019_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_06-14-2018_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_06-20-2019_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_06-21-2018_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_06-25-2019_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_06-28-2018_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_07-06-2018_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_07-11-2019_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_07-12-2018_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_07-18-2019_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_07-19-2018_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_07-25-2019_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_07-26-2018_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_07-31-2020_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_08-01-2019_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_08-02-2018_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_08-09-2018_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_08-09-2019_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_08-10-2020_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_08-15-2019_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_08-16-2018_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_08-18-2020_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_08-22-2019_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_08-23-2018_Baseline_AnalogHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_08-23-2018_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_08-24-2020_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_08-26-2019_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_08-29-2019_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_08-30-2018_Baseline_AnalogHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_08-30-2018_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_09-05-2019_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_09-06-2018_Baseline_AnalogHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_09-06-2018_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_09-12-2019_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_09-13-2018_Baseline_AnalogHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_09-13-2018_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_09-19-2019_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_09-20-2018_Baseline_AnalogHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_09-20-2018_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_09-22-2017_Baseline-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_09-25-2017_Baseline-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_09-26-2019_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_09-27-2017_Baseline-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_09-27-2018_Baseline_AnalogHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_09-27-2018_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_09-28-2017_Baseline-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_09-29-2017_Baseline-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_10-03-2017_Baseline-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_10-03-2019_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_10-04-2017_Baseline-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_10-04-2018_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_10-05-2017_Baseline-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_10-06-2017_Baseline-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_10-09-2017_Baseline-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_10-10-2019_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_10-11-2017_Baseline-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_10-11-2018_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_10-12-2017_Baseline-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_10-17-2019_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_10-18-2018_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_10-24-2019_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_10-25-2018_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_10-26-2017_Baseline-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_10-27-2017_Baseline-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_10-30-2017_Baseline-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_10-31-2017_Baseline-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_10-31-2019_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_11-01-2018_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_11-02-2017_Baseline-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_11-03-2017_Baseline-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_11-07-2019_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_11-09-2018_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_11-13-2019_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_11-15-2018_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_11-21-2018_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_11-21-2019_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_11-29-2018_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_11-29-2019_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_12-05-2019_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_12-06-2018_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_12-12-2019_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_12-13-2018_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_12-19-2019_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_12-20-2018_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_2022-05-25_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_2022-06-01_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_2022-06-08_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_2022-06-15_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_2022-06-22_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_2022-06-29_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_2022-07-06_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_2022-07-13_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_2022-07-28_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_2022-08-03_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_2022-08-10_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_2022-08-17_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_2022-08-26_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_2022-08-30_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_2022-09-09_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_2022-09-14_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_2022-09-23_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_2022-09-29_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_2022-10-07_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_2022-10-14_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_2022-10-21_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_2022-10-28_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_2022-11-04_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_2022-11-11_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_2022-11-17_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_2022-12-02_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_2022-12-09_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_2022-12-16_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_2022-12-22_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_2022-12-30_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_2023-01-06_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_2023-01-13_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_2023-07-27_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_2023-08-04_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_2023-08-011_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_2023-08-17_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_2023-08-24_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_2023-09-29_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Anterior\Sorted\Exported\Rocky_Anterior_2023-10-06_Baseline_DigitalHeadstage-01.wfexp.mat"



% Posterior Posterior Ctrl, Anterior L1
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_01-02-2020_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_01-03-2019_Baseline_AnalogHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_01-03-2019_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_01-09-2020_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_01-10-2019_Baseline_AnalogHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_01-10-2019_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_01-16-2020_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_01-17-2019_Baseline_AnalogHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_01-17-2019_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_01-24-2019_Baseline_AnalogHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_01-24-2019_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_01-26-2018_Baseline-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_01-31-2019_Baseline_AnalogHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_01-31-2019_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_01-31-2020_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_02-01-2018_Baseline-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_02-07-2019_Baseline_AnalogHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_02-07-2019_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_02-08-2018_Baseline-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_02-13-2020_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_02-14-2019_Baseline_AnalogHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_02-14-2019_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_02-15-2018_Baseline-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_02-19-2020_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_02-21-2019_Baseline_AnalogHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_02-21-2019_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_02-22-2018_Baseline-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_02-26-2020_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_02-28-2019_Baseline_AnalogHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_02-28-2019_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_03-01-2018_Baseline-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_03-04-2020_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_03-08-2018_Baseline-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_03-09-2019_Baseline_AnalogHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_03-09-2019_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_03-14-2020_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_03-15-2018_Baseline-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_03-15-2019_Baseline_AnalogHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_03-15-2019_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_03-21-2019_Baseline_AnalogHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_03-21-2019_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_03-22-2018_Baseline-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_03-28-2019_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_03-29-2018_Baseline-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_04-04-2019_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_04-05-2018_Baseline-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_04-12-2018_Baseline-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_04-15-2019_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_04-19-2018_Baseline-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_04-22-2019_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_04-26-2018_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_04-26-2019_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_05-02-2019_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_05-03-2018_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_05-10-2018_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_05-10-2019_Baseline_AnalogHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_05-10-2019_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_05-17-2018_Baseline_AnalogHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_05-17-2018_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_05-17-2019_Baseline_AnalogHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_05-17-2019_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_05-23-2019_Baseline_AnalogHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_05-23-2019_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_05-24-2018_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_05-30-2019_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_05-31-2018_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_06-06-2019_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_06-07-2018_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_06-13-2019_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_06-14-2018_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_06-20-2019_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_06-21-2018_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_06-25-2019_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_06-28-2018_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_07-06-2018_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_07-11-2019_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_07-12-2018_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_07-18-2019_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_07-19-2018_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_07-25-2019_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_07-26-2018_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_07-31-2020_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_08-01-2019_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_08-02-2018_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_08-09-2018_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_08-09-2019_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_08-10-2020_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_08-15-2019_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_08-16-2018_Baseline_AnalogHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_08-16-2018_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_08-18-2020_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_08-23-2018_Baseline_AnalogHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_08-23-2018_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_08-24-2020_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_08-26-2019_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_08-29-2019_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_08-30-2018_Baseline_AnalogHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_08-30-2018_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_09-05-2019_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_09-06-2018_Baseline_AnalogHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_09-06-2018_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_09-12-2019_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_09-13-2018_Baseline_AnalogHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_09-13-2018_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_09-19-2019_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_09-20-2018_Baseline_AnalogHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_09-20-2018_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_09-21-2017_Baseline-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_09-26-2019_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_09-27-2018_Baseline_AnalogHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_09-27-2018_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_10-03-2019_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_10-04-2018_Baseline_AnalogHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_10-04-2018_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_10-10-2019_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_10-11-2018_Baseline_AnalogHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_10-11-2018_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_10-13-2017_Baseline-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_10-13-2017_Baselineb-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_10-16-2017_Baseline-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_10-17-2017_Baseline-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_10-17-2019_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_10-18-2018_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_10-19-2017_Baseline-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_10-20-2017_Baseline-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_10-23-2017_Baseline-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_10-24-2019_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_10-25-2017_Baseline-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_10-25-2018_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_10-30-2017_Baseline-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_10-31-2017_Baseline-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_10-31-2019_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_11-01-2018_Baseline_AnalogHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_11-01-2018_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_11-02-2017_baseline-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_11-03-2017_Baseline-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_11-07-2019_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_11-09-2018_Baseline_AnalogHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_11-09-2018_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_11-13-2019_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_11-15-2018_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_11-21-2018_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_11-21-2019_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_11-29-2018_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_11-29-2019_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_12-05-2019_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_12-06-2018_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_12-12-2019_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_12-13-2018_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_12-19-2019_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_12-20-2018_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_2022-05-25_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_2022-06-01_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_2022-06-08_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_2022-06-15_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_2022-06-22_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_2022-06-29_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_2022-07-06_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_2022-07-13_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_2022-07-28_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_2022-08-03_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_2022-08-10_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_2022-08-17_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_2022-08-26_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_2022-08-30_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_2022-09-09_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_2022-09-14_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_2022-09-23_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_2022-09-29_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_2022-10-07_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_2022-10-14_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_2022-10-21_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_2022-10-28_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_2022-11-04_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_2022-11-11_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_2022-11-17_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_2022-12-02_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_2022-12-09_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_2022-12-16_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_2022-12-22_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_2022-12-30_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_2023-01-06_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_2023-01-13_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_2023-07-27_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_2023-08-04_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_2023-08-11_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_2023-08-17_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_2023-08-24_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_2023-09-29_Baseline_DigitalHeadstage-01.wfexp.mat"
"E:\Rocky all nev\Posterior\Sorted\Exported\Rocky_Posterior_2023-10-06_Baseline_DigitalHeadstage-01.wfexp.mat"


};

Compiled_unit_data=struct('Date',datetime('now','TimeZone','local','Format','d-MMM-y HH:mm:ss Z'));
Compiled_unit_data.Imported_Data=struct('Date',datetime('now','TimeZone','local','Format','d-MMM-y HH:mm:ss Z'),'Note','First column full spectrum, second column 1khz');
file_name_list=cell(size(file_list,1),2);
correctedfile_name_list=cell(size(file_list));

% for file_indx=1
for file_indx=1:length(file_list)
    % this section is hard coded to generate temporary names that contains array
    % info and the timestamp info from the file path and file name
    file_name_split=split(file_list{file_indx},'\');
    file_name_split_temp=split(file_name_split(end),'_');
    file_name=strcat(file_name_split_temp{1},'_',file_name_split_temp{2},'_',file_name_split_temp{3}); % hard coded to find the folder that contains array name
    file_name_list{file_indx,1}=file_name;
    file_name_list{file_indx,2}=file_name_split_temp(1:3);
    
    sorted_unitdata=load(file_list{file_indx});
    corrected_filename_format=strrep(file_name,"-","_");
    correctedfile_name_list{file_indx}=corrected_filename_format;

%     Compiled_unit_data.Imported_Data.(corrected_filename_format).data=sorted_unitdata;     % Store all the waveforms might take up too much memory if there are
    % many files. 
    Compiled_unit_data.Imported_Data.(corrected_filename_format).units=cell(Num_ch,10); % different columns are different units
    % assume less than 10 units
    Compiled_unit_data.Imported_Data.(corrected_filename_format).num_units=nan(Num_ch,1);
    Compiled_unit_data.Imported_Data.(corrected_filename_format).unit_amp=nan(Num_ch,10);% assume less than 10 units
    Compiled_unit_data.Imported_Data.(corrected_filename_format).unit_amp(:,1)=0;% use zeros to prefill the container, so nonactive channel has a zero, the rest are nan
    Compiled_unit_data.Imported_Data.(corrected_filename_format).max_amp=nan(Num_ch,1);
    
    if plot_status==true
        figure_handle=figure;
        hold on
        set(gcf,'Position',[0 0 1000 1000],'Units','pixels','PaperSize',[8,8],'PaperUnits','inches','visible','off')
        ax=gca;
        ax.FontSize=5;
    end
    for chan_indx=1:Num_ch
        temp_chan_name=['Chan',num2str(chan_indx,'%03.f')];
        temp_chan_data=sorted_unitdata.(temp_chan_name);
        num_of_units=length(unique(temp_chan_data(:,2)))-1;% find the unit labels
        if num_of_units<0
            num_of_units=0;
        end
        Compiled_unit_data.Imported_Data.(corrected_filename_format).num_units(chan_indx)=num_of_units;
        if plot_status==true
            subplot(Grid_num,Grid_num,chan_indx)
            hold on
            title(temp_chan_name,'FontSize',5)
            ylabel('Amp(uV)','FontSize',5)
        end
        tempwaveform={}; %store all the waveforms of the a temp unit
        wave_length=length(waveform_start_indx:size(temp_chan_data,2));
        mean_waveform=zeros(1,wave_length);
        for unit_indx=1:num_of_units
            tempwaveform{1}=temp_chan_data(temp_chan_data(:,2)==unit_indx,waveform_start_indx:size(temp_chan_data,2));
            % all the waveforms of the a temp unit with index equal to
            % current unit_indx
            Compiled_unit_data.Imported_Data.(corrected_filename_format).units{chan_indx,unit_indx}=tempwaveform{1};
            mean_waveform=mean(tempwaveform{1},1);
            waveform_range=[max(tempwaveform{1},[],1);min(tempwaveform{1},[],1)];
            % plot a range of waveforms instead of all the individual
            % traces
            Compiled_unit_data.Imported_Data.(corrected_filename_format).unit_amp(chan_indx,unit_indx)=abs(max(max(mean_waveform))-min(min(mean_waveform)));
            if plot_status==true
                if abs(max(max(mean_waveform))-min(min(mean_waveform)))>Min_P2P_exclusion
                    patch([1:wave_length,fliplr(1:wave_length)]/sampling_rate,[waveform_range(1,:),fliplr(waveform_range(2,:))],Color_book(unit_indx,:),'FaceAlpha',0.3,'EdgeColor','none')
        % % %             plot(1:wave_length,tempwaveform{1}(:,1:wave_length),'b-')
                    hold on
                    plot((1:wave_length)/sampling_rate,mean_waveform,'Color',Color_book(unit_indx,:))
        %             line([1 wave_length]/sampling_rate,[max(max(mean_waveform)) max(max(mean_waveform))],'Color',Color_book(unit_indx,:),'LineStyle','--','LineWidth',0.5)
        %             line([1 wave_length]/sampling_rate,[min(min(mean_waveform)) min(min(mean_waveform))],'Color',Color_book(unit_indx,:),'LineStyle','--','LineWidth',0.5)
                end
            end
        end
        Compiled_unit_data.Imported_Data.(corrected_filename_format).max_amp(chan_indx)=max(max(Compiled_unit_data.Imported_Data.(corrected_filename_format).unit_amp(chan_indx,:)));
        clear temp_chan_data
    end
    if plot_status==true
        savefig(figure_handle,corrected_filename_format)
        print(figure_handle,corrected_filename_format,'-dpng')
        close all
        fclose('all');
    end

    clear sorted_unitdata
    disp(['Processing ',num2str(file_indx),' /', num2str(length(file_list))])
end

Compiled_unit_data.Imported_Data.FileList=file_list;

