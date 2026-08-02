%功能：录音-播放-保存

%设置采样率（Hz）
smp_rate = 44100;
%设置ADC位数
adc_bit = 16;
%设置录音通道数（1=单声道，2=立体声）
n_chls = 1;

%创建录音对象，参数依次为：采样率、位数、通道数
rec = audiorecorder(smp_rate, adc_bit, n_chls);

%提示开始说话
disp('start speaking');

%设置录音时长（秒）
T = 5;
%开始阻塞式录音，持续T秒
recordblocking(rec, T);

%提示停止说话
disp('stop speaking');

%从录音对象中获取音频数据（列向量）
y = getaudiodata(rec);

x = linspace(0, T, smp_rate * T);

%绘制时域波形图
plot(x, y);
xlabel('Time(s)');
title('Time Domain for Recording');

%播放录制的音频
play(rec);

%保存录音文件
if ~exist('./data/number/', 'dir')
    mkdir('./data/number/');
end
audiowrite('./data/numbers/10.wav', y, smp_rate);
disp('录音已保存至 ./data/numbers/x.wav');