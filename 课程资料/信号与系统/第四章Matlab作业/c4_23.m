%4-23

%定义原信号DTFT X(e^jω)
%原信号是周期为2π的三角窗，在|ω|≤π/2时为1-(2/π)|ω|，其余为0
X = @(omega) arrayfun(@(w) ...
    (abs(mod(w + pi, 2*pi) - pi) <= pi/2) .* (1 - (2/pi)*abs(mod(w + pi, 2*pi) - pi)), ...
    omega);

%频率范围（两个周期）
omega = linspace(-2*pi, 2*pi, 2000);
X_original = X(omega);

%情况1：p[n] = cos(πn)
W1 = X(omega - pi);

%情况3：p[n] = Σδ[n-2k]
W3 = 0.5 * (X(omega) + X(omega - pi));

%绘图对比
figure('Name','DTFT调制性质验证','Position',[100,100,1000,800]);

%子图1：原信号频谱X(e^jω)
subplot(3,1,1);
plot(omega, X_original, 'b','LineWidth',1.5);
title('原信号频谱 X(e^{j\omega})');
xlabel('\omega (rad)');
ylabel('X(e^{j\omega})');
grid on;
axis([-2*pi 2*pi -0.1 1.1]);
xticks([-2*pi -3*pi/2 -pi -pi/2 0 pi/2 pi 3*pi/2 2*pi]);
xticklabels({'-2π','-3π/2','-π','-π/2','0','π/2','π','3π/2','2π'});

%子图2：调制后频谱W1(e^jω)（p[n]=cos(πn)）
subplot(3,1,2);
plot(omega, W1, 'r','LineWidth',1.5);
title('调制后频谱 W_1(e^{j\omega}) = X(e^{j(\omega-\pi)})');
xlabel('\omega (rad)');
ylabel('W_1(e^{j\omega})');
grid on;
axis([-2*pi 2*pi -0.1 1.1]);
xticks([-2*pi -3*pi/2 -pi -pi/2 0 pi/2 pi 3*pi/2 2*pi]);
xticklabels({'-2π','-3π/2','-π','-π/2','0','π/2','π','3π/2','2π'});

%子图3：调制后频谱W3(e^jω)（p[n]=周期冲激串）
subplot(3,1,3);
plot(omega, W3, 'g','LineWidth',1.5);
title('调制后频谱 W_3(e^{j\omega}) = 0.5[X(e^{j\omega}) + X(e^{j(\omega-\pi)})]');
xlabel('\omega (rad)');
ylabel('W_3(e^{j\omega})');
grid on;
axis([-2*pi 2*pi -0.1 0.6]);
xticks([-2*pi -3*pi/2 -pi -pi/2 0 pi/2 pi 3*pi/2 2*pi]);
xticklabels({'-2π','-3π/2','-π','-π/2','0','π/2','π','3π/2','2π'});
