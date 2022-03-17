This is a project based on the first part of Marc Lamberti airflow course.

The main idea is to get forex data from API, process using spark, loading into a hive data warehouse and send a slack notification.

1 - Check if API is available
2 - Download Forex rates from API
3 - Move forex rates into Hadoop HDFS
4 - Create a Hive table
5 - Process the rates using Spark and load into the hive table
6 - Send a Slack notification abou the rate