%第3、4部分
x1_known = [6.70, 6.38, 6.00, 5.49, 5.00, 4.00, 3.00, 2.00, 1.00, 0.00, -1.00, -2.00, -3.00, -4.00, -5.00, -5.44];
y1_known = [1.85, 1.38, 1.13, 1.00, 1.08, 1.38, 1.92, 2.58, 3.19, 3.81, 4.10, 4.21, 4.08, 3.71, 3.00, 2.65];

x1_fit = linspace(min(x1_known), max(x1_known), 1000);
y1_fit = zeros(size(x1_fit));

n1 = length(x1_known);

for k1 = 1:length(x1_fit)
    L1 = 0;
    for i1 = 1:n1
        basis1 = 1;
        for j1 = 1:n1
            if j1 ~= i1
                basis1 = basis1 * (x1_fit(k1) - x1_known(j1)) / (x1_known(i1) - x1_known(j1));
            end
        end
        L1 = L1 + y1_known(i1) * basis1;
    end
    y1_fit(k1) = L1;
end

figure;
plot(y1_known, x1_known, 'ro', 'MarkerSize', 2, 'LineWidth', 2);
hold on;
plot(y1_fit, x1_fit, 'b-', 'LineWidth', 2);
grid on;
xlabel('x');
ylabel('y');

%第5部分
x2_known = [-5.44, -6.00, -6.46, -6.62];
y2_known = [2.65, 2.67, 2.00, 0.00];

x2_fit = linspace(min(x2_known), max(x2_known), 1000);
y2_fit = zeros(size(x2_fit));

n2 = length(x2_known);

for k2 = 1:length(x2_fit)
    L2 = 0;
    for i2 = 1:n2
        basis2 = 1;
        for j2 = 1:n2
            if j2 ~= i2
                basis2 = basis2 * (x2_fit(k2) - x2_known(j2)) / (x2_known(i2) - x2_known(j2));
            end
        end
        L2 = L2 + y2_known(i2) * basis2;
    end
    y2_fit(k2) = L2;
end

plot(y2_known, x2_known, 'ro', 'MarkerSize', 2, 'LineWidth', 2);
hold on;
plot(y2_fit, x2_fit, 'b-', 'LineWidth', 2);
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