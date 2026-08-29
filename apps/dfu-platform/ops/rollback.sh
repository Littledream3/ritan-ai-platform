#!/usr/bin/env bash
set -euo pipefail
sudo systemctl disable --now dfu-v2.service || true
if grep -Fq 'include /etc/nginx/snippets/dfu-v2-test.conf;' /etc/nginx/sites-enabled/default; then
    sudo sed -i '\|include /etc/nginx/snippets/dfu-v2-test.conf;|d' /etc/nginx/sites-enabled/default
fi
sudo rm -f /etc/nginx/snippets/dfu-v2-test.conf
sudo nginx -t
sudo systemctl reload nginx
docker stop dfu-v2-postgres || true
echo 'DFU v2 staging service stopped. Source and PostgreSQL volume were preserved.'
