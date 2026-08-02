
x = [1.00, 0.95, 0.89, 0.84, 0.75, 0.59, 0.42, 0.22, 0.12, 0.03];
y = [0, 100, 200, 300, 500, 1000, 2000, 5000, 10000, 30000];

xi = linspace(min(x), max(x), 1000);  %插值点
yi_spline = interp1(x, y, xi, 'spline');  %进行三次样条插值

figure('Position', [100, 100, 1200, 500]);  %绘制图像
subplot(1,2,1);
plot(xi, yi_spline, 'b-', 'LineWidth', 2);
hold on;
plot(x, y, 'ro', 'MarkerSize', 8, 'MarkerFaceColor', 'red');
grid on;
xlabel('I(mA)');
ylabel('R_x(Ohm)');
legend('show', 'Location', 'northeast');