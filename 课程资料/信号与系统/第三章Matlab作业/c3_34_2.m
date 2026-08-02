%3-34(2)题仿真

E = 1;%输入信号幅度
wc = 1;%滤波器截止频率(rad/s)
Ts = 0.01;%采样间隔(0.01s)
T_list = [0.1*2*pi/wc, 2*2*pi/wc, 10*2*pi/wc];%T的取值（3个）
T_labels = {'T = (1/10)(2π/ω_c)', 'T = 2(2π/ω_c)', 'T = 10(2π/ω_c)'};

%时间范围
t_h = (- 15*2*pi/wc) : Ts : (15*2*pi/wc);

%滤波器的时域函数
h = (wc/pi) * sinc(wc*t_h/pi);

for i = 1:length(T_list)
    T = T_list(i);
    
    %输入信号x(t)
    t_x = 0 : Ts : 3*T;
    x = zeros(size(t_x));
    x(t_x >= 0 & t_x < T) = 2*E;
    x(t_x >= T & t_x < 2*T) = -2*E;
    x(t_x >= 2*T & t_x < 3*T) = 2*E;
    
    y = conv(x, h) * Ts;
    t_y = (t_x(1) + t_h(1)) : Ts : (t_x(end) + t_h(end));
    
    subplot(3,1,i);
    plot(t_y, y, 'b-', 'LineWidth',1.5);
    title(['输出波形 (', T_labels{i}, ')']);
    xlabel('时间 t (s)');
    ylabel('幅度');
    legend('输出 y(t)','Location','best');
    grid on;
    xlim([min(t_y), max(t_y)]);
end
