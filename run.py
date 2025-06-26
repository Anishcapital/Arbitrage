# run.py
import subprocess
import threading
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

def run_melbet_instance(instance_id):
    """Run a single instance of melbet.py"""
    print(f"Starting melbet instance {instance_id}")
    try:
        process = subprocess.run(['python', 'melbet.py'], 
                               capture_output=True, 
                               text=True,
                               check=True)
        print(f"Melbet instance {instance_id} completed successfully")
        return f"melbet_{instance_id}", True, process.stdout
    except subprocess.CalledProcessError as e:
        print(f"Melbet instance {instance_id} failed: {e}")
        return f"melbet_{instance_id}", False, e.stderr

def run_mostbet_instance(instance_id):
    """Run a single instance of mostbet.py"""
    print(f"Starting mostbet instance {instance_id}")
    try:
        process = subprocess.run(['python', 'mostbet.py'], 
                               capture_output=True, 
                               text=True,
                               check=True)
        print(f"Mostbet instance {instance_id} completed successfully")
        return f"mostbet_{instance_id}", True, process.stdout
    except subprocess.CalledProcessError as e:
        print(f"Mostbet instance {instance_id} failed: {e}")
        return f"mostbet_{instance_id}", False, e.stderr

def run_sequential_script(script_name):
    """Run a script sequentially"""
    print(f"\nRunning {script_name}...")
    try:
        process = subprocess.run(['python', script_name], 
                               capture_output=True, 
                               text=True,
                               check=True)
        print(f"{script_name} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"{script_name} failed: {e}")
        print(f"Error output: {e.stderr}")
        return False

def main():
    print("Starting Arbitrage Automation...")
    
    # Step 1: Run melbet.py and mostbet.py in parallel (50 instances each)
    print("\n=== Step 1: Running melbet.py and mostbet.py in parallel ===")
    
    with ThreadPoolExecutor(max_workers=100) as executor:  # 50 melbet + 50 mostbet
        futures = []
        
        # Submit 50 melbet instances
        for i in range(50):
            future = executor.submit(run_melbet_instance, i+1)
            futures.append(future)
        
        # Submit 50 mostbet instances
        for i in range(50):
            future = executor.submit(run_mostbet_instance, i+1)
            futures.append(future)
        
        # Wait for all to complete and collect results
        completed = 0
        failed = 0
        for future in as_completed(futures):
            name, success, output = future.result()
            completed += 1
            if not success:
                failed += 1
            print(f"Progress: {completed}/100 completed, {failed} failed")
    
    print(f"\nParallel execution completed. Total: {completed}, Failed: {failed}")
    
    # Step 2: Run remaining scripts sequentially
    print("\n=== Step 2: Running remaining scripts sequentially ===")
    
    sequential_scripts = [
        'match.py',
        'arbitrage_final.py',
        'Telegram_final.py'
    ]
    
    for script in sequential_scripts:
        success = run_sequential_script(script)
        if not success:
            print(f"Warning: {script} failed, but continuing with next script...")
            # You can choose to exit here if you want to stop on failure
            # return 1
    
    print("\n=== Arbitrage Automation Completed ===")
    return 0

if __name__ == "__main__":
    exit(main())