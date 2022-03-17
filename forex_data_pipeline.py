from airflow import DAG
from datetime import datetime, timedelta
from airflow.providers.http.sensors.http import HttpSensor
from airflow.sensors.filesystem import FileSensor
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.providers.apache.hive.operators.hive import HiveOperator
from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator
from airflow.contrib.operators.slack_webhook_operator import SlackWebhookOperator
import csv
import requests
import json

def download_rates():
    BASE_URL = "https://gist.githubusercontent.com/marclamberti/f45f872dea4dfd3eaa015a4a1af4b39b/raw/"
    ENDPOINTS = {
        'USD': 'api_forex_exchange_usd.json',
        'EUR': 'api_forex_exchange_eur.json'
    }
    with open('/opt/airflow/dags/files/forex_currencies.csv') as forex_currencies:
        reader = csv.DictReader(forex_currencies, delimiter=';')
        for idx, row in enumerate(reader):
            base = row['base']
            with_pairs = row['with_pairs'].split(' ')
            indata = requests.get(f"{BASE_URL}{ENDPOINTS[base]}").json()
            outdata = {'base': base, 'rates': {}, 'last_update': indata['date']}
            for pair in with_pairs:
                outdata['rates'][pair] = indata['rates'][pair]
            with open('/opt/airflow/dags/files/forex_rates.json', 'a') as outfile:
                json.dump(outdata, outfile)
                outfile.write('\n')

def _get_message() -> str:
	return 'Hi from forex_data_pipeline' 


default_args = {
	
	"owner": "airflow",
	"email_on_failure": False,
	"email_on_retry": False,
	"email": "admin@admin.com.br",
	"retries": 1,
	"retry_delay": timedelta(minutes = 5)
}

with DAG("forex_data_pipeline", start_date = datetime(2022, 1, 1), 
	schedule_interval = "@daily", default_args = default_args, catchup = False) as dag:

	is_forex_rates_available = HttpSensor(

		task_id = "is_forex_rates_available",
		http_conn_id = 'forex_api',
		endpoint = 'marclamberti/f45f872dea4dfd3eaa015a4a1af4b39b',
		response_check = lambda response: 'rates' in response.text,
		poke_interval = 5,
		timeout = 20
		)


	is_forex_currencies_file_available = FileSensor(

		task_id = 'is_forex_currencies_file_available',
		fs_conn_id = 'forex_path',
		filepath = 'forex_currencies.csv',
		poke_interval = 5,
		timeout = 20


		)


	downloading_rates = PythonOperator(

		task_id = 'downloading_rates',
		python_callable = download_rates,



		)


	saving_rates = BashOperator(

		task_id = 'saving_rates',
		bash_command = """
			hdfs dfs -mkdir -p /forex && \
			hdfs dfs -put -f $AIRFLOW_HOME/dags/files/forex_rates.json /forex
		"""



		)


	creating_forex_rates_table = HiveOperator(
        task_id="creating_forex_rates_table",
        hive_cli_conn_id="hive_conn",
        hql="""
            CREATE EXTERNAL TABLE IF NOT EXISTS forex_rates(
                base STRING,
                last_update DATE,
                eur DOUBLE,
                usd DOUBLE,
                nzd DOUBLE,
                gbp DOUBLE,
                jpy DOUBLE,
                cad DOUBLE
                )
            ROW FORMAT DELIMITED
            FIELDS TERMINATED BY ','
            STORED AS TEXTFILE
        """
    )

	forex_processing = SparkSubmitOperator(

		task_id = 'forex_processing',
		application = '/opt/airflow/dags/scripts/forex_processing.py',
		conn_id = 'spark_conn',
		verbose = False 


		)

	send_slack_notification = SlackWebhookOperator(

	        task_id='send_slack_notification',
	        http_conn_id='slack_conn',
	        message= 'hello',
	        channel='#airflow_test'
	        )


	is_forex_rates_available >> is_forex_currencies_file_available >> downloading_rates >> saving_rates 
	saving_rates  >> creating_forex_rates_table >> forex_processing >> send_slack_notification




	

