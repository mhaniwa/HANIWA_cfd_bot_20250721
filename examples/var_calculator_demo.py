#!/usr/bin/env python3
"""
VaR Calculator Demo Script

HANIWA CFD BOT - VaR計算システムの包括的なデモンストレーション

このスクリプトは以下の機能をデモンストレーションします：
1. ヒストリカルVaR計算
2. パラメトリックVaR計算
3. モンテカルロVaR計算
4. ハイブリッドVaR計算
5. ポートフォリオVaR計算
6. VaRモデル検証

Author: HANIWA
Date: 2025-01-25
Version: 1.0.0
"""

import sys
import os
import numpy as np
from datetime import datetime

# プロジェクトルートをパスに追加
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.cfd_bot.core.var_calculator import (
    VaRCalculator,
    create_sample_data
)


def print_separator(title: str = ""):
    """セクション区切り線を印刷"""
    if title:
        print("\n" + "=" * 60)
        print("  {}".format(title))
        print("=" * 60)
    else:
        print("-" * 60)


def print_var_result(result, title: str = ""):
    """VaR計算結果を整形して印刷"""
    if title:
        print("\n📊 {}".format(title))
        print_separator()

    print("手法: {}".format(result.method))
    print("信頼水準: {:.1%}".format(result.confidence_level))
    print("ポートフォリオ価値: {:.0f}円".format(result.portfolio_value))
    print("データポイント数: {}".format(result.data_points))
    print()
    print("💰 VaR: {:.0f}円 ({:.2f}%)".format(
        result.var_value, result.var_percentage
    ))
    print("💰 CVaR: {:.0f}円 ({:.2f}%)".format(
        result.cvar_value, result.cvar_percentage
    ))
    print("💰 期待ショートフォール: {:.0f}円".format(result.expected_shortfall))
    print()
    print("📈 統計情報:")
    print("  ボラティリティ: {:.4f} ({:.2%})".format(
        result.volatility, result.volatility
    ))
    print("  歪度: {:.4f}".format(result.skewness))
    print("  尖度: {:.4f}".format(result.kurtosis))

    if result.additional_stats:
        print("\n📋 追加統計:")
        for key, value in result.additional_stats.items():
            if isinstance(value, dict):
                print("  {}:".format(key))
                for sub_key, sub_value in value.items():
                    print("    {}: {}".format(sub_key, sub_value))
            else:
                print("  {}: {}".format(key, value))


def demo_historical_var():
    """ヒストリカルVaRデモ"""
    print_separator("🔍 ヒストリカルVaR計算デモ")

    calculator = VaRCalculator(portfolio_value=1400000)  # 140万円
    sample_data = create_sample_data(days=252)  # 1年分のデータ

    # 95%信頼水準でVaR計算
    result_95 = calculator.calculate_historical_var(
        sample_data, confidence_level=0.95
    )
    print_var_result(result_95, "ヒストリカルVaR (95%信頼水準)")

    # 99%信頼水準でVaR計算
    result_99 = calculator.calculate_historical_var(
        sample_data, confidence_level=0.99
    )
    print_var_result(result_99, "ヒストリカルVaR (99%信頼水準)")

    return [result_95, result_99]


def demo_parametric_var():
    """パラメトリックVaRデモ"""
    print_separator("📊 パラメトリックVaR計算デモ")

    calculator = VaRCalculator(portfolio_value=1400000)
    sample_data = create_sample_data(days=252)

    # 正規分布VaR
    result_normal = calculator.calculate_parametric_var(
        sample_data, confidence_level=0.95, distribution="normal"
    )
    print_var_result(result_normal, "パラメトリックVaR (正規分布)")

    # t分布VaR
    result_t = calculator.calculate_parametric_var(
        sample_data, confidence_level=0.95, distribution="t"
    )
    print_var_result(result_t, "パラメトリックVaR (t分布)")

    return [result_normal, result_t]


def demo_monte_carlo_var():
    """モンテカルロVaRデモ"""
    print_separator("🎲 モンテカルロVaR計算デモ")

    calculator = VaRCalculator(portfolio_value=1400000)
    sample_data = create_sample_data(days=252)

    # 10,000回シミュレーション
    result_10k = calculator.calculate_monte_carlo_var(
        sample_data, confidence_level=0.95, simulations=10000
    )
    print_var_result(result_10k, "モンテカルロVaR (10,000回シミュレーション)")

    # 50,000回シミュレーション
    result_50k = calculator.calculate_monte_carlo_var(
        sample_data, confidence_level=0.95, simulations=50000
    )
    print_var_result(result_50k, "モンテカルロVaR (50,000回シミュレーション)")

    return [result_10k, result_50k]


