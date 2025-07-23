"""
VaR Calculator Unit Tests

VaR計算システムの包括的な単体テスト

テスト範囲:
- ヒストリカルVaR計算
- パラメトリックVaR計算
- モンテカルロVaR計算
- ハイブリッドVaR計算
- ポートフォリオVaR計算
- VaRモデル検証
- エラーハンドリング
- エッジケース

Author: HANIWA
Date: 2025-01-25
Version: 1.0.0
"""

import unittest
import numpy as np
import tempfile
import os
import json
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from src.cfd_bot.core.var_calculator import (
    VaRCalculator,
    VaRResult,
    PortfolioVaRResult,
    VaRValidationResult,
    create_sample_data
)


class TestVaRCalculator(unittest.TestCase):
    """VaR計算システムテストクラス"""

    def setUp(self):
        """テスト前準備"""
        self.calculator = VaRCalculator(portfolio_value=1000000)
        self.sample_returns = [
            -0.05, -0.03, -0.01, 0.01, 0.02, 0.03, -0.02, 0.01, -0.01, 0.02
        ]
        np.random.seed(42)  # 再現性のため

    def test_initialization(self):
        """初期化テスト"""
        calc = VaRCalculator(portfolio_value=500000)
        self.assertEqual(calc.portfolio_value, 500000)

        # デフォルト値テスト
        calc_default = VaRCalculator()
        self.assertEqual(calc_default.portfolio_value, 1000000.0)

    def test_historical_var_basic(self):
        """ヒストリカルVaR基本テスト"""
        result = self.calculator.calculate_historical_var(
            self.sample_returns, confidence_level=0.95
        )

        self.assertIsInstance(result, VaRResult)
        self.assertEqual(result.method, "Historical VaR")
        self.assertEqual(result.confidence_level, 0.95)
        self.assertGreater(result.var_value, 0)
        self.assertGreater(result.cvar_value, 0)
        self.assertEqual(result.portfolio_value, 1000000)
        self.assertEqual(result.data_points, len(self.sample_returns))

    def test_historical_var_different_confidence_levels(self):
        """異なる信頼水準でのヒストリカルVaRテスト"""
        result_90 = self.calculator.calculate_historical_var(
            self.sample_returns, confidence_level=0.90
        )
        result_95 = self.calculator.calculate_historical_var(
            self.sample_returns, confidence_level=0.95
        )
        result_99 = self.calculator.calculate_historical_var(
            self.sample_returns, confidence_level=0.99
        )

        # 信頼水準が高いほどVaRが大きくなることを確認
        self.assertLessEqual(result_90.var_value, result_95.var_value)
        self.assertLessEqual(result_95.var_value, result_99.var_value)

    def test_parametric_var_normal(self):
        """パラメトリックVaR（正規分布）テスト"""
        result = self.calculator.calculate_parametric_var(
            self.sample_returns, confidence_level=0.95, distribution="normal"
        )

        self.assertIsInstance(result, VaRResult)
        self.assertEqual(result.method, "Parametric VaR (Normal)")
        self.assertEqual(result.confidence_level, 0.95)
        self.assertGreater(result.var_value, 0)
        self.assertGreater(result.cvar_value, 0)
        self.assertIn("z_score", result.additional_stats)

    def test_parametric_var_t_distribution(self):
        """パラメトリックVaR（t分布）テスト"""
        result = self.calculator.calculate_parametric_var(
            self.sample_returns, confidence_level=0.95, distribution="t"
        )

        self.assertIsInstance(result, VaRResult)
        self.assertEqual(result.method, "Parametric VaR (T)")
        self.assertIn("t_score", result.additional_stats)
        self.assertIn("degrees_of_freedom", result.additional_stats)

    def test_parametric_var_invalid_distribution(self):
        """無効な分布でのパラメトリックVaRテスト"""
        with self.assertRaises(ValueError):
            self.calculator.calculate_parametric_var(
                self.sample_returns, distribution="invalid"
            )

    def test_monte_carlo_var(self):
        """モンテカルロVaRテスト"""
        result = self.calculator.calculate_monte_carlo_var(
            self.sample_returns, confidence_level=0.95, simulations=1000
        )

        self.assertIsInstance(result, VaRResult)
        self.assertEqual(result.method, "Monte Carlo VaR")
        self.assertEqual(result.confidence_level, 0.95)
        self.assertGreater(result.var_value, 0)
        self.assertEqual(result.additional_stats["simulations"], 1000)

    def test_monte_carlo_var_different_simulations(self):
        """異なるシミュレーション回数でのモンテカルロVaRテスト"""
        result_1k = self.calculator.calculate_monte_carlo_var(
            self.sample_returns, simulations=1000
        )
        result_10k = self.calculator.calculate_monte_carlo_var(
            self.sample_returns, simulations=10000
        )

        # シミュレーション回数の違いを確認
        self.assertEqual(result_1k.additional_stats["simulations"], 1000)
        self.assertEqual(result_10k.additional_stats["simulations"], 10000)

    def test_hybrid_var_default_weights(self):
        """ハイブリッドVaR（デフォルト重み）テスト"""
        result = self.calculator.calculate_hybrid_var(
            self.sample_returns, confidence_level=0.95
        )

        self.assertIsInstance(result, VaRResult)
        self.assertEqual(result.method, "Hybrid VaR")
        self.assertIn("weights", result.additional_stats)
        self.assertIn("historical_var", result.additional_stats)
        self.assertIn("parametric_var", result.additional_stats)
        self.assertIn("monte_carlo_var", result.additional_stats)

    def test_hybrid_var_custom_weights(self):
        """ハイブリッドVaR（カスタム重み）テスト"""
        custom_weights = {
            "historical": 0.5,
            "parametric": 0.3,
            "monte_carlo": 0.2
        }
        result = self.calculator.calculate_hybrid_var(
            self.sample_returns, weights=custom_weights
        )

        self.assertEqual(result.additional_stats["weights"], custom_weights)

    def test_portfolio_var(self):
        """ポートフォリオVaRテスト"""
        assets_returns = {
            "Asset1": [0.01, -0.02, 0.03, -0.01, 0.02],
            "Asset2": [-0.01, 0.02, -0.03, 0.01, -0.02],
            "Asset3": [0.005, -0.01, 0.015, -0.005, 0.01]
        }
        weights = {"Asset1": 0.5, "Asset2": 0.3, "Asset3": 0.2}

        result = self.calculator.calculate_portfolio_var(
            assets_returns, weights, confidence_level=0.95
        )

        self.assertIsInstance(result, PortfolioVaRResult)
        self.assertEqual(len(result.individual_vars), 3)
        self.assertGreater(result.portfolio_var, 0)
        self.assertIsInstance(result.correlation_matrix, list)
        self.assertEqual(len(result.correlation_matrix), 3)

    def test_portfolio_var_diversification_benefit(self):
        """ポートフォリオVaR分散効果テスト"""
        # 負の相関を持つ資産
        assets_returns = {
            "Asset1": [0.02, -0.01, 0.03, -0.02, 0.01],
            "Asset2": [-0.02, 0.01, -0.03, 0.02, -0.01]  # Asset1と逆相関
        }
        weights = {"Asset1": 0.5, "Asset2": 0.5}

        result = self.calculator.calculate_portfolio_var(
            assets_returns, weights
        )

        # 分散効果があることを確認（個別VaRの合計 > ポートフォリオVaR）
        individual_sum = sum(result.individual_vars.values())
        self.assertGreater(individual_sum, result.portfolio_var)
        self.assertGreater(result.diversification_benefit, 0)

    def test_var_validation(self):
        """VaRモデル検証テスト"""
        returns = [-0.06, -0.02, 0.01, -0.04, 0.02,
                   -0.03, 0.01, -0.01, 0.02, -0.05]
        var_estimates = [0.03, 0.03, 0.03, 0.03, 0.03,
                         0.03, 0.03, 0.03, 0.03, 0.03]

        result = self.calculator.validate_var_model(
            returns, var_estimates, confidence_level=0.95
        )

        self.assertIsInstance(result, VaRValidationResult)
        self.assertEqual(result.confidence_level, 0.95)
        self.assertEqual(result.total_observations, len(returns))
        self.assertGreaterEqual(result.violations, 0)
        self.assertIsInstance(result.is_model_valid, bool)

    def test_var_validation_no_violations(self):
        """VaR違反なしの検証テスト"""
        returns = [0.01, 0.02, -0.01, 0.015, -0.005]
        var_estimates = [0.05, 0.05, 0.05, 0.05, 0.05]

        result = self.calculator.validate_var_model(returns, var_estimates)

        self.assertEqual(result.violations, 0)
        self.assertEqual(result.violation_rate, 0.0)
        self.assertEqual(result.kupiec_statistic, 0.0)
        self.assertEqual(result.kupiec_p_value, 1.0)

    def test_export_results_single(self):
        """単一結果エクスポートテスト"""
        result = self.calculator.calculate_historical_var(self.sample_returns)

        with tempfile.NamedTemporaryFile(
                mode='w', delete=False, suffix='.json') as f:
            filename = f.name

        try:
            success = self.calculator.export_results(result, filename)
            self.assertTrue(success)
            self.assertTrue(os.path.exists(filename))

            # ファイル内容確認
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.assertEqual(data['method'], "Historical VaR")

        finally:
            if os.path.exists(filename):
                os.unlink(filename)

    def test_export_results_list(self):
        """複数結果エクスポートテスト"""
        results = [
            self.calculator.calculate_historical_var(self.sample_returns),
            self.calculator.calculate_parametric_var(self.sample_returns)
        ]

        with tempfile.NamedTemporaryFile(
                mode='w', delete=False, suffix='.json') as f:
            filename = f.name

        try:
            success = self.calculator.export_results(results, filename)
            self.assertTrue(success)

            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.assertEqual(len(data), 2)

        finally:
            if os.path.exists(filename):
                os.unlink(filename)

    def test_empty_returns_error(self):
        """空の収益率データエラーテスト"""
        with self.assertRaises(ValueError):
            self.calculator.calculate_historical_var([])

        with self.assertRaises(ValueError):
            self.calculator.calculate_parametric_var([])

        with self.assertRaises(ValueError):
            self.calculator.calculate_monte_carlo_var([])

        with self.assertRaises(ValueError):
            self.calculator.calculate_hybrid_var([])

    def test_mismatched_validation_data(self):
        """検証データ不一致エラーテスト"""
        returns = [0.01, 0.02, 0.03]
        var_estimates = [0.02, 0.03]  # 長さが異なる

        with self.assertRaises(ValueError):
            self.calculator.validate_var_model(returns, var_estimates)

    def test_portfolio_var_empty_assets(self):
        """空資産ポートフォリオVaRエラーテスト"""
        with self.assertRaises(ValueError):
            self.calculator.calculate_portfolio_var({}, {})

    def test_zero_volatility_handling(self):
        """ゼロボラティリティ処理テスト"""
        constant_returns = [0.01] * 10  # 一定収益率

        result = self.calculator.calculate_historical_var(constant_returns)
        # ボラティリティが非常に小さいことを確認（浮動小数点精度考慮）
        self.assertLess(result.volatility, 1e-15)

    def test_extreme_returns_handling(self):
        """極端な収益率処理テスト"""
        extreme_returns = [-0.5, 0.3, -0.2, 0.4, -0.1]

        result = self.calculator.calculate_historical_var(extreme_returns)
        self.assertGreater(result.var_value, 0)
        self.assertGreater(result.volatility, 0.1)  # 高ボラティリティ

    def test_confidence_level_edge_cases(self):
        """信頼水準エッジケーステスト"""
        # 非常に高い信頼水準
        result_999 = self.calculator.calculate_historical_var(
            self.sample_returns, confidence_level=0.999
        )
        self.assertGreater(result_999.var_value, 0)

        # 低い信頼水準
        result_50 = self.calculator.calculate_historical_var(
            self.sample_returns, confidence_level=0.50
        )
        self.assertGreater(result_50.var_value, 0)

    def test_large_dataset_performance(self):
        """大規模データセット性能テスト"""
        large_returns = create_sample_data(days=2520)  # 10年分

        result = self.calculator.calculate_historical_var(large_returns)
        self.assertEqual(result.data_points, 2520)
        self.assertGreater(result.var_value, 0)

    def test_create_sample_data(self):
        """サンプルデータ生成テスト"""
        sample_data = create_sample_data(days=100)
        self.assertEqual(len(sample_data), 100)
        self.assertIsInstance(sample_data, list)
        self.assertTrue(all(isinstance(x, float) for x in sample_data))

    def test_result_attributes(self):
        """結果オブジェクト属性テスト"""
        result = self.calculator.calculate_historical_var(self.sample_returns)

        # 必須属性の存在確認
        required_attrs = [
            'method', 'confidence_level', 'var_value', 'var_percentage',
            'cvar_value', 'cvar_percentage', 'expected_shortfall',
            'portfolio_value', 'calculation_date', 'data_points',
            'volatility', 'skewness', 'kurtosis', 'additional_stats'
        ]

        for attr in required_attrs:
            self.assertTrue(hasattr(result, attr))
            self.assertIsNotNone(getattr(result, attr))

    def test_to_dict_conversion(self):
        """辞書変換テスト"""
        result = self.calculator.calculate_historical_var(self.sample_returns)
        result_dict = result.to_dict()

        self.assertIsInstance(result_dict, dict)
        self.assertEqual(result_dict['method'], result.method)
        self.assertEqual(result_dict['var_value'], result.var_value)


if __name__ == '__main__':
    unittest.main() 