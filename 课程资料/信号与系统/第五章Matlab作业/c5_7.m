%5-7

%参数
T = 1;
A = 1; B = 1; theta = 0;
Delta = 0.2;
P = T + Delta;
a = Delta / P;%时间缩放
f0 = 1/T;%原始信号频率
fc = 1/(2*P);%低通截止频率
fprintf('参数：\n原周期T=%.2f s，延迟Δ=%.2f s\n采样间隔P=%.2f s，缩放因子a=%.4f\n原频率f0=%.2f Hz，慢放后fa=%.4f Hz，低通截止fc=%.4f Hz\n',...
    T,Delta,P,a,f0,a*f0,fc);

%生成原始信号与理论慢放信号
t_ori = linspace(0, 6*T, 10000);
x_ori = A + B*cos(2*pi*f0*t_ori + theta);

t_rec = linspace(0, 6*P, 10000); 
x_scaled = A + B*cos(2*pi*f0*a*t_rec + theta);

%采样点
n_list = 0:floor(max(t_rec)/P);
tn = n_list * P;
xn = A + B*cos(2*pi*f0*tn + theta);

%理想低通sinc插值重构输出
h_fun = @(t) (1/P)*sinc(t/P);
y_rec = zeros(size(t_rec));
for idx = 1:length(t_rec)
    tau = t_rec(idx);
    y_rec(idx) = sum(xn .* h_fun(tau - tn));
end

%绘图
figure('Color','w','Position',[100,100,900,750]);

subplot(3,1,1);
plot(t_ori, x_ori, 'k-','LineWidth',1.2); hold on;
stem(tn, zeros(size(tn)), 'r','filled','MarkerSize',4);
title('原始周期信号与逐周期延迟采样时刻');
xlabel('t (s)'); ylabel('x(t)');
grid on; xlim([0 max(t_rec)]);
legend('原始x(t)','采样冲激位置','Location','best');


subplot(3,1,2);
plot(t_rec, x_scaled, 'g--','LineWidth',1.5); hold on;
plot(t_rec, y_rec, 'b-','LineWidth',1);
title(['慢放波形对比：理论x(at) (a=',num2str(a,4),') 与重构y(t)']);
xlabel('t (s)'); ylabel('幅值');
grid on; xlim([0 max(t_rec)]);
legend('理论x(at)','采样重构y(t)','Location','best');


subplot(3,1,3);
Fs_sim = 1000; NFFT = 2^16;
Y_fft = fft(y_rec, NFFT);
f_axis = (0:NFFT/2-1)*(Fs_sim/NFFT);
Y_amp = 2/NFFT*abs(Y_fft(1:NFFT/2));
plot(f_axis, Y_amp, 'b-'); hold on;
xline(fc,'r--',sprintf('截止f_c=%.3f Hz',fc));
xline(a*f0,'g--',sprintf('慢放频率f_a=%.3f Hz',a*f0));
title('重构信号频谱与低通截止约束');
xlabel('频率f (Hz)'); ylabel('幅度');
xlim([0 3*fc]); grid on;
legend('y(t)频谱','低通截止频率','目标慢放频率','Location','best');
