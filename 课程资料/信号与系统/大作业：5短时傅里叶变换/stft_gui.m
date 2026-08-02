function stft_gui()
%STFT音频分析 GUI — 短时傅里叶变换交互式界面

%主窗口
fig = figure('Name', 'STFT 音频分析 — 短时傅里叶变换', ...
             'NumberTitle', 'off', ...
             'Position', [50, 50, 1400, 880], ...
             'Color', [0.12 0.12 0.12], ...
             'MenuBar', 'none', ...
             'ToolBar', 'none', ...
             'KeyPressFcn', @keyPressFcn, ...
             'CloseRequestFcn', @closeGUI, ...
             'ResizeFcn', @resizeGUI, ...
             'DefaultTextFontName', 'Microsoft YaHei', ...
             'DefaultUicontrolFontName', 'Microsoft YaHei');

%共享数据
handles = struct();
handles.fig = fig;
handles.audio = [];%音频数据
handles.fs = [];%采样率
handles.T_total = 0;%总时长
handles.t = [];%时间轴
handles.N_total = 0;

%STFT数据
handles.STFT_dB = [];
handles.time_frames = [];%帧时间
handles.freq = [];%频率轴
handles.n_frames = 0;
handles.half_nfft = 0;
handles.STFT_binned = [];
handles.bin_centers = [];
handles.n_bins = 40;
handles.dB_max = 0;
handles.dB_min = -80;

%参数
handles.win_len = 2048;
handles.overlap_ratio = 0.875;
handles.nfft = 4096;
handles.win_type = 'hann';
handles.freq_max_display = 4000;
handles.audio_device = -1;   % -1=系统默认音频输出设备

% 播放状态
handles.player = [];
handles.timer = [];
handles.is_playing = false;
handles.is_paused = false;
handles.current_time = 0;
handles.play_start_time = 0;%tic对应的起始已播时间

%音频文件名
handles.filename = '';
guidata(fig, handles);

