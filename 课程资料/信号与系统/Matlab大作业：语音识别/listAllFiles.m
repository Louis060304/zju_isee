function files = listAllFiles(directory)
   
    audio_exts = {'*.wav', '*.mp3'};
    files = {};

    for e = 1:length(audio_exts)
        found = dir(fullfile(directory, audio_exts{e}));
        for f = 1:length(found)
            if ~strcmp(found(f).name, '.') && ~strcmp(found(f).name, '..')
                files{end+1} = fullfile(directory, found(f).name);
            end
        end
    end

    files = sort(files);
end
