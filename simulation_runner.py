"""
Multi-Client Delay Simulation Runner

This script runs comprehensive simulations of the SCIoT system with:
- Multiple client configurations
- Various delay scenarios (computation and network)
- Automated server and client orchestration
- Per-inference result collection and analysis

Usage:
    python simulation_runner.py

Results are saved to: simulated_results/SCENARIO_TIMESTAMP/
  - Each folder contains inference_results.csv with one row per inference
"""

import subprocess
import time
import json
import yaml
import csv
import sys
from pathlib import Path
from datetime import datetime
import threading
import signal
import os
import requests

# Configuration
SCRIPT_DIR = Path(__file__).resolve().parent
SERVER_DIR = SCRIPT_DIR / "src" / "server" / "edge"
CLIENT_DIR = SCRIPT_DIR / "server_client_light" / "client"
CLIENT_CONFIG_FILE = CLIENT_DIR / "http_config.yaml"
SERVER_SETTINGS_FILE = SCRIPT_DIR / "src" / "server" / "settings.yaml"
RESULTS_DIR = SCRIPT_DIR / "simulated_results"

# Ensure results directory exists
RESULTS_DIR.mkdir(exist_ok=True)

# Simulation parameters
SIMULATION_SCENARIOS = [
    # Scenario 1: No delays (baseline)
    {
        "name": "baseline",
        "computation_delay": {"enabled": False},
        "network_delay": {"enabled": False},
        "duration_seconds": 30,
        "num_clients": 1
    },
    
    # Scenario 2: Network delay only (gaussian 20ms ± 5ms)
    {
        "name": "network_delay_20ms",
        "computation_delay": {"enabled": False},
        "network_delay": {
            "enabled": True,
            "type": "gaussian",
            "mean": 0.020,
            "std_dev": 0.005
        },
        "duration_seconds": 30,
        "num_clients": 1
    },
    
    # Scenario 3: Network delay high (gaussian 50ms ± 10ms)
    {
        "name": "network_delay_50ms",
        "computation_delay": {"enabled": False},
        "network_delay": {
            "enabled": True,
            "type": "gaussian",
            "mean": 0.050,
            "std_dev": 0.010
        },
        "duration_seconds": 30,
        "num_clients": 1
    },
    
    # Scenario 4: Computation delay only (gaussian 2ms ± 0.5ms)
    {
        "name": "computation_delay_2ms",
        "computation_delay": {
            "enabled": True,
            "type": "gaussian",
            "mean": 0.002,
            "std_dev": 0.0005
        },
        "network_delay": {"enabled": False},
        "duration_seconds": 30,
        "num_clients": 1
    },
    
    # Scenario 5: Computation delay high (gaussian 5ms ± 1ms)
    {
        "name": "computation_delay_5ms",
        "computation_delay": {
            "enabled": True,
            "type": "gaussian",
            "mean": 0.005,
            "std_dev": 0.001
        },
        "network_delay": {"enabled": False},
        "duration_seconds": 30,
        "num_clients": 1
    },
    
    # Scenario 6: Both delays (realistic mobile)
    {
        "name": "mobile_realistic",
        "computation_delay": {
            "enabled": True,
            "type": "gaussian",
            "mean": 0.003,
            "std_dev": 0.001
        },
        "network_delay": {
            "enabled": True,
            "type": "gaussian",
            "mean": 0.030,
            "std_dev": 0.010
        },
        "duration_seconds": 30,
        "num_clients": 1
    },
    
    # Scenario 7: High variance (unstable network)
    {
        "name": "unstable_network",
        "computation_delay": {"enabled": False},
        "network_delay": {
            "enabled": True,
            "type": "gaussian",
            "mean": 0.040,
            "std_dev": 0.020  # High variance
        },
        "duration_seconds": 30,
        "num_clients": 1
    },
    
    # Scenario 8: Multiple clients (no delay)
    {
        "name": "multi_client_baseline",
        "computation_delay": {"enabled": False},
        "network_delay": {"enabled": False},
        "duration_seconds": 30,
        "num_clients": 3
    },
    
    # Scenario 9: Multiple clients with network delay
    {
        "name": "multi_client_network",
        "computation_delay": {"enabled": False},
        "network_delay": {
            "enabled": True,
            "type": "gaussian",
            "mean": 0.025,
            "std_dev": 0.008
        },
        "duration_seconds": 30,
        "num_clients": 3
    },
]


