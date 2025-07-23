#!/usr/bin/env python3
"""
ドローダウンマネージャー デモスクリプト - ステップ62

ドローダウン管理システムの使用方法を示すデモ
"""

import sys
import os
import time
import random
from datetime import datetime, timedelta

# パスの設定
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.cfd_bot.core.drawdown_manager import (
    DrawdownManager, DrawdownLevel, RecoveryMode,
    create_drawdown_manager
)


def demo_basic_usage():
    """基本的な使用方法のデモ"""
    print("=" * 60)
    print("ドローダウンマネージャー - 基本使用方法デモ")
    print("=" * 60)
    
    # 設定
    config = {
        "warning_threshold": 0.05,   # 5%で警告
        "critical_threshold": 0.10,  # 10%で危険
        "emergency_threshold": 0.15, # 15%で緊急
        "max_drawdown": 0.20        # 20%で最大
    }
    
    # ドローダウンマネージャー作成
    manager = create_drawdown_manager(config)
    
    print(f"初期設定:")
    print(f"  警告閾値: {config['warning_threshold']:.1%}")
    print(f"  危険閾値: {config['critical_threshold']:.1%}")
    print(f"  緊急閾値: {config['emergency_threshold']:.1%}")
    
    # サンプル資産価値データ
    initial_equity = 1000000  # 100万円
    equity_changes = [
        0.00,   # 開始
        -0.02,  # -2%
        -0.03,  # -3%
        -0.06,  # -6% (警告レベル)
        -0.08,  # -8%
        -0.12,  # -12% (危険レベル)
        -0.09,  # -9% (回復開始)
        -0.04,  # -4% (警告レベル以下)
        -0.01,  # -1%
        0.02,   # +2% (新しいピーク)
    ]
    
    print(f"\n資産価値の変化をシミュレーション:")
    print(f"初期資産: {initial_equity:,}円")
    
    for i, change in enumerate(equity_changes):
        equity = initial_equity * (1 + change)
        timestamp = datetime.now() - timedelta(days=len(equity_changes)-i-1)
        
        # ドローダウン更新
        metrics = manager.update_equity(equity, timestamp)
        
        # 結果表示
        status_icon = {
            DrawdownLevel.NORMAL: "✅",
            DrawdownLevel.WARNING: "⚠️",
            DrawdownLevel.CRITICAL: "🚨",
            DrawdownLevel.EMERGENCY: "🔥"
        }.get(manager.current_level, "❓")
        
        print(f"  {i+1:2d}日目: {equity:8,.0f}円 "
              f"({change:+.1%}) - DD:{metrics.current_drawdown:6.2%} "
              f"{status_icon} {manager.current_level.value.upper()}")
    
    # 最終統計
    stats = manager.get_statistics()
    print(f"\n最終統計:")
    print(f"  最大ドローダウン: {stats.get('max_drawdown', 0):.2%}")
    print(f"  平均ドローダウン: {stats.get('avg_drawdown', 0):.2%}")
    print(f"  総アラート数: {stats.get('total_alerts', 0)}")


def demo_callback_system():
    """コールバックシステムのデモ"""
    print("\n" + "=" * 60)
    print("コールバックシステム デモ")
    print("=" * 60)
    
    manager = create_drawdown_manager()
    
    # コールバック関数定義
    def on_drawdown_warning(data):
        print(f"🟡 警告コールバック: ドローダウン {data['current_drawdown']:.2%} "
              f"(閾値: {data['alert'].threshold:.2%})")
    
    def on_drawdown_critical(data):
        print(f"🔴 危険コールバック: ドローダウン {data['current_drawdown']:.2%}")
        print(f"   推奨アクション: {data['alert'].recommended_action}")
    
    def on_peak_updated(data):
        print(f"📈 新ピーク: {data['old_peak']:,.0f} → {data['new_peak']:,.0f}")
    
    def on_recovery_started(data):
        print(f"🔄 回復開始: {data['mode']} モード (目標: {data['target']:.2%})")
    
    # コールバック登録
    manager.add_callback("drawdown_warning", on_drawdown_warning)
    manager.add_callback("drawdown_critical", on_drawdown_critical)
    manager.add_callback("peak_updated", on_peak_updated)
    manager.add_callback("recovery_started", on_recovery_started)
    
    print("コールバック関数を登録しました")
    
    # ドローダウンシナリオ
    equity_values = [100000, 95000, 88000, 92000, 105000]
    
    print(f"\nドローダウンシナリオ実行:")
    for equity in equity_values:
        manager.update_equity(equity)
        time.sleep(0.1)  # 視覚効果のため


