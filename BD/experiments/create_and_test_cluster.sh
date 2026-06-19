#!/usr/bin/env sh

set -eu

echo "attesa avvio nodi redis..."

# Use the container names on the redis-cluster bridge network (space-separated)
NODES="redis-node-1:6379 redis-node-2:6379 redis-node-3:6379"

command -v redis-cli >/dev/null 2>&1 || {
  echo "redis-cli non trovato. Esegui lo script in un container che ha redis-cli (es. redis:7.2-alpine) o installalo." >&2
  exit 1
}

for node in $NODES; do
  host=${node%%:*}
  port=${node##*:}
  until redis-cli -h "$host" -p "$port" ping >/dev/null 2>&1; do
    echo "host $host:$port non pronta"
    sleep 1
  done
  echo "host $host:$port pronta"
done

echo "creazione cluster..."
redis-cli --cluster create $NODES --cluster-replicas 0 --cluster-yes

echo
echo "stato cluster"
redis-cli -h redis-node-1 -p 6379 cluster info

echo "stato cluster"
redis-cli -h redis-node-2 -p 6379 cluster info

echo "stato cluster"
redis-cli -h redis-node-3 -p 6379 cluster info


echo "Syncronization waiting..."
sleep 10


echo "scrittura chiavi..."
redis-cli -c -h redis-node-1 -p 6379 set user:1 mario
redis-cli -c -h redis-node-2 -p 6379 set user:2 luca
redis-cli -c -h redis-node-3 -p 6379 set user:3 anna

echo
echo "slot assegnati"
redis-cli -h redis-node-1 -p 6379 cluster keyslot user:1
redis-cli -h redis-node-2 -p 6379 cluster keyslot user:2
redis-cli -h redis-node-3 -p 6379 cluster keyslot user:3

echo "lettura chiavi..."
echo "user:1 => $(redis-cli -c -h redis-node-1 -p 6379 get user:1)"
echo "user:2 => $(redis-cli -c -h redis-node-2 -p 6379 get user:2)"
echo "user:3 => $(redis-cli -c -h redis-node-3 -p 6379 get user:3)"

echo
echo "informazioni cluster"
redis-cli -h redis-node-1 -p 6379 cluster nodes