def demo_hybrid_var():
    """ハイブリッドVaRデモ"""
    print_separator("🔗 ハイブリッドVaR計算デモ")

    calculator = VaRCalculator(portfolio_value=1400000)
    sample_data = create_sample_data(days=252)

    # デフォルト重み
    result_default = calculator.calculate_hybrid_var(
        sample_data, confidence_level=0.95
    )
    print_var_result(result_default, "ハイブリッドVaR (デフォルト重み)")

    # カスタム重み
    custom_weights = {
        "historical": 0.5,
        "parametric": 0.3,
        "monte_carlo": 0.2
    }
    result_custom = calculator.calculate_hybrid_var(
        sample_data, confidence_level=0.95, weights=custom_weights
    )
    print_var_result(result_custom, "ハイブリッドVaR (カスタム重み)")

    return [result_default, result_custom]


def demo_portfolio_var():
    """ポートフォリオVaRデモ"""
    print_separator("📈 ポートフォリオVaR計算デモ")

    calculator = VaRCalculator(portfolio_value=2000000)  # 200万円

    # マルチアセットポートフォリオデータ生成
    np.random.seed(42)
    days = 252

    # 株式（高ボラティリティ）
    stock_returns = np.random.normal(0.0008, 0.025, days).tolist()

    # 債券（低ボラティリティ）
    bond_returns = np.random.normal(0.0003, 0.008, days).tolist()

    # 商品（中ボラティリティ、株式と負の相関）
    commodity_base = np.random.normal(0.0005, 0.018, days)
    stock_array = np.array(stock_returns)
    commodity_returns = (commodity_base - 0.3 * stock_array).tolist()

    assets_returns = {
        "株式": stock_returns,
        "債券": bond_returns,
        "商品": commodity_returns
    }

    weights = {
        "株式": 0.6,
        "債券": 0.3,
        "商品": 0.1
    }

    # ポートフォリオVaR計算
    portfolio_result = calculator.calculate_portfolio_var(
        assets_returns, weights, confidence_level=0.95
    )

    print("\n📊 ポートフォリオVaR計算結果")
    print_separator()
    print("ポートフォリオ構成:")
    for asset, weight in weights.items():
        print("  {}: {:.1%}".format(asset, weight))

    print("\n💰 個別資産VaR:")
    for asset, var_value in portfolio_result.individual_vars.items():
        print("  {}: {:.0f}円".format(asset, var_value))

    individual_sum = sum(portfolio_result.individual_vars.values())
    print("  合計: {:.0f}円".format(individual_sum))

    print("\n💰 ポートフォリオVaR: {:.0f}円".format(
        portfolio_result.portfolio_var
    ))
    print("💰 分散効果: {:.0f}円 ({:.1%}削減)".format(
        portfolio_result.diversification_benefit,
        portfolio_result.diversification_benefit / individual_sum
    ))

    print("\n📊 相関行列:")
    assets = list(assets_returns.keys())
    for i, asset1 in enumerate(assets):
        row = "  {}:".format(asset1)
        for j, asset2 in enumerate(assets):
            correlation = portfolio_result.correlation_matrix[i][j]
            row += " {:.3f}".format(correlation)
        print(row)

    print("\n📈 ポートフォリオボラティリティ: {:.4f} ({:.2%})".format(
        portfolio_result.portfolio_volatility,
        portfolio_result.portfolio_volatility
    ))

    return portfolio_result


def demo_var_validation():
    """VaRモデル検証デモ"""
    print_separator("✅ VaRモデル検証デモ")

    calculator = VaRCalculator(portfolio_value=1400000)

    # テスト用データ生成
    np.random.seed(42)
    days = 252
    returns = np.random.normal(0.001, 0.02, days).tolist()

    # VaR推定値生成（実際の運用では過去のVaR予測値を使用）
    var_estimates = []
    for i in range(days):
        # 簡単なローリングウィンドウVaR推定
        if i < 30:
            var_est = 0.025  # 初期値
        else:
            window_returns = returns[i-30:i]
            var_est = abs(np.percentile(window_returns, 5))
        var_estimates.append(var_est)

    # バックテスト実行
    validation_result = calculator.validate_var_model(
        returns, var_estimates, confidence_level=0.95, method="historical"
    )

    print("\n📊 VaRモデル検証結果")
    print_separator()
    print("手法: {}".format(validation_result.method))
    print("信頼水準: {:.1%}".format(validation_result.confidence_level))
    print("観測期間: {}日".format(validation_result.total_observations))
    print()
    print("💥 VaR違反:")
    print("  実際の違反回数: {}回".format(validation_result.violations))
    print("  期待違反回数: {}回".format(validation_result.expected_violations))
    print("  違反率: {:.2%}".format(validation_result.violation_rate))
    print("  期待違反率: {:.2%}".format(
        1 - validation_result.confidence_level))
    print()
    print("📊 Kupiec検定:")
    print("  検定統計量: {:.4f}".format(validation_result.kupiec_statistic))
    print("  p値: {:.4f}".format(validation_result.kupiec_p_value))
    print("  モデル妥当性: {}".format(
        "✅ 妥当" if validation_result.is_model_valid else "❌ 要改善"))

    return validation_result


