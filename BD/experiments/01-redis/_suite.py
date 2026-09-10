
#!/usr/bin/env python3
"""Common utilities shared by the redis cluster test scripts.

Place shared constants, client helpers, subprocess wrapper and metrics
recording here so individual tests can import them.
"""
import subprocess
import logging
from redis.cluster import RedisCluster, ClusterNode, logger
from redis.exceptions import ConnectionError as RedisConnectionError
import threading
import random
import time



HOST='127.0.0.1'
PRIMARY_PORT=6379

REVERSE_NODE_LIST = {
   6379: "redis-node-1",
   6380: "redis-node-2",
   6381: "redis-node-3"
}

random.seed(PRIMARY_PORT)  # Seed for reproducibility in random events


def run(cmd: str) -> subprocess.CompletedProcess | None:
    """Run a shell command and return subprocess.CompletedProcess (prints the command).

    This mirrors the helper used in the individual test scripts.
    """
    print(f"> {cmd}")
    try:
        return subprocess.run(cmd, shell=True, check=False, text=True, capture_output=True)
    except Exception as e:
        logging.exception("Failed to run command: %s", cmd , exc_info=e)
        return None


def client(host: str = HOST, port: int = PRIMARY_PORT) -> RedisCluster | None:
    """Create a RedisCluster client pointed at the given host/port.

    Use `client(host, port)` from tests to target a specific node.
    """
    try:
        node = ClusterNode(host=host, port=port)
        return RedisCluster(startup_nodes=[node], decode_responses=True)
    except Exception as e:
        logging.exception("Failed to create RedisCluster client for %s:%s", host, port, exc_info=e)
        return None 


def write(r: RedisCluster, key: str, value: str) -> bool:
    """Helper to write a key and log exceptions."""
    try:
        r.set(key, value)
        return True
    except RedisConnectionError as e:
        logger.exception("SET failed during disabled node scenario (connection)", exc_info=e)
    except Exception as e:
        logger.exception("SET failed during disabled node scenario", exc_info=e)
    return False



def read(r: RedisCluster, key: str) -> str | None:
    """Helper to read a key and log exceptions."""
    try:
        return r.get(key)
    except RedisConnectionError as e:
        logger.exception("GET failed during disabled node scenario (connection)", exc_info=e)
    except Exception as e:
        logger.exception("GET failed during disabled node scenario", exc_info=e)
    return None


def s_e_s(node_name , op_type=True) -> bool:
    if op_type:
        logger.info("Starting container %s", node_name)
        start = True
    else:
        logger.info("Stopping container %s", node_name)
        start = False

    command = "docker start" if start else "docker stop"
    try:
        run(f"{command} {node_name}")
        return True
    except Exception as e:
        logger.exception("Failed to %s container %s", command , node_name, exc_info=e)
        return False

# Configure logging for the suite
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("redis_tests")


class RedisConnector:
    """A simple wrapper to manage RedisCluster connections."""
    def __init__(self, host: str = HOST, port: int = PRIMARY_PORT):
        self.host = host
        self.port = port
        self.client = client(host, port)

    def write(self, key: str, value: str) -> bool:
        """Write a key-value pair to the Redis cluster."""
        if self.client:
            return write(self.client, key, value)
        logger.error("Client not initialized for writing.")
        return False

    def read(self, key: str) -> str | None:
        """Read a key-value pair from the Redis cluster."""
        if self.client:
            return read(self.client, key)
        logger.error("Client not initialized for reading.")
        return None

    def start_stop_container(self, node_name: str, op_type: bool = True) -> bool:
        """Start or stop a container by name."""
        return s_e_s(node_name, op_type=op_type)

    def scan_all(self) -> dict:

        result = {}

        for k in self.client.scan_iter(match='*', count=100):
            try:
                result[k] = self.client.get(k)
            except Exception:
                logger.exception("Failed to get value for key %s", k)
                result[k] = None
        return result





