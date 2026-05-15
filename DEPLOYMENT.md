# ANKA Deployment Guide

## Transport Security (TLS)

ANKA node processes serve HTTP on localhost. For institutional deployment, TLS termination is handled by a reverse proxy. This is the correct architecture — TLS is a transport concern, not an application concern.

### Recommended: Caddy

Caddy automatically provisions and renews TLS certificates via Let's Encrypt.

    anka-node-a.institution.edu {
        reverse_proxy localhost:18080
    }

    anka-node-b.institution.edu {
        reverse_proxy localhost:18081
    }

    anka-origin.institution.edu {
        reverse_proxy localhost:18090
    }

    anka-policy.institution.edu {
        reverse_proxy localhost:18082
    }

Run with: caddy run --config Caddyfile

### Alternative: nginx

    server {
        listen 443 ssl;
        server_name anka-node-a.institution.edu;
        ssl_certificate     /etc/ssl/certs/anka.crt;
        ssl_certificate_key /etc/ssl/private/anka.key;
        ssl_protocols       TLSv1.2 TLSv1.3;
        location / {
            proxy_pass http://localhost:18080;
            proxy_set_header Host $host;
        }
    }

### Node Address Configuration

Update local_address in the node process to reflect the public HTTPS URL so gossip sender addresses are resolvable by peers:

    let local_address = "https://anka-node-a.institution.edu"

## Port Reference

| Node     | Default Port | Role                              |
|----------|-------------|-----------------------------------|
| Origin   | 18090       | Genesis registry, space registration |
| Node A   | 18080       | Agent/Validator                   |
| Node B   | 18081       | Agent/Validator                   |
| Policy   | 18082       | Policy collapse                   |
| Archive  | 18083       | Archive and reconstruction        |

## Key Management

Each node derives its Ed25519 keypair from a seed string. For institutional deployment:

- Use a cryptographically random seed stored in a secrets manager (HashiCorp Vault, AWS Secrets Manager)
- Never commit seeds to version control
- Rotate keys by generating a new keypair and re-registering the node identity with the origin

## Bootstrap Sequence

On first startup, fetch the genesis registry from the origin node:

    curl -X POST https://anka-node-a.institution.edu/registry/fetch \
      -H "Content-Type: application/json" \
      -d '{"sender_address": "https://anka-origin.institution.edu"}'

## Peer Registration

    curl -X POST https://anka-node-a.institution.edu/peer \
      -H "Content-Type: application/json" \
      -d '{"address": "https://anka-node-b.institution.edu"}'

## Subscription Configuration

Declare which claim spaces each node subscribes to:

    curl -X POST https://anka-node-a.institution.edu/subscribe \
      -H "Content-Type: application/json" \
      -d '{"spaces": ["anka.interpretive.econ", "anka.invariant.compute"]}'

Wildcard subscription (archive and policy nodes):

    curl -X POST https://anka-archive.institution.edu/subscribe \
      -H "Content-Type: application/json" \
      -d '{"spaces": ["*"]}'

## Audit Trail

Query the full epistemic trail of any claim by digest:

    curl https://anka-node-a.institution.edu/audit/trail/{digest_hex}

Returns: published, witnessed, and challenged events with timestamps and node identities.
