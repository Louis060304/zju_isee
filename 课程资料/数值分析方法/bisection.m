f = @(x) x*cos(x) - 2*x^2 + 3*x - 1;
a = 1.2;
b = 1.3;
tol = 1e-5;
[root, midpoints] = bisection_method(f, a, b, tol);

function [root, midpoints] = bisection_method(f, a, b, tol);
    if f(a) * f(b) > 0
    end
    
    midpoints = [];
    iter = 0;
    
    fprintf('List\tMidpoint\n');
    while (b - a) / 2 > tol
        c = (a + b) / 2;
        midpoints = [midpoints; c];
        fc = f(c);
        
        fprintf('%d\t\t%.6f\n', iter, c);
        
        if fc == 0
            break;
        elseif f(a) * fc < 0
            b = c;
        else
            a = c;
        end
        
        iter = iter + 1;
    end
    
    root = (a + b) / 2;
    fprintf('Root: %.6f\n', root);
end