%界面构建
buildGUI();

    function buildGUI()
        %颜色方案
        bg_dark  = [0.12 0.12 0.12];
        bg_panel = [0.18 0.18 0.18];
        bg_btn   = [0.25 0.25 0.25];
        fg_text  = [0.9  0.9  0.9];
        green    = [0.2  0.7  0.3];
        red_btn  = [0.7  0.2  0.2];
        orange   = [0.9  0.6  0.1];
        blue_btn = [0.2  0.4  0.8];

        fig_pos = get(fig, 'Position');
        W = fig_pos(3);
        H = fig_pos(4);

        %顶部控制栏
        ctrl_h = 55;
        %控制栏背景
        uicontrol('Style', 'text', 'Units', 'pixels', ...
                  'Position', [0, H-ctrl_h, W, ctrl_h], ...
                  'BackgroundColor', bg_panel, 'Enable', 'inactive');

        btn_w = 90;
        btn_h = 35;
        btn_y = H - ctrl_h + 12;
        gap = 12;
        x0 = 15;

        %导入按钮
        uicontrol('Style', 'pushbutton', 'String', '📂 导入音频', ...
                  'Position', [x0, btn_y, btn_w+20, btn_h], ...
                  'BackgroundColor', blue_btn, 'ForegroundColor', 'w', ...
                  'FontSize', 11, 'FontWeight', 'bold', ...
                  'Tooltip', '选择 MP3/WAV/FLAC 等音频文件', ...
                  'Callback', @(~,~) importAudio());
        x0 = x0 + btn_w + 20 + gap;

        %播放按钮
        handles.btn_play = uicontrol('Style', 'pushbutton', 'String', '▶ 播放', ...
                  'Position', [x0, btn_y, btn_w, btn_h], ...
                  'BackgroundColor', green, 'ForegroundColor', 'w', ...
                  'FontSize', 11, 'FontWeight', 'bold', ...
                  'Tooltip', '播放音频 (空格键)', 'Enable', 'off', ...
                  'Callback', @(~,~) playAudio());
        x0 = x0 + btn_w + gap;

        %暂停按钮
        handles.btn_pause = uicontrol('Style', 'pushbutton', 'String', '⏸ 暂停', ...
                  'Position', [x0, btn_y, btn_w, btn_h], ...
                  'BackgroundColor', orange, 'ForegroundColor', 'w', ...
                  'FontSize', 11, 'FontWeight', 'bold', ...
                  'Tooltip', '暂停/继续播放 (空格键)', 'Enable', 'off', ...
                  'Callback', @(~,~) pauseAudio());
        x0 = x0 + btn_w + gap;

        %停止按钮
        handles.btn_stop = uicontrol('Style', 'pushbutton', 'String', '⏹ 停止', ...
                  'Position', [x0, btn_y, btn_w, btn_h], ...
                  'BackgroundColor', red_btn, 'ForegroundColor', 'w', ...
                  'FontSize', 11, 'FontWeight', 'bold', ...
                  'Tooltip', '停止播放 (Esc键)', 'Enable', 'off', ...
                  'Callback', @(~,~) stopAudio());
        x0 = x0 + btn_w + gap;

        %分隔线
        x0 = x0 + gap;
        uicontrol('Style', 'text', 'Units', 'pixels', ...
                  'Position', [x0, btn_y-3, 2, btn_h+6], ...
                  'BackgroundColor', [0.4 0.4 0.4]);
        x0 = x0 + 12 + gap;

        %窗类型标签+下拉框
        uicontrol('Style', 'text', 'String', '窗:', ...
                  'Position', [x0, btn_y+10, 30, 18], ...
                  'BackgroundColor', bg_panel, 'ForegroundColor', fg_text, ...
                  'FontSize', 10);
        handles.popup_win = uicontrol('Style', 'popupmenu', ...
                  'String', {'Hann', 'Hamming', 'Blackman'}, ...
                  'Value', 1, ...
                  'Position', [x0+30, btn_y+2, 110, btn_h-4], ...
                  'BackgroundColor', bg_btn, 'ForegroundColor', 'w', ...
                  'FontSize', 10, 'Tooltip', '选择窗函数类型', ...
                  'Callback', @(~,~) onParamChange());
        x0 = x0 + 30 + 110 + gap;

        %窗长标签+编辑框
        uicontrol('Style', 'text', 'String', '窗长:', ...
                  'Position', [x0, btn_y+10, 35, 18], ...
                  'BackgroundColor', bg_panel, 'ForegroundColor', fg_text, ...
                  'FontSize', 10);
        handles.edit_winlen = uicontrol('Style', 'edit', ...
                  'String', '2048', ...
                  'Position', [x0+35, btn_y+2, 65, btn_h-4], ...
                  'BackgroundColor', bg_btn, 'ForegroundColor', 'w', ...
                  'FontSize', 10, 'Tooltip', '窗长度 (样本点数, 2的幂次更优)', ...
                  'Callback', @(~,~) onParamChange());
        x0 = x0 + 35 + 65 + gap;

        %重叠率标签+编辑框
        uicontrol('Style', 'text', 'String', '重叠:', ...
                  'Position', [x0, btn_y+10, 35, 18], ...
                  'BackgroundColor', bg_panel, 'ForegroundColor', fg_text, ...
                  'FontSize', 10);
        handles.edit_overlap = uicontrol('Style', 'edit', ...
                  'String', '0.875', ...
                  'Position', [x0+35, btn_y+2, 55, btn_h-4], ...
                  'BackgroundColor', bg_btn, 'ForegroundColor', 'w', ...
                  'FontSize', 10, 'Tooltip', '重叠率 (0~1), 如 0.875 = 87.5%', ...
                  'Callback', @(~,~) onParamChange());
        x0 = x0 + 35 + 55 + gap;

        %频率上限滑块标签
        uicontrol('Style', 'text', 'String', '频率上限:', ...
                  'Position', [x0, btn_y+10, 55, 18], ...
                  'BackgroundColor', bg_panel, 'ForegroundColor', fg_text, ...
                  'FontSize', 10);
        %滑块
        handles.slider_freq = uicontrol('Style', 'slider', ...
                  'Min', 1000, 'Max', 20000, 'Value', 4000, ...
                  'Position', [x0+55, btn_y+4, 100, btn_h-8], ...
                  'BackgroundColor', bg_btn, 'ForegroundColor', 'w', ...
                  'Tooltip', '拖动调整频率显示范围', ...
                  'Callback', @(~,~) onFreqSliderChange());
        %频率值显示
        handles.txt_freq = uicontrol('Style', 'text', ...
                  'String', '4000 Hz', ...
                  'Position', [x0+55+100+4, btn_y+5, 60, btn_h-10], ...
                  'BackgroundColor', bg_panel, 'ForegroundColor', [0.3 1 0.3], ...
                  'FontSize', 10, 'FontWeight', 'bold');
        x0 = x0 + 55 + 100 + 60 + gap;

        %音频输出设备选择
        uicontrol('Style', 'text', 'String', '输出:', ...
                  'Position', [x0, btn_y+10, 35, 18], ...
                  'BackgroundColor', bg_panel, 'ForegroundColor', fg_text, ...
                  'FontSize', 10);
        dev_info = audiodevinfo;
        n_dev = length(dev_info.output);
        dev_names = cell(1, max(n_dev,1));
        handles.device_ids = zeros(1, max(n_dev,1));
        if n_dev > 0
            for d = 1:n_dev
                dev_names{d} = dev_info.output(d).Name;
                handles.device_ids(d) = dev_info.output(d).ID;
            end
            handles.audio_device = handles.device_ids(1);
        else
            dev_names{1} = '默认设备';
            handles.device_ids(1) = -1;
            handles.audio_device = -1;
        end
        handles.popup_device = uicontrol('Style', 'popupmenu', ...
                  'String', dev_names, 'Value', 1, ...
                  'Position', [x0+35, btn_y+2, 100, btn_h-4], ...
                  'BackgroundColor', bg_btn, 'ForegroundColor', 'w', ...
                  'FontSize', 8, 'Tooltip', '选择音频输出设备 (耳机无声音时切换)', ...
                  'Callback', @(~,~) onDeviceChange());
        x0 = x0 + 35 + 100 + gap;

        %重置按钮
        handles.btn_reset = uicontrol('Style', 'pushbutton', 'String', '↺ 重置', ...
                  'Position', [x0, btn_y, 80, btn_h], ...
                  'BackgroundColor', bg_btn, 'ForegroundColor', 'w', ...
                  'FontSize', 11, 'Tooltip', '清除数据恢复初始状态', ...
                  'Enable', 'off', ...
                  'Callback', @(~,~) resetAll());

        %布局
        MARGIN_LEFT = 70;%左侧留白
        MARGIN_RIGHT = 25;% 右侧留白
        MARGIN_MID = 55;%左右列间距
        MARGIN_TOP = 30;%控制栏下方间距
        MARGIN_BOT = 35;%底部留白
        GAP_ROWS = 55;%上下行间距

        plot_area_w = W - MARGIN_LEFT - MARGIN_MID - MARGIN_RIGHT;
        col_w   = plot_area_w / 2;
        plot_area_h = H - ctrl_h - MARGIN_TOP - MARGIN_BOT;
        row_h   = (plot_area_h - GAP_ROWS) / 2;

        left_x  = MARGIN_LEFT;
        right_x = MARGIN_LEFT + col_w + MARGIN_MID;
        y_row1  = H - ctrl_h - MARGIN_TOP - row_h;
        y_row2  = MARGIN_BOT;

        %时域波形
        handles.ax_wave = axes('Units', 'pixels', ...
                               'Position', [left_x, y_row1, col_w, row_h], ...
                               'Color', [0.08 0.08 0.08]);
        handles.h_wave = plot(handles.ax_wave, 0, 0, 'c', 'LineWidth', 0.8);
        hold(handles.ax_wave, 'on');
        handles.h_cursor = xline(handles.ax_wave, 0, 'r', 'LineWidth', 2);
        y_lim_temp = [-1, 1];
        handles.h_patch = patch(handles.ax_wave, [0 0 0 0], ...
                                [y_lim_temp(1) y_lim_temp(2) y_lim_temp(2) y_lim_temp(1)], ...
                                'y', 'FaceAlpha', 0.10, 'EdgeColor', 'none');
        hold(handles.ax_wave, 'off');
        xlabel(handles.ax_wave, '时间 (s)', 'Color', 'w', 'FontSize', 9, 'FontName', 'Microsoft YaHei');
        ylabel(handles.ax_wave, '幅度', 'Color', 'w', 'FontSize', 9, 'FontName', 'Microsoft YaHei');
        title(handles.ax_wave, '时域波形', 'Color', 'w', 'FontSize', 11, 'FontName', 'Microsoft YaHei');
        handles.ax_wave.XColor = 'w'; handles.ax_wave.YColor = 'w';
        handles.ax_wave.ButtonDownFcn = @(~,~) waveClick();
        grid(handles.ax_wave, 'on');

        %STFT时频图
        handles.ax_stft = axes('Units', 'pixels', ...
                               'Position', [right_x, y_row1, col_w, row_h], ...
                               'Color', [0.08 0.08 0.08]);
        handles.h_img = imagesc(handles.ax_stft, [0 1], [0 4000], zeros(10, 10));
        axis(handles.ax_stft, 'xy');
        hold(handles.ax_stft, 'on');
        handles.h_tline = xline(handles.ax_stft, 0, 'y', 'LineWidth', 2);
        hold(handles.ax_stft, 'off');
        colormap(handles.ax_stft, 'jet');
        handles.ax_stft.CLim = [-80, 0];
        xlabel(handles.ax_stft, '时间 (s)', 'Color', 'w', 'FontSize', 9, 'FontName', 'Microsoft YaHei');
        ylabel(handles.ax_stft, '频率 (Hz)', 'Color', 'w', 'FontSize', 9, 'FontName', 'Microsoft YaHei');
        title(handles.ax_stft, 'STFT 时频图', 'Color', 'w', 'FontSize', 11, 'FontName', 'Microsoft YaHei');
        handles.ax_stft.XColor = 'w'; handles.ax_stft.YColor = 'w';
        handles.ax_stft.ButtonDownFcn = @(~,~) stftClick();

        %当前帧频谱
        handles.ax_spec = axes('Units', 'pixels', ...
                               'Position', [left_x, y_row2, col_w, row_h], ...
                               'Color', [0.08 0.08 0.08]);
        handles.h_spec = bar(handles.ax_spec, 1:40, zeros(1,40), 'BarWidth', 0.85, ...
                              'EdgeColor', 'none', 'FaceColor', [0.2 0.9 0.2]);
        xlabel(handles.ax_spec, '频率 (Hz)', 'Color', 'w', 'FontSize', 9, 'FontName', 'Microsoft YaHei');
        ylabel(handles.ax_spec, '幅度 (dB)', 'Color', 'w', 'FontSize', 9, 'FontName', 'Microsoft YaHei');
        title(handles.ax_spec, '当前帧瞬时频谱 (100Hz/bin)', 'Color', 'w', 'FontSize', 11, 'FontName', 'Microsoft YaHei');
        handles.ax_spec.XColor = 'w'; handles.ax_spec.YColor = 'w';
        handles.ax_spec.XLim = [0, 4000];
        grid(handles.ax_spec, 'on');

        %信息面板
        handles.ax_info = axes('Units', 'pixels', ...
                               'Position', [right_x, y_row2, col_w, row_h], ...
                               'Color', [0.06 0.06 0.06]);
        axis(handles.ax_info, 'off');
        handles.h_info = text(handles.ax_info, 0.5, 0.5, ...
                              {'请导入音频文件开始分析', '', ...
                               '支持格式: MP3, WAV, FLAC, OGG, M4A', ''}, ...
                              'Color', [0.5 0.5 0.5], 'FontSize', 13, ...
                              'HorizontalAlignment', 'center', ...
                              'VerticalAlignment', 'middle', ...
                              'FontName', 'Microsoft YaHei');

        guidata(fig, handles);
    end

