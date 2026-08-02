function digit_recognizer_gui()
    %基于FFT的数字语音识别GUI

    %参数
    smp_rate = 44100;
    template_path = './data/data_fft.mat';
    rec = audiorecorder(smp_rate, 16, 1);

    has_templates = exist(template_path, 'file');
    is_recording = false;  % 录音状态标志

    %识别结果存储
    y_cached      = [];   % 原始录音
    digits_cached = [];   % 识别数字数组
    scores_cached = [];   % N×10 相关系数
    segs_cached   = [];   % N×2 段起止索引
    seg_idx       = 1;    % 当前查看的段索引

    %创建GUI窗口
    fig = figure('Name', '数字语音识别系统', ...
                 'NumberTitle', 'off', ...
                 'Position', [150, 100, 800, 600], ...
                 'Resize', 'off', ...
                 'MenuBar', 'none');

    uicontrol('Style', 'text', ...
              'String', '基于FFT的数字语音识别系统', ...
              'FontSize', 18, 'FontWeight', 'bold', ...
              'Position', [150, 550, 500, 40], ...
              'BackgroundColor', get(gcf, 'Color'));

    %绘图轴
    ax_time = axes('Parent', fig, 'Position', [0.08, 0.55, 0.40, 0.30]);
    title('原始录音时域波形'); xlabel('Time (s)'); ylabel('Amplitude'); grid on;

    ax_cut = axes('Parent', fig, 'Position', [0.55, 0.55, 0.40, 0.30]);
    title('截取语音段'); xlabel('Time (s)'); ylabel('Amplitude'); grid on;

    ax_fft = axes('Parent', fig, 'Position', [0.08, 0.12, 0.40, 0.30]);
    title('FFT幅度谱'); xlabel('Frequency (Hz)'); ylabel('|X(f)|'); grid on;

    ax_bar = axes('Parent', fig, 'Position', [0.55, 0.12, 0.40, 0.30]);
    title('模板匹配相关系数'); xlabel('数字'); ylabel('相关系数');
    xticks(0:9); grid on;

    %结果显示
    txt_result = uicontrol('Style', 'text', ...
                           'String', '就绪', ...
                           'FontSize', 12, 'FontWeight', 'bold', ...
                           'ForegroundColor', [0 0 0.5], ...
                           'Position', [210, 5, 300, 18], ...
                           'HorizontalAlignment', 'left', ...
                           'BackgroundColor', get(gcf, 'Color'));

    %导航按钮
    btn_prev = uicontrol('Style', 'pushbutton', ...
                         'String', '<', ...
                         'FontSize', 10, 'FontWeight', 'bold', ...
                         'Position', [10, 4, 35, 24], ...
                         'Callback', @(~,~) nav_segment(-1), ...
                         'Enable', 'off');

    txt_seg = uicontrol('Style', 'text', ...
                        'String', '-', ...
                        'FontSize', 10, ...
                        'Position', [48, 5, 50, 18], ...
                        'HorizontalAlignment', 'center', ...
                        'BackgroundColor', get(gcf, 'Color'));

    btn_next = uicontrol('Style', 'pushbutton', ...
                         'String', '>', ...
                         'FontSize', 10, 'FontWeight', 'bold', ...
                         'Position', [100, 4, 35, 24], ...
                         'Callback', @(~,~) nav_segment(+1), ...
                         'Enable', 'off');

    btn_all = uicontrol('Style', 'pushbutton', ...
                        'String', '总览', ...
                        'FontSize', 10, ...
                        'Position', [140, 4, 55, 24], ...
                        'Callback', @(~,~) show_overview(), ...
                        'Enable', 'off');

    %录音/训练按钮
    btn_record = uicontrol('Style', 'pushbutton', ...
              'String', '开始录音 (空格键)', ...
              'FontSize', 14, 'FontWeight', 'bold', ...
              'ForegroundColor', [0 0.4 0], ...
              'Position', [480, 10, 200, 42], ...
              'Callback', @toggle_recording);

    %键盘快捷键：空格键开始/停止录音
    set(fig, 'KeyPressFcn', @key_press_handler);

    uicontrol('Style', 'pushbutton', ...
              'String', '重新训练', ...
              'FontSize', 10, ...
              'Position', [680, 16, 100, 28], ...
              'Callback', @retrain_system);

    %状态栏
    txt_status = uicontrol('Style', 'text', ...
                           'String', sprintf('模板: %s | 采样率: %d Hz', ...
                           condstr(has_templates), smp_rate), ...
                           'FontSize', 9, ...
                           'Position', [520, 2, 270, 18], ...
                           'BackgroundColor', get(gcf, 'Color'), ...
                           'HorizontalAlignment', 'right');

    % ================================================================
    function key_press_handler(~, event)
        %空格键切换录音状态
        if strcmp(event.Key, 'space')
            toggle_recording();
        end
    end

    % ================================================================
    function toggle_recording(~, ~)
        if ~exist(template_path, 'file')
            set(txt_result, 'String', '错误：请先训练模板！');
            return;
        end

        if ~is_recording
            %---- 开始录音 ----
            is_recording = true;
            record(rec);  % 非阻塞录音

            set(btn_record, 'String', '停止录音 (空格键)', ...
                            'ForegroundColor', [0.8 0 0], ...
                            'FontWeight', 'bold');
            set(txt_result, 'String', '🔴 录音中，请朗读数字...');
            set(txt_status, 'String', '录音中...');
        else
            %---- 停止录音并识别 ----
            is_recording = false;
            stop(rec);
            y = getaudiodata(rec);

            set(btn_record, 'String', '开始录音 (空格键)', ...
                            'ForegroundColor', [0 0.4 0]);
            set(txt_status, 'String', '识别中...');
            drawnow;

            %识别（含能量阈值分段）
            [digits, all_scores, segments] = recognize_digits(y, smp_rate, template_path);

            if isempty(digits)
                set(txt_result, 'String', '未检测到语音，请重试');
                set(txt_status, 'String', '识别失败');
                return;
            end

            %缓存结果
            y_cached      = y;
            digits_cached = digits;
            scores_cached = all_scores;
            segs_cached   = segments;
            seg_idx       = 1;

            %显示时域总览
            show_overview();

            %显示第一段细节
            show_segment(1);

            %启用导航
            n = length(digits);
            if n > 1
                set(btn_prev, 'Enable', 'off');   % 第1段，不能前退
                set(btn_next, 'Enable', 'on');
                set(btn_all, 'Enable', 'on');
                set(txt_seg, 'String', sprintf('1/%d', n));
            else
                set(btn_prev, 'Enable', 'off');
                set(btn_next, 'Enable', 'off');
                set(btn_all, 'Enable', 'off');
                set(txt_seg, 'String', '1/1');
            end

            %结果显示
            if n == 1
                result_str = sprintf('识别结果: 数字 %d  (置信度: %.1f%%)', ...
                                     digits(1), max(all_scores(1,:))*100);
            else
                result_str = sprintf('识别结果: [%s]  (%d个数字)', ...
                                     join(string(digits), ', '), n);
            end
            set(txt_result, 'String', result_str);
            set(txt_status, 'String', ...
                sprintf('模板: 已加载 | 采样率: %d Hz | 识别完成', smp_rate));
        end
    end

    % ================================================================
    function nav_segment(delta)
        new_idx = seg_idx + delta;
        if new_idx < 1 || new_idx > length(digits_cached)
            return;
        end
        seg_idx = new_idx;
        show_segment(seg_idx);

        n = length(digits_cached);
        set(txt_seg, 'String', sprintf('%d/%d', seg_idx, n));
        set(btn_prev, 'Enable', cond_enable(seg_idx > 1));
        set(btn_next, 'Enable', cond_enable(seg_idx < n));
    end

    % ================================================================
    function show_segment(idx)
        %显示第idx段的截取波形、FFT谱、相关系数
        y_seg = y_cached(segs_cached(idx,1) : segs_cached(idx,2));
        [spec, f_shift, y_cut] = extract_feature(y_seg, smp_rate);
        sc = scores_cached(idx, :);
        d  = digits_cached(idx);

        %截取语音段
        axes(ax_cut); cla;
        t_cut = (0:length(y_cut)-1) / smp_rate;
        plot(t_cut, y_cut, 'r');
        xlabel('Time (s)'); ylabel('Amplitude');
        title(sprintf('语音段%d（识别为 %d）', idx, d)); grid on;

        %FFT幅度谱
        axes(ax_fft); cla;
        plot(f_shift, spec, 'b');
        xlabel('Frequency (Hz)'); ylabel('|X(f)|');
        title(sprintf('语音段%d FFT幅度谱（识别为 %d）', idx, d));
        xlim([0, smp_rate/8]); grid on;

        %相关系数柱状图
        axes(ax_bar); cla;
        bar(0:9, sc, 'FaceColor', [0.3 0.5 0.8]);
        hold on;
        bar(d, sc(d+1), 'FaceColor', [0.9 0.2 0.2]);
        hold off;
        xlabel('数字'); ylabel('相关系数');
        title(sprintf('语音段%d 模板匹配相关系数', idx));
        xticks(0:9); ylim([0, 1]); grid on;
    end

    % ================================================================
    function show_overview()
        %显示时域波形总览，标注所有语音段
        axes(ax_time); cla;
        t_full = (0:length(y_cached)-1) / smp_rate;
        plot(t_full, y_cached);
        hold on;
        yl = ylim;
        colors = lines(length(digits_cached));
        for k = 1:size(segs_cached, 1)
            x1 = segs_cached(k,1) / smp_rate;
            x2 = segs_cached(k,2) / smp_rate;
            fill([x1, x2, x2, x1], ...
                 [yl(1), yl(1), yl(2), yl(2)], ...
                 colors(k,:), 'FaceAlpha', 0.12, 'EdgeColor', 'none');
            text((x1+x2)/2, yl(2)*0.9, num2str(digits_cached(k)), ...
                 'FontSize', 16, 'FontWeight', 'bold', ...
                 'Color', colors(k,:), ...
                 'HorizontalAlignment', 'center');
        end
        hold off;
        xlabel('Time (s)'); ylabel('Amplitude');
        title(sprintf('原始录音时域波形（检测到 %d 个语音段）', length(digits_cached)));
        xlim([0, max(t_full)]); grid on;
    end

    % ================================================================
    function retrain_system(~, ~)
        set(txt_result, 'String', '正在训练...');
        set(txt_status, 'String', '训练中...');
        drawnow;

        try
            templates = batch_fft_numbers('./data/numbers/', template_path, false);
            has_templates = true;
            set(txt_result, 'String', '训练完成！就绪');
            set(txt_status, 'String', ...
                sprintf('模板: 已加载 | 样本数: %d', length(templates)));
        catch ME
            set(txt_result, 'String', '训练失败！请检查音频文件');
            set(txt_status, 'String', ME.message);
        end
    end

    function s = condstr(tf)
        if tf, s = '已加载'; else, s = '未训练'; end
    end

    function s = cond_enable(tf)
        if tf, s = 'on'; else, s = 'off'; end
    end
end
