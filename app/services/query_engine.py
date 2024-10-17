"""
This module implements a SmartQueryEngine for efficient data retrieval and analysis.
It supports querying from both pre-aggregated data in Redis and raw data in SQL database.
"""

from typing import List, Dict, Any, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models import ProcessData
from app.redis_client import redis_client
import json
from functools import lru_cache

class SmartQueryEngine:
    """
    A smart query engine that optimizes and executes queries based on input parameters.
    It can query different data sources (pre-aggregated store, SQL store) depending on the query type and required aggregations.
    """

    @staticmethod
    def execute_query(query_params: Dict[str, Any], db: Session) -> Tuple[int, List[Dict[str, Any]]]:
        """
        Execute a query based on the provided parameters.

        Args:
            query_params (Dict[str, Any]): A dictionary containing query parameters.
            db (Session): SQLAlchemy database session.

        Returns:
            Tuple[int, List[Dict[str, Any]]]: A tuple containing the count of results and the results themselves.
        """
        analyzed_query = SmartQueryEngine._analyze_query(query_params)
        optimized_query = SmartQueryEngine._optimize_query(analyzed_query)
        data_source = SmartQueryEngine._select_data_source(optimized_query)
        result = SmartQueryEngine._execute_optimized_query(optimized_query, data_source, db)
        return len(result), result

    @staticmethod
    def _analyze_query(query_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze and structure the input query parameters.

        Args:
            query_params (Dict[str, Any]): Raw query parameters.

        Returns:
            Dict[str, Any]: Structured query parameters.
        """
        return {
            "type": query_params.get('type', 'historical'),
            "start_time": query_params.get('start_time'),
            "end_time": query_params.get('end_time'),
            "os_type": query_params.get('os_type'),
            "machine_id": query_params.get('machine_id'),
            "command": query_params.get('command'),
            "cpu_usage_gt": query_params.get('cpu_usage_gt'),
            "memory_usage_gt": query_params.get('memory_usage_gt'),
            "limit": query_params.get('limit', 100),
            "offset": query_params.get('offset', 0),
            "aggregations": query_params.get('aggregations', []),
            "group_by": query_params.get('group_by', [])
        }

    @staticmethod
    def _optimize_query(analyzed_query: Dict[str, Any]) -> Dict[str, Any]:
        """
        Optimize the query for better performance and data retrieval.

        Args:
            analyzed_query (Dict[str, Any]): The analyzed query parameters.

        Returns:
            Dict[str, Any]: Optimized query parameters.
        """
        optimized = analyzed_query.copy()

        # Set default time range if not provided
        now = datetime.now()
        if not optimized['start_time']:
            optimized['start_time'] = now - timedelta(days=30)
        if not optimized['end_time']:
            optimized['end_time'] = now

        # Ensure start_time is before end_time
        if optimized['start_time'] > optimized['end_time']:
            optimized['start_time'], optimized['end_time'] = optimized['end_time'], optimized['start_time']

        # Limit the time range to prevent overly broad queries
        max_time_range = timedelta(days=365)  # Example: 1 year max
        if optimized['end_time'] - optimized['start_time'] > max_time_range:
            optimized['start_time'] = optimized['end_time'] - max_time_range

        # Set a reasonable default limit if not provided
        if not optimized.get('limit'):
            optimized['limit'] = 100

        # Cap the maximum limit to prevent excessive data retrieval
        optimized['limit'] = min(optimized.get('limit', 100), 1000)

        # Ensure offset is non-negative
        optimized['offset'] = max(optimized.get('offset', 0), 0)

        # Optimize aggregations
        if optimized.get('aggregations'):
            optimized['aggregations'] = SmartQueryEngine._optimize_aggregations(optimized['aggregations'])

        # Optimize filters
        optimized['filters'] = SmartQueryEngine._optimize_filters(optimized)

        return optimized

    @staticmethod
    def _optimize_aggregations(aggregations: List[str]) -> List[str]:
        """
        Optimize the list of aggregations.

        Args:
            aggregations (List[str]): List of aggregation operations.

        Returns:
            List[str]: Optimized list of aggregations.
        """
        # Remove duplicates while preserving order
        unique_aggregations = list(dict.fromkeys(aggregations))

        # Define priority order for aggregations
        priority_order = ['count', 'sum', 'avg', 'min', 'max']

        # Sort aggregations based on priority
        return sorted(unique_aggregations, key=lambda x: priority_order.index(x.split('_')[0]) if x.split('_')[0] in priority_order else len(priority_order))

    @staticmethod
    def _optimize_filters(query: Dict[str, Any]) -> Dict[str, Any]:
        """
        Optimize the query filters.

        Args:
            query (Dict[str, Any]): The query parameters.

        Returns:
            Dict[str, Any]: Optimized filters.
        """
        filters = {}

        # Only include non-None filter values
        for key in ['os_type', 'machine_id', 'command']:
            if query.get(key) is not None:
                filters[key] = query[key]

        # Optimize numeric filters
        if query.get('cpu_usage_gt') is not None:
            filters['cpu_usage_gt'] = max(0, query['cpu_usage_gt'])
        if query.get('memory_usage_gt') is not None:
            filters['memory_usage_gt'] = max(0, query['memory_usage_gt'])

        return filters

    @staticmethod
    def _select_data_source(optimized_query: Dict[str, Any]) -> str:
        """
        Select the appropriate data source based on the query type and aggregations.

        Args:
            optimized_query (Dict[str, Any]): The optimized query parameters.

        Returns:
            str: The selected data source ('raw_data_store', 'pre_aggregated_store', or 'sql_store').
        """
        if optimized_query.get('type') == 'real_time':
            return 'raw_data_store'
        
        aggregations: List[str] = optimized_query.get('aggregations', [])
        
        if not aggregations:
            return 'sql_store'  # Default to sql_store if no aggregations
        
        pre_aggregated_aggs = {'total_cpu_usage', 'total_memory_usage', 'process_count'}
        if all(agg in pre_aggregated_aggs for agg in aggregations):
            return 'pre_aggregated_store'
        
        return 'sql_store'  # Default to sql_store for any other case

    @staticmethod
    def _execute_optimized_query(optimized_query: Dict[str, Any], data_source: str, db: Session) -> List[Dict[str, Any]]:
        """
        Execute the optimized query on the selected data source.

        Args:
            optimized_query (Dict[str, Any]): The optimized query parameters.
            data_source (str): The selected data source.
            db (Session): SQLAlchemy database session.

        Returns:
            List[Dict[str, Any]]: Query results.

        Raises:
            NotImplementedError: If the raw_data_store is selected (not implemented in this example).
        """
        if data_source == 'pre_aggregated_store':
            return SmartQueryEngine._execute_on_pre_aggregated(optimized_query)
        elif data_source == 'sql_store':
            return SmartQueryEngine._execute_on_sql(optimized_query, db)
        else:
            raise NotImplementedError("Raw data store queries not implemented in this example")

    @staticmethod
    @lru_cache(maxsize=128)
    def _get_aggregated_data(partition_key: str) -> Dict[str, Any]:
        """
        Retrieve and parse aggregated data from Redis with LRU caching.

        Args:
            partition_key (str): The key for the aggregated data in Redis.

        Returns:
            Dict[str, Any]: Parsed aggregated data or an empty dict if not found.
        """
        aggregated_data = redis_client.get(f"agg_{partition_key}")
        if aggregated_data:
            return json.loads(aggregated_data)
        return {}

    @staticmethod
    def _execute_on_pre_aggregated(optimized_query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Execute the query on pre-aggregated data stored in Redis.

        Args:
            optimized_query (Dict[str, Any]): The optimized query parameters.

        Returns:
            List[Dict[str, Any]]: Query results from pre-aggregated data.
        """
        start_date = optimized_query['start_time'].date()
        end_date = optimized_query['end_time'].date()
        current_date = start_date
        results = []
        while current_date <= end_date:
            for os_type in optimized_query['filters'].get('os_type', ['windows', 'linux', 'mac']):
                partition_key = f"{current_date}_{os_type}"
                aggregated_data = SmartQueryEngine._get_aggregated_data(partition_key)
                if aggregated_data:
                    results.append(aggregated_data)
            current_date += timedelta(days=1)
        return results

    @staticmethod
    def _get_aggregation_func(agg_type: str, column: str):
        """
        Map aggregation type to SQLAlchemy function.

        Args:
            agg_type (str): Type of aggregation (e.g., 'avg', 'max', 'min', 'sum', 'count').
            column (str): The column to apply the aggregation to.

        Returns:
            function: SQLAlchemy aggregation function.
        """
        agg_map = {
            'avg': func.avg,
            'max': func.max,
            'min': func.min,
            'sum': func.sum,
            'count': func.count,
        }
        return agg_map.get(agg_type, func.avg)(getattr(ProcessData, column))

    @staticmethod
    def _execute_on_sql(optimized_query: Dict[str, Any], db: Session) -> List[Dict[str, Any]]:
        """
        Execute the query on the SQL database.

        Args:
            optimized_query (Dict[str, Any]): The optimized query parameters.
            db (Session): SQLAlchemy database session.

        Returns:
            List[Dict[str, Any]]: Query results from SQL database.
        """
        query = db.query(ProcessData)
        # # Apply time range filter
        if optimized_query.get('start_time'):
            query = query.filter(ProcessData.timestamp >= optimized_query['start_time'])
        if optimized_query.get('end_time'):
            query = query.filter(ProcessData.timestamp <= optimized_query['end_time'])
        
        # # Apply additional filters
        if optimized_query.get('os_type'):
            query = query.filter(ProcessData.os_type == optimized_query['os_type'])
        if optimized_query.get('machine_id'):
            query = query.filter(ProcessData.machine_id == optimized_query['machine_id'])
        if optimized_query.get('command'):
            query = query.filter(ProcessData.command.ilike(f"%{optimized_query['command']}%"))
        if optimized_query.get('cpu_usage_gt') is not None:
            query = query.filter(ProcessData.cpu_usage > optimized_query['cpu_usage_gt'])
        if optimized_query.get('memory_usage_gt') is not None:
            query = query.filter(ProcessData.mem_usage > optimized_query['memory_usage_gt'])
        
        # # Apply grouping
        group_by = optimized_query.get('group_by', [])
        if group_by:
            query = query.group_by(*[getattr(ProcessData, col) for col in group_by if hasattr(ProcessData, col)])
        
        # # Apply aggregations
        aggregations = optimized_query.get('aggregations', [])
        if aggregations:
            select_entities = [getattr(ProcessData, col) for col in group_by if hasattr(ProcessData, col)]
            for agg in aggregations:
                agg_parts = agg.split('_')
                if len(agg_parts) >= 2:
                    agg_type, column = agg_parts[0], '_'.join(agg_parts[1:])
                    if hasattr(ProcessData, column):
                        select_entities.append(SmartQueryEngine._get_aggregation_func(agg_type, column).label(agg))
            query = query.with_entities(*select_entities)
        
        # # Apply limit and offset
        limit = optimized_query.get('limit', 100)
        offset = optimized_query.get('offset', 0)
        query = query.limit(limit).offset(offset)

        # Execute query and return results
        results = query.all()
        return [row._asdict() if hasattr(row, '_asdict') else row.to_dict() for row in results]
