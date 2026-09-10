from pyspark.sql import SparkSession
from pyspark.sql.functions import col, concat, length, lpad, sum as spark_sum, lit
spark = (
    SparkSession.builder
    .appName("SparkDiskBenchmark")
    .remote("sc://10.0.0.79:6066")
    .config("spark.sql.shuffle.partitions", "4")
    .config("spark.default.parallelism", "4")
    .config("spark.sql.execution.arrow.pyspark.enabled", "false")
    .getOrCreate()
)

rows = 250000
partitions = 4

# Small disk-oriented workload: force spill/shuffle-heavy execution without relying on a mounted filesystem.
df = spark.range(0, rows, numPartitions=partitions).select(
    col("id"),
    (col("id") % 100).alias("bucket"),
    concat(
        lpad(col("id").cast("string"), 8, "0"),
        lit("-"),
        lpad(col("id").cast("string"), 8, "0")
    ).alias("line")
)

result = (
    df
    .select(
        col("bucket").cast("int").alias("bucket"),
        col("line").alias("line")
    )
    .repartition(4, "bucket")
    .agg(
        spark_sum(length("line")).alias("total_line_length"),
    )
    .collect()[0][0]
)

print(f"rows={rows}")
print(f"total_line_length={result}")

spark.stop()