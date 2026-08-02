function [maxSubArray, startIndex, maxSum] = maxSumSubArray(arr, fraction)
    
    n = length(arr);                     
    windowSize = floor(n * fraction);%根据比例计算滑动窗口大小
    windowSize = max(windowSize, 1);
    if windowSize > n
        windowSize = n;
    end

    %计算第一个窗口的和
    currentSum = sum(arr(1:windowSize));
    maxSum = currentSum;
    startIndex = 1;

    %滑动窗口：减去离开元素，加入新元素
    for i = 2:(n - windowSize + 1)
        currentSum = currentSum - arr(i - 1) + arr(i + windowSize - 1);

        if currentSum > maxSum
            maxSum = currentSum;
            startIndex = i;
        end
    end

    %根据最佳起始索引提取子数组
    maxSubArray = arr(startIndex:(startIndex + windowSize - 1));
end