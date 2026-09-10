from pyspark.sql import SparkSession
from pyspark.sql.functions import col, concat, length, lpad, sum as spark_sum, lit, sqrt, sin, cos
from pyspark.storagelevel import StorageLevel
from functools import wraps
from time import perf_counter


EXECUTION_SPEEDS = {}


def track_speed(unit_key):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = perf_counter()
            result = func(*args, **kwargs)
            elapsed = perf_counter() - start
            speed_gbps = result.get("processed_gb", 0.0) / max(elapsed, 1e-9)
            result["elapsed_s"] = elapsed
            result["speed_gbps"] = speed_gbps
            EXECUTION_SPEEDS[unit_key] = speed_gbps
            return result

        return wrapper

    return decorator


def build_spark_session():
    return (
        SparkSession.builder
        .appName("SparkClusterScore")
        .remote("sc://10.0.0.79:6066")
        .config("spark.sql.shuffle.partitions", "4")
        .config("spark.default.parallelism", "4")
        .config("spark.sql.execution.arrow.pyspark.enabled", "false")
        .getOrCreate()
    )


@track_speed("mem")
def test_mem(spark):
    rows = 500000
    df = spark.range(0, rows, numPartitions=4).selectExpr(
        "id",
        "CAST(id % 100 AS INT) AS group_id",
        "LPAD(CAST(id AS STRING), 12, '0') AS payload"
    )

    cached = df.persist(StorageLevel.MEMORY_ONLY)
    count1 = cached.count()
    count2 = cached.filter("group_id >= 0").count()
    total_payload = cached.selectExpr("SUM(LENGTH(payload)) AS bytes").collect()[0][0]
    cached.unpersist()

    processed_gb = total_payload / (1024 ** 3)

    return {
        "rows": count1,
        "rows_recheck": count2,
        "payload_bytes": total_payload,
        "processed_gb": processed_gb,
        "score": (count1 + count2) / max(total_payload, 1),
    }


@track_speed("cpu")
def test_cpu(spark):
    rows = 200000
    df = spark.range(0, rows, numPartitions=4).select(
        col("id").cast("double").alias("x")
    )

    computed = df.select(
        (
            sqrt(col("x") + 1.0)
            + sin(col("x") / 10.0)
            + cos(col("x") / 25.0)
        ).alias("score")
    )

    total_score = computed.agg(spark_sum("score").alias("total_score")).collect()[0][0]

    processed_gb = (rows * 8) / (1024 ** 3)

    return {
        "rows": rows,
        "total_score": total_score,
        "processed_gb": processed_gb,
        "score": abs(total_score) / max(rows, 1),
    }


@track_speed("hdd")
def test_hdd(spark):
    rows = 250000
    df = spark.range(0, rows, numPartitions=4).select(
        col("id"),
        (col("id") % 100).alias("bucket"),
        concat(
            lpad(col("id").cast("string"), 8, "0"),
            lit("-"),
            lpad(col("id").cast("string"), 8, "0")
        ).alias("line")
    )

    total_line_length = (
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

    processed_gb = total_line_length / (1024 ** 3)

    return {
        "rows": rows,
        "total_line_length": total_line_length,
        "processed_gb": processed_gb,
        "score": total_line_length / max(rows, 1),
    }


def orchestrate_cluster_score(cpu_result, mem_result, hdd_result):
    cpu_score = cpu_result["score"]
    mem_score = mem_result["score"]
    hdd_score = hdd_result["score"]
    cluster_score = (cpu_score + mem_score + hdd_score) / 3.0
    cluster_speed_gbps = (
        EXECUTION_SPEEDS.get("cpu", 0.0)
        + EXECUTION_SPEEDS.get("mem", 0.0)
        + EXECUTION_SPEEDS.get("hdd", 0.0)
    ) / 3.0

    return {
        "cpu": cpu_score,
        "mem": mem_score,
        "hdd": hdd_score,
        "cluster_score": cluster_score,
        "cluster_speed_gbps": cluster_speed_gbps,
    }


if __name__ == "__main__":
    spark = build_spark_session()

    TEST_N=10

    converge : list[dict]=[]
    for i in range(TEST_N):
        local = orchestrate_cluster_score(test_cpu(spark), test_mem(spark), test_hdd(spark))
        converge.append(local)



    avg={"count":len(converge),"cpu":0.0,"mem":0.0,"hdd":0.0,"cluster_score":0.0,"cluster_speed_gbps":0.0}
    for v in converge:
        avg["cpu"] += v["cpu"]
        avg["mem"] += v["mem"]
        avg["hdd"] += v["hdd"]
        avg["cluster_score"] += v["cluster_score"]
        avg["cluster_speed_gbps"] += v["cluster_speed_gbps"]

    avg["cpu"] /= avg["count"]
    avg["mem"] /= avg["count"]
    avg["hdd"] /= avg["count"]
    avg["cluster_score"] /= avg["count"]
    avg["cluster_speed_gbps"] /= avg["count"]

    print(f"Average results over {avg['count']} runs:")
    print(f"CPU score: {avg['cpu']:.6f}")
    print(f"Memory score: {avg['mem']:.6f}")
    print(f"HDD score: {avg['hdd']:.6f}")
    print(f"Cluster score: {avg['cluster_score']:.6f}")
    print(f"Cluster speed (GB/s): {avg['cluster_speed_gbps']:.6f}")


    spark.stop()