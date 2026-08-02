%短时傅里叶变换(STFT)

%原理: F_s(ω) = ∫ f(τ)·h(τ-t)·e^{-jωτ} dτ

clear; clc; close all;

%参数设置
fs = 1000;%采样频率(Hz)
T = 2;%信号总时长(s)
t = 0:1/fs:T-1/fs;%时间轴
N = length(t);%总采样点数

%假设输入为一个三次谐波信号:基频25Hz+二次谐波50Hz+三次谐波75Hz
f0 = 25;%基频
f1 = f0;
f2 = 2 * f0;
f3 = 3 * f0;
signal = 1.0 * sin(2*pi*f1*t) + 0.6 * sin(2*pi*f2*t) + 0.3 * sin(2*pi*f3*t);

%添加噪声
signal = signal + 0.05 * randn(size(t));

fprintf('=== 三次谐波信号参数 ===\n');
fprintf('采样频率 fs  = %d Hz\n', fs);
fprintf('信号时长 T   = %.1f s\n', T);
fprintf('基频 f0      = %d Hz\n', f0);
fprintf('谐波频率: %d Hz, %d Hz, %d Hz\n', f1, f2, f3);

%窗函数设计
%选择汉明窗(Hamming Window)，旁瓣抑制好
win_len = 256;%窗长度
overlap = win_len - 32;%窗长度—步长 = win_len - overlap
window = Hamming(win_len, 'periodic');
%其他窗函数:
%hamming(win_len, 'periodic') 汉明窗
%hann(win_len, 'periodic') 汉宁窗
%blackman(win_len, 'periodic') 布莱克曼窗

fprintf('\n=== 窗函数参数 ===\n');
fprintf('窗类型: Hamming\n');
fprintf('窗长度 = %d 点 (%.0f ms)\n', win_len, win_len/fs*1000);
fprintf('重叠   = %d 点\n', overlap);

%STFT
nfft = 512;%FFT点数(应该大于win_len，零填充提升频率分辨率)
step = win_len - overlap;%每次滑动步长
n_frames = floor((N - win_len) / step) + 1;%总帧数
%行=频率,列=时间帧
STFT = zeros(nfft, n_frames);
time_frames = zeros(1, n_frames);

for k = 1:n_frames
    %起始索引
    idx_start = (k-1) * step + 1;
    idx_end   = idx_start + win_len - 1;

    segment = signal(idx_start:idx_end) .* window';
    X = fft(segment, nfft);
    STFT(:, k) = abs(X);

    %窗的中心位置
    time_frames(k) = t(round((idx_start + idx_end) / 2));
end

%频率轴
freq = (0:nfft/2) * fs / nfft;
half_nfft = nfft/2 + 1;

%绘图
figure('Position', [100, 100, 1400, 1000], 'Color', 'w');

%时域波形
subplot(3, 2, [1, 2]);
plot(t, signal, 'b', 'LineWidth', 0.8);
xlabel('时间 (s)', 'FontSize', 12);
ylabel('幅度', 'FontSize', 12);
title(sprintf('三次谐波信号时域波形  (基频=%dHz, 谐波=%d/%d/%dHz)', f0, f1, f2, f3), ...
      'FontSize', 13);
grid on; xlim([0, T]);

%标注各谐波分量的时间段
text(0.02, max(signal)*0.9, ...
     sprintf('f_1=%.0fHz + f_2=%.0fHz + f_3=%.0fHz', f1, f2, f3), ...
     'FontSize', 10, 'Color', [0.5 0 0], 'FontWeight', 'bold');

%窗函数形状
subplot(3, 2, 3);
t_win = (0:win_len-1) / fs * 1000;
plot(t_win, window, 'r', 'LineWidth', 1.5);
xlabel('时间 (ms)', 'FontSize', 11);
ylabel('幅度', 'FontSize', 11);
title(sprintf('Hamming 窗函数 (长度=%d点, %.0fms)', win_len, win_len/fs*1000), ...
      'FontSize', 12);
grid on;

%传统傅里叶变换的频谱
subplot(3, 2, 4);
Y = fft(signal);
P2 = abs(Y/N);
P1 = P2(1:N/2+1);
P1(2:end-1) = 2 * P1(2:end-1);
f_full = fs * (0:(N/2)) / N;

plot(f_full, P1, 'b', 'LineWidth', 1.2);
xlabel('频率 (Hz)', 'FontSize', 11);
ylabel('|P(f)|', 'FontSize', 11);
title('传统 FFT 幅度谱 (全局平均，无时间定位)', 'FontSize', 12);
grid on;
xlim([0, 200]);

%谐波频率线
hold on;
for fi = [f1, f2, f3]
    xline(fi, 'r--', sprintf('%.0f Hz', fi), 'LineWidth', 1, 'FontSize', 9);
end
hold off;

%STFT时频图
subplot(3, 2, [5, 6]);
STFT_dB = 20 * log10(STFT(1:half_nfft, :) + eps);

imagesc(time_frames, freq, STFT_dB);
axis xy;
colormap('jet');
c = colorbar;
c.Label.String = '幅度 (dB)';
c.Label.FontSize = 11;

xlabel('时间 (s)', 'FontSize', 12);
ylabel('频率 (Hz)', 'FontSize', 12);
title('短时傅里叶变换 (STFT) 时频图', 'FontSize', 13);

%谐波频率
hold on;
for fi = [f1, f2, f3]
    yline(fi, 'w--', sprintf('%.0f Hz', fi), 'LineWidth', 1, ...
          'FontSize', 9, 'Color', [1 1 1 0.7]);
end
hold off;

ylim([0, 150]);

fprintf('时间帧数 = %d\n', n_frames);
fprintf('频率分辨率 Δf = %.2f Hz\n', fs/nfft);
fprintf('时间分辨率 Δt = %.3f s\n', win_len/fs);

%对比不同窗长度的影响
figure('Position', [150, 150, 1200, 800], 'Color', 'w');

win_lengths = [64, 128, 256, 512];
nfft_vals   = [128, 256, 512, 1024];

for i = 1:4
    win_i = hamming(win_lengths(i), 'periodic');
    step_i = max(1, round(win_lengths(i) / 4));%重叠75%
    n_frames_i = floor((N - win_lengths(i)) / step_i) + 1;

    STFT_i = zeros(nfft_vals(i), n_frames_i);
    time_frames_i = zeros(1, n_frames_i);

    for k = 1:n_frames_i
        idx_start = (k-1) * step_i + 1;
        idx_end   = idx_start + win_lengths(i) - 1;
        segment   = signal(idx_start:idx_end) .* win_i';
        X = fft(segment, nfft_vals(i));
        STFT_i(:, k) = abs(X);
        time_frames_i(k) = t(round((idx_start + idx_end) / 2));
    end

    half_i = nfft_vals(i)/2 + 1;
    freq_i = (0:nfft_vals(i)/2) * fs / nfft_vals(i);

    subplot(2, 2, i);
    STFT_i_dB = 20 * log10(STFT_i(1:half_i, :) + eps);
    imagesc(time_frames_i, freq_i, STFT_i_dB);
    axis xy;
    colormap('jet');
    colorbar;
    xlabel('时间 (s)'); ylabel('频率 (Hz)');
    title(sprintf('窗长 = %d 点 (%.0f ms), NFFT = %d', ...
          win_lengths(i), win_lengths(i)/fs*1000, nfft_vals(i)), ...
          'FontSize', 11);
    ylim([0, 150]);
end

sgtitle('不同窗长度对 STFT 时频分辨率的影响', ...
       'FontSize', 13, 'FontWeight', 'bold');