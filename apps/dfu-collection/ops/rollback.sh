#!/usr/bin/env bash
set -euo pipefail

ROOT=/home/ubuntu/dfu-collection
sudo systemctl disable --now dfu-collection.service || true
if grep -Fq 'include /etc/nginx/snippets/dfu-collection.conf;' /etc/nginx/sites-enabled/default; then
    sudo sed -i '\|include /etc/nginx/snippets/dfu-collection.conf;|d' /etc/nginx/sites-enabled/default
fi
sudo rm -f /etc/nginx/snippets/dfu-collection.conf
if [ -f "$ROOT/ops/ritan-index.before-dfu-collection.html" ]; then
    cp "$ROOT/ops/ritan-index.before-dfu-collection.html" /home/ubuntu/ritan/Ritan/index.html
fi
sudo nginx -t
sudo systemctl reload nginx
docker stop dfu-collection-postgres || true
echo "Collection service stopped. PostgreSQL volume and media files were preserved."
