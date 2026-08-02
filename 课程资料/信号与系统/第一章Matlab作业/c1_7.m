%习题 1-7（1）（3）（4）

%定义x(t)
function y = f(t)
y1 = -t;
y2 = 1;
y3 = 2;
y = y1.* (t >= -1 & t <= 0) + y2.* (t > 0 & t <= 1) + y3.* (t > 1 & t <= 2);
end

%画出x(t)图像
t = linspace(-1, 2, 1000); %横坐标取值范围
subplot(2, 2, 1); %设置子图2*2
y = f(t);
plot(t, y, 'LineWidth', 2); %进行绘制
grid on; %打开网格
xlabel('t'); %x轴标记
ylabel('f(t)'); %y轴标记
xlim([-2, 3]); %横坐标显示范围
ylim([-1, 3]); %纵坐标显示范围

%(1)画出f(2t-1)图像
t_1 = linspace(0, 1.5, 1000); 
subplot(2, 2, 2);
y_1 = f(2 * t_1 - 1);
plot(t_1, y_1, 'LineWidth', 2);
grid on;
xlabel('t');
ylabel('f(2t-1)');
xlim([-1, 2]);
ylim([-1, 3]);

%(3)画出f(-t/2+1)图像
t_2 = linspace(-2, 4, 1000); 
subplot(2, 2, 3);
y_2 = f(-t_2 / 2 + 1);
plot(t_2, y_2, 'LineWidth', 2);
grid on;
xlabel('t');
ylabel('f(-t/2+1)');
xlim([-3, 5]);
ylim([-1, 3]);

%(4)画出f(t)[delta(t+1)+delta(t-2)]图像
subplot(2, 2, 4);
f_neg1 = f(-1); % 计算冲激强度 
f_2 = f(2);  
stem([-1, 2], [f_neg1, f_2], 'filled', 'LineWidth', 2); %画冲激函数
grid on;
xlabel('t');
ylabel('f(t)[delta(t+1)+delta(t-2)]');
xlim([-2, 3]);
ylim([-1, 3]);