def demo_recovery_strategies():
    """回復戦略のデモ"""
    print("\n" + "=" * 60)
    print("回復戦略 デモ")
    print("=" * 60)
    
    manager = create_drawdown_manager()
    
    # 各回復戦略の表示
    print("利用可能な回復戦略:")
    for mode in RecoveryMode:
        strategy = manager.recovery_strategies[mode]
        print(f"\n{mode.value.upper()}モード:")
        print(f"  ポジションサイズ倍率: {strategy.position_size_multiplier:.1f}")
        print(f"  リスク削減係数: {strategy.risk_reduction_factor:.1f}")
        print(f"  エントリー閾値倍率: {strategy.entry_threshold_multiplier:.1f}")
        print(f"  最大ポジション数: {strategy.max_positions}")
        print(f"  回復目標: {strategy.recovery_target:.2%}")
        print(f"  タイムアウト: {strategy.timeout_hours}時間")
    
    # 回復戦略の切り替えデモ
    print(f"\n回復戦略切り替えデモ:")
    
    # ドローダウン発生
    manager.update_equity(100000)  # 初期
    manager.update_equity(85000)   # -15% (緊急レベル)
    
    current_strategy = manager.get_recovery_strategy()
    print(f"現在の戦略: {current_strategy.mode.value}")
    print(f"ポジションサイズ倍率: {current_strategy.position_size_multiplier}")
    
    # 手動で回復モード開始
    manager.start_recovery_mode(RecoveryMode.AGGRESSIVE, target=0.02)
    
    # 回復完了チェック
    manager.update_equity(98000)  # 回復
    recovery_completed = manager.check_recovery_completion()
    print(f"回復完了: {recovery_completed}")


def demo_monitoring_system():
    """監視システムのデモ"""
    print("\n" + "=" * 60)
    print("監視システム デモ")
    print("=" * 60)
    
    manager = create_drawdown_manager()
    
    # 監視コールバック
    def on_monitoring_alert(data):
        print(f"📊 監視アラート: {data}")
    
    manager.add_callback("drawdown_warning", on_monitoring_alert)
    
    print("監視システム開始...")
    manager.start_monitoring(interval_seconds=1)
    
    # リアルタイムデータシミュレーション
    base_equity = 100000
    for i in range(10):
        # ランダムな価格変動
        change = random.uniform(-0.02, 0.02)  # ±2%
        equity = base_equity * (1 + change)
        
        manager.update_equity(equity)
        
        status = manager.get_current_status()
        print(f"時刻 {i+1:2d}: 資産={equity:8,.0f} "
              f"DD={status['current_drawdown']:6.2%} "
              f"レベル={status['current_level']}")
        
        time.sleep(0.5)
    
    print("監視システム停止...")
    manager.stop_monitoring()


