%% Plot the spikes

Color_book=[158 001 066; 078 098 171;135 207 164;214 064 078; 245 117 071; 253 185 106; 254 232 154; 245 251 177;203 233 157;070 158 180]./255;

waveform_start_indx=12;
Min_P2P_exclusion=20;
Num_ch=96;
Grid_num=ceil(sqrt(Num_ch));
sampling_rate=30000;

file_list={
    % Curated files
% SN4377 Anterior Medial
"D:\OnedriveSync\OneDrive - University of Pittsburgh\Backup\Downloads\L1 stuff\Rocky New\Curated\Rocky_Anterior_2025-04-04_Baseline_DigitalHeadstage-02.wfexp.mat"
"D:\OnedriveSync\OneDrive - University of Pittsburgh\Backup\Downloads\L1 stuff\Rocky New\Curated\Rocky_Anterior_2025-04-11_Baseline_DigitalHeadstage-02.wfexp.mat"
"D:\OnedriveSync\OneDrive - University of Pittsburgh\Backup\Downloads\L1 stuff\Rocky New\Curated\Rocky_Anterior_2025-04-18_Baseline_DigitalHeadstage-02.wfexp.mat"
"D:\OnedriveSync\OneDrive - University of Pittsburgh\Backup\Downloads\L1 stuff\Rocky New\Curated\Rocky_Anterior_2025-04-25_Baseline_DigitalHeadstage-02.wfexp.mat"

% SN4419 Posterior Lateral
"D:\OnedriveSync\OneDrive - University of Pittsburgh\Backup\Downloads\L1 stuff\Rocky New\Curated\Rocky_Posterior_2025-04-04_Baseline_DigitalHeadstage-02.wfexp.mat"
"D:\OnedriveSync\OneDrive - University of Pittsburgh\Backup\Downloads\L1 stuff\Rocky New\Curated\Rocky_Posterior_2025-04-11_Baseline_DigitalHeadstage-02.wfexp.mat"
"D:\OnedriveSync\OneDrive - University of Pittsburgh\Backup\Downloads\L1 stuff\Rocky New\Curated\Rocky_Posterior_2025-04-18_Baseline_DigitalHeadstage-02.wfexp.mat"
"D:\OnedriveSync\OneDrive - University of Pittsburgh\Backup\Downloads\L1 stuff\Rocky New\Curated\Rocky_Posterior_2025-04-25_Baseline_DigitalHeadstage-02.wfexp.mat"

};
%%

Compiled_unit_data=struct('Date',datetime('now','TimeZone','local','Format','d-MMM-y HH:mm:ss Z'));
Compiled_unit_data.Imported_Data=struct('Date',datetime('now','TimeZone','local','Format','d-MMM-y HH:mm:ss Z'),'Note','First column full spectrum, second column 1khz');
file_name_list=cell(size(file_list,1),2);
correctedfile_name_list=cell(size(file_list));

