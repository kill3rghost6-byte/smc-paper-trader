import json

with open('all_portfolios_validation.json', 'r') as f:
    data = f.read()

html_content = f"""<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SMC Quant | پلتفرم مدیریت سرمایه هوشمند</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Vazirmatn:wght@300;400;600;800&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-dark: #050505;
            --bg-surface: #111111;
            --bg-card: rgba(24, 24, 27, 0.85);
            --primary: #00ffcc;
            --primary-glow: rgba(0, 255, 204, 0.4);
            --secondary: #7000ff;
            --text-main: #ffffff;
            --text-muted: #888888;
            --border: #222222;
            --danger: #ef4444;
        }}

        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: 'Vazirmatn', sans-serif;
        }}

        body {{
            background-color: var(--bg-dark);
            color: var(--text-main);
            overflow-x: hidden;
        }}

        /* --- Animated Background for Dashboard --- */
        .bg-animation {{
            position: fixed;
            top: 0; left: 0; width: 100vw; height: 100vh;
            z-index: -1;
            background: radial-gradient(circle at 15% 50%, rgba(0, 255, 204, 0.05), transparent 25%),
                        radial-gradient(circle at 85% 30%, rgba(112, 0, 255, 0.05), transparent 25%);
            animation: pulseBg 10s infinite alternate;
            display: none;
        }}

        @keyframes pulseBg {{
            0% {{ transform: scale(1); }}
            100% {{ transform: scale(1.1); }}
        }}

        /* --- Navigation --- */
        nav {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 1.5rem 4rem;
            border-bottom: 1px solid var(--border);
            background: rgba(5, 5, 5, 0.8);
            backdrop-filter: blur(10px);
            position: fixed;
            top: 0;
            width: 100%;
            z-index: 100;
        }}

        .logo {{
            font-size: 1.8rem;
            font-weight: 800;
            background: linear-gradient(90deg, var(--primary), #00b3ff);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}

        .nav-links button {{
            background: transparent;
            color: var(--text-main);
            border: none;
            cursor: pointer;
            font-size: 1rem;
            font-weight: 600;
            margin-right: 2rem;
            transition: 0.3s;
        }}

        .nav-links button:hover {{
            color: var(--primary);
        }}

        .login-btn {{
            background: var(--primary);
            color: #000 !important;
            padding: 0.6rem 1.5rem;
            border-radius: 30px;
            box-shadow: 0 0 15px var(--primary-glow);
        }}

        /* --- Landing Page --- */
        .landing {{
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            text-align: center;
            padding: 0 2rem;
            position: relative;
        }}

        .bg-glow {{
            position: absolute;
            width: 600px;
            height: 600px;
            background: radial-gradient(circle, var(--primary-glow) 0%, transparent 60%);
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            z-index: -1;
            filter: blur(50px);
            opacity: 0.5;
        }}

        .landing h1 {{
            font-size: 4rem;
            margin-bottom: 1rem;
            line-height: 1.2;
        }}

        .landing p {{
            font-size: 1.2rem;
            color: var(--text-muted);
            max-width: 600px;
            margin-bottom: 2.5rem;
        }}

        .cta-btn {{
            background: linear-gradient(90deg, var(--primary), #00b3ff);
            color: #000;
            border: none;
            padding: 1rem 3rem;
            font-size: 1.2rem;
            font-weight: 800;
            border-radius: 50px;
            cursor: pointer;
            box-shadow: 0 10px 30px var(--primary-glow);
            transition: 0.3s;
        }}

        .cta-btn:hover {{
            transform: translateY(-3px);
            box-shadow: 0 15px 40px var(--primary-glow);
        }}

        /* --- Auth Modal --- */
        .modal-overlay {{
            position: fixed;
            top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(0,0,0,0.8);
            backdrop-filter: blur(5px);
            display: flex;
            justify-content: center;
            align-items: center;
            z-index: 200;
            opacity: 0;
            pointer-events: none;
            transition: 0.3s;
        }}

        .modal-overlay.active {{
            opacity: 1;
            pointer-events: all;
        }}

        .auth-box {{
            background: var(--bg-surface);
            padding: 3rem;
            border-radius: 20px;
            border: 1px solid var(--border);
            width: 400px;
            text-align: center;
            transform: translateY(50px);
            transition: 0.3s;
        }}

        .modal-overlay.active .auth-box {{
            transform: translateY(0);
        }}

        .auth-box input {{
            width: 100%;
            padding: 1rem;
            margin-bottom: 1rem;
            background: var(--bg-dark);
            border: 1px solid var(--border);
            color: white;
            border-radius: 10px;
            font-family: inherit;
        }}

        .auth-box input:focus {{
            outline: none;
            border-color: var(--primary);
        }}

        /* --- Dashboard Container --- */
        .dashboard-container {{
            display: none;
            padding-top: 100px;
            min-height: 100vh;
        }}

        .dash-layout {{
            display: flex;
            max-width: 1400px;
            margin: 0 auto;
            gap: 2rem;
            padding: 0 2rem;
        }}

        /* Sidebar Tabs */
        .sidebar {{
            width: 300px;
            padding: 2rem;
            background: var(--bg-surface);
            border-radius: 20px;
            border: 1px solid var(--border);
            height: fit-content;
            position: sticky;
            top: 120px;
        }}

        .sidebar button {{
            width: 100%;
            background: transparent;
            color: var(--text-muted);
            border: 1px solid var(--border);
            padding: 1rem;
            margin-bottom: 1rem;
            border-radius: 12px;
            cursor: pointer;
            text-align: right;
            font-weight: 600;
            transition: 0.3s;
            font-size: 1rem;
        }}

        .sidebar button:hover {{
            background: rgba(255,255,255,0.05);
            transform: translateX(-5px);
        }}

        .sidebar button.active {{
            background: rgba(0, 255, 204, 0.1);
            color: var(--primary);
            border-color: var(--primary);
            box-shadow: 0 0 15px var(--primary-glow);
        }}

        /* Main Content */
        .main-dash {{
            flex: 1;
            padding-bottom: 4rem;
        }}

        .dash-header {{
            text-align: center;
            margin-bottom: 2rem;
        }}

        .dash-header h2 {{
            font-size: 2rem;
            color: var(--primary);
        }}

        .gif-container {{
            display: flex;
            justify-content: center;
            flex-wrap: wrap;
            gap: 1.5rem;
            margin-top: 1.5rem;
            margin-bottom: 2rem;
        }}

        .gif-container img {{
            border-radius: 15px;
            box-shadow: 0 5px 20px rgba(0, 255, 204, 0.1);
            height: 100px;
            object-fit: cover;
        }}

        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 1.5rem;
            margin-bottom: 2rem;
        }}

        .stat-card {{
            background: var(--bg-surface);
            padding: 2rem;
            border-radius: 16px;
            border: 1px solid var(--border);
            text-align: center;
            transition: 0.3s;
        }}

        .stat-card:hover {{
            transform: translateY(-5px);
            border-color: var(--primary);
        }}

        .stat-value {{
            font-size: 2.2rem;
            font-weight: 800;
            color: var(--text-main);
            margin: 0.5rem 0;
        }}

        .stat-value.green {{ color: var(--primary); text-shadow: 0 0 10px var(--primary-glow); }}
        .stat-value.red {{ color: var(--danger); }}

        .charts {{
            display: grid;
            grid-template-columns: 2fr 1fr;
            gap: 1.5rem;
            margin-bottom: 3rem;
        }}

        .chart-box {{
            background: var(--bg-surface);
            padding: 1.5rem;
            border-radius: 16px;
            border: 1px solid var(--border);
        }}

        .logs-section {{
            background: var(--bg-surface);
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
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
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

        .coin-row {{
            display: flex;
            justify-content: space-between;
            background: rgba(255,255,255,0.02);
            padding: 0.3rem 0.5rem;
            border-radius: 5px;
        }}

        .coin-row span.win {{ color: var(--primary); font-weight: bold; }}
        .coin-row span.loss {{ color: var(--danger); font-weight: bold; }}

        /* Memes Section */
        .memes-section {{
            text-align: center;
            margin-top: 4rem;
            padding-top: 2rem;
            border-top: 1px solid var(--border);
        }}
        
        .memes-section h2 {{
            margin-bottom: 2rem;
            color: var(--text-muted);
        }}

        .memes-grid {{
            display: flex;
            justify-content: center;
            gap: 2rem;
            flex-wrap: wrap;
        }}

        .meme-card {{
            background: #111;
            padding: 1rem;
            border-radius: 15px;
            border: 1px solid var(--border);
        }}

        .meme-card img {{
            border-radius: 10px;
            width: 250px;
            height: 250px;
            object-fit: cover;
        }}
        
        .meme-card p {{
            margin-top: 1rem;
            font-weight: bold;
            color: var(--primary);
        }}
    </style>
</head>
<body>

    <div class="bg-animation" id="bg-anim"></div>

    <!-- Navigation -->
    <nav>
        <div class="logo">SMC Quant</div>
        <div class="nav-links">
            <button onclick="showLanding()">صفحه اصلی</button>
            <button onclick="openModal()">ورود اعضا</button>
            <button class="login-btn" onclick="openModal()">ثبت نام رایگان</button>
        </div>
    </nav>

    <!-- Landing Page -->
    <div class="landing" id="landing-page">
        <div class="bg-glow"></div>
        <h1 id="hero-title">پلتفرم مدیریت سرمایه و بک‌تست هوشمند</h1>
        <p>شبیه‌سازی مونت‌کارلو برای پیدا کردن امن‌ترین و پرسودترین سبد الگوریتمی شما در بازار کریپتو. ریسک را کاهش دهید، سود را تضمین کنید.</p>
        <button class="cta-btn" onclick="openModal()">ورود به داشبورد تخصصی</button>
    </div>

    <!-- Login Modal -->
    <div class="modal-overlay" id="auth-modal">
        <div class="auth-box">
            <h2 style="margin-bottom: 1.5rem;">ورود به حساب کاربری</h2>
            <input type="text" placeholder="نام کاربری (demo)" id="username">
            <input type="password" placeholder="رمز عبور (1234)" id="password">
            <button class="cta-btn" style="width: 100%; padding: 0.8rem; font-size: 1rem;" onclick="login()">ورود</button>
            <p style="margin-top: 1rem; font-size: 0.8rem; color: var(--text-muted); cursor: pointer;" onclick="closeModal()">انصراف</p>
        </div>
    </div>

    <!-- Dashboard Interface -->
    <div class="dashboard-container" id="dashboard-page">
        
        <div class="dash-layout">
            <div class="sidebar" id="sidebar-tabs">
                <h3 style="margin-bottom: 2rem; color: var(--text-muted); text-align: center;">پورتفولیوهای بهینه شده</h3>
                <!-- Generated via JS -->
            </div>
            
            <div class="main-dash">
                <div class="dash-header">
                    <h2 id="dash-title">اعتبارسنجی بک‌تست لایو ۳۶۵ روزه 💯</h2>
                    <p id="dash-subtitle" style="color: var(--text-muted); margin-top: 0.5rem; font-size: 1.2rem;">انتخاب پورتفولیو...</p>
                    
                    <div class="gif-container">
                        <img src="https://media.giphy.com/media/xTiTnqUxyWbsAXq7Ju/giphy.gif" alt="Money Raining">
                        <img src="https://media.giphy.com/media/trN9ht5RlE3Dcwavg2/giphy.gif" alt="Stonks">
                        <img src="https://media.giphy.com/media/Y2ZUWLrTy63j9T6qrK/giphy.gif" alt="Rocket">
                    </div>
                </div>

                <div class="stats-grid">
                    <div class="stat-card">
                        <div style="color: var(--text-muted);">سرمایه اولیه 💵</div>
                        <div class="stat-value">$10,000</div>
                    </div>
                    <div class="stat-card">
                        <div style="color: var(--text-muted);">سرمایه نهایی 💰</div>
                        <div class="stat-value green" id="stat-final">$--</div>
                    </div>
                    <div class="stat-card">
                        <div style="color: var(--text-muted);">رشد یک‌ساله 🚀</div>
                        <div class="stat-value green" id="stat-return">--%</div>
                    </div>
                    <div class="stat-card" style="grid-column: span 3; text-align: center; padding: 1rem;">
                        <span style="color: var(--text-muted);">حداکثر افت (MDD): <b id="stat-mdd" class="red">--%</b> 📉</span>
                    </div>
                </div>

                <div class="charts">
                    <div class="chart-box">
                        <h4 style="text-align: center; margin-bottom: 1rem;">شبیه‌سازی رشد سرمایه (فرضی)</h4>
                        <canvas id="lineChart" height="150"></canvas>
                    </div>
                    <div class="chart-box">
                        <h4 style="text-align: center; margin-bottom: 1rem;">تخصیص سرمایه (ریسک)</h4>
                        <div style="height: 250px; display:flex; justify-content:center;">
                            <canvas id="pieChart"></canvas>
                        </div>
                    </div>
                </div>

                <div class="logs-section">
                    <div class="logs-header">
                        <h3 style="margin:0;">گزارش ماه به ماه 📅</h3>
                        <span id="win-months" style="background: rgba(0,255,204,0.1); color: var(--primary); padding: 0.5rem 1rem; border-radius: 10px;">--</span>
                    </div>
                    
                    <div class="logs-grid" id="logsGrid">
                        <!-- Injected via JS -->
                    </div>
                </div>

                <div class="memes-section">
                    <h2>وقتی الگوریتم داره برات پول در میاره 😂👇</h2>
                    <div class="memes-grid">
                        <div class="meme-card">
                            <img src="https://media.giphy.com/media/VTxmwaCEwSlZm/giphy.gif" alt="Dump it">
                            <p>He bought? Dump it. 📉</p>
                        </div>
                        <div class="meme-card">
                            <img src="https://media.giphy.com/media/7FBY7h5Psqd20/giphy.gif" alt="Rollercoaster">
                            <p>Bitcoin Rollercoaster 🎢</p>
                        </div>
                        <div class="meme-card">
                            <img src="https://media.giphy.com/media/3o6gDWzmAzrpi5DQU8/giphy.gif" alt="HODL">
                            <p>Just HODL & Chill ☕</p>
                        </div>
                    </div>
                </div>

            </div>
        </div>
    </div>

    <script>
        // Data populated from validation
        const portfolios = {data};

        let pieChartInstance, lineChartInstance;

        // UI Flow
        function openModal() {{ document.getElementById('auth-modal').classList.add('active'); }}
        function closeModal() {{ document.getElementById('auth-modal').classList.remove('active'); }}
        
        function login() {{
            closeModal();
            document.getElementById('landing-page').style.display = 'none';
            document.getElementById('dashboard-page').style.display = 'block';
            document.getElementById('bg-anim').style.display = 'block';
            if(!pieChartInstance) {{
                initSidebar();
                initCharts();
                loadPortfolio(0);
            }}
        }}

        function showLanding() {{
            document.getElementById('dashboard-page').style.display = 'none';
            document.getElementById('bg-anim').style.display = 'none';
            document.getElementById('landing-page').style.display = 'flex';
        }}

        function getCoinEmoji(coin) {{
            if(coin.includes('BTC')) return '👑';
            if(coin.includes('DOGE')) return '🐶';
            if(coin.includes('TRX')) return '🔴';
            if(coin.includes('AVAX')) return '🔺';
            return '🪙';
        }}

        function initSidebar() {{
            const sidebarDiv = document.getElementById('sidebar-tabs');
            portfolios.forEach((p, idx) => {{
                const btn = document.createElement('button');
                btn.className = idx === 0 ? 'port-btn active' : 'port-btn';
                btn.innerText = p.name;
                btn.onclick = () => loadPortfolio(idx);
                sidebarDiv.appendChild(btn);
            }});
        }}

        function initCharts() {{
            Chart.defaults.color = '#888';
            Chart.defaults.font.family = "'Vazirmatn', sans-serif";

            const pieCtx = document.getElementById('pieChart').getContext('2d');
            pieChartInstance = new Chart(pieCtx, {{
                type: 'doughnut',
                data: {{
                    labels: [],
                    datasets: [{{
                        data: [],
                        backgroundColor: ['#00ffcc', '#7000ff', '#ff007f', '#f59e0b'],
                        borderWidth: 0,
                        hoverOffset: 10
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    cutout: '75%',
                    plugins: {{
                        legend: {{ position: 'bottom', labels: {{ color: '#fff', font: {{ size: 12 }} }} }}
                    }}
                }}
            }});

            const lineCtx = document.getElementById('lineChart').getContext('2d');
            let gradient = lineCtx.createLinearGradient(0, 0, 0, 400);
            gradient.addColorStop(0, 'rgba(0, 255, 204, 0.4)');
            gradient.addColorStop(1, 'rgba(0, 255, 204, 0.0)');

            lineChartInstance = new Chart(lineCtx, {{
                type: 'line',
                data: {{
                    labels: [],
                    datasets: [{{
                        label: 'موجودی (دلار)',
                        data: [],
                        borderColor: '#00ffcc',
                        backgroundColor: gradient,
                        borderWidth: 3,
                        pointBackgroundColor: '#050505',
                        pointBorderColor: '#00ffcc',
                        pointRadius: 0,
                        fill: true,
                        tension: 0.4
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {{
                        y: {{ grid: {{ color: 'rgba(255,255,255,0.05)' }} }},
                        x: {{ grid: {{ display: false }} }}
                    }},
                    plugins: {{
                        legend: {{ display: false }}
                    }}
                }}
            }});
        }}

        function loadPortfolio(idx) {{
            // Update tabs
            document.querySelectorAll('.port-btn').forEach((b, i) => b.className = i === idx ? 'port-btn active' : 'port-btn');

            const p = portfolios[idx];
            
            // Subtitle string
            const subtitleParts = Object.entries(p.weights).map(([k, v]) => `${{k}} (${{(v*100).toFixed(2)}}%) ${{getCoinEmoji(k)}}`);
            document.getElementById('dash-subtitle').innerText = `ترکیب: ${{subtitleParts.join(' + ')}}`;

            // Stats
            const finalCap = 10000 + (10000 * (p.return / 100));
            document.getElementById('stat-final').innerText = '$' + Math.round(finalCap).toLocaleString();
            document.getElementById('stat-return').innerText = '+' + p.return.toFixed(1) + '%';
            document.getElementById('stat-mdd').innerText = p.mdd.toFixed(1) + '%';

            // Update Charts
            const coinNames = Object.keys(p.weights).map(c => c.replace('USDT_', ' '));
            const coinWeights = Object.values(p.weights).map(v => (v*100).toFixed(2));
            pieChartInstance.data.labels = coinNames;
            pieChartInstance.data.datasets[0].data = coinWeights;
            pieChartInstance.update();

            lineChartInstance.data.labels = Array(p.eq_curve.length).fill('');
            lineChartInstance.data.datasets[0].data = p.eq_curve;
            lineChartInstance.update();

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
                for(const [coin, pnl] of Object.entries(log.coins)) {{
                    const coinClass = pnl >= 0 ? 'win' : 'loss';
                    const coinSign = pnl >= 0 ? '+' : '';
                    coinsHtml += `
                        <div class="coin-row">
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

    </script>
</body>
</html>"""

with open('index.html', 'w') as f:
    f.write(html_content)
    
print("Updated index.html by merging dashboard.html features into it.")
