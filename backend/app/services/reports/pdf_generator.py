"""PDF report generation for Marketing Mix Model results."""

import io
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


class PDFReportGenerator:
    """
    Generate PDF reports for MMM results.

    Creates professional PDF reports containing:
    - Executive summary
    - Model metrics
    - Coefficient table
    - Contribution analysis
    - Diagnostic information
    """

    def __init__(
        self,
        title: str = "Marketing Mix Model Report",
        page_size: str = "letter",
    ):
        self.title = title
        self.page_size = letter if page_size == "letter" else A4
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()

    def _setup_custom_styles(self):
        """Setup custom paragraph styles."""
        self.styles.add(
            ParagraphStyle(
                name="CustomTitle",
                parent=self.styles["Heading1"],
                fontSize=24,
                spaceAfter=30,
                alignment=TA_CENTER,
                textColor=colors.HexColor("#1a365d"),
            )
        )

        self.styles.add(
            ParagraphStyle(
                name="SectionHeader",
                parent=self.styles["Heading2"],
                fontSize=14,
                spaceBefore=20,
                spaceAfter=10,
                textColor=colors.HexColor("#2c5282"),
            )
        )

        self.styles.add(
            ParagraphStyle(
                name="SubHeader",
                parent=self.styles["Heading3"],
                fontSize=12,
                spaceBefore=15,
                spaceAfter=8,
                textColor=colors.HexColor("#4a5568"),
            )
        )

        self.styles.add(
            ParagraphStyle(
                name="MetricValue",
                parent=self.styles["Normal"],
                fontSize=18,
                alignment=TA_CENTER,
                textColor=colors.HexColor("#2b6cb0"),
            )
        )

    def _create_header(self, model_name: str, project_name: str) -> list:
        """Create report header elements."""
        elements = []

        elements.append(Paragraph(self.title, self.styles["CustomTitle"]))
        elements.append(Spacer(1, 0.1 * inch))

        info_text = f"""
        <b>Model:</b> {model_name}<br/>
        <b>Project:</b> {project_name}<br/>
        <b>Generated:</b> {datetime.now().strftime("%Y-%m-%d %H:%M")}
        """
        elements.append(Paragraph(info_text, self.styles["Normal"]))
        elements.append(Spacer(1, 0.3 * inch))

        return elements

    def _create_executive_summary(self, metrics: dict, contributions: list) -> list:
        """Create executive summary section."""
        elements = []

        elements.append(Paragraph("Executive Summary", self.styles["SectionHeader"]))

        # Key metrics grid
        r_squared = metrics.get("r_squared", 0) * 100
        mape = metrics.get("mape", 0)
        rmse = metrics.get("rmse", 0)

        summary_data = [
            ["R-Squared", "MAPE", "RMSE"],
            [f"{r_squared:.1f}%", f"{mape:.1f}%", f"{rmse:,.0f}"],
        ]

        summary_table = Table(summary_data, colWidths=[2 * inch] * 3)
        summary_table.setStyle(
            TableStyle(
                [
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 10),
                    ("FONTSIZE", (0, 1), (-1, 1), 16),
                    ("TEXTCOLOR", (0, 1), (-1, 1), colors.HexColor("#2b6cb0")),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
                    ("TOPPADDING", (0, 0), (-1, -1), 12),
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f7fafc")),
                    ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#e2e8f0")),
                ]
            )
        )

        elements.append(summary_table)
        elements.append(Spacer(1, 0.2 * inch))

        # Top contributors
        if contributions:
            elements.append(Paragraph("Top Contributing Channels", self.styles["SubHeader"]))

            sorted_contribs = sorted(
                [c for c in contributions if c.get("variable") != "base"],
                key=lambda x: x.get("contribution_pct", 0),
                reverse=True,
            )[:5]

            contrib_text = ""
            for i, contrib in enumerate(sorted_contribs, 1):
                contrib_text += f"{i}. <b>{contrib['variable']}</b>: {contrib.get('contribution_pct', 0):.1f}%<br/>"

            elements.append(Paragraph(contrib_text, self.styles["Normal"]))

        return elements

    def _create_metrics_section(self, metrics: dict) -> list:
        """Create detailed metrics section."""
        elements = []

        elements.append(Paragraph("Model Performance Metrics", self.styles["SectionHeader"]))

        # Fit metrics table
        fit_data = [
            ["Metric", "Value", "Interpretation"],
            [
                "R-Squared",
                f"{metrics.get('r_squared', 0):.4f}",
                "Variance explained by model",
            ],
            [
                "Adjusted R²",
                f"{metrics.get('adjusted_r_squared', 0):.4f}",
                "R² adjusted for features",
            ],
            ["RMSE", f"{metrics.get('rmse', 0):,.2f}", "Root mean squared error"],
            ["MAE", f"{metrics.get('mae', 0):,.2f}", "Mean absolute error"],
            ["MAPE", f"{metrics.get('mape', 0):.2f}%", "Mean absolute % error"],
        ]

        if metrics.get("aic"):
            fit_data.append(["AIC", f"{metrics['aic']:,.0f}", "Akaike Information Criterion"])
        if metrics.get("bic"):
            fit_data.append(["BIC", f"{metrics['bic']:,.0f}", "Bayesian Information Criterion"])

        fit_table = Table(fit_data, colWidths=[1.5 * inch, 1.5 * inch, 3 * inch])
        fit_table.setStyle(
            TableStyle(
                [
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#edf2f7")),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ]
            )
        )

        elements.append(fit_table)

        return elements

    def _create_coefficients_section(
        self,
        coefficients: dict,
        std_errors: dict,
        p_values: dict,
        intercept: float,
    ) -> list:
        """Create coefficients table section."""
        elements = []

        elements.append(Paragraph("Model Coefficients", self.styles["SectionHeader"]))

        # Coefficients table
        coef_data = [["Variable", "Coefficient", "Std Error", "P-Value", "Significance"]]

        for var, coef in coefficients.items():
            se = std_errors.get(var, 0)
            pval = p_values.get(var, 1)

            # Significance stars
            if pval < 0.001:
                sig = "***"
            elif pval < 0.01:
                sig = "**"
            elif pval < 0.05:
                sig = "*"
            elif pval < 0.1:
                sig = "."
            else:
                sig = ""

            coef_data.append(
                [
                    var,
                    f"{coef:.4f}",
                    f"{se:.4f}" if se else "-",
                    f"{pval:.4f}" if pval < 1 else "-",
                    sig,
                ]
            )

        # Add intercept
        coef_data.append(["(Intercept)", f"{intercept:.2f}", "-", "-", ""])

        coef_table = Table(coef_data, colWidths=[2 * inch, 1.2 * inch, 1 * inch, 1 * inch, 0.8 * inch])
        coef_table.setStyle(
            TableStyle(
                [
                    ("ALIGN", (0, 0), (0, -1), "LEFT"),
                    ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#edf2f7")),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                    ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#f7fafc")),
                ]
            )
        )

        elements.append(coef_table)
        elements.append(Spacer(1, 0.1 * inch))
        elements.append(
            Paragraph(
                "<i>Significance codes: *** p&lt;0.001, ** p&lt;0.01, * p&lt;0.05, . p&lt;0.1</i>",
                self.styles["Normal"],
            )
        )

        return elements

    def _create_contributions_section(self, contributions: list) -> list:
        """Create contributions analysis section."""
        elements = []

        elements.append(Paragraph("Channel Contributions", self.styles["SectionHeader"]))

        # Contributions table
        contrib_data = [["Channel", "Contribution", "Percentage"]]

        sum(c.get("total_contribution", 0) for c in contributions if c.get("variable") != "base")

        # Sort by contribution percentage
        sorted_contribs = sorted(contributions, key=lambda x: x.get("contribution_pct", 0), reverse=True)

        for contrib in sorted_contribs:
            var = contrib.get("variable", "")
            total = contrib.get("total_contribution", 0)
            pct = contrib.get("contribution_pct", 0)

            contrib_data.append(
                [
                    var,
                    f"{total:,.0f}",
                    f"{pct:.1f}%",
                ]
            )

        contrib_table = Table(contrib_data, colWidths=[2.5 * inch, 2 * inch, 1.5 * inch])
        contrib_table.setStyle(
            TableStyle(
                [
                    ("ALIGN", (0, 0), (0, -1), "LEFT"),
                    ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#edf2f7")),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ]
            )
        )

        elements.append(contrib_table)

        return elements

    def _create_diagnostics_section(self, diagnostics: dict) -> list:
        """Create model diagnostics section."""
        elements = []

        elements.append(Paragraph("Model Diagnostics", self.styles["SectionHeader"]))

        # Diagnostics checks
        diag_items = []

        dw = diagnostics.get("durbin_watson")
        if dw is not None:
            status = "✓" if 1.5 <= dw <= 2.5 else "⚠"
            diag_items.append(f"{status} Durbin-Watson: {dw:.2f} (tests for autocorrelation)")

        jb = diagnostics.get("jarque_bera_pvalue")
        if jb is not None:
            status = "✓" if jb >= 0.05 else "⚠"
            diag_items.append(f"{status} Jarque-Bera p-value: {jb:.4f} (tests residual normality)")

        # VIF
        vif = diagnostics.get("vif", {})
        high_vif = [k for k, v in vif.items() if v > 5]
        if high_vif:
            diag_items.append(f"⚠ High VIF (>5) detected for: {', '.join(high_vif)}")
        else:
            diag_items.append("✓ No multicollinearity issues detected (VIF < 5)")

        diag_text = "<br/>".join(diag_items) if diag_items else "No diagnostic information available."
        elements.append(Paragraph(diag_text, self.styles["Normal"]))

        return elements

    def generate(
        self,
        model_name: str,
        project_name: str,
        model_result: dict,
        contributions: list,
    ) -> bytes:
        """
        Generate complete PDF report.

        Args:
            model_name: Name of the model.
            project_name: Name of the project.
            model_result: Model result dictionary.
            contributions: List of contribution dictionaries.

        Returns:
            PDF file as bytes.
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=self.page_size,
            rightMargin=0.75 * inch,
            leftMargin=0.75 * inch,
            topMargin=0.75 * inch,
            bottomMargin=0.75 * inch,
        )

        elements = []

        # Header
        elements.extend(self._create_header(model_name, project_name))

        # Executive Summary
        elements.extend(self._create_executive_summary(model_result, contributions))

        elements.append(PageBreak())

        # Metrics
        elements.extend(self._create_metrics_section(model_result))
        elements.append(Spacer(1, 0.3 * inch))

        # Coefficients
        elements.extend(
            self._create_coefficients_section(
                model_result.get("coefficients", {}),
                model_result.get("std_errors", {}),
                model_result.get("p_values", {}),
                model_result.get("intercept", 0),
            )
        )

        elements.append(PageBreak())

        # Contributions
        elements.extend(self._create_contributions_section(contributions))
        elements.append(Spacer(1, 0.3 * inch))

        # Diagnostics
        elements.extend(
            self._create_diagnostics_section(
                {
                    "durbin_watson": model_result.get("durbin_watson"),
                    "jarque_bera_pvalue": model_result.get("jarque_bera_pvalue"),
                    "vif": model_result.get("vif", {}),
                }
            )
        )

        # Build PDF
        doc.build(elements)

        buffer.seek(0)
        return buffer.read()


def generate_pdf_report(
    model_name: str,
    project_name: str,
    model_result: dict,
    contributions: list,
) -> bytes:
    """
    Convenience function to generate a PDF report.

    Args:
        model_name: Name of the model.
        project_name: Name of the project.
        model_result: Model result dictionary.
        contributions: List of contribution dictionaries.

    Returns:
        PDF file as bytes.
    """
    generator = PDFReportGenerator()
    return generator.generate(model_name, project_name, model_result, contributions)
