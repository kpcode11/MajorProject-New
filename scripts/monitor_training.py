"""Monitor mouse training progress by checking the state file."""

import json
import time
from pathlib import Path

state_file = Path("data/processed/mouse_features/_state.json")
target_sessions = 500

print("=" * 70)
print("MONITORING MOUSE FEATURE EXTRACTION PROGRESS")
print("=" * 70)
print(f"Target: {target_sessions} sessions")
print(f"Monitoring: {state_file}")
print()

last_count = 0
start_time = time.time()

while True:
    try:
        if state_file.exists():
            data = json.loads(state_file.read_text())
            completed = data.get("completed", {})
            total_sessions = len([k for k in completed.keys() if not k.endswith("_state.json")])
            total_windows = sum(v.get("windows", 0) for v in completed.values())
            
            if total_sessions != last_count:
                elapsed = time.time() - start_time
                percent = (total_sessions / target_sessions) * 100
                rate = total_sessions / elapsed if elapsed > 0 else 0
                eta = (target_sessions - total_sessions) / rate if rate > 0 else 0
                
                print(f"[{percent:5.1f}%] Sessions: {total_sessions:3d}/{target_sessions} | "
                      f"Windows: {total_windows:5d} | "
                      f"Rate: {rate:.1f} sess/sec | "
                      f"ETA: {eta/60:.1f} min")
                
                last_count = total_sessions
                
                if total_sessions >= target_sessions:
                    print()
                    print("=" * 70)
                    print("FEATURE EXTRACTION COMPLETE!")
                    print(f"Total time: {elapsed/60:.1f} minutes")
                    print(f"Total windows extracted: {total_windows}")
                    print("=" * 70)
                    break
        
        time.sleep(10)
        
    except KeyboardInterrupt:
        print("\nMonitoring stopped by user.")
        break
    except Exception as e:
        print(f"Error: {e}")
        time.sleep(10)
