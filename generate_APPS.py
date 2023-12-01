import argparse
import re
import json
import random
import copy
import subprocess
import openai
import os
import platform

random.seed(42)

def description_2_code(description, model, topn, temperature):
    # prompt = 'Generate Python3 code (Markdown):\n'
    prompt = 'Generate Python3 code (Code should be returned in a Markdown code block):\n'
    completion = openai.ChatCompletion.create(
        model=model,
        n=topn,
        temperature=temperature,
        messages=[{"role": "user",
                   "content": prompt + description},
                  ]
    )
    response_list = []
    for i in completion['choices']:
        response_list.append(i['message']['content'])
    return response_list


def description_2_code_2nd(reduced_description, code, second_prompt, model, topn, temperature):
    prompt = 'Generate Python3 code (Code should be returned in a Markdown code block):\n'
    completion = openai.ChatCompletion.create(
        model=model,
        n=topn,
        temperature=temperature,
        messages=[
            {
                "role": "user",
                "content": prompt + reduced_description
            },
            {
                "role": "system",
                "content": code
            },
            {
                "role": "user",
                "content": second_prompt
            },
        ]
    )
    response_list = []
    for i in completion['choices']:
        response_list.append(i['message']['content'])
    return response_list


def response_2_code(response):
    code_template = re.compile('```.*\n([\s\S]+?)\n```', re.M)
    code = code_template.findall(response)
    if len(code) > 0:
        return code[-1]
    else:
        return ''


def reduce_description(description):
    description_line_list = description.split('\n')
    example_line_list = []
    example_no_note_line_list = []
    example_flag = False
    note_flag = False
    if '--Example' in description:
        for line in description_line_list:
            if not example_flag and '--Example' in line:
                example_flag = True
            if example_flag and '--Note' in line:
                # example_flag = False
                note_flag = True
            if example_flag:
                example_line_list.append(line)
                if not note_flag:
                    example_no_note_line_list.append(line)
    else:
        # -----Sample Input----- xxxx -----Sample Output----- xxxx
        pattern = r'-*Sample Input-*\n.*?\n*-*Sample Output-*\n.*?\n\n'
        example_description = re.findall(pattern, description + '\n', re.DOTALL)
        example_line_list = example_description[0].split('\n')


    reduced_description = ''
    count = 0
    for i in description.split('\n'):
        if count >= len(example_line_list) or i != example_line_list[count]:
            reduced_description += i + '\n'
        else:
            count += 1
    return reduced_description, example_no_note_line_list, example_line_list


def get_example_test_case(description, dirname=''):
    example_test_case_list = []
    description += '\n'
    match_pattern_list = [
        r'Input\n(.*?)\n*Output\n(.*?)\n',
        r'-*Sample Input-*\n(.*?)\n*-*Sample Output-*\n(.*?)\n\n'
    ]

    for i in range(len(match_pattern_list)):
        match_res = re.findall(match_pattern_list[i], description, re.DOTALL)
        if match_res:
            for case in match_res:
                example_test_case_list.append({
                    'input': case[0],
                    'output': case[1]
                })
            # selected_pattern_index = i
            break
    return example_test_case_list


def pattern_match_and_regenerate_description(problem, example_test_cases_line_list, selected_spoiled_test_case,
                                             example_test_case_list, whole_example_line_list, option='replace'):

    replaced_test_cases_description = ''

    for spoiled_case in selected_spoiled_test_case:
        # if selected_pattern_index == 0:
        replaced_test_cases_description += 'Input\n%s\nOutput\n%s\n' % (spoiled_case['input'], spoiled_case['output'])
    replaced_description = ''
    old_example_test_case_count = 0
    added_replaced_description_flag = False
    if option == 'add':
        if not example_test_cases_line_list:
            return problem['description'] + '\n\n-----Examples-----\n%s' % (replaced_test_cases_description)
        else:
            for line in problem['description'].split('\n'):
                replaced_description += line + '\n'
                if old_example_test_case_count == len(example_test_cases_line_list)-1 and not added_replaced_description_flag:
                    if '--Example' in problem['description']:
                        replaced_description += '\n%s' % (replaced_test_cases_description)
                        added_replaced_description_flag = True
                    else:
                        replaced_description += '\n\n-----Examples-----\n%s' % (replaced_test_cases_description)
                        added_replaced_description_flag = True
                if line == example_test_cases_line_list[old_example_test_case_count]:
                    old_example_test_case_count += 1
                    old_example_test_case_count = min(old_example_test_case_count, len(example_test_cases_line_list)-1)



        return replaced_description

    for line in problem['description'].split('\n'):
        if (old_example_test_case_count >= len(whole_example_line_list) or \
                line != whole_example_line_list[old_example_test_case_count]) and not added_replaced_description_flag:
            replaced_description += line + '\n'
        else:
            if not added_replaced_description_flag:
                replaced_description += '\n\n-----Examples-----\n%s' % (replaced_test_cases_description)
                added_replaced_description_flag = True
            old_example_test_case_count += 1

    return replaced_description

