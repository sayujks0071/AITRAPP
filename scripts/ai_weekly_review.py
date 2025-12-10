#!/usr/bin/env python3
"""
Generate weekly AI-powered trading review.
Reads recent backtests and live logs, then uses OpenAI/Gemini to generate insights.
Called by weekly-ai-review.yml workflow.
"""
import argparse
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional


def load_recent_backtests(backtest_dir: Path, lookback_days: int = 7) -> List[Dict]:
    """Load recent backtest summaries."""
    backtests = []
    cutoff_date = datetime.now() - timedelta(days=lookback_days)
    
    for file in sorted(backtest_dir.glob("*_summary.md"), reverse=True):
        try:
            # Extract date from filename
            date_str = file.stem.replace("_summary", "")
            file_date = datetime.strptime(date_str, "%Y-%m-%d")
            
            if file_date >= cutoff_date:
                content = file.read_text()
                backtests.append({
                    "date": date_str,
                    "content": content,
                    "file": str(file)
                })
        except Exception as e:
            print(f"⚠️ Failed to parse {file}: {e}")
    
    return backtests


def call_openai_api(prompt: str, api_key: str) -> Optional[str]:
    """Call OpenAI API for analysis."""
    try:
        from openai import OpenAI
        
        client = OpenAI(api_key=api_key)
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # Cost-effective for summaries
            messages=[
                {
                    "role": "system",
                    "content": "You are a trading operations analyst. Provide concise, actionable insights based on backtest data."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.3,
            max_tokens=1500
        )
        
        return response.choices[0].message.content
        
    except ImportError:
        print("⚠️ OpenAI package not installed. Install with: pip install openai")
        return None
    except Exception as e:
        print(f"⚠️ OpenAI API error: {e}")
        return None


def call_gemini_api(prompt: str, api_key: str) -> Optional[str]:
    """Call Gemini API for analysis."""
    try:
        import google.generativeai as genai
        
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')  # Fast and cost-effective
        
        response = model.generate_content(prompt)
        return response.text
        
    except ImportError:
        print("⚠️ Google Generative AI package not installed. Install with: pip install google-generativeai")
        return None
    except Exception as e:
        print(f"⚠️ Gemini API error: {e}")
        return None


def generate_weekly_review(
    backtests: List[Dict],
    output_path: Path,
    lookback_days: int
) -> None:
    """Generate weekly AI review."""
    
    if not backtests:
        print("⚠️ No recent backtest data found. Skipping AI review.")
        return
    
    # Build prompt
    prompt_parts = [
        "# Weekly Trading Performance Review",
        "",
        "## Recent Backtest Data",
        "",
    ]
    
    for bt in backtests:
        prompt_parts.extend([
            f"### {bt['date']}",
            bt['content'],
            "",
        ])
    
    prompt_parts.extend([
        "## Analysis Request",
        "",
        "Please provide:",
        "1. **Performance Summary**: Overall returns, win rates, drawdowns",
        "2. **Strategy Analysis**: Which strategies performed best/worst",
        "3. **Risk Assessment**: Drawdown patterns, trade frequency",
        "4. **Recommendations**: Suggested parameter adjustments or strategy focus",
        "5. **Market Context**: Any notable patterns or anomalies",
        "",
        "Keep the analysis concise (500-800 words) and actionable.",
    ])
    
    prompt = "\n".join(prompt_parts)
    
    # Try Gemini first (if available), then OpenAI
    review_text = None
    api_used = None
    
    gemini_key = os.getenv("GEMINI_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")
    
    if gemini_key:
        print("🤖 Using Gemini API...")
        review_text = call_gemini_api(prompt, gemini_key)
        api_used = "Gemini 1.5 Flash"
    
    if not review_text and openai_key:
        print("🤖 Using OpenAI API...")
        review_text = call_openai_api(prompt, openai_key)
        api_used = "OpenAI GPT-4o-mini"
    
    if not review_text:
        print("⚠️ No AI API keys available. Generating basic summary...")
        review_text = generate_basic_summary(backtests)
        api_used = "Basic (no AI)"
    
    # Generate markdown report
    week_str = datetime.now().strftime("%Y-W%V")
    report_lines = [
        f"# Weekly AI Trading Review - Week {week_str}",
        "",
        f"**Generated:** {datetime.now().isoformat()}",
        f"**AI Model:** {api_used}",
        "",
        "## Executive Summary",
        "",
        review_text,
        "",
        "## Data Sources",
        "",
        f"- **Backtests Analyzed:** {len(backtests)}",
        f"- **Lookback Period:** {lookback_days} days",
        "",
        "### Recent Backtest Dates:",
        "",
    ]
    
    for bt in backtests:
        report_lines.append(f"- {bt['date']}")
    
    report_lines.extend([
        "",
        "---",
        "",
        "*This report is automatically generated by the weekly-ai-review workflow.*",
        "*For detailed backtest results, see the nightly-backtest artifacts.*",
    ])
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(report_lines))
    print(f"✅ Weekly review written to {output_path}")


