"""Tests for report generation features."""

from io import BytesIO

import pytest

from app.services.reports.pdf_generator import PDFReportGenerator, generate_pdf_report
from app.services.reports.pptx_generator import (
    PPTXReportGenerator,
    generate_pptx_report,
)


class TestPDFReportGenerator:
    """Tests for PDF report generation."""

    @pytest.fixture
    def sample_model_result(self):
        """Sample model result for testing."""
        return {
            "model_type": "ridge",
            "r_squared": 0.85,
            "adj_r_squared": 0.83,
            "rmse": 150.5,
            "mae": 120.3,
            "mape": 0.08,
            "aic": 450.2,
            "bic": 480.5,
            "n_observations": 52,
            "coefficients": {
                "intercept": 1000,
                "tv_spend": 0.5,
                "digital_spend": 0.8,
                "print_spend": 0.3,
            },
            "std_errors": {
                "intercept": 50,
                "tv_spend": 0.05,
                "digital_spend": 0.04,
                "print_spend": 0.06,
            },
        }

    @pytest.fixture
    def sample_contributions(self):
        """Sample contributions data as list of dicts."""
        return [
            {"variable": "tv_spend", "contribution": 5230, "contribution_pct": 35.0},
            {
                "variable": "digital_spend",
                "contribution": 8180,
                "contribution_pct": 45.0,
            },
            {"variable": "print_spend", "contribution": 2955, "contribution_pct": 20.0},
        ]

    def test_generate_pdf_returns_bytes(self, sample_model_result, sample_contributions):
        """Test that PDF generation returns bytes."""
        generator = PDFReportGenerator()

        pdf_bytes = generator.generate(
            model_name="Test Model",
            project_name="Test Project",
            model_result=sample_model_result,
            contributions=sample_contributions,
        )

        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 0
        # PDF files start with %PDF
        assert pdf_bytes[:4] == b"%PDF"

    def test_generate_pdf_convenience_function(self, sample_model_result, sample_contributions):
        """Test the convenience function."""
        pdf_bytes = generate_pdf_report(
            model_name="Test Model",
            project_name="Test Project",
            model_result=sample_model_result,
            contributions=sample_contributions,
        )

        assert isinstance(pdf_bytes, bytes)
        assert pdf_bytes[:4] == b"%PDF"

    def test_generate_pdf_without_contributions(self, sample_model_result):
        """Test PDF generation without contributions."""
        pdf_bytes = generate_pdf_report(
            model_name="Test Model",
            project_name="Test Project",
            model_result=sample_model_result,
            contributions=[],
        )

        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 0

    def test_generate_pdf_with_minimal_data(self):
        """Test PDF generation with minimal data."""
        model_result = {
            "model_type": "ols",
            "r_squared": 0.5,
            "coefficients": {"intercept": 100},
        }

        pdf_bytes = generate_pdf_report(
            model_name="Minimal Model",
            project_name="Test Project",
            model_result=model_result,
            contributions=[],
        )

        assert isinstance(pdf_bytes, bytes)