%导入音频
    function importAudio()
        setStatus('正在导入音频...', [1 1 0]);

        [filename, filepath] = uigetfile(...
            {'*.mp3;*.wav;*.flac;*.ogg;*.m4a;*.wma;*.aac', ...
             '音频文件 (*.mp3,*.wav,*.flac,*.ogg,*.m4a)'; ...
             '*.*', '所有文件'}, ...
            '选择音频文件');

        if filename == 0
            setStatus('就绪 — 请导入音频文件', [0.5 0.5 0.5]);
            return;
        end

        file_full = fullfile(filepath, filename);
        try
            [audio, fs] = audioread(file_full);
        catch ME
            setStatus(['导入失败: ' ME.message], [1 0.3 0.3]);
            errordlg(['无法读取音频文件: ' ME.message], '导入错误');
            return;
        end

        %立体声 → 单声道
        if size(audio, 2) == 2
            audio = mean(audio, 2);
        end

        audio = audio / max(abs(audio)) * 0.95;

        %存储数据
        handles.audio = audio;
        handles.fs = fs;
        handles.N_total = length(audio);
        handles.T_total = handles.N_total / fs;
        handles.t = (0:handles.N_total-1)' / fs;
        handles.filename = filename;

        set(handles.slider_freq, 'Max', fs/2);

        %时域波形
        handles.h_wave.XData = handles.t;
        handles.h_wave.YData = handles.audio;
        handles.ax_wave.XLim = [0, handles.T_total];
        y_lim = max(abs(handles.audio)) * 1.1;
        handles.ax_wave.YLim = [-y_lim, y_lim];
        handles.h_patch.YData = [-y_lim, y_lim, y_lim, -y_lim];

        computeSTFT();
        set(handles.btn_play, 'Enable', 'on');
        set(handles.btn_pause, 'Enable', 'on');
        set(handles.btn_stop, 'Enable', 'on');
        set(handles.btn_reset, 'Enable', 'on');

        %更新信息面板
        updateInfoPanel();

        dur_str = sprintf('%d:%05.2f', floor(handles.T_total/60), mod(handles.T_total, 60));
        setStatus(sprintf('已导入: %s | 时长 %s | fs=%d Hz | 采样点=%d', ...
                 filename, dur_str, fs, handles.N_total), [0.3 1 0.3]);
    end

