%第3、4部分
x1 = [6.70, 6.38, 6.00, 5.49, 5.00, 4.00, 3.00, 2.00, 1.00, 0.00, -1.00, -2.00, -3.00, -4.00, -5.00, -5.44];
y1 = [1.85, 1.38, 1.13, 1.00, 1.08, 1.38, 1.92, 2.58, 3.19, 3.81, 4.10, 4.21, 4.08, 3.71, 3.00, 2.65];

pp1 = csape(x1, y1, 'second');
x1_fine = linspace(min(x1), max(x1), 1000);
y1_spline = ppval(pp1, x1_fine);

figure;
plot(y1, x1, 'ro', 'MarkerSize', 2, 'LineWidth', 2);
hold on;
plot(y1_spline,x1_fine, 'b-', 'LineWidth', 2);
grid on;
xlabel('x');
ylabel('y');

%第5部分
x2 = [-5.44, -5.83, -6.00, -6.37, -6.46 -6.62];
y2 = [2.65, 2.71, 2.67, 2.37, 2.00, 0.00];

pp2 = csape(x2, y2, 'second');
x2_fine = linspace(min(x2), max(x2), 1000);
y2_spline = ppval(pp2, x2_fine);

plot(y2, x2, 'ro', 'MarkerSize', 2, 'LineWidth', 2);
hold on;
plot(y2_spline, x2_fine, 'b-', 'LineWidth', 2);
grid on;

%第1、2部分
hold on;
x0 = linspace(0, 1.85, 100);
y0 = 7.00 * ones(size(x0));
plot(x0, y0, 'b-', 'LineWidth', 2);

y1 = linspace(6.70, 7.00, 100);
x1 = 1.85 + sqrt(0.0225 - (y1 - 6.85).^2);
plot(x1, y1, 'b-', 'LineWidth', 2);

axis equal;
grid on;
hold off;