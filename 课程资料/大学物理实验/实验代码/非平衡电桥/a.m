
clear;

x = [25, 30, 35, 40, 45, 50, 55, 60];
y = [55.53,	56.58,	57.68,	58.78,	59.82,	60.94,	62.02,	63.13];

p = polyfit(x, y, 1);
k = p(1);      % 斜率
b = p(2);      % 截距

y_f = polyval(p, x);

residual = y - y_f;          %计算残差
R_squared = 1 - (sum(residual.^2)/sum((y-mean(y)).^2)); %计算决定系数R^2

fprintf('斜率：%.4f\n',k);
fprintf('截距：%.4f\n',b);
fprintf('决定系数R^2：%.4f\n',R_squared);

x_fit = linspace(min(x), max(x), 100);
y_fit = polyval(p, x_fit); 

figure;    %绘制图像
plot(x, y, 'o', 'DisplayName', '原始数据'); 
hold on;
plot(x_fit, y_fit, '-', 'DisplayName', '拟合直线');
xlabel('t/℃');
ylabel('R_t/Ω');
legend;
grid on;
hold off;

eq = sprintf('y = %.4fx + %.4f', k, b); %显示函数式
text(30,62,eq);