%STFT计算
    function computeSTFT()
        if isempty(handles.audio); return; end

        setStatus('正在计算 STFT ...', [1 1 0]);
        drawnow;

        %读取参数
        handles.win_len = max(16, str2double(get(handles.edit_winlen, 'String')));
        if isnan(handles.win_len); handles.win_len = 2048; end
        handles.win_len = round(handles.win_len);
        set(handles.edit_winlen, 'String', num2str(handles.win_len));

        handles.overlap_ratio = str2double(get(handles.edit_overlap, 'String'));
        if isnan(handles.overlap_ratio) || handles.overlap_ratio <= 0 || handles.overlap_ratio >= 1
            handles.overlap_ratio = 0.875;
        end
        set(handles.edit_overlap, 'String', num2str(handles.overlap_ratio));

        handles.nfft = 2^nextpow2(handles.win_len * 2);

        overlap = round(handles.win_len * handles.overlap_ratio);
        step = handles.win_len - overlap;

        %读窗类型
        win_types = get(handles.popup_win, 'String');
        win_idx   = get(handles.popup_win, 'Value');
        win_name  = strtrim(win_types{win_idx});
        switch win_name(1:3)
            case 'Han'; window = hann(handles.win_len, 'periodic');    handles.win_type = 'hann';
            case 'Ham'; window = hamming(handles.win_len, 'periodic');  handles.win_type = 'hamming';
            case 'Bla'; window = blackman(handles.win_len, 'periodic'); handles.win_type = 'blackman';
            otherwise;  window = hann(handles.win_len, 'periodic');    handles.win_type = 'hann';
        end

        n_frames = floor((handles.N_total - handles.win_len) / step) + 1;
        half_nfft = handles.nfft / 2 + 1;
        handles.half_nfft = half_nfft;
        handles.n_frames = n_frames;
        handles.freq = (0:half_nfft-1)' * handles.fs / handles.nfft;

        STFT_dB = zeros(half_nfft, n_frames);
        time_frames = zeros(1, n_frames);

        for k = 1:n_frames
            idx_start = (k-1) * step + 1;
            idx_end   = idx_start + handles.win_len - 1;
            segment = handles.audio(idx_start:idx_end) .* window;
            X = fft(segment, handles.nfft);
            STFT_dB(:, k) = 20 * log10(abs(X(1:half_nfft)) + eps);
            time_frames(k) = handles.t(round((idx_start + idx_end) / 2));
        end

        handles.STFT_dB = STFT_dB;
        handles.time_frames = time_frames;
        handles.dB_max = max(STFT_dB(:));
        handles.dB_min = handles.dB_max - 80;

        %裁剪动态范围
        STFT_display = STFT_dB;
        STFT_display(STFT_display < handles.dB_min) = handles.dB_min;

        %更新时频图
        handles.h_img.XData = time_frames;
        handles.h_img.YData = handles.freq;
        handles.h_img.CData = STFT_display;
        handles.ax_stft.XLim = [0, handles.T_total];
        handles.ax_stft.CLim = [handles.dB_min, handles.dB_max];

        %频谱柱状图
        bin_width = 100;
        bin_edges = 0:bin_width:4000;
        n_bins = length(bin_edges) - 1;
        bin_centers = (bin_edges(1:end-1) + bin_edges(2:end)) / 2;

        STFT_binned = zeros(n_bins, n_frames);
        for b = 1:n_bins
            idx = (handles.freq >= bin_edges(b)) & (handles.freq < bin_edges(b+1));
            if any(idx)
                STFT_binned(b, :) = mean(STFT_dB(idx, :), 1);
            else
                STFT_binned(b, :) = handles.dB_min;
            end
        end
        STFT_binned(STFT_binned < 0) = 0;%仅显示0dB及以上
        handles.STFT_binned = STFT_binned;
        handles.bin_centers = bin_centers;
        handles.n_bins = n_bins;

        %频谱图轴
        handles.ax_spec.XLim = [0, 4000];
        handles.ax_spec.YLim = [0, handles.dB_max];
        set(handles.h_spec, 'XData', bin_centers, 'YData', zeros(1, n_bins));

        guidata(fig, handles);
        setStatus(sprintf('STFT 计算完成 | 窗=%s %d点 %.0fms | 帧=%d | 重叠=%.0f%%', ...
                 handles.win_type, handles.win_len, handles.win_len/handles.fs*1000, ...
                 n_frames, handles.overlap_ratio*100), [0.3 1 0.3]);
    end

