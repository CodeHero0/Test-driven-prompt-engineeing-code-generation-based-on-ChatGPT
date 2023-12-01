import argparse
import json
import os
import subprocess

from evalplus.data import get_human_eval_plus, write_jsonl

def generate_test_case(problem, demo_file, call_demo_file):
# def get_output(problem):
    entry_point = problem['entry_point']
    solution = problem['prompt'] + problem['canonical_solution']
    with open(demo_file, 'w', encoding='UTF-8') as f:
        f.write(solution)

    base_inputs = problem['base_input']
    plus_inputs = problem['plus_input']
    time_limit = 3
    test_case_base = []
    for i in range(len(base_inputs)):
        with open(call_demo_file, 'w', encoding='utf-8') as f:
            f.write('from %s import %s\nprint(%s(%s))' % (
                demo_file.split('.')[0],
                entry_point,
                entry_point,
                str(base_inputs[i])[1:-1]
            ))
        try:
            output = subprocess.run(["python", call_demo_file], capture_output=True, text=True, timeout=time_limit)
        except:
            continue
        if output.stdout:
            test_case_base.append({
                'input': str(base_inputs[i])[1:-1],
                'output': output.stdout.strip()
            })
        else:
            test_case_base.append({
                'input': str(base_inputs[i])[1:-1],
                'output': "None"
            })
    test_case_plus = []
    for i in range(len(plus_inputs)):
        with open(call_demo_file, 'w', encoding='utf-8') as f:
            f.write('from %s import %s\nprint(%s(%s))' % (
                demo_file.split('.')[0],
                entry_point,
                entry_point,
                str(plus_inputs[i])[1:-1]
            ))
        try:
            output = subprocess.run(["python", call_demo_file], capture_output=True, text=True, timeout=time_limit)
        except:
            continue
        if output.stdout:
            test_case_plus.append({
                'input': str(plus_inputs[i])[1:-1],
                'output': output.stdout.strip()
            })
        else:
            test_case_plus.append({
                'input': str(plus_inputs[i])[1:-1],
                'output': "None"
            })

    return test_case_base, test_case_plus

def generate_dataset(targert_file, mini=False):

    if mini:
        problems = get_human_eval_plus(True, True)
    else:
        problems = get_human_eval_plus()
    # generate the test case
    demo_file = 'demo.py'
    call_demo_file = 'call_demo.py'
    names = []


    # targert_file = '../alpha_code/HumanEval/HumanEval_plus.jsonl'

    if not os.path.exists(targert_file):
        with open(targert_file, 'w', encoding='utf-8') as f:
            f.write('')

    with open(targert_file, 'r', encoding='utf-8') as f:
        for line in f.readlines():
            names.append(json.loads(line)['name'])

    for key in problems:
        if key in names:
            continue
        print(key, flush=True)
        problem = problems[key]
        test_case_base, test_case_plus = generate_test_case(problem, demo_file, call_demo_file)
        problem_dic = {
            'name': key,
            'prompt': problem['prompt'],
            'entry_point': problem['entry_point'],
            'canonical_solution': problem['canonical_solution'],
            'test_case_base': test_case_base,
            'test_case_plus': test_case_plus,
            'atol': problem['atol']
        }
        json_str = json.dumps(problem_dic)
        with open(targert_file, 'a', encoding='utf-8') as f:
            f.write(json_str + '\n')


    os.remove(demo_file)
    os.remove(call_demo_file)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-m",
        "--mini",
        action='store_true',
        help="Whether want mini version",
        required=True,
    )
    parser.add_argument(
        "-s",
        "--store_file_path",
        help="Choose your Openai Model",
        type=str,
        required=True,
    )
    args = parser.parse_args()
    generate_dataset(args.store_file_path, args.mini)