#!/usr/bin/env python3
"""Partitioning test in the same style as `test_consistency.py` and `test_availability.py`.

Simulate network partitions by disconnecting a random node from the Docker
network, perform read/write operations during the partition, then heal and
record the results in a shared history list for later analysis.
"""

import time
import logging
import threading
from pprint import pp
import sys
import argparse

from _suite import (
    RedisConnector,
    RedisClusterTestSuite,
)


safe_list = []
safe_list_lock = threading.Lock()

logger = logging.getLogger("partitioning")

arg_parser = argparse.ArgumentParser(description="Run availability tests on Redis cluster")
arg_parser.add_argument("--local-test-count", type=int, default=10, help="Number of random events per thread")
arg_parser.add_argument("--thread-count", type=int, default=200, help="Number of concurrent threads to run")
args = arg_parser.parse_args()
LOCAL_TEST_COUNT:int=args.local_test_count
MT_COUNT:int=args.thread_count

def random_test(conn, test) -> list:
    """Perform a random partitioning test by disconnecting a node, performing read/write operations,
    and then reconnecting the node. Every operation is logged in the history.
    """
    history = []
    for _ in range(LOCAL_TEST_COUNT):
        local_conn = RedisConnector() if conn is None else conn
        local_test = RedisClusterTestSuite(connector=local_conn) if test is None else test
        local_test.random_partition_event()
        history.extend(local_test.history)
    return history


print("=" * 50)
print("Initial cluster state:")
conn = RedisConnector()  # base connection to the cluster
print(conn.scan_all())
print("*" * 50)

threads = []
master_test = RedisClusterTestSuite(connector=conn)
for i in range(MT_COUNT):
    int_conn = RedisConnector()
    worker_test = RedisClusterTestSuite(connector=int_conn)
    thread = threading.Thread(target=random_test, args=(int_conn, worker_test))
    thread.start()
    threads.append(thread)

for thread in threads:
    thread.join()

# Merge collected worker histories into the master test history
with master_test.history_lock:
    master_test.history.extend(safe_list)

pp(master_test.history)
print("Final cluster state:")
conn1 = RedisConnector(port=6379)
stat1 = conn1.scan_all()
print(stat1)
print("*" * 50)
conn2 = RedisConnector(port=6380)
stat2 = conn2.scan_all()
print(stat2)
print("*" * 50)
conn3 = RedisConnector(port=6381)
stat3 = conn3.scan_all()
print(stat3)
print("*" * 50)

partitioning_ok = True
for entry in master_test.history:
    if entry.get("operation") == "partition":
        if not (entry.get("disconnected") and entry.get("reconnected") and entry.get("success_during")):
            partitioning_ok = False
            break

print("Is Redis Partitioning-tolerant in this test scenario? ")
print({
    "partitioning_ok": partitioning_ok,
    "nodes_state_equal": stat1 == stat2 == stat3,
})
if not partitioning_ok:
    print("No, the cluster did not tolerate partitions cleanly in this scenario.")
    sys.exit(1)
else:
    print("Yes, the cluster tolerated partitions in this scenario.")

print("@" * 50)