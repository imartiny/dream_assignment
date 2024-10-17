
import json
import pandas as pd

from typing import Dict, Any, List

from app.database import SessionLocal
from app.models import ProcessData
from app.parsers.parser_factory import ParserFactory
from app.redis_client import redis_client

class DataOrganizer:
    """
    A class to organize and manage process data, including storing in Redis
    and updating a SQL database.
    """
    @staticmethod
    def store_process_data_in_redis(meta_info: Dict[str, Any], process_data_list: List[Dict[str, Any]]) -> str:
        """
        Stores process data and associated metadata in Redis.

        Args:
            meta_info (Dict[str, Any]): A dictionary containing metadata such as timestamp,
                                          machine name, machine ID, and OS type.
            process_data_list (List[Dict[str, Any]]): A list of process data dictionaries to store.

        Returns:
            str: A unique batch ID for the stored data.
            int: length of results
        """
        batch_id = f"batch_{pd.Timestamp.now().strftime('%Y%m%d%H%M%S')}"
        data_to_store = {
            "meta_info": {
                "timestamp": meta_info['timestamp'],
                "machine_name": meta_info['machine_name'],
                "machine_id": meta_info['machine_id'],
                "os_type": meta_info['os_type'],
            },
            "process_data": [data.to_dict() for data in process_data_list]  # Convert SQLAlchemy object to dict
        }
        
        redis_client.set(batch_id, json.dumps(data_to_store))
        return batch_id, len(process_data_list)

    @staticmethod
    async def receive_and_parse_data(data: Dict[str, Any]) -> str:
        """
        Receives raw data, parses it using the appropriate parser, and stores it in Redis.

        Args:
            data (Dict[str, Any]): A dictionary containing 'os_type', 'content', and 'meta_info'.

        Returns:
            str: The batch ID for the stored data in Redis.

        Raises:
            ValueError: If required fields 'os_type' or 'content' are missing.
        """
        os_type = data.get('os_type')
        raw_content = data.get('content')
        meta_info_data = data.get('meta_info', {})

        if not os_type or not raw_content:
            raise ValueError("Missing required fields: os_type and content")

        parser = ParserFactory.get_parser(os_type)
        parsed_data = parser.parse(raw_content)

        return DataOrganizer.store_process_data_in_redis(meta_info_data, parsed_data)

    @staticmethod
    async def process_and_store_data(batch_id: str) -> None:
        """
        Processes and stores data from Redis into a SQL database after validating.

        Args:
            batch_id (str): The unique batch ID for retrieving data from Redis.

        Returns:
            None
        """
        raw_data = redis_client.get(batch_id)
        
        if not raw_data:
            print(f"No data found for batch_id: {batch_id}")
            return
        try:
            data = json.loads(raw_data)
            if 'process_data' not in data or 'meta_info' not in data:
                print(f"Missing required keys in the data for batch_id: {batch_id}")
                return
            
            for process in data['process_data']:
                process.update(data['meta_info'])
            
            df = pd.DataFrame(data['process_data'])
            
            if 'timestamp' not in df.columns:
                print(f"Missing 'timestamp' column in the data for batch_id: {batch_id}")
                return
            
            df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
            df['partition_key'] = df['timestamp'].dt.to_period('D').astype(str) + '_' + df['os_type']
            
            DataOrganizer._update_sql_database(df)
            DataOrganizer._update_redis_aggregations(df)
            
            redis_client.delete(batch_id)
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            print(f"Error processing data for batch_id {batch_id}: {e}")

    @staticmethod
    def _update_sql_database(df: pd.DataFrame) -> None:
        session = SessionLocal()
        try:
            records = df.to_dict('records')
            session.bulk_insert_mappings(ProcessData, records)
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    @staticmethod
    def _update_redis_aggregations(df: pd.DataFrame) -> None:
        """
        Updates the SQL database with new records from the given DataFrame.

        Args:
            df (pd.DataFrame): A DataFrame containing the process data to store.

        Returns:
            None

        Raises:
            Exception: If there's an error during the database transaction.
        """
        for partition_key, partition_df in df.groupby('partition_key'):
            aggregated_data = {
                'total_cpu_usage': float(partition_df['cpu_usage'].sum()),
                'total_memory_usage': float(partition_df['mem_usage'].sum()),
                'process_count': int(partition_df['command'].nunique()),
                'top_cpu_processes': partition_df.nlargest(10, 'cpu_usage')[['command', 'cpu_usage']].to_dict('records'),
                'top_memory_processes': partition_df.nlargest(10, 'mem_usage')[['command', 'mem_usage']].to_dict('records')
            }
            redis_client.set(f"agg_{partition_key}", json.dumps(aggregated_data))
        
