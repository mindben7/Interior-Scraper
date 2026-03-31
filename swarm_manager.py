import os
import sys
import time

def main():
    print("========================================")
    print("   LIGHT COLLIDER SWARM ORCHESTRATOR    ")
    print("========================================\n")
    
    if len(sys.argv) > 1:
        try:
            n_agents = int(sys.argv[1])
        except ValueError:
            print("[-] Invalid number. Exiting.")
            sys.exit(1)
    else:
        try:
            n_agents = int(input("[?] How many concurrent swarm agents do you want to devote? (Recommended 2-5): "))
        except ValueError:
            print("[-] Invalid number. Exiting.")
            sys.exit(1)
            
    if n_agents < 1 or n_agents > 10:
        print("[-] Please select between 1 and 10 agents.")
        sys.exit(1)
        
    print("[*] Terminating any existing crawler processes...")
    os.system("pkill -f 'agent.py --modes'")
    time.sleep(1)
    
    modes = "wide,detail,lighting,mood,preset-contemporary"
    print(f"\n[*] Spinning up {n_agents} completely isolated Swarm Agents...")
    
    workspace = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(workspace, "data")
    os.makedirs(data_dir, exist_ok=True)
    
    for i in range(n_agents):
        log_file = os.path.join(data_dir, "agent.log") if i == 0 else os.path.join(data_dir, f"swarm_agent_{i}.log")
        cmd = f"cd '{workspace}' && nohup venv/bin/python -u agent.py --modes '{modes}' --chunk-index {i} --chunk-total {n_agents} >> '{log_file}' 2>&1 &"
        os.system(cmd)
        print(f"    [+] Agent {i}/{n_agents} launched. Logs -> data/swarm_agent_{i}.log")
        time.sleep(2) # Stagger playwright chromium init
        
    print("\n[+] Swarm successfully deployed to the background.")
    print(f"[+] To monitor node 0 : tail -f data/swarm_agent_0.log")

if __name__ == "__main__":
    main()
