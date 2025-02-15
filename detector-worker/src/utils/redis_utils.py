"""Utility functions for running actions on Redis"""

from datetime import timedelta
from typing import Any
from loguru import logger
import random
import numpy as np
from redis import Redis
from redis.commands.search.field import TagField, VectorField, TextField
from redis.commands.search.indexDefinition import IndexDefinition, IndexType
from redis.commands.search.query import Query


def add_vector(
    redis_client: Redis, 
    vector: tuple[int, ...], 
    result_class: str, 
    source: str, 
    ttl: timedelta, 
    tag: str | None = None
):
    """Adds vector to redis with a defined TTL

    Params:
        redis_client: The Redis object used to add the vector to
        vector: The vector to add
        result_class: The result identifying the vector
        source: The source of the vector
        ttl: The amount of time this vector will stay in Redis
        tag: The metadata tag to add
    """
    logger.debug(f"Adding vector into Redis with a ttl of: {ttl}, vector is: {vector}")

    key = f"doc:{random.randint(1, 1000)}"
    encoded_vector = np.array(vector).astype(np.float32).tobytes()
    mapping = {'vector': encoded_vector, 'source': source, 'result_class': result_class}
    
    if tag:
        mapping['tag'] = tag

    pipe = redis_client.pipeline()
    pipe.hset(key, mapping=mapping)
    pipe.expire(key, time=ttl)
    pipe.execute(raise_on_error=True)
    logger.debug("Finished indexing vector")



def query_knn(
    redis_client: Redis, 
    index_name: str, 
    vector: tuple[int, ...], 
    result_class: str, 
    source: str, 
    radius: float, 
    tag: str | None = None,
    path: str | None = None,
) -> Any:
    """Queries Redis for vectors in a radius of `radius` to `vector`.
    
    The query also makes sure the field `result_class` does not match.

    Params:
        redis_client The Redis object used to add the vector to
        index_name: The index to query
        vector: The vector to use as a base query
        result_class: The class identifying the vector
        source: The source of the vector
        radius: The radius to use in KNN
        tag: A tag to index. If None, will not use this field in the search.
        hash: path

    Returns: ...
    """
    logger.debug(
        "Querying Redis using KNN: "
        f"index: {index_name} "
        f"input: {vector} "
        f"result_class: {result_class} "
        f"source: {source} "
        f"radius: {radius}"
        f"tag: {tag}"
        f"path: {path}"
    )
    
    encoded_vector = np.array(vector).astype(np.float32).tobytes()
    
    query_params={"vec": encoded_vector, "radius": radius, "source": source, "class": result_class}
    query_filters=["@result_class:{$class}", "@source:{$source}"]
    if tag:
        query_params['tag'] = tag
        query_filters.append("@tag:{$tag}")
    
    base_query_string = "@vector:[VECTOR_RANGE $radius $vec]=>{$YIELD_DISTANCE_AS: score}"
    query_string = ' '.join(query_filters) + " " + base_query_string
    query = Query(query_string)

    logger.debug(f"Running query: {query_string}")
    logger.debug(f"Query parameters: {query_params}")

    result = redis_client.ft(index_name).search(
        query=query
        .sort_by("score")
        .return_fields("id", "score")
        .paging(0, 2)
        .dialect(2),
        query_params=query_params
    )

    logger.debug(f"Queried REDIS, returned: {result.docs}")
    return result.docs


def create_index(redis_client: Redis, index_name: str, vector_dimensions: int) -> bool:
    """Creates an index in Redis with `vector_dimensions` size.

    The index is composed of the following fields:
        1. vector - A FLOAT32 vector with `vector_dimensions` dimensions
        2. result_class - A class identifying the vector
        3. source - The source of the vector
        4. tag - A way to tag the vector with optional metadata to search on
        5. path - A path to a file to read

    Params:
        redis_client: The Redis object used to create the index on
        index_name: The index to create
        vector_dimensions: The size to create

    Returns:
        True if created, False if already exists.
    """
    logger.debug("Checking Redis for index {index_name}")
    try:
        redis_client.ft(index_name).info()
        logger.debug("Redis index already exists, continuing...")
        return False
    except:
        logger.debug("Redis index does not exist, creating...")
        schema = [
            VectorField(
                "vector",  # Vector Field Name
                "FLAT",
                {  # Vector Index Type: FLAT or HNSW
                    "TYPE": "FLOAT32",  # FLOAT32 or FLOAT64
                    "DIM": vector_dimensions,  # Number of Vector Dimensions
                    "DISTANCE_METRIC": "COSINE",  # Vector Search Distance Metric
                },
            ),
            TagField("result_class"),
            TagField("source"),
            TagField("tag"),
            TextField("path")
        ]

        definition = IndexDefinition(prefix=["doc:"], index_type=IndexType.HASH)

        redis_client.ft(index_name).create_index(fields=schema, definition=definition)

        logger.debug("Created Index in Redis")
        return True