class RedisClusterTestSuite:
    """A test suite for Redis cluster operations."""
    NUM_KEYS = 10
    keys = [f"key_{i}" for i in range(NUM_KEYS)]
    history = [] 
    history_lock = threading.Lock()
    primary_port = PRIMARY_PORT
    op_counter = 0 


  

    def __init__(self, connector: RedisConnector):
        self.connector = connector

    def random_rw_event(self):
        op_type = random.choice(['read', 'write'])
        key = random.choice(self.keys)
        start_time = time.time()
        # Avoid blocking: increment the operation counter once instead
        with self.history_lock:
            self.op_counter += 1
        if op_type == 'write':
            write_value = f"value_{random.randint(1, 100)}"
            success = self.connector.write(key, write_value)
            end_time = time.time()
        else:
            write_value = None
            success = self.connector.read(key) is not None
            end_time = time.time()
        with self.history_lock:
            self.history.append({
                "operation": op_type,
                "value": {key:write_value},
                "success": success,
                "start_time": start_time,   
                "end_time": end_time
            })

    def random_partition_event(self, node_name: str = None):
        possible_nodes = {"redis-node-1", "redis-node-2", "redis-node-3"}
        if node_name is None:
            node_name = REVERSE_NODE_LIST[self.primary_port]
        op_type = "partition_event"
        start_time = time.time()
        with self.history_lock:
            self.op_counter += 1
        choices= possible_nodes - set([REVERSE_NODE_LIST[self.primary_port]])

        logger.info("Available nodes for partitioning: %s", choices)
        initial_state=self.connector.scan_all()
        for i in choices:
            stop_success = s_e_s(i, op_type="stop")
            rw_success = self.random_rw_event()
            rw_success = self.random_rw_event()
            self.primary_port = random.choice([6379, 6380, 6381])
            self.connector = RedisConnector(host=HOST, port=self.primary_port)
            rw_success = self.random_rw_event()
            rw_success = self.random_rw_event()
            time.sleep(0.1)  # Simulate partition duration
            start_success = s_e_s(i, op_type="start")
        final_state=self.connector.scan_all()

        end_time = time.time()
        with self.history_lock:
            self.history.append({
                "operation": op_type,
                "value": {node_name:initial_state != final_state},
                "success": any ( [stop_success, rw_success ,start_success] ),
                "start_time": start_time,
                "end_time": end_time
            })
        

    def random_ses_event(self, node_name: str = None):
        possible_nodes = {"redis-node-1", "redis-node-2", "redis-node-3"}
        start_time = time.time()
        with self.history_lock:
            self.op_counter += 1
        choices= possible_nodes - set([REVERSE_NODE_LIST[self.primary_port]])

        if not node_name:
            node_name = random.choice(list(choices))
        op_type = "ses_event"
        stop_success = s_e_s(node_name, op_type="stop")
        start_success = s_e_s(node_name, op_type="start")
        end_time = time.time()
        with self.history_lock:
            self.history.append({
                "operation": op_type,
                "value": {node_name:op_type},
                "success": stop_success and start_success,
                "start_time": start_time,
                "end_time": end_time
            })

    def random_primary_switch(self):
        op_type = "switch_primary"
        start_time = time.time()
        with self.history_lock:
            self.op_counter += 1
        self.primary_port = random.choice([6379, 6380, 6381])
        self.connector = RedisConnector(host=HOST, port=self.primary_port)
        success = True  if self.connector.client is not None else False
        end_time = time.time()
        with self.history_lock:
            self.history.append({
                "operation": op_type,
                "value": {HOST:self.primary_port},
                "success": success,
                "start_time": start_time,
                "end_time": end_time
            })

    def random_event(self):
        if random.random() < 0.8:  # 80% chance to do read/write
            self.random_rw_event()
        else:
          if random.random() < 0.8:  # 50% chance to do SES event
              self.random_ses_event()
          else:  # 50% chance to do primary switch event
              self.random_primary_switch()


# all exposed
__all__ = [
    "RedisConnector",
    "RedisClusterTestSuite",
]
