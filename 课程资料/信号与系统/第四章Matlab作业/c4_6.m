%4-6(2)(6)(8)

%信号1：X1(e^jω) = 1 - e^(-jω) + 2e^(-j2ω) - 3e^(-j3ω) + 4e^(-j4ω)

%生成时域序列
n1 = 0:4;
x1 = [1, -1, 2, -3, 4];
fprintf('x1[n] = ['); fprintf('%.0f ', x1); fprintf('] (n=0~4)\n\n');

%绘制时域信号
figure('Name','信号1','Position',[100,100,600,400]);
stem(n1, x1, 'filled','b','LineWidth',1.5);
title('时域信号 x_1[n]');
xlabel('n'); ylabel('x_1[n]');
grid on;
axis([-0.5 4.5 -3.5 4.5]);

%信号2：X2(e^jω) = (1 - e^(-jω)) / (1 - (5/6)e^(-jω) + (1/6)e^(-j2ω))

fprintf('x2[n] = [-3*(1/2)^n + 4*(1/3)^n] u[n]\n\n');

%生成时域序列（n=20截断）
n2 = 0:20;
x2 = -3*(1/2).^n2 + 4*(1/3).^n2;

%绘制时域信号
figure('Name','信号2','Position',[100,100,600,400]);
stem(n2, x2, 'filled','r','LineWidth',1.5);
title('时域信号 x_2[n]');
xlabel('n'); ylabel('x_2[n]');
grid on;

%信号3
fprintf('x[0] = 1/2\n');
fprintf('x[n] = [sin(nπ/8) + sin(3nπ/8)]/(πn)\n\n');

%生成时域序列（n=±20截断）
n3 = -20:20;
x3 = zeros(size(n3));
for idx = 1:length(n3)
    n = n3(idx);
    if n == 0
        x3(idx) = 1/2;
    else
        x3(idx) = (sin(n*pi/8) + sin(3*n*pi/8))/(pi*n);
    end
end

%绘制时域信号
figure('Name','信号3','Position',[100,100,600,400]);
stem(n3, x3, 'filled','g','LineWidth',1.5);
title('时域信号 x_3[n]');
xlabel('n'); ylabel('x_3[n]');
grid on;

%输出结果
%x1[n] = [1 -1 2 -3 4 ] (n=0~4)

%x2[n] = [-3*(1/2)^n + 4*(1/3)^n] u[n]

%x[0] = 1/2
%x[n] = [sin(nπ/8) + sin(3nπ/8)]/(πn)
