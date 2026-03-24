import datetime
from core.currency import fmt

def generate_html_report(metrics_dict: dict) -> str:
    """
    Generates a beautiful HTML report from the dashboard metrics.
    Includes glassmorphism CSS grid layouts and native dark mode media query support.
    """
    today_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    sections = []
    
    if "compound" in metrics_dict:
        m = metrics_dict["compound"]
        sections.append(f"""
        <div class="card">
            <h3>💰 复利投资预测</h3>
            <p>预测累计收益: <span class="highlight">{fmt(m.get('total_interest', 0), decimals=2)}</span></p>
            <p>最终资产规模: <span class="highlight">{fmt(m.get('final_balance', 0), decimals=2)}</span></p>
        </div>
        """)
        
    if "loan" in metrics_dict:
        m = metrics_dict["loan"]
        sections.append(f"""
        <div class="card">
            <h3>🏦 贷款负担评估</h3>
            <p>平均每期还款: <span class="highlight">{fmt(m.get('monthly_payment', 0), decimals=2)}</span></p>
            <p>总计利息支出: <span class="warn">{fmt(m.get('total_interest', 0), decimals=2)}</span></p>
        </div>
        """)

    if "savings" in metrics_dict:
        m = metrics_dict["savings"]
        months = m.get("months_needed", 0)
        y, mo = months // 12, months % 12
        sections.append(f"""
        <div class="card">
            <h3>🎯 储蓄达成路径</h3>
            <p>预计达成时长: <span class="highlight">{y}年{mo}个月</span></p>
            <p>复利利息贡献: <span class="highlight">{fmt(m.get('total_interest', 0), decimals=2)}</span></p>
        </div>
        """)

    if "budget" in metrics_dict:
        m = metrics_dict["budget"]
        sections.append(f"""
        <div class="card">
            <h3>💡 预算分配雷达</h3>
            <p>建议月储蓄额: <span class="highlight">{fmt(m.get('amt_save', 0), decimals=2)}</span></p>
            <p>核心储蓄比例: <strong>{m.get('pct_save', 0)}%</strong></p>
        </div>
        """)

    if "retirement" in metrics_dict:
        m = metrics_dict["retirement"]
        gap = m.get("gap", 0)
        status = "🏖️ ✅ 养老金库已充足，可安心规划" if gap <= 0 else f"🏖️ ⚠️ 退休资金缺口预警: <span class='warn'>{fmt(gap, decimals=2)}</span>"
        extra = f"<br>弥补缺口需额外月存: <span class='warn'>{fmt(m.get('extra_monthly', 0), decimals=2)}</span>" if gap > 0 else ""
        sections.append(f"""
        <div class="card">
            <h3>🏖️ 高级生命周期规划</h3>
            <p>{status} {extra}</p>
        </div>
        """)

    if "insurance" in metrics_dict:
        m = metrics_dict["insurance"]
        sections.append(f"""
        <div class="card">
            <h3>🛡️ 储蓄保险测算</h3>
            <p>核算总保费投入: <span class="highlight">{fmt(m.get('total_premium', 0), decimals=2)}</span></p>
            <p>综合安全收益率 (IRR): <span class="highlight">{m.get('irr_pct', 0):.2f}%</span></p>
        </div>
        """)

    if "networth" in metrics_dict:
        m = metrics_dict["networth"]
        sections.append(f"""
        <div class="card">
            <h3>🏠 全局资产净值监控</h3>
            <p>全盘资产评估: <span class="highlight">{fmt(m.get('total_assets', 0), decimals=2)}</span></p>
            <p>去杠杆核心净值: <span class="highlight">{fmt(m.get('net_worth', 0), decimals=2)}</span></p>
        </div>
        """)

    if not sections:
        sections.append("<div class='card' style='text-align:center;'><p><strong>未检测到交互数据记录。</strong><br>提示：请您先进入左侧任意子页面完成计算测评，稍后生成的报告将会自动捕获所有关联结果与雷达图数据。</p></div>")

    sections_html = "\n".join(sections)
    
    html_template = f"""
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>OmniFinance 综合财务体检报告</title>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;700&display=swap" rel="stylesheet">
        <style>
            :root {{
                --bg-color: #f9fafb;
                --text-color: #1f2937;
                --primary: #2563eb;
                --card-bg: #ffffff;
                --border: #e5e7eb;
                --warn: #dc2626;
            }}
            @media (prefers-color-scheme: dark) {{
                :root {{
                    --bg-color: #0f1115;
                    --text-color: #f3f4f6;
                    --primary: #3b82f6;
                    --card-bg: #1f2228;
                    --border: #374151;
                    --warn: #ef4444;
                }}
            }}
            body {{
                font-family: 'Inter', -apple-system, blinkmacsystemfont, sans-serif;
                background-color: var(--bg-color);
                color: var(--text-color);
                margin: 0;
                padding: 40px 20px;
                line-height: 1.6;
                transition: all 0.3s ease;
            }}
            .container {{
                max-width: 900px;
                margin: 0 auto;
            }}
            .header {{
                text-align: center;
                margin-bottom: 40px;
                padding-bottom: 25px;
                border-bottom: 1px solid var(--border);
            }}
            .header h1 {{
                font-size: 2.2rem;
                margin-bottom: 8px;
                letter-spacing: -0.02em;
            }}
            .header_gradient {{
                background: linear-gradient(90deg, var(--primary), #8b5cf6);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
            }}
            .subtitle {{
                font-size: 1.05rem;
                opacity: 0.7;
                margin-top: 0;
            }}
            .grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
                gap: 24px;
            }}
            .card {{
                background: var(--card-bg);
                border: 1px solid var(--border);
                border-radius: 12px;
                padding: 24px;
                box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
            }}
            .card h3 {{
                margin-top: 0;
                font-size: 1.15rem;
                border-bottom: 1px solid var(--border);
                padding-bottom: 12px;
                margin-bottom: 16px;
                color: var(--text-color);
            }}
            .card p {{
                margin: 10px 0;
                font-size: 0.95rem;
                opacity: 0.9;
            }}
            .highlight {{
                font-weight: 600;
                color: var(--primary);
                font-size: 1.05rem;
            }}
            .warn {{
                font-weight: 600;
                color: var(--warn);
                font-size: 1.05rem;
            }}
            .footer {{
                margin-top: 50px;
                text-align: center;
                font-size: 0.85rem;
                opacity: 0.5;
                padding-top: 25px;
                border-top: 1px solid var(--border);
            }}
            @media print {{
                body {{
                    background-color: #ffffff;
                    color: #000000;
                }}
                .card {{
                    box-shadow: none;
                    border: 1px solid #dddddd;
                    page-break-inside: avoid;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🌟 OmniFinance <span class="header_gradient">全局个人财务诊断体检</span></h1>
                <p class="subtitle">Empower Your Knowledge, Enrich Your Life</p>
                <p style="font-size: 0.9rem; opacity: 0.6; margin-top: 15px;">智能扫描生成时刻：{today_str}</p>
            </div>
            <div class="grid">
                {sections_html}
            </div>
            <div class="footer">
                <p>Eugene Finance 核心分析引擎技术生成 | 💡 温馨提示：当前报告结果仅用于财务辅助决策参考。</p>
            </div>
        </div>
    </body>
    </html>
    """
    return html_template
