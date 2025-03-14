"""

This script is used for creating a collection of publications per specific concepts from the
FoS taxonomy. Given levels (L3, L4) of the taxonomy, the script retrieves classified publications in 
the concepts of these levels. We are going to use pyspark to process the predictions. The prediction folder
must be mounted in the container. In case you do not have the predictions, please contact as at
https://github.com/iNoBo/scinobo-fos-taxonomy/discussions.

Finally, you must have the papers metadata in parquet format. They are from the Semantic Scholar dump.
"""

import json, os
import argparse

from pyspark.sql import SparkSession
from pyspark.sql.window import Window
from pyspark.sql.functions import col, row_number
from pyspark.conf import SparkConf



def parse_args():
    ##############################################
    parser = argparse.ArgumentParser()
    parser.add_argument("--infer_results_dir",type=str, help="The path where the predictions exist", required=True)
    parser.add_argument("--papers_dir",type=str, help="The path where the papers exist", required=True)
    parser.add_argument("--out_results",type=str, help="The path where the output will be saved", required=True)
    parser.add_argument("--fos_taxonomy_path", type=str, help="The path with the fos taxonomy", required=True)
    parser.add_argument("--tmp_path", type=str, help="The path to the tmp folder for spark", required=True)
    parser.add_argument("--datalake_path", type=str, help="The path to the datalake folder for spark", required=True)
    parser.add_argument("--year_span", type=str, help="The years to consider for the validation", required=False, default="2010-2023")
    args = parser.parse_args()
    return args
    ##############################################
    

################################################
def create_spark_conf(tmp_path, datalake_path):
    conf = SparkConf()
    conf.set('spark.executor.cores', '6')
    conf.set('spark.executor.memory', '30g')
    conf.set('spark.executor.instances', '6')
    conf.set('spark.sql.shuffle.partitions', 600)
    conf.set('spark.sql.parquet.columnarReaderBatchSize', 1000)
    conf.set("spark.driver.memory", "90g")
    conf.set("spark.memory.offHeap.enabled", True)
    conf.set("spark.sql.files.ignoreCorruptFiles", True)
    conf.set("spark.memory.offHeap.size","20g") 

    conf.set('spark.kubernetes.executor.volumes.hostPath.datalake.options.path', datalake_path)
    conf.set('spark.kubernetes.executor.volumes.hostPath.datalake.options.type', 'Directory')
    conf.set('spark.kubernetes.executor.volumes.hostPath.datalake.mount.path', datalake_path)

    conf.set('spark.kubernetes.executor.volumes.hostPath.tmp.options.path', tmp_path)
    conf.set('spark.kubernetes.executor.volumes.hostPath.tmp.options.type', 'Directory')
    conf.set('spark.kubernetes.executor.volumes.hostPath.tmp.mount.path', tmp_path)

    conf.set('spark.kubernetes.driver.volumes.hostPath.datalake.options.path', datalake_path)
    conf.set('spark.kubernetes.driver.volumes.hostPath.datalake.options.type', 'Directory')
    conf.set('spark.kubernetes.driver.volumes.hostPath.datalake.mount.path', datalake_path)

    conf.set('spark.kubernetes.driver.volumes.hostPath.tmp.options.path', tmp_path)
    conf.set('spark.kubernetes.driver.volumes.hostPath.tmp.options.type', 'Directory')
    conf.set('spark.kubernetes.driver.volumes.hostPath.tmp.mount.path', tmp_path)
    
    conf.set('spark.yarn.executor.volumes.hostPath.datalake.options.path', datalake_path)
    conf.set('spark.yarn.executor.volumes.hostPath.datalake.options.type', 'Directory')
    conf.set('spark.yarn.executor.volumes.hostPath.datalake.mount.path', datalake_path)

    conf.set('spark.yarn.executor.volumes.hostPath.tmp.options.path', tmp_path)
    conf.set('spark.yarn.executor.volumes.hostPath.tmp.options.type', 'Directory')
    conf.set('spark.yarn.executor.volumes.hostPath.tmp.mount.path', tmp_path)

    conf.set('spark.yarn.driver.volumes.hostPath.datalake.options.path', datalake_path)
    conf.set('spark.yarn.driver.volumes.hostPath.datalake.options.type', 'Directory')
    conf.set('spark.yarn.driver.volumes.hostPath.datalake.mount.path', datalake_path)

    conf.set('spark.yarn.driver.volumes.hostPath.tmp.options.path', tmp_path)
    conf.set('spark.yarn.driver.volumes.hostPath.tmp.options.type', 'Directory')
    conf.set('spark.yarn.driver.volumes.hostPath.tmp.mount.path', tmp_path)
    
    conf.set('spark.local.dir', tmp_path)
    return conf
    

def create_spark_session(conf, app_name: str):
    spark = SparkSession.builder.config(conf=conf).appName(app_name).getOrCreate()
    return spark
################################################


def load_fos(spark, idir: list):
    fos_predictions_df = spark.read.option("mergeSchema","true").parquet(*idir)
    # drop the column "__index_level_0__"
    fos_predictions_df = fos_predictions_df.drop("__index_level_0__")
    fos_predictions_df = fos_predictions_df.dropDuplicates() # drop entire rows that are duplicates
    return fos_predictions_df


