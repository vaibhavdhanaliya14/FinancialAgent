"""
Main Entry Point for Buy or Wait? AI Financial Decision Agent
HackerRank Orchestrate (September 2026)
"""

import os
import sys
import csv
from datetime import datetime

# Ensure code directory is on path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from simulator import FinancialAgent, format_amount

def run_agent(input_csv='dataset/requests.csv', output_csv='output.csv'):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Initializing Financial Decision Agent...")
    agent = FinancialAgent(dataset_dir='dataset')
    
    print(f"Reading evaluation requests from: {input_csv}")
    with open(input_csv, 'r', encoding='utf-8') as f:
        requests = list(csv.DictReader(f))
    
    total_requests = len(requests)
    print(f"Processing {total_requests} requests...")
    
    results = []
    status_counts = {}
    method_counts = {}

    for idx, req in enumerate(requests, 1):
        decision = agent.evaluate_request(req)
        results.append(decision)
        
        status = decision['affordability_status']
        method = decision['recommended_payment_method']
        status_counts[status] = status_counts.get(status, 0) + 1
        method_counts[method] = method_counts.get(method, 0) + 1
        
        if idx % 50 == 0 or idx == total_requests:
            print(f"  Processed {idx}/{total_requests} requests ({(idx/total_requests)*100:.1f}%)")

    # Output CSV columns contract
    output_headers = [
        'request_id',
        'amount_safe_to_pay',
        'affordability_status',
        'recommended_payment_method',
        'payment_plan',
        'earliest_date_for_full_payment',
        'spending_changes_needed',
        'decision_explanation'
    ]
    
    print(f"Writing predictions to: {output_csv}")
    with open(output_csv, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=output_headers)
        writer.writeheader()
        for r in results:
            writer.writerow(r)
            
    print("\n" + "="*50)
    print("Execution Summary:")
    print(f"Total Requests Predicted: {len(results)}")
    print("\nAffordability Status Distribution:")
    for st, cnt in sorted(status_counts.items()):
        print(f"  {st:<25}: {cnt:>4} ({cnt/total_requests*100:.1f}%)")
    print("\nPayment Method Distribution:")
    for mt, cnt in sorted(method_counts.items()):
        print(f"  {mt:<25}: {cnt:>4} ({cnt/total_requests*100:.1f}%)")
    print("="*50)
    print(f"Successfully generated {output_csv} with {len(results)} rows.")

if __name__ == '__main__':
    run_agent()

