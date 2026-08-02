%4-2(2)

N = 8;%周期
k = 0:N-1;
a = sin(k * pi / 4);%傅里叶级数
x = N * ifft(a);        

fprintf('x[n](n=0-7)\n');
for n = 0:N-1
    real_part = real(x(n+1));
    imag_part = imag(x(n+1)); 
    fprintf('x[%d] = %.4f + j%.4f\n', n, real_part, imag_part);
end

%输出结果
%x[n](n=0-7)
%x[0] = 0.0000 + j0.0000
%x[1] = -0.0000 + j4.0000
%x[2] = 0.0000 + j0.0000
%x[3] = 0.0000 + j0.0000
%x[4] = 0.0000 + j0.0000
%x[5] = 0.0000 + j-0.0000
%x[6] = 0.0000 + j-0.0000
%x[7] = -0.0000 + j-4.0000
