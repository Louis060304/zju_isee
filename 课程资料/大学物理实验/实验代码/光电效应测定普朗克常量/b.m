clear;

x = [];                                       %x轴数据
y = [87, 101, 117, 137, 162, 196];            %y轴数据

p = polyfit(x, y, n);                        %n为多项式拟合的次数

x_fit = linspace(min(x), max(x), 100);
y_fit = polyval(p, x_fit); 

figure;                                      %绘制图像
plot(x, y, 'o', 'DisplayName', '原始数据'); 
hold on;
plot(x_fit, y_fit, '-', 'DisplayName', '拟合曲线');
xlabel('');                                  %单位标注
ylabel('');
legend;
grid on;
hold off;