def load_papers(spark, idir: str):
    # load the table of "papers" and dump only the required columns
    paper_metadata_df = spark.read.parquet(idir)
    # drop duplicates based on id
    paper_metadata_df = paper_metadata_df.dropDuplicates(["id"])
    return paper_metadata_df


def get_fos_prediction_folders(fos_predictions_path: str, start_year: int, end_year: int):
    my_paths = []
    for year in os.listdir(fos_predictions_path):
            if int(year) >= start_year and int(year) <= end_year:
                folder_path = os.path.join(fos_predictions_path, year, "output")
                for in_folder in os.listdir(folder_path):
                        # check if the folder contains parquet files
                        if any([file.endswith(".parquet") for file in os.listdir(os.path.join(folder_path, in_folder))]):
                            my_path = os.path.join(folder_path, in_folder, "*.parquet")  
                            my_paths.append(my_path)
    return my_paths


def drop_columns(df, cols):
    for col in cols:
        df = df.drop(col)
    return df


def collect_concepts(top_per_L3, top_per_L4):
    concepts = dict()
    for row in top_per_L3.collect():
        if row.L3 in concepts:
            concepts[row.L3].append(row.asDict())
        else:
            concepts[row.L3] = [row.asDict()]
    for row in top_per_L4.collect():
        if row.L4 in concepts:
            concepts[row.L4].append(row.asDict())
        else:
            concepts[row.L4] = [row.asDict()]
    return concepts

    
def main():
    # Parse the arguments
    args = parse_args()
    predictions_dir = args.infer_results_dir
    output_path = args.out_results
    papers_dir = args.papers_dir
    tmp_path = args.tmp_path
    datalake_path = args.datalake_path
    year_span = args.year_span
    # Create the spark configuration
    conf = create_spark_conf(tmp_path, datalake_path)
    # Create the spark session
    spark = create_spark_session(conf, "Build-FoS-validation-Collection")
    # Load the fos predictions
    start_year, end_year = year_span.split("-")
    start_year, end_year = int(start_year), int(end_year)
    fos_predictions_paths = get_fos_prediction_folders(predictions_dir, start_year, end_year)
    fos_predictions = load_fos(spark, fos_predictions_paths)
    # group by L3 and sort based on the column "score_for_L3"
    window_spec = Window.partitionBy("L3").orderBy(col("score_for_L3").desc())
    ranked_df_l3 = fos_predictions.withColumn("row_number", row_number().over(window_spec))
    top_per_L3 = ranked_df_l3.filter(col("row_number") <= 10)
    # drop rows where the L3 is null
    top_per_L3 = top_per_L3.filter(col("L3").isNotNull())
    # do the same for L4
    window_spec = Window.partitionBy("L4").orderBy(col("score_for_L4").desc())
    ranked_df_l4 = fos_predictions.withColumn("row_number", row_number().over(window_spec))
    top_per_L4 = ranked_df_l4.filter(col("row_number") <= 10)
    # drop rows where the L3 is null
    top_per_L4 = top_per_L4.filter(col("L4").isNotNull())
    # load the papers to retrieve the metadata for the publications
    papers_df = load_papers(spark, papers_dir)
    # filter the papers based on the years span (use the column 'year')
    papers_df = papers_df.filter(col("year").between(start_year, end_year))
    # join the papers with the top_per_L3 and top_per_L4
    top_per_L3 = top_per_L3.join(papers_df, top_per_L3.id == papers_df.id, how="left")
    top_per_L4 = top_per_L4.join(papers_df, top_per_L4.id == papers_df.id, how="left")
    # save the results into a json file - they will be flatten
    # drop columns that are not needed
    """
    Index(['authors', 'id', 'title', 'S2Url', 'year', 'doi', 'pmid', 'magId',
       'externalids', 'publicationtypes', 'publicationdate', 'journalName',
       'journalPages', 'journalVolume', 'venue', 'publicationvenueid',
       'isopenaccess', 'referencecount', 'citationcount',
       'influentialcitationcount', 'paperAbstract', 'openaccessinfo'],
    """    
    top_per_L3 = drop_columns(
        top_per_L3,
        cols=[
            'authors',
            'id',
            'S2Url',
            'pmid',
            'magId',
            'externalids',
            'publicationdate',
            'journalPages',
            'journalVolume',
            'isopenaccess',
            'referencecount',
            'citationcount',
            'influentialcitationcount',
            'openaccessinfo'
        ]
    )
    top_per_L4 = drop_columns(
        top_per_L4,
        cols=[
            'authors',
            'id',
            'S2Url',
            'pmid',
            'magId',
            'externalids',
            'publicationdate',
            'journalPages',
            'journalVolume',
            'isopenaccess',
            'referencecount',
            'citationcount',
            'influentialcitationcount',
            'openaccessinfo'
        ]
    )
    # save the results in a dict
    concepts = collect_concepts(top_per_L3, top_per_L4)
    with open(output_path, "w") as f:
        json.dump(concepts, f)


if __name__ == "__main__":
    main()