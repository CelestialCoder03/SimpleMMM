"""Export model results to various formats."""

import csv
import io
import json
from pathlib import Path

import pandas as pd

from app.services.results.processor import ProcessedResult


class ResultExporter:
    """
    Export model results to various formats.

    Supports:
    - CSV: Coefficients, contributions, decomposition
    - Excel: Full workbook with multiple sheets
    - JSON: Complete result data
    - HTML: Formatted report

    Usage:
        exporter = ResultExporter(result)

        # Export to CSV
        csv_data = exporter.to_csv('contributions')

        # Export to Excel
        excel_bytes = exporter.to_excel()

        # Export to JSON
        json_str = exporter.to_json()
    """

    # Localized field names
    LABELS = {
        "en": {
            "variable": "Variable",
            "group": "Group",
            "type": "Type",
            "value": "Value",
            "date": "Date",
            "actual": "Actual",
            "predicted": "Predicted",
            "intercept": "Intercept (Base)",
            "base": "Base",
            "seasonality": "Seasonality",
            "support": "Support",
            "decomp": "Decomp",
            "coefficient": "Coefficient",
            "std_error": "Std Error",
            "p_value": "P-Value",
            "significant": "Significant",
            "metric": "Metric",
            "description": "Description",
            "contribution_pct": "Contribution %",
            "total_contribution": "Total Contribution",
            "roi": "ROI",
            "sheet_metrics": "Model Metrics",
            "sheet_coefficients": "Coefficients",
            "sheet_decomposition": "Decomposition",
            "yes": "Yes",
            "no": "No",
        },
        "zh": {
            "variable": "变量",
            "group": "分组",
            "type": "类型",
            "value": "数值",
            "date": "日期",
            "actual": "实际值",
            "predicted": "预测值",
            "intercept": "截距 (基准)",
            "base": "基准",
            "seasonality": "季节性",
            "support": "原始值",
            "decomp": "增量贡献",
            "coefficient": "系数",
            "std_error": "标准误",
            "p_value": "P值",
            "significant": "显著",
            "metric": "指标",
            "description": "说明",
            "contribution_pct": "贡献度 %",
            "total_contribution": "总贡献",
            "roi": "ROI",
            "sheet_metrics": "模型指标",
            "sheet_coefficients": "系数",
            "sheet_decomposition": "分解数据",
            "yes": "是",
            "no": "否",
        },
    }

    def __init__(
        self,
        result: ProcessedResult,
        language: str = "en",
        variable_groups: dict[str, str] | None = None,
    ):
        self.result = result
        self.language = language if language in self.LABELS else "en"
        self.variable_groups = variable_groups or {}  # variable -> group name mapping

    def _label(self, key: str) -> str:
        """Get localized label."""
        return self.LABELS[self.language].get(key, key)

    def _translate_variable(self, var_name: str) -> str:
        """Translate special variable names like 'seasonality' and 'base'."""
        special_vars = {
            "seasonality": self._label("seasonality"),
            "base": self._label("base"),
        }
        return special_vars.get(var_name, var_name)

    def to_csv(
        self,
        data_type: str = "all",
        include_header: bool = True,
    ) -> str:
        """
        Export to CSV format.

        Args:
            data_type: What to export ('coefficients', 'contributions',
                      'decomposition', 'metrics', 'all')
            include_header: Whether to include column headers

        Returns:
            CSV string
        """
        output = io.StringIO()

        if data_type == "coefficients":
            self._write_coefficients_csv(output, include_header)
        elif data_type == "contributions":
            self._write_contributions_csv(output, include_header)
        elif data_type == "decomposition":
            self._write_decomposition_csv(output, include_header)
        elif data_type == "metrics":
            self._write_metrics_csv(output, include_header)
        elif data_type == "all":
            self._write_all_csv(output)
        else:
            raise ValueError(f"Unknown data type: {data_type}")

        return output.getvalue()

    def _write_coefficients_csv(
        self,
        output: io.StringIO,
        include_header: bool = True,
    ) -> None:
        """Write coefficients to CSV."""
        writer = csv.writer(output)

        if include_header:
            writer.writerow(
                [
                    "Variable",
                    "Estimate",
                    "Std Error",
                    "T-Statistic",
                    "P-Value",
                    "CI Lower",
                    "CI Upper",
                    "Significant",
                ]
            )

        for coef in self.result.coefficients:
            writer.writerow(
                [
                    coef["variable"],
                    coef["estimate"],
                    coef.get("std_error", ""),
                    coef.get("t_statistic", ""),
                    coef.get("p_value", ""),
                    coef.get("ci_lower", ""),
                    coef.get("ci_upper", ""),
                    "Yes" if coef.get("is_significant") else "No" if coef.get("is_significant") is not None else "",
                ]
            )

    def _write_contributions_csv(
        self,
        output: io.StringIO,
        include_header: bool = True,
    ) -> None:
        """Write contributions to CSV."""
        writer = csv.writer(output)

        if include_header:
            writer.writerow(
                [
                    "Variable",
                    "Total Contribution",
                    "Contribution %",
                    "Avg Contribution",
                    "ROI",
                    "Marginal ROI",
                ]
            )

        for contrib in self.result.contributions:
            writer.writerow(
                [
                    contrib["variable"],
                    contrib["total_contribution"],
                    contrib["contribution_pct"],
                    contrib["avg_contribution"],
                    contrib.get("roi", ""),
                    contrib.get("marginal_roi", ""),
                ]
            )

    def _write_decomposition_csv(
        self,
        output: io.StringIO,
        include_header: bool = True,
    ) -> None:
        """Write time series decomposition to CSV."""
        decomp = self.result.decomposition
        dates = decomp.get("dates", [])
        actual = decomp.get("actual", [])
        predicted = decomp.get("predicted", [])
        base = decomp.get("base", [])
        contributions = decomp.get("contributions", {})

        writer = csv.writer(output)

        if include_header:
            headers = ["Date", "Actual", "Predicted", "Base"]
            headers.extend(contributions.keys())
            writer.writerow(headers)

        for i in range(len(dates)):
            row = [
                dates[i] if i < len(dates) else "",
                actual[i] if i < len(actual) else "",
                predicted[i] if i < len(predicted) else "",
                base[i] if i < len(base) else "",
            ]
            for channel, values in contributions.items():
                row.append(values[i] if i < len(values) else "")
            writer.writerow(row)

    def _write_metrics_csv(
        self,
        output: io.StringIO,
        include_header: bool = True,
    ) -> None:
        """Write model metrics to CSV."""
        writer = csv.writer(output)

        if include_header:
            writer.writerow(["Metric", "Value"])

        metrics = self.result.metrics
        metric_labels = {
            "r_squared": "R-Squared",
            "adjusted_r_squared": "Adjusted R-Squared",
            "rmse": "RMSE",
            "mape": "MAPE (%)",
            "aic": "AIC",
            "bic": "BIC",
            "n_observations": "N Observations",
            "n_features": "N Features",
        }

        for key, label in metric_labels.items():
            value = metrics.get(key)
            if value is not None:
                writer.writerow([label, value])

    def _write_all_csv(self, output: io.StringIO) -> None:
        """Write all data sections to CSV."""
        output.write("# MODEL METRICS\n")
        self._write_metrics_csv(output)
        output.write("\n")

        output.write("# COEFFICIENTS\n")
        self._write_coefficients_csv(output)
        output.write("\n")

        output.write("# CONTRIBUTIONS\n")
        self._write_contributions_csv(output)
        output.write("\n")

        output.write("# TIME SERIES DECOMPOSITION\n")
        self._write_decomposition_csv(output)

    def to_excel(self, file_path: str | Path | None = None) -> bytes:
        """
        Export to Excel workbook with multiple sheets.

        Sheets:
        1. Model Metrics - Key performance metrics
        2. Coefficients - Coefficients with p-values and significance
        3. Decomposition - Pivot format with variable name, group, type (support/decomp), value

        Args:
            file_path: Optional path to save file

        Returns:
            Excel file as bytes
        """
        output = io.BytesIO()

        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            # Sheet 1: Model Metrics
            self._write_metrics_sheet_enhanced(writer)

            # Sheet 2: Coefficients with p-values
            self._write_coefficients_sheet_enhanced(writer)

            # Sheet 3: Decomposition in pivot format
            self._write_decomposition_pivot_sheet(writer)

        excel_bytes = output.getvalue()

        if file_path:
            Path(file_path).write_bytes(excel_bytes)

        return excel_bytes

    def _write_metrics_sheet_enhanced(self, writer: pd.ExcelWriter) -> None:
        """Write enhanced metrics sheet."""
        metrics = self.result.metrics

        data = {
            self._label("metric"): [],
            self._label("value"): [],
            self._label("description"): [],
        }

        metric_info = [
            (
                "r_squared",
                "R²",
                "Proportion of variance explained" if self.language == "en" else "解释方差比例",
            ),
            (
                "adjusted_r_squared",
                "Adjusted R²",
                "R² adjusted for predictors" if self.language == "en" else "调整后R²",
            ),
            (
                "rmse",
                "RMSE",
                "Root Mean Square Error" if self.language == "en" else "均方根误差",
            ),
            (
                "mape",
                "MAPE (%)",
                "Mean Absolute Percentage Error" if self.language == "en" else "平均绝对百分比误差",
            ),
            (
                "mae",
                "MAE",
                "Mean Absolute Error" if self.language == "en" else "平均绝对误差",
            ),
            (
                "aic",
                "AIC",
                "Akaike Information Criterion" if self.language == "en" else "赤池信息准则",
            ),
            (
                "bic",
                "BIC",
                "Bayesian Information Criterion" if self.language == "en" else "贝叶斯信息准则",
            ),
            (
                "n_observations",
                "N",
                "Number of observations" if self.language == "en" else "观测数",
            ),
            (
                "n_features",
                "K",
                "Number of features" if self.language == "en" else "特征数",
            ),
        ]

        for key, label, desc in metric_info:
            value = metrics.get(key)
            if value is not None:
                data[self._label("metric")].append(label)
                data[self._label("value")].append(value)
                data[self._label("description")].append(desc)

        df = pd.DataFrame(data)
        df.to_excel(writer, sheet_name=self._label("sheet_metrics"), index=False)

    def _write_coefficients_sheet_enhanced(self, writer: pd.ExcelWriter) -> None:
        """Write enhanced coefficients sheet with variable groups."""
        data = {
            self._label("variable"): [],
            self._label("group"): [],
            self._label("coefficient"): [],
            self._label("std_error"): [],
            self._label("p_value"): [],
            self._label("significant"): [],
            self._label("contribution_pct"): [],
        }

        # Create contribution lookup
        contrib_lookup = {c["variable"]: c for c in self.result.contributions}

        for coef in self.result.coefficients:
            var_name = coef["variable"]
            # Translate special variable names for display
            display_name = self._translate_variable(var_name)
            data[self._label("variable")].append(display_name)
            data[self._label("group")].append(self.variable_groups.get(var_name, ""))
            data[self._label("coefficient")].append(coef["estimate"])
            data[self._label("std_error")].append(coef.get("std_error", ""))
            data[self._label("p_value")].append(coef.get("p_value", ""))

            sig = coef.get("is_significant")
            if sig is True:
                data[self._label("significant")].append(self._label("yes"))
            elif sig is False:
                data[self._label("significant")].append(self._label("no"))
            else:
                data[self._label("significant")].append("")

            # Add contribution %
            contrib = contrib_lookup.get(var_name, {})
            data[self._label("contribution_pct")].append(contrib.get("contribution_pct", ""))

        df = pd.DataFrame(data)
        df.to_excel(writer, sheet_name=self._label("sheet_coefficients"), index=False)

    def _write_decomposition_pivot_sheet(self, writer: pd.ExcelWriter) -> None:
        """
        Write decomposition in pivot format.

        Columns: Date, Variable, Group, Type (support/decomp), Value
        """
        decomp = self.result.decomposition
        dates = decomp.get("dates", [])
        actual = decomp.get("actual", [])
        predicted = decomp.get("predicted", [])
        base = decomp.get("base", [])
        contributions = decomp.get("contributions", {})
        support_values = decomp.get("support_values", {})
        decomp.get("transformed_values", {})

        rows = []

        for i, date in enumerate(dates):
            # Actual values
            rows.append(
                {
                    self._label("date"): date,
                    self._label("variable"): self._label("actual"),
                    self._label("group"): "",
                    self._label("type"): "",
                    self._label("value"): actual[i] if i < len(actual) else None,
                }
            )

            # Predicted values
            rows.append(
                {
                    self._label("date"): date,
                    self._label("variable"): self._label("predicted"),
                    self._label("group"): "",
                    self._label("type"): "",
                    self._label("value"): predicted[i] if i < len(predicted) else None,
                }
            )

            # Intercept (base)
            rows.append(
                {
                    self._label("date"): date,
                    self._label("variable"): self._label("intercept"),
                    self._label("group"): "",
                    self._label("type"): self._label("decomp"),
                    self._label("value"): base[i] if i < len(base) else None,
                }
            )

            # Feature contributions and support values
            for var_name, values in contributions.items():
                group_name = self.variable_groups.get(var_name, "")
                # Translate special variable names
                display_name = self._translate_variable(var_name)

                # Support value (original or transformed)
                if var_name in support_values:
                    support_val = support_values[var_name]
                    rows.append(
                        {
                            self._label("date"): date,
                            self._label("variable"): display_name,
                            self._label("group"): group_name,
                            self._label("type"): self._label("support"),
                            self._label("value"): support_val[i] if i < len(support_val) else None,
                        }
                    )

                # Decomp value (incremental contribution)
                rows.append(
                    {
                        self._label("date"): date,
                        self._label("variable"): display_name,
                        self._label("group"): group_name,
                        self._label("type"): self._label("decomp"),
                        self._label("value"): values[i] if i < len(values) else None,
                    }
                )

        df = pd.DataFrame(rows)
        df.to_excel(writer, sheet_name=self._label("sheet_decomposition"), index=False)

    def _write_summary_sheet(self, writer: pd.ExcelWriter) -> None:
        """Write summary sheet."""
        summary_data = {
            "Property": [
                "Model Name",
                "Model Type",
                "Created At",
                "Training Duration (s)",
                "N Observations",
                "N Features",
                "R-Squared",
                "MAPE (%)",
            ],
            "Value": [
                self.result.model_name,
                self.result.model_type,
                self.result.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                f"{self.result.training_duration_seconds:.2f}",
                self.result.metrics.get("n_observations", ""),
                self.result.metrics.get("n_features", ""),
                f"{self.result.metrics.get('r_squared', 0):.4f}",
                f"{self.result.metrics.get('mape', 0):.2f}",
            ],
        }

        df = pd.DataFrame(summary_data)
        df.to_excel(writer, sheet_name="Summary", index=False)

    def _write_metrics_sheet(self, writer: pd.ExcelWriter) -> None:
        """Write metrics sheet."""
        metrics = self.result.metrics

        metrics_data = {
            "Metric": [],
            "Value": [],
            "Description": [],
        }

        metric_info = [
            ("r_squared", "R-Squared", "Proportion of variance explained"),
            (
                "adjusted_r_squared",
                "Adjusted R-Squared",
                "R² adjusted for number of predictors",
            ),
            ("rmse", "RMSE", "Root Mean Square Error"),
            ("mape", "MAPE (%)", "Mean Absolute Percentage Error"),
            ("aic", "AIC", "Akaike Information Criterion"),
            ("bic", "BIC", "Bayesian Information Criterion"),
        ]

        for key, label, desc in metric_info:
            value = metrics.get(key)
            if value is not None:
                metrics_data["Metric"].append(label)
                metrics_data["Value"].append(value)
                metrics_data["Description"].append(desc)

        df = pd.DataFrame(metrics_data)
        df.to_excel(writer, sheet_name="Metrics", index=False)

    def _write_coefficients_sheet(self, writer: pd.ExcelWriter) -> None:
        """Write coefficients sheet."""
        df = pd.DataFrame(self.result.coefficients)
        df.columns = [
            "Variable",
            "Estimate",
            "Std Error",
            "T-Statistic",
            "P-Value",
            "CI Lower",
            "CI Upper",
            "Significant",
        ]
        df.to_excel(writer, sheet_name="Coefficients", index=False)

    def _write_contributions_sheet(self, writer: pd.ExcelWriter) -> None:
        """Write contributions sheet."""
        df = pd.DataFrame(self.result.contributions)
        df.columns = [
            "Variable",
            "Total Contribution",
            "Contribution %",
            "Avg Contribution",
            "ROI",
            "Marginal ROI",
        ]
        df.to_excel(writer, sheet_name="Contributions", index=False)

    def _write_decomposition_sheet(self, writer: pd.ExcelWriter) -> None:
        """Write decomposition sheet."""
        decomp = self.result.decomposition

        data = {
            "Date": decomp.get("dates", []),
            "Actual": decomp.get("actual", []),
            "Predicted": decomp.get("predicted", []),
            "Base": decomp.get("base", []),
        }

        for channel, values in decomp.get("contributions", {}).items():
            data[channel] = values

        df = pd.DataFrame(data)
        df.to_excel(writer, sheet_name="Decomposition", index=False)

    def _write_response_curves_sheet(self, writer: pd.ExcelWriter) -> None:
        """Write response curves sheet."""
        for channel, curve in self.result.response_curves.items():
            data = {
                "Spend": curve.get("spend_levels", []),
                "Response": curve.get("response_values", []),
                "Marginal Response": curve.get("marginal_response", []),
                "ROI": curve.get("roi_values", []),
            }
            df = pd.DataFrame(data)

            # Sheet name max 31 chars
            sheet_name = f"RC_{channel}"[:31]
            df.to_excel(writer, sheet_name=sheet_name, index=False)

    def _write_diagnostics_sheet(self, writer: pd.ExcelWriter) -> None:
        """Write diagnostics sheet."""
        diag = self.result.diagnostics

        # VIF table
        vif_data = {
            "Variable": list(diag.get("vif", {}).keys()),
            "VIF": list(diag.get("vif", {}).values()),
        }
        df_vif = pd.DataFrame(vif_data)
        df_vif.to_excel(writer, sheet_name="Diagnostics", index=False, startrow=0)

        # Other diagnostics
        other_diag = {
            "Diagnostic": [],
            "Value": [],
        }

        if diag.get("durbin_watson") is not None:
            other_diag["Diagnostic"].append("Durbin-Watson")
            other_diag["Value"].append(diag["durbin_watson"])

        if diag.get("jarque_bera_pvalue") is not None:
            other_diag["Diagnostic"].append("Jarque-Bera P-Value")
            other_diag["Value"].append(diag["jarque_bera_pvalue"])

        if diag.get("skewness") is not None:
            other_diag["Diagnostic"].append("Skewness")
            other_diag["Value"].append(diag["skewness"])

        if diag.get("kurtosis") is not None:
            other_diag["Diagnostic"].append("Kurtosis")
            other_diag["Value"].append(diag["kurtosis"])

        if other_diag["Diagnostic"]:
            df_other = pd.DataFrame(other_diag)
            df_other.to_excel(
                writer,
                sheet_name="Diagnostics",
                index=False,
                startrow=len(df_vif) + 3,
            )

    def to_json(self, indent: int = 2) -> str:
        """
        Export to JSON format.

        Args:
            indent: JSON indentation level

        Returns:
            JSON string
        """
        return json.dumps(self.result.to_dict(), indent=indent, default=str)

    def to_html_report(self) -> str:
        """
        Generate HTML report.

        Returns:
            HTML string
        """
        metrics = self.result.metrics

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>MMM Results Report - {self.result.model_name}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        h1 {{ color: #333; }}
        h2 {{ color: #666; border-bottom: 1px solid #ccc; padding-bottom: 5px; }}
        table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #4E79A7; color: white; }}
        tr:nth-child(even) {{ background-color: #f2f2f2; }}
        .metric-value {{ font-size: 24px; font-weight: bold; color: #4E79A7; }}
        .metric-card {{ display: inline-block; padding: 20px; margin: 10px;
                       background: #f9f9f9; border-radius: 5px; text-align: center; }}
        .good {{ color: #59A14F; }}
        .warning {{ color: #F28E2B; }}
        .bad {{ color: #E15759; }}
    </style>
</head>
<body>
    <h1>Marketing Mix Model Results</h1>
    <p><strong>Model:</strong> {self.result.model_name} ({self.result.model_type})</p>
    <p><strong>Generated:</strong> {self.result.created_at.strftime("%Y-%m-%d %H:%M:%S")}</p>

    <h2>Model Performance</h2>
    <div class="metric-card">
        <div class="metric-value">{metrics.get("r_squared", 0):.1%}</div>
        <div>R-Squared</div>
    </div>
    <div class="metric-card">
        <div class="metric-value">{metrics.get("mape", 0):.1f}%</div>
        <div>MAPE</div>
    </div>
    <div class="metric-card">
        <div class="metric-value">{metrics.get("rmse", 0):,.0f}</div>
        <div>RMSE</div>
    </div>

    <h2>Channel Contributions</h2>
    <table>
        <tr>
            <th>Channel</th>
            <th>Contribution %</th>
            <th>Total Contribution</th>
            <th>ROI</th>
        </tr>
        {"".join(self._contribution_row(c) for c in self.result.contributions)}
    </table>

    <h2>Coefficient Estimates</h2>
    <table>
        <tr>
            <th>Variable</th>
            <th>Estimate</th>
            <th>Std Error</th>
            <th>P-Value</th>
            <th>Significant</th>
        </tr>
        {"".join(self._coefficient_row(c) for c in self.result.coefficients)}
    </table>

    <h2>Diagnostics</h2>
    {self._diagnostics_html()}

    <footer style="margin-top: 40px; color: #999; font-size: 12px;">
        Generated by Marketing Mix Model Platform
    </footer>
</body>
</html>
"""
        return html

    def _contribution_row(self, contrib: dict) -> str:
        """Generate HTML table row for contribution."""
        return f"""
        <tr>
            <td>{contrib["variable"]}</td>
            <td>{contrib["contribution_pct"]:.1f}%</td>
            <td>{contrib["total_contribution"]:,.0f}</td>
            <td>{contrib.get("roi", "-")}</td>
        </tr>
        """

    def _coefficient_row(self, coef: dict) -> str:
        """Generate HTML table row for coefficient."""
        sig_class = "good" if coef.get("is_significant") else ""
        sig_text = "Yes" if coef.get("is_significant") else "No" if coef.get("is_significant") is not None else "-"

        return f"""
        <tr class="{sig_class}">
            <td>{coef["variable"]}</td>
            <td>{coef["estimate"]:.4f}</td>
            <td>{coef.get("std_error", "-")}</td>
            <td>{coef.get("p_value", "-")}</td>
            <td>{sig_text}</td>
        </tr>
        """

    def _diagnostics_html(self) -> str:
        """Generate diagnostics HTML section."""
        diag = self.result.diagnostics

        html = "<table><tr><th>Diagnostic</th><th>Value</th><th>Status</th></tr>"

        # Durbin-Watson
        dw = diag.get("durbin_watson")
        if dw is not None:
            status = "good" if 1.5 <= dw <= 2.5 else "warning"
            dw_status_text = "OK" if status == "good" else "Check"
            html += f'<tr class="{status}"><td>Durbin-Watson</td><td>{dw:.2f}</td><td>{dw_status_text}</td></tr>'

        # Jarque-Bera
        jb = diag.get("jarque_bera_pvalue")
        if jb is not None:
            status = "good" if jb >= 0.05 else "warning"
            jb_status_text = "OK" if status == "good" else "Check"
            html += f'<tr class="{status}"><td>Jarque-Bera P-Value</td><td>{jb:.4f}</td><td>{jb_status_text}</td></tr>'

        html += "</table>"

        # VIF
        vif = diag.get("vif", {})
        if vif:
            html += "<h3>Variance Inflation Factors</h3><table><tr><th>Variable</th><th>VIF</th><th>Status</th></tr>"
            for var, value in vif.items():
                status = "good" if value < 5 else "warning" if value < 10 else "bad"
                vif_text = "OK" if value < 10 else "High"
                html += f'<tr class="{status}"><td>{var}</td><td>{value:.2f}</td><td>{vif_text}</td></tr>'
            html += "</table>"

        return html
