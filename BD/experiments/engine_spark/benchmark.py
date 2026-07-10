from pyspark.sql import SparkSession
from pyspark.sql.functions import col, concat, length, lpad, sum as spark_sum, lit, sqrt, sin, cos, rand, when, count, expr
from pyspark.storagelevel import StorageLevel
from functools import wraps
from time import perf_counter
import os
import tempfile
import shutil
import glob

EXECUTION_SPEEDS = {}

def track_speed(unit_key):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = perf_counter()
            result = func(*args, **kwargs)
            elapsed = perf_counter() - start
            processed_gb = result.get("processed_gb", 0.0)
            speed_gbps = processed_gb / max(elapsed, 1e-9)
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
        .master("spark://10.0.0.79:7077")
        .config("spark.sql.shuffle.partitions", "8")
        .config("spark.default.parallelism", "8")
        .config("spark.sql.execution.arrow.pyspark.enabled", "false")
        .config("spark.sql.adaptive.enabled", "true")
        .config("spark.sql.adaptive.coalescePartitions.enabled", "true")
        .config("spark.serializer", "org.apache.spark.serializer.KryoSerializer")
        .getOrCreate()
    )

def build_spark_session_hdd():
    return (
        SparkSession.builder
        .appName("SparkClusterScore")
        .master("spark://10.0.0.79:7077")
        .config("spark.sql.shuffle.partitions", "8")
        .config("spark.default.parallelism", "8")
        .config("spark.sql.execution.arrow.pyspark.enabled", "false")
        .config("spark.serializer", "org.apache.spark.serializer.KryoSerializer")
        .config("spark.sql.adaptive.enabled", "false")
        .config("spark.sql.autoBroadcastJoinThreshold", "1")
        .config("spark.sql.shuffle.partitions", "50")
        .config("spark.shuffle.spill.compress", "true")
        .config("spark.shuffle.memoryFraction", "0.1")
        .config("spark.storage.memoryFraction", "0.1")
        .config("spark.memory.fraction", "0.2")
        .config("spark.local.dir", "/tmp/spark-test")
        .getOrCreate()
    )

def measure_data_size(df, sample_fraction=0.01):
    sampled_df = df.sample(withReplacement=False, fraction=sample_fraction, seed=42)
    row_count = sampled_df.count()
    if row_count == 0:
        return 0
    size_per_row = 0
    for field in sampled_df.schema.fields:
        if field.dataType.typeName() in ['string', 'binary']:
            avg_len = sampled_df.selectExpr(f"AVG(LENGTH(CAST({field.name} AS STRING)))").collect()[0][0] or 0
            size_per_row += avg_len
        else:
            size_per_row += 8
    total_rows = df.count()
    estimated_size = (size_per_row * total_rows) / sample_fraction
    return int(estimated_size)

@track_speed("mem")
def test_mem(spark):
    rows = 1000000
    partitions = 8
    
    df = spark.range(0, rows, numPartitions=partitions).selectExpr(
        "id",
        "CAST(id % 100 AS INT) AS group_id",
        "LPAD(CAST(id AS STRING), 20, '0') AS payload",
        "LPAD(CAST(id AS STRING), 15, '0') AS payload2"
    )
    
    actual_size_bytes = measure_data_size(df)
    cached = df.persist(StorageLevel.MEMORY_ONLY)
    count1 = cached.count()
    count2 = cached.filter("group_id >= 50").count()
    count3 = cached.groupBy("group_id").agg(count("*").alias("cnt")).count()
    shuffled = cached.repartition(partitions * 2, "group_id")
    count4 = shuffled.count()
    cached.unpersist()
    
    processed_gb = actual_size_bytes / (1024 ** 3)
    
    return {
        "rows": count1,
        "processed_gb": processed_gb,
        "score": processed_gb,
        "shuffle_ops": count4,
    }