def generate_basic_summary(backtests: List[Dict]) -> str:
    """Generate a basic summary without AI."""
    return f"""
## Basic Summary

Analyzed {len(backtests)} recent backtest(s).

**Note:** AI analysis unavailable. Install OpenAI or Gemini API keys for detailed insights.

To enable AI reviews:
1. Add `OPENAI_API_KEY` or `GEMINI_API_KEY` to GitHub Secrets
2. Re-run the workflow

Recent backtest dates: {', '.join(bt['date'] for bt in backtests)}
"""


def main():
    parser = argparse.ArgumentParser(description="Generate weekly AI trading review")
    parser.add_argument(
        "--output",
        type=str,
        required=True,
        help="Output markdown file path"
    )
    parser.add_argument(
        "--backtest-dir",
        type=str,
        default="reports/backtests",
        help="Directory containing backtest summaries"
    )
    parser.add_argument(
        "--lookback-days",
        type=int,
        default=7,
        help="Number of days to look back for backtest data"
    )
    
    args = parser.parse_args()
    
    backtest_dir = Path(args.backtest_dir)
    if not backtest_dir.exists():
        print(f"⚠️ Backtest directory not found: {backtest_dir}")
        return
    
    backtests = load_recent_backtests(backtest_dir, args.lookback_days)
    
    generate_weekly_review(
        backtests=backtests,
        output_path=Path(args.output),
        lookback_days=args.lookback_days
    )


if __name__ == "__main__":
    main()


"""
Generate weekly AI-powered trading review.
Reads recent backtests and live logs, then uses OpenAI/Gemini to generate insights.
Called by weekly-ai-review.yml workflow.
"""
import argparse
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional


def load_recent_backtests(backtest_dir: Path, lookback_days: int = 7) -> List[Dict]:
    """Load recent backtest summaries."""
    backtests = []
    cutoff_date = datetime.now() - timedelta(days=lookback_days)
    
    for file in sorted(backtest_dir.glob("*_summary.md"), reverse=True):
        try:
            # Extract date from filename
            date_str = file.stem.replace("_summary", "")
            file_date = datetime.strptime(date_str, "%Y-%m-%d")
            
            if file_date >= cutoff_date:
                content = file.read_text()
                backtests.append({
                    "date": date_str,
                    "content": content,
                    "file": str(file)
                })
        except Exception as e:
            print(f"⚠️ Failed to parse {file}: {e}")
    
    return backtests


