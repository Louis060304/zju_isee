function [digits, all_scores, segments] = recognize_digits(audio, fs, template_path)
    %多数字语音识别
    %算法：1.短时能量阈值检测，分割语音段
    %     2.滑动窗截取，FFT，生成幅度谱
    %     3.与模板计算相关系数，取最佳匹配
    %     4.按时间顺序输出识别数字
    %输入：
    %audio - 音频数据向量
    %fs - 采样率
    %template_path - 模板文件路径，'./data/data_fft.mat'
    %输出：
    %digits - 识别出的数字数组（按出现顺序），1×N
    %all_scores - N×10 矩阵，第i行为第i段的10个数字相关系数
    %segments - N×2 矩阵，每行 [start_idx, end_idx]

    if nargin < 3
        template_path = './data/data_fft.mat';
    end

    %模板
    if ~exist(template_path, 'file')
        error('模板文件 %s 不存在，请先运行 batch_fft_numbers', template_path);
    end
    S = load(template_path, 'templates');
    templates = S.templates;

    %能量阈值分段
    segments = segment_by_energy(audio, fs);
    n_seg = size(segments, 1);

    if n_seg == 0
        fprintf('未检测到语音段\n');
        digits = []; all_scores = []; segments = [];
        return;
    end

    fprintf('检测到 %d 个语音段\n', n_seg);

    %逐段识别
    digits = zeros(1, n_seg);
    all_scores = zeros(n_seg, length(templates));

    for i = 1:n_seg
        y_seg = audio(segments(i,1) : segments(i,2));
        input_spec = extract_feature(y_seg, fs);
        %进行模板匹配
        match_scores = zeros(length(templates), 1);
        for j = 1:length(templates)
            tpl = templates{j}(:);
            if length(tpl) ~= length(input_spec)
                tpl = interp1(linspace(0, 1, length(tpl)), tpl, ...
                              linspace(0, 1, length(input_spec)), 'linear');
            end
            R = corrcoef(input_spec, tpl);
            match_scores(j) = R(1, 2);
        end

        all_scores(i, :) = match_scores;
        [~, idx] = max(match_scores);
        digits(i) = idx - 1;
        fprintf('  段%d: 数字 %d (置信度: %.1f%%)\n', i, digits(i), match_scores(idx)*100);
    end

    fprintf('===== 识别结果: [%s] =====\n', join(string(digits), ', '));
end


function segments = segment_by_energy(audio, fs)
    %语音分段
    %
    %算法：计算短时能量-阈值判定-合并邻近段
    %
    %输出：
    %segments - N×2 矩阵，每行[start_idx, end_idx]

    %分帧参数
    frame_len = round(0.025 * fs);
    frame_hop = round(0.010 * fs);
    n_frames = floor((length(audio) - frame_len) / frame_hop) + 1;

    %计算能量
    energy = zeros(1, n_frames);
    for k = 1:n_frames
        start_idx = (k-1) * frame_hop + 1;
        frame = audio(start_idx : start_idx + frame_len - 1);
        energy(k) = sum(frame.^2);
    end

    %阈值：均值+0.3倍标准差
    thr = mean(energy) + 0.3 * std(energy);
    active = energy > thr;

    min_active = round(0.08 / 0.010);%至少持续80ms
    min_gap = round(0.15 / 0.010);%允许150ms内的间隙合并
    %去除短小段
    active = remove_short(active, min_active);
    %合并邻近段
    active = fill_gaps(active, min_gap);

    %提取连续活动段起止位置
    segments = [];
    in_speech = false;
    for k = 1:length(active)
        sample_center = (k-1) * frame_hop + frame_len/2;

        if active(k) && ~in_speech
            %语音段开始
            seg_start = max(1, (k-1) * frame_hop + 1);
            in_speech = true;
        elseif ~active(k) && in_speech
            %语音段结束
            seg_end = min(length(audio), (k-1) * frame_hop + frame_len);
            if (seg_end - seg_start) > 0.05 * fs  % 至少 50ms
                segments(end+1, :) = [seg_start, seg_end];
            end
            in_speech = false;
        end
    end
    %末尾段
    if in_speech
        seg_end = length(audio);
        if (seg_end - seg_start) > 0.05 * fs
            segments(end+1, :) = [seg_start, seg_end];
        end
    end
end


function arr = remove_short(arr, min_len)
    %去除长度< min_len的连续1段
    d = diff([0, arr, 0]);
    starts = find(d == 1);
    ends   = find(d == -1) - 1;
    for i = 1:length(starts)
        if ends(i) - starts(i) + 1 < min_len
            arr(starts(i):ends(i)) = 0;
        end
    end
end


function arr = fill_gaps(arr, max_gap)
    %将长度<= max_gap的0段填充为1（合并邻近语音段）
    d = diff([1, arr, 1]);
    starts = find(d == -1);
    ends   = find(d == 1) - 1;
    for i = 1:length(starts)
        if ends(i) - starts(i) + 1 <= max_gap
            arr(starts(i):ends(i)) = 1;
        end
    end
end
