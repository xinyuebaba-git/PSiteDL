"""
进度跟踪和预测 - Phase 3 实现

包含:
- SpeedHistory: 速度历史记录（环形缓冲区）
- ETAPredictor: ETA 预测器（指数加权滑动平均）
- DownloadProgress: 下载进度数据类
"""

from collections import deque
from dataclasses import dataclass, field
import time
from typing import List, Optional
import numpy as np


@dataclass
class SpeedHistory:
    """
    速度历史记录（环形缓冲区）
    
    特性:
    - 固定大小（最大 60 秒）
    - O(1) 添加操作
    - 支持获取最近 N 秒数据
    - 支持计算平均值
    """
    
    max_seconds: int = 60
    buffer: deque = field(default_factory=lambda: deque(maxlen=60))
    timestamps: deque = field(default_factory=lambda: deque(maxlen=60))
    
    def __post_init__(self):
        """确保 deque 有正确的 maxlen"""
        if not hasattr(self.buffer, 'maxlen'):
            self.buffer = deque(maxlen=self.max_seconds)
        if not hasattr(self.timestamps, 'maxlen'):
            self.timestamps = deque(maxlen=self.max_seconds)
    
    def add(self, speed_bps: float, timestamp: Optional[float] = None):
        """
        添加速度样本
        
        Args:
            speed_bps: 速度（bits per second）
            timestamp: 时间戳（默认当前时间）
        """
        if timestamp is None:
            timestamp = time.time()
        
        self.buffer.append(speed_bps)
        self.timestamps.append(timestamp)
    
    def get_recent(self, seconds: int = 10) -> np.ndarray:
        """
        获取最近 N 秒的数据
        
        Args:
            seconds: 获取最近多少秒的数据
            
        Returns:
            np.ndarray: 速度数组
        """
        if not self.buffer or not self.timestamps:
            return np.array([])
        
        cutoff = self.timestamps[-1] - seconds
        indices = [i for i, t in enumerate(self.timestamps) if t >= cutoff]
        
        if not indices:
            return np.array([])
        
        return np.array([self.buffer[i] for i in indices])
    
    def get_average(self, seconds: int = 10) -> float:
        """
        计算最近 N 秒的平均速度
        
        Args:
            seconds: 计算多少秒的平均值
            
        Returns:
            float: 平均速度（bps）
        """
        recent = self.get_recent(seconds)
        return float(np.mean(recent)) if len(recent) > 0 else 0.0
    
    def get_max(self, seconds: int = 60) -> float:
        """
        获取 N 秒内的峰值速度
        
        Args:
            seconds: 获取多少秒内的峰值
            
        Returns:
            float: 峰值速度
        """
        recent = self.get_recent(seconds)
        return float(np.max(recent)) if len(recent) > 0 else 0.0
    
    def clear(self):
        """清空历史记录"""
        self.buffer.clear()
        self.timestamps.clear()


@dataclass
class ETAPredictor:
    """
    ETA 预测器（指数加权滑动平均）
    
    特性:
    - 指数平滑避免 ETA 跳动
    - 可配置平滑因子
    - 支持格式化显示
    """
    
    alpha: float = 0.3  # 平滑因子
    ema_speed: Optional[float] = field(default=None, init=False)
    
    def update(self, current_speed: float) -> float:
        """
        更新速度并返回平滑后的速度
        
        Args:
            current_speed: 当前速度（bps）
            
        Returns:
            float: 平滑后的速度
        """
        if self.ema_speed is None:
            self.ema_speed = current_speed
        else:
            # 指数加权移动平均
            self.ema_speed = (self.alpha * current_speed + 
                            (1 - self.alpha) * self.ema_speed)
        
        return float(self.ema_speed)
    
    def calculate_eta(self, remaining_bytes: int) -> int:
        """
        计算剩余时间（秒）
        
        Args:
            remaining_bytes: 剩余字节数
            
        Returns:
            int: 剩余时间（秒），无法计算返回 inf
        """
        if self.ema_speed is None or self.ema_speed <= 0:
            return float('inf')
        
        return int(remaining_bytes / self.ema_speed)
    
    def format_eta(self, seconds: int) -> str:
        """
        格式化 ETA 显示
        
        Args:
            seconds: 秒数
            
        Returns:
            str: 格式化字符串（HH:MM:SS 或 MM:SS）
        """
        if seconds == float('inf') or seconds < 0:
            return "--:--"
        
        hours = int(seconds) // 3600
        minutes = (int(seconds) % 3600) // 60
        secs = int(seconds) % 60
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes:02d}:{secs:02d}"
    
    def reset(self):
        """重置预测器"""
        self.ema_speed = None


