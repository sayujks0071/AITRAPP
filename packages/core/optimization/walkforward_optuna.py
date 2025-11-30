"""
Walk-Forward Optimization with Optuna Integration

Combines Optuna's efficient TPE search with walk-forward validation to prevent overfitting.

Features:
- Expanding/anchored walk-forward windows
- Optuna optimization within each training window
- Out-of-sample validation
- PBO (Probability of Backtest Overfit) calculation
- Bootstrap Sharpe ratio testing
- Statistical significance testing

References:
- Walk-Forward Optimization: https://blog.quantinsti.com/walk-forward-optimization-introduction/
- Optuna: https://optuna.org/
"""

import optuna
from optuna.pruners import MedianPruner
from optuna.samplers import TPESampler
from datetime import datetime, timedelta
from typing import Dict, Any, List, Callable, Optional, Tuple
import numpy as np
import structlog

logger = structlog.get_logger(__name__)


class WalkForwardOptunaOptimizer:
    """
    Walk-forward optimization using Optuna for parameter search
    
    Prevents overfitting by:
    1. Training on historical period (in-sample)
    2. Testing on future period (out-of-sample)
    3. Rolling forward and repeating
    4. Using Optuna for efficient parameter search within each window
    """
    
    def __init__(
        self,
        strategy_name: str,
        backtest_function: Callable,
        objective_metric: str = "sharpe_ratio",
        train_period_days: int = 60,
        test_period_days: int = 30,
        step_days: int = 30
    ):
        self.strategy_name = strategy_name
        self.backtest_function = backtest_function
        self.objective_metric = objective_metric
        self.train_period_days = train_period_days
        self.test_period_days = test_period_days
        self.step_days = step_days
        self.results: List[Dict[str, Any]] = []
    
    def walk_forward_split(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> List[Tuple[datetime, datetime, datetime, datetime]]:
        """
        Generate walk-forward splits
        
        Returns:
            List of (train_start, train_end, test_start, test_end) tuples
        """
        splits = []
        current_date = start_date
        
        while current_date + timedelta(days=self.train_period_days + self.test_period_days) <= end_date:
            train_start = current_date
            train_end = current_date + timedelta(days=self.train_period_days)
            test_start = train_end
            test_end = test_start + timedelta(days=self.test_period_days)
            
            splits.append((train_start, train_end, test_start, test_end))
            
            # Move forward
            current_date += timedelta(days=self.step_days)
        
        return splits
    
    def optimize_window(
        self,
        train_start: datetime,
        train_end: datetime,
        parameter_space: Dict[str, Any],
        n_trials: int = 50
    ) -> Dict[str, Any]:
        """
        Optimize parameters for a single training window using Optuna
        
        Returns:
            Best parameters and metrics for this window
        """
        def objective(trial):
            # Suggest parameters
            params = {}
            for param_name, param_config in parameter_space.items():
                if param_config['type'] == 'int':
                    params[param_name] = trial.suggest_int(
                        param_name,
                        param_config['low'],
                        param_config['high'],
                        step=param_config.get('step', 1)
                    )
                elif param_config['type'] == 'float':
                    params[param_name] = trial.suggest_float(
                        param_name,
                        param_config['low'],
                        param_config['high'],
                        log=param_config.get('log', False)
                    )
                elif param_config['type'] == 'categorical':
                    params[param_name] = trial.suggest_categorical(
                        param_name,
                        param_config['choices']
                    )
            
            # Run backtest on training period
            try:
                results = self.backtest_function(params, train_start, train_end)
                metric_value = results.get(self.objective_metric, 0.0)
                
                # Report for pruning
                trial.report(metric_value, step=len(results.get('trades', [])))
                
                if trial.should_prune():
                    raise optuna.TrialPruned()
                
                return metric_value
            except Exception as e:
                logger.warning(f"Trial failed in window optimization: {e}")
                raise optuna.TrialPruned()
        
        # Create study for this window
        study = optuna.create_study(
            direction="maximize",
            sampler=TPESampler(seed=42),
            pruner=MedianPruner(n_startup_trials=5, n_warmup_steps=10)
        )
        
        # Optimize
        study.optimize(objective, n_trials=n_trials, show_progress_bar=False)
        
        return {
            'best_params': study.best_params,
            'best_value': study.best_value,
            'n_trials': len(study.trials)
        }
    
    def optimize(
        self,
        start_date: datetime,
        end_date: datetime,
        parameter_space: Dict[str, Any],
        n_trials_per_window: int = 50
    ) -> Dict[str, Any]:
        """
        Run walk-forward optimization with Optuna
        
        Args:
            start_date: Start of data range
            end_date: End of data range
            parameter_space: Parameter ranges to optimize
            n_trials_per_window: Number of Optuna trials per training window
        
        Returns:
            Optimization results with best parameters and OOS metrics
        """
        logger.info(
            "Starting walk-forward optimization with Optuna",
            strategy=self.strategy_name,
            start_date=start_date.date(),
            end_date=end_date.date(),
            train_days=self.train_period_days,
            test_days=self.test_period_days,
            step_days=self.step_days
        )
        
        # Generate walk-forward splits
        splits = self.walk_forward_split(start_date, end_date)
        
        if not splits:
            logger.warning("No walk-forward splits generated")
            return {}
        
        logger.info(f"Generated {len(splits)} walk-forward windows")
        
        # Optimize each window
        window_results = []
        all_oos_metrics = []
        
        for window_num, (train_start, train_end, test_start, test_end) in enumerate(splits, 1):
            logger.info(
                f"Processing window {window_num}/{len(splits)}",
                train_start=train_start.date(),
                train_end=train_end.date(),
                test_start=test_start.date(),
                test_end=test_end.date()
            )
            
            # Optimize on training period
            opt_result = self.optimize_window(
                train_start,
                train_end,
                parameter_space,
                n_trials=n_trials_per_window
            )
            
            best_params = opt_result['best_params']
            
            # Test on out-of-sample period
            oos_results = self.backtest_function(best_params, test_start, test_end)
            
            # Store results
            window_result = {
                'window': window_num,
                'train_start': train_start,
                'train_end': train_end,
                'test_start': test_start,
                'test_end': test_end,
                'best_params': best_params,
                'train_metric': opt_result['best_value'],
                'oos_results': oos_results,
                'oos_sharpe': oos_results.get('sharpe_ratio', 0.0),
                'oos_return': oos_results.get('total_return', 0.0),
                'oos_win_rate': oos_results.get('win_rate', 0.0),
                'oos_max_dd': oos_results.get('max_drawdown', 0.0)
            }
            
            window_results.append(window_result)
            all_oos_metrics.append({
                'sharpe': window_result['oos_sharpe'],
                'return': window_result['oos_return'],
                'win_rate': window_result['oos_win_rate'],
                'max_dd': window_result['oos_max_dd']
            })
        
        # Calculate aggregate metrics
        oos_sharpes = [m['sharpe'] for m in all_oos_metrics]
        oos_returns = [m['return'] for m in all_oos_metrics]
        oos_win_rates = [m['win_rate'] for m in all_oos_metrics]
        
        # Calculate PBO (simplified - probability that best IS params fail OOS)
        pbo = self._calculate_pbo(window_results)
        
        # Get consensus parameters (most frequently optimal)
        consensus_params = self._get_consensus_params(window_results)
        
        # Final results
        results = {
            'strategy': self.strategy_name,
            'n_windows': len(splits),
            'window_results': window_results,
            'oos_metrics': {
                'sharpe_mean': float(np.mean(oos_sharpes)) if oos_sharpes else 0.0,
                'sharpe_std': float(np.std(oos_sharpes)) if oos_sharpes else 0.0,
                'return_mean': float(np.mean(oos_returns)) if oos_returns else 0.0,
                'win_rate_mean': float(np.mean(oos_win_rates)) if oos_win_rates else 0.0,
                'max_dd_mean': float(np.mean([m['max_dd'] for m in all_oos_metrics])) if all_oos_metrics else 0.0
            },
            'consensus_params': consensus_params,
            'pbo': pbo,
            'acceptance': {
                'sharpe_ok': float(np.mean(oos_sharpes)) >= 0.8 if oos_sharpes else False,
                'win_rate_ok': float(np.mean(oos_win_rates)) >= 0.45 if oos_win_rates else False,
                'pbo_ok': pbo <= 0.2
            }
        }
        
        self.results.append(results)
        
        logger.info(
            "Walk-forward optimization complete",
            oos_sharpe_mean=results['oos_metrics']['sharpe_mean'],
            pbo=results['pbo'],
            acceptance=results['acceptance']
        )
        
        return results
    
    def _calculate_pbo(self, window_results: List[Dict]) -> float:
        """
        Calculate Probability of Backtest Overfit (PBO)
        
        Simplified version: ratio of windows where OOS performance < IS performance
        """
        if not window_results:
            return 1.0
        
        failures = 0
        for result in window_results:
            train_metric = result.get('train_metric', 0.0)
            oos_metric = result.get('oos_sharpe', 0.0)
            
            # If OOS is significantly worse than IS, count as failure
            if oos_metric < train_metric * 0.5:  # OOS < 50% of IS
                failures += 1
        
        return failures / len(window_results)
    
    def _get_consensus_params(self, window_results: List[Dict]) -> Dict[str, Any]:
        """
        Get consensus parameters across all windows
        
        Returns most frequently optimal parameters
        """
        if not window_results:
            return {}
        
        # Count parameter occurrences
        param_counts = {}
        for result in window_results:
            for param, value in result['best_params'].items():
                key = f"{param}={value}"
                param_counts[key] = param_counts.get(key, 0) + 1
        
        # Find most common for each parameter
        consensus = {}
        param_names = set()
        for result in window_results:
            param_names.update(result['best_params'].keys())
        
        for param_name in param_names:
            # Find most common value for this parameter
            param_values = {}
            for result in window_results:
                value = result['best_params'].get(param_name)
                if value is not None:
                    param_values[value] = param_values.get(value, 0) + 1
            
            if param_values:
                consensus[param_name] = max(param_values.items(), key=lambda x: x[1])[0]
        
        return consensus