def demo_data_export():
    """データエクスポートのデモ"""
    print("\n" + "=" * 60)
    print("データエクスポート デモ")
    print("=" * 60)
    
    manager = create_drawdown_manager()
    
    # サンプルデータ作成
    equity_values = [100000, 95000, 90000, 88000, 92000, 98000]
    
    for equity in equity_values:
        manager.update_equity(equity)
    
    # データエクスポート
    export_file = "data/drawdown_export_demo.json"
    os.makedirs(os.path.dirname(export_file), exist_ok=True)
    
    success = manager.export_data(export_file)
    
    if success:
        print(f"✅ データエクスポート成功: {export_file}")
        
        # ファイルサイズ確認
        file_size = os.path.getsize(export_file)
        print(f"   ファイルサイズ: {file_size:,} bytes")
        
        # 統計情報表示
        stats = manager.get_statistics()
        print(f"   エクスポート統計:")
        print(f"     資産価値履歴: {len(manager.equity_history)}件")
        print(f"     アラート履歴: {stats.get('total_alerts', 0)}件")
        print(f"     最大ドローダウン: {stats.get('max_drawdown', 0):.2%}")
    else:
        print("❌ データエクスポート失敗")


def demo_stress_test():
    """ストレステストのデモ"""
    print("\n" + "=" * 60)
    print("ストレステスト デモ")
    print("=" * 60)
    
    manager = create_drawdown_manager()
    
    # 極端なドローダウンシナリオ
    print("極端なドローダウンシナリオ:")
    
    initial_equity = 1000000
    crash_scenario = [
        1.00,   # 開始
        0.95,   # -5%
        0.85,   # -15%
        0.70,   # -30%
        0.60,   # -40%
        0.50,   # -50% (極端なドローダウン)
        0.55,   # 小幅回復
        0.65,   # 回復継続
        0.80,   # 大幅回復
        0.90,   # ほぼ回復
        1.05,   # 新高値
    ]
    
    alert_count = 0
    for i, multiplier in enumerate(crash_scenario):
        equity = initial_equity * multiplier
        metrics = manager.update_equity(equity)
        
        # アラート数カウント
        new_alerts = len([a for a in manager.alert_history if not a.acknowledged])
        if new_alerts > alert_count:
            alert_count = new_alerts
        
        print(f"  ステップ {i+1:2d}: {equity:8,.0f}円 "
              f"({multiplier-1:+.1%}) - DD:{metrics.current_drawdown:6.2%} "
              f"[{manager.current_level.value}]")
    
    # ストレステスト結果
    stats = manager.get_statistics()
    print(f"\nストレステスト結果:")
    print(f"  最大ドローダウン: {stats.get('max_drawdown', 0):.2%}")
    print(f"  総アラート数: {alert_count}")
    print(f"  ピーク・トラフ比率: {stats.get('peak_to_trough_ratio', 1):.2f}")
    print(f"  回復係数: {stats.get('recovery_factor', 1):.2f}")
    
    # パフォーマンス測定
    start_time = time.time()
    for _ in range(1000):
        equity = initial_equity * random.uniform(0.8, 1.2)
        manager.update_equity(equity)
    
    end_time = time.time()
    processing_time = end_time - start_time
    
    print(f"\nパフォーマンステスト:")
    print(f"  1000回更新時間: {processing_time:.3f}秒")
    print(f"  1回あたり平均: {processing_time/1000*1000:.3f}ms")


def main():
    """メイン関数"""
    print("🚀 ドローダウンマネージャー 包括デモ")
    print(f"実行時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # 各デモ実行
        demo_basic_usage()
        demo_callback_system()
        demo_recovery_strategies()
        demo_monitoring_system()
        demo_data_export()
        demo_stress_test()
        
        print("\n" + "=" * 60)
        print("✅ 全デモ完了")
        print("=" * 60)
        
        print(f"\n📊 ドローダウンマネージャーの主要機能:")
        print(f"  ✅ リアルタイムドローダウン監視")
        print(f"  ✅ 4段階のアラートレベル")
        print(f"  ✅ 4種類の回復戦略")
        print(f"  ✅ コールバックシステム")
        print(f"  ✅ 包括的統計分析")
        print(f"  ✅ データエクスポート")
        print(f"  ✅ 高パフォーマンス処理")
        
    except KeyboardInterrupt:
        print("\n\n⚠️ デモが中断されました")
    except Exception as e:
        print(f"\n❌ エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main() 