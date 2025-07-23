"""
VaR (Value at Risk) Calculator

金融機関レベルのVaR計算システム
- ヒストリカルVaR、パラメトリックVaR、モンテカルロVaR、ハイブリッドVaR
- CVaR (Conditional VaR) / Expected Shortfall
- ポートフォリオVaR (相関考慮)
- VaRモデル検証 (バックテスト、Kupiec検定)

Author: HANIWA
Date: 2025-01-25
Version: 1.0.0
"""

import logging
import json
from datetime import datetime
from typing import Dict, List, Optional, Union, Any
from dataclasses import dataclass, asdict
from enum import Enum
import numpy as np
import scipy.stats as stats
from scipy.stats import norm, t

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VaRMethod(Enum):
    """VaR計算手法"""
    HISTORICAL = "historical"
    PARAMETRIC = "parametric"
    MONTE_CARLO = "monte_carlo"
    HYBRID = "hybrid"


class ConfidenceLevel(Enum):
    """信頼水準"""
    LEVEL_90 = 0.90
    LEVEL_95 = 0.95
    LEVEL_99 = 0.99
    LEVEL_999 = 0.999


@dataclass
class VaRResult:
    """VaR計算結果"""
    method: str
    confidence_level: float
    var_value: float
    var_percentage: float
    cvar_value: float
    cvar_percentage: float
    expected_shortfall: float
    portfolio_value: float
    calculation_date: str
    data_points: int
    volatility: float
    skewness: float
    kurtosis: float
    additional_stats: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return asdict(self)


@dataclass
class PortfolioVaRResult:
    """ポートフォリオVaR結果"""
    individual_vars: Dict[str, float]
    portfolio_var: float
    diversification_benefit: float
    correlation_matrix: List[List[float]]
    portfolio_volatility: float
    calculation_date: str


@dataclass
class VaRValidationResult:
    """VaRモデル検証結果"""
    method: str
    confidence_level: float
    violations: int
    total_observations: int
    violation_rate: float
    expected_violations: int
    kupiec_statistic: float
    kupiec_p_value: float
    is_model_valid: bool
    validation_date: str