class TestPPTXReportGenerator:
    """Tests for PowerPoint report generation."""

    @pytest.fixture
    def sample_model_result(self):
        """Sample model result for testing."""
        return {
            "model_type": "ridge",
            "metrics": {
                "r_squared": 0.85,
                "adj_r_squared": 0.83,
                "rmse": 150.5,
                "mae": 120.3,
                "mape": 0.08,
                "aic": 450.2,
                "bic": 480.5,
                "n_observations": 52,
            },
            "coefficients": {
                "intercept": 1000,
                "tv_spend": 0.5,
                "digital_spend": 0.8,
                "print_spend": 0.3,
                "radio_spend": 0.2,
            },
            "std_errors": {
                "intercept": 50,
                "tv_spend": 0.05,
                "digital_spend": 0.04,
                "print_spend": 0.06,
                "radio_spend": 0.08,
            },
        }

    @pytest.fixture
    def sample_contributions(self):
        """Sample contributions data."""
        return {
            "base": [1000] * 10,
            "tv_spend": [500, 550, 480, 520, 510, 530, 490, 540, 500, 520],
            "digital_spend": [800, 820, 780, 850, 810, 830, 790, 860, 800, 840],
            "print_spend": [300, 280, 310, 290, 300, 285, 305, 295, 300, 290],
            "radio_spend": [200, 210, 190, 205, 200, 215, 195, 208, 200, 205],
        }

    def test_generate_pptx_returns_bytes(self, sample_model_result, sample_contributions):
        """Test that PPTX generation returns bytes."""
        generator = PPTXReportGenerator(
            model_name="Test Model",
            project_name="Test Project",
            model_result=sample_model_result,
            contributions=sample_contributions,
        )

        pptx_bytes = generator.generate()

        assert isinstance(pptx_bytes, bytes)
        assert len(pptx_bytes) > 0
        # PPTX files are ZIP archives, start with PK
        assert pptx_bytes[:2] == b"PK"

    def test_generate_pptx_convenience_function(self, sample_model_result, sample_contributions):
        """Test the convenience function."""
        pptx_bytes = generate_pptx_report(
            model_name="Test Model",
            project_name="Test Project",
            model_result=sample_model_result,
            contributions=sample_contributions,
        )

        assert isinstance(pptx_bytes, bytes)
        assert pptx_bytes[:2] == b"PK"

    def test_generate_pptx_without_contributions(self, sample_model_result):
        """Test PPTX generation without contributions."""
        pptx_bytes = generate_pptx_report(
            model_name="Test Model",
            project_name="Test Project",
            model_result=sample_model_result,
            contributions=None,
        )

        assert isinstance(pptx_bytes, bytes)
        assert len(pptx_bytes) > 0

    def test_generate_pptx_with_minimal_data(self):
        """Test PPTX generation with minimal data."""
        model_result = {
            "model_type": "ols",
            "metrics": {"r_squared": 0.5},
            "coefficients": {"channel_a": 0.1},
        }

        pptx_bytes = generate_pptx_report(
            model_name="Minimal",
            project_name="Test",
            model_result=model_result,
            contributions=None,
        )

        assert isinstance(pptx_bytes, bytes)

    def test_pptx_contains_multiple_slides(self, sample_model_result, sample_contributions):
        """Test that generated PPTX contains multiple slides."""
        from pptx import Presentation

        pptx_bytes = generate_pptx_report(
            model_name="Test Model",
            project_name="Test Project",
            model_result=sample_model_result,
            contributions=sample_contributions,
        )

        # Load the generated PPTX
        prs = Presentation(BytesIO(pptx_bytes))

        # Should have multiple slides
        assert len(prs.slides) >= 5  # Title, Summary, Metrics, Contributions, Coefficients, etc.


class TestReportGenerationIntegration:
    """Integration tests for report generation."""

    def test_both_formats_generate_successfully(self):
        """Test that both PDF and PPTX generate for the same data."""
        model_result = {
            "model_type": "bayesian",
            "r_squared": 0.9,
            "mape": 0.05,
            "n_observations": 100,
            "coefficients": {"channel": 0.5},
        }
        # PDF expects list of dicts, PPTX expects dict of arrays
        pdf_contributions = [{"variable": "channel", "contribution": 1000, "contribution_pct": 100.0}]
        pptx_contributions = {"channel": [100] * 10}

        pdf_bytes = generate_pdf_report(
            model_name="Integration Test",
            project_name="Test Project",
            model_result=model_result,
            contributions=pdf_contributions,
        )

        pptx_bytes = generate_pptx_report(
            model_name="Integration Test",
            project_name="Test Project",
            model_result=model_result,
            contributions=pptx_contributions,
        )

        assert len(pdf_bytes) > 0
        assert len(pptx_bytes) > 0
        assert pdf_bytes[:4] == b"%PDF"
        assert pptx_bytes[:2] == b"PK"
