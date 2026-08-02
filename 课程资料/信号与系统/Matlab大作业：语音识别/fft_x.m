function X = fft_x(x)
    %手动实现基于蝶形运算的FFT

    %输入x：为一个矩阵
    [orig_rows, orig_cols] = size(x);

    %当x不为列向量时：应该逐列进行FFT
    if orig_cols > 1 && orig_rows > 1
        X = zeros(orig_rows, orig_cols);
        for c = 1:orig_cols
            X(:, c) = fft_x(x(:, c));
        end
        return;
    end

    %保证x为列向量
    x = x(:);
    N_orig = length(x);

    %先进行补零（达到2的幂）
    N = 2^nextpow2(N_orig);
    if N > N_orig
        x = [x; zeros(N - N_orig, 1)];
    end

    %逆序化
    L = log2(N);%蝶形运算对应的层数
    rev_idx = bitrevorder(0:N-1) + 1;
    X = x(rev_idx);%逆序输入序列

    %开始运算，共L=log2(N)层
    for stage = 1:L
        half = 2^(stage - 1);%蝶形运算的间距
        group_size = 2 * half;%每组包含的点数=2^stage，即2*half

        for k = 0 : group_size : (N - 1)
            %遍历组内的每个蝶形
            for j = 1 : half
                %分为上下两个支路
                p = k + j;%上支路索引
                q = k + j + half;%下支路索引

                W = exp(-1i * 2 * pi * (j - 1) / group_size);
                temp = W * X(q);
                X_top = X(p) + temp;%上支路输出
                X_bot = X(p) - temp;%下支路输出

                X(p) = X_top;
                X(q) = X_bot;
            end
        end
    end

    %恢复
    if orig_rows == 1
        X = X(:).';%转化为行向量输出
    end
end

%逆序化函数
function rev = bitrevorder(idx)
    %输入：idx为索引[0, 1, 2, ..., N-1]
    N = length(idx);
    L = log2(N);
    rev = zeros(1, N);

    for i = 1:N
        n = idx(i);
        r = 0;
        for b = 0:(L-1)
            r = r * 2 + mod(n, 2);%左移并加入最低比特
            n = floor(n / 2);%移除最低比特
        end
        rev(i) = r;
    end
end