%参数变更回调
    function onParamChange()
        if isempty(handles.audio); return; end
        stopAudio();
        computeSTFT();
        updateInfoPanel();
    end

    function onFreqSliderChange()
        handles.freq_max_display = round(get(handles.slider_freq, 'Value'));
        set(handles.txt_freq, 'String', sprintf('%d Hz', handles.freq_max_display));
        ylim(handles.ax_stft, [0, handles.freq_max_display]);
        guidata(fig, handles);
    end

    function onDeviceChange()
        idx = get(handles.popup_device, 'Value');
        handles.audio_device = handles.device_ids(idx);
        guidata(fig, handles);
    end

%播放控制
    function playAudio()
        if isempty(handles.audio); return; end

        if handles.is_paused
            %从暂停位置恢复播放
            resume(handles.player);
            startTimer();
            handles.is_paused = false;
            handles.is_playing = true;
            set(handles.btn_play, 'String', '▶ 播放中');
            set(handles.btn_pause, 'String', '⏸ 暂停');
            setStatus('继续播放...', [0.3 1 0.3]);
        else
            %从当前位置开始播放
            start_idx = max(1, round(handles.current_time * handles.fs));
            audio_to_play = handles.audio(start_idx:end);

            if isempty(audio_to_play) || length(audio_to_play) < handles.fs * 0.1
                %已到尾端，从头开始
                start_idx = 1;
                handles.current_time = 0;
                audio_to_play = handles.audio;
            end

            handles.play_start_time = handles.current_time;
            handles.player = audioplayer(audio_to_play, handles.fs, 16, ...
                                         handles.audio_device);
            play(handles.player);
            handles.is_playing = true;
            handles.is_paused = false;
            set(handles.btn_play, 'String', '▶ 播放中');
            set(handles.btn_pause, 'String', '⏸ 暂停');
            setStatus('正在播放...', [0.3 1 0.3]);
            startTimer();
        end

        guidata(fig, handles);
    end

    function pauseAudio()
        if ~handles.is_playing; return; end

        if handles.is_paused
            %恢复播放
            playAudio();
        else
            %暂停
            pause(handles.player);
            handles.is_paused = true;
            handles.is_playing = true;
            set(handles.btn_play, 'String', '▶ 继续');
            set(handles.btn_pause, 'String', '⏸ 已暂停');
            setStatus('已暂停', [1 0.7 0]);
            drawnow;
        end

        guidata(fig, handles);
    end

    function stopAudio()
        if ~isempty(handles.player) && isplaying(handles.player)
            stop(handles.player);
        end
        stopTimer();

        handles.is_playing = false;
        handles.is_paused = false;
        handles.current_time = 0;
        handles.play_start_time = 0;

        set(handles.btn_play, 'String', '▶ 播放');
        set(handles.btn_pause, 'String', '⏸ 暂停');
        setStatus('已停止', [1 0.5 0.3]);

        %重置游标
        handles.h_cursor.Value = 0;
        handles.h_tline.Value = 0;
        handles.h_patch.XData = [0 0 0 0];
        set(handles.h_spec, 'YData', zeros(1, handles.n_bins));
        updateProgressBar(0);
        updateInfoPanel();

        guidata(fig, handles);
    end

