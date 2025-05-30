# main.py

from input_collector import collect_user_inputs
from trader import run_trader

if __name__ == "__main__":
    user_data = collect_user_inputs()
    client_id = 1001  # You can change this if needed
    run_trader(user_data, client_id)
