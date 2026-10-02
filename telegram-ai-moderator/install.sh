#!/usr/bin/env bash
set -Eeuo pipefail

REPO_URL="https://github.com/Joker5000/Joker5000.github.io.git"
BRANCH="telegram-ai-moderator"
APP_DIR="/opt/tg-ai-moderator"
SRC_SUBDIR="telegram-ai-moderator"

if [[ ${EUID} -ne 0 ]]; then
  echo "Запустите: curl -fsSL .../install.sh | sudo bash"
  exit 1
fi

if ! grep -qiE 'ubuntu|debian' /etc/os-release; then
  echo "Поддерживаются Ubuntu/Debian."
  exit 1
fi

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y ca-certificates curl git openssl ufw

if ! command -v docker >/dev/null 2>&1; then
  curl -fsSL https://get.docker.com | sh
fi
systemctl enable --now docker

tmpdir="$(mktemp -d)"
trap 'rm -rf "$tmpdir"' EXIT
git clone --depth 1 --branch "$BRANCH" "$REPO_URL" "$tmpdir/repo"
mkdir -p "$APP_DIR"
cp -a "$tmpdir/repo/$SRC_SUBDIR/." "$APP_DIR/"
cd "$APP_DIR"

POSTGRES_PASSWORD="$(openssl rand -hex 24)"
WEB_SESSION_SECRET="$(openssl rand -hex 48)"

echo
echo "╔════════════════════════════════════════════╗"
echo "║       Telegram AI Moderator Setup         ║"
echo "╚════════════════════════════════════════════╝"
echo
echo "Создайте Telegram-бота через @BotFather и вставьте токен."
read -r -s -p "BOT TOKEN: " BOT_TOKEN
echo
read -r -p "Ваш Telegram ID (владелец): " OWNER_ID

while [[ ! "$OWNER_ID" =~ ^[0-9]+$ ]]; do
  echo "Telegram ID должен состоять из цифр."
  read -r -p "Ваш Telegram ID: " OWNER_ID
done

echo
echo "ИИ можно подключить позже из конфигурации."
read -r -p "Включить OpenAI-compatible AI сейчас? [y/N]: " ENABLE_AI
AI_ENABLED=false
AI_KEY=""
AI_BASE="https://api.openai.com/v1"
AI_MODEL="gpt-5-mini"
if [[ "$ENABLE_AI" =~ ^[YyДд]$ ]]; then
  AI_ENABLED=true
  read -r -s -p "AI API KEY: " AI_KEY
  echo
  read -r -p "API URL [$AI_BASE]: " input; AI_BASE="${input:-$AI_BASE}"
  read -r -p "Модель [$AI_MODEL]: " input; AI_MODEL="${input:-$AI_MODEL}"
fi

cat > .env <<EOF
BOT_TOKEN=$BOT_TOKEN
OWNER_TELEGRAM_ID=$OWNER_ID
EXTRA_ADMIN_IDS=
MODERATION_MODE=assist
POSTGRES_PASSWORD=$POSTGRES_PASSWORD
DATABASE_URL=postgresql://moderator:$POSTGRES_PASSWORD@postgres:5432/moderator
REDIS_URL=redis://redis:6379/0
OPENAI_API_KEY=$AI_KEY
OPENAI_BASE_URL=$AI_BASE
OPENAI_MODEL=$AI_MODEL
AI_ENABLED=$AI_ENABLED
WEB_SESSION_SECRET=$WEB_SESSION_SECRET
WEB_PORT=8080
WEB_PUBLIC_URL=
EOF
chmod 600 .env

cat > /usr/local/bin/moderator <<'CLI'
#!/usr/bin/env bash
set -e
cd /opt/tg-ai-moderator
case "${1:-menu}" in
  status) docker compose ps ;;
  logs) docker compose logs -f --tail=200 bot ;;
  restart) docker compose restart ;;
  stop) docker compose stop ;;
  start) docker compose up -d ;;
  update)
    tmp="$(mktemp -d)"
    git clone --depth 1 --branch telegram-ai-moderator https://github.com/Joker5000/Joker5000.github.io.git "$tmp/repo"
    cp -a "$tmp/repo/telegram-ai-moderator/." /opt/tg-ai-moderator/
    rm -rf "$tmp"
    docker compose up -d --build
    ;;
  config) ${EDITOR:-nano} .env ;;
  *)
    echo "Telegram AI Moderator"
    echo "  moderator status   - состояние"
    echo "  moderator logs     - логи"
    echo "  moderator restart  - перезапуск"
    echo "  moderator stop     - остановить"
    echo "  moderator start    - запустить"
    echo "  moderator update   - обновить из GitHub"
    echo "  moderator config   - открыть .env"
    ;;
esac
CLI
chmod +x /usr/local/bin/moderator

ufw allow OpenSSH >/dev/null 2>&1 || true
# Веб-панель по умолчанию слушает только localhost. Используйте SSH tunnel или reverse proxy с HTTPS.
ufw --force enable >/dev/null 2>&1 || true

docker compose up -d --build

echo
echo "=============================================="
echo " Telegram AI Moderator установлен"
echo "=============================================="
echo
echo "Каталог: $APP_DIR"
echo "Режим: ASSIST"
echo
echo "Теперь:"
echo "  1) Добавьте бота в Telegram-группу."
echo "  2) Выдайте ему права удаления сообщений, мута и бана."
echo "  3) Напишите боту в ЛС /start."
echo "  4) Второго администратора добавьте: /addadmin TELEGRAM_ID"
echo "  5) В личке задайте пароль панели: /webpass ВАШ_НАДЁЖНЫЙ_ПАРОЛЬ"
echo
echo "Веб-панель безопасно слушает только 127.0.0.1:8080."
echo "С компьютера откройте SSH-туннель:"
echo "  ssh -L 8080:127.0.0.1:8080 root@IP_ВАШЕЙ_VM"
echo "Затем откройте: http://127.0.0.1:8080"
echo
echo "Команды VM:"
echo "  moderator status"
echo "  moderator logs"
echo "  moderator restart"
echo "  moderator update"
echo