% for file_indx=1
for file_indx=1:length(file_list)
    file_name_split=split(file_list{file_indx},'\');
    file_name_split_temp=split(file_name_split(end),'_');
    file_name=strcat(file_name_split_temp{1},"_",file_name_split_temp{2},"_",file_name_split_temp{3});% hard coded to match the file name regexp
    file_name_list{file_indx,1}=file_name;
    file_name_list{file_indx,2}=file_name_split_temp(1:3);
    
    sorted_unitdata=load(file_list{file_indx});% load mat file
    corrected_filename_format=strrep(file_name,"-","_");
    correctedfile_name_list{file_indx}=corrected_filename_format;

    %Compiled_unit_data.Imported_Data.(corrected_filename_format).data=sorted_unitdata;
    % Store all the waveforms might take up too much memory if there are
    % many files. 
    Compiled_unit_data.Imported_Data.(corrected_filename_format).units=cell(Num_ch,10); % different columns are different units
    % assume less than 10 units
    Compiled_unit_data.Imported_Data.(corrected_filename_format).num_units=zeros(Num_ch,1);
    Compiled_unit_data.Imported_Data.(corrected_filename_format).unit_amp=zeros(Num_ch,10);% assume less than 10 units
    Compiled_unit_data.Imported_Data.(corrected_filename_format).max_amp=zeros(Num_ch,1);
    
    figure_handle=figure;
    hold on
    set(gcf,'Position',[0 0 1000 1000],'Units','pixels','PaperSize',[8,8],'PaperUnits','inches','visible','off')
    ax=gca;
    ax.FontSize=5;
    for chan_indx=1:Num_ch
        % The channel index here is for the Blackrock recording file
        % channel index, NOT the elec# !!! Remap later.
        temp_chan_name=['Chan',num2str(chan_indx,'%03.f')];
        temp_chan_data=sorted_unitdata.(temp_chan_name);
        num_of_units=length(unique(temp_chan_data(:,2)))-1;
        if num_of_units<0
            num_of_units=0;
        end
        Compiled_unit_data.Imported_Data.(corrected_filename_format).num_units(chan_indx)=num_of_units;
       
        subplot(Grid_num,Grid_num,chan_indx)
        hold on
        tempwaveform={}; %store all the waveforms of the a temp unit
        wave_length=length(waveform_start_indx:size(temp_chan_data,2));
        mean_waveform=zeros(1,wave_length);
        % remove the unsorted waveforms which are marked as 0 and use the
        % rest of the index as unit index
        unit_indx_all=unique(temp_chan_data(:,2));
        unit_indx_all(unit_indx_all==0)=[];
        for unit_indx=1:length(unit_indx_all)
            temp_unit_indx=unit_indx_all(unit_indx);
            tempwaveform{1}=temp_chan_data(temp_chan_data(:,2)==temp_unit_indx,waveform_start_indx:size(temp_chan_data,2));
            % all the waveforms of the a temp unit with index equal to
            % current unit_indx
            Compiled_unit_data.Imported_Data.(corrected_filename_format).units{chan_indx,unit_indx}=tempwaveform{1};
            mean_waveform=mean(tempwaveform{1},1);
            waveform_range=[max(tempwaveform{1},[],1);min(tempwaveform{1},[],1)];
            % plot a range of waveforms instead of all the individual
            % traces
            Compiled_unit_data.Imported_Data.(corrected_filename_format).unit_amp(chan_indx,unit_indx)=abs(max(max(mean_waveform))-min(min(mean_waveform)));
            if abs(max(max(mean_waveform))-min(min(mean_waveform)))>Min_P2P_exclusion
                patch([1:wave_length,fliplr(1:wave_length)]/sampling_rate,[waveform_range(1,:),fliplr(waveform_range(2,:))],Color_book(unit_indx,:),'FaceAlpha',0.1,'EdgeColor','none')
    % % %             plot(1:wave_length,tempwaveform{1}(:,1:wave_length),'b-')
                hold on
                plot((1:wave_length)/sampling_rate,mean_waveform,'Color',Color_book(unit_indx,:))
            end
%             line([1 wave_length]/sampling_rate,[max(max(mean_waveform)) max(max(mean_waveform))],'Color',Color_book(unit_indx,:),'LineStyle','--','LineWidth',0.5)
%             line([1 wave_length]/sampling_rate,[min(min(mean_waveform)) min(min(mean_waveform))],'Color',Color_book(unit_indx,:),'LineStyle','--','LineWidth',0.5)
        end
        Compiled_unit_data.Imported_Data.(corrected_filename_format).max_amp(chan_indx)=max(max(Compiled_unit_data.Imported_Data.(corrected_filename_format).unit_amp(chan_indx,:)));
        title(temp_chan_name,'FontSize',5)
        ylabel('Amp(uV)','FontSize',5)
        clear temp_chan_data
    end
    
    savefig(figure_handle,corrected_filename_format)
    print(figure_handle,corrected_filename_format,'-dpng')
    close all
    fclose('all');

    clear sorted_unitdata
    disp(['Processing ',num2str(file_indx),' /', num2str(length(file_list))])
end

Compiled_unit_data.Imported_Data.FileList=file_list;

%% Arrange data according to coating types
% Use the order of the file list to rearrange the impedance data according
% to individual array
array_SN=[4377,4419];% 
% SN4377 Anterior Medial
% SN4419 Posterior Lateral
Rocky_Implant_date="2025-03-26";
Day_indx=zeros(1,length(file_list));
Week_indx=zeros(1,length(file_list));
Month_indx=zeros(1,length(file_list));
% get the week indx post implant for each time point
% get the week indx post implant for each time point
for file_indx=1:length(file_list)
    Day_indx(file_indx)=caldays(between(datetime(Rocky_Implant_date,'InputFormat','yyyy-MM-dd'),datetime(file_name_list{file_indx, 2}(end),'InputFormat','yyyy-MM-dd'),'days'));
    Week_indx(file_indx)=calweeks(between(datetime(Rocky_Implant_date,'InputFormat','yyyy-MM-dd'),datetime(file_name_list{file_indx, 2}(end),'InputFormat','yyyy-MM-dd'),'weeks'));
    Month_indx(file_indx)=calmonths(between(datetime(Rocky_Implant_date,'InputFormat','yyyy-MM-dd'),datetime(file_name_list{file_indx, 2}(end),'InputFormat','yyyy-MM-dd'),'months'));
end
array_to_file_map={ % Be careful here, the file list should match the actual array SN
   [1:4] % all the file indx from one array
[5:8] % the rest of the file indx from another array
};
% There is a few file mismatch, 'anterior delete row 41, posterior delete row 46, row 73'
time_points=max(length(array_to_file_map{1}),length(array_to_file_map{2})); %  w1, w2, etc....... 
% Week_indx={'W0','W1','W2','W3','W4','W5','W6','W7','W8','W9','W10','W11','W12','W13','W14','W15','W16','W17','W18','W19','W20','W21','W22'};
Days_ticks=unique(Day_indx);

% This is elec to coating type mapping, column 1-96 is elec 1-96.   
array_selectivecoating_elec2coating_map={
[2	2	2	2	2	2	2	2	2	2	2	2	2	2	2	2	2	2	2	2	2	2	2	2	2	2	2	2	2	2	2	2	2	2	2	2	2	2	2	2	2	2	2	2	2	2	2	2	2	2	2	2	2	2	2	2	2	2	2	2	2	2	2	2	2	2	2	2	2	2	2	2	2	2	2	2	2	2	2	2	2	2	2	2	2	2	2	2	2	2	2	2	2	2	2	2
];% SN4377 Anterior Medial
[3	3	3	3	3	3	3	3	3	3	3	3	3	3	3	3	3	3	3	3	3	3	3	3	3	3	3	3	3	3	3	3	3	3	3	3	3	3	3	3	3	3	3	3	3	3	3	3	3	3	3	3	3	3	3	3	3	3	3	3	3	3	3	3	3	3	3	3	3	3	3	3	3	3	3	3	3	3	3	3	3	3	3	3	3	3	3	3	3	3	3	3	3	3	3	3
];% SN4419 Posterior Lateral
};
% coating map code: 0 is uncoated ctrl, 1 is EDCNHS L1, 2 is TNP, 3 is TNP
% L1, each row is one array
 


Blackrock_elec_to_channel_map=[
   1	2	3	4	5	6	7	8	9	10	11	12	13	14	15	16	17	18	19	20	21	22	23	24	25	26	27	28	29	30	31	32	33	34	35	36	37	38	39	40	41	42	43	44	45	46	47	48	49	50	51	52	53	54	55	56	57	58	59	60	61	62	63	64	65	66	67	68	69	70	71	72	73	74	75	76	77	78	79	80	81	82	83	84	85	86	87	88	89	90	91	92	93	94	95	96;
95	32	30	28	26	24	22	18	96	63	61	64	31	29	27	20	16	14	93	94	59	60	62	21	25	23	12	10	92	91	57	58	52	54	19	13	11	8	90	89	55	56	46	50	15	17	9	6	88	87	53	51	44	42	48	5	7	4	85	86	49	47	43	40	38	36	34	3	83	84	82	45	41	39	37	35	33	1	81	80	78	76	74	72	70	68	66	2	79	77	75	73	71	69	67	65
]; % top row actual site (elec#), botton row blackrock channels (channel #)

Array_selectivecoating_coord=zeros(Num_ch,2,length(array_SN));
CMP4377_Cord=zeros(Num_ch,2);% x,y coordiantes to create heatmap
CMP4419_Cord=zeros(Num_ch,2);% x,y coordiantes to create heatmap

array_selectivecoating_chan2coating_map=cell(length(array_SN),1);% remap the site coating to the blackrock headstage channel indx
for i=1:length(array_SN)
    temp_map=nan(1,Num_ch);
    for chan_indx=1:Num_ch
        remap_indx=Blackrock_elec_to_channel_map(2,:)==chan_indx; % find the elec # that matches a channel index
        temp_map(1,chan_indx)=array_selectivecoating_elec2coating_map{i,1}(Blackrock_elec_to_channel_map(1,remap_indx)); % map coating type to channel indx
        
        Array_CMP=eval(strcat('CMP',num2str(array_SN(i)))); % load the elec map
        [Array_selectivecoating_coord(chan_indx,1,i),Array_selectivecoating_coord(chan_indx,2,i)]=find(Array_CMP==find(remap_indx)); % the row and col of matching elec
        [CMP4377_Cord(chan_indx,1),CMP4377_Cord(chan_indx,2)]=find(CMP4377==find(remap_indx)); % the row and col of the elec# that matches a channel index
        [CMP4419_Cord(chan_indx,1),CMP4419_Cord(chan_indx,2)]=find(CMP4419==find(remap_indx)); % the row and col of the elec# that matches a channel index
    end
    array_selectivecoating_chan2coating_map{i,1}=temp_map; % now this is the blackrock chan to coating type map, column 1-96 is chan 1-96. 
end

%%
colorstyle=['k','g','r','b'];
coating_types={'  Ctrl','  EDCNHS L1','  TNP','  TNP L1'};
Num_ch=96;
Compiled_unit_data.Arranged_Data.unitsinfo_by_group=cell(4, time_points,4);% coating type, time points, unit info (units, num_units, unit_amp, max_amp)

for array_indx=1:length(array_SN)
    Array_SN=['SN',num2str(array_SN(array_indx))]; % From SN 4377 and 4419
    temp_file_indx=array_to_file_map{array_indx}; 
    temp_filelist={file_list{temp_file_indx}};
    temp_filenamelist={file_name_list{array_to_file_map{array_indx}}};
    Compiled_unit_data.Arranged_Data.(Array_SN).Imported_file_list=temp_filelist;
    Compiled_unit_data.Arranged_Data.(Array_SN).Imported_filename_list=temp_filenamelist;

    Compiled_unit_data.Arranged_Data.(Array_SN).Imported=cell(1,time_points); 
    Compiled_unit_data.Arranged_Data.(Array_SN).CoatingMap=array_selectivecoating_chan2coating_map{array_indx};
    Compiled_unit_data.Arranged_Data.(Array_SN).num_units=zeros(Num_ch,time_points);
    Compiled_unit_data.Arranged_Data.(Array_SN).max_amp=zeros(Num_ch,time_points);

    Compiled_unit_data.Arranged_Data.(Array_SN).num_units_by_type=cell(2,2); % first column type note, second column is data
    Compiled_unit_data.Arranged_Data.(Array_SN).num_units_by_type{1,2}=nan(Num_ch,time_points);
    Compiled_unit_data.Arranged_Data.(Array_SN).num_units_by_type{2,2}=nan(Num_ch,time_points);
    Compiled_unit_data.Arranged_Data.(Array_SN).yield_by_type=cell(2,2); % first column type note, second column is data
    Compiled_unit_data.Arranged_Data.(Array_SN).yield_by_type{1,2}=zeros(1,time_points);
    Compiled_unit_data.Arranged_Data.(Array_SN).yield_by_type{2,2}=zeros(1,time_points);
    Compiled_unit_data.Arranged_Data.(Array_SN).max_amp_by_type=cell(2,2); % first column type note, second column is data
    Compiled_unit_data.Arranged_Data.(Array_SN).max_amp_by_type{1,2}=nan(Num_ch,time_points);
    Compiled_unit_data.Arranged_Data.(Array_SN).max_amp_by_type{2,2}=nan(Num_ch,time_points);

    for time_point_indx=1:length(temp_filelist)
        temp_unit=Compiled_unit_data.Imported_Data.(correctedfile_name_list{temp_file_indx(time_point_indx)});
        Compiled_unit_data.Arranged_Data.(Array_SN).Imported{1,time_point_indx}=temp_unit(:,1);% all units info
        
        Compiled_unit_data.Arranged_Data.(Array_SN).num_units(:,time_point_indx)=temp_unit.num_units;
        Compiled_unit_data.Arranged_Data.(Array_SN).max_amp(:,time_point_indx)=temp_unit.max_amp;

            if ismember(array_SN(array_indx),[4377])
                TNP_indx=Compiled_unit_data.Arranged_Data.(Array_SN).CoatingMap==2;
                Compiled_unit_data.Arranged_Data.(Array_SN).num_units_by_type{1,1}=[num2str(2) '  TNP'];

                Compiled_unit_data.Arranged_Data.(Array_SN).num_units_by_type{1,2}(1:sum(TNP_indx),time_point_indx)=temp_unit.num_units(TNP_indx);
                Compiled_unit_data.Arranged_Data.(Array_SN).yield_by_type{1,1}=[num2str(2) '  TNP'];
                Compiled_unit_data.Arranged_Data.(Array_SN).yield_by_type{1,2}(time_point_indx)=sum(temp_unit.num_units(TNP_indx)>0)/(sum(TNP_indx));
                Compiled_unit_data.Arranged_Data.(Array_SN).max_amp_by_type{1,1}=[num2str(2) '  TNP'];
                Compiled_unit_data.Arranged_Data.(Array_SN).max_amp_by_type{1,2}(1:sum(TNP_indx),time_point_indx)=temp_unit.max_amp(TNP_indx);

                Compiled_unit_data.Arranged_Data.unitsinfo_by_group{3,time_point_indx,1}=temp_unit.units{TNP_indx,:};
                Compiled_unit_data.Arranged_Data.unitsinfo_by_group{3,time_point_indx,2}=temp_unit.num_units(TNP_indx);
                Compiled_unit_data.Arranged_Data.unitsinfo_by_group{3,time_point_indx,3}=temp_unit.unit_amp(TNP_indx,:);
                Compiled_unit_data.Arranged_Data.unitsinfo_by_group{3,time_point_indx,4}=temp_unit.max_amp(TNP_indx);

            elseif ismember(array_SN(array_indx),[4419])
                TNPL1_indx=Compiled_unit_data.Arranged_Data.(Array_SN).CoatingMap==3;

                Compiled_unit_data.Arranged_Data.(Array_SN).num_units_by_type{2,1}=[num2str(3) '  TNP L1'];
                Compiled_unit_data.Arranged_Data.(Array_SN).num_units_by_type{2,2}(1:sum(TNPL1_indx),time_point_indx)=temp_unit.num_units(TNPL1_indx);
                Compiled_unit_data.Arranged_Data.(Array_SN).yield_by_type{2,1}=[num2str(3) '  TNP L1'];
                Compiled_unit_data.Arranged_Data.(Array_SN).yield_by_type{2,2}(time_point_indx)=sum(temp_unit.num_units(TNPL1_indx)>0)/(sum(TNPL1_indx));
                Compiled_unit_data.Arranged_Data.(Array_SN).max_amp_by_type{2,1}=[num2str(3) '  TNP L1'];
                Compiled_unit_data.Arranged_Data.(Array_SN).max_amp_by_type{2,2}(1:sum(TNPL1_indx),time_point_indx)=temp_unit.max_amp(TNPL1_indx);

                Compiled_unit_data.Arranged_Data.unitsinfo_by_group{4,time_point_indx,1}=temp_unit.units{TNPL1_indx,:};
                Compiled_unit_data.Arranged_Data.unitsinfo_by_group{4,time_point_indx,2}=temp_unit.num_units(TNPL1_indx);
                Compiled_unit_data.Arranged_Data.unitsinfo_by_group{4,time_point_indx,3}=temp_unit.unit_amp(TNPL1_indx,:);
                Compiled_unit_data.Arranged_Data.unitsinfo_by_group{4,time_point_indx,4}=temp_unit.max_amp(TNPL1_indx);
            end
    end

    figure_handle=figure;
    hold on
    for chan_indx=1:Num_ch
        temp_imp2=Compiled_unit_data.Arranged_Data.(Array_SN).num_units;
        temp_linestyle=[colorstyle(Compiled_unit_data.Arranged_Data.(Array_SN).CoatingMap(chan_indx)+1),'-'];
        plot(Day_indx(array_to_file_map{array_indx}),temp_imp2(chan_indx,1:length(temp_filelist)),temp_linestyle)
    end
%     xticks(Days_ticks(round(linspace(1,length(Days_ticks),10))))
    xticks(Days_ticks)
    xtickangle(45)
    xlabel('Time (days)')
    ylabel('Num units')
    title([Array_SN '  k uncoated ctrl, g EDCNHS L1, r TNP, b TNP L1'])
    savefig(figure_handle,[Array_SN '_num_units'])
    print(figure_handle,[Array_SN '_num_units'],'-dpng')

    figure_handle=figure;
    hold on
    for chan_indx=1:Num_ch
        temp_imp2=Compiled_unit_data.Arranged_Data.(Array_SN).max_amp;
        temp_linestyle=[colorstyle(Compiled_unit_data.Arranged_Data.(Array_SN).CoatingMap(chan_indx)+1),'-'];
        plot(Day_indx(array_to_file_map{array_indx}),temp_imp2(chan_indx,1:length(temp_filelist)),temp_linestyle)
    end
%     xticks(Days_ticks(round(linspace(1,length(Days_ticks),10))))
    xticks(Days_ticks)
    xtickangle(45)
    xlabel('Time (days)')
    ylabel('Max Amp (uV)')
    title([Array_SN '  k uncoated ctrl, g EDCNHS L1, r TNP, b TNP L1'])
    savefig(figure_handle,[Array_SN '_maxamp'])
    print(figure_handle,[Array_SN '_maxamp'],'-dpng')

end


%%
% Get the max amp zero numbers stored in nan 
Compiled_unit_data.Arranged_Data.SN4377.max_amp_by_type_nan{1,1}=[num2str(2) '  TNP'];
Compiled_unit_data.Arranged_Data.SN4419.max_amp_by_type_nan{2,1}=[num2str(3) '  TNP L1'];
temp_maxamp=Compiled_unit_data.Arranged_Data.SN4377.max_amp_by_type{1,2};
temp_maxamp(temp_maxamp==0)=nan;
Compiled_unit_data.Arranged_Data.SN4377.max_amp_by_type_nan{1,2}=temp_maxamp;
temp_maxamp=Compiled_unit_data.Arranged_Data.SN4419.max_amp_by_type{2,2};
temp_maxamp(temp_maxamp==0)=nan;
Compiled_unit_data.Arranged_Data.SN4419.max_amp_by_type_nan{2,2}=temp_maxamp;


CMP4377_num_units=nan(10,10,time_points);
CMP4377_map_amp=nan(10,10,time_points);
CMP4419_num_units=nan(10,10,time_points);
CMP4419_map_amp=nan(10,10,time_points);

Subplots_rowcol=[floor(sqrt(time_points)),ceil(sqrt(time_points))+1]; %number of row and columns for subplots
figure_size=[1600,1000]; % figure width and height

for time_indx=1:time_points
    for chan_indx=1:Num_ch
        CMP4377_num_units(CMP4377_Cord(chan_indx,1),CMP4377_Cord(chan_indx,2),time_indx)=Compiled_unit_data.Arranged_Data.('SN4377').num_units(chan_indx,time_indx);
        CMP4377_map_amp(CMP4377_Cord(chan_indx,1),CMP4377_Cord(chan_indx,2),time_indx)=Compiled_unit_data.Arranged_Data.('SN4377').max_amp(chan_indx,time_indx);

        CMP4419_num_units(CMP4419_Cord(chan_indx,1),CMP4419_Cord(chan_indx,2),time_indx)=Compiled_unit_data.Arranged_Data.('SN4419').num_units(chan_indx,time_indx);
        CMP4419_map_amp(CMP4419_Cord(chan_indx,1),CMP4419_Cord(chan_indx,2),time_indx)=Compiled_unit_data.Arranged_Data.('SN4419').max_amp(chan_indx,time_indx);
    end
end

figure_handle=figure;
for time_indx=1:length(array_to_file_map{1})
    subplot(Subplots_rowcol(1),Subplots_rowcol(2),time_indx)
    heatmap(CMP4377_num_units(:,:,time_indx),'Colormap',hot)
    caxis([0,5])
    title(strcat('Day',num2str(Day_indx(array_to_file_map{1}(time_indx)) )))
end
sgtitle('SN4377 Number of Units')
set(gcf,'Position',[0 0 figure_size])
savefig(figure_handle,'SN4377 Units')
print(figure_handle,'SN4377 Units','-dpng')


figure_handle=figure;
for time_indx=1:length(array_to_file_map{1})
    subplot(Subplots_rowcol(1),Subplots_rowcol(2),time_indx)
    heatmap(CMP4377_map_amp(:,:,time_indx),'Colormap',hot)
    caxis([0,600])
    title(strcat('Day',num2str(Day_indx(array_to_file_map{1}(time_indx)) )))
end
sgtitle('SN4377 Maximum amplitude')
set(gcf,'Position',[0 0 figure_size])
savefig(figure_handle,'SN4377 Max amp')
print(figure_handle,'SN4377 Max amp','-dpng')

figure_handle=figure;
for time_indx=1:length(array_to_file_map{2})
    subplot(Subplots_rowcol(1),Subplots_rowcol(2),time_indx)
    heatmap(CMP4419_num_units(:,:,time_indx),'Colormap',hot)
    caxis([0,6])
    title(strcat('Day',num2str(Day_indx(array_to_file_map{1}(time_indx)) )))
end
sgtitle('SN4419 Number of Units')
set(gcf,'Position',[0 0 figure_size])
savefig(figure_handle,'SN4419 Units')
print(figure_handle,'SN4419 Units','-dpng')


figure_handle=figure;
for time_indx=1:length(array_to_file_map{2})
    subplot(Subplots_rowcol(1),Subplots_rowcol(2),time_indx)
    heatmap(CMP4419_map_amp(:,:,time_indx),'Colormap',hot)
    caxis([0,600])
    title(strcat('Day',num2str(Day_indx(array_to_file_map{1}(time_indx)) )))
end
sgtitle('SN4419 Maximum amplitude')
set(gcf,'Position',[0 0 figure_size])
savefig(figure_handle,'SN4419 Max amp')
print(figure_handle,'SN4419 Max amp','-dpng')

%% Compile Plot by day
files_to_ignore={[],[]};% recording sessions that shows techinical error or orphaned file (does not have recording from both arrays on the same day)


for array_indx=1:length(array_SN)
    Array_SN=['SN',num2str(array_SN(array_indx))]; % From 4377,4419
    Compiled_unit_data.Arranged_Data.(Array_SN).TimeStamp=cell(1,3); % days, weeks, months
    Compiled_unit_data.Arranged_Data.(Array_SN).TimeStamp{1}=Day_indx(array_to_file_map{array_indx});
    Compiled_unit_data.Arranged_Data.(Array_SN).TimeStamp{2}=Week_indx(array_to_file_map{array_indx});
    Compiled_unit_data.Arranged_Data.(Array_SN).TimeStamp{3}=Month_indx(array_to_file_map{array_indx});
end

figure_handle=figure;
hold on;
plot_option=1; % 1 day, 2 week, 3 month
temp_unit=Compiled_unit_data.Arranged_Data.SN4377.num_units_by_type{1, 2}(:,1:length(Compiled_unit_data.Arranged_Data.SN4377.TimeStamp{1, plot_option}));
errorbar(Compiled_unit_data.Arranged_Data.SN4377.TimeStamp{1, plot_option},mean(temp_unit,1,'omitnan'),std(temp_unit,0,1,'omitnan')./sqrt(sum(~isnan(temp_unit),1)),'r-')
temp_unit2=Compiled_unit_data.Arranged_Data.SN4419.num_units_by_type{2, 2}(:,1:length(Compiled_unit_data.Arranged_Data.SN4419.TimeStamp{1, plot_option}));
errorbar(Compiled_unit_data.Arranged_Data.SN4419.TimeStamp{1, plot_option},mean(temp_unit2,1,'omitnan'),std(temp_unit2,0,1,'omitnan')./sqrt(sum(~isnan(temp_unit2),1)),'b-')
set(gcf,'Position',[0 0 figure_size])
legend('TNP','TNP L1')
xlabel('Time (Days)')
ylabel('Number of units/site')
savefig(figure_handle,'Num of Units by day')
print(figure_handle,'Num of Units by day','-dpng')
% 
figure_handle=figure;
hold on;
plot_option=1; % 1 day, 2 week, 3 month
temp_unit=Compiled_unit_data.Arranged_Data.SN4377.max_amp_by_type{1, 2}(:,1:length(Compiled_unit_data.Arranged_Data.SN4377.TimeStamp{1, plot_option}));
errorbar(Compiled_unit_data.Arranged_Data.SN4377.TimeStamp{1, plot_option},mean(temp_unit,1,'omitnan'),std(temp_unit,0,1,'omitnan')./sqrt(sum(~isnan(temp_unit),1)),'r-')
temp_unit2=Compiled_unit_data.Arranged_Data.SN4419.max_amp_by_type{2, 2}(:,1:length(Compiled_unit_data.Arranged_Data.SN4419.TimeStamp{1, plot_option}));
errorbar(Compiled_unit_data.Arranged_Data.SN4419.TimeStamp{1, plot_option},mean(temp_unit2,1,'omitnan'),std(temp_unit2,0,1,'omitnan')./sqrt(sum(~isnan(temp_unit2),1)),'b-')
set(gcf,'Position',[0 0 figure_size])
legend('TNP','TNP L1')
xlabel('Time (Days)')
ylabel('Max Amp (uV)')
savefig(figure_handle,'Max amp by day')
print(figure_handle,'Max amp by day','-dpng')
%
figure_handle=figure;
hold on;
plot_option=1; % 1 day, 2 week, 3 month
temp_unit=Compiled_unit_data.Arranged_Data.SN4377.max_amp_by_type_nan{1, 2}(:,1:length(Compiled_unit_data.Arranged_Data.SN4377.TimeStamp{1, plot_option}));
errorbar(Compiled_unit_data.Arranged_Data.SN4377.TimeStamp{1, plot_option},mean(temp_unit,1,'omitnan'),std(temp_unit,0,1,'omitnan')./sqrt(sum(~isnan(temp_unit),1)),'r-')
temp_unit2=Compiled_unit_data.Arranged_Data.SN4419.max_amp_by_type_nan{2, 2}(:,1:length(Compiled_unit_data.Arranged_Data.SN4419.TimeStamp{1, plot_option}));
errorbar(Compiled_unit_data.Arranged_Data.SN4419.TimeStamp{1, plot_option},mean(temp_unit2,1,'omitnan'),std(temp_unit2,0,1,'omitnan')./sqrt(sum(~isnan(temp_unit2),1)),'b-')
set(gcf,'Position',[0 0 figure_size])
legend('TNP','TNP L1')
xlabel('Time (Days)')
ylabel('Max Amp (uV)')
savefig(figure_handle,'Max amp nan by day')
print(figure_handle,'Max amp nan by day','-dpng')

%% Correlation with impedance

import_impedance=import_impedancefile("D:\OnedriveSync\OneDrive - University of Pittsburgh\Backup\AUTOLAB\Rocky new\04-21-2025\Anterior_A1.txt");

plot_options=cell(1,2);
plot_options{1}="Anterior_A1";
plot_options{2}=3;
% plot_options: a 1*2 cell array, first one is the filename, second one is
% plot options, 0: plot nothing, 1: only plot impedance, 2: impedance+phase, 3: impedance+phase, plus Nyquist 

[impedance_data,khz_impedance,full_impedance_data] = process_impedance_single(import_impedance,plot_options);
frequencies=full_impedance_data(1,:,1);

figure
hold on
for chan_indx=1:size(impedance_data,1)
   plot(frequencies,impedance_data(chan_indx,:),'k-')
end
set(gca, 'YScale', 'log')
set(gca, 'XScale', 'log')
xlabel('Frequency (Hz)')
ylabel('Impedance(Ohm)')
% ylim([1e3 1e8])

%% Batch import impedance data Utah array

% 4377 Anterior TNP only; 4419 Posterior TNP L1

file_list={
% 4377 Anterior TNP only

"E:\Github\rockystone\Functional-Electrodes\Blackrock Utah array\Characterization\10by10\SN1025-004377\SN1025-004377pristineEIS-A.txt"
"E:\Github\rockystone\Functional-Electrodes\Blackrock Utah array\Characterization\10by10\SN1025-004377\SN1025-004377pristineEIS-B.txt"
"E:\Github\rockystone\Functional-Electrodes\Blackrock Utah array\Characterization\10by10\SN1025-004377\SN1025-004377pristineEIS-C.txt"

"D:\OnedriveSync\OneDrive - University of Pittsburgh\Backup\AUTOLAB\Rocky new\04-21-2025\Anterior_A1.txt"
"D:\OnedriveSync\OneDrive - University of Pittsburgh\Backup\AUTOLAB\Rocky new\04-21-2025\Anterior_A2.txt"
"D:\OnedriveSync\OneDrive - University of Pittsburgh\Backup\AUTOLAB\Rocky new\04-21-2025\Anterior_B1.txt"
"D:\OnedriveSync\OneDrive - University of Pittsburgh\Backup\AUTOLAB\Rocky new\04-21-2025\Anterior_B2.txt"
"D:\OnedriveSync\OneDrive - University of Pittsburgh\Backup\AUTOLAB\Rocky new\04-21-2025\Anterior_C1.txt"
"D:\OnedriveSync\OneDrive - University of Pittsburgh\Backup\AUTOLAB\Rocky new\04-21-2025\Anterior_C2.txt"

% 4419 Posterior TNP L1
"E:\Github\rockystone\Functional-Electrodes\Blackrock Utah array\Characterization\10by10\SN1025-004419\SN1025-004419pristineEIS-A.txt"
"E:\Github\rockystone\Functional-Electrodes\Blackrock Utah array\Characterization\10by10\SN1025-004419\SN1025-004419pristineEIS-B.txt"
"E:\Github\rockystone\Functional-Electrodes\Blackrock Utah array\Characterization\10by10\SN1025-004419\SN1025-004419pristineEIS-C.txt"

"D:\OnedriveSync\OneDrive - University of Pittsburgh\Backup\AUTOLAB\Rocky new\04-21-2025\Posterior_A1.txt"
"D:\OnedriveSync\OneDrive - University of Pittsburgh\Backup\AUTOLAB\Rocky new\04-21-2025\Posterior_A2.txt"
"D:\OnedriveSync\OneDrive - University of Pittsburgh\Backup\AUTOLAB\Rocky new\04-21-2025\Posterior_B1.txt"
"D:\OnedriveSync\OneDrive - University of Pittsburgh\Backup\AUTOLAB\Rocky new\04-21-2025\Posterior_B2.txt"
"D:\OnedriveSync\OneDrive - University of Pittsburgh\Backup\AUTOLAB\Rocky new\04-21-2025\Posterior_C1.txt"
"D:\OnedriveSync\OneDrive - University of Pittsburgh\Backup\AUTOLAB\Rocky new\04-21-2025\Posterior_C2.txt"

};


array_SN=[4377,4419];% 4377 Anterior TNP only; 4419 Posterior TNP L1
array_to_file_map={
   [1:9]
[10:18]
};
chronic_imp_indx={[4:9 ,13:18]}; % exclude the in vitro characterization

Rocky_Implant_date="2025-03-26";
Day_indx=zeros(1,length(file_list));
Week_indx=zeros(1,length(file_list));
Month_indx=zeros(1,length(file_list));
% get the week indx post implant for each time point


Compiled_EIS_data=struct('Date',datetime('now','TimeZone','local','Format','d-MMM-y HH:mm:ss Z'));
Compiled_EIS_data.Imported_Data=struct('Date',datetime('now','TimeZone','local','Format','d-MMM-y HH:mm:ss Z'),'Note','First column full spectrum, second column 1khz');
filename_list=cell(size(file_list));

Compiled_1khz_data=cell(size(file_list));

for array_indx=1:length(array_SN)
    for file_indx=array_to_file_map{array_indx}
        import_impedance=import_impedancefile(file_list{file_indx});
        
        temp_str_split=strsplit(file_list{file_indx},'\');
        temp_filename=strrep(temp_str_split{end},'.txt','');

        if ismember(file_indx,chronic_imp_indx{1})
            temp_time=temp_str_split{end-1};
        else
            temp_time='03-10-2025';
        end

        temp_fieldname=strrep(strcat('Imported_', temp_time,temp_filename),'-','_');
        filename_list{file_indx}=temp_fieldname;
        plot_options{1}=temp_fieldname;
        [impedance_data,khz_impedance,full_impedance_data] = process_impedance_single(import_impedance,plot_options);
        % impedance_data: full spectrum |Z| for all channels, matrix size: num_ch*num_freq
        % khz_impedance: only at 1khz
        % full_impedance_data: all data for all channels separated by channels, matrix size: num_ch*num_freq*7, ["FrequencyHz", "Z", "Phase", "Zr", "Zi", "Time", "Index"]
        Compiled_EIS_data.Imported_Data.(temp_fieldname).impedance_data=impedance_data;
        Compiled_EIS_data.Imported_Data.(temp_fieldname).khz_impedance=khz_impedance;
        Compiled_EIS_data.Imported_Data.(temp_fieldname).full_impedance_data=full_impedance_data;
        Compiled_EIS_data.Imported_Data.(temp_fieldname).rawdata=import_impedance;
        Compiled_1khz_data{file_indx}=khz_impedance;

        Day_indx(file_indx)=caldays(between(datetime(Rocky_Implant_date,'InputFormat','yyyy-MM-dd'),datetime(temp_time,'InputFormat','MM-dd-yyyy'),'days'));
        Week_indx(file_indx)=calweeks(between(datetime(Rocky_Implant_date,'InputFormat','yyyy-MM-dd'),datetime(temp_time,'InputFormat','MM-dd-yyyy'),'weeks'));
        Month_indx(file_indx)=calmonths(between(datetime(Rocky_Implant_date,'InputFormat','yyyy-MM-dd'),datetime(temp_time,'InputFormat','MM-dd-yyyy'),'months'));

        disp(file_indx)
    end
    fclose('all')
end

%% TDT to channel # map

Blackrock_TDT_to_channel_map=[
   1	2	3	4	5	6	7	8	9	10	11	12	13	14	15	16	17	18	19	20	21	22	23	24	25	26	27	28	29	30	31	32	33	34	35	36	37	38	39	40	41	42	43	44	45	46	47	48	49	50	51	52	53	54	55	56	57	58	59	60	61	62	63	64	65	66	67	68	69	70	71	72	73	74	75	76	77	78	79	80	81	82	83	84	85	86	87	88	89	90	91	92	93	94	95	96
16	6	15	14	13	12	11	1	10	2	9	3	8	4	7	5	32	22	31	30	29	28	27	17	26	18	25	19	24	20	23	21	48	38	47	46	45	44	43	33	42	34	41	35	40	36	39	37	64	54	63	62	61	60	59	49	58	50	57	51	56	52	55	53	80	70	79	78	77	76	75	65	74	66	73	67	72	68	71	69	96	86	95	94	93	92	91	81	90	82	89	83	88	84	87	85
]; % top row TDT impedance channel index (A1-A2-B1-B2-C1-C2), botton row blackrock channels (channel #) recording channel indx

%%

day_points=unique(Day_indx);
wk_points=unique(Week_indx);
mth_points=unique(Month_indx);
num_ch=96;
time_points=length(day_points);
compiled_khz_impedance_overtime=zeros(num_ch,time_points,length(array_SN));

for array_indx=1:length(array_SN)
    file_indx_range=array_to_file_map{array_indx};
    temp_logic_indx=zeros(size(Week_indx));
    temp_logic_indx(file_indx_range)=1;
    for time_indx=1:time_points
        temp_timepoint=wk_points(time_indx);
        temp_data=cell2mat(Compiled_1khz_data(Week_indx==temp_timepoint & temp_logic_indx));% find impedance from indx ( x week time point from x array)
        compiled_khz_impedance_overtime(:,time_indx,array_indx)=temp_data(:); % turn 16 ch indidvidual DSUB file format into 96 ch format, assume the file sequence is A1-A2-B1-B2-C1-C2
    end
end
%%
figure_handle=figure;
hold on
for array_indx=1:length(array_SN)
        plot(wk_points,compiled_khz_impedance_overtime(:,:,array_indx),'Color',Color_book(array_indx,:))
end
set(gca, 'YScale', 'log')
xlabel('Weeks Post Implant')
ylabel('Impedance(Ohm)')
savefig(figure_handle,'SN4377 and SN4419 1khz impedance')
print(figure_handle,'SN4377 and SN4419 1khz impedance','-dpng')

figure_handle=figure;
hold on
for array_indx=1:length(array_SN)
        errorbar(wk_points,mean(compiled_khz_impedance_overtime(:,:,array_indx),1),std(compiled_khz_impedance_overtime(:,:,array_indx),0,1),'Color',Color_book(array_indx,:))
end
set(gca, 'YScale', 'log')
ylabel('Impedance(Ohm)')
xlabel('Weeks Post Implant')
savefig(figure_handle,'SN4377 and SN4419 1khz impedance2')
print(figure_handle,'SN4377 and SN4419 1khz impedance2','-dpng')

%%

CMP4377_1khz_imp=nan(10,10,time_points);
CMP4419_1khz_imp=nan(10,10,time_points);

Subplots_rowcol=[floor(sqrt(time_points)),ceil(sqrt(time_points))+1]; %number of row and columns for subplots
figure_size=[1600,1000]; % figure width and height

for time_indx=1:time_points
    CMP4377_temp_data=compiled_khz_impedance_overtime(:,time_indx,1);
    CMP4419_temp_data=compiled_khz_impedance_overtime(:,time_indx,2);
    for chan_indx=1:Num_ch
        remap_tdt_chan_indx=Blackrock_TDT_to_channel_map(2,:)==chan_indx; % find the tdt indx that matches the channel indx
        CMP4377_1khz_imp(CMP4377_Cord(chan_indx,1),CMP4377_Cord(chan_indx,2),time_indx)=CMP4377_temp_data(remap_tdt_chan_indx);
        CMP4419_1khz_imp(CMP4419_Cord(chan_indx,1),CMP4419_Cord(chan_indx,2),time_indx)=CMP4419_temp_data(remap_tdt_chan_indx);     
    end
end

figure_handle=figure;
for time_indx=1:time_points
    subplot(Subplots_rowcol(1),Subplots_rowcol(2),time_indx)
    heatmap(CMP4377_1khz_imp(:,:,time_indx),'Colormap',hot)
%     caxis([0,5])
    set(gca,'ColorScaling','log')
    title(strcat('Day',num2str(day_points(time_indx)) ))
end
sgtitle('SN4377 1khz impedance')
set(gcf,'Position',[0 0 figure_size])
savefig(figure_handle,'SN4377 1khz impedance')
print(figure_handle,'SN4377 1khz impedance','-dpng')


figure_handle=figure;
for time_indx=1:1:time_points
    subplot(Subplots_rowcol(1),Subplots_rowcol(2),time_indx)
    heatmap(CMP4419_1khz_imp(:,:,time_indx),'Colormap',hot)
%     caxis([0,6])
    set(gca,'ColorScaling','log')
    title(strcat('Day',num2str(day_points(time_indx)) ))
end
sgtitle('SN4419 1khz impedance')
set(gcf,'Position',[0 0 figure_size])
savefig(figure_handle,'SN4419 1khz impedance')
print(figure_handle,'SN4419 1khz impedance','-dpng')

figure_handle=figure;
subplot(1,2,1)
scatter(CMP4377_1khz_imp(:,:,2),CMP4377_num_units(:,:,4),'k*')
% set(gca, 'XScale', 'log')
xlabel('Impedance(Ohm)')
ylabel('# Units')
subplot(1,2,2)
histogram2(CMP4377_1khz_imp(:,:,2),CMP4377_num_units(:,:,4),[10,10],'FaceColor','flat')
colorbar
xlabel('Impedance(Ohm)')
ylabel('# Units')

figure_handle=figure;
subplot(1,2,1)
scatter(CMP4377_1khz_imp(:,:,2),CMP4377_map_amp(:,:,4),'k*')
% set(gca, 'XScale', 'log')
xlabel('Impedance(Ohm)')
ylabel('Max P2P amplitude (uV)')
subplot(1,2,2)
histogram2(CMP4377_1khz_imp(:,:,2),CMP4377_map_amp(:,:,4),[10,10],'FaceColor','flat')
colorbar
xlabel('Impedance(Ohm)')
ylabel('Max P2P amplitude (uV)')


figure_handle=figure;
subplot(1,2,1)
scatter(CMP4419_1khz_imp(:,:,2),CMP4419_num_units(:,:,4),'k*')
% set(gca, 'XScale', 'log')
xlabel('Impedance(Ohm)')
ylabel('# Units')
subplot(1,2,2)
histogram2(CMP4419_1khz_imp(:,:,2),CMP4419_num_units(:,:,4),[10,10],'FaceColor','flat')
colorbar
xlabel('Impedance(Ohm)')
ylabel('# Units')

figure_handle=figure;
subplot(1,2,1)
scatter(CMP4419_1khz_imp(:,:,2),CMP4419_map_amp(:,:,4),'k*')
% set(gca, 'XScale', 'log')
xlabel('Impedance(Ohm)')
ylabel('Max P2P amplitude (uV)')
subplot(1,2,2)
histogram2(CMP4419_1khz_imp(:,:,2),CMP4419_map_amp(:,:,4),[10,10],'FaceColor','flat')
colorbar
xlabel('Impedance(Ohm)')
ylabel('Max P2P amplitude (uV)')
%%
% %% Bin by month
% files_to_ignore={[20],[]};% recording sessions that shows techinical error or orphaned file (does not have recording from both arrays on the same day)
% % There is a few file mismatch, 'anterior delete row 41, posterior delete row 46, row 73'
% 
% for array_indx=1:length(array_SN)
%     Array_SN=['SN',num2str(array_SN(array_indx))]; % From SN 1498 and 1504
%     Compiled_unit_data.Arranged_Data.(Array_SN).TimeStamp=cell(1,3); % days, weeks, months
%     Compiled_unit_data.Arranged_Data.(Array_SN).TimeStamp{1}=Day_indx(array_to_file_map{array_indx});
%     Compiled_unit_data.Arranged_Data.(Array_SN).TimeStamp{2}=Week_indx(array_to_file_map{array_indx});
%     Compiled_unit_data.Arranged_Data.(Array_SN).TimeStamp{3}=Month_indx(array_to_file_map{array_indx});
%     Analysis_results.(Array_SN)=Compiled_unit_data.Arranged_Data.(Array_SN);
%     Analysis_results.(Array_SN).num_units_by_month=cell(2,3);
%     Analysis_results.(Array_SN).max_amp_by_month=cell(2,3);
%     Analysis_results.(Array_SN).max_amp_by_month_nan=cell(2,3);
%     Analysis_results.(Array_SN).yield_by_month=cell(2,3);
%     
%     coating_types=unique(Analysis_results.(Array_SN).CoatingMap);
%     for coating_type_indx=1:length(coating_types)
%         Analysis_results.(Array_SN).num_units_by_month{coating_type_indx,1}=str2num(Compiled_unit_data.Arranged_Data.(Array_SN).num_units_by_type{coating_type_indx,1}(1));
%         Analysis_results.(Array_SN).num_units_by_month{coating_type_indx,2}=Compiled_unit_data.Arranged_Data.(Array_SN).num_units_by_type{coating_type_indx,1};
%         
%         Analysis_results.(Array_SN).max_amp_by_month{coating_type_indx,1}=str2num(Compiled_unit_data.Arranged_Data.(Array_SN).max_amp_by_type{coating_type_indx,1}(1));
%         Analysis_results.(Array_SN).max_amp_by_month{coating_type_indx,2}=Compiled_unit_data.Arranged_Data.(Array_SN).max_amp_by_type{coating_type_indx,1};
%         
%         Analysis_results.(Array_SN).max_amp_by_month_nan{coating_type_indx,1}=str2num(Compiled_unit_data.Arranged_Data.(Array_SN).max_amp_by_type_nan{coating_type_indx,1}(1));
%         Analysis_results.(Array_SN).max_amp_by_month_nan{coating_type_indx,2}=Compiled_unit_data.Arranged_Data.(Array_SN).max_amp_by_type_nan{coating_type_indx,1};
% 
%         Analysis_results.(Array_SN).yield_by_month{coating_type_indx,1}=str2num(Compiled_unit_data.Arranged_Data.(Array_SN).yield_by_type{coating_type_indx,1}(1));
%         Analysis_results.(Array_SN).yield_by_month{coating_type_indx,2}=Compiled_unit_data.Arranged_Data.(Array_SN).yield_by_type{coating_type_indx,1};
%         
%         temp_months=Analysis_results.(Array_SN).TimeStamp{1, 3};
%         temp_months(files_to_ignore{array_indx})=nan;
%         temp_months_unique=unique(temp_months(~isnan(temp_months)));
%         datapoints_per_month=histcounts(temp_months,min(temp_months):(max(temp_months)+1));
%         shank_number=sum(Analysis_results.(Array_SN).CoatingMap==Analysis_results.(Array_SN).max_amp_by_month_nan{coating_type_indx,1});  
%         
%         temp_data_grouped=nan(length(temp_months_unique),shank_number*max(datapoints_per_month));
%         for month_indx=1:length(temp_months_unique)
%             temp_month_data=Compiled_unit_data.Arranged_Data.(Array_SN).num_units_by_type{coating_type_indx,2}(:,temp_months==temp_months_unique(month_indx));
%             temp_data_grouped(month_indx,1:numel(temp_month_data))=temp_month_data(:);
%         end
%         Analysis_results.(Array_SN).num_units_by_month{coating_type_indx,3}=temp_data_grouped;
%         
%         temp_data_grouped=nan(length(temp_months_unique),shank_number*max(datapoints_per_month));
%         for month_indx=1:length(temp_months_unique)
%             temp_month_data=Compiled_unit_data.Arranged_Data.(Array_SN).max_amp_by_type{coating_type_indx,2}(:,temp_months==temp_months_unique(month_indx));
%             temp_data_grouped(month_indx,1:numel(temp_month_data))=temp_month_data(:);
%         end
%         Analysis_results.(Array_SN).max_amp_by_month{coating_type_indx,3}=temp_data_grouped;
%         
%         temp_data_grouped=nan(length(temp_months_unique),shank_number*max(datapoints_per_month));
%         for month_indx=1:length(temp_months_unique)
%             temp_month_data=Compiled_unit_data.Arranged_Data.(Array_SN).max_amp_by_type_nan{coating_type_indx,2}(:,temp_months==temp_months_unique(month_indx));
%             temp_data_grouped(month_indx,1:numel(temp_month_data))=temp_month_data(:);
%         end
%         Analysis_results.(Array_SN).max_amp_by_month_nan{coating_type_indx,3}=temp_data_grouped;   
%         
%         temp_data_grouped=nan(length(temp_months_unique),max(datapoints_per_month));
%         for month_indx=1:length(temp_months_unique)
%             temp_month_data=Compiled_unit_data.Arranged_Data.(Array_SN).yield_by_type{coating_type_indx,2}(:,temp_months==temp_months_unique(month_indx));
%             temp_data_grouped(month_indx,1:numel(temp_month_data))=temp_month_data(:);
%         end
%         Analysis_results.(Array_SN).yield_by_month{coating_type_indx,3}=temp_data_grouped; 
%     end
% end
% 
% 
% figure_handle=figure;
% hold on;
% errorbar(unique(Analysis_results.SN1473.TimeStamp{1, 3}),mean(Analysis_results.SN1473.num_units_by_month{1,3},2,'omitnan'),std(Analysis_results.SN1473.num_units_by_month{1,3},0,2,'omitnan')./sqrt(sum(~isnan(Analysis_results.SN1473.num_units_by_month{1,3}),2)),'k-')
% errorbar(unique(Analysis_results.SN1473.TimeStamp{1, 3}),mean(Analysis_results.SN1473.num_units_by_month{2,3},2,'omitnan'),std(Analysis_results.SN1473.num_units_by_month{2,3},0,2,'omitnan')./sqrt(sum(~isnan(Analysis_results.SN1473.num_units_by_month{2,3}),2)),'g-')
% errorbar(unique(Analysis_results.SN1496.TimeStamp{1, 3}),mean(Analysis_results.SN1496.num_units_by_month{1,3},2,'omitnan'),std(Analysis_results.SN1496.num_units_by_month{1,3},0,2,'omitnan')./sqrt(sum(~isnan(Analysis_results.SN1496.num_units_by_month{1,3}),2)),'y-')
% errorbar(unique(Analysis_results.SN1496.TimeStamp{1, 3}),mean(Analysis_results.SN1496.num_units_by_month{2,3},2,'omitnan'),std(Analysis_results.SN1496.num_units_by_month{2,3},0,2,'omitnan')./sqrt(sum(~isnan(Analysis_results.SN1496.num_units_by_month{2,3}),2)),'b-')
% set(gcf,'Position',[0 0 figure_size])
% legend('Ctrl','EDCNHS L1','TNP','TNP L1')
% xlabel('Time (months)')
% ylabel('Number of units/site')
% savefig(figure_handle,'Num of Units by month')
% print(figure_handle,'Num of Units by month','-dpng')
% % 
% figure_handle=figure;
% hold on;
% errorbar(unique(Analysis_results.SN1473.TimeStamp{1, 3}),mean(Analysis_results.SN1473.max_amp_by_month{1,3},2,'omitnan'),std(Analysis_results.SN1473.max_amp_by_month{1,3},0,2,'omitnan')./sqrt(sum(~isnan(Analysis_results.SN1473.max_amp_by_month{1,3}),2)),'k-')
% errorbar(unique(Analysis_results.SN1473.TimeStamp{1, 3}),mean(Analysis_results.SN1473.max_amp_by_month{2,3},2,'omitnan'),std(Analysis_results.SN1473.max_amp_by_month{2,3},0,2,'omitnan')./sqrt(sum(~isnan(Analysis_results.SN1473.max_amp_by_month{2,3}),2)),'g-')
% errorbar(unique(Analysis_results.SN1496.TimeStamp{1, 3}),mean(Analysis_results.SN1496.max_amp_by_month{1,3},2,'omitnan'),std(Analysis_results.SN1496.max_amp_by_month{1,3},0,2,'omitnan')./sqrt(sum(~isnan(Analysis_results.SN1496.max_amp_by_month{1,3}),2)),'y-')
% errorbar(unique(Analysis_results.SN1496.TimeStamp{1, 3}),mean(Analysis_results.SN1496.max_amp_by_month{2,3},2,'omitnan'),std(Analysis_results.SN1496.max_amp_by_month{2,3},0,2,'omitnan')./sqrt(sum(~isnan(Analysis_results.SN1496.max_amp_by_month{2,3}),2)),'b-')
% set(gcf,'Position',[0 0 figure_size])
% legend('Ctrl','EDCNHS L1','TNP','TNP L1')
% xlabel('Time (months)')
% ylabel('Max Amp (uV)')
% savefig(figure_handle,'Max amp by month')
% print(figure_handle,'Max amp by month','-dpng')
% %
% figure_handle=figure;
% hold on;
% errorbar(unique(Analysis_results.SN1473.TimeStamp{1, 3}),mean(Analysis_results.SN1473.max_amp_by_month_nan{1,3},2,'omitnan'),std(Analysis_results.SN1473.max_amp_by_month_nan{1,3},0,2,'omitnan')./sqrt(sum(~isnan(Analysis_results.SN1473.max_amp_by_month_nan{1,3}),2)),'k-')
% errorbar(unique(Analysis_results.SN1473.TimeStamp{1, 3}),mean(Analysis_results.SN1473.max_amp_by_month_nan{2,3},2,'omitnan'),std(Analysis_results.SN1473.max_amp_by_month_nan{2,3},0,2,'omitnan')./sqrt(sum(~isnan(Analysis_results.SN1473.max_amp_by_month_nan{2,3}),2)),'g-')
% errorbar(unique(Analysis_results.SN1496.TimeStamp{1, 3}),mean(Analysis_results.SN1496.max_amp_by_month_nan{1,3},2,'omitnan'),std(Analysis_results.SN1496.max_amp_by_month_nan{1,3},0,2,'omitnan')./sqrt(sum(~isnan(Analysis_results.SN1496.max_amp_by_month_nan{1,3}),2)),'y-')
% errorbar(unique(Analysis_results.SN1496.TimeStamp{1, 3}),mean(Analysis_results.SN1496.max_amp_by_month_nan{2,3},2,'omitnan'),std(Analysis_results.SN1496.max_amp_by_month_nan{2,3},0,2,'omitnan')./sqrt(sum(~isnan(Analysis_results.SN1496.max_amp_by_month_nan{2,3}),2)),'b-')
% set(gcf,'Position',[0 0 figure_size])
% legend('Ctrl','EDCNHS L1','TNP','TNP L1')
% xlabel('Time (months)')
% ylabel('Max Amp (uV)')
% savefig(figure_handle,'Max amp nan by month')
% print(figure_handle,'Max amp nan by month','-dpng')
% %
% figure_handle=figure;
% hold on;
% errorbar(unique(Analysis_results.SN1473.TimeStamp{1, 3}),mean(Analysis_results.SN1473.yield_by_month{1,3},2,'omitnan'),std(Analysis_results.SN1473.yield_by_month{1,3},0,2,'omitnan')./sqrt(sum(~isnan(Analysis_results.SN1473.yield_by_month{1,3}),2)),'k-')
% errorbar(unique(Analysis_results.SN1473.TimeStamp{1, 3}),mean(Analysis_results.SN1473.yield_by_month{2,3},2,'omitnan'),std(Analysis_results.SN1473.yield_by_month{2,3},0,2,'omitnan')./sqrt(sum(~isnan(Analysis_results.SN1473.yield_by_month{2,3}),2)),'g-')
% errorbar(unique(Analysis_results.SN1496.TimeStamp{1, 3}),mean(Analysis_results.SN1496.yield_by_month{1,3},2,'omitnan'),std(Analysis_results.SN1496.yield_by_month{1,3},0,2,'omitnan')./sqrt(sum(~isnan(Analysis_results.SN1496.yield_by_month{1,3}),2)),'y-')
% errorbar(unique(Analysis_results.SN1496.TimeStamp{1, 3}),mean(Analysis_results.SN1496.yield_by_month{2,3},2,'omitnan'),std(Analysis_results.SN1496.yield_by_month{2,3},0,2,'omitnan')./sqrt(sum(~isnan(Analysis_results.SN1496.yield_by_month{2,3}),2)),'b-')
% set(gcf,'Position',[0 0 figure_size])
% legend('Ctrl','EDCNHS L1','TNP','TNP L1')
% xlabel('Time (months)')
% ylabel('Yield')
% savefig(figure_handle,'Channel yield by month')
% print(figure_handle,'Channel yield by month','-dpng')

