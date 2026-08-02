
clear;

x = 2.9979*10^17*[1/365, 1/405, 1/436, 1/546, 1/577];
y = [1.866, 1.464, 1.264, 0.747, 0.626];

[p, S] = polyfit(x, y, 1);
k = p(1);      % 斜率
b = p(2);      % 截距

y_fit = polyval(p, x);
residuals = y - y_fit;     %计算残差

RSS = norm(residuals)^2;   %计算残差平方和
dof = length(y) - length(p);  %自由度
resid_std = sqrt(RSS / dof);

R = S.R;
cov_matrix = (resid_std^2) * inv(R * R'); % 计算系数（斜率和截距）的协方差矩阵
slope_std = sqrt(cov_matrix(1, 1));       % 斜率的标准差
intercept_std = sqrt(cov_matrix(2, 2));   % 截距的标准差

fprintf('h的不确定度 %.4ej·s\n',slope_std*1.6022*10^-19);
fprintf('W的不确定度 %.4ej\n',intercept_std*1.6022*10^-19);


x_f = linspace(min(x), max(x), 400);
y_f = polyval(p, x_f); 

figure;    %绘制图像
plot(x, y, 'o', 'DisplayName', '原始数据'); 
hold on;
plot(x_f, y_f, '-', 'DisplayName', '拟合直线');
xlabel('频率(Hz)');
ylabel('U(V)');
legend;
grid on;
hold off;

eq = sprintf('y = %.4ex + %.4e', k, b); %绘制函数式
text(5,5*10^14,1.8,eq);