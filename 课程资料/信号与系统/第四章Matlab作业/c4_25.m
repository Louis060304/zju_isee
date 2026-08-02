%4-25

%差分方程：y[n] + (1/6)y[n-1] - (1/6)y[n-2] = x[n] - x[n-1]

%分子
b = [1, -1];  
%分母
a = [1, 1/6, -1/6];  

%(1)系统频率响应
fprintf('(1) 系统频率响应\n');
[H, w] = freqz(b, a, 1024, 'whole');  
mag_H = abs(H);
phase_H = angle(H);

%绘制频率响应
figure('Name','系统频率响应','Position',[100,100,800,600]);
subplot(2,2,1);
plot(w/pi, mag_H, 'b','LineWidth',1.5);
title('频率响应幅度 |H(e^{j\omega})|');
xlabel('\omega / \pi');
ylabel('幅度');
grid on;
axis([0 2 0 max(mag_H)+0.1]);

subplot(2,2,2);
plot(w/pi, phase_H/pi, 'r','LineWidth',1.5);
title('频率响应相位 ∠H(e^{j\omega})');
xlabel('\omega / \pi');
ylabel('相位 / \pi');
grid on;
axis([0 2 -1.1 1.1]);

%(2)单位脉冲响应h[n]
fprintf('\n(2)单位脉冲响应h[n]\n');
N = 20;
n_h = 0:N-1;

h_impz = impz(b, a, N);
h_closed = (9/5)*(-1/2).^n_h - (4/5)*(1/3).^n_h;

%输出
fprintf('n\timpz计算值\t闭式解\t\t绝对误差\n');
for n = 0:4
    fprintf('%d\t%.6f\t%.6f\t%.6e\n', ...
        n, h_impz(n+1), h_closed(n+1), abs(h_impz(n+1)-h_closed(n+1)));
end
%绘制
subplot(2,2,3);
stem(n_h, h_impz, 'filled','b','LineWidth',1.5,'DisplayName','impz数值解');
hold on;
plot(n_h, h_closed, 'r--','LineWidth',1.5,'DisplayName','理论闭式解');
title('单位脉冲响应 h[n]');
xlabel('n');
ylabel('h[n]');
legend('Location','best');
grid on;

%(3)输入x[n]=4^{-n}u[n]的系统响应 =====================
fprintf('\n(3)系统对x[n] = 4^{-n}u[n]的响应\n');
n_x = 0:N-1;
x = (1/4).^n_x;  %输入


y_filter = filter(b, a, x);

y_closed = 3*(1/4).^n_x + (6/5)*(-1/2).^n_x - (16/5)*(1/3).^n_x;

%输出
fprintf('n\tfilter计算值\t闭式解\t\t绝对误差\n');
for n = 0:4
    fprintf('%d\t%.6f\t%.6f\t%.6e\n', ...
        n, y_filter(n+1), y_closed(n+1), abs(y_filter(n+1)-y_closed(n+1)));
end

%绘制
subplot(2,2,4);
stem(n_x, y_filter, 'filled','b','LineWidth',1.5,'DisplayName','filter数值解');
hold on;
plot(n_x, y_closed, 'r--','LineWidth',1.5,'DisplayName','理论闭式解');
title('系统对 x[n] = 4^{-n}u[n] 的响应 y[n]');
xlabel('n');
ylabel('y[n]');
legend('Location','best');
grid on;

%输出结果
%(1) 系统频率响应

%(2)单位脉冲响应h[n]
%n	impz计算值	闭式解		绝对误差
%0	1.000000	1.000000	0.000000e+00
%1	-1.166667	-1.166667	0.000000e+00
%2	0.361111	0.361111	0.000000e+00
%3	-0.254630	-0.254630	0.000000e+00
%4	0.102623	0.102623	1.387779e-17

%(3)系统对x[n] = 4^{-n}u[n]的响应
%n	filter计算值	闭式解		绝对误差
%0	1.000000	1.000000	0.000000e+00
%1	-0.916667	-0.916667	1.110223e-16
%2	0.131944	0.131944	2.775558e-17
%3	-0.221644	-0.221644	5.551115e-17
%4	0.047213	0.047213	0.000000e+00
