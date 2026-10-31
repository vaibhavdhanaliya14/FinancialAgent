"""
Evaluation Workflow for Buy or Wait? AI Financial Agent
HackerRank Orchestrate (September 2026)
"""

import os
import sys
import csv
import math

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(current_dir, '..'))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from simulator import FinancialAgent

def evaluate_sample_benchmark(dataset_dir='dataset'):
    print("="*60)
    print("Running Evaluation Benchmark on Solved Samples...")
    print("="*60)
    
    agent = FinancialAgent(dataset_dir=dataset_dir)
    samples_path = os.path.join(dataset_dir, 'sample_requests.csv')
    
    with open(samples_path, 'r', encoding='utf-8') as f:
        samples = list(csv.DictReader(f))
        
    total = len(samples)
    status_correct = 0
    method_correct = 0
    earliest_correct = 0
    plan_correct = 0
    spending_correct = 0
    safe_pay_diffs = []

    for s in samples:
        pred = agent.evaluate_request(s)
        
        # 1. Status
        if pred['affordability_status'] == s['affordability_status']:
            status_correct += 1
            
        # 2. Method
        if pred['recommended_payment_method'] == s['recommended_payment_method']:
            method_correct += 1
            
        # 3. Earliest Date
        if pred['earliest_date_for_full_payment'] == s['earliest_date_for_full_payment']:
            earliest_correct += 1
            
        # 4. Plan
        if pred['payment_plan'] == s['payment_plan']:
            plan_correct += 1
            
        # 5. Spending changes
        if pred['spending_changes_needed'] == s['spending_changes_needed']:
            spending_correct += 1
            
        # 6. Safe to pay error
        exp_safe = float(s['amount_safe_to_pay'])
        pred_safe = float(pred['amount_safe_to_pay'])
        safe_pay_diffs.append(abs(exp_safe - pred_safe))

    mae_safe_pay = sum(safe_pay_diffs) / total
    
    print(f"Total Evaluated Samples       : {total}")
    print(f"Affordability Status Accuracy : {status_correct}/{total} ({status_correct/total*100:.1f}%)")
    print(f"Payment Method Accuracy       : {method_correct}/{total} ({method_correct/total*100:.1f}%)")
    print(f"Payment Plan Exact Match Rate : {plan_correct}/{total} ({plan_correct/total*100:.1f}%)")
    print(f"Earliest Full Date Accuracy   : {earliest_correct}/{total} ({earliest_correct/total*100:.1f}%)")
    print(f"Spending Changes Accuracy     : {spending_correct}/{total} ({spending_correct/total*100:.1f}%)")
    print(f"Mean Safe Amount Diff (MAE)   : {mae_safe_pay:.2f}")
    print("="*60)

def verify_output_csv(output_csv='output.csv', requests_csv='dataset/requests.csv'):
    print(f"\nVerifying schema and integrity of: {output_csv}")
    if not os.path.exists(output_csv):
        print(f"ERROR: {output_csv} does not exist!")
        return False

    with open(requests_csv, 'r', encoding='utf-8') as f:
        req_rows = list(csv.DictReader(f))
    req_ids = [r['request_id'] for r in req_rows]
    req_lookup = {r['request_id']: r for r in req_rows}

    with open(output_csv, 'r', encoding='utf-8') as f:
        out_rows = list(csv.DictReader(f))

    required_cols = [
        'request_id',
        'amount_safe_to_pay',
        'affordability_status',
        'recommended_payment_method',
        'payment_plan',
        'earliest_date_for_full_payment',
        'spending_changes_needed',
        'decision_explanation'
    ]

    # Check header
    if out_rows:
        cols = list(out_rows[0].keys())
        if cols != required_cols:
            print(f"ERROR: Columns mismatch!\nExpected: {required_cols}\nFound: {cols}")
            return False

    # Check row count
    if len(out_rows) != len(req_ids):
        print(f"ERROR: Row count mismatch! Expected {len(req_ids)}, found {len(out_rows)}")
        return False

    # Check values and constraints
    for i, r in enumerate(out_rows):
        rid = r['request_id']
        if rid != req_ids[i]:
            print(f"ERROR: Row order mismatch at row {i+1}: expected {req_ids[i]}, got {rid}")
            return False

        orig = req_lookup[rid]
        req_amt = float(orig['requested_amount'])
        safe_amt = float(r['amount_safe_to_pay'])

        # 0 <= amount_safe_to_pay <= requested_amount
        if not (0 <= safe_amt <= req_amt):
            print(f"ERROR: Row {rid} has invalid amount_safe_to_pay: {safe_amt} (requested: {req_amt})")
            return False

        # Status allowed values
        if r['affordability_status'] not in ('affordable_now', 'affordable_with_plan', 'affordable_later', 'not_affordable'):
            print(f"ERROR: Row {rid} has invalid affordability_status: {r['affordability_status']}")
            return False

        # Method allowed values
        if r['recommended_payment_method'] not in ('full_payment', 'partial_payment', 'installments', 'wait', 'not_recommended'):
            print(f"ERROR: Row {rid} has invalid recommended_payment_method: {r['recommended_payment_method']}")
            return False

        # For affordable_now, earliest_date_for_full_payment must equal request_date
        if r['affordability_status'] == 'affordable_now':
            if r['earliest_date_for_full_payment'] != orig['request_date']:
                print(f"ERROR: Row {rid} affordable_now requires earliest_date == request_date")
                return False

    print("All output schema, row count, and bounds checks PASSED successfully!")
    return True

if __name__ == '__main__':
    evaluate_sample_benchmark()
    if os.path.exists('output.csv'):
        verify_output_csv('output.csv')

