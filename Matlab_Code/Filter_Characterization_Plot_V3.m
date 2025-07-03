%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% Code to plot Raw transmittance data and create scalled data
%                 Hannah Page 22498729 GENG5512 
% First step is to use Create_CSV.m code to turn the raw data into a csv
%load in data
clear;
file1 = 'Spec_data1.csv';       %file with data in
load(file1);                    %Load the data 
close all                       %closes previous figures 
file = 'Spec_data.csv';         %file with data in
load(file);                     %Load the data

%get each variable from the csv file
w=Spec_data1(:,1);              %allocate each column 
Ref_532 = Spec_data1(:,2); 
Raw_532 = Spec_data1(:,4);
Ref_570 = Spec_data1(:,6);
Raw_570 = Spec_data1(:,8);

w1=Spec_data(:,1);                          
Ref_Red = Spec_data(:,2);                   
Ref_NIR_Sat = Spec_data(:,3);
Ref_NIR_NoSat = Spec_data(:,4);
Raw_Red = Spec_data(:,5);
Raw_NIR_Sat = Spec_data(:,6);
Raw_NIR_NoSat = Spec_data(:,7);

%gets rid of noise that occurs when the incident & ref are both almost 0
gap =500;                                     %The front data that is noisy
for col = gap:1:2048                          %finds the scaled 
    if Raw_532(col) <65                       %
        Raw_532(col) = 0;
    end

    if Raw_570(col) <50
        Raw_570(col) = 0;
    end
    if Raw_Red(col) <60
        Raw_Red(col) = 0;
    end
    if Raw_NIR_Sat(col) <60
        Raw_NIR_Sat(col) = 0;
    end
    if Raw_NIR_NoSat(col) <60
        Raw_NIR_NoSat(col) = 0;
    end
    %finding the scalled transmission %
    T532(col) = 100* Raw_532(col)/Ref_532(col); 
    T570(col) = 100*Raw_570(col)/Ref_570(col);
    RedT(col) = 100* Raw_Red(col)/Ref_Red(col);
    NIRT(col) = 100*Raw_NIR_NoSat(col)/Ref_NIR_NoSat(col);
    NIRT_Sat(col) = 100*Raw_NIR_Sat(col)/Ref_NIR_Sat(col);
end

for col = 1:1:gap 
    T532(col) = 0;
    T570(col) = 0;
    RedT(col) = 0;
    NIRT(col) = 0;
    NIRT_Sat(col) =0;

end
% Define line styles & Colours 
pairColors = {"#77AC30", "#0072BD", "#A2142F", "#EDB120","#000000"}; 
lineStyles = {'-', '--'};

% Plots the raw data with the same color for each pair
hold on;
plot(w, Raw_532, lineStyles{1}, 'Color', pairColors{1}, 'LineWidth', 1.4);
plot(w, Ref_532, lineStyles{2}, 'Color', pairColors{1}, 'LineWidth', 1.4);
plot(w, Raw_570, lineStyles{1}, 'Color', pairColors{2}, 'LineWidth', 1.4);
plot(w, Ref_570, lineStyles{2}, 'Color', pairColors{2}, 'LineWidth', 1.4);
plot(w1,   Raw_Red  , lineStyles{1}, 'Color', pairColors{3}, 'LineWidth', 1.4);
plot(w1, Ref_Red, lineStyles{2}, 'Color', pairColors{3}, 'LineWidth', 1.4);
plot(w, Raw_NIR_NoSat, lineStyles{1}, 'Color', pairColors{4}, 'LineWidth', 1.4);
plot(w, Ref_NIR_NoSat, lineStyles{2}, 'Color', pairColors{4}, 'LineWidth', 1.4);
plot(w, Raw_NIR_Sat, lineStyles{1}, 'Color', pairColors{5}, 'LineWidth', 1.4);
plot(w, Ref_NIR_Sat, lineStyles{2}, 'Color', pairColors{5}, 'LineWidth', 1.4);
%grid on; % Add vertical gridlines
legend("532 Incident","532 Reference","572 Incident", "572 Reference","660 Incident","660 Reference","850 Incident", "850 Reference","850 Incident (Sat)", "850 Reference (Sat)","FontSize", 12);%,"Raw"
xlim([450 950]);
ylim([0 16000]);
xlabel("Wavelength (nm)")
ylabel("Intensity (counts)")
title("Raw Intensity Data")

%Plots the scaled data
figure()                                    
hold on;
plot(w,T532, 'Color', pairColors{1},'LineWidth',1.4);
plot(w,T570,  'Color', pairColors{2},'LineWidth',1.4);
plot(w1,RedT,  'Color', pairColors{3},'LineWidth',1.4);
plot(w,NIRT,  'Color', pairColors{4},'LineWidth',1.4);
plot(w,NIRT_Sat,'Color', pairColors{5},'LineWidth',1.4);
%the vertical grid lines
ax = gca;
ax.XGrid = 'on';
ax.YGrid = 'off';
ax.XMinorGrid = 'on';
title("Scaled transmittance", "FontSize", 10)
legend("532 Filter","572 Filter", "660 Filter", "850 Filter", "850 Filter (Sat)" ,"FontSize", 10)
xlabel("Wavelength (nm)")
%grid(gca, 'YGrid', 'on');
ylabel("% Transmission")
xlim([450 950]);
ylim([00 130]);

%end of plot :)