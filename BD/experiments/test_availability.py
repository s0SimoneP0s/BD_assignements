#!/usr/bin/env python3
"""Test availability by stopping a node and attempting reads/writes.

This script uses the docker CLI to stop/start containers and tests client operations
to observe how the cluster responds (availability under node failure).
"""
#!/usr/bin/env python3
"""Test availability by stopping a node and attempting reads/writes.

This script follows the style of `test_consistency.py` and uses the
helpers in `_suite.py` (`RedisConnector`, `RedisClusterTestSuite`).
"""
import sys
import logging
from pprint import pp
import threading
import argparse



from _suite import (
    RedisConnector,
    RedisClusterTestSuite
)

safe_list = []
safe_list_lock = threading.Lock()

logger = logging.getLogger("availability")

logger.info("Starting availability test across cluster nodes")
logger.info("The cluster is in a known state, with all nodes up and running.")

arg_parser = argparse.ArgumentParser(description="Run availability tests on Redis cluster")
arg_parser.add_argument("--local-test-count", type=int, default=10, help="Number of random events per thread")
arg_parser.add_argument("--thread-count", type=int, default=200, help="Number of concurrent threads to run")
args = arg_parser.parse_args()
LOCAL_TEST_COUNT:int=args.local_test_count
MT_COUNT:int=args.thread_count

def random_test(conn, test) -> list:
    """Perform a random availability test by stopping/starting a node and performing read/write operations.
    Every operation need to be logged in the history by design.
    """
    history = []
    local_history = {}
    for _ in range(LOCAL_TEST_COUNT):
        local_conn = RedisConnector() if conn is None else conn
        local_history[f"initial_connection_state"] = "success"  if local_conn.client is not None else None
        suite = RedisClusterTestSuite(connector=local_conn) if test is None else test
        local_history[f"loaded_suite"] = "success"  if suite.connector.client is not None else None
        suite.random_ses_event()
        local_history[f"ses_event"] = suite.history if suite.history else None
        suite.random_rw_event()
        local_history[f"rw_event"] = suite.history if suite.history else None
        suite.random_primary_switch()
        local_history[f"primary_switch_event"] = suite.history if suite.history else None
        history.append(local_history)
    return history

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


pp(master_test.history)
print("Is Redis Available in this test scenario? ")
for check in master_test.history:
    for key, value in check.items():
        if value is None:
            print(f"Key: {key} has value: {value}")
            print("No, the cluster is not available in this scenario.")
            sys.exit(1)
            break
else:    print("Yes, the cluster is available in this scenario.")

print("@" * 50)