def call_openai_api(prompt: str, api_key: str) -> Optional[str]:
    """Call OpenAI API for analysis."""
    try:
        from openai import OpenAI
        
        client = OpenAI(api_key=api_key)
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # Cost-effective for summaries
            messages=[
                {
                    "role": "system",
                    "content": "You are a trading operations analyst. Provide concise, actionable insights based on backtest data."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.3,
            max_tokens=1500
        )
        
        return response.choices[0].message.content
        
    except ImportError:
        print("⚠️ OpenAI package not installed. Install with: pip install openai")
        return None
    except Exception as e:
        print(f"⚠️ OpenAI API error: {e}")
        return None


def call_gemini_api(prompt: str, api_key: str) -> Optional[str]:
    """Call Gemini API for analysis."""
    try:
        import google.generativeai as genai
        
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')  # Fast and cost-effective
        
        response = model.generate_content(prompt)
        return response.text
        
    except ImportError:
        print("⚠️ Google Generative AI package not installed. Install with: pip install google-generativeai")
        return None
    except Exception as e:
        print(f"⚠️ Gemini API error: {e}")
        return None


def generate_weekly_review(
    backtests: List[Dict],
    output_path: Path,
    lookback_days: int
) -> None:
    """Generate weekly AI review."""
    
    if not backtests:
        print("⚠️ No recent backtest data found. Skipping AI review.")
        return
    
    # Build prompt
    prompt_parts = [
        "# Weekly Trading Performance Review",
        "",
        "## Recent Backtest Data",
        "",
    ]
    
    for bt in backtests:
        prompt_parts.extend([
            f"### {bt['date']}",
            bt['content'],
            "",
        ])
    
    prompt_parts.extend([
        "## Analysis Request",
        "",
        "Please provide:",
        "1. **Performance Summary**: Overall returns, win rates, drawdowns",
        "2. **Strategy Analysis**: Which strategies performed best/worst",
        "3. **Risk Assessment**: Drawdown patterns, trade frequency",
        "4. **Recommendations**: Suggested parameter adjustments or strategy focus",
        "5. **Market Context**: Any notable patterns or anomalies",
        "",
        "Keep the analysis concise (500-800 words) and actionable.",
    ])
    
    prompt = "\n".join(prompt_parts)
    
    # Try Gemini first (if available), then OpenAI
    review_text = None
    api_used = None
    
    gemini_key = os.getenv("GEMINI_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")
    
    if gemini_key:
        print("🤖 Using Gemini API...")
        review_text = call_gemini_api(prompt, gemini_key)
        api_used = "Gemini 1.5 Flash"
    
    if not review_text and openai_key:
        print("🤖 Using OpenAI API...")
        review_text = call_openai_api(prompt, openai_key)
        api_used = "OpenAI GPT-4o-mini"
    
    if not review_text:
        print("⚠️ No AI API keys available. Generating basic summary...")
        review_text = generate_basic_summary(backtests)
        api_used = "Basic (no AI)"
    
    # Generate markdown report
    week_str = datetime.now().strftime("%Y-W%V")
    report_lines = [
        f"# Weekly AI Trading Review - Week {week_str}",
        "",
        f"**Generated:** {datetime.now().isoformat()}",
        f"**AI Model:** {api_used}",
        "",
        "## Executive Summary",
        "",
        review_text,
        "",
        "## Data Sources",
        "",
        f"- **Backtests Analyzed:** {len(backtests)}",
        f"- **Lookback Period:** {lookback_days} days",
        "",
        "### Recent Backtest Dates:",
        "",
    ]
    
    for bt in backtests:
        report_lines.append(f"- {bt['date']}")
    
    report_lines.extend([
        "",
        "---",
        "",
        "*This report is automatically generated by the weekly-ai-review workflow.*",
        "*For detailed backtest results, see the nightly-backtest artifacts.*",
    ])
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(report_lines))
    print(f"✅ Weekly review written to {output_path}")


def generate_basic_summary(backtests: List[Dict]) -> str:
    """Generate a basic summary without AI."""
    return f"""
## Basic Summary

Analyzed {len(backtests)} recent backtest(s).

**Note:** AI analysis unavailable. Install OpenAI or Gemini API keys for detailed insights.

To enable AI reviews:
1. Add `OPENAI_API_KEY` or `GEMINI_API_KEY` to GitHub Secrets
2. Re-run the workflow

Recent backtest dates: {', '.join(bt['date'] for bt in backtests)}
"""


def main():
    parser = argparse.ArgumentParser(description="Generate weekly AI trading review")
    parser.add_argument(
        "--output",
        type=str,
        required=True,
        help="Output markdown file path"
    )
    parser.add_argument(
        "--backtest-dir",
        type=str,
        default="reports/backtests",
        help="Directory containing backtest summaries"
    )
    parser.add_argument(
        "--lookback-days",
        type=int,
        default=7,
        help="Number of days to look back for backtest data"
    )
    
    args = parser.parse_args()
    
    backtest_dir = Path(args.backtest_dir)
    if not backtest_dir.exists():
        print(f"⚠️ Backtest directory not found: {backtest_dir}")
        return
    
    backtests = load_recent_backtests(backtest_dir, args.lookback_days)
    
    generate_weekly_review(
        backtests=backtests,
        output_path=Path(args.output),
        lookback_days=args.lookback_days
    )


if __name__ == "__main__":
    main()