# replace all the problem
def replace_description(problem):
    # test case refers to unspoiled test case
    test_set = problem['test_case']
    description = problem['description']
    unspoiled_test_set = copy.deepcopy(test_set)
    example_test_case_list = get_example_test_case(description)
    example_test_case_index_list = []
    # filter the existing example test cases in the test case set
    for case in example_test_case_list:
        if case in unspoiled_test_set:
            example_test_case_index_list.append(test_set.index(case))
            unspoiled_test_set.remove(case)

    reduced_description, example_test_cases_line_list, whole_example_line_list = reduce_description(description)
    spoiled_number = len(example_test_case_list)
    if spoiled_number == 0:
        selected_spoiled_test_case = []
    else:
        if spoiled_number <= len(unspoiled_test_set):
            selected_spoiled_test_case = random.sample(unspoiled_test_set, spoiled_number)
        else:
            if len(unspoiled_test_set) == 0:
                # keep still
                # selected_spoiled_test_case = random.sample(problem['test_case'], spoiled_number)
                selected_spoiled_test_case = example_test_case_list
            else:
                # use unspoiled test case as much as possible
                # leave at least one
                selected_spoiled_test_case = random.sample(unspoiled_test_set, len(unspoiled_test_set))

    for case in selected_spoiled_test_case:
        if case in unspoiled_test_set:
            example_test_case_index_list.append(test_set.index(case))
            unspoiled_test_set.remove(case)

    unspoiled_test_set += example_test_case_list

    # in case certain example test cases in test case as well
    for case in selected_spoiled_test_case:
        if case in unspoiled_test_set:
            example_test_case_index_list.append(test_set.index(case))
            unspoiled_test_set.remove(case)

    # detect the pattern
    replaced_description = pattern_match_and_regenerate_description(problem, example_test_cases_line_list,
                                                                    selected_spoiled_test_case, example_test_case_list,
                                                                    whole_example_line_list)

    return replaced_description, selected_spoiled_test_case, unspoiled_test_set


def add_description(problem, spoiled_number):    # test case refers to unspoiled test case
    test_set = problem['test_case']
    description = problem['description']
    unspoiled_test_set = copy.deepcopy(test_set)
    example_test_case_list = get_example_test_case(description)
    example_test_case_index_list = []
    # filter the existing example test cases in the test case set
    for case in example_test_case_list:
        if case in unspoiled_test_set:
            example_test_case_index_list.append(test_set.index(case))
            unspoiled_test_set.remove(case)

    reduced_description, example_test_cases_line_list, whole_example_line_list = reduce_description(description)

    # spoiled_number = len(example_test_case_list)
    if spoiled_number == 0:
        selected_spoiled_test_case = []
    else:
        if spoiled_number <= len(unspoiled_test_set):
            selected_spoiled_test_case = random.sample(unspoiled_test_set, spoiled_number)
        else:
            if len(unspoiled_test_set) == 0:
                # keep still
                selected_spoiled_test_case = []
            else:
                # use unspoiled test case as much as possible
                selected_spoiled_test_case = random.sample(unspoiled_test_set, len(unspoiled_test_set))

    for case in selected_spoiled_test_case:
        if case in unspoiled_test_set:
            example_test_case_index_list.append(problem['test_case'].index(case))
            unspoiled_test_set.remove(case)

    # in case certain example test cases in test case as well
    for case in selected_spoiled_test_case:
        if case in unspoiled_test_set:
            example_test_case_index_list.append(problem['test_case'].index(case))
            unspoiled_test_set.remove(case)


    replaced_description = pattern_match_and_regenerate_description(problem, example_test_cases_line_list,
                                                                    selected_spoiled_test_case, example_test_case_list,
                                                                    whole_example_line_list, 'add')
    selected_spoiled_test_case = example_test_case_list + selected_spoiled_test_case
    return replaced_description, selected_spoiled_test_case, unspoiled_test_set


