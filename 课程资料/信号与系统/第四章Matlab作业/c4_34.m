%4-34

%参数定义
b = [1, -1];%分子
a = [1, -5/6, 1/6];%分母

%输出理论结果
fprintf('理论推导结果\n');
fprintf('(1) 系统差分方程：\n');
fprintf('    y[n] - (5/6)y[n-1] + (1/6)y[n-2] = x[n] - x[n-1]\n');
fprintf('    或 y[n] = (5/6)y[n-1] - (1/6)y[n-2] + x[n] - x[n-1]\n\n');

fprintf('(2) 系统频率响应：\n');
fprintf('    H(e^{jω}) = (1 - e^{-jω}) / (1 - (5/6)e^{-jω} + (1/6)e^{-j2ω})\n\n');

fprintf('(3) 系统单位脉冲响应：\n');
fprintf('    h[n] = [-3*(1/2)^n + 4*(1/3)^n] u[n]\n\n');

%频率响应
[H, w] = freqz(b, a, 1024);%计算0~π范围内1024点频率响应
mag_H = abs(H);%幅度响应
phase_H = angle(H);%相位响应（弧度）

%单位脉冲响应
N = 20;
n_h = 0:N-1;
h_impz = impz(b, a, N);
h_closed = -3*(1/2).^n_h + 4*(1/3).^n_h;

fprintf('单位脉冲响应验证\n');
fprintf('n\timpz计算值\t理论闭式解\t绝对误差\n');
for n = 0:4
    fprintf('%d\t%.6f\t%.6f\t%.6e\n', ...
        n, h_impz(n+1), h_closed(n+1), abs(h_impz(n+1)-h_closed(n+1)));
end
fprintf('\n');

%零极点图
[z, p, k] = tf2zpk(b, a);  %转换为零极点形式

%绘制
figure('Name','因果LTI系统完整分析','Position',[100,100,1000,800]);

%频率响应幅度
subplot(2,2,1);
plot(w/pi, mag_H, 'b','LineWidth',1.5);
title('频率响应幅度 |H(e^{j\omega})|');
xlabel('\omega / \pi'); ylabel('幅度');
grid on; axis([0 1 0 max(mag_H)+0.1]);

%频率响应相位
subplot(2,2,2);
plot(w/pi, phase_H/pi, 'r','LineWidth',1.5);
title('频率响应相位 ∠H(e^{j\omega})');
xlabel('\omega / \pi'); ylabel('相位 / \pi');
grid on; axis([0 1 -1.1 1.1]);

% 单位脉冲响应
subplot(2,2,3);
stem(n_h, h_impz, 'filled','b','LineWidth',1.5,'DisplayName','impz数值解');
hold on;
plot(n_h, h_closed, 'r--','LineWidth',1.5,'DisplayName','理论闭式解');
title('单位脉冲响应 h[n]');
xlabel('n'); ylabel('h[n]');
legend('Location','best');
grid on;

%系统零极点图
subplot(2,2,4);
zplane(z, p);
title('系统零极点图');
grid on;

%输出结果
%理论推导结果
%(1) 系统差分方程：
%    y[n] - (5/6)y[n-1] + (1/6)y[n-2] = x[n] - x[n-1]
%    或 y[n] = (5/6)y[n-1] - (1/6)y[n-2] + x[n] - x[n-1]

%(2) 系统频率响应：
%    H(e^{jω}) = (1 - e^{-jω}) / (1 - (5/6)e^{-jω} + (1/6)e^{-j2ω})

%(3) 系统单位脉冲响应：
%    h[n] = [-3*(1/2)^n + 4*(1/3)^n] u[n]

%单位脉冲响应验证
%n	impz计算值	理论闭式解	绝对误差
%0	1.000000	1.000000	0.000000e+00
%1	-0.166667	-0.166667	1.110223e-16
%2	-0.305556	-0.305556	5.551115e-17
%3	-0.226852	-0.226852	5.551115e-17
%4	-0.138117	-0.138117	0.000000e+00
