function [spec, f_shift, y_cut, fs] = extract_feature(audio, fs, frac)
    %语音特征提取
    
    %算法：1.滑动窗，截取能量最大语音段 
    %     2.FFT，生成幅度谱
    %输入：
    %audio - 音频数据向量
    %fs - 采样率（Hz）
    %frac - 语音段占比，默认 0.3
    %输出：
    %spec - FFT幅度谱
    %f_shift - 对应的频率轴（Hz，以零频为中心）
    %y_cut - 截取后的语音段
    %fs - 采样率

    if nargin < 3, frac = 0.3; end

    %滑动窗截取语音段
    N_smp = length(audio);
    win_len = floor(frac * N_smp);
    [~, start_idx] = maxSumSubArray(abs(audio), frac);
    y_cut = audio(start_idx : win_len + start_idx - 1);

    %FFT
    y_fft = fftshift(fft_x(y_cut));
    spec = abs(y_fft(:));

    %频率轴
    n_fft = length(y_fft);
    f_shift = (-n_fft/2 : n_fft/2-1) * (fs / n_fft);
end
