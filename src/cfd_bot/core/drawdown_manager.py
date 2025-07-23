"""
ドローダウン管理システム - ステップ62

高度なドローダウン監視・制御・回復機能を提供
"""

import math
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import threading
import time

# ログ設定
logger = logging.getLogger(__name__)


class DrawdownLevel(Enum):
    """ドローダウンレベル"""
    NORMAL = "normal"       # 正常範囲
    WARNING = "warning"     # 警告レベル
    CRITICAL = "critical"   # 危険レベル
    EMERGENCY = "emergency" # 緊急レベル


class RecoveryMode(Enum):
    """回復モード"""
    NORMAL = "normal"           # 通常モード
    CONSERVATIVE = "conservative" # 保守的モード
    AGGRESSIVE = "aggressive"   # 積極的モード
    DEFENSIVE = "defensive"     # 防御的モード


@dataclass
class DrawdownPeriod:
    """ドローダウン期間"""
    start_date: datetime
    end_date: Optional[datetime]
    peak_value: float
    trough_value: float
    drawdown_amount: float
    drawdown_percentage: float
    duration_days: int
    recovery_date: Optional[datetime] = None
    recovery_duration_days: Optional[int] = None


@dataclass
class DrawdownMetrics:
    """ドローダウン指標"""
    current_drawdown: float
    max_drawdown: float
    avg_drawdown: float
    drawdown_frequency: float
    avg_recovery_time: float
    current_underwater_days: int
    max_underwater_days: int
    peak_to_trough_ratio: float
    recovery_factor: float
    timestamp: datetime


@dataclass
class DrawdownAlert:
    """ドローダウンアラート"""
    level: DrawdownLevel
    message: str
    current_drawdown: float
    threshold: float
    recommended_action: str
    timestamp: datetime
    acknowledged: bool = False


@dataclass
class RecoveryStrategy:
    """回復戦略"""
    mode: RecoveryMode
    position_size_multiplier: float
    risk_reduction_factor: float
    entry_threshold_multiplier: float
    exit_threshold_multiplier: float
    max_positions: int
    recovery_target: float
    timeout_hours: int


