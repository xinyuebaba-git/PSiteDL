"""
进度图表 GUI 组件 - Phase 3 实现

包含:
- ProgressChartWidget: 实时进度图表组件
"""

import pyqtgraph as pg
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QGridLayout, QHBoxLayout
from PyQt5.QtCore import QTimer, Qt
import numpy as np

from .progress import SpeedHistory, ETAPredictor, DownloadProgress


class ProgressChartWidget(QWidget):
    """
    实时进度图表组件
    
    功能:
    - 实时速度曲线图（PyQtGraph）
    - 统计信息显示（当前/平均/峰值速度）
    - ETA 预测显示
    - 1Hz 更新频率
    """
    
    def __init__(self, config: dict = None):
        super().__init__()
        
        self.config = config or {}
        self.speed_history = SpeedHistory(
            max_seconds=self.config.get('speed_history_duration', 60)
        )
        self.eta_predictor = ETAPredictor(
            alpha=self.config.get('eta_smoothing_factor', 0.3)
        )
        self.peak_speed = 0.0
        
        self._init_ui()
        self._init_timer()
    
    def _init_ui(self):
        """初始化 UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)
        
        # 主布局：左侧参数区 (70%)，右侧日志区 (30%)
        content_layout = QHBoxLayout()
        content_layout.setStretch(0, 7)  # 参数区 70%
        content_layout.setStretch(1, 3)  # 日志区 30%
        
        # 左侧：参数区（图表和统计信息）
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 5, 0)
        
        # 统计信息面板
        self._init_stats_panel(left_layout)
        
        # 速度图表
        self._init_speed_chart(left_layout)
        
        # 带宽使用图表（可选）
        self._init_bandwidth_chart(left_layout)
        
        # 右侧：日志区
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(5, 0, 0, 0)
        
        self.log_display = QLabel("等待下载...")
        self.log_display.setWordWrap(True)
        self.log_display.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.log_display.setStyleSheet("""
            QLabel {
                font-size: 12px;
                padding: 10px;
                background-color: #1e1e1e;
                color: #00ff00;
                border-radius: 5px;
                font-family: 'Monaco', 'Courier New', monospace;
            }
        """)
        right_layout.addWidget(self.log_display)
        
        # 添加到主布局
        content_layout.addWidget(left_panel)
        content_layout.addWidget(right_panel)
        main_layout.addLayout(content_layout)
        
        self.setLayout(main_layout)
    
    def _init_stats_panel(self, layout):
        """初始化统计信息面板"""
        self.stats_label = QLabel()
        self.stats_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                padding: 10px;
                background-color: #2b2b2b;
                color: #ffffff;
                border-radius: 5px;
                font-family: 'Monaco', 'Courier New', monospace;
            }
        """)
        self.stats_label.setText("""
        当前速度：--.-- Mbps
        平均速度：--.-- Mbps
        峰值速度：--.-- Mbps
        剩余时间：--:--
        """)
        layout.addWidget(self.stats_label)
    
    def _init_speed_chart(self, layout):
        """初始化速度图表"""
        # 创建图表
        self.speed_plot = pg.PlotWidget()
        self.speed_plot.setBackground('w')
        self.speed_plot.setTitle("下载速度", color='#000000', size='14pt')
        self.speed_plot.setLabel('left', '速度', units='Mbps', color='#000000')
        self.speed_plot.setLabel('bottom', '时间', units='秒', color='#000000')
        self.speed_plot.showGrid(x=True, y=True, alpha=0.3)
        
        # 设置 Y 轴范围
        self.speed_plot.setYRange(0, 100)  # 0-100 Mbps
        
        # 创建曲线
        self.speed_curve = self.speed_plot.plot(
            pen=pg.mkPen(color='#1f77b4', width=2),
            symbol=None,
            name='速度'
        )
        
        layout.addWidget(self.speed_plot)
    
    def _init_bandwidth_chart(self, layout):
        """初始化带宽使用图表"""
        self.bandwidth_plot = pg.PlotWidget()
        self.bandwidth_plot.setBackground('w')
        self.bandwidth_plot.setTitle("带宽使用率", color='#000000', size='12pt')
        self.bandwidth_plot.setLabel('left', '使用率', units='%', color='#000000')
        self.bandwidth_plot.showGrid(x=True, y=True, alpha=0.3)
        
        # 设置 Y 轴范围 0-100%
        self.bandwidth_plot.setYRange(0, 100)
        
        # 创建曲线
        self.bandwidth_curve = self.bandwidth_plot.plot(
            pen=pg.mkPen(color='#2ca02c', width=2),
            symbol=None,
            name='带宽使用'
        )
        
        layout.addWidget(self.bandwidth_plot)
    
    def _init_timer(self):
        """初始化更新定时器"""
        self.timer = QTimer()
        interval = self.config.get('chart_update_interval', 1000)  # 默认 1Hz
        self.timer.timeout.connect(self._update_charts)
        self.timer.start(interval)
    
    def update_speed(self, speed_bps: float, total_bandwidth_bps: float = 0):
        """
        更新速度数据
        
        Args:
            speed_bps: 当前速度（bits per second）
            total_bandwidth_bps: 总带宽限制（可选）
        """
        import time
        
        # 更新速度历史
        self.speed_history.add(speed_bps, time.time())
        
        # 更新 ETA 预测
        self.eta_predictor.update(speed_bps)
        
        # 更新峰值速度
        current_max = self.speed_history.get_max()
        if current_max > self.peak_speed:
            self.peak_speed = current_max
        
        # 更新带宽使用率
        if total_bandwidth_bps > 0:
            self.bandwidth_usage = (speed_bps / total_bandwidth_bps) * 100
        else:
            self.bandwidth_usage = 0
    
    def _update_charts(self):
        """更新图表显示"""
        # 获取速度数据（最近 60 秒）
        speeds = self.speed_history.get_recent(60) / 1_000_000  # 转换为 Mbps
        
        # 更新速度曲线
        if len(speeds) > 0:
            self.speed_curve.setData(speeds)
            
            # 自动调整 Y 轴范围
            max_speed = np.max(speeds) if len(speeds) > 0 else 0
            if max_speed > 0:
                self.speed_plot.setYRange(0, max_speed * 1.2)  # 留 20% 余量
        
        # 更新带宽使用曲线
        if hasattr(self, 'bandwidth_usage'):
            self.bandwidth_curve.setData([self.bandwidth_usage])
        
        # 更新统计信息
        self._update_stats()
    
    def _update_stats(self):
        """更新统计信息显示"""
        speeds = self.speed_history.get_recent(10) / 1_000_000  # 最近 10 秒
        
        current_speed = float(speeds[-1]) if len(speeds) > 0 else 0
        avg_speed = float(np.mean(speeds)) if len(speeds) > 0 else 0
        peak_speed = self.peak_speed / 1_000_000
        
        # 计算 ETA
        eta_str = self.eta_predictor.format_eta(self.eta_predictor.calculate_eta(0))
        
        self.stats_label.setText(f"""
        当前速度：<span style='color: #1f77b4; font-weight: bold;'>{current_speed:.2f} Mbps</span>
        平均速度：<span style='color: #2ca02c;'>{avg_speed:.2f} Mbps</span>
        峰值速度：<span style='color: #ff7f0e;'>{peak_speed:.2f} Mbps</span>
        剩余时间：<span style='color: #d62728;'>{eta_str}</span>
        """)
    
    def reset(self):
        """重置图表"""
        self.speed_history.clear()
        self.eta_predictor.reset()
        self.peak_speed = 0.0
        self.speed_curve.setData([])
        self.bandwidth_curve.setData([])
        self._update_stats()
    
    def set_theme(self, theme: str):
        """
        设置主题
        
        Args:
            theme: 'dark' 或 'light'
        """
        if theme == 'dark':
            bg_color = '#2b2b2b'
            fg_color = '#ffffff'
            plot_bg = '#1e1e1e'
        else:
            bg_color = '#f0f0f0'
            fg_color = '#000000'
            plot_bg = '#ffffff'
        
        self.stats_label.setStyleSheet(f"""
            QLabel {{
                font-size: 14px;
                padding: 10px;
                background-color: {bg_color};
                color: {fg_color};
                border-radius: 5px;
                font-family: 'Monaco', 'Courier New', monospace;
            }}
        """)


if __name__ == "__main__":
    # 简单测试
    from PyQt5.QtWidgets import QApplication
    import sys
    
    app = QApplication(sys.argv)
    
    chart = ProgressChartWidget()
    chart.setWindowTitle("进度图表测试")
    chart.resize(800, 600)
    chart.show()
    
    # 模拟速度数据
    import time
    def simulate_download():
        for i in range(60):
            speed = 10_000_000 + np.random.randn() * 1_000_000  # 10 Mbps ± 1 Mbps
            chart.update_speed(max(0, speed), 100_000_000)
            time.sleep(1)
    
    # 在独立线程中模拟
    from PyQt5.QtCore import QThread
    class SimulateThread(QThread):
        def run(self):
            simulate_download()
    
    thread = SimulateThread()
    thread.start()
    
    sys.exit(app.exec_())
