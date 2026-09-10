from pyspark.sql import SparkSession
from pyspark.sql.functions import col, sqrt, sin, cos, sum as spark_sum

spark = (
    SparkSession.builder
    .appName("SparkCpuBenchmark")
    .master("spark://10.0.0.79:7077")
    .config("spark.sql.shuffle.partitions", "4")
    .config("spark.default.parallelism", "4")
    .getOrCreate()
)

rows = 200000
partitions = 4

# Small CPU-heavy workload: compute a derived metric and aggregate it.
df = spark.range(0, rows, numPartitions=partitions).select(
    col("id").cast("double").alias("x")
)

computed = df.select(
    (
        sqrt(col("x") + 1.0)
        + sin(col("x") / 10.0)
        + cos(col("x") / 25.0)
    ).alias("score")
)

result = computed.agg(spark_sum("score").alias("total_score")).collect()[0][0]
print(f"rows={rows}")
print(f"total_score={result}")

spark.stop()