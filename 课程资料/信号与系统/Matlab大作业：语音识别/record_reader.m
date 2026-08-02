%读取录音-播放-绘图
close all; clear all;

%读取WAV格式音频文件（返回音频数据data_wav和采样率fs_wav）
[data_wav, fs_wav] = audioread('./data/0.wav');

%读取MP3格式音频文件（返回音频数据data_mp和采样率fs_mp）
%[data_mp, fs_mp] = audioread('./data/rec1.mp3');

%播放
sound(data_wav, fs_wav);

%创建一个音频播放器对象，便于控制播放过程
player = audioplayer(data_wav, fs_wav);

%开始播放音频
play(player);
pause(5);%程序暂停5秒
pause(player);%暂停当前正在播放的音频
pause(5);
stop(player);

%绘制MP3音频数据的时域波形图
plot(data_wav);
title('Time Domain Signals');