@track_speed("cpu")
def test_cpu(spark):
    rows = 500000
    partitions = 8
    
    df = spark.range(0, rows, numPartitions=partitions).select(
        col("id").cast("double").alias("x"),
        rand(42).alias("y"),
        (col("id") % 1000).cast("double").alias("z")
    )
    
    computed = df.select(
        (
            sqrt(col("x") + 1.0) * sin(col("y") * 100) * cos(col("z") / 50.0) +
            sin(col("x") / 10.0) * cos(col("y") * 5) +
            sqrt(col("y") + 2.0) * sin(col("z") / 20.0)
        ).alias("score1"),
        (
            cos(col("x") / 25.0) * sqrt(col("y") + 1.0) +
            sin(col("z") * 3.0) * cos(col("x") * 0.1)
        ).alias("score2")
    )
    
    result = computed.agg(
        spark_sum("score1").alias("total_score1"),
        spark_sum("score2").alias("total_score2"),
        expr("AVG(score1)").alias("avg_score1"),
        expr("AVG(score2)").alias("avg_score2"),
    ).collect()[0]
    
    processed_gb = (rows * 3 * 8) / (1024 ** 3)
    
    return {
        "rows": rows,
        "total_score": result[0] + result[1],
        "processed_gb": processed_gb,
        "score": abs(result[0] + result[1]) / (rows * 2),
        "avg_scores": (abs(result[2]) + abs(result[3])) / 2,
    }

@track_speed("hdd")
def test_hdd(spark):
    os.makedirs("/tmp/spark-test", exist_ok=True)
    rows = 500000
    
    df = spark.range(0, rows, numPartitions=8).select(
        col("id"),
        (col("id") % 100).alias("group_key"),
        concat(
            lpad(col("id").cast("string"), 30, "0"),
            lit("-"),
            lpad((col("id") * 2).cast("string"), 30, "0"),
            lit("-"),
            lpad((col("id") * 3).cast("string"), 30, "0"),
            lit("-"),
            lpad((col("id") * 4).cast("string"), 30, "0"),
            lit("-"),
            lpad((col("id") * 5).cast("string"), 30, "0")
        ).alias("large_payload"),
        rand(42).alias("value")
    )
    
    df1 = df.repartition(50, "group_key")
    aggregated = df1.groupBy("group_key").agg(
        spark_sum(length("large_payload")).alias("total_len"),
        spark_sum("value").alias("total_value"),
        count("*").alias("row_count")
    )
    sorted_df = aggregated.orderBy("total_len", ascending=False)
    result = sorted_df.collect()
    
    total_payload_size = sum(row[1] for row in result)
    total_payload_size += rows * 100
    processed_gb = total_payload_size / (1024 ** 3)
    
    has_spill = False
    spill_size = 0
    try:
        spill_files = glob.glob("/tmp/spark-test/*/spill*")
        has_spill = len(spill_files) > 0
        spill_size = sum(os.path.getsize(f) for f in spill_files) if spill_files else 0
    except:
        pass
    
    spill_bonus = 1.5 if has_spill else 0.5
    score = processed_gb * spill_bonus
    
    return {
        "rows": rows,
        "processed_gb": processed_gb,
        "score": score,
        "has_spill": has_spill,
        "spill_size_gb": spill_size / (1024 ** 3),
        "result_count": len(result)
    }

@track_speed("network")
def test_network(spark):
    rows = 500000
    partitions = 8
    
    df = spark.range(0, rows, numPartitions=partitions).select(
        col("id"),
        (col("id") % 10).alias("key1"),
        (col("id") % 50).alias("key2"),
        lpad(col("id").cast("string"), 12, "0").alias("large_field")
    )
    
    df1 = df.select(col("id"), col("key1"), col("large_field").alias("field1"))
    df2 = df.select(
        (col("id") + 100).alias("id2"),
        col("key2"),
        col("large_field").alias("field2")
    )
    
    joined = df1.join(df2, col("id") == col("id2"), "inner")
    
    aggregated = joined.groupBy("key1", "key2").agg(
        spark_sum(length("field1")).alias("sum_len1"),
        spark_sum(length("field2")).alias("sum_len2"),
        count("*").alias("cnt")
    )
    
    result = aggregated.collect()
    
    estimated_shuffle_bytes = rows * 50 * 2
    processed_gb = estimated_shuffle_bytes / (1024 ** 3)
    
    return {
        "rows": rows,
        "processed_gb": processed_gb,
        "score": processed_gb,
        "join_results": len(result),
    }