%Timer管理
    function startTimer()
        stopTimer();%停止已有timer
        handles.timer = timer('TimerFcn', @(~,~) onTimerTick(), ...
                              'Period', 0.04, ...         % 25 fps
                              'ExecutionMode', 'fixedRate', ...
                              'BusyMode', 'drop');
        guidata(fig, handles);
        start(handles.timer);
    end

    function stopTimer()
        if ~isempty(handles.timer) && isvalid(handles.timer)
            stop(handles.timer);
            delete(handles.timer);
            handles.timer = [];
            guidata(fig, handles);
        end
    end

    function onTimerTick()
        if isempty(handles.player) || ~isvalid(handles.player)
            stopTimer();
            return;
        end

        if ~isplaying(handles.player) && ~handles.is_paused
            %播放自然结束
            stopAudio();
            setStatus('播放结束', [0.5 0.5 0.5]);
            return;
        end

        if handles.is_paused
            %暂停
            drawnow limitrate;
            return;
        end

        %当前样本位置
        try
            curr_sample = get(handles.player, 'CurrentSample');
        catch
            return;
        end

        elapsed_in_chunk = (curr_sample - 1) / handles.fs;
        handles.current_time = handles.play_start_time + elapsed_in_chunk;
        handles.current_time = min(handles.current_time, handles.T_total);

        %当前帧
        step = handles.win_len - round(handles.win_len * handles.overlap_ratio);
        current_frame = round(handles.current_time / (step / handles.fs));
        current_frame = min(max(current_frame, 1), handles.n_frames);

        %更新游标
        set(handles.h_cursor, 'Value', handles.current_time);
        set(handles.h_tline, 'Value', handles.current_time);

        %更新已播放区域
        y_lim = handles.ax_wave.YLim;
        set(handles.h_patch, 'XData', [0, handles.current_time, handles.current_time, 0], ...
                             'YData', [y_lim(1), y_lim(1), y_lim(2), y_lim(2)]);

        %更新当前频谱
        if current_frame <= size(handles.STFT_dB, 2)
            set(handles.h_spec, 'YData', handles.STFT_binned(:, current_frame));
        end

        %更新进度条
        progress = handles.current_time / handles.T_total * 100;
        updateProgressBar(progress);

        %更新信息面板
        updatePlayingInfo();

        guidata(fig, handles);
        drawnow limitrate;
    end

