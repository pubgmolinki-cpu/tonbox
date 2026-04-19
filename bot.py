<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>TONBOX NEWS | Portal</title>
    <link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;700;900&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-dark: #0a0a0c;
            --accent-red: #ff004c;
            --accent-purple: #8a2be2;
            --grad: linear-gradient(135deg, #ff004c 0%, #8a2be2 100%);
            --glass: rgba(255, 255, 255, 0.05);
            --glass-border: rgba(255, 255, 255, 0.1);
        }

        * { box-sizing: border-box; -webkit-tap-highlight-color: transparent; }

        body, html {
            margin: 0; padding: 0;
            background-color: var(--bg-dark);
            color: #fff;
            font-family: 'Montserrat', sans-serif;
            overflow-x: hidden;
            height: 100%;
        }

        .glow-bg {
            position: fixed; top: 50%; left: 50%;
            width: 150vw; height: 150vh;
            background: radial-gradient(circle, rgba(255,0,76,0.15) 0%, rgba(138,43,226,0.08) 50%, transparent 100%);
            transform: translate(-50%, -50%);
            z-index: -1; filter: blur(60px);
            animation: pulse 10s infinite alternate;
        }

        @keyframes pulse {
            from { transform: translate(-50%, -50%) scale(1); opacity: 0.6; }
            to { transform: translate(-50%, -50%) scale(1.2); opacity: 1; }
        }

        #welcome {
            position: fixed; inset: 0;
            background: var(--bg-dark);
            display: flex; justify-content: center; align-items: center;
            z-index: 1000; text-align: center;
            transition: transform 0.7s cubic-bezier(0.86, 0, 0.07, 1);
        }

        .welcome-card {
            background: var(--glass);
            backdrop-filter: blur(20px);
            border: 1px solid var(--glass-border);
            padding: 40px 25px;
            border-radius: 35px;
            width: 90%; max-width: 400px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.6);
        }

        h1 { font-weight: 900; font-size: 28px; margin-bottom: 15px; letter-spacing: -1px; }
        h1 span { color: var(--accent-red); }

        .welcome-card p { font-size: 14px; line-height: 1.5; opacity: 0.8; margin-bottom: 30px; }

        .btn {
            display: flex; align-items: center; justify-content: center;
            padding: 16px; border-radius: 18px;
            text-decoration: none; font-weight: 700;
            text-transform: uppercase; font-size: 13px;
            transition: 0.3s; border: none; cursor: pointer;
            margin-bottom: 12px; color: #fff; width: 100%;
            gap: 10px;
        }

        .btn-red { background: var(--grad); box-shadow: 0 8px 15px rgba(255,0,76,0.2); }
        .btn-blue { background: #24A1DE; }
        .btn:active { transform: scale(0.96); }

        header {
            position: fixed; top: 0; width: 100%;
            padding: 15px 20px; display: none; align-items: center;
            background: rgba(10, 10, 12, 0.8);
            backdrop-filter: blur(15px); z-index: 900;
            border-bottom: 1px solid var(--glass-border);
        }

        .burger { font-size: 28px; cursor: pointer; }
        .header-title { flex-grow: 1; text-align: center; font-weight: 900; letter-spacing: 2px; font-size: 18px; }

        .news-section {
            display: none; padding: 90px 15px 30px;
            max-width: 800px; margin: 0 auto;
        }

        .news-card {
            display: flex; flex-direction: row;
            background: var(--glass); border-radius: 25px;
            margin-bottom: 20px; overflow: hidden;
            border: 1px solid var(--glass-border);
            animation: fadeIn 0.5s ease;
        }

        .news-img { width: 40%; min-width: 140px; height: auto; object-fit: cover; }
        .news-info { padding: 20px; flex-grow: 1; }
        .news-info h2 { margin: 0 0 10px 0; font-size: 18px; color: var(--accent-red); line-height: 1.3; }
        .news-info p { margin: 0; font-size: 14px; opacity: 0.8; line-height: 1.6; }

        .sidebar {
            position: fixed; left: -280px; top: 0;
            width: 260px; height: 100%;
            background: rgba(10,10,12,0.98);
            backdrop-filter: blur(25px); transition: 0.4s;
            z-index: 1100; padding: 50px 20px;
            border-right: 1px solid var(--accent-red);
        }
        .sidebar.active { left: 0; }
        .close-menu { position: absolute; right: 20px; top: 20px; font-size: 24px; }

        @media (max-width: 600px) {
            .news-card { flex-direction: column; }
            .news-img { width: 100%; height: 200px; }
            .news-info { padding: 15px; }
            .news-info h2 { font-size: 17px; }
        }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
    </style>
</head>
<body>

<div class="glow-bg"></div>

<div id="welcome">
    <div class="welcome-card">
        <h1>TONBOX <span>NEWS</span></h1>
        <p>Приветствуем тебя на портале TONBOX! Следи за самыми свежими новостями лиги вместе с нами.</p>
        <button onclick="enterSite()" class="btn btn-red">Смотреть Новости!</button>
    </div>
</div>

<header id="header">
    <div class="burger" onclick="toggleMenu()">☰</div>
    <div class="header-title">TONBOX NEWS</div>
    <div style="width: 28px;"></div>
</header>

<div class="sidebar" id="sidebar">
    <div class="close-menu" onclick="toggleMenu()">✕</div>
    <div style="margin-top: 30px;">
        <a href="https://t.me/TonBoxFTCL" class="btn btn-blue" style="font-size: 11px;">
            <img src="https://upload.wikimedia.org/wikipedia/commons/8/82/Telegram_logo.svg" width="16"> Наш Канал
        </a>
        <a href="https://t.me/fanziks" class="btn btn-red" style="font-size: 11px;">
             Создатель Бота
        </a>
    </div>
</div>

<div class="news-section" id="news-section">
    <div id="news-container">
        <div style="text-align: center; opacity: 0.5; margin-top: 50px;">Загрузка новостей...</div>
    </div>
</div>

<script>
    const tg = window.Telegram ? window.Telegram.WebApp : null;
    if (tg) tg.expand();

    function enterSite() {
        document.getElementById('welcome').style.transform = 'translateY(-100%)';
        setTimeout(() => {
            document.getElementById('header').style.display = 'flex';
            document.getElementById('news-section').style.display = 'block';
            loadNews();
        }, 400);
    }

    function toggleMenu() {
        document.getElementById('sidebar').classList.toggle('active');
    }

    async function loadNews() {
        try {
            const response = await fetch('/api/news');
            const news = await response.json();
            const container = document.getElementById('news-container');
            
            if (news.length === 0) {
                container.innerHTML = '<div style="text-align:center; padding:50px;">Новостей пока нет ⚽️</div>';
                return;
            }

            container.innerHTML = news.map(item => `
                <div class="news-card">
                    <img src="${item.image_url}" class="news-img" onerror="this.src='https://via.placeholder.com/400x300/1a1a1a/ffffff?text=TONBOX+NEWS'">
                    <div class="news-info">
                        <h2>${item.title}</h2>
                        <p>${item.content}</p>
                    </div>
                </div>
            `).join('');
        } catch (e) {
            console.error("Ошибка загрузки:", e);
            document.getElementById('news-container').innerHTML = '<div style="text-align:center; color:red;">Ошибка связи с сервером</div>';
        }
    }
</script>

</body>
</html>