def demo_comparison():
    """各手法の比較デモ"""
    print_separator("🔍 VaR計算手法比較")

    calculator = VaRCalculator(portfolio_value=1400000)
    sample_data = create_sample_data(days=252)
    confidence_level = 0.95

    # 各手法でVaR計算
    hist_result = calculator.calculate_historical_var(
        sample_data, confidence_level
    )
    param_result = calculator.calculate_parametric_var(
        sample_data, confidence_level, "normal"
    )
    mc_result = calculator.calculate_monte_carlo_var(
        sample_data, confidence_level, 10000
    )
    hybrid_result = calculator.calculate_hybrid_var(
        sample_data, confidence_level
    )

    results = [hist_result, param_result, mc_result, hybrid_result]

    print("\n📊 VaR計算結果比較 (95%信頼水準)")
    print_separator()
    print("{:<20} {:>12} {:>10} {:>12} {:>10}".format(
        "手法", "VaR(円)", "VaR(%)", "CVaR(円)", "CVaR(%)"))
    print("-" * 70)

    for result in results:
        method_name = result.method.replace(" VaR", "").replace(
            " (Normal)", "")
        print("{:<20} {:>12,.0f} {:>9.2f}% {:>12,.0f} {:>9.2f}%".format(
            method_name,
            result.var_value,
            result.var_percentage,
            result.cvar_value,
            result.cvar_percentage))

    # 統計情報比較
    print("\n📈 統計情報比較")
    print_separator()
    print("{:<20} {:>12} {:>10} {:>10}".format(
        "手法", "ボラティリティ", "歪度", "尖度"))
    print("-" * 60)

    for result in results:
        method_name = result.method.replace(" VaR", "").replace(
            " (Normal)", "")
        print("{:<20} {:>11.4f} {:>10.4f} {:>10.4f}".format(
            method_name,
            result.volatility,
            result.skewness,
            result.kurtosis))

    return results


def export_demo_results(all_results):
    """デモ結果をエクスポート"""
    print_separator("💾 結果エクスポート")

    calculator = VaRCalculator()

    # 結果をまとめてエクスポート
    export_data = {
        "demo_date": datetime.now().isoformat(),
        "portfolio_value": 1400000,
        "results": []
    }

    for result_group in all_results:
        if isinstance(result_group, list):
            for result in result_group:
                if hasattr(result, 'to_dict'):
                    export_data["results"].append(result.to_dict())
        elif hasattr(result_group, 'to_dict'):
            export_data["results"].append(result_group.to_dict())

    filename = "var_demo_results_{}.json".format(
        datetime.now().strftime("%Y%m%d_%H%M%S")
    )

    success = calculator.export_results(export_data, filename)
    if success:
        print("✅ デモ結果をエクスポートしました: {}".format(filename))
    else:
        print("❌ エクスポートに失敗しました")

    return success


def main():
    """メイン実行関数"""
    print("🚀 HANIWA CFD BOT - VaR計算システム デモ")
    print("=" * 60)
    print("このデモでは、4つのVaR計算手法とポートフォリオVaR、")
    print("モデル検証機能を包括的にテストします。")

    all_results = []

    try:
        # 各デモ実行
        hist_results = demo_historical_var()
        all_results.append(hist_results)

        param_results = demo_parametric_var()
        all_results.append(param_results)

        mc_results = demo_monte_carlo_var()
        all_results.append(mc_results)

        hybrid_results = demo_hybrid_var()
        all_results.append(hybrid_results)

        portfolio_result = demo_portfolio_var()
        all_results.append(portfolio_result)

        validation_result = demo_var_validation()
        all_results.append(validation_result)

        comparison_results = demo_comparison()
        all_results.append(comparison_results)

        # 結果エクスポート
        export_demo_results(all_results)

        print_separator("🎉 デモ完了")
        print("✅ 全てのVaR計算デモが正常に完了しました！")
        print()
        print("📊 実行されたデモ:")
        print("  • ヒストリカルVaR計算")
        print("  • パラメトリックVaR計算 (正規分布・t分布)")
        print("  • モンテカルロVaR計算")
        print("  • ハイブリッドVaR計算")
        print("  • ポートフォリオVaR計算 (相関考慮)")
        print("  • VaRモデル検証 (バックテスト)")
        print("  • 手法間比較分析")
        print("  • 結果エクスポート")
        print()
        print("🎯 VaR計算システムは本格運用準備完了です！")

    except Exception as e:
        print("❌ デモ実行中にエラーが発生しました: {}".format(str(e)))
        return False

    return True


if __name__ == "__main__":
    success = main()
    if not success:
        sys.exit(1) 