class SimulationRunner:
    def __init__(self):
        self.server_process = None
        self.client_processes = []
        self.server_host = "0.0.0.0"
        self.server_port = 8000
        self.current_results_folder = None  # Main folder for all scenarios
        self.current_scenario_dir = None
        self.inference_count = 0
        self.csv_file = None
        self.csv_writer = None
        
    def backup_config(self, filepath):
        """Backup a configuration file"""
        backup_path = f"{filepath}.backup"
        if Path(filepath).exists():
            with open(filepath, 'r') as f:
                content = f.read()
            with open(backup_path, 'w') as f:
                f.write(content)
        return backup_path
    
    def restore_config(self, filepath, backup_path):
        """Restore a configuration file from backup"""
        if Path(backup_path).exists():
            with open(backup_path, 'r') as f:
                content = f.read()
            with open(filepath, 'w') as f:
                f.write(content)
            os.remove(backup_path)
    
    def update_client_config(self, scenario, client_index=0):
        """Update client configuration for scenario"""
        with open(CLIENT_CONFIG_FILE, 'r') as f:
            config = yaml.safe_load(f)
        
        # Set client ID (null for first, fixed for others)
        if client_index == 0:
            config['client']['client_id'] = None  # Auto-generate
        else:
            config['client']['client_id'] = f"sim_client_{client_index}"
        
        # Update delay simulation
        config['delay_simulation'] = {
            'computation': scenario['computation_delay'],
            'network': scenario['network_delay']
        }
        
        with open(CLIENT_CONFIG_FILE, 'w') as f:
            yaml.dump(config, f, default_flow_style=False)
    
    def update_server_config(self, scenario):
        """Update server configuration for scenario"""
        with open(SERVER_SETTINGS_FILE, 'r') as f:
            config = yaml.safe_load(f)
        
        # Disable server-side delays for cleaner client measurements
        if 'delay_simulation' not in config:
            config['delay_simulation'] = {}
        
        config['delay_simulation']['computation'] = {'enabled': False}
        config['delay_simulation']['network'] = {'enabled': False}
        
        with open(SERVER_SETTINGS_FILE, 'w') as f:
            yaml.dump(config, f, default_flow_style=False)
    
    def start_server(self):
        """Start the edge server"""
        print("\n🚀 Starting server...")
        server_script = SERVER_DIR / "run_edge.py"
        
        self.server_process = subprocess.Popen(
            [sys.executable, str(server_script)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            cwd=str(SCRIPT_DIR)
        )
        
        # Start thread to monitor server output
        self.server_monitor_thread = threading.Thread(target=self._monitor_server_output, daemon=True)
        self.server_monitor_thread.start()
        
        # Wait for server to be ready
        max_wait = 15
        for i in range(max_wait):
            try:
                response = requests.get(f"http://{self.server_host}:{self.server_port}/docs", timeout=1)
                if response.status_code == 200:
                    print(f"✓ Server ready after {i+1} seconds")
                    return True
            except:
                time.sleep(1)
        
        print("⚠ Server may not be ready, proceeding anyway")
        return False
    
    def stop_server(self):
        """Stop the edge server"""
        if self.server_process:
            print("\n🛑 Stopping server...")
            self.server_process.terminate()
            try:
                self.server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.server_process.kill()
            self.server_process = None
    
    def _monitor_server_output(self):
        """Monitor server output for inference events"""
        if not self.server_process:
            return
        
        for line in self.server_process.stdout:
            # Look for inference completion patterns
            # Adjust these patterns based on actual server output
            if "inference" in line.lower() or "layer" in line.lower():
                # Try to extract inference data from logs
                self._try_capture_inference_event(line)
    
    def _try_capture_inference_event(self, log_line):
        """Try to capture inference event from log line"""
        # This is called when we detect potential inference activity
        # We'll also check files for more reliable data
        pass
    
    def _check_and_record_new_inferences(self):
        """Check server data files and record any new inferences"""
        try:
            # Read current device inference times
            device_file = SCRIPT_DIR / "src" / "server" / "device_inference_times.json"
            edge_file = SCRIPT_DIR / "src" / "server" / "edge_inference_times.json"
            
            if device_file.exists() and edge_file.exists():
                with open(device_file, 'r') as f:
                    device_times = json.load(f)
                with open(edge_file, 'r') as f:
                    edge_times = json.load(f)
                
                # Record inference data
                self._record_inference(device_times, edge_times)
        except Exception as e:
            pass  # Silently ignore errors during monitoring
    
    def _record_inference(self, device_times, edge_times):
        """Record a single inference to CSV"""
        if not self.csv_writer:
            return
        
        self.inference_count += 1
        
        # Calculate statistics
        device_values = [v for k, v in device_times.items() if k.startswith('layer_') and isinstance(v, (int, float))]
        edge_values = [v for k, v in edge_times.items() if k.startswith('layer_') and isinstance(v, (int, float))]
        
        row = {
            'inference_id': self.inference_count,
            'timestamp': datetime.now().isoformat(),
            'avg_device_time': sum(device_values) / len(device_values) if device_values else 0,
            'min_device_time': min(device_values) if device_values else 0,
            'max_device_time': max(device_values) if device_values else 0,
            'avg_edge_time': sum(edge_values) / len(edge_values) if edge_values else 0,
            'min_edge_time': min(edge_values) if edge_values else 0,
            'max_edge_time': max(edge_values) if edge_values else 0,
            'num_device_layers': len(device_values),
            'num_edge_layers': len(edge_values),
        }
        
        self.csv_writer.writerow(row)
        self.csv_file.flush()  # Ensure data is written immediately
    
    def start_client(self, client_index=0):
        """Start a client and monitor its output"""
        print(f"  Starting client {client_index}...")
        client_script = CLIENT_DIR / "http_client.py"
        
        process = subprocess.Popen(
            [sys.executable, str(client_script)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            cwd=str(CLIENT_DIR)
        )
        
        # Start monitoring thread
        monitor_thread = threading.Thread(
            target=self._monitor_client_output,
            args=(process, client_index),
            daemon=True
        )
        monitor_thread.start()
        
        self.client_processes.append(process)
        return process
    
    def _monitor_client_output(self, process, client_index):
        """Monitor client output for inference completion"""
        for line in process.stdout:
            if "Inference complete" in line or "✓" in line:
                # Inference completed, check and record
                self._check_and_record_new_inferences()
    
    def stop_clients(self):
        """Stop all client processes"""
        print("\n🛑 Stopping clients...")
        for process in self.client_processes:
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
        self.client_processes = []
    
    def create_scenario_folder(self, scenario):
        """Create CSV file for scenario results in main results folder"""
        self.inference_count = 0
        
        # Create CSV file with scenario name prefix in main folder
        csv_filename = f"{scenario['name']}_inference_results.csv"
        csv_path = self.current_results_folder / csv_filename
        self.csv_file = open(csv_path, 'w', newline='')
        
        fieldnames = [
            'inference_id',
            'timestamp',
            'avg_device_time',
            'min_device_time',
            'max_device_time',
            'avg_edge_time',
            'min_edge_time',
            'max_edge_time',
            'num_device_layers',
            'num_edge_layers',
        ]
        
        self.csv_writer = csv.DictWriter(self.csv_file, fieldnames=fieldnames)
        self.csv_writer.writeheader()
        self.csv_file.flush()
        
        # Save scenario configuration in main folder
        config_filename = f"{scenario['name']}_scenario_config.json"
        config_path = self.current_results_folder / config_filename
        with open(config_path, 'w') as f:
            json.dump(scenario, f, indent=2)
        
        print(f"\n📝 Recording {scenario['name']} results to: {csv_filename}")
    
    def close_scenario_folder(self):
        """Close current scenario CSV file"""
        if self.csv_file:
            self.csv_file.close()
            self.csv_file = None
            self.csv_writer = None
        self.current_scenario_dir = None
    
    
    def collect_server_statistics(self):
        """Collect statistics from server data files"""
        stats = {
            'device_inference_times': {},
            'edge_inference_times': {},
        }
        
        # Read device inference times
        device_file = SCRIPT_DIR / "src" / "server" / "device_inference_times.json"
        if device_file.exists():
            with open(device_file, 'r') as f:
                stats['device_inference_times'] = json.load(f)
        
        # Read edge inference times
        edge_file = SCRIPT_DIR / "src" / "server" / "edge_inference_times.json"
        if edge_file.exists():
            with open(edge_file, 'r') as f:
                stats['edge_inference_times'] = json.load(f)
        
        return stats
    
    def run_scenario(self, scenario):
        """Run a single simulation scenario"""
        print("\n" + "="*80)
        print(f"📊 Running scenario: {scenario['name']}")
        print(f"   Computation delay: {scenario['computation_delay']}")
        print(f"   Network delay: {scenario['network_delay']}")
        print(f"   Duration: {scenario['duration_seconds']}s")
        print(f"   Clients: {scenario['num_clients']}")
        print("="*80)
        
        # Backup configurations
        client_backup = self.backup_config(CLIENT_CONFIG_FILE)
        server_backup = self.backup_config(SERVER_SETTINGS_FILE)
        
        try:
            # Create folder for this scenario
            self.create_scenario_folder(scenario)
            
            # Update configurations
            self.update_server_config(scenario)
            
            # Start server
            self.start_server()
            time.sleep(3)  # Extra time for server initialization
            
            # Start clients
            for i in range(scenario['num_clients']):
                self.update_client_config(scenario, i)
                time.sleep(0.5)  # Small delay between client starts
                self.start_client(i)
            
            # Monitor and record inferences during simulation
            print(f"\n⏳ Running for {scenario['duration_seconds']} seconds...")
            start_time = time.time()
            while time.time() - start_time < scenario['duration_seconds']:
                time.sleep(2)  # Check every 2 seconds
                self._check_and_record_new_inferences()
            
            # Stop clients
            self.stop_clients()
            time.sleep(2)
            
            # Final check for any remaining inferences
            self._check_and_record_new_inferences()
            
            print(f"\n✓ Scenario '{scenario['name']}' completed with {self.inference_count} inferences")
            
            # Stop server
            self.stop_server()
            time.sleep(3)  # Wait for cleanup
            
        except Exception as e:
            print(f"\n❌ Error in scenario '{scenario['name']}': {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            # Close scenario folder
            self.close_scenario_folder()
            
            # Cleanup
            self.stop_clients()
            self.stop_server()
            
            # Restore configurations
            self.restore_config(CLIENT_CONFIG_FILE, client_backup)
            self.restore_config(SERVER_SETTINGS_FILE, server_backup)
    
    def run_all_scenarios(self):
        """Run all simulation scenarios"""
        # Create main results folder with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.current_results_folder = RESULTS_DIR / f"simulation_{timestamp}"
        self.current_results_folder.mkdir(parents=True, exist_ok=True)
        
        print("\n" + "="*80)
        print("🔬 SCIoT Multi-Client Delay Simulation")
        print("="*80)
        print(f"Total scenarios: {len(SIMULATION_SCENARIOS)}")
        print(f"Results folder: {self.current_results_folder}")
        
        for i, scenario in enumerate(SIMULATION_SCENARIOS, 1):
            print(f"\n\n[{i}/{len(SIMULATION_SCENARIOS)}]")
            self.run_scenario(scenario)
        
        # Print summary
        print("\n" + "="*80)
        print("✅ All simulations completed!")
        print("="*80)
        print(f"\nResults saved to: {self.current_results_folder}")
        print("="*80)


def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    print("\n\n🛑 Simulation interrupted by user")
    sys.exit(0)


def main():
    # Setup signal handler
    signal.signal(signal.SIGINT, signal_handler)
    
    # Run simulations
    runner = SimulationRunner()
    try:
        runner.run_all_scenarios()
    except KeyboardInterrupt:
        print("\n\n🛑 Simulation interrupted")
    finally:
        # Cleanup
        runner.stop_clients()
        runner.stop_server()


if __name__ == "__main__":
    main()
