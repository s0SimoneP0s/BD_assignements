#!/usr/bin/env python3
"""Test basic consistency behaviour across cluster nodes.

This script writes a key to one node and attempts to read it from other nodes.
It is a pragmatic test to observe eventual vs strong consistency characteristics.
"""

import logging
from _suite import RedisConnector, RedisClusterTestSuite
from pprint import pp
import threading
import sys
import argparse

safe_list = []
safe_list_lock = threading.Lock()

logger = logging.getLogger("consistency")



# Jepsen test: disable each node in turn and run a write/read test
# a Pivot node is used to simplify achitecture
logger.info("Starting consistency test across cluster nodes")
logger.info("The cluster is in a known state, with all nodes up and running.")

arg_parser = argparse.ArgumentParser(description="Run availability tests on Redis cluster")
arg_parser.add_argument("--local-test-count", type=int, default=10, help="Number of random events per thread")
arg_parser.add_argument("--thread-count", type=int, default=200, help="Number of concurrent threads to run")
args = arg_parser.parse_args()
LOCAL_TEST_COUNT:int=args.local_test_count
MT_COUNT:int=args.thread_count

def random_test(conn, test) -> dict:
    """Perform a random consistency test by stopping/starting a node and performing read/write operations.
    Every worker collects its own history and appends it to the shared `safe_list`.
    """
    local_conn = RedisConnector() if conn is None else conn
    local_test = RedisClusterTestSuite(connector=local_conn) if test is None else test
    for _ in range(LOCAL_TEST_COUNT):
        local_test.random_event()
    if local_test.history:
        global safe_list
        with safe_list_lock:
            safe_list.extend(local_test.history)
    return local_test.history if local_test.history else None



print("="*50)
print("Initial cluster state:")
conn = RedisConnector() # base connection to the cluster
print(conn.scan_all())
print("*"*50)

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
print("*"*50)
print("Node 2:")
conn2 = RedisConnector(port=6380)
stat2 = conn2.scan_all()
print(stat2)
print("*"*50)
print("Node 3:")
conn3 = RedisConnector(port=6381)
stat3 = conn3.scan_all()
print(stat3)
print("*"*50)
consistency_dag = {
        "stat1 == stat2": stat1 == stat2,
        "stat1 == stat3": stat1 == stat3,
        "stat2 == stat3": stat2 == stat3,
}


print("Is Redis Consistent in this test scenario? ")
pp(consistency_dag)
for check in consistency_dag.values():
    if not check:
        print("No, the cluster is not consistent in this scenario.")
        sys.exit(1)
        break
else:    print("Yes, the cluster is consistent in this scenario.")

print("@"*50)