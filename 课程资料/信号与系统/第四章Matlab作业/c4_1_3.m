%4-1(3)

N = 4;%周期
n = 0:N-1;
x = [2, 4, 0, 0];%值
a = fft(x) / N;%傅里叶级数
mag_a = abs(a);%模
phase_a = angle(a);%相位

fprintf('傅里叶级数\n');
for k = 0:N-1
    fprintf('a_%d = %.4f + j%.4f\n', k, real(a(k+1)), imag(a(k+1)));
end

fprintf('模|a_k|\n');
for k = 0:N-1
    fprintf('|a_%d| = %.4f\n', k, mag_a(k+1));
end

fprintf('相位∠a_k\n');
for k = 0:N-1
    fprintf('∠a_%d = %.4f\n', k, phase_a(k+1));
end

%输出结果
%傅里叶级数
%a_0 = 1.5000 + j0.0000
%a_1 = 0.5000 + j-1.0000
%a_2 = -0.5000 + j0.0000
%a_3 = 0.5000 + j1.0000
%模|a_k|
%|a_0| = 1.5000
%|a_1| = 1.1180
%|a_2| = 0.5000
%|a_3| = 1.1180
%相位∠a_k
%∠a_0 = 0.0000
%∠a_1 = -1.1071
%∠a_2 = 3.1416
%∠a_3 = 1.1071