%跳转
    function seekToTime(new_time)
        new_time = max(0, min(handles.T_total, new_time));
        was_playing = handles.is_playing && ~handles.is_paused;

        %停止当前播放
        if ~isempty(handles.player) && isplaying(handles.player)
            stop(handles.player);
        end
        stopTimer();

        handles.current_time = new_time;
        handles.is_playing = false;
        handles.is_paused = false;
        handles.play_start_time = new_time;

        %更新显示
        set(handles.h_cursor, 'Value', new_time);
        set(handles.h_tline, 'Value', new_time);
        updateProgressBar(new_time / handles.T_total * 100);

        step = handles.win_len - round(handles.win_len * handles.overlap_ratio);
        current_frame = round(new_time / (step / handles.fs));
        current_frame = min(max(current_frame, 1), handles.n_frames);
        if current_frame <= size(handles.STFT_binned, 2)
            set(handles.h_spec, 'YData', handles.STFT_binned(:, current_frame));
        end

        guidata(fig, handles);
        updatePlayingInfo();

        if was_playing
            playAudio();
        end
    end

    function waveClick()
        if isempty(handles.audio); return; end
        cp = handles.ax_wave.CurrentPoint;
        seekToTime(cp(1, 1));
    end

    function stftClick()
        if isempty(handles.audio); return; end
        cp = handles.ax_stft.CurrentPoint;
        seekToTime(cp(1, 1));
    end

    function updateInfoPanel()
        if isempty(handles.audio)
            set(handles.h_info, 'String', {'请导入音频文件开始分析', '', ...
                '支持格式: MP3, WAV, FLAC, OGG, M4A', '', ...
                '快捷键: 空格=播放/暂停  Esc=停止'}, 'Color', [0.5 0.5 0.5]);
            return;
        end

        dur_str = sprintf('%d:%05.2f', floor(handles.T_total/60), mod(handles.T_total, 60));
        info = {...
            sprintf('📁 文件: %s', handles.filename), ...
            sprintf('⏱  时长: %s  |  fs = %d Hz', dur_str, handles.fs), ...
            sprintf('📐 窗: %s  %d点 (%.0fms)', ...
                    handles.win_type, handles.win_len, ...
                    handles.win_len/handles.fs*1000), ...
            sprintf('📊 帧: %d  |  重叠: %.0f%%  |  NFFT: %d', ...
                    handles.n_frames, handles.overlap_ratio*100, handles.nfft), ...
            sprintf('📏 Δf = %.1f Hz  |  Δt = %.1f ms', ...
                    handles.fs/handles.nfft, ...
                    handles.win_len/handles.fs*1000), ...
            '', ...
            '🖱 点击波形图或时频图跳转播放位置'};
        set(handles.h_info, 'String', info, 'Color', [0.8 0.8 0.8]);
    end

    function updatePlayingInfo()
        if isempty(handles.audio); return; end

        dur_str = sprintf('%d:%05.2f', floor(handles.T_total/60), mod(handles.T_total, 60));
        cur_str = sprintf('%d:%05.2f', floor(handles.current_time/60), mod(handles.current_time, 60));

        step = handles.win_len - round(handles.win_len * handles.overlap_ratio);
        cf = round(handles.current_time / (step / handles.fs));
        cf = min(max(cf, 1), handles.n_frames);

        state = '⏹ 停止';
        if handles.is_playing && ~handles.is_paused; state = '▶ 播放中';
        elseif handles.is_paused; state = '⏸ 已暂停'; end

        info = {...
            sprintf('📁 %s', handles.filename), ...
            sprintf('⏱  %s / %s  [%s]', cur_str, dur_str, state), ...
            sprintf('📐 窗: %s %d点  |  重叠: %.0f%%', ...
                    handles.win_type, handles.win_len, handles.overlap_ratio*100), ...
            sprintf('📊 帧: %d / %d', cf, handles.n_frames), ...
            '', ...
            '🖱 点击波形/时频图跳转播放', ...
            '⌨ 空格=播放/暂停  Esc=停止'};
        set(handles.h_info, 'String', info, 'Color', [0.8 0.8 0.8]);
    end