@dataclass
class DownloadProgress:
    """
    下载进度数据类
    
    整合速度历史、ETA 预测和进度信息
    """
    
    downloaded_bytes: int = 0
    total_bytes: int = 0
    speed_history: SpeedHistory = field(default_factory=SpeedHistory)
    eta_predictor: ETAPredictor = field(default_factory=ETAPredictor)
    peak_speed: float = 0.0
    start_time: float = field(default_factory=time.time)
    
    @property
    def progress(self) -> float:
        """下载进度（0.0 - 1.0）"""
        if self.total_bytes == 0:
            return 0.0
        return min(1.0, self.downloaded_bytes / self.total_bytes)
    
    @property
    def current_speed(self) -> float:
        """当前速度（最近 10 秒平均）"""
        return self.speed_history.get_average(seconds=10)
    
    @property
    def average_speed(self) -> float:
        """平均速度（全部历史）"""
        return self.speed_history.get_average(seconds=60)
    
    @property
    def eta_seconds(self) -> int:
        """剩余时间（秒）"""
        remaining = self.total_bytes - self.downloaded_bytes
        return self.eta_predictor.calculate_eta(remaining)
    
    @property
    def eta_formatted(self) -> str:
        """格式化的 ETA"""
        return self.eta_predictor.format_eta(self.eta_seconds)
    
    def update(self, downloaded_bytes: int, speed_bps: float):
        """
        更新下载进度
        
        Args:
            downloaded_bytes: 已下载字节数
            speed_bps: 当前速度（bps）
        """
        self.downloaded_bytes = downloaded_bytes
        
        # 更新速度历史
        self.speed_history.add(speed_bps)
        
        # 更新峰值速度
        current_max = self.speed_history.get_max()
        if current_max > self.peak_speed:
            self.peak_speed = current_max
        
        # 更新 ETA 预测
        self.eta_predictor.update(speed_bps)
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "progress": self.progress,
            "downloaded_bytes": self.downloaded_bytes,
            "total_bytes": self.total_bytes,
            "current_speed": self.current_speed,
            "average_speed": self.average_speed,
            "peak_speed": self.peak_speed,
            "eta_seconds": self.eta_seconds,
            "eta_formatted": self.eta_formatted,
        }


if __name__ == "__main__":
    # 简单测试
    print("Testing SpeedHistory...")
    history = SpeedHistory()
    for i in range(100):
        history.add(i * 1000, time.time() + i)
    print(f"Buffer size: {len(history.buffer)} (max 60)")
    print(f"Recent 10s: {len(history.get_recent(10))} samples")
    print(f"Average: {history.get_average():.2f} bps")
    
    print("\nTesting ETAPredictor...")
    predictor = ETAPredictor()
    for _ in range(20):
        predictor.update(1_000_000)
    eta = predictor.calculate_eta(10_000_000)
    print(f"ETA for 10MB at 1Mbps: {predictor.format_eta(eta)}")
    
    print("\nTesting DownloadProgress...")
    progress = DownloadProgress(total_bytes=100_000_000)
    for i in range(10):
        progress.update(i * 10_000_000, 1_000_000 + i * 100_000)
        print(f"Progress: {progress.progress:.1%}, Speed: {progress.current_speed/1e6:.2f}Mbps, ETA: {progress.eta_formatted}")
