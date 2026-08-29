#!/usr/bin/env bash
set -euo pipefail

sudo systemctl disable --now media-drop.service || true
if grep -Fq 'include /etc/nginx/snippets/media-drop.conf;' /etc/nginx/sites-enabled/default; then
    sudo sed -i '\|include /etc/nginx/snippets/media-drop.conf;|d' /etc/nginx/sites-enabled/default
fi
sudo rm -f /etc/nginx/snippets/media-drop.conf
sudo nginx -t
sudo systemctl reload nginx
docker stop media-drop-postgres || true
echo "Media drop service stopped. Database volume and uploaded files were preserved."

