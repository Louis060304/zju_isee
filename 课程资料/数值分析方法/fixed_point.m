
g = @(x) log(3) + 2*log(x);

x0 = 3;       
max_iter = 100;  
tolerance = 1e-2; 

fprintf('List\t g(x)\n');

x_old = x0;

for iter = 1:max_iter
    x_new = g(x_old);
    
    fprintf('%d\t\t %.3f\n', iter, x_new);
    
    error = abs(x_new - x_old);
    if error < tolerance
        converged = true;
        break;
    end
    x_old = x_new;
end

fprintf('root = %.3f\n',x_new);