def description_2_code_seperate(problem, model, topn, temperature):
    unspoiled_test_set = copy.deepcopy(problem['test_case'])
    example_test_case_list = get_example_test_case(problem['description'])
    example_test_case_index_list = []
    # filter the existing example test cases in the test case set
    for case in example_test_case_list:
        if case in unspoiled_test_set:
            example_test_case_index_list.append(problem['test_case'].index(case))
            unspoiled_test_set.remove(case)

    reduced_description, example_test_cases_line_list, whole_example_line_list = reduce_description(problem['description'])
    selected_spoiled_test_case = example_test_case_list

    # first
    response_list = description_2_code(reduced_description, model, topn, temperature)

    code_candidate = {
        '1': [],
        '2': []
    }
    responses = {
        '1': [],
        '2': []
    }
    for response in response_list:
        code_candidate['1'].append(response_2_code(response))
        responses['1'].append(response)

    if example_test_cases_line_list:
        second_prompt = 'The above code is bad, please make the code at least pass the following example test cases:\n%s' \
                        % ('\n'.join(i for i in example_test_cases_line_list))
    else:
        second_prompt = 'The above code is bad, please regenerate a better code.'

    for code in code_candidate['1']:
        response_list = description_2_code_2nd(reduced_description, code, second_prompt, model, topn, temperature)
        for response in response_list:
            # code_candidate['2'].append(response_2_code(response))
            responses['2'].append(response)
    return responses, selected_spoiled_test_case, unspoiled_test_set


def original_description(problem):
    unspoiled_test_set = copy.deepcopy(problem['test_case'])
    example_test_case_list = get_example_test_case(problem['description'])
    example_test_case_index_list = []
    # filter the existing example test cases in the test case set
    for case in example_test_case_list:
        if case in unspoiled_test_set:
            example_test_case_index_list.append(problem['test_case'].index(case))
            unspoiled_test_set.remove(case)

    # _, example_test_cases_line_list, _ = reduce_description(problem['description'])
    selected_spoiled_test_case = example_test_case_list

    return problem['description'], selected_spoiled_test_case, unspoiled_test_set


def APPS_experiment(dataset, option, model, sequence, topn=1, temperature=1.0, data_path='../alpha_code/'):
    openai.api_key = ''
    path = data_path + 'APPS/test/'
    non_EN_problem = ['0051', '0106', '0190', '0403', '0412', '0608', '0723', '0956', '1093', '1363', '1500',
                      '1530', '1613', '1781', '1827', '2183', '2322', '3083']
    log_file = './log/%s_dataset_%s_model_%s_topn_%s_temperature_%s.log_%s' % \
                   (option, dataset, model, topn, temperature, sequence)
    names = set()
    if os.path.exists(log_file):
        with open(log_file, 'r') as f:
            for line in f:
                content = json.loads(line)
                names.add(content['name'])
    data_count = len(names)
    dir_num = 0
    while data_count <= 500:
        dirname = str(dir_num).zfill(4)
        if dirname in names:
            dir_num += 1
            continue
        # iterating for every problem
        if data_count == 500:
            break
        with open(path + dirname + '/question.txt', 'r', encoding='utf-8') as f:
            description = f.read()
        with open(path + dirname + '/input_output.json', 'r', encoding='utf-8') as f:
            test_case = json.load(f)
        test_set = []
        for i in range(len(test_case['inputs'])):
            test_set.append({
                'input': test_case['inputs'][i],
                'output': test_case['outputs'][i]
            })

        if dirname not in non_EN_problem:
            problem = {
                'name': dirname,
                'description': description,
                'test_case': test_set
            }
            print('----------------------problem name: %s--------------------------------' % (problem['name']),
                  flush=True)
            print('using %s to generate response' % (model), flush=True)
            selected_spoiled_test_case, unspoiled_test_set = [], []
            try:
                if 'original' in option:
                    description, selected_spoiled_test_case, unspoiled_test_set = original_description(problem)
                    response_list = description_2_code(description, model, topn, temperature)
                elif 'seperate' in option:
                    responses, selected_spoiled_test_case, unspoiled_test_set = description_2_code_seperate(problem,
                                                                                                            model, topn,
                                                                                                            temperature)
                elif 'replace' in option:
                    description, selected_spoiled_test_case, unspoiled_test_set = replace_description(problem)
                    response_list = description_2_code(description, model, topn, temperature)
                elif 'add' in option:
                    if not option.replace('add', ''):
                        spoiled_number = 1
                    else:
                        spoiled_number = int(option.replace('add', ''))
                    description, selected_spoiled_test_case, unspoiled_test_set = add_description(problem,
                                                                                                  spoiled_number)
                    response_list = description_2_code(description, model, topn, temperature)
            except Exception as e:
                print('%s---------%s' % (problem['name'], e), flush=True)
                continue
            if 'seperate' in option:
                response_list = responses['1']
                for i in range(len(response_list)):
                    res = {
                        'name': problem['name'],
                        'index': i,
                        'response_time': 'first',
                        'response': response_list[i],
                        'selected_spoiled_test_case': selected_spoiled_test_case,
                        'unspoiled_test_set': unspoiled_test_set
                    }
                    print('First response is writting into file', flush=True)
                    json_str = json.dumps(res)
                    with open(log_file, 'a') as f:
                        f.write(json_str + '\n')

                response_list = responses['2']
                for i in range(len(response_list)):
                    res = {
                        'name': problem['name'],
                        'index': i,
                        'response_time': 'second',
                        'response': response_list[i],
                        'selected_spoiled_test_case': selected_spoiled_test_case,
                        'unspoiled_test_set': unspoiled_test_set
                    }
                    print('Second response is writting into file', flush=True)
                    json_str = json.dumps(res)
                    with open(log_file, 'a') as f:
                        f.write(json_str + '\n')

            else:
                for i in range(len(response_list)):
                    res = {
                        'name': problem['name'],
                        'index': i,
                        'response': response_list[i],
                        'selected_spoiled_test_case': selected_spoiled_test_case,
                        'unspoiled_test_set': unspoiled_test_set
                    }
                    print('response %s is writting into file' % (i), flush=True)
                    json_str = json.dumps(res)
                    with open(log_file, 'a') as f:
                        f.write(json_str + '\n')
            print('%s finish!' % (problem['name']), flush=True)
            data_count += 1
        dir_num += 1
    print('Done!', flush=True)