class DrawdownManager:
    """ドローダウン管理システム"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """初期化"""
        self.config = config or {}
        
        # ドローダウン閾値設定
        self.thresholds = {
            "warning": self.config.get("warning_threshold", 0.05),      # 5%
            "critical": self.config.get("critical_threshold", 0.10),    # 10%
            "emergency": self.config.get("emergency_threshold", 0.15),  # 15%
            "max_drawdown": self.config.get("max_drawdown", 0.20)       # 20%
        }
        
        # 履歴データ
        self.equity_history: List[Tuple[datetime, float]] = []
        self.drawdown_periods: List[DrawdownPeriod] = []
        self.alert_history: List[DrawdownAlert] = []
        self.recovery_history: List[Dict[str, Any]] = []
        
        # 現在の状態
        self.current_peak = 0.0
        self.current_drawdown = 0.0
        self.current_level = DrawdownLevel.NORMAL
        self.current_recovery_mode = RecoveryMode.NORMAL
        self.underwater_start_date: Optional[datetime] = None
        
        # 回復戦略
        self.recovery_strategies = {
            RecoveryMode.NORMAL: RecoveryStrategy(
                mode=RecoveryMode.NORMAL,
                position_size_multiplier=1.0,
                risk_reduction_factor=1.0,
                entry_threshold_multiplier=1.0,
                exit_threshold_multiplier=1.0,
                max_positions=10,
                recovery_target=0.02,
                timeout_hours=24
            ),
            RecoveryMode.CONSERVATIVE: RecoveryStrategy(
                mode=RecoveryMode.CONSERVATIVE,
                position_size_multiplier=0.5,
                risk_reduction_factor=0.7,
                entry_threshold_multiplier=1.5,
                exit_threshold_multiplier=0.8,
                max_positions=5,
                recovery_target=0.01,
                timeout_hours=48
            ),
            RecoveryMode.AGGRESSIVE: RecoveryStrategy(
                mode=RecoveryMode.AGGRESSIVE,
                position_size_multiplier=1.5,
                risk_reduction_factor=1.2,
                entry_threshold_multiplier=0.8,
                exit_threshold_multiplier=1.2,
                max_positions=15,
                recovery_target=0.05,
                timeout_hours=12
            ),
            RecoveryMode.DEFENSIVE: RecoveryStrategy(
                mode=RecoveryMode.DEFENSIVE,
                position_size_multiplier=0.3,
                risk_reduction_factor=0.5,
                entry_threshold_multiplier=2.0,
                exit_threshold_multiplier=0.6,
                max_positions=3,
                recovery_target=0.005,
                timeout_hours=72
            )
        }
        
        # コールバック関数
        self.callbacks: Dict[str, List[Callable]] = {
            "drawdown_warning": [],
            "drawdown_critical": [],
            "drawdown_emergency": [],
            "recovery_started": [],
            "recovery_completed": [],
            "peak_updated": []
        }
        
        # 監視スレッド
        self.monitoring_thread: Optional[threading.Thread] = None
        self.monitoring_active = False
        
        logger.info("ドローダウン管理システム初期化完了")
    
    def update_equity(self, equity: float, timestamp: Optional[datetime] = None) -> DrawdownMetrics:
        """資産価値更新とドローダウン計算"""
        if timestamp is None:
            timestamp = datetime.now()
        
        # 履歴に追加
        self.equity_history.append((timestamp, equity))
        
        # 履歴サイズ制限（最新1000件）
        if len(self.equity_history) > 1000:
            self.equity_history = self.equity_history[-1000:]
        
        # ピーク更新チェック
        if equity > self.current_peak:
            self._update_peak(equity, timestamp)
        
        # ドローダウン計算
        self.current_drawdown = self._calculate_current_drawdown(equity)
        
        # レベル判定
        new_level = self._determine_drawdown_level(self.current_drawdown)
        if new_level != self.current_level:
            self._handle_level_change(new_level, timestamp)
        
        # 水面下期間の管理
        self._manage_underwater_period(timestamp)
        
        # ドローダウン指標計算
        metrics = self._calculate_drawdown_metrics(timestamp)
        
        logger.debug(
            f"資産価値更新: {equity:.2f}, ドローダウン: {self.current_drawdown:.2%}, "
            f"レベル: {self.current_level.value}"
        )
        
        return metrics
    
    def _update_peak(self, equity: float, timestamp: datetime):
        """ピーク更新処理"""
        old_peak = self.current_peak
        self.current_peak = equity
        
        # 水面下期間終了
        if self.underwater_start_date:
            self._end_underwater_period(timestamp)
        
        # コールバック実行
        self._execute_callbacks("peak_updated", {
            "old_peak": old_peak,
            "new_peak": equity,
            "timestamp": timestamp
        })
        
        logger.info(f"新しいピーク更新: {old_peak:.2f} -> {equity:.2f}")
    
    def _calculate_current_drawdown(self, current_equity: float) -> float:
        """現在のドローダウン計算"""
        if self.current_peak <= 0:
            return 0.0
        
        return (self.current_peak - current_equity) / self.current_peak
    
    def _determine_drawdown_level(self, drawdown: float) -> DrawdownLevel:
        """ドローダウンレベル判定"""
        if drawdown >= self.thresholds["emergency"]:
            return DrawdownLevel.EMERGENCY
        elif drawdown >= self.thresholds["critical"]:
            return DrawdownLevel.CRITICAL
        elif drawdown >= self.thresholds["warning"]:
            return DrawdownLevel.WARNING
        else:
            return DrawdownLevel.NORMAL
    
    def _handle_level_change(self, new_level: DrawdownLevel, timestamp: datetime):
        """レベル変更処理"""
        old_level = self.current_level
        self.current_level = new_level
        
        # アラート生成
        alert = self._create_alert(new_level, timestamp)
        self.alert_history.append(alert)
        
        # 回復戦略の調整
        self._adjust_recovery_strategy(new_level)
        
        # コールバック実行
        callback_key = f"drawdown_{new_level.value}"
        if callback_key in self.callbacks:
            self._execute_callbacks(callback_key, {
                "old_level": old_level,
                "new_level": new_level,
                "current_drawdown": self.current_drawdown,
                "alert": alert
            })
        
        logger.warning(
            f"ドローダウンレベル変更: {old_level.value} -> {new_level.value} "
            f"({self.current_drawdown:.2%})"
        )
    
    def _create_alert(self, level: DrawdownLevel, timestamp: datetime) -> DrawdownAlert:
        """アラート作成"""
        threshold = self.thresholds.get(level.value, 0.0)
        
        messages = {
            DrawdownLevel.WARNING: "ドローダウンが警告レベルに達しました",
            DrawdownLevel.CRITICAL: "ドローダウンが危険レベルに達しました",
            DrawdownLevel.EMERGENCY: "ドローダウンが緊急レベルに達しました"
        }
        
        recommendations = {
            DrawdownLevel.WARNING: "リスク管理の見直しを検討してください",
            DrawdownLevel.CRITICAL: "ポジションサイズの削減を推奨します",
            DrawdownLevel.EMERGENCY: "取引の一時停止を強く推奨します"
        }
        
        return DrawdownAlert(
            level=level,
            message=messages.get(level, "ドローダウン状況が変化しました"),
            current_drawdown=self.current_drawdown,
            threshold=threshold,
            recommended_action=recommendations.get(level, "状況を監視してください"),
            timestamp=timestamp
        )
    
    def _adjust_recovery_strategy(self, level: DrawdownLevel):
        """回復戦略調整"""
        strategy_mapping = {
            DrawdownLevel.NORMAL: RecoveryMode.NORMAL,
            DrawdownLevel.WARNING: RecoveryMode.CONSERVATIVE,
            DrawdownLevel.CRITICAL: RecoveryMode.DEFENSIVE,
            DrawdownLevel.EMERGENCY: RecoveryMode.DEFENSIVE
        }
        
        new_mode = strategy_mapping.get(level, RecoveryMode.NORMAL)
        if new_mode != self.current_recovery_mode:
            old_mode = self.current_recovery_mode
            self.current_recovery_mode = new_mode
            
            logger.info(f"回復戦略変更: {old_mode.value} -> {new_mode.value}")
    
    def _manage_underwater_period(self, timestamp: datetime):
        """水面下期間管理"""
        if self.current_drawdown > 0:
            if self.underwater_start_date is None:
                self.underwater_start_date = timestamp
                logger.info(f"水面下期間開始: {timestamp}")
        else:
            if self.underwater_start_date is not None:
                self._end_underwater_period(timestamp)
    
    def _end_underwater_period(self, timestamp: datetime):
        """水面下期間終了"""
        if self.underwater_start_date:
            duration = (timestamp - self.underwater_start_date).days
            logger.info(f"水面下期間終了: {duration}日間")
            self.underwater_start_date = None
    
    def _calculate_drawdown_metrics(self, timestamp: datetime) -> DrawdownMetrics:
        """ドローダウン指標計算"""
        if not self.equity_history:
            return DrawdownMetrics(
                current_drawdown=0.0,
                max_drawdown=0.0,
                avg_drawdown=0.0,
                drawdown_frequency=0.0,
                avg_recovery_time=0.0,
                current_underwater_days=0,
                max_underwater_days=0,
                peak_to_trough_ratio=1.0,
                recovery_factor=1.0,
                timestamp=timestamp
            )
        
        # 最大ドローダウン計算
        max_drawdown = self._calculate_max_drawdown()
        
        # 平均ドローダウン計算
        avg_drawdown = self._calculate_average_drawdown()
        
        # ドローダウン頻度計算
        drawdown_frequency = self._calculate_drawdown_frequency()
        
        # 平均回復時間計算
        avg_recovery_time = self._calculate_average_recovery_time()
        
        # 現在の水面下日数
        current_underwater_days = 0
        if self.underwater_start_date:
            current_underwater_days = (timestamp - self.underwater_start_date).days
        
        # 最大水面下日数
        max_underwater_days = self._calculate_max_underwater_days()
        
        # ピーク・トラフ比率
        peak_to_trough_ratio = self._calculate_peak_to_trough_ratio()
        
        # 回復係数
        recovery_factor = self._calculate_recovery_factor()
        
        return DrawdownMetrics(
            current_drawdown=self.current_drawdown,
            max_drawdown=max_drawdown,
            avg_drawdown=avg_drawdown,
            drawdown_frequency=drawdown_frequency,
            avg_recovery_time=avg_recovery_time,
            current_underwater_days=current_underwater_days,
            max_underwater_days=max_underwater_days,
            peak_to_trough_ratio=peak_to_trough_ratio,
            recovery_factor=recovery_factor,
            timestamp=timestamp
        )
    
    def _calculate_max_drawdown(self) -> float:
        """最大ドローダウン計算"""
        if not self.equity_history:
            return 0.0
        
        max_drawdown = 0.0
        peak = self.equity_history[0][1]
        
        for _, equity in self.equity_history:
            if equity > peak:
                peak = equity
            
            if peak > 0:
                drawdown = (peak - equity) / peak
                max_drawdown = max(max_drawdown, drawdown)
        
        return max_drawdown
    
    def _calculate_average_drawdown(self) -> float:
        """平均ドローダウン計算"""
        if not self.drawdown_periods:
            return 0.0
        
        total_drawdown = sum(period.drawdown_percentage for period in self.drawdown_periods)
        return total_drawdown / len(self.drawdown_periods) / 100
    
    def _calculate_drawdown_frequency(self) -> float:
        """ドローダウン頻度計算（年間）"""
        if not self.equity_history or not self.drawdown_periods:
            return 0.0
        
        # 期間計算（日数）
        start_date = self.equity_history[0][0]
        end_date = self.equity_history[-1][0]
        total_days = (end_date - start_date).days
        
        if total_days <= 0:
            return 0.0
        
        # 年間頻度
        return len(self.drawdown_periods) * 365 / total_days
    
    def _calculate_average_recovery_time(self) -> float:
        """平均回復時間計算（日数）"""
        completed_periods = [
            period for period in self.drawdown_periods 
            if period.recovery_duration_days is not None
        ]
        
        if not completed_periods:
            return 0.0
        
        total_recovery_days = sum(
            period.recovery_duration_days for period in completed_periods
        )
        return total_recovery_days / len(completed_periods)
    
    def _calculate_max_underwater_days(self) -> int:
        """最大水面下日数計算"""
        if not self.drawdown_periods:
            return 0
        
        max_days = 0
        for period in self.drawdown_periods:
            if period.recovery_duration_days:
                max_days = max(max_days, period.recovery_duration_days)
        
        return max_days
    
    def _calculate_peak_to_trough_ratio(self) -> float:
        """ピーク・トラフ比率計算"""
        if not self.equity_history:
            return 1.0
        
        peak = max(equity for _, equity in self.equity_history)
        trough = min(equity for _, equity in self.equity_history)
        
        return peak / trough if trough > 0 else 1.0
    
    def _calculate_recovery_factor(self) -> float:
        """回復係数計算"""
        if not self.drawdown_periods:
            return 1.0
        
        # 完了した回復期間の平均回復率
        completed_recoveries = [
            period for period in self.drawdown_periods 
            if period.recovery_date is not None
        ]
        
        if not completed_recoveries:
            return 1.0
        
        recovery_rates = []
        for period in completed_recoveries:
            if period.drawdown_percentage > 0:
                recovery_rate = 1.0 / (period.drawdown_percentage / 100)
                recovery_rates.append(recovery_rate)
        
        return sum(recovery_rates) / len(recovery_rates) if recovery_rates else 1.0
    
    def get_recovery_strategy(self) -> RecoveryStrategy:
        """現在の回復戦略取得"""
        return self.recovery_strategies[self.current_recovery_mode]
    
    def start_recovery_mode(self, mode: RecoveryMode, target: Optional[float] = None) -> bool:
        """回復モード開始"""
        try:
            if mode not in self.recovery_strategies:
                logger.error(f"不明な回復モード: {mode}")
                return False
            
            old_mode = self.current_recovery_mode
            self.current_recovery_mode = mode
            
            # 回復目標設定
            if target is not None:
                self.recovery_strategies[mode].recovery_target = target
            
            # 回復履歴記録
            recovery_record = {
                "start_time": datetime.now(),
                "mode": mode.value,
                "old_mode": old_mode.value,
                "target": self.recovery_strategies[mode].recovery_target,
                "starting_drawdown": self.current_drawdown
            }
            self.recovery_history.append(recovery_record)
            
            # コールバック実行
            self._execute_callbacks("recovery_started", recovery_record)
            
            logger.info(
                f"回復モード開始: {mode.value} (目標: {target:.2%})"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"回復モード開始エラー: {e}")
            return False
    
    def check_recovery_completion(self) -> bool:
        """回復完了チェック"""
        try:
            strategy = self.get_recovery_strategy()
            
            # 回復目標達成チェック
            if self.current_drawdown <= strategy.recovery_target:
                self._complete_recovery()
                return True
            
            # タイムアウトチェック
            if self.recovery_history:
                last_recovery = self.recovery_history[-1]
                start_time = last_recovery.get("start_time")
                if start_time:
                    elapsed_hours = (datetime.now() - start_time).total_seconds() / 3600
                    if elapsed_hours >= strategy.timeout_hours:
                        logger.warning(f"回復タイムアウト: {elapsed_hours:.1f}時間経過")
                        self._timeout_recovery()
                        return False
            
            return False
            
        except Exception as e:
            logger.error(f"回復完了チェックエラー: {e}")
            return False

    def _complete_recovery(self):
        """回復完了処理"""
        if self.recovery_history:
            last_recovery = self.recovery_history[-1]
            last_recovery["end_time"] = datetime.now()
            last_recovery["success"] = True
            last_recovery["final_drawdown"] = self.current_drawdown
            
            # コールバック実行
            self._execute_callbacks("recovery_completed", last_recovery)
            
            logger.info("回復完了")
        
        # 通常モードに戻す
        self.current_recovery_mode = RecoveryMode.NORMAL
    
    def _timeout_recovery(self):
        """回復タイムアウト処理"""
        if self.recovery_history:
            last_recovery = self.recovery_history[-1]
            last_recovery["end_time"] = datetime.now()
            last_recovery["success"] = False
            last_recovery["timeout"] = True
            last_recovery["final_drawdown"] = self.current_drawdown
        
        # より保守的なモードに変更
        old_mode = self.current_recovery_mode
        if self.current_recovery_mode == RecoveryMode.AGGRESSIVE:
            self.current_recovery_mode = RecoveryMode.CONSERVATIVE
        elif self.current_recovery_mode == RecoveryMode.CONSERVATIVE:
            self.current_recovery_mode = RecoveryMode.DEFENSIVE
        else:
            # それ以外はNORMALに戻す
            self.current_recovery_mode = RecoveryMode.NORMAL
            
        logger.info(f"回復タイムアウト: {old_mode.value} -> {self.current_recovery_mode.value}")
    
    def add_callback(self, event_type: str, callback: Callable):
        """コールバック関数追加"""
        if event_type in self.callbacks:
            self.callbacks[event_type].append(callback)
            logger.info(f"コールバック追加: {event_type}")
        else:
            logger.warning(f"不明なイベントタイプ: {event_type}")
    
    def _execute_callbacks(self, event_type: str, data: Dict[str, Any]):
        """コールバック実行"""
        try:
            for callback in self.callbacks.get(event_type, []):
                callback(data)
        except Exception as e:
            logger.error(f"コールバック実行エラー ({event_type}): {e}")
    
    def start_monitoring(self, interval_seconds: int = 60):
        """監視開始"""
        if self.monitoring_active:
            logger.warning("監視は既に開始されています")
            return
        
        self.monitoring_active = True
        self.monitoring_thread = threading.Thread(
            target=self._monitoring_loop,
            args=(interval_seconds,),
            daemon=True
        )
        self.monitoring_thread.start()
        
        logger.info(f"ドローダウン監視開始 (間隔: {interval_seconds}秒)")
    
    def stop_monitoring(self):
        """監視停止"""
        self.monitoring_active = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)
        
        logger.info("ドローダウン監視停止")
    
    def _monitoring_loop(self, interval_seconds: int):
        """監視ループ"""
        while self.monitoring_active:
            try:
                # 回復完了チェック
                if self.current_recovery_mode != RecoveryMode.NORMAL:
                    self.check_recovery_completion()
                
                # アラート履歴清理（古いアラートを削除）
                self._cleanup_old_alerts()
                
                time.sleep(interval_seconds)
                
            except Exception as e:
                logger.error(f"監視ループエラー: {e}")
                time.sleep(interval_seconds)
    
    def _cleanup_old_alerts(self, max_age_days: int = 30):
        """古いアラート清理"""
        cutoff_date = datetime.now() - timedelta(days=max_age_days)
        self.alert_history = [
            alert for alert in self.alert_history 
            if alert.timestamp > cutoff_date
        ]
    
    def get_current_status(self) -> Dict[str, Any]:
        """現在の状態取得"""
        return {
            "current_drawdown": self.current_drawdown,
            "current_level": self.current_level.value,
            "current_peak": self.current_peak,
            "recovery_mode": self.current_recovery_mode.value,
            "underwater_days": (
                (datetime.now() - self.underwater_start_date).days 
                if self.underwater_start_date else 0
            ),
            "active_alerts": len([
                alert for alert in self.alert_history 
                if not alert.acknowledged
            ]),
            "monitoring_active": self.monitoring_active
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """統計情報取得"""
        if not self.equity_history:
            return {}
        
        metrics = self._calculate_drawdown_metrics(datetime.now())
        
        return {
            "total_periods": len(self.drawdown_periods),
            "max_drawdown": metrics.max_drawdown,
            "avg_drawdown": metrics.avg_drawdown,
            "drawdown_frequency": metrics.drawdown_frequency,
            "avg_recovery_time": metrics.avg_recovery_time,
            "max_underwater_days": metrics.max_underwater_days,
            "peak_to_trough_ratio": metrics.peak_to_trough_ratio,
            "recovery_factor": metrics.recovery_factor,
            "total_alerts": len(self.alert_history),
            "recovery_attempts": len(self.recovery_history)
        }
    
    def export_data(self, filepath: str) -> bool:
        """データエクスポート"""
        try:
            export_data = {
                "config": self.config,
                "thresholds": self.thresholds,
                "equity_history": [
                    {"timestamp": ts.isoformat(), "equity": eq}
                    for ts, eq in self.equity_history
                ],
                "drawdown_periods": [
                    asdict(period) for period in self.drawdown_periods
                ],
                "alert_history": [
                    asdict(alert) for alert in self.alert_history
                ],
                "recovery_history": self.recovery_history,
                "current_status": self.get_current_status(),
                "statistics": self.get_statistics()
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False, default=str)
            
            logger.info(f"データエクスポート完了: {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"データエクスポートエラー: {e}")
            return False


def create_drawdown_manager(config: Optional[Dict[str, Any]] = None) -> DrawdownManager:
    """ドローダウンマネージャー作成"""
    return DrawdownManager(config)


# 使用例
if __name__ == "__main__":
    # 設定
    config = {
        "warning_threshold": 0.05,
        "critical_threshold": 0.10,
        "emergency_threshold": 0.15,
        "max_drawdown": 0.20
    }
    
    # ドローダウンマネージャー作成
    manager = create_drawdown_manager(config)
    
    # コールバック関数設定
    def on_drawdown_warning(data):
        print(f"警告: ドローダウン {data['current_drawdown']:.2%}")
    
    def on_drawdown_critical(data):
        print(f"危険: ドローダウン {data['current_drawdown']:.2%}")
    
    manager.add_callback("drawdown_warning", on_drawdown_warning)
    manager.add_callback("drawdown_critical", on_drawdown_critical)
    
    # 監視開始
    manager.start_monitoring(interval_seconds=30)
    
    # サンプルデータ
    equity_values = [100000, 95000, 90000, 85000, 88000, 92000, 98000, 102000]
    
    for i, equity in enumerate(equity_values):
        timestamp = datetime.now() - timedelta(days=len(equity_values)-i-1)
        metrics = manager.update_equity(equity, timestamp)
        
        print(f"日付: {timestamp.date()}, 資産: {equity:,}, "
              f"ドローダウン: {metrics.current_drawdown:.2%}, "
              f"レベル: {manager.current_level.value}")
    
    # 統計情報表示
    stats = manager.get_statistics()
    print(f"\n統計情報:")
    print(f"最大ドローダウン: {stats.get('max_drawdown', 0):.2%}")
    print(f"平均ドローダウン: {stats.get('avg_drawdown', 0):.2%}")
    
    # 監視停止
    time.sleep(2)
    manager.stop_monitoring() 