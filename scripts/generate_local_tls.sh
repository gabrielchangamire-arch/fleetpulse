#!/bin/sh
set -eu
tls_dir="${1:-certs/generated}"
mkdir -p "$tls_dir"
openssl req -x509 -newkey rsa:2048 -nodes -days 30 -subj "/CN=FleetPulse Local CA" -addext "basicConstraints=critical,CA:TRUE" -addext "keyUsage=critical,keyCertSign,cRLSign" -addext "subjectKeyIdentifier=hash" -keyout "$tls_dir/ca.key" -out "$tls_dir/ca.crt"
openssl req -newkey rsa:2048 -nodes -subj "/CN=localhost" -keyout "$tls_dir/server.key" -out "$tls_dir/server.csr"
printf 'subjectAltName=DNS:localhost,DNS:nginx,IP:127.0.0.1\nextendedKeyUsage=serverAuth\n' > "$tls_dir/server.ext"
openssl x509 -req -days 30 -in "$tls_dir/server.csr" -CA "$tls_dir/ca.crt" -CAkey "$tls_dir/ca.key" -CAcreateserial -extfile "$tls_dir/server.ext" -out "$tls_dir/server.crt"
chmod 600 "$tls_dir"/*.key