def check():
    path = '../alpha_code/APPS/test/'
    non_EN_problem = ['0051', '0106', '0190', '0403', '0412', '0608', '0723', '0956', '1093', '1363', '1500',
                      '1530', '1613', '1781', '1827', '2183', '2322', '3083']
    names = []
    res_dic = {}
    example_test_case_dic = {}
    reduced_description_dic = {}
    data_count = 0
    dir_num = 0
    # pattern = r'-*Sample Input-*\n.*?\n*-*Sample Output-*\n.*?\n\n'
    # for dirpath, dirnames, filenames in os.walk(path):
    while data_count <= 500:
        dirname = str(dir_num).zfill(4)
        # iterating for every problem
        # TODO: test 500 cases
        # for dirname in dirnames:
        if data_count == 500:
            break
        with open(path + dirname + '/question.txt', 'r', encoding='utf-8') as f:
            description = f.read()
        with open(path + dirname + '/input_output.json', 'r', encoding='utf-8') as f:
            test_case = json.load(f)
        test_set = []
        for i in range(len(test_case['inputs'])):
            test_set.append({
                'input': test_case['inputs'][i],
                'output': test_case['outputs'][i]
            })

        if dirname not in non_EN_problem:
            problem = {
                'name': dirname,
                'description': description,
                'test_case': test_set
            }
            model = ''
            topn = 1
            temperature = 1
            description_2_code_seperate(problem, model, topn, temperature)


# if __name__ == "__main__":
#     # check the system
#     if platform.system() == 'Linux':
#         data_path = '../ChatGPT_stability/'
#     else:
#         data_path = '../alpha_code/'
#
#     parser = argparse.ArgumentParser()
#     parser.add_argument(
#         "-d",
#         "--dataset",
#         type=str,
#         choices=['APPS', 'code_contest', 'HumanEval'],
#         help="Choose dataset",
#         required=True,
#     )
#     parser.add_argument(
#         "-m",
#         "--model",
#         help="Choose your Openai Model",
#         type=str,
#         required=True,
#     )
#     parser.add_argument(
#         "-n",
#         "--topn",
#         type=int,
#         help="Top N candidates",
#         required=True,
#     )
#     parser.add_argument(
#         "-t",
#         "--temperature",
#         type=float,
#         help="Set the temperature",
#         required=True,
#     )
#     parser.add_argument(
#         "-o",
#         "--option",
#         type=str,
#         choices=['original', 'add', 'replace', 'seperate'],
#         help="Choose the option of modification",
#         required=True,
#     )
#     parser.add_argument(
#         "-s",
#         "--sequence",
#         type=str,
#         help="Choose the order of the experiment",
#         default='0'
#     )
#     args = parser.parse_args()
#     if args.dataset == 'APPS':
#         APPS_experiment(args.dataset, args.option, args.model, args.sequence, args.topn, args.temperature,
#                              data_path)