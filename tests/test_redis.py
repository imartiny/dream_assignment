from app.redis_client import redis_client
import json
from colorama import init, Fore, Style


def inspect_redis_content():
    print(f"\n{Fore.CYAN}Inspecting Redis Content...{Style.RESET_ALL}")
    keys = redis_client.keys('*')
    for key in keys:
        key_str = key.decode('utf-8')
        value = redis_client.get(key)
        try:
            value_json = json.loads(value)
            print(f"{Fore.YELLOW}Key:{Style.RESET_ALL} {key_str}")
            print(f"{Fore.YELLOW}Value:{Style.RESET_ALL} {json.dumps(value_json, indent=2)}")
        except json.JSONDecodeError:
            print(f"{Fore.YELLOW}Key:{Style.RESET_ALL} {key_str}")
            print(f"{Fore.YELLOW}Value:{Style.RESET_ALL} {value.decode('utf-8')}")
        print("---")

# Add this to your main function
def main():
    inspect_redis_content()

main()