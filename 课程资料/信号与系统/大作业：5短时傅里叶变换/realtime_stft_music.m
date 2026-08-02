%实时短时傅里叶变换

clear; clc; close all;

%读取 MP3 文件
[filename, filepath] = uigetfile('*.mp3', '选择 MP3 音频文件');
if filename == 0
    error('未选择文件，程序退出。');
end
file_full = fullfile(filepath, filename);
[audio, fs] = audioread(file_full);

%若为立体声，转为单声道
if size(audio, 2) == 2
    audio = mean(audio, 2);
end

%归一化到[-1, 1]范围，确保音量足够
audio = audio / max(abs(audio)) * 0.95;

N_total = length(audio);
T_total = N_total / fs;
t = (0:N_total-1)' / fs;

fprintf('采样率 fs    = %d Hz\n', fs);
fprintf('总时长       = %.1f s (%.1f min)\n', T_total, T_total/60);
fprintf('总采样点数   = %d\n', N_total);

%STFT参数设置
win_len  = round(fs * 0.046);
win_len  = 2^nextpow2(win_len);
overlap  = round(win_len * 0.875);
step     = win_len - overlap;
nfft     = win_len * 2;

%汉宁窗(Hann)
window = hann(win_len, 'periodic');

n_frames = floor((N_total - win_len) / step) + 1;
half_nfft = nfft / 2 + 1;
freq = (0:half_nfft-1)' * fs / nfft;

fprintf('=== STFT 参数 ===\n');
fprintf('窗类型   = Hann\n');
fprintf('窗长度   = %d 点 (%.0f ms)\n', win_len, win_len/fs*1000);
fprintf('步长     = %d 点 (%.1f ms)\n', step, step/fs*1000);
fprintf('NFFT     = %d\n', nfft);
fprintf('总帧数   = %d\n', n_frames);

%计算STFT
STFT_dB = zeros(half_nfft, n_frames);
time_frames = zeros(1, n_frames);

for k = 1:n_frames
    idx_start = (k-1) * step + 1;
    idx_end   = idx_start + win_len - 1;
    segment = audio(idx_start:idx_end) .* window;
    X = fft(segment, nfft);
    STFT_dB(:, k) = 20 * log10(abs(X(1:half_nfft)) + eps);
    time_frames(k) = t(round((idx_start + idx_end) / 2));
end

%动态范围裁剪
dB_max = max(STFT_dB(:));
dB_min = dB_max - 80;
STFT_dB(STFT_dB < dB_min) = dB_min;

fprintf('STFT计算完成。\n');

%绘图
fig = figure('Name', '实时 STFT 音乐时频分析', ...
             'Position', [60, 60, 1400, 900], ...
             'Color', 'k', ...
             'NumberTitle', 'off', ...
             'KeyPressFcn', @(~,~) setappdata(gcf, 'stopFlag', true));
setappdata(fig, 'stopFlag', false);

%时域波形
ax1 = subplot(3, 1, 1);
h_wave = plot(ax1, t, audio, 'c', 'LineWidth', 0.8);
hold(ax1, 'on');
h_cursor = xline(ax1, 0, 'r', 'LineWidth', 2.5);
y_lim_val = max(abs(audio)) * 1.1;
h_patch = patch(ax1, [0 0 0 0], [-y_lim_val y_lim_val y_lim_val -y_lim_val], ...
                'y', 'FaceAlpha', 0.10, 'EdgeColor', 'none');
hold(ax1, 'off');
xlim(ax1, [0, T_total]);
ylim(ax1, [-y_lim_val, y_lim_val]);
xlabel(ax1, '时间 (s)', 'Color', 'w', 'FontSize', 11);
ylabel(ax1, '幅度', 'Color', 'w', 'FontSize', 11);
title(ax1, '音频波形 (实时)', 'Color', 'w', 'FontSize', 13);
ax1.Color = [0.08 0.08 0.08];
ax1.XColor = 'w'; ax1.YColor = 'w';
grid(ax1, 'on');

%STFT时频图
ax2 = subplot(3, 2, 3);
h_img = imagesc(ax2, time_frames, freq, STFT_dB);
axis(ax2, 'xy');
hold(ax2, 'on');
h_tline = xline(ax2, 0, 'y', 'LineWidth', 2.5);
hold(ax2, 'off');
colormap(ax2, 'jet');
clim(ax2, [dB_min, dB_max]);
xlabel(ax2, '时间 (s)', 'Color', 'w', 'FontSize', 11);
ylabel(ax2, '频率 (Hz)', 'Color', 'w', 'FontSize', 11);
title(ax2, 'STFT 时频图 (Hann窗)', 'Color', 'w', 'FontSize', 13);
ax2.Color = [0.08 0.08 0.08];
ax2.XColor = 'w'; ax2.YColor = 'w';
freq_max_display = min(8000, fs/2);
ylim(ax2, [0, freq_max_display]);

