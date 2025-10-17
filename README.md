# FOREXNEWSBOT
Руководство: установка всех зависимостей и развёртывание Forex News Discord-бота на Ubuntu

Описание
--------
Краткая инструкция по установке Python, необходимых системных библиотек, созданию виртуального окружения, установке зависимостей из `requirements.txt`, запуску бота и настройке автозапуска через systemd.

1) Обновление системы и установка необходимых пакетов
------------------------------------------------------
Откройте терминал и выполните:

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-venv python3-pip build-essential libssl-dev libffi-dev curl
```

Пояснение:
- `python3-venv` — для создания виртуальных окружений
- `build-essential`, `libssl-dev`, `libffi-dev` — нужны для сборки Python-зависимостей
- `curl` — удобная утилита для скачивания файлов

2) Копирование проекта на сервер
--------------------------------
перенесите файлы с арива просто в удобную вам папку

3) Создание и активация виртуального окружения
----------------------------------------------
Рекомендуется запускать бота в venv:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Обновите pip и установите зависимости:

```bash
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

4) (Опционально) Системные зависимости для браузерных парсеров
----------------------------------------------------------------
Если ваш бот будет использовать Selenium/Playwright или headless-браузеры, установите дополнительные пакеты (пример для Chromium):

```bash
sudo apt install -y chromium-browser chromium-chromedriver
```

5) Настройка токена и параметров
--------------------------------
настройте в forex_news такие переменные как: TOKEN(токен бота дискорда), CHANNEL_ID(куда бот будет писать что он активен и писать с утра отчет), GUILD_ID(id дискорд сервера)
6) Тестовый запуск
------------------
С активированным виртуальным окружением запустите бота вручную и проверьте логи:

```bash
source .venv/bin/activate
python forex_news.py
```

Если бот запускается успешно, вы увидите сообщение в консоли о готовности и синхронизации slash-команд.

7) Настройка автозапуска через systemd
-------------------------------------
Создайте unit-файл `/etc/systemd/system/forex_bot.service` со следующим содержимым (замените YOUR_USER и пути при необходимости):

```ini
[Unit]
Description=Forex News Discord Bot
After=network.target

[Service]
User=YOUR_USER
Group=YOUR_USER
WorkingDirectory=/opt/forex_bot
Environment=PYTHONUNBUFFERED=1
Environment=DISCORD_TOKEN=ваш_токен_здесь
ExecStart=/opt/forex_bot/.venv/bin/python /opt/forex_bot/forex_news.py
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
```

Примените и запустите сервис:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now forex_bot.service
sudo journalctl -u forex_bot -f
```