%键盘快捷键
    function keyPressFcn(~, event)
        switch event.Key
            case 'space'
                if handles.is_playing && ~handles.is_paused
                    pauseAudio();
                else
                    playAudio();
                end
            case 'escape'
                stopAudio();
            case 'leftarrow'
                seekToTime(handles.current_time - 2);
            case 'rightarrow'
                seekToTime(handles.current_time + 2);
        end
    end

%重置
    function resetAll()
        stopAudio();

        handles.audio = [];
        handles.fs = [];
        handles.T_total = 0;
        handles.t = [];
        handles.N_total = 0;
        handles.STFT_dB = [];
        handles.STFT_binned = [];
        handles.time_frames = [];
        handles.freq = [];
        handles.n_frames = 0;
        handles.half_nfft = 0;
        handles.dB_max = 0;
        handles.dB_min = -80;
        handles.current_time = 0;
        handles.filename = '';

        %清空图形
        handles.h_wave.XData = 0; handles.h_wave.YData = 0;
        handles.ax_wave.XLim = [0, 1]; handles.ax_wave.YLim = [-1, 1];
        handles.h_cursor.Value = 0;
        handles.h_tline.Value = 0;
        handles.h_patch.XData = [0 0 0 0];
        handles.h_img.CData = zeros(10, 10);
        handles.h_img.XData = [0, 1]; handles.h_img.YData = [0, 4000];
        handles.ax_stft.XLim = [0, 1]; handles.ax_stft.CLim = [-80, 0];
        set(handles.h_spec, 'XData', 1:40, 'YData', zeros(1,40));
        handles.ax_spec.XLim = [0, 4000]; handles.ax_spec.YLim = [0, 0];

        %禁用按钮
        set(handles.btn_play, 'Enable', 'off', 'String', '▶ 播放');
        set(handles.btn_pause, 'Enable', 'off', 'String', '⏸ 暂停');
        set(handles.btn_stop, 'Enable', 'off');
        set(handles.btn_reset, 'Enable', 'off');

        updateProgressBar(0);
        updateInfoPanel();
        setStatus('已重置 — 请导入音频文件', [0.5 0.5 0.5]);

        guidata(fig, handles);
    end

%关闭
    function closeGUI(~, ~)
        stopTimer();
        if ~isempty(handles.player) && isplaying(handles.player)
            stop(handles.player);
        end
        delete(fig);
    end

    function setStatus(~, ~)
    end

    function updateProgressBar(~)
    end

    function resizeGUI(~, ~)
    end

end
