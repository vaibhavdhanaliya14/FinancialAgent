"""
Complete Production Financial Simulation & Decision Engine
HackerRank Orchestrate: 'Buy or Wait?'
"""

import csv
import os
import re
import math
from datetime import datetime, timedelta
from collections import defaultdict

def parse_date(d_str):
    if not d_str:
        return None
    try:
        return datetime.strptime(d_str.strip(), '%Y-%m-%d').date()
    except Exception:
        return None

def format_date(d):
    if isinstance(d, str):
        return d
    return d.strftime('%Y-%m-%d')

def format_date_human(d_str):
    d = parse_date(d_str)
    if not d:
        return d_str
    # e.g. 8 August 2025
    return f"{d.day} {d.strftime('%B %Y')}"

def format_amount(val):
    if val is None or val == '':
        return ''
    f = float(val)
    if f.is_integer():
        return f"{int(f)}"
    # Round to 2 decimal places
    s = f"{f:.2f}"
    return s.rstrip('0').rstrip('.') if s.endswith('.00') else s

def format_amount_with_commas(val):
    if val is None or val == '':
        return ''
    f = float(val)
    if f.is_integer():
        return f"{int(f):,}"
    return f"{f:,.2f}"

class FinancialAgent:
    def __init__(self, dataset_dir='dataset'):
        self.dataset_dir = dataset_dir
        self.load_data()

    def load_data(self):
        # 1. Profiles
        self.profiles = {}
        with open(os.path.join(self.dataset_dir, 'financial_profiles.csv'), 'r', encoding='utf-8') as f:
            for r in csv.DictReader(f):
                self.profiles[r['user_id']] = r

        # 2. Exchange rates
        self.exchange_rates = {}
        with open(os.path.join(self.dataset_dir, 'exchange_rates.csv'), 'r', encoding='utf-8') as f:
            for r in csv.DictReader(f):
                self.exchange_rates[(r['rate_date'], r['from_currency'], r['to_currency'])] = float(r['rate'])

        # 3. Known / extracted image amounts
        self.image_amounts = {
            'event_253': 4365000.0,
            'event_1442': 100000.0,
            'event_1545': 41272.0,
            'event_1700': 2854.0,
            'event_1786': 704.05,
            'event_3051': 1995.0,
            'event_3231': 8528.0,
            'event_4535': 15339.0,
            'event_5170': 723.0,
            'event_6033': 79679.26,
            'event_6859': 3650.0,
            'event_7307': 33.50,
            'event_7941': 2298.0,
            'event_9421': 4543.0,
            'event_9806': 9968.0,
            'event_10521': 393.22,
        }

        # 4. Financial Events
        self.events_by_user = defaultdict(list)
        self.all_events = {}
        with open(os.path.join(self.dataset_dir, 'financial_events.csv'), 'r', encoding='utf-8') as f:
            for r in csv.DictReader(f):
                if not r['amount'] and r['event_id'] in self.image_amounts:
                    r['amount'] = str(self.image_amounts[r['event_id']])
                self.events_by_user[r['user_id']].append(r)
                self.all_events[r['event_id']] = r

        # 5. Payment Options
        self.options_by_request = defaultdict(list)
        with open(os.path.join(self.dataset_dir, 'request_payment_options.csv'), 'r', encoding='utf-8') as f:
            for r in csv.DictReader(f):
                self.options_by_request[r['request_id']].append(r)

        # 6. Messages
        self.messages_by_user = defaultdict(list)
        with open(os.path.join(self.dataset_dir, 'messages.csv'), 'r', encoding='utf-8') as f:
            for r in csv.DictReader(f):
                self.messages_by_user[r['user_id']].append(r)

    def convert_currency(self, amount, from_curr, to_curr, date_str):
        if from_curr == to_curr or amount == 0:
            return amount
        key = (date_str, from_curr, to_curr)
        if key in self.exchange_rates:
            return amount * self.exchange_rates[key]
        rev_key = (date_str, to_curr, from_curr)
        if rev_key in self.exchange_rates:
            return amount / self.exchange_rates[rev_key]
        return amount

    def get_user_messages(self, user_id, req_date_str):
        user_msgs = self.messages_by_user.get(user_id, [])
        valid_msgs = []
        for m in user_msgs:
            sent_at = m['sent_at'].split('T')[0]
            if sent_at <= req_date_str:
                valid_msgs.append(m)
        return valid_msgs

    def parse_message_overrides(self, user_id, req_date_str):
        msgs = self.get_user_messages(user_id, req_date_str)
        overrides = {
            'salary_amount': None,
            'salary_day': None,
            'salary_effective_date': None,
            'gig_payout_blocked': False,
            'rent_multiplier': 1.0,
            'ignore_events': set()
        }

        for m in msgs:
            text = m['message_text']
            src = m['source_type']
            rel_evt = m['related_event_id']

            if rel_evt:
                t_lower = text.lower()
                if any(w in t_lower for w in ('cancelled', 'not reached', 'still in payment processing', 'pending', 'unrealized')):
                    overrides['ignore_events'].add(rel_evt)

            if 'quickcrew' in text.lower() or 'payout is still pending' in text.lower():
                overrides['gig_payout_blocked'] = True

            if src == 'employer':
                t_lower = text.lower()
                date_match = re.search(r'\b(20\d\d-\d\d-(\d\d))\b', text)
                if 'expected on' in t_lower or 'terjadwal' in t_lower or 'payroll date' in t_lower:
                    if date_match:
                        overrides['salary_day'] = int(date_match.group(2))
                        overrides['salary_effective_date'] = date_match.group(1)

                amt_match = re.search(r'(?:IDR|EUR|USD|ZAR|INR)\s*([\d,]+(?:\.\d+)?)', text)
                if amt_match and any(w in t_lower for w in ('gaji', 'salary', 'pay')):
                    amt_str = amt_match.group(1).replace(',', '').rstrip('.')
                    try:
                        amt_val = float(amt_str)
                        overrides['salary_amount'] = amt_val
                        if date_match and not overrides['salary_effective_date']:
                            overrides['salary_effective_date'] = date_match.group(1)
                    except ValueError:
                        pass

            elif src == 'service_provider':
                pct_match = re.search(r'increases monthly rent by (\d+)%', text)
                if pct_match:
                    pct = float(pct_match.group(1))
                    overrides['rent_multiplier'] = 1.0 + (pct / 100.0)

        return overrides

    def get_salary_profile(self, user_id, req_date_str):
        u_events = self.events_by_user.get(user_id, [])
        sals = [e for e in u_events if e['category'] == 'salary' and e['amount']]
        sals.sort(key=lambda x: x['event_date'])

        overrides = self.parse_message_overrides(user_id, req_date_str)
        if overrides['gig_payout_blocked']:
            return None

        if not sals:
            return None

        # Check if final payroll
        for s in sals:
            if 'final employer payroll' in s.get('description', '').lower():
                return None

        dates = [parse_date(s['event_date']) for s in sals]
        days = [d.day for d in dates]

        from collections import Counter
        day_counts = Counter(days)
        mode_day = day_counts.most_common(1)[0][0]

        if overrides['salary_day']:
            salary_day = overrides['salary_day']
        else:
            salary_day = mode_day

        latest_sal = sals[-1]
        base_amt = float(latest_sal['amount'])
        if overrides['salary_amount']:
            eff_dt = overrides['salary_effective_date'] or req_date_str
            final_amt = overrides['salary_amount']
        else:
            final_amt = base_amt
            eff_dt = req_date_str

        return {
            'day': salary_day,
            'amount': final_amt,
            'currency': latest_sal['currency'],
            'effective_date': eff_dt
        }

    def analyze_user_recurrence(self, user_id, req_date_str):
        profile = self.profiles[user_id]
        home_curr = profile['home_currency']
        u_events = self.events_by_user.get(user_id, [])
        
        # Settled events before request date
        settled = [e for e in u_events if e['status'] == 'settled' and e['event_date'] <= req_date_str and e['amount']]
        settled.sort(key=lambda x: x['event_date'])

        by_cat = defaultdict(list)
        for e in settled:
            by_cat[e['category']].append(e)

        recurring_series = []
        for cat, evts in by_cat.items():
            if cat in ('salary', 'refund', 'investment_purchase', 'investment_valuation', 'investment_sale'):
                continue

            if len(evts) >= 2:
                dates = [parse_date(e['event_date']) for e in evts]
                dates.sort()
                diffs = [(dates[i+1] - dates[i]).days for i in range(len(dates)-1)]
                avg_diff = sum(diffs) / len(diffs)

                period = None
                if 27 <= avg_diff <= 33:
                    period = 'monthly'
                elif 6 <= avg_diff <= 8:
                    period = 'weekly'
                elif 9 <= avg_diff <= 11:
                    period = '10days'
                elif 13 <= avg_diff <= 15:
                    period = '14days'
                elif 20 <= avg_diff <= 22:
                    period = '21days'

                if period:
                    amts = [float(e['amount']) for e in evts]
                    latest_evt = evts[-1]
                    min_amt = float(latest_evt['minimum_allowed_amount']) if latest_evt.get('minimum_allowed_amount') else None

                    # If fixed/essential commitment, use latest amount
                    if cat in ('rent', 'housing', 'education', 'debt_repayment', 'insurance') or cat.endswith('subscription') or cat.endswith('membership') or cat in ('gym', 'cloud_storage', 'streaming'):
                        rep_amount = amts[-1]
                    else:
                        # Exclude outliers (e.g. bulk purchases > 2x median)
                        sorted_amts = sorted(amts)
                        med = sorted_amts[len(sorted_amts) // 2]
                        normal_amts = [a for a in amts if a <= 2.0 * med]
                        if normal_amts:
                            rep_amount = sum(normal_amts[-4:]) / len(normal_amts[-4:])
                        else:
                            rep_amount = med

                    recurring_series.append({
                        'category': cat,
                        'period': period,
                        'direction': evts[-1]['direction'],
                        'amount': rep_amount,
                        'currency': evts[-1]['currency'],
                        'last_date': dates[-1],
                        'flexibility': latest_evt['flexibility'],
                        'latest_event_id': latest_evt['event_id'],
                        'minimum_allowed_amount': min_amt,
                        'description': latest_evt['description']
                    })

        return recurring_series

    def build_timeline(self, user_id, req_date_str, spending_changes=None):
        profile = self.profiles[user_id]
        home_curr = profile['home_currency']
        req_date = parse_date(req_date_str)
        end_date = req_date + timedelta(days=90)

        daily_flows = defaultdict(float)

        stopped_events = set()
        reduced_events = {}
        if spending_changes and spending_changes != 'none':
            for sc in spending_changes.split('|'):
                parts = sc.split(':')
                if parts[0] == 'stop':
                    stopped_events.add(parts[1])
                elif parts[0] == 'reduce_to':
                    reduced_events[parts[1]] = float(parts[2])

        overrides = self.parse_message_overrides(user_id, req_date_str)

        # 1. Existing scheduled/pending events in database
        u_events = self.events_by_user.get(user_id, [])
        existing_salary_dates = set()
        for e in u_events:
            if e['event_id'] in overrides['ignore_events']:
                continue
            set_dt_str = e['settlement_date'] if e['settlement_date'] else e['event_date']
            set_dt = parse_date(set_dt_str)
            if not set_dt or set_dt < req_date or set_dt > end_date:
                continue

            status = e['status']
            direction = e['direction']
            amt = float(e['amount']) if e['amount'] else 0.0
            amt = self.convert_currency(amt, e['currency'], home_curr, set_dt_str)

            if direction == 'debit' and status in ('pending', 'scheduled'):
                if e['category'] in ('rent', 'housing') and overrides['rent_multiplier'] != 1.0:
                    amt *= overrides['rent_multiplier']
                daily_flows[set_dt] -= amt

            elif direction == 'credit' and status in ('settled', 'scheduled') and e['category'] == 'salary':
                if not overrides['gig_payout_blocked']:
                    daily_flows[set_dt] += amt
                    existing_salary_dates.add(set_dt)

        # 2. Project Confirmed Monthly Salary
        sal_profile = self.get_salary_profile(user_id, req_date_str)
        if sal_profile:
            sal_day = sal_profile['day']
            sal_amt = sal_profile['amount']
            sal_curr = sal_profile['currency']
            
            curr = req_date
            while curr <= end_date:
                m = curr.month
                y = curr.year
                max_d = 28 if m == 2 else 30 if m in (4,6,9,11) else 31
                actual_d = min(sal_day, max_d)
                s_date = datetime(y, m, actual_d).date()

                if req_date <= s_date <= end_date:
                    if s_date not in existing_salary_dates:
                        s_amt_home = self.convert_currency(sal_amt, sal_curr, home_curr, format_date(s_date))
                        daily_flows[s_date] += s_amt_home
                        existing_salary_dates.add(s_date)

                curr = datetime(y + (1 if m == 12 else 0), m % 12 + 1, 1).date()

        # 3. Project Recurring Expenses
        recurring = self.analyze_user_recurrence(user_id, req_date_str)
        for rec in recurring:
            cat = rec['category']
            evt_id = rec['latest_event_id']

            if evt_id in stopped_events:
                continue

            amt = rec['amount']
            if evt_id in reduced_events:
                amt = reduced_events[evt_id]

            if cat in ('rent', 'housing') and overrides['rent_multiplier'] != 1.0:
                amt *= overrides['rent_multiplier']

            direction = rec['direction']
            last_dt = rec['last_date']
            period = rec['period']

            curr_dt = last_dt
            while curr_dt <= end_date:
                if period == 'monthly':
                    m = curr_dt.month % 12 + 1
                    y = curr_dt.year + (1 if curr_dt.month == 12 else 0)
                    day = min(last_dt.day, 28 if m == 2 else 30 if m in (4,6,9,11) else 31)
                    curr_dt = datetime(y, m, day).date()
                elif period == 'weekly':
                    curr_dt += timedelta(days=7)
                elif period == '10days':
                    curr_dt += timedelta(days=10)
                elif period == '14days':
                    curr_dt += timedelta(days=14)
                elif period == '21days':
                    curr_dt += timedelta(days=21)

                if req_date <= curr_dt <= end_date:
                    amt_home = self.convert_currency(amt, rec['currency'], home_curr, format_date(curr_dt))
                    if direction == 'debit':
                        daily_flows[curr_dt] -= amt_home

        return daily_flows

    def simulate_trajectory(self, user_id, req_date_str, payment_schedule=None, spending_changes=None):
        profile = self.profiles[user_id]
        cur_bal = float(profile['current_available_balance'])
        min_bal = float(profile['minimum_balance_to_keep'])
        req_date = parse_date(req_date_str)
        end_date = req_date + timedelta(days=90)

        daily_flows = self.build_timeline(user_id, req_date_str, spending_changes)

        if payment_schedule and payment_schedule != 'none':
            for p in payment_schedule.split('|'):
                if not p: continue
                p_dt_str, p_amt_str = p.split(':')
                p_dt = parse_date(p_dt_str)
                p_amt = float(p_amt_str)
                if req_date <= p_dt <= end_date:
                    daily_flows[p_dt] -= p_amt

        balance = cur_bal
        min_balance_seen = balance
        daily_balances = {}

        curr = req_date
        while curr <= end_date:
            balance += daily_flows[curr]
            daily_balances[curr] = balance
            if balance < min_balance_seen:
                min_balance_seen = balance
            curr += timedelta(days=1)

        is_safe = (round(min_balance_seen, 2) >= min_bal - 0.01)
        return is_safe, min_balance_seen, daily_balances

    def calculate_amount_safe_to_pay(self, user_id, req_date_str, requested_amount):
        profile = self.profiles[user_id]
        min_bal = float(profile['minimum_balance_to_keep'])
        
        is_safe, min_seen, daily_balances = self.simulate_trajectory(user_id, req_date_str, payment_schedule=None)
        
        max_buffer = min_seen - min_bal
        safe_to_pay = max(0.0, min(requested_amount, max_buffer))
        safe_to_pay = round(safe_to_pay, 2)
        if safe_to_pay.is_integer():
            safe_to_pay = int(safe_to_pay)
        return safe_to_pay

    def calculate_earliest_date_for_full_payment(self, user_id, req_date_str, requested_amount, desired_completion_date_str):
        req_date = parse_date(req_date_str)
        end_date = req_date + timedelta(days=90)
        
        safe_today = self.calculate_amount_safe_to_pay(user_id, req_date_str, requested_amount)
        if safe_today >= requested_amount:
            return req_date_str

        curr = req_date
        while curr <= end_date:
            curr_str = format_date(curr)
            is_safe, _, _ = self.simulate_trajectory(user_id, req_date_str, payment_schedule=f"{curr_str}:{requested_amount}")
            if is_safe:
                return curr_str
            curr += timedelta(days=1)

        return ""

    def find_spending_changes(self, user_id, req_date_str, candidate_plan, target_shortfall):
        profile = self.profiles[user_id]
        reduce_cats = set(c for c in profile['expense_categories_user_is_willing_to_reduce'].split('|') if c)
        stop_cats = set(c for c in profile['expense_categories_user_is_willing_to_stop'].split('|') if c)
        protect_cats = set(c for c in profile['expense_categories_to_protect'].split('|') if c)

        recurring = self.analyze_user_recurrence(user_id, req_date_str)
        available_changes = []

        for rec in recurring:
            cat = rec['category']
            if cat in protect_cats:
                continue
            evt_id = rec['latest_event_id']
            flex = rec['flexibility']

            if cat in stop_cats and flex in ('stoppable', 'reducible_or_stoppable'):
                available_changes.append(('stop', evt_id, rec['amount'], f"stop:{evt_id}", rec['description']))

            if cat in reduce_cats and flex in ('reducible', 'reducible_or_stoppable') and rec['minimum_allowed_amount'] is not None:
                saving = rec['amount'] - rec['minimum_allowed_amount']
                if saving > 0:
                    min_amt_str = format_amount(rec['minimum_allowed_amount'])
                    available_changes.append(('reduce_to', evt_id, saving, f"reduce_to:{evt_id}:{min_amt_str}", rec['description'], rec['minimum_allowed_amount']))

        import itertools
        for k in range(1, min(4, len(available_changes) + 1)):
            for combo in itertools.combinations(available_changes, k):
                evt_ids = set(c[1] for c in combo)
                if len(evt_ids) < len(combo):
                    continue
                sc_str = '|'.join(c[3] for c in combo)
                is_safe, _, _ = self.simulate_trajectory(user_id, req_date_str, payment_schedule=candidate_plan, spending_changes=sc_str)
                if is_safe:
                    return sc_str, combo

        return None, None

    def evaluate_request(self, req):
        req_id = req['request_id']
        user_id = req['user_id']
        req_date_str = req['request_date']
        req_amt = float(req['requested_amount'])
        desired_dt_str = req['desired_completion_date']
        allows_partial = req['allows_partial_payment'].lower() == 'true'

        profile = self.profiles[user_id]
        home_curr = profile['home_currency']
        considered_methods = set(m for m in profile['payment_methods_user_will_consider'].split('|') if m)
        max_inst_months = int(profile['max_installment_months']) if profile['max_installment_months'] else 0

        safe_to_pay = self.calculate_amount_safe_to_pay(user_id, req_date_str, req_amt)
        earliest_full_dt = self.calculate_earliest_date_for_full_payment(user_id, req_date_str, req_amt, desired_dt_str)

        candidates = []

        # Option A: Full Payment Today
        if 'full_payment' in considered_methods:
            is_safe, _, _ = self.simulate_trajectory(user_id, req_date_str, payment_schedule=f"{req_date_str}:{req_amt}")
            if is_safe:
                candidates.append({
                    'status': 'affordable_now',
                    'method': 'full_payment',
                    'plan': f"{req_date_str}:{format_amount(req_amt)}",
                    'earliest_full': req_date_str,
                    'spending_changes': 'none',
                    'total_cost': req_amt,
                    'start_date': req_date_str,
                    'num_payments': 1,
                    'option_id': '0',
                    'completes_by_deadline': True,
                    'requires_spending_changes': False,
                    'raw_combo': None
                })

        # Option B: Installments
        if 'installments' in considered_methods and max_inst_months > 0:
            options = self.options_by_request.get(req_id, [])
            for opt in options:
                if opt['payment_method'] != 'installments':
                    continue
                num_pmts = int(opt['number_of_payments'])
                if num_pmts > max_inst_months:
                    continue
                pmt_amt = float(opt['payment_amount'])
                first_dt = parse_date(opt['first_payment_date'])
                freq = int(opt['payment_frequency_days'])
                total_cost = float(opt['total_payable_amount'])
                
                schedule_parts = []
                cur_dt = first_dt
                for i in range(num_pmts):
                    schedule_parts.append(f"{format_date(cur_dt)}:{format_amount(pmt_amt)}")
                    cur_dt += timedelta(days=freq)
                
                last_pmt_dt = format_date(first_dt + timedelta(days=freq * (num_pmts - 1)))
                plan_str = '|'.join(schedule_parts)
                completes_on_time = (last_pmt_dt <= desired_dt_str)

                is_safe, _, _ = self.simulate_trajectory(user_id, req_date_str, payment_schedule=plan_str)
                if is_safe:
                    candidates.append({
                        'status': 'affordable_with_plan',
                        'method': 'installments',
                        'plan': plan_str,
                        'earliest_full': earliest_full_dt,
                        'spending_changes': 'none',
                        'total_cost': total_cost,
                        'start_date': opt['first_payment_date'],
                        'num_payments': num_pmts,
                        'option_id': opt['payment_option_id'],
                        'completes_by_deadline': completes_on_time,
                        'requires_spending_changes': False,
                        'pmt_amt': pmt_amt,
                        'raw_combo': None
                    })

        # Option C: Partial Payment
        if allows_partial and 'partial_payment' in considered_methods:
            if 0 < safe_to_pay < req_amt and earliest_full_dt and earliest_full_dt <= desired_dt_str:
                rem_amt = round(req_amt - safe_to_pay, 2)
                plan_str = f"{req_date_str}:{format_amount(safe_to_pay)}|{earliest_full_dt}:{format_amount(rem_amt)}"
                is_safe, _, _ = self.simulate_trajectory(user_id, req_date_str, payment_schedule=plan_str)
                if is_safe:
                    candidates.append({
                        'status': 'affordable_with_plan',
                        'method': 'partial_payment',
                        'plan': plan_str,
                        'earliest_full': earliest_full_dt,
                        'spending_changes': 'none',
                        'total_cost': req_amt,
                        'start_date': req_date_str,
                        'num_payments': 2,
                        'option_id': '0',
                        'completes_by_deadline': True,
                        'requires_spending_changes': False,
                        'safe_amt': safe_to_pay,
                        'rem_amt': rem_amt,
                        'raw_combo': None
                    })

        # Option D: Wait
        if 'full_payment' in considered_methods and earliest_full_dt and earliest_full_dt != req_date_str:
            completes_on_time = (earliest_full_dt <= desired_dt_str)
            if completes_on_time:
                plan_str = f"{earliest_full_dt}:{format_amount(req_amt)}"
                candidates.append({
                    'status': 'affordable_later',
                    'method': 'wait',
                    'plan': plan_str,
                    'earliest_full': earliest_full_dt,
                    'spending_changes': 'none',
                    'total_cost': req_amt,
                    'start_date': earliest_full_dt,
                    'num_payments': 1,
                    'option_id': '9999',
                    'completes_by_deadline': True,
                    'requires_spending_changes': False,
                    'raw_combo': None
                })

        # 3. If no candidate completes on time, try spending changes
        valid_candidates = [c for c in candidates if c['completes_by_deadline']]
        if not valid_candidates:
            if 'full_payment' in considered_methods:
                plan_today = f"{req_date_str}:{format_amount(req_amt)}"
                sc_str, combo = self.find_spending_changes(user_id, req_date_str, plan_today, req_amt - safe_to_pay)
                if sc_str:
                    candidates.append({
                        'status': 'affordable_with_plan',
                        'method': 'full_payment',
                        'plan': plan_today,
                        'earliest_full': earliest_full_dt,
                        'spending_changes': sc_str,
                        'total_cost': req_amt,
                        'start_date': req_date_str,
                        'num_payments': 1,
                        'option_id': '0',
                        'completes_by_deadline': True,
                        'requires_spending_changes': True,
                        'raw_combo': combo
                    })

        # 4. Rank candidates according to the specification
        valid_candidates = [c for c in candidates if c['completes_by_deadline']]
        if valid_candidates:
            def rank_key(c):
                return (
                    1 if c['requires_spending_changes'] else 0,
                    c['total_cost'],
                    c['start_date'],
                    c['num_payments'],
                    c['option_id']
                )
            valid_candidates.sort(key=rank_key)
            best = valid_candidates[0]
        else:
            best = {
                'status': 'not_affordable',
                'method': 'not_recommended',
                'plan': 'none',
                'earliest_full': earliest_full_dt if (earliest_full_dt and earliest_full_dt <= desired_dt_str) else '',
                'spending_changes': 'none',
                'decision_explanation': f"Do not make this payment by {format_date_human(desired_dt_str)}. None of the available options keeps the {home_curr} {format_amount_with_commas(profile['minimum_balance_to_keep'])} minimum protected."
            }

        # Build decision explanation
        min_bal_str = format_amount_with_commas(profile['minimum_balance_to_keep'])
        req_amt_str = format_amount_with_commas(req_amt)

        if 'decision_explanation' not in best:
            method = best['method']
            if method == 'full_payment' and best['status'] == 'affordable_now':
                exp = f"Pay {home_curr} {req_amt_str} today. This leaves at least {home_curr} {min_bal_str} available over the next 90 days."
            elif method == 'full_payment' and best['requires_spending_changes']:
                combo = best.get('raw_combo', [])
                action_texts = []
                for c in combo:
                    if c[0] == 'stop':
                        action_texts.append(f"Stop the {c[4].lower()}")
                    elif c[0] == 'reduce_to':
                        action_texts.append(f"reduce the {c[4].lower()} to {home_curr} {format_amount_with_commas(c[5])}")
                sc_text = " and ".join(action_texts)
                exp = f"{sc_text}, then pay {home_curr} {req_amt_str} today. This leaves at least {home_curr} {min_bal_str} available."
            elif method == 'installments':
                pmt_str = format_amount_with_commas(best.get('pmt_amt', 0))
                start_h = format_date_human(best['start_date'])
                exp = f"Use {best['num_payments']} installments of {home_curr} {pmt_str}, starting {start_h}. This leaves at least {home_curr} {min_bal_str} available."
            elif method == 'partial_payment':
                s_amt_str = format_amount_with_commas(best.get('safe_amt', safe_to_pay))
                rem_str = format_amount_with_commas(best.get('rem_amt', req_amt - safe_to_pay))
                earl_h = format_date_human(earliest_full_dt)
                exp = f"Pay {home_curr} {s_amt_str} today and the remaining {home_curr} {rem_str} on {earl_h}. This completes the full request and keeps the {home_curr} {min_bal_str} minimum protected."
            elif method == 'wait':
                earl_h = format_date_human(earliest_full_dt)
                exp = f"Pay {home_curr} {req_amt_str} in full on {earl_h}. Paying earlier would take the balance below the {home_curr} {min_bal_str} minimum."
            else:
                exp = f"Do not make this payment by {format_date_human(desired_dt_str)}. None of the available options keeps the {home_curr} {min_bal_str} minimum protected."
            best['decision_explanation'] = exp

        return {
            'request_id': req_id,
            'amount_safe_to_pay': safe_to_pay,
            'affordability_status': best['status'],
            'recommended_payment_method': best['method'],
            'payment_plan': best['plan'],
            'earliest_date_for_full_payment': best['earliest_full'],
            'spending_changes_needed': best['spending_changes'],
            'decision_explanation': best['decision_explanation']
        }
