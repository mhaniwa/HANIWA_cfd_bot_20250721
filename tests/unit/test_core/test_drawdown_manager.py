#!/usr/bin/env python3
"""
ドローダウンマネージャー 単体テスト - ステップ62

DrawdownManagerクラスの包括的なテスト
"""

import unittest
import tempfile
import os
import json
import time
import threading
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '../../..'))

from src.cfd_bot.core.drawdown_manager import (
    DrawdownManager, DrawdownLevel, RecoveryMode,
    DrawdownPeriod, DrawdownMetrics, DrawdownAlert, RecoveryStrategy,
    create_drawdown_manager
)


class TestDrawdownManager(unittest.TestCase):
    """ドローダウンマネージャーテストクラス"""
    
    def setUp(self):
        """テスト前準備"""
        self.config = {
            "warning_threshold": 0.05,
            "critical_threshold": 0.10,
            "emergency_threshold": 0.15,
            "max_drawdown": 0.20
        }
        self.manager = DrawdownManager(self.config)
    
    def tearDown(self):
        """テスト後清理"""
        if self.manager.monitoring_active:
            self.manager.stop_monitoring()
    
    def test_initialization(self):
        """初期化テスト"""
        # 基本設定確認
        self.assertEqual(self.manager.thresholds["warning"], 0.05)
        self.assertEqual(self.manager.thresholds["critical"], 0.10)
        self.assertEqual(self.manager.thresholds["emergency"], 0.15)
        
        # 初期状態確認
        self.assertEqual(self.manager.current_peak, 0.0)
        self.assertEqual(self.manager.current_drawdown, 0.0)
        self.assertEqual(self.manager.current_level, DrawdownLevel.NORMAL)
        self.assertEqual(self.manager.current_recovery_mode, RecoveryMode.NORMAL)
        
        # 履歴初期化確認
        self.assertEqual(len(self.manager.equity_history), 0)
        self.assertEqual(len(self.manager.drawdown_periods), 0)
        self.assertEqual(len(self.manager.alert_history), 0)
    
    def test_create_drawdown_manager(self):
        """ファクトリー関数テスト"""
        manager = create_drawdown_manager(self.config)
        self.assertIsInstance(manager, DrawdownManager)
        self.assertEqual(manager.thresholds["warning"], 0.05)
    
    def test_update_equity_basic(self):
        """基本的な資産価値更新テスト"""
        # 初期値設定
        metrics = self.manager.update_equity(100000)
        
        self.assertEqual(self.manager.current_peak, 100000)
        self.assertEqual(self.manager.current_drawdown, 0.0)
        self.assertEqual(self.manager.current_level, DrawdownLevel.NORMAL)
        self.assertIsInstance(metrics, DrawdownMetrics)
        
        # 履歴確認
        self.assertEqual(len(self.manager.equity_history), 1)
        self.assertEqual(self.manager.equity_history[0][1], 100000)
    
    def test_drawdown_calculation(self):
        """ドローダウン計算テスト"""
        # ピーク設定
        self.manager.update_equity(100000)
        
        # ドローダウン発生
        metrics = self.manager.update_equity(95000)
        self.assertAlmostEqual(self.manager.current_drawdown, 0.05, places=3)
        self.assertEqual(self.manager.current_level, DrawdownLevel.WARNING)
        
        # さらなるドローダウン
        metrics = self.manager.update_equity(85000)
        self.assertAlmostEqual(self.manager.current_drawdown, 0.15, places=3)
        self.assertEqual(self.manager.current_level, DrawdownLevel.EMERGENCY)
    
    def test_peak_update(self):
        """ピーク更新テスト"""
        # 初期ピーク
        self.manager.update_equity(100000)
        self.assertEqual(self.manager.current_peak, 100000)
        
        # ドローダウン
        self.manager.update_equity(95000)
        self.assertEqual(self.manager.current_peak, 100000)  # ピーク変わらず
        
        # 新しいピーク
        self.manager.update_equity(105000)
        self.assertEqual(self.manager.current_peak, 105000)
        self.assertEqual(self.manager.current_drawdown, 0.0)  # ドローダウンリセット
    
    def test_drawdown_levels(self):
        """ドローダウンレベル判定テスト"""
        self.manager.update_equity(100000)
        
        # 正常レベル
        self.manager.update_equity(97000)  # -3%
        self.assertEqual(self.manager.current_level, DrawdownLevel.NORMAL)
        
        # 警告レベル
        self.manager.update_equity(94000)  # -6%
        self.assertEqual(self.manager.current_level, DrawdownLevel.WARNING)
        
        # 危険レベル
        self.manager.update_equity(88000)  # -12%
        self.assertEqual(self.manager.current_level, DrawdownLevel.CRITICAL)
        
        # 緊急レベル
        self.manager.update_equity(82000)  # -18%
        self.assertEqual(self.manager.current_level, DrawdownLevel.EMERGENCY)
    
    def test_alert_generation(self):
        """アラート生成テスト"""
        self.manager.update_equity(100000)
        
        # 警告アラート
        self.manager.update_equity(94000)  # -6%
        self.assertEqual(len(self.manager.alert_history), 1)
        
        alert = self.manager.alert_history[0]
        self.assertEqual(alert.level, DrawdownLevel.WARNING)
        self.assertAlmostEqual(alert.current_drawdown, 0.06, places=3)
        self.assertEqual(alert.threshold, 0.05)
        self.assertFalse(alert.acknowledged)
        
        # 危険アラート
        self.manager.update_equity(88000)  # -12%
        self.assertEqual(len(self.manager.alert_history), 2)
        
        critical_alert = self.manager.alert_history[1]
        self.assertEqual(critical_alert.level, DrawdownLevel.CRITICAL)
    
    def test_recovery_strategy_adjustment(self):
        """回復戦略調整テスト"""
        self.manager.update_equity(100000)
        
        # 警告レベル → 保守的モード
        self.manager.update_equity(94000)
        self.assertEqual(self.manager.current_recovery_mode, RecoveryMode.CONSERVATIVE)
        
        # 危険レベル → 防御的モード
        self.manager.update_equity(88000)
        self.assertEqual(self.manager.current_recovery_mode, RecoveryMode.DEFENSIVE)
        
        # 緊急レベル → 防御的モード維持
        self.manager.update_equity(82000)
        self.assertEqual(self.manager.current_recovery_mode, RecoveryMode.DEFENSIVE)
    
    def test_recovery_strategies(self):
        """回復戦略テスト"""
        # 各戦略の存在確認
        for mode in RecoveryMode:
            self.assertIn(mode, self.manager.recovery_strategies)
            strategy = self.manager.recovery_strategies[mode]
            self.assertIsInstance(strategy, RecoveryStrategy)
        
        # 通常戦略
        normal_strategy = self.manager.recovery_strategies[RecoveryMode.NORMAL]
        self.assertEqual(normal_strategy.position_size_multiplier, 1.0)
        self.assertEqual(normal_strategy.max_positions, 10)
        
        # 保守的戦略
        conservative_strategy = self.manager.recovery_strategies[RecoveryMode.CONSERVATIVE]
        self.assertEqual(conservative_strategy.position_size_multiplier, 0.5)
        self.assertEqual(conservative_strategy.max_positions, 5)
        
        # 積極的戦略
        aggressive_strategy = self.manager.recovery_strategies[RecoveryMode.AGGRESSIVE]
        self.assertEqual(aggressive_strategy.position_size_multiplier, 1.5)
        self.assertEqual(aggressive_strategy.max_positions, 15)
        
        # 防御的戦略
        defensive_strategy = self.manager.recovery_strategies[RecoveryMode.DEFENSIVE]
        self.assertEqual(defensive_strategy.position_size_multiplier, 0.3)
        self.assertEqual(defensive_strategy.max_positions, 3)
    
    def test_start_recovery_mode(self):
        """回復モード開始テスト"""
        # 積極的モード開始
        success = self.manager.start_recovery_mode(RecoveryMode.AGGRESSIVE, target=0.02)
        self.assertTrue(success)
        self.assertEqual(self.manager.current_recovery_mode, RecoveryMode.AGGRESSIVE)
        
        # 回復履歴確認
        self.assertEqual(len(self.manager.recovery_history), 1)
        recovery_record = self.manager.recovery_history[0]
        self.assertEqual(recovery_record["mode"], "aggressive")
        self.assertEqual(recovery_record["target"], 0.02)
        
        # 不正なモードテスト
        with patch.object(self.manager, 'recovery_strategies', {}):
            success = self.manager.start_recovery_mode(RecoveryMode.NORMAL)
            self.assertFalse(success)
    
    def test_recovery_completion(self):
        """回復完了テスト"""
        self.manager.update_equity(100000)
        self.manager.update_equity(90000)  # -10%
        
        # 回復モード開始
        self.manager.start_recovery_mode(RecoveryMode.CONSERVATIVE, target=0.05)
        
        # 回復未完了
        self.manager.update_equity(92000)  # -8% (目標5%より大)
        completed = self.manager.check_recovery_completion()
        self.assertFalse(completed)
        
        # 回復完了 - より明確に目標以下にする
        self.manager.update_equity(97000)  # -3% (目標5%以下)
        completed = self.manager.check_recovery_completion()
        self.assertTrue(completed)
        self.assertEqual(self.manager.current_recovery_mode, RecoveryMode.NORMAL)
        
        # 回復履歴更新確認
        recovery_record = self.manager.recovery_history[0]
        self.assertTrue(recovery_record.get("success", False))
        self.assertIn("end_time", recovery_record)
    
    def test_recovery_timeout(self):
        """回復タイムアウトテスト"""
        self.manager.update_equity(100000)
        self.manager.update_equity(90000)
        
        # 短いタイムアウトで回復モード開始
        strategy = self.manager.recovery_strategies[RecoveryMode.AGGRESSIVE]
        original_timeout = strategy.timeout_hours
        strategy.timeout_hours = 0.001  # 0.001時間（3.6秒）
        
        self.manager.start_recovery_mode(RecoveryMode.AGGRESSIVE, target=0.01)
        
        # タイムアウト待機
        time.sleep(0.1)
        
        # 回復未完了でタイムアウトチェック
        completed = self.manager.check_recovery_completion()
        self.assertFalse(completed)
        
        # タイムアウト後にモードが変更されることを確認
        self.assertEqual(self.manager.current_recovery_mode, RecoveryMode.CONSERVATIVE)
        
        # 元の設定に戻す
        strategy.timeout_hours = original_timeout
    
    def test_callback_system(self):
        """コールバックシステムテスト"""
        callback_data = []
        
        def warning_callback(data):
            callback_data.append(("warning", data))
        
        def critical_callback(data):
            callback_data.append(("critical", data))
        
        def peak_callback(data):
            callback_data.append(("peak", data))
        
        # コールバック登録
        self.manager.add_callback("drawdown_warning", warning_callback)
        self.manager.add_callback("drawdown_critical", critical_callback)
        self.manager.add_callback("peak_updated", peak_callback)
        
        # 不正なイベントタイプ
        self.manager.add_callback("invalid_event", lambda x: None)
        
        # コールバック実行テスト
        self.manager.update_equity(100000)  # ピーク更新
        self.manager.update_equity(94000)   # 警告レベル
        self.manager.update_equity(88000)   # 危険レベル
        self.manager.update_equity(105000)  # 新ピーク
        
        # コールバック実行確認
        self.assertGreaterEqual(len(callback_data), 3)
        
        # イベントタイプ確認
        event_types = [data[0] for data in callback_data]
        self.assertIn("peak", event_types)
        self.assertIn("warning", event_types)
        self.assertIn("critical", event_types)
    
    def test_underwater_period_management(self):
        """水面下期間管理テスト"""
        # 初期状態
        self.assertIsNone(self.manager.underwater_start_date)
        
        # ピーク設定
        self.manager.update_equity(100000)
        
        # 水面下期間開始
        self.manager.update_equity(95000)
        self.assertIsNotNone(self.manager.underwater_start_date)
        
        # 水面下継続
        self.manager.update_equity(90000)
        self.assertIsNotNone(self.manager.underwater_start_date)
        
        # 水面下期間終了（新ピーク）
        self.manager.update_equity(105000)
        self.assertIsNone(self.manager.underwater_start_date)
    
    def test_drawdown_metrics_calculation(self):
        """ドローダウン指標計算テスト"""
        # サンプルデータ
        equity_values = [100000, 95000, 90000, 85000, 88000, 92000, 98000, 102000]
        
        for equity in equity_values:
            metrics = self.manager.update_equity(equity)
        
        # 指標確認
        self.assertIsInstance(metrics, DrawdownMetrics)
        self.assertGreater(metrics.max_drawdown, 0)
        self.assertGreaterEqual(metrics.current_drawdown, 0)
        self.assertGreaterEqual(metrics.peak_to_trough_ratio, 1.0)
        self.assertGreater(metrics.recovery_factor, 0)
    
    def test_max_drawdown_calculation(self):
        """最大ドローダウン計算テスト"""
        # 複数のドローダウン期間
        equity_sequence = [
            100000, 95000, 90000, 85000,  # -15%ドローダウン
            95000, 100000,                 # 回復
            105000, 98000, 92000, 88000,   # -16%ドローダウン
            95000, 110000                  # 回復・新高値
        ]
        
        for equity in equity_sequence:
            self.manager.update_equity(equity)
        
        max_drawdown = self.manager._calculate_max_drawdown()
        self.assertAlmostEqual(max_drawdown, 0.16, places=2)  # 16%が最大
    
    def test_monitoring_system(self):
        """監視システムテスト"""
        # 監視開始
        self.assertFalse(self.manager.monitoring_active)
        self.manager.start_monitoring(interval_seconds=0.1)
        self.assertTrue(self.manager.monitoring_active)
        self.assertIsNotNone(self.manager.monitoring_thread)
        
        # 監視中の動作
        time.sleep(0.2)
        self.assertTrue(self.manager.monitoring_active)
        
        # 監視停止
        self.manager.stop_monitoring()
        self.assertFalse(self.manager.monitoring_active)
        
        # 重複開始テスト
        self.manager.start_monitoring()
        self.manager.start_monitoring()  # 警告が出るが問題なし
        self.manager.stop_monitoring()
    
    def test_current_status(self):
        """現在状態取得テスト"""
        self.manager.update_equity(100000)
        self.manager.update_equity(90000)  # -10%
        
        status = self.manager.get_current_status()
        
        # 必要なキー確認
        required_keys = [
            "current_drawdown", "current_level", "current_peak",
            "recovery_mode", "underwater_days", "active_alerts",
            "monitoring_active"
        ]
        for key in required_keys:
            self.assertIn(key, status)
        
        # 値確認
        self.assertAlmostEqual(status["current_drawdown"], 0.10, places=2)
        self.assertEqual(status["current_level"], "critical")
        self.assertEqual(status["current_peak"], 100000)
        self.assertGreaterEqual(status["underwater_days"], 0)
    
    def test_statistics(self):
        """統計情報テスト"""
        # データなし状態
        stats = self.manager.get_statistics()
        self.assertEqual(stats, {})
        
        # データありの状態
        equity_values = [100000, 95000, 90000, 95000, 105000]
        for equity in equity_values:
            self.manager.update_equity(equity)
        
        stats = self.manager.get_statistics()
        
        # 統計項目確認
        expected_keys = [
            "total_periods", "max_drawdown", "avg_drawdown",
            "drawdown_frequency", "avg_recovery_time", "max_underwater_days",
            "peak_to_trough_ratio", "recovery_factor", "total_alerts",
            "recovery_attempts"
        ]
        for key in expected_keys:
            self.assertIn(key, stats)
    
    def test_data_export(self):
        """データエクスポートテスト"""
        # サンプルデータ作成
        equity_values = [100000, 95000, 90000, 95000, 105000]
        for equity in equity_values:
            self.manager.update_equity(equity)
        
        # 一時ファイルにエクスポート
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_file = f.name
        
        try:
            # エクスポート実行
            success = self.manager.export_data(temp_file)
            self.assertTrue(success)
            self.assertTrue(os.path.exists(temp_file))
            
            # ファイル内容確認
            with open(temp_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 必要なキー確認
            expected_keys = [
                "config", "thresholds", "equity_history",
                "drawdown_periods", "alert_history", "recovery_history",
                "current_status", "statistics"
            ]
            for key in expected_keys:
                self.assertIn(key, data)
            
            # データ内容確認
            self.assertEqual(len(data["equity_history"]), 5)
            self.assertGreaterEqual(len(data["alert_history"]), 0)
            
        finally:
            # 一時ファイル削除
            if os.path.exists(temp_file):
                os.unlink(temp_file)
        
        # 不正なパスでのエクスポート
        success = self.manager.export_data("/invalid/path/file.json")
        self.assertFalse(success)
    
    def test_equity_history_limit(self):
        """資産価値履歴制限テスト"""
        # 制限を超えるデータ追加
        for i in range(1200):  # 制限は1000
            self.manager.update_equity(100000 + i)
        
        # 履歴サイズ確認
        self.assertEqual(len(self.manager.equity_history), 1000)
        
        # 最新データが保持されていることを確認
        latest_equity = self.manager.equity_history[-1][1]
        self.assertEqual(latest_equity, 101199)
    
    def test_alert_cleanup(self):
        """アラート清理テスト"""
        # 古いアラートを作成
        old_alert = DrawdownAlert(
            level=DrawdownLevel.WARNING,
            message="Test alert",
            current_drawdown=0.06,
            threshold=0.05,
            recommended_action="Test action",
            timestamp=datetime.now() - timedelta(days=35)  # 35日前
        )
        self.manager.alert_history.append(old_alert)
        
        # 新しいアラートを作成
        self.manager.update_equity(100000)
        self.manager.update_equity(94000)  # 警告アラート生成
        
        initial_count = len(self.manager.alert_history)
        
        # 清理実行
        self.manager._cleanup_old_alerts(max_age_days=30)
        
        # 古いアラートが削除されることを確認
        final_count = len(self.manager.alert_history)
        self.assertLess(final_count, initial_count)
        
        # 新しいアラートは残っていることを確認
        remaining_alerts = [
            alert for alert in self.manager.alert_history
            if alert.timestamp > datetime.now() - timedelta(days=30)
        ]
        self.assertGreater(len(remaining_alerts), 0)
    
    def test_error_handling(self):
        """エラーハンドリングテスト"""
        # コールバックエラー
        def error_callback(data):
            raise Exception("Test error")
        
        self.manager.add_callback("drawdown_warning", error_callback)
        
        # エラーが発生してもシステムが継続することを確認
        self.manager.update_equity(100000)
        self.manager.update_equity(94000)  # エラーコールバック実行
        
        # システムは正常に動作し続ける
        self.assertEqual(self.manager.current_level, DrawdownLevel.WARNING)
    
    def test_edge_cases(self):
        """エッジケーステスト"""
        # 新しいマネージャーでテスト（履歴をクリアな状態で開始）
        clean_manager = DrawdownManager()
        
        # ゼロ資産価値
        metrics = clean_manager.update_equity(0)
        self.assertEqual(clean_manager.current_drawdown, 0.0)
        
        # 負の資産価値
        metrics = clean_manager.update_equity(-1000)
        self.assertGreaterEqual(clean_manager.current_drawdown, 0.0)
        
        # 非常に大きな値
        clean_manager.update_equity(1e12)
        self.assertEqual(clean_manager.current_peak, 1e12)
        
        # 同じ値の連続更新（新しいマネージャーで）
        test_manager = DrawdownManager()
        for _ in range(5):
            metrics = test_manager.update_equity(100000)
        self.assertEqual(len(test_manager.equity_history), 5)


class TestDrawdownManagerIntegration(unittest.TestCase):
    """統合テストクラス"""
    
    def test_full_lifecycle(self):
        """完全なライフサイクルテスト"""
        manager = create_drawdown_manager({
            "warning_threshold": 0.05,
            "critical_threshold": 0.10,
            "emergency_threshold": 0.15
        })
        
        callback_events = []
        
        def track_events(event_type):
            def callback(data):
                callback_events.append(event_type)
            return callback
        
        # コールバック登録
        manager.add_callback("drawdown_warning", track_events("warning"))
        manager.add_callback("drawdown_critical", track_events("critical"))
        manager.add_callback("peak_updated", track_events("peak"))
        manager.add_callback("recovery_started", track_events("recovery"))
        
        # 監視開始
        manager.start_monitoring(interval_seconds=0.1)
        
        # シナリオ実行
        scenario = [
            100000,  # 初期ピーク
            95000,   # -5% (警告)
            85000,   # -15% (緊急)
            90000,   # 部分回復
            105000,  # 新ピーク
            98000,   # 小幅下落
            110000   # 最終ピーク
        ]
        
        for equity in scenario:
            manager.update_equity(equity)
            time.sleep(0.05)
        
        # 回復モードテスト
        manager.start_recovery_mode(RecoveryMode.CONSERVATIVE, target=0.02)
        manager.check_recovery_completion()
        
        # 結果確認
        self.assertGreater(len(callback_events), 0)
        self.assertIn("peak", callback_events)
        self.assertIn("warning", callback_events)
        
        # 統計確認
        stats = manager.get_statistics()
        self.assertGreater(stats["max_drawdown"], 0)
        self.assertGreater(stats["total_alerts"], 0)
        
        # 監視停止
        manager.stop_monitoring()
        
        # エクスポートテスト
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            temp_file = f.name
        
        try:
            success = manager.export_data(temp_file)
            self.assertTrue(success)
        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)


def run_performance_test():
    """パフォーマンステスト"""
    print("ドローダウンマネージャー パフォーマンステスト")
    
    manager = create_drawdown_manager()
    
    # 大量データ処理テスト
    import random
    
    start_time = time.time()
    
    for i in range(10000):
        equity = 100000 * (1 + random.uniform(-0.2, 0.2))
        manager.update_equity(equity)
    
    end_time = time.time()
    processing_time = end_time - start_time
    
    print(f"10,000回更新処理時間: {processing_time:.3f}秒")
    print(f"1回あたり平均: {processing_time/10000*1000:.3f}ms")
    
    # メモリ使用量確認
    import sys
    memory_usage = sys.getsizeof(manager.equity_history)
    print(f"履歴メモリ使用量: {memory_usage:,} bytes")
    
    # 統計計算パフォーマンス
    start_time = time.time()
    for _ in range(100):
        stats = manager.get_statistics()
    end_time = time.time()
    
    stats_time = end_time - start_time
    print(f"統計計算100回: {stats_time:.3f}秒")


if __name__ == "__main__":
    # 単体テスト実行
    unittest.main(argv=[''], exit=False, verbosity=2)
    
    # パフォーマンステスト実行
    print("\n" + "="*60)
    run_performance_test() 