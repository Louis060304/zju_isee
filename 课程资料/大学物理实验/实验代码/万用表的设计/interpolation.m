
x = 0.001*[ 0.22, 0.42, 0.59, 0.75, 0.84, 0.89]; 
y = [ 5000, 2000, 1000, 500, 300, 200]; 

fitType = 'a/x + b';

[fittedModel, goodnessOfFit] = fit(x', y', fitType, 'StartPoint', [1, 1]);

disp('拟合系数 a, b 为:');
disp(fittedModel.a);
disp(fittedModel.b);

plot(fittedModel, x, y);  %绘制函数
xlabel('I(A)');
ylabel('R_x(Ohm)');
legend('原始数据', '拟合曲线');