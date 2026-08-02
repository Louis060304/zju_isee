%第3部分
x_known = [230.7692308,454.1538462,537.2307692,666.9230769,804,890.3076923,987.6923077,1225.846154,1846.153846,2653.846154];
y_known = [0.646774194,1.301612903,1.553225806,1.943548387,2.320967742,2.585483871,2.829032258,3.232258065,3.585483871,3.862903226];
z_known = [0.002802688,0.002866018,0.002891171,0.002914202,0.002886776,0.002904034,0.002864285,0.002636757,0.001942137,0.001455587];

x_fine = linspace(min(x_known), max(x_known), 1000);
y_interp = interp1(x_known, y_known, x_fine, 'linear');
z_interp = interp1(x_known, z_known, x_fine, 'linear');

figure;
yyaxis left
hold on;
plot( x_known,y_known, 'ro', 'MarkerSize', 2, 'LineWidth', 2);
plot(x_fine,y_interp , 'b-', 'LineWidth', 2);
xlabel('H(A/m)');
ylabel('B(T)');
grid on;

yyaxis right
hold on;
plot( x_known,z_known, 'ro', 'MarkerSize', 2, 'LineWidth', 2);
plot(x_fine,z_interp,  'b-', 'LineWidth', 2);
xlabel('x');
ylabel('μ(H/m)');
grid on;
