%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% Code to read the scope ouput txt file and combine it into one csv
%                 Hannah Page 22498729 GENG5512 
%the names of the files
file_names = {'HRC08061_01.txt', 'HRC08061_03.txt', 'HRC08061_04.txt', 'HRC08061_06.txt'};

% Initialize combined data array
combined_data = [];

% Loop through each file
for file_idx = 1:length(file_names)
    % Open the current file for reading
    fileID = fopen(file_names{file_idx}, 'r');
    
    % Ignore the first 10 lines
    for i = 1:10
        fgetl(fileID);
    end
    
    % Read the numeric data from the remaining lines
    data = [];
    line = fgetl(fileID);
    while ischar(line)
        % Split the line into numeric values
        values = str2num(line); %#ok<ST2NM>
        % Check if the line contains numeric data
        if ~isempty(values)
            % Append the numeric data to the data array
            data = [data; values];
        end
        % Read the next line
        line = fgetl(fileID);
    end
    
    % Close the current file
    fclose(fileID);
    
    % Append the data from the current file to the combined data array
    combined_data = [combined_data, data];
end

% Save the combined data to a CSV file
csv_file_name = 'Spec_data1.csv';
csvwrite(csv_file_name, combined_data);

disp(['Combined data saved to ' csv_file_name]);

%done :)