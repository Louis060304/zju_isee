%4-32
%系统：H(ejω) = H1(ejω)H2(ejω) + (1-H1(ejω))H3(ejω)

%各子系统频率
omega_plot = linspace(-2*pi, 2*pi, 2000);
N_fft = 2048;%逆DTFT用采样频率
omega_fft = linspace(-pi, pi, N_fft);

%H1(ejω)：高通滤波器（|ω| mod 2π ≥ π/2时为1，否则为0）
H1 = @(omega) arrayfun(@(w) ...
    abs(mod(w + pi, 2*pi) - pi) >= pi/2, omega);

%H2(ejω)：周期为2π的分段线性函数
H2 = @(omega) arrayfun(@(w) helper_H2(mod(w + pi, 2*pi) - pi), omega);

%H3(ejω)：周期为2π的三角波函数
H3 = @(omega) arrayfun(@(w) helper_H3(mod(w + pi, 2*pi) - pi), omega);

%输入频谱X(ejω)：周期为2π的梯形函数
X = @(omega) arrayfun(@(w) helper_X(mod(w + pi, 2*pi) - pi), omega);

%总系统频率响应
H_total = @(omega) H1(omega).*H2(omega) + (1 - H1(omega)).*H3(omega);

%输出频谱Y(ejω) = H(ejω)·X(ejω)
Y = @(omega) H_total(omega) .* X(omega);

%各频率响应数值
H1_val = H1(omega_plot);
H2_val = H2(omega_plot);
H3_val = H3(omega_plot);
H_total_val = H_total(omega_plot);
X_val = X(omega_plot);
Y_val = Y(omega_plot);

%逆DTFT计算时域输出
Y_sampled = Y(omega_fft);
y = ifftshift(ifft(fftshift(Y_sampled)));
y = real(y); 
n = -N_fft/2 : N_fft/2 - 1;

n_plot = -20:20;
y_plot = y(ismember(n, n_plot));

%绘制
figure('Name','离散时间LTI系统完整分析','Position',[100,100,1200,900]);

%H1(ejω)
subplot(3,3,1);
plot(omega_plot/pi, H1_val, 'b','LineWidth',1.5);
title('H_1(e^{j\omega}) 高通滤波器');
xlabel('\omega / \pi'); ylabel('幅度');
grid on; axis([-2 2 -0.1 1.1]);
xticks(-2:0.5:2);

%H2(ejω)
subplot(3,3,2);
plot(omega_plot/pi, H2_val, 'r','LineWidth',1.5);
title('H_2(e^{j\omega})');
xlabel('\omega / \pi'); ylabel('幅度');
grid on; axis([-2 2 0.9 2.1]);
xticks(-2:0.5:2);

%H3(ejω)
subplot(3,3,3);
plot(omega_plot/pi, H3_val, 'g','LineWidth',1.5);
title('H_3(e^{j\omega})');
xlabel('\omega / \pi'); ylabel('幅度');
grid on; axis([-2 2 -0.1 2.1]);
xticks(-2:0.5:2);

%总系统频率响应
subplot(3,3,4);
plot(omega_plot/pi, H_total_val, 'm','LineWidth',1.5);
title('总系统频率响应 H(e^{j\omega})');
xlabel('\omega / \pi'); ylabel('幅度');
grid on; axis([-2 2 -0.1 2.1]);
xticks(-2:0.5:2);

%输入频谱
subplot(3,3,5);
plot(omega_plot/pi, X_val, 'c','LineWidth',1.5);
title('输入频谱 X(e^{j\omega})');
xlabel('\omega / \pi'); ylabel('幅度');
grid on; axis([-2 2 -0.1 1.1]);
xticks(-2:0.5:2);

%输出频谱
subplot(3,3,6);
plot(omega_plot/pi, Y_val, 'k','LineWidth',1.5);
title('输出频谱 Y(e^{j\omega})');
xlabel('\omega / \pi'); ylabel('幅度');
grid on; axis([-2 2 -0.1 2.1]);
xticks(-2:0.5:2);

% 时域输出y[n]
subplot(3,3,7:9);
stem(n_plot, y_plot, 'filled','b','LineWidth',1.5);
title('时域输出 y[n]（n=-20~20）');
xlabel('n'); ylabel('y[n]');
grid on; axis([-20.5 20.5 min(y_plot)-0.1 max(y_plot)+0.1]);

%输出
fprintf('y[0]  = %.6f （理论值：1.000000）\n', y(n==0));
fprintf('y[±1] = %.6f （理论值：≈0.174042）\n', y(n==1));
fprintf('y[±2] = %.6f （理论值：0.000000）\n', y(n==2));
fprintf('y[±3] = %.6f （理论值：≈0.302260）\n', y(n==3));
fprintf('y[±4] = %.6f （理论值：0.000000）\n', y(n==4));

%函数定义
function h2 = helper_H2(w)
    abs_w = abs(w);
    if abs_w <= pi/2
        h2 = 1 + (2/pi)*abs_w;
    else
        h2 = 2;
    end
end

function h3 = helper_H3(w)
    abs_w = abs(w);
    if abs_w <= pi/2
        h3 = 2 - (4/pi)*abs_w;
    else
        h3 = (4/pi)*(abs_w - pi/2);
    end
end

function x = helper_X(w)
    abs_w = abs(w);
    if abs_w <= pi/2
        x = 1;
    else
        x = (2/pi)*(pi - abs_w);
    end
end

%y[0]  = 0.999023 （理论值：1.000000）
%y[±1] = 0.174345 （理论值：≈0.174042）
%y[±2] = -0.000000 （理论值：0.000000）
%y[±3] = 0.302311 （理论值：≈0.302260）
%y[±4] = -0.000000 （理论值：0.000000）