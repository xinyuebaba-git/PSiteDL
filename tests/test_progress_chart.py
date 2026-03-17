"""
进度图表 TDD 测试 - Phase 2

基于 specs/progress-chart.md 编写
验收标准：AC1-AC4
"""

import pytest
import time
from collections import deque
from unittest.mock import Mock, patch
import numpy as np


class TestSpeedHistory:
    """测试速度历史记录（环形缓冲区）"""

    def test_create_speed_history(self):
        """测试创建速度历史"""
        from src.webvidgrab.progress import SpeedHistory
        
        history = SpeedHistory(max_seconds=60)
        
        assert history.max_seconds == 60
        assert len(history.buffer) == 0

    def test_add_speed_sample(self):
        """测试添加速度样本"""
        from src.webvidgrab.progress import SpeedHistory
        
        history = SpeedHistory(max_seconds=60)
        timestamp = time.time()
        
        history.add(1_000_000, timestamp)  # 1 Mbps
        
        assert len(history.buffer) == 1
        assert history.buffer[0] == 1_000_000

    def test_buffer_max_size(self):
        """测试环形缓冲区最大大小"""
        from src.webvidgrab.progress import SpeedHistory
        
        history = SpeedHistory(max_seconds=60)
        
        # 添加 100 个样本（超过 60 秒）
        for i in range(100):
            history.add(i * 1000, time.time() + i)
        
        # 应该不超过最大大小
        assert len(history.buffer) <= 60

    def test_get_recent_seconds(self):
        """测试获取最近 N 秒数据"""
        from src.webvidgrab.progress import SpeedHistory
        
        history = SpeedHistory(max_seconds=60)
        base_time = time.time()
        
        # 添加 30 秒的数据（每秒 1 个样本）
        for i in range(30):
            history.add(i * 1000, base_time + i)
        
        # 获取最近 10 秒
        recent = history.get_recent(10)
        
        # 应该返回约 10 个样本
        assert 8 <= len(recent) <= 12  # 允许一定误差

    def test_get_average(self):
        """测试计算平均速度"""
        from src.webvidgrab.progress import SpeedHistory
        
        history = SpeedHistory(max_seconds=60)
        base_time = time.time()
        
        # 添加稳定速度
        for i in range(20):
            history.add(1_000_000, base_time + i)  # 1 Mbps
        
        avg = history.get_average(seconds=10)
        
        assert 0.9e6 <= avg <= 1.1e6  # 允许 10% 误差

    def test_empty_buffer_average(self):
        """测试空缓冲区平均速度"""
        from src.webvidgrab.progress import SpeedHistory
        
        history = SpeedHistory()
        
        avg = history.get_average()
        
        assert avg == 0.0


class TestETAPredictor:
    """测试 ETA 预测器"""

    def test_create_eta_predictor(self):
        """测试创建 ETA 预测器"""
        from src.webvidgrab.progress import ETAPredictor
        
        predictor = ETAPredictor(alpha=0.3)
        
        assert predictor.alpha == 0.3
        assert predictor.ema_speed is None

    def test_first_update(self):
        """测试首次更新"""
        from src.webvidgrab.progress import ETAPredictor
        
        predictor = ETAPredictor()
        speed = predictor.update(1_000_000)
        
        assert speed == 1_000_000  # 首次应该等于当前速度

    def test_exponential_smoothing(self):
        """测试指数平滑"""
        from src.webvidgrab.progress import ETAPredictor
        
        predictor = ETAPredictor(alpha=0.3)
        
        # 多次更新
        speeds = [predictor.update(1_000_000) for _ in range(10)]
        
        # 应该趋于稳定
        assert abs(speeds[-1] - speeds[-2]) < 1000  # 差异应该很小

    def test_calculate_eta(self):
        """测试计算剩余时间"""
        from src.webvidgrab.progress import ETAPredictor
        
        predictor = ETAPredictor()
        
        # 稳定速度 1 Mbps
        for _ in range(20):
            predictor.update(1_000_000)
        
        # 10 MB 剩余
        eta = predictor.calculate_eta(10_000_000)
        
        # 应该约 10 秒
        assert 8 <= eta <= 12  # ±20%

    def test_calculate_eta_zero_speed(self):
        """测试零速度时 ETA"""
        from src.webvidgrab.progress import ETAPredictor
        
        predictor = ETAPredictor()
        
        eta = predictor.calculate_eta(1_000_000)
        
        assert eta == float('inf')

    def test_format_eta(self):
        """测试格式化 ETA"""
        from src.webvidgrab.progress import ETAPredictor
        
        predictor = ETAPredictor()
        
        # 测试不同格式
        assert predictor.format_eta(3661) == "01:01:01"  # 1 小时 1 分 1 秒
        assert predictor.format_eta(125) == "02:05"      # 2 分 5 秒
        assert predictor.format_eta(float('inf')) == "--:--"


class TestProgressChartWidget:
    """测试进度图表组件"""

    @pytest.fixture
    def chart(self):
        """创建图表组件"""
        from src.webvidgrab.gui.progress_chart import ProgressChartWidget
        return ProgressChartWidget()

    def test_chart_creation(self, chart):
        """测试图表创建"""
        assert chart.speed_history is not None
        assert chart.eta_predictor is not None
        assert chart.stats_label is not None

    def test_update_speed(self, chart):
        """测试更新速度"""
        chart.update_speed(1_000_000, 10_000_000)
        
        assert len(chart.speed_history.buffer) > 0

    def test_stats_display(self, chart):
        """测试统计信息显示"""
        # 更新速度
        for _ in range(5):
            chart.update_speed(1_000_000, 10_000_000)
            time.sleep(0.1)
        
        # 验证统计信息
        stats = chart.stats_label.text()
        assert "当前速度" in stats
        assert "Mbps" in stats


class TestAcceptanceCriteria:
    """验收标准测试"""

    def test_ac1_realtime_chart(self):
        """AC1: 实时速度图表显示（1Hz 更新）"""
        from src.webvidgrab.gui.progress_chart import ProgressChartWidget
        
        chart = ProgressChartWidget()
        
        # 模拟下载
        for i in range(10):
            chart.update_speed(1_000_000 + i * 100000, 10_000_000)
            time.sleep(0.1)
        
        # 验证图表更新
        assert len(chart.speed_history.buffer) > 0
        assert chart.speed_curve is not None

    def test_ac2_eta_accuracy(self):
        """AC2: ETA 预测误差 < ±20%"""
        from src.webvidgrab.progress import ETAPredictor
        
        predictor = ETAPredictor(alpha=0.3)
        
        # 稳定速度 1 Mbps
        for _ in range(20):
            predictor.update(1_000_000)
        
        # 10 MB 剩余，应该约 10 秒
        eta = predictor.calculate_eta(10_000_000)
        
        # 验证误差 < ±20%
        expected = 10
        error = abs(eta - expected) / expected
        assert error <= 0.2

    def test_ac3_task_queue(self):
        """AC3: 任务队列状态可视化"""
        # 这个测试需要 GUI 环境，暂时跳过
        pytest.skip("需要 GUI 环境")

    def test_ac4_global_control(self):
        """AC4: 全局暂停/恢复"""
        # 这个测试需要完整的下载器，暂时跳过
        pytest.skip("需要下载器环境")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
