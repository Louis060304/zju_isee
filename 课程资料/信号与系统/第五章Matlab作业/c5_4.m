%5-4

%参数
T = 0.2;
fs = 1/T;
t_total = -2:0.001:2; 
x_original = @(t) cos(2*pi*t);

%采样
n = -10:10;
tn = n*T;
xn = x_original(tn);

%线性内插

h_fun = @(tau) (1-abs(tau)/T).*(abs(tau)<=T);%三角波
x_r_conv = zeros(size(t_total));
for idx = 1:length(t_total)
    t = t_total(idx);
    sum_val = 0;
    for k = 1:length(n)
        sum_val = sum_val + xn(k)*h_fun(t - tn(k));
    end
    x_r_conv(idx) = sum_val;
end


x_r_interp = interp1(tn, xn, t_total, 'linear','extrap');

%绘图
figure('Color','w');

subplot(2,1,1);
plot(t_total, x_original(t_total), 'k-','LineWidth',1.2); hold on;
stem(tn, xn, 'r','filled','MarkerSize',4);
title('原始信号 x(t)=cos(2\pi t) 与采样点(T=0.2)');
xlabel('t (s)'); ylabel('x(t)');
grid on; xlim([-2 2]);

subplot(2,1,2);
plot(t_total, x_original(t_total), 'k--','LineWidth',1.2); hold on;
plot(t_total, x_r_conv, 'b-','LineWidth',1);
plot(t_total, x_r_interp, 'g-.','LineWidth',1);
legend('原始信号','卷积实现线性内插','interp1线性内插','Location','best');
title('一阶线性内插输出对比');
xlabel('t (s)'); ylabel('x_r(t)');
grid on; xlim([-2 2]);
