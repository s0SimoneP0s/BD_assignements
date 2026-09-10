from pyspark.sql import SparkSession
from pyspark.storagelevel import StorageLevel
import os


spark = (
    SparkSession.builder
    .appName("SparkMemBenchmark")
    .remote("sc://10.0.0.79:6066")
    .config("spark.sql.shuffle.partitions", "4")
    .config("spark.default.parallelism", "4")
    .getOrCreate()
)

rows = 500000
partitions = 4

# Small in-memory workload: keep a DataFrame cached and force repeated reads.
df = spark.range(0, rows, numPartitions=partitions).selectExpr(
    "id",
    "CAST(id % 100 AS INT) AS group_id",
    "LPAD(CAST(id AS STRING), 12, '0') AS payload"
)

cached = df.persist(StorageLevel.MEMORY_ONLY)
count1 = cached.count()
count2 = cached.filter("group_id >= 0").count()

total_payload = cached.selectExpr("SUM(LENGTH(payload)) AS bytes").collect()[0][0]

print(f"rows={count1}")
print(f"rows_recheck={count2}")
print(f"payload_bytes={total_payload}")

cached.unpersist()
spark.stop()