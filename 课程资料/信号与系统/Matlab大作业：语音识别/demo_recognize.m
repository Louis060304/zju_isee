
close all;

%参数
T_record = 2;
smp_rate = 44100;
template_path = './data/data_fft.mat';

%模板 ----
if ~exist(template_path, 'file')
    fprintf('未找到训练模板，请先运行:\n');
    fprintf('  1. recorder           → 录制数字0-9\n');
    fprintf('  2. batch_fft_numbers   → 训练模板\n');
    return;
end

%录制
rec = audiorecorder(smp_rate, 16, 1);

fprintf('请在提示后清晰朗读数字(可连续读多个，如"123")...\n');
pause(2);
fprintf('开始录音！\n');
recordblocking(rec, T_record);
fprintf('录音结束，正在识别...\n');

y = getaudiodata(rec);

%多数字识别
[digits, all_scores] = recognize_digits(y, smp_rate, template_path);

if isempty(digits)
    fprintf('未识别到数字，请重试\n');
    return;
end

%取第一个数字做频谱展示
digit  = digits(1);
scores = all_scores(1, :);

%单独提取第一段做可视化
frac = 0.3;
N_smp = length(y);
win_len = floor(frac * N_smp);
[~, start_idx] = maxSumSubArray(abs(y), frac);
y_cut = y(start_idx : win_len + start_idx - 1);
[spec, f_shift] = extract_feature(y, smp_rate, frac);

%绘图
figure('Name', '数字语音识别结果', 'NumberTitle', 'off', ...
       'Position', [100, 100, 900, 600]);

%子图1：原始录音时域波形
subplot(2, 3, 1);
t_full = (0:length(y)-1) / smp_rate;
frac = 0.3;
N_smp = length(y);
win_len = floor(frac * N_smp);
[~, start_idx] = maxSumSubArray(abs(y), frac);
plot(t_full, y);
hold on;
yl = ylim;
fill([start_idx, start_idx+win_len, start_idx+win_len, start_idx] / smp_rate, ...
     [yl(1), yl(1), yl(2), yl(2)], 'r', 'FaceAlpha', 0.15, 'EdgeColor', 'none');
hold off;
xlabel('Time (s)'); ylabel('Amplitude');
title('原始录音时域波形（红框=检测语音段）');
grid on;

%子图2：截取的语音段
subplot(2, 3, 2);
t_cut = (0:length(y_cut)-1) / smp_rate;
plot(t_cut, y_cut, 'r');
xlabel('Time (s)'); ylabel('Amplitude');
title('截取的语音段（滑动窗法）');
grid on;

%子图3：FFT幅度谱
subplot(2, 3, 3);
plot(f_shift, spec);
xlabel('Frequency (Hz)'); ylabel('|X(f)|');
title('手动蝶形FFT幅度谱');
xlim([0, smp_rate/2]);
grid on;

%子图4-6：与最佳3个模板的对比
digits_to_show = [digit, mod(digit+1, 10), mod(digit+2, 10)];
titles = {'最佳匹配模板', '次近模板', '第三模板'};
S = load(template_path, 'templates');
templates = S.templates;

for j = 1:3
    subplot(2, 3, 3+j);
    d = digits_to_show(j);
    tpl = templates{d+1}(:);
    f_tpl = (-length(tpl)/2 : length(tpl)/2-1) * (smp_rate / length(tpl));

    plot(f_shift, spec / max(spec), 'b', 'LineWidth', 1); hold on;
    plot(f_tpl, tpl / max(tpl), 'r--', 'LineWidth', 1);
    xlabel('Frequency (Hz)'); ylabel('归一化幅度');
    title(sprintf('%s: 数字%d (r=%.3f)', titles{j}, d, scores(d+1)));
    legend('输入', '模板', 'Location', 'best');
    xlim([0, smp_rate/2]);
    grid on;
end

sgtitle(sprintf('识别结果: [%s]  (置信度: %.1f%%)', join(string(digits), ', '), max(all_scores(1,:))*100));