def orchestrate_cluster_score(cpu_result, mem_result, hdd_result, network_result):
    normalized_cpu = cpu_result["score"] / 0.06
    normalized_mem = mem_result["score"] / 5.0
    normalized_hdd = hdd_result["score"] / 6.0
    normalized_network = network_result["score"] / 0.05
    
    cluster_score = (normalized_cpu + normalized_mem + normalized_hdd + normalized_network) / 4
    
    cluster_speed_gbps = (
        EXECUTION_SPEEDS.get("cpu", 0.0) + 
        EXECUTION_SPEEDS.get("mem", 0.0) +
        EXECUTION_SPEEDS.get("hdd", 0.0) +
        EXECUTION_SPEEDS.get("network", 0.0)
    ) / 4.0
    
    return {
        "cpu": normalized_cpu,
        "mem": normalized_mem,
        "hdd": normalized_hdd,
        "network": normalized_network,
        "cluster_score": cluster_score,
        "cluster_speed_gbps": cluster_speed_gbps,
        "cpu_gbps": cpu_result.get("speed_gbps", 0),
        "mem_gbps": mem_result.get("speed_gbps", 0),
        "hdd_gbps": hdd_result.get("speed_gbps", 0),
        "network_gbps": network_result.get("speed_gbps", 0),
    }

if __name__ == "__main__":
    os.makedirs("/tmp/spark-test", exist_ok=True)
    spark = build_spark_session()
    spark_hdd = build_spark_session_hdd()
    
    TEST_N = 5
    converge = []
    
    for i in range(TEST_N):
        cpu_result = test_cpu(spark)
        mem_result = test_mem(spark)
        hdd_result = test_hdd(spark_hdd)
        network_result = test_network(spark)
        
        local = orchestrate_cluster_score(cpu_result, mem_result, hdd_result, network_result)
        converge.append(local)
    
    avg = {
        "count": len(converge),
        "cpu": sum(v["cpu"] for v in converge) / len(converge),
        "mem": sum(v["mem"] for v in converge) / len(converge),
        "hdd": sum(v["hdd"] for v in converge) / len(converge),
        "network": sum(v["network"] for v in converge) / len(converge),
        "cluster_score": sum(v["cluster_score"] for v in converge) / len(converge),
        "cluster_speed_gbps": sum(v["cluster_speed_gbps"] for v in converge) / len(converge),
        "cpu_gbps": sum(v["cpu_gbps"] for v in converge) / len(converge),
        "mem_gbps": sum(v["mem_gbps"] for v in converge) / len(converge),
        "hdd_gbps": sum(v["hdd_gbps"] for v in converge) / len(converge),
        "network_gbps": sum(v["network_gbps"] for v in converge) / len(converge),
    }
    
    print(f"CPU score: {avg['cpu']:.6f} ({avg['cpu_gbps']:.4f} GB/s)")
    print(f"Memory score: {avg['mem']:.6f} ({avg['mem_gbps']:.4f} GB/s)")
    print(f"HDD score: {avg['hdd']:.6f} ({avg['hdd_gbps']:.4f} GB/s)")
    print(f"Network score: {avg['network']:.6f} ({avg['network_gbps']:.4f} GB/s)")
    print(f"Cluster score: {avg['cluster_score']:.6f}")
    print(f"Cluster speed: {avg['cluster_speed_gbps']:.6f} GB/s")
    
    spark.stop()
    spark_hdd.stop()
    
    try:
        shutil.rmtree("/tmp/spark-test")
    except:
        pass