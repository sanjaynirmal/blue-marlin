#  Licensed to the Apache Software Foundation (ASF) under one
#  or more contributor license agreements.  See the NOTICE file
#  distributed with this work for additional information
#  regarding copyright ownership.  The ASF licenses this file
#  to you under the Apache License, Version 2.0 (the
#  "License"); you may not use this file except in compliance
#  with the License.  You may obtain a copy of the License at

#  http://www.apache.org/licenses/LICENSE-2.0.html

#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

import yaml
import argparse
import pyspark.sql.functions as fn

from pyspark import SparkContext
from pyspark.sql import HiveContext
from pyspark.sql.types import FloatType, StringType, StructType, StructField, ArrayType, MapType, StructType

# from rest_client import predict, str_to_intlist
import requests
import json
import argparse
from pyspark.sql.functions import udf
from math import sqrt
import time
import numpy as np
import itertools
import heapq

'''
This process generates the top-n-similarity table.

spark-submit --master yarn --num-executors 20 --executor-cores 5 --executor-memory 16G --driver-memory 16G --conf spark.driver.maxResultSize=5g --conf spark.hadoop.hive.exec.dynamic.partition=true --conf spark.hadoop.hive.exec.dynamic.partition.mode=nonstrict top_n_similarity_table_generator.py config.yml

The top-n-similarity table is 

|user| top-N-similarity|top-n-users
|:-------------| :------------: |
|user-1-did| [similarity-score-11, similarity-score-12, similarity-score-13] |[user-did-1, user-did-2, user-did-3]|
|user-2-did| [similarity-score-21, similarity-score-22, similarity-score-23] |[user-did-10, user-did-20, user-did-30]|
|user-3-did| [similarity-score-31, similarity-score-32, similarity-score-33] |[user-did-23, user-did-87, user-did-45]|

'''


def __save_as_table(df, table_name, hive_context, create_table):

    if create_table:
        command = """
            DROP TABLE IF EXISTS {}
            """.format(table_name)

        hive_context.sql(command)

        df.createOrReplaceTempView("r907_temp_table")

        command = """
            CREATE TABLE IF NOT EXISTS {} as select * from r907_temp_table
            """.format(table_name)

        hive_context.sql(command)


def run(sc, hive_context, cfg):

    score_vector_alpha_table = cfg['score_vector_rebucketing']['score_vector_alpha_table']
    similarity_table = cfg['top_n_similarity']['similarity_table']
    N = cfg['top_n_similarity']['top_n']

    command = "SELECT did, score_vector FROM {}".format(score_vector_alpha_table)

    # |0004f3b4731abafa9ac54d04cb88782ed61d30531262decd799d91beb6d6246a|0         |
    # [0.24231663, 0.20828941, 0.0]|
    df = hive_context.sql(command)
    df = df.withColumn('top_n_user_score', fn.array())

    alpha_bucket_size = cfg['score_vector_rebucketing']['alpha_did_bucket_size']
    alpha_bucket_step = cfg['top_n_similarity']['alpha_did_bucket_step']

    first_round = True
    for start_bucket in range(0, alpha_bucket_size,alpha_bucket_step):
        command = "SELECT did, did_bucket, score_vector, alpha_did_bucket FROM {} WHERE alpha_did_bucket BETWEEN {} AND {}".format(score_vector_alpha_table, 
        start_bucket, start_bucket + alpha_bucket_size - 1)

        df_user = hive_context.sql(command)
        block_user = df_user.select('did', 'score_vector').collect()
        block_user = ([_['did'] for _ in block_user], [_['score_vector'] for _ in block_user])
        block_user_broadcast = sc.broadcast(block_user)

        def calculate_similarity(user_score_vector, top_n_user_score):
            user_score_vector = np.array(user_score_vector)
            dids, other_score_vectors = block_user_broadcast.value
            other_score_vectors = np.array(other_score_vectors)
            product = np.matmul(user_score_vector, other_score_vectors.transpose()).tolist()
            user_score_s = list(itertools.izip(dids, product))
            user_score_s.extend(top_n_user_score)
            user_score_s = heapq.nlargest(N, user_score_s, key=lambda x: x[1])
            return user_score_s

        elements_type = StructType([StructField('did', StringType(), False), StructField('score', FloatType(), False)])
        df = df.withColumn('top_n_user_score', udf(calculate_similarity, ArrayType(elements_type))(df.score_vector, df.top_n_user_score))
    
    __save_as_table(df.select('did', 'top_n_user_score'), similarity_table, hive_context, True)
        


if __name__ == "__main__":
    start = time.time()
    parser = argparse.ArgumentParser(description=" ")
    parser.add_argument('config_file')
    args = parser.parse_args()
    with open(args.config_file, 'r') as yml_file:
        cfg = yaml.safe_load(yml_file)

    sc = SparkContext.getOrCreate()
    sc.setLogLevel('INFO')
    hive_context = HiveContext(sc)

    run(sc=sc, hive_context=hive_context, cfg=cfg)
    sc.stop()
    end = time.time()
    print('Runtime of the program is:', (end - start))