class VaRCalculator:
    """VaR計算システム"""

    def __init__(self, portfolio_value: float = 1000000.0):
        """
        初期化

        Args:
            portfolio_value: ポートフォリオ価値（デフォルト: 100万円）
        """
        self.portfolio_value = portfolio_value
        self.logger = logging.getLogger(__name__)

    def calculate_historical_var(
        self,
        returns: List[float],
        confidence_level: float = 0.95,
        portfolio_value: Optional[float] = None
    ) -> VaRResult:
        """
        ヒストリカルVaR計算

        Args:
            returns: 収益率データ
            confidence_level: 信頼水準
            portfolio_value: ポートフォリオ価値

        Returns:
            VaRResult: VaR計算結果
        """
        try:
            if not returns:
                raise ValueError("収益率データが空です")

            portfolio_val = portfolio_value or self.portfolio_value
            returns_array = np.array(returns)

            # 統計量計算
            volatility = np.std(returns_array)
            skewness = stats.skew(returns_array)
            kurtosis = stats.kurtosis(returns_array)

            # ヒストリカルVaR計算
            percentile = (1 - confidence_level) * 100
            var_return = np.percentile(returns_array, percentile)
            var_value = abs(var_return * portfolio_val)
            var_percentage = abs(var_return) * 100

            # CVaR計算 (期待ショートフォール)
            tail_returns = returns_array[returns_array <= var_return]
            if len(tail_returns) > 0:
                cvar_return = np.mean(tail_returns)
                cvar_value = abs(cvar_return * portfolio_val)
                cvar_percentage = abs(cvar_return) * 100
                expected_shortfall = cvar_value
            else:
                cvar_return = var_return
                cvar_value = var_value
                cvar_percentage = var_percentage
                expected_shortfall = var_value

            # 追加統計情報
            additional_stats = {
                "min_return": float(np.min(returns_array)),
                "max_return": float(np.max(returns_array)),
                "mean_return": float(np.mean(returns_array)),
                "median_return": float(np.median(returns_array)),
                "percentile_used": percentile,
                "tail_observations": len(tail_returns)
            }

            result = VaRResult(
                method="Historical VaR",
                confidence_level=confidence_level,
                var_value=var_value,
                var_percentage=var_percentage,
                cvar_value=cvar_value,
                cvar_percentage=cvar_percentage,
                expected_shortfall=expected_shortfall,
                portfolio_value=portfolio_val,
                calculation_date=datetime.now().isoformat(),
                data_points=len(returns_array),
                volatility=volatility,
                skewness=skewness,
                kurtosis=kurtosis,
                additional_stats=additional_stats
            )

            self.logger.info(
                "ヒストリカルVaR計算完了: {:.0f}円 ({:.2f}%)".format(
                    var_value, var_percentage
                )
            )
            return result

        except Exception as e:
            self.logger.error("ヒストリカルVaR計算エラー: {}".format(str(e)))
            raise

    def calculate_parametric_var(
        self,
        returns: List[float],
        confidence_level: float = 0.95,
        distribution: str = "normal",
        portfolio_value: Optional[float] = None
    ) -> VaRResult:
        """
        パラメトリックVaR計算

        Args:
            returns: 収益率データ
            confidence_level: 信頼水準
            distribution: 分布タイプ ("normal" or "t")
            portfolio_value: ポートフォリオ価値

        Returns:
            VaRResult: VaR計算結果
        """
        try:
            if not returns:
                raise ValueError("収益率データが空です")

            portfolio_val = portfolio_value or self.portfolio_value
            returns_array = np.array(returns)

            # 統計量計算
            mean_return = np.mean(returns_array)
            volatility = np.std(returns_array)
            skewness = stats.skew(returns_array)
            kurtosis = stats.kurtosis(returns_array)

            # 分布に応じたVaR計算
            if distribution == "normal":
                z_score = norm.ppf(1 - confidence_level)
                var_return = mean_return + z_score * volatility
            elif distribution == "t":
                # t分布のパラメータ推定
                df = len(returns_array) - 1
                t_score = t.ppf(1 - confidence_level, df)
                var_return = mean_return + t_score * volatility
            else:
                raise ValueError(
                    "サポートされていない分布: {}".format(distribution)
                )

            var_value = abs(var_return * portfolio_val)
            var_percentage = abs(var_return) * 100

            # CVaR計算
            if distribution == "normal":
                # 正規分布のCVaR解析解
                phi_z = norm.pdf(norm.ppf(1 - confidence_level))
                cvar_return = (mean_return - volatility * phi_z /
                               (1 - confidence_level))
            else:
                # t分布のCVaR近似
                cvar_return = var_return * 1.2  # 近似値

            cvar_value = abs(cvar_return * portfolio_val)
            cvar_percentage = abs(cvar_return) * 100
            expected_shortfall = cvar_value

            # 追加統計情報
            additional_stats = {
                "distribution": distribution,
                "mean_return": float(mean_return),
                "z_score": (float(z_score) if distribution == "normal"
                            else None),
                "t_score": (float(t_score) if distribution == "t"
                            else None),
                "degrees_of_freedom": df if distribution == "t" else None
            }

            result = VaRResult(
                method="Parametric VaR ({})".format(distribution.title()),
                confidence_level=confidence_level,
                var_value=var_value,
                var_percentage=var_percentage,
                cvar_value=cvar_value,
                cvar_percentage=cvar_percentage,
                expected_shortfall=expected_shortfall,
                portfolio_value=portfolio_val,
                calculation_date=datetime.now().isoformat(),
                data_points=len(returns_array),
                volatility=volatility,
                skewness=skewness,
                kurtosis=kurtosis,
                additional_stats=additional_stats
            )

            self.logger.info(
                "パラメトリックVaR計算完了: {:.0f}円 ({:.2f}%)".format(
                    var_value, var_percentage
                )
            )
            return result

        except Exception as e:
            self.logger.error(
                "パラメトリックVaR計算エラー: {}".format(str(e))
            )
            raise

    def calculate_monte_carlo_var(
        self,
        returns: List[float],
        confidence_level: float = 0.95,
        simulations: int = 10000,
        portfolio_value: Optional[float] = None
    ) -> VaRResult:
        """
        モンテカルロVaR計算

        Args:
            returns: 収益率データ
            confidence_level: 信頼水準
            simulations: シミュレーション回数
            portfolio_value: ポートフォリオ価値

        Returns:
            VaRResult: VaR計算結果
        """
        try:
            if not returns:
                raise ValueError("収益率データが空です")

            portfolio_val = portfolio_value or self.portfolio_value
            returns_array = np.array(returns)

            # 統計量計算
            mean_return = np.mean(returns_array)
            volatility = np.std(returns_array)
            skewness = stats.skew(returns_array)
            kurtosis = stats.kurtosis(returns_array)

            # モンテカルロシミュレーション
            np.random.seed(42)  # 再現性のため
            simulated_returns = np.random.normal(
                mean_return, volatility, simulations
            )

            # VaR計算
            percentile = (1 - confidence_level) * 100
            var_return = np.percentile(simulated_returns, percentile)
            var_value = abs(var_return * portfolio_val)
            var_percentage = abs(var_return) * 100

            # CVaR計算
            tail_returns = simulated_returns[simulated_returns <= var_return]
            cvar_return = np.mean(tail_returns)
            cvar_value = abs(cvar_return * portfolio_val)
            cvar_percentage = abs(cvar_return) * 100
            expected_shortfall = cvar_value

            # 追加統計情報
            additional_stats = {
                "simulations": simulations,
                "simulated_mean": float(np.mean(simulated_returns)),
                "simulated_std": float(np.std(simulated_returns)),
                "percentile_used": percentile,
                "tail_observations": len(tail_returns)
            }

            result = VaRResult(
                method="Monte Carlo VaR",
                confidence_level=confidence_level,
                var_value=var_value,
                var_percentage=var_percentage,
                cvar_value=cvar_value,
                cvar_percentage=cvar_percentage,
                expected_shortfall=expected_shortfall,
                portfolio_value=portfolio_val,
                calculation_date=datetime.now().isoformat(),
                data_points=len(returns_array),
                volatility=volatility,
                skewness=skewness,
                kurtosis=kurtosis,
                additional_stats=additional_stats
            )

            self.logger.info(
                "モンテカルロVaR計算完了: {:.0f}円 ({:.2f}%)".format(
                    var_value, var_percentage
                )
            )
            return result

        except Exception as e:
            self.logger.error(
                "モンテカルロVaR計算エラー: {}".format(str(e))
            )
            raise

    def calculate_hybrid_var(
        self,
        returns: List[float],
        confidence_level: float = 0.95,
        weights: Optional[Dict[str, float]] = None,
        portfolio_value: Optional[float] = None
    ) -> VaRResult:
        """
        ハイブリッドVaR計算（複数手法の統合）

        Args:
            returns: 収益率データ
            confidence_level: 信頼水準
            weights: 各手法の重み
            portfolio_value: ポートフォリオ価値

        Returns:
            VaRResult: VaR計算結果
        """
        try:
            if not returns:
                raise ValueError("収益率データが空です")

            # デフォルト重み
            if weights is None:
                weights = {
                    "historical": 0.4,
                    "parametric": 0.3,
                    "monte_carlo": 0.3
                }

            # 各手法でVaR計算
            hist_var = self.calculate_historical_var(
                returns, confidence_level, portfolio_value
            )
            param_var = self.calculate_parametric_var(
                returns, confidence_level, "normal", portfolio_value
            )
            mc_var = self.calculate_monte_carlo_var(
                returns, confidence_level, 5000, portfolio_value
            )

            # 重み付き平均でハイブリッドVaR計算
            hybrid_var_value = (
                weights["historical"] * hist_var.var_value +
                weights["parametric"] * param_var.var_value +
                weights["monte_carlo"] * mc_var.var_value
            )

            hybrid_cvar_value = (
                weights["historical"] * hist_var.cvar_value +
                weights["parametric"] * param_var.cvar_value +
                weights["monte_carlo"] * mc_var.cvar_value
            )

            portfolio_val = portfolio_value or self.portfolio_value
            hybrid_var_percentage = (hybrid_var_value / portfolio_val) * 100
            hybrid_cvar_percentage = (hybrid_cvar_value / portfolio_val) * 100

            # 統計量（平均値使用）
            returns_array = np.array(returns)
            volatility = np.std(returns_array)
            skewness = stats.skew(returns_array)
            kurtosis = stats.kurtosis(returns_array)

            # 追加統計情報
            additional_stats = {
                "weights": weights,
                "historical_var": hist_var.var_value,
                "parametric_var": param_var.var_value,
                "monte_carlo_var": mc_var.var_value,
                "method_agreement": {
                    "hist_param_diff": abs(
                        hist_var.var_value - param_var.var_value
                    ),
                    "hist_mc_diff": abs(
                        hist_var.var_value - mc_var.var_value
                    ),
                    "param_mc_diff": abs(
                        param_var.var_value - mc_var.var_value
                    )
                }
            }

            result = VaRResult(
                method="Hybrid VaR",
                confidence_level=confidence_level,
                var_value=hybrid_var_value,
                var_percentage=hybrid_var_percentage,
                cvar_value=hybrid_cvar_value,
                cvar_percentage=hybrid_cvar_percentage,
                expected_shortfall=hybrid_cvar_value,
                portfolio_value=portfolio_val,
                calculation_date=datetime.now().isoformat(),
                data_points=len(returns_array),
                volatility=volatility,
                skewness=skewness,
                kurtosis=kurtosis,
                additional_stats=additional_stats
            )

            self.logger.info(
                "ハイブリッドVaR計算完了: {:.0f}円 ({:.2f}%)".format(
                    hybrid_var_value, hybrid_var_percentage
                )
            )
            return result

        except Exception as e:
            self.logger.error("ハイブリッドVaR計算エラー: {}".format(str(e)))
            raise

    def calculate_portfolio_var(
        self,
        assets_returns: Dict[str, List[float]],
        weights: Dict[str, float],
        confidence_level: float = 0.95,
        method: str = "parametric",
        portfolio_value: Optional[float] = None
    ) -> PortfolioVaRResult:
        """
        ポートフォリオVaR計算（相関考慮）

        Args:
            assets_returns: 各資産の収益率
            weights: 各資産の重み
            confidence_level: 信頼水準
            method: 計算手法
            portfolio_value: ポートフォリオ価値

        Returns:
            PortfolioVaRResult: ポートフォリオVaR結果
        """
        try:
            if not assets_returns:
                raise ValueError("資産収益率データが空です")

            portfolio_val = portfolio_value or self.portfolio_value

            # 各資産の個別VaR計算
            individual_vars = {}
            returns_matrix = []
            asset_names = list(assets_returns.keys())

            for asset, returns in assets_returns.items():
                if method == "historical":
                    var_result = self.calculate_historical_var(
                        returns, confidence_level,
                        portfolio_val * weights[asset]
                    )
                else:
                    var_result = self.calculate_parametric_var(
                        returns, confidence_level, "normal",
                        portfolio_val * weights[asset]
                    )
                individual_vars[asset] = var_result.var_value
                returns_matrix.append(returns)

            # 相関行列計算
            returns_array = np.array(returns_matrix)
            correlation_matrix = np.corrcoef(returns_array).tolist()

            # ポートフォリオリターン計算
            portfolio_returns = []
            min_length = min(
                len(returns) for returns in assets_returns.values()
            )

            for i in range(min_length):
                portfolio_return = sum(
                    weights[asset] * assets_returns[asset][i]
                    for asset in asset_names
                )
                portfolio_returns.append(portfolio_return)

            # ポートフォリオVaR計算
            if method == "historical":
                portfolio_var_result = self.calculate_historical_var(
                    portfolio_returns, confidence_level, portfolio_val
                )
            else:
                portfolio_var_result = self.calculate_parametric_var(
                    portfolio_returns, confidence_level, "normal",
                    portfolio_val
                )

            portfolio_var = portfolio_var_result.var_value

            # 分散効果計算
            sum_individual_vars = sum(individual_vars.values())
            diversification_benefit = (sum_individual_vars - portfolio_var)

            # ポートフォリオボラティリティ
            portfolio_volatility = np.std(portfolio_returns)

            result = PortfolioVaRResult(
                individual_vars=individual_vars,
                portfolio_var=portfolio_var,
                diversification_benefit=diversification_benefit,
                correlation_matrix=correlation_matrix,
                portfolio_volatility=portfolio_volatility,
                calculation_date=datetime.now().isoformat()
            )

            self.logger.info(
                "ポートフォリオVaR計算完了: {:.0f}円 (分散効果: {:.0f}円)".format(
                    portfolio_var, diversification_benefit
                )
            )
            return result

        except Exception as e:
            self.logger.error(
                "ポートフォリオVaR計算エラー: {}".format(str(e))
            )
            raise

    def validate_var_model(
        self,
        returns: List[float],
        var_estimates: List[float],
        confidence_level: float = 0.95,
        method: str = "historical"
    ) -> VaRValidationResult:
        """
        VaRモデル検証（バックテスト）

        Args:
            returns: 実際の収益率
            var_estimates: VaR推定値
            confidence_level: 信頼水準
            method: 計算手法

        Returns:
            VaRValidationResult: 検証結果
        """
        try:
            if len(returns) != len(var_estimates):
                raise ValueError("収益率とVaR推定値の長さが一致しません")

            returns_array = np.array(returns)
            var_array = np.array(var_estimates)

            # VaR違反回数計算（損失がVaRを超えた回数）
            violations = np.sum(returns_array < -var_array)
            total_observations = len(returns_array)
            violation_rate = violations / total_observations

            # 期待違反回数
            expected_violations = int(
                total_observations * (1 - confidence_level)
            )

            # Kupiec検定
            if violations == 0:
                kupiec_statistic = 0.0
                kupiec_p_value = 1.0
            else:
                # 尤度比検定統計量
                p_observed = violation_rate
                p_expected = 1 - confidence_level

                if 0 < p_observed < 1:
                    lr_statistic = 2 * (
                        violations * np.log(p_observed / p_expected) +
                        (total_observations - violations) *
                        np.log((1 - p_observed) / (1 - p_expected))
                    )
                    kupiec_statistic = lr_statistic
                    kupiec_p_value = 1 - stats.chi2.cdf(lr_statistic, 1)
                else:
                    kupiec_statistic = float('inf')
                    kupiec_p_value = 0.0

            # モデル妥当性判定（p値 > 0.05で妥当）
            is_model_valid = kupiec_p_value > 0.05

            result = VaRValidationResult(
                method=method,
                confidence_level=confidence_level,
                violations=violations,
                total_observations=total_observations,
                violation_rate=violation_rate,
                expected_violations=expected_violations,
                kupiec_statistic=kupiec_statistic,
                kupiec_p_value=kupiec_p_value,
                is_model_valid=is_model_valid,
                validation_date=datetime.now().isoformat()
            )

            self.logger.info(
                "VaRモデル検証完了: 違反率 {:.2%} (期待値: {:.2%})".format(
                    violation_rate, 1 - confidence_level
                )
            )
            return result

        except Exception as e:
            self.logger.error("VaRモデル検証エラー: {}".format(str(e)))
            raise

    def export_results(
        self,
        results: Union[VaRResult, List[VaRResult], PortfolioVaRResult,
                      VaRValidationResult],
        filename: str
    ) -> bool:
        """
        結果をJSONファイルにエクスポート

        Args:
            results: エクスポートする結果
            filename: ファイル名

        Returns:
            bool: エクスポート成功可否
        """
        try:
            if isinstance(results, list):
                export_data = [result.to_dict() for result in results]
            elif hasattr(results, 'to_dict'):
                export_data = results.to_dict()
            else:
                export_data = asdict(results)

            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)

            self.logger.info("結果エクスポート完了: {}".format(filename))
            return True

        except Exception as e:
            self.logger.error(
                "結果エクスポートエラー: {}".format(str(e))
            )
            return False


def create_sample_data(days: int = 252) -> List[float]:
    """
    サンプルデータ生成（テスト用）

    Args:
        days: データ日数

    Returns:
        List[float]: サンプル収益率データ
    """
    np.random.seed(42)
    # 平均0.1%、標準偏差2%
    returns = np.random.normal(0.001, 0.02, days)
    return returns.tolist()


# テスト実行用
if __name__ == "__main__":
    # サンプルデータでテスト
    calculator = VaRCalculator(portfolio_value=1000000)
    sample_returns = create_sample_data()

    # ヒストリカルVaR
    hist_result = calculator.calculate_historical_var(sample_returns)
    print("ヒストリカルVaR: {:.0f}円".format(hist_result.var_value)) 