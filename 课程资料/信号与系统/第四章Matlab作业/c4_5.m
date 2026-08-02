%4-5(1)(4)(11)

%x1[n] = 3^(-n+1)u[n-1]
N1 = 10;
n1 = 0:N1-1;
x1 = (3.^(-n1+1)) .* (n1 >= 1);
X1 = fft(x1);
mag_X1 = abs(X1);%模
phase_X1 = angle(X1);%相位

%输出结果
fprintf('x1[n] = 3^{-n+1}u[n-1] \n');
fprintf('k\t|X1[k]|\t相位\n');
for k = 0:N1-1
    fprintf('%d\t%.4f\t%.4f\n', k, mag_X1(k+1), phase_X1(k+1));
end

%绘图
subplot(3,2,1);
stem(0:N1-1, mag_X1, 'filled','r','LineWidth',1.5);
title('模');
xlabel('k'); ylabel('|X_1[k]|');
grid on;

subplot(3,2,2);
stem(0:N1-1, phase_X1, 'filled','g','LineWidth',1.5);
title('相位');
xlabel('k'); ylabel('∠X_1[k]');
grid on;

%x2[n] = δ[6-2n]
N2 = 8;
n2 = 0:N2-1;
x2 = (n2 == 3);
X2 = fft(x2);
mag_X2 = abs(X2);%模
phase_X2 = angle(X2);%相位

%输出结果
fprintf('\nx2[n] = δ[6-2n]\n');
fprintf('k\t|X2[k]|\t相位\n');
for k = 0:N2-1
    fprintf('%d\t%.4f\t%.4f\n', k, mag_X2(k+1), phase_X2(k+1));
end

%绘图
subplot(3,2,3);
stem(0:N2-1, mag_X2, 'filled','r','LineWidth',1.5);
title('模');
xlabel('k'); ylabel('|X_2[k]|');
grid on;

subplot(3,2,4);
stem(0:N2-1, phase_X2, 'filled','g','LineWidth',1.5);
title('相位');
xlabel('k'); ylabel('∠X_2[k]');
grid on;

%x3[n]
N3 = 8;
M3 = 5;
n3 = 0:N3-1;
x3 = (n3 >= 0) & (n3 < M3);
X3 = fft(x3);
mag_X3 = abs(X3);%模
phase_X3 = angle(X3);%相位

%输出结果
fprintf('\nx3[n]\n');
fprintf('k\t|X3[k]|\t相位\n');
for k = 0:N3-1
    fprintf('%d\t%.4f\t%.4f\n', k, mag_X3(k+1), phase_X3(k+1));
end

%绘图
subplot(3,2,5);
stem(0:N3-1, mag_X3, 'filled','r','LineWidth',1.5);
title('模');
xlabel('k'); ylabel('|X_3[k]|');
grid on;

subplot(3,2,6);
stem(0:N3-1, phase_X3, 'filled','g','LineWidth',1.5);
title('相位');
xlabel('k'); ylabel('∠X_3[k]');
grid on;

%输出结果
%x1[n] = 3^{-n+1}u[n-1] 
%k	|X1[k]|	相位
%0	1.4999	0.0000
%1	1.3224	-0.8905
%2	1.0511	-1.5964
%3	0.8714	-2.1649
%4	0.7784	-2.6664
%5	0.7500	3.1416
%6	0.7784	2.6664
%7	0.8714	2.1649
%8	1.0511	1.5964
%9	1.3224	0.8905
%
%x2[n] = δ[6-2n]
%k	|X2[k]|	相位
%0	1.0000	0.0000
%1	1.0000	-2.3562
%2	1.0000	1.5708
%3	1.0000	-0.7854
%4	1.0000	3.1416
%5	1.0000	0.7854
%6	1.0000	-1.5708
%7	1.0000	2.3562
%
%x3[n]
%k	|X3[k]|	相位
%0	5.0000	0.0000
%1	2.4142	-1.5708
%2	1.0000	0.0000
%3	0.4142	-1.5708
%4	1.0000	0.0000
%5	0.4142	1.5708
%6	1.0000	-0.0000
%7	2.4142	1.5708
