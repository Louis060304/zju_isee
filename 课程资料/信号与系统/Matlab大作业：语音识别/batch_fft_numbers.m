function templates = batch_fft_numbers(data_dir, output_path, do_plot)
    %处理数字0-9音频，提取FFT特征（训练模板）
    %
    %算法：1.扫描目录，读取所有音频文件
    %     2.滑动窗截取能量最大语音段，FFT（fft_x）
    %     3.生成频谱对比图
    %     4.保存模板至.mat文件
    %输入：
    %data_dir - 训练音频目录，'./data/numbers/'
    %output_path - 模板保存路径，'./data/data_fft.mat'
    %do_plot - 是否绘图，默认true
    %输出：
    %templates - cell数组，每个元素为对应数字的FFT幅度谱

    if nargin < 1, data_dir    = './data/numbers/'; end
    if nargin < 2, output_path = './data/data_fft.mat'; end
    if nargin < 3, do_plot     = true; end
    
    frac = 0.3;%子段长度占音频总长度的比例

    files = listAllFiles(data_dir);

    if isempty(files)
        error('未找到音频文件！请先运行 recorder.m 录制训练数据');
    end

    n_files = length(files);
    fprintf('找到 %d 个音频文件，开始FFT...\n', n_files);
    templates = cell(n_files, 1);

    if do_plot
        figure
        set(gcf, 'unit', 'centimeters', 'position', [10 5 20, max(8, ceil(n_files/5)*4)]);
    end

    %处理音频文件
    for i = 1:n_files
        cur_file = files{i};
        [~, fname, ~] = fileparts(cur_file);
        disp(['处理: ' cur_file]);

        [data_mp, fs_mp] = audioread(cur_file);%读取音频数据及采样率

        [spec, f_shift] = extract_feature(data_mp, fs_mp, frac);
        templates{i} = spec;

        %绘制频谱幅度
        if do_plot
            n_rows = ceil(n_files / 5);
            subplot(n_rows, 5, i);
            plot(f_shift, spec);
            xlabel('Frequency (Hz)');
            ylabel('Magnitude');
            title(sprintf('数字: %s', fname));
        end
    end

    %保存模板
    [out_dir, ~, ~] = fileparts(output_path);
    if ~exist(out_dir, 'dir')
        mkdir(out_dir);
    end
    save(output_path, 'templates');
    fprintf('模板已保存至 %s\n', output_path);
end
