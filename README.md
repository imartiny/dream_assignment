# dream_assignment

# Smart Process Analyzer

The Smart Process Analyzer is a high-performance system designed to ingest, store, and analyze process data from various operating systems.
It provides an efficient way to handle large volumes of process data and execute complex queries.

## Features

- Multi-OS support (Unix-like systems and Windows)
- Efficient data ingestion and storage
- Smart querying capabilities
- Real-time and historical data analysis
- Scalable architecture

## Installation

1. Clone the repository:

   ```
   git clone https://github.com/imartiny/dream_assignment.git
   ```

2. Create a virtual environment and activate it:

   ```
   python -m venv venv
   source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
   ```

3. Install the required packages:

   ```
   pip install -r requirements.txt
   ```

4. Set up the environment variables:
   Create a `.env` file in the root directory and add the following:
   ```
   DATABASE_URL=sqlite:///./process_data.db
   REDIS_URL=redis://localhost:6379/0
   ```

## Usage

1. Start the FastAPI server:

   ```
   uvicorn app.main:app --reload
   ```

2. The API will be available at `http://localhost:8000`. You can access the interactive API documentation at `http://localhost:8000/docs`.

3. Use the `/api/v1/ingest` endpoint to ingest process data.

4. Use the `/api/v1/query` endpoint to query and analyze the data.

5. Use the `/api/v1/process/{{process_id}}` endpoint to get a specific process.

## Architecture and Optimizations

The Smart Process Analyzer uses several optimizations to ensure high performance and scalability:

1. Asynchronous Data Ingestion:

   - The system uses background tasks for data processing, allowing for quick response times on the API.

2. Efficient Parsing:

   - Custom parsers for different OS types ensure efficient conversion of raw data to structured format.

3. Dual-Database Approach:

   - SQLAlchemy with SQLite (easily switchable to other RDBMS) for structured data storage.
   - Redis for storing pre-aggregated data and temporary batch information.

4. Smart Query Engine:

   - Analyzes queries to determine the most efficient data source (pre-aggregated or raw data).
   - Optimizes SQL queries based on the requested aggregations and filters.

5. Data Partitioning:

   - Data is partitioned by date and OS type for efficient querying.

6. Indexing:

   - Strategic indexing on frequently queried columns for faster data retrieval.

7. Bulk Insertions:

   - Uses SQLAlchemy's bulk_insert_mappings for efficient database insertions.

8. Pre-aggregation:
   - Commonly requested aggregations are pre-computed and stored in Redis for fast retrieval.

These optimizations work together to provide a system that can handle large volumes of data with quick ingestion and query response times.