%当前帧瞬时频谱
ax3 = subplot(3, 2, 4);
h_spec = plot(ax3, freq, zeros(half_nfft, 1), 'g', 'LineWidth', 1.5);
xlim(ax3, [0, freq_max_display]);
ylim(ax3, [dB_min, dB_max]);
xlabel(ax3, '频率 (Hz)', 'Color', 'w', 'FontSize', 11);
ylabel(ax3, '幅度 (dB)', 'Color', 'w', 'FontSize', 11);
title(ax3, '当前帧瞬时频谱', 'Color', 'w', 'FontSize', 13);
ax3.Color = [0.08 0.08 0.08];
ax3.XColor = 'w'; ax3.YColor = 'w';
grid(ax3, 'on');
hold(ax3, 'on');
%频谱峰值标记
h_peaks = stem(ax3, freq(1:4:end), zeros(ceil(half_nfft/4), 1), ...
               'r.', 'MarkerSize', 4);
hold(ax3, 'off');

%信息栏
ax4 = subplot(3, 2, [5, 6]);
axis(ax4, 'off');
h_info = text(ax4, 0.5, 0.5, '', ...
              'Color', 'w', 'FontSize', 14, ...
              'HorizontalAlignment', 'center', ...
              'VerticalAlignment', 'middle', ...
              'FontName', 'Consolas');

%播放
fprintf('\n========================================\n');
fprintf('开始播放 — 请确认电脑音量已打开！\n');
fprintf('按任意键可提前终止。\n');
fprintf('========================================\n\n');

pause(0.5);

try
    player = audioplayer(audio, fs);
    play(player);
    use_player = true;
    fprintf('音频输出: audioplayer (正在播放...)\n');
catch
    use_player = false;
end
t_start = tic;

%主循环
while toc(t_start) < T_total + 0.5
    elapsed = toc(t_start);
    elapsed = min(elapsed, T_total);

    current_frame = round(elapsed / (step / fs));
    current_frame = min(max(current_frame, 1), n_frames);

    %更新时域波形
    h_cursor.Value = elapsed;
    h_patch.XData = [0, elapsed, elapsed, 0];
    h_tline.Value = elapsed;

    %更新当前帧频谱
    h_spec.YData = STFT_dB(:, current_frame);
    spec_curr = STFT_dB(:, current_frame);
    h_peaks.YData = spec_curr(1:4:end);

    %更新信息
    elapsed_min = floor(elapsed / 60);
    elapsed_sec = mod(elapsed, 60);
    total_min   = floor(T_total / 60);
    total_sec   = mod(T_total, 60);

    h_info.String = sprintf(['▶ 播放时间: %02d:%05.2f / %02d:%05.2f\n', ...
                             '  当前帧: %d / %d  |  %.0f fps\n', ...
                             '  窗函数: Hann  %d点 / %.0fms  |  fs=%dHz'], ...
                            elapsed_min, elapsed_sec, total_min, total_sec, ...
                            current_frame, n_frames, 1/0.03, ...
                            win_len, win_len/fs*1000, fs);

    drawnow;

    if getappdata(fig, 'stopFlag')
        break;
    end

    pause(0.03);
end

%清理音频
try %#ok<*TRYNC>
    if exist('player', 'var')
        stop(player);
    end
end
clear sound;

fprintf('播放结束。\n');

%输出完整时频图
figure('Name', '完整 STFT 时频图', ...
       'Position', [100, 100, 1200, 600], ...
       'Color', 'w');

imagesc(time_frames, freq, STFT_dB);
axis xy;
colormap('jet');
clim([dB_min, dB_max]);
cb = colorbar;
cb.Label.String = '幅度 (dB)';
cb.Label.FontSize = 12;

xlabel('时间 (s)', 'FontSize', 13);
ylabel('频率 (Hz)', 'FontSize', 13);
title(sprintf('STFT 时频图 — %s  (Hann窗, %d点, %.0fms)', ...
      filename, win_len, win_len/fs*1000), ...
      'FontSize', 14, 'Interpreter', 'none');
ylim([0, freq_max_display]);
