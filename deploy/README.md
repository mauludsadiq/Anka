# ANKA Node — Production Deployment

## TLS Setup

ANKA nodes communicate over HTTP internally. TLS is terminated at the
reverse proxy layer. Two options:

### Option A: Caddy (recommended — auto-provisions certificates)

    # Install Caddy
    curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
    sudo apt install caddy

    # Configure
    cp caddy.conf /etc/caddy/Caddyfile
    # Edit: replace YOUR_DOMAIN and YOUR_PORT
    sudo systemctl reload caddy

### Option B: nginx + Let's Encrypt

    sudo apt install nginx certbot python3-certbot-nginx
    sudo certbot --nginx -d YOUR_DOMAIN
    cp nginx.conf /etc/nginx/sites-available/anka-node
    # Edit: replace YOUR_DOMAIN and YOUR_PORT
    sudo ln -s /etc/nginx/sites-available/anka-node /etc/nginx/sites-enabled/
    sudo nginx -t && sudo systemctl reload nginx

## Node Setup

    # Configure node with your public HTTPS address
    python3 anka/setup.py \
      --name "Your-Institution-Node" \
      --institution "Your Institution" \
      --address "https://YOUR_DOMAIN" \
      --origin "https://origin.anka.network" \
      --db out/node/anka_node.db

    # Start node
    fardrun run --program anka/src/node_process.fard --out out/node

## Joining an Existing Mesh

    bash anka/join.sh \
      --name "Your-Institution-Node" \
      --institution "Your Institution" \
      --address "https://YOUR_DOMAIN" \
      --mesh "https://EXISTING_NODE_DOMAIN" \
      --program anka/src/node_process.fard \
      --db out/node/anka_node.db

## Systemd Service

    cp deploy/anka-node.service /etc/systemd/system/
    sudo systemctl enable anka-node
    sudo systemctl start anka-node

