import argparse
import os
import requests
import time
from colorama import init, Fore, Style
from datetime import datetime, timedelta

# Initialize colorama
init(autoreset=True)

BASE_URL = "http://localhost:8000/api/v1"

def print_result(test_name, passed, message=""):
    if passed:
        print(f"{Fore.GREEN}{test_name}: Passed{Style.RESET_ALL} {message}")
    else:
        print(f"{Fore.RED}{test_name}: Failed{Style.RESET_ALL} {message}")

def read_file(file_path):
    """Read the content of the file."""
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.read()

def determine_os_type(file_name):
    """Determine OS type based on file name."""
    if 'windows' in file_name.lower():
        return 'windows'
    else:
        return 'unix'  # Default to unix for simplicity

def send_to_api(endpoint, method='POST', data=None):
    """Send request to the API."""
    url = f"{BASE_URL}/{endpoint}"
    headers = {'Content-Type': 'application/json'}
    
    try:
        if method == 'GET':
            response = requests.get(url)
        elif method == 'POST':
            response = requests.post(url, json=data, headers=headers)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")

        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"{Fore.RED}Error sending data to API: {e}{Style.RESET_ALL}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"{Fore.YELLOW}API Response: {e.response.text}{Style.RESET_ALL}")
        return None

def test_health_check():
    print(f"\n{Fore.CYAN}Testing Health Check...{Style.RESET_ALL}")
    response = send_to_api('health', method='GET')
    print_result("Health Check", response and response.get('status') == 'healthy')

def test_ingest_data(file_path):
    print(f"\n{Fore.CYAN}Testing Data Ingestion...{Style.RESET_ALL}")
    content = read_file(file_path)
    os_type = determine_os_type(os.path.basename(file_path))
    meta_info = {
        "timestamp": datetime.now().isoformat(),
        "machine_name": "test-machine",
        "machine_id": "123456",
        "os_type": os_type
    }
    payload = {
        "os_type": os_type,
        "content": content,
        "meta_info": meta_info
    }
    response = send_to_api('ingest', data=payload)
    print_result("Data Ingestion", response and 'message' in response, f"- {response['message'] if response else ''}")

def test_query_data(os_type):
    print(f"\n{Fore.CYAN}Testing Data Query...{Style.RESET_ALL}")
    query_params = {
        "start_time": (datetime.now() - timedelta(days=1)).isoformat(),
        "end_time": datetime.now().isoformat(),
        "os_type": os_type,
        "machine_id": "123456",
        "limit": 10,
        "offset": 0
    }
    response = send_to_api('query', method='POST', data=query_params)
    if response and 'records' in response:
        print_result("Data Query", True, f"- Retrieved {len(response['records'])} records")
        return response['records']
    else:
        print_result("Data Query", False)
        if response:
            print(f"{Fore.YELLOW}Response content: {response}{Style.RESET_ALL}")
        return None

def test_get_process(process_id):
    print(f"\n{Fore.CYAN}Testing Get Process (ID: {process_id})...{Style.RESET_ALL}")
    response = send_to_api(f'process/{process_id}', method='GET')
    print_result("Get Process", response and 'process' in response)

def test_not_found_scenarios():
    print(f"\n{Fore.CYAN}Testing Not Found Scenarios...{Style.RESET_ALL}")
    process_response = send_to_api('process/99999', method='GET')
    print_result("Not Found Scenarios", process_response is None)

def test_aggregation_query():
    print(f"\n{Fore.CYAN}Testing Aggregation Query...{Style.RESET_ALL}")
    query_params = {
        "start_time": (datetime.now() - timedelta(days=7)).isoformat(),
        "end_time": datetime.now().isoformat(),
        "aggregations": ['total_cpu_usage', 'total_memory_usage', 'process_count'],
        "group_by": ["os_type", "machine_id"]
    }
    response = send_to_api('query', method='POST', data=query_params)
    if response and 'records' in response:
        print_result("Aggregation Query", True, f"- Retrieved {len(response['records'])} aggregated records")
        return response['records']
    else:
        print_result("Aggregation Query", False)
        return None

def test_duplicate_data_insertion(file_path):
    print(f"\n{Fore.CYAN}Testing Duplicate Data Insertion...{Style.RESET_ALL}")
    content = read_file(file_path)
    os_type = determine_os_type(os.path.basename(file_path))
    meta_info = {
        "timestamp": datetime.now().isoformat(),
        "machine_name": "test-machine",
        "machine_id": "123456",
        "os_type": os_type
    }
    payload = {
        "os_type": os_type,
        "content": content,
        "meta_info": meta_info
    }
    
    response1 = send_to_api('ingest', data=payload)
    response2 = send_to_api('ingest', data=payload)
    
    print_result("Duplicate Data Insertion", 
                 response1 and response2 and response1['message'] == response2['message'], 
                 "- System handled duplicate data correctly" if response1 and response2 else "- Unexpected behavior with duplicate data")

def test_large_data_query():
    print(f"\n{Fore.CYAN}Testing Large Data Query...{Style.RESET_ALL}")
    query_params = {
        "start_time": (datetime.now() - timedelta(days=30)).isoformat(),
        "end_time": datetime.now().isoformat(),
        "limit": 10000,  # Requesting a large number of records
        "offset": 0
    }
    response = send_to_api('query', method='POST', data=query_params)
    print_result("Large Data Query", response and 'records' in response, f"- Retrieved {len(response['records']) if response and 'records' in response else 0} records")

def test_invalid_data_insertion(os_type):
    print(f"\n{Fore.CYAN}Testing Invalid Data Insertion...{Style.RESET_ALL}")
    invalid_payload = {
        "os_type": os_type,
        "content": "This is not valid process data",
        "meta_info": {
            "timestamp": "not_a_timestamp",
            "machine_name": 123,  # Should be a string
            "machine_id": "valid_id",
            "os_type": "invalid_version"
        }
    }
    response = send_to_api('ingest', data=invalid_payload)
    print_result("Invalid Data Insertion", response is None, "- System rejected invalid data" if response is None else "- System accepted invalid data")

def main():
    parser = argparse.ArgumentParser(description="Test the Smart Process Analyzer API")
    parser.add_argument("files", nargs='+', help="Path to the files to be ingested")
    args = parser.parse_args()

    for file in args.files:
        if not os.path.exists(file):
            print(f"{Fore.RED}Error: File {file} does not exist.{Style.RESET_ALL}")
            return

        os_type = 'unix' if any(os in file for os in ['linux', 'unix', 'mac']) else 'windows'
        
        print(f"\n{Fore.MAGENTA}Testing with file: {file} (OS Type: {os_type}){Style.RESET_ALL}")
        
        # test_health_check()
        test_ingest_data(file)
        
        print(f"{Fore.YELLOW}Waiting for data to be processed...{Style.RESET_ALL}")
        time.sleep(2)
        
        records = test_query_data(os_type)
        if records:
            test_get_process(records[-1]['id'])
        
        test_not_found_scenarios()
        test_aggregation_query()
        test_duplicate_data_insertion(file)
        test_large_data_query()
        test_invalid_data_insertion('invalid')
        test_invalid_data_insertion('unix')

    print(f"\n{Fore.MAGENTA}All tests completed.{Style.RESET_ALL}")

if __name__ == "__main__":
    main()