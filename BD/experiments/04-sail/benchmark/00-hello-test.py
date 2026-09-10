# we need to ad a 2 way IP binding to the spark driver, 
# otherwise it will fail to connect to the spark master when running in a docker container 
# returning the error: 
#
# 26/08/30 11:46:20 WARN TaskSchedulerImpl: Initial job has not accepted any resources; 
# check your cluster UI to ensure that workers are registered and have sufficient resources


from pyspark.sql import SparkSession
from pyspark.sql.functions import when, lit
import os

spark = (
    SparkSession.builder
    .appName("HelloSpark")
    .remote("sc://10.0.0.79:6066")
    .getOrCreate()
)

df = (
    spark.range(2)
    .select(
        when(lit(True), lit("hello")).otherwise(lit("world")).alias("word")
    )
)

df.show()
print("Rows:", df.count())

spark.stop()