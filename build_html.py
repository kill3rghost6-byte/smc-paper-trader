import json

with open('all_portfolios_validation.json', 'r') as f:
    data = f.read()

html_content = f"""<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SMC Quant | نتایج بک‌تست واقعی 🚀</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Vazirmatn:wght@300;400;600;800&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-dark: #09090b;
            --bg-card: rgba(24, 24, 27, 0.85);
            --primary: #10b981;
            --danger: #ef4444;
            --accent: #6366f1;
            --text-main: #f4f4f5;
            --text-muted: #a1a1aa;
            --border: rgba(39, 39, 42, 0.6);
        }}

        body {{
            background-color: var(--bg-dark);
            color: var(--text-main);
            font-family: 'Vazirmatn', sans-serif;
            margin: 0;
            padding: 0;
            overflow-x: hidden;
            position: relative;
        }}

        /* Animated Background */
        .bg-animation {{
            position: fixed;
            top: 0; left: 0; width: 100vw; height: 100vh;
            z-index: -1;
            background: radial-gradient(circle at 15% 50%, rgba(16, 185, 129, 0.1), transparent 25%),
                        radial-gradient(circle at 85% 30%, rgba(99, 102, 241, 0.1), transparent 25%);
            animation: pulseBg 10s infinite alternate;
        }}

        @keyframes pulseBg {{
            0% {{ transform: scale(1); }}
            100% {{ transform: scale(1.1); }}
        }}

        /* Navbar / Tabs */
        .tabs-container {{
            position: sticky;
            top: 0;
            background: rgba(9, 9, 11, 0.9);
            backdrop-filter: blur(10px);
            z-index: 100;
            padding: 1rem 0;
            border-bottom: 1px solid var(--border);
            display: flex;
            justify-content: center;
            gap: 1rem;
            flex-wrap: wrap;
        }}

        .tab-btn {{
            background: transparent;
            color: var(--text-muted);
            border: 1px solid var(--border);
            padding: 0.8rem 1.5rem;
            border-radius: 50px;
            cursor: pointer;
            font-weight: 800;
            font-family: inherit;
            transition: 0.3s;
        }}

        .tab-btn:hover {{
            background: rgba(255,255,255,0.05);
            transform: translateY(-2px);
        }}

        .tab-btn.active {{
            background: rgba(16, 185, 129, 0.1);
            color: var(--primary);
            border-color: var(--primary);
            box-shadow: 0 0 15px rgba(16, 185, 129, 0.3);
        }}

        .header {{
            text-align: center;
            padding: 3rem 1rem;
            border-bottom: 1px solid var(--border);
            position: relative;
        }}

        .header h1 {{
            font-size: 2.5rem;
            margin-bottom: 1rem;
            background: linear-gradient(90deg, #10b981, #3b82f6);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}

        .gif-container {{
            display: flex;
            justify-content: center;
            flex-wrap: wrap;
            gap: 2rem;
            margin-top: 2rem;
        }}

        .gif-container img {{
            border-radius: 20px;
            box-shadow: 0 10px 30px rgba(16, 185, 129, 0.2);
            height: 120px;
            object-fit: cover;
        }}

        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 2rem;
        }}

        .stats-top {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 1.5rem;
            margin-bottom: 2rem;
        }}

        .stat-card {{
            background: var(--bg-card);
            backdrop-filter: blur(5px);
            border: 1px solid var(--border);
            border-radius: 20px;
            padding: 2rem;
            text-align: center;
            transition: 0.3s;
            position: relative;
            overflow: hidden;
        }}

        .stat-card:hover {{
            transform: translateY(-5px);
            border-color: var(--primary);
            box-shadow: 0 10px 40px rgba(16, 185, 129, 0.1);
        }}

        .stat-title {{ color: var(--text-muted); font-size: 1.1rem; margin-bottom: 0.5rem; }}
        .stat-val {{ font-size: 2.5rem; font-weight: 800; color: var(--text-main); }}
        .stat-val.green {{ color: var(--primary); text-shadow: 0 0 10px rgba(16, 185, 129, 0.3); }}



        .logs-section {{
            background: var(--bg-card);
            backdrop-filter: blur(5px);
            border: 1px solid var(--border);
            border-radius: 20px;
            padding: 2rem;
            margin-bottom: 3rem;
        }}

        .logs-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 2rem;
            border-bottom: 1px solid var(--border);
            padding-bottom: 1rem;
        }}

        .logs-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 1.5rem;
        }}

        .log-card {{
            background: rgba(0, 0, 0, 0.4);
            border: 1px solid var(--border);
            border-radius: 15px;
            padding: 1.5rem;
            transition: 0.3s;
        }}
        
        .log-card:hover {{
            background: rgba(255, 255, 255, 0.05);
            transform: scale(1.02);
            border-color: rgba(255,255,255,0.2);
        }}

        .log-card.positive {{ border-left: 4px solid var(--primary); }}
        .log-card.negative {{ border-left: 4px solid var(--danger); }}

        .month-title {{
            font-size: 1.2rem;
            font-weight: 800;
            display: flex;
            justify-content: space-between;
            margin-bottom: 1rem;
            padding-bottom: 0.5rem;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }}

        .coin-breakdown {{
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
            font-size: 0.9rem;
            color: var(--text-muted);
        }}

        /* Modal Styles */
        .modal-overlay {{
            position: fixed;
            top: 0; left: 0; width: 100vw; height: 100vh;
            background: rgba(0, 0, 0, 0.8);
            backdrop-filter: blur(10px);
            z-index: 1000;
            display: none;
            justify-content: center;
            align-items: center;
            opacity: 0;
            transition: opacity 0.3s ease;
        }}

        .modal-overlay.active {{
            display: flex;
            opacity: 1;
        }}

        .modal-content {{
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 20px;
            width: 90%;
            max-width: 600px;
            max-height: 80vh;
            overflow-y: auto;
            padding: 2rem;
            transform: translateY(20px) scale(0.95);
            transition: 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            box-shadow: 0 20px 50px rgba(0,0,0,0.5);
            position: relative;
        }}

        .modal-overlay.active .modal-content {{
            transform: translateY(0) scale(1);
        }}

        .modal-close {{
            position: absolute;
            top: 1rem;
            left: 1rem; /* RTL mode left side */
            background: rgba(255,255,255,0.1);
            border: none;
            color: #fff;
            width: 30px;
            height: 30px;
            border-radius: 50%;
            cursor: pointer;
            transition: 0.3s;
        }}
        
        .modal-close:hover {{
            background: var(--danger);
        }}

        .trade-table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 1rem;
            font-size: 0.9rem;
        }}

        .trade-table th, .trade-table td {{
            padding: 0.8rem;
            text-align: right;
            border-bottom: 1px solid rgba(255,255,255,0.05);
        }}

        .trade-table th {{
            color: var(--text-muted);
            font-weight: bold;
        }}

        .trade-table tr:hover {{
            background: rgba(255,255,255,0.02);
        }}
        
        .coin-row {{
            display: flex;
            justify-content: space-between;
            background: rgba(255,255,255,0.02);
            padding: 0.3rem 0.5rem;
            border-radius: 5px;
            cursor: pointer;
            transition: 0.2s;
        }}

        .coin-row:hover {{
            background: rgba(255,255,255,0.1);
            transform: translateX(-5px);
        }}

        .coin-row span.win {{ color: var(--primary); font-weight: bold; }}
        .coin-row span.loss {{ color: var(--danger); font-weight: bold; }}
    </style>
</head>
<body>
    <div class="bg-animation"></div>

    <div class="tabs-container" id="tabs">
        <!-- Generated via JS -->
    </div>

    <div class="header">
        <h1 id="page-title">اعتبارسنجی بک‌تست لایو ۳۶۵ روزه 💯</h1>
        <p id="page-subtitle" style="font-size: 1.2rem; color: var(--text-muted);">انتخاب پورتفولیو...</p>
        
        <div class="gif-container">
            <img src="https://media.giphy.com/media/xTiTnqUxyWbsAXq7Ju/giphy.gif" alt="Money Raining">
            <img src="https://media.giphy.com/media/trN9ht5RlE3Dcwavg2/giphy.gif" alt="Stonks">
            <img src="https://media.giphy.com/media/Y2ZUWLrTy63j9T6qrK/giphy.gif" alt="Rocket">
        </div>
    </div>

    <div class="container">
        
        <div class="stats-top">
            <div class="stat-card">
                <div class="stat-title">سرمایه اولیه 💵</div>
                <div class="stat-val">$10,000</div>
            </div>
            <div class="stat-card">
                <div class="stat-title">سرمایه نهایی 💰</div>
                <div class="stat-val green" id="stat-final">$--</div>
            </div>
            <div class="stat-card">
                <div class="stat-title">درصد رشد کل 🚀</div>
                <div class="stat-val green" id="stat-return">--%</div>
            </div>
            <div class="stat-card" style="grid-column: span 3; text-align: center; padding: 1rem;">
                <span style="color: var(--text-muted);">حداکثر افت (MDD): <b id="stat-mdd" style="color: var(--danger);">--%</b> 📉</span>
            </div>
        </div>



        <div class="logs-section">
            <div class="logs-header">
                <h2 style="margin:0;">گزارش ماه به ماه 📅</h2>
                <span id="win-months" style="background: rgba(16,185,129,0.1); color: var(--primary); padding: 0.5rem 1rem; border-radius: 10px;">--</span>
            </div>
            
            <div class="logs-grid" id="logsGrid">
                <!-- Injected via JS -->
            </div>
        </div>
    </div>

    <!-- Modal for Detailed Trades -->
    <div class="modal-overlay" id="tradesModal" onclick="closeModal(event)">
        <div class="modal-content" onclick="event.stopPropagation()">
            <button class="modal-close" onclick="closeModal(event)">✕</button>
            <h2 id="modalTitle" style="margin-top: 0; margin-bottom: 0.5rem; color: var(--primary);"></h2>
            <p id="modalSubtitle" style="color: var(--text-muted); font-size: 0.9rem; margin-bottom: 1.5rem;"></p>
            <div style="overflow-x: auto;">
                <table class="trade-table">
                    <thead>
                        <tr>
                            <th>تاریخ ورود</th>
                            <th>تاریخ خروج</th>
                            <th>نوع سیگنال</th>
                            <th>نوع سفارش</th>
                            <th>قیمت دقیق ورود</th>
                            <th>قیمت دقیق خروج</th>
                            <th>سود/ضرر ($)</th>
                        </tr>
                    </thead>
                    <tbody id="modalTradesBody">
                        <!-- Injected via JS -->
                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <script>
        const portfolios = {data};

        function getCoinEmoji(coin) {{
            if(coin.includes('BTC')) return '👑';
            if(coin.includes('DOGE')) return '🐶';
            if(coin.includes('TRX')) return '🔴';
            if(coin.includes('AVAX')) return '🔺';
            return '🪙';
        }}



        function initTabs() {{
            const tabsDiv = document.getElementById('tabs');
            portfolios.forEach((p, idx) => {{
                const btn = document.createElement('button');
                btn.className = idx === 0 ? 'tab-btn active' : 'tab-btn';
                btn.innerText = p.name;
                btn.onclick = () => loadPortfolio(idx);
                tabsDiv.appendChild(btn);
            }});
        }}

        function loadPortfolio(idx) {{
            // Update tabs
            document.querySelectorAll('.tab-btn').forEach((b, i) => b.className = i === idx ? 'tab-btn active' : 'tab-btn');

            const p = portfolios[idx];
            
            // Subtitle string
            const subtitleParts = Object.entries(p.weights).map(([k, v]) => `${{k}} (${{(v*100).toFixed(2)}}%) ${{getCoinEmoji(k)}}`);
            document.getElementById('page-subtitle').innerText = `ترکیب: ${{subtitleParts.join(' + ')}}`;

            // Stats
            const finalCap = 10000 + (10000 * (p.return / 100));
            document.getElementById('stat-final').innerText = '$' + Math.round(finalCap).toLocaleString();
            document.getElementById('stat-return').innerText = '+' + p.return.toFixed(1) + '%';
            document.getElementById('stat-mdd').innerText = p.mdd.toFixed(1) + '%';



            // Logs
            let winMonths = 0;
            const grid = document.getElementById('logsGrid');
            grid.innerHTML = '';
            
            p.logs.forEach(log => {{
                const isPositive = log.profit >= 0;
                if(isPositive && log.profit > 10) winMonths++;
                
                const cardClass = isPositive ? 'log-card positive' : 'log-card negative';
                const emoji = isPositive ? '🟢' : '🔴';
                const sign = isPositive ? '+' : '';

                let coinsHtml = '';
                for(const [coin, coinData] of Object.entries(log.coins)) {{
                    const pnl = coinData.pnl;
                    const tradesStr = encodeURIComponent(JSON.stringify(coinData.trades));
                    const coinClass = pnl >= 0 ? 'win' : 'loss';
                    const coinSign = pnl >= 0 ? '+' : '';
                    const titleStr = `${{coin.replace('USDT_', ' ')}} - ${{log.month}}`;
                    
                    coinsHtml += `
                        <div class="coin-row" onclick="openModal('${{titleStr}}', '${{tradesStr}}')">
                            <span>${{coin.replace('USDT_', ' ')}} ${{getCoinEmoji(coin)}}</span>
                            <span class="${{coinClass}}">${{coinSign}}$${{Math.round(pnl)}}</span>
                        </div>
                    `;
                }}

                grid.innerHTML += `
                    <div class="${{cardClass}}">
                        <div class="month-title">
                            <span>${{log.month}}</span>
                            <span style="color: ${{isPositive ? 'var(--primary)' : 'var(--danger)'}}">${{sign}}$${{Math.round(log.profit)}} ${{emoji}}</span>
                        </div>
                        <div style="font-size: 0.8rem; margin-bottom: 1rem; color: #888;">تعداد معاملات: ${{log.trades}}</div>
                        <div class="coin-breakdown">
                            ${{coinsHtml}}
                        </div>
                    </div>
                `;
            }});

            document.getElementById('win-months').innerText = `${{winMonths}} ماه سودده / ${{p.logs.length}} ماه`;
        }}

        function openModal(title, tradesStr) {{
            const trades = JSON.parse(decodeURIComponent(tradesStr));
            document.getElementById('modalTitle').innerText = title;
            document.getElementById('modalSubtitle').innerText = `تعداد کل معاملات این ماه: ${{trades.length}}`;
            
            const tbody = document.getElementById('modalTradesBody');
            tbody.innerHTML = '';
            
            if(trades.length === 0) {{
                tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; padding: 2rem;">معامله‌ای یافت نشد</td></tr>`;
            }} else {{
                trades.forEach(t => {{
                    const pnlClass = t.pnl >= 0 ? 'color: var(--primary)' : 'color: var(--danger)';
                    const pnlSign = t.pnl >= 0 ? '+' : '';
                    
                    let typeLabel = t.type;
                    if(t.type.includes('L')) typeLabel = 'Long 🟢';
                    if(t.type.includes('S')) typeLabel = 'Short 🔴';
                    
                    tbody.innerHTML += `
                        <tr>
                            <td dir="ltr" style="text-align: right;">${{t.entry_time.slice(5, 16)}}</td>
                            <td dir="ltr" style="text-align: right;">${{t.exit_time.slice(5, 16)}}</td>
                            <td dir="ltr" style="text-align: right;">${{typeLabel}}</td>
                            <td dir="ltr" style="text-align: right;">${{t.order_type}}</td>
                            <td dir="ltr" style="text-align: right;">$${{t.entry_price}}</td>
                            <td dir="ltr" style="text-align: right;">$${{t.exit_price}}</td>
                            <td dir="ltr" style="text-align: right; font-weight: bold; ${{pnlClass}}">${{pnlSign}}$${{t.pnl.toFixed(2)}}</td>
                        </tr>
                    `;
                }});
            }}
            
            document.getElementById('tradesModal').classList.add('active');
        }}

        function closeModal(e) {{
            if (e.target.id === 'tradesModal' || e.target.classList.contains('modal-close')) {{
                document.getElementById('tradesModal').classList.remove('active');
            }}
        }}

        window.onload = () => {{
            initTabs();
            loadPortfolio(0);
        }};
    </script>
</body>
</html>"""

with open('dashboard.html', 'w') as f:
    f.write(html_content)

print("Updated dashboard.html back to the clean, chart-less original design with horizontal tabs.")
