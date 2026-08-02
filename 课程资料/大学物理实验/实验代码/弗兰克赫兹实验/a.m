
clear;

x = [1, 2, 3, 4, 5, 6];
y = [26.9, 37.5, 49.1, 61.3, 74.5, 87.0];

p = polyfit(x, y, 1);
k = p(1);      % 斜率
b = p(2);      % 截距

y_f = polyval(p, x);

residual = y - y_f;          %计算残差
std = std(residual);         %计算标准差
A_uncertainty = std/sqrt(6);   %计算不确定度
R_squared = 1 - (sum(residual.^2)/sum((y-mean(y)).^2)); %计算决定系数R^2

fprintf('U0：%.1fV\n',k);
fprintf('标准差：%.4f\n',std);
fprintf('A类不确定度：%.4fV\n',A_uncertainty);
fprintf('决定系数R^2：%.4f\n',R_squared);

x_fit = linspace(min(x), max(x), 100);
y_fit = polyval(p, x_fit); 

figure;    %绘制图像
plot(x, y, 'o', 'DisplayName', '原始数据'); 
hold on;
plot(x_fit, y_fit, '-', 'DisplayName', '拟合直线');
xlabel('峰值序号');
ylabel('U_G_2_K(V)');
legend;
grid on;
hold off;

eq = sprintf('y = %.1fx + %.1f', k, b); %绘制函数式
text(2,80,eq);