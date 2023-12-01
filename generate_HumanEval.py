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


def get_example_test_case_list_HumanEval(problem):
    description_list = problem['prompt'].split('\n')
    example_flag = False
    example_test_case_list = []
    p = r'>>>.*?\((.*)\)'
    tmp_test_case = {}
    for line in description_list:
        if '>>>' in line:
            example_flag = True
        if example_flag:
            if '"""' in line or "'''" in line:
                break
            p1 = re.search(p, line)
            if p1:
                tmp_test_case['input'] = p1.group(1)
                # print(p1.group(1))
            else:
                output = line.strip()
                if problem['name'] == 'HumanEval/12' and not output:
                    output = 'None'
                if not output.strip():
                    continue
                if ('\'' in output[0] and '\'' in output[-1]) or ('\"' in output[0] and '\"' in output[-1]):
                    tmp_test_case['output'] = output[1:-1]
                else:
                    tmp_test_case['output'] = output
                tmp_test_case['relation'] = '=='

                if 'input' in tmp_test_case and 'output' in tmp_test_case:
                    example_test_case_list.append(tmp_test_case)
                tmp_test_case = {}
                # print(line.strip())
    if problem['name'] == 'HumanEval/32':
        example_test_case_list = [
            {
                'input': '[1, 2]',
                'output': 'True',
                'relation': 'round(find_zero([1, 2]), 2) == -0.5'
            },
            {
                'input': '[-6, 11, -6, 1]',
                'output': 'True',
                'relation': 'round(find_zero([-6, 11, -6, 1]), 2) == 1.0'
            }
        ]
    elif problem['name'] == 'HumanEval/51':
        example_test_case_list[1] = {
            'input': '"abcdef\\nghijklm"',
            'output': 'bcdf\nghjklm',
            'relation': '=='
        }
    elif problem['name'] == 'HumanEval/113':
        tmp = [
            ("['1234567']", '["the number of odd elements 4n the str4ng 4 of the 4nput."]'),
            ("['3','11111111']", '["the number of odd elements 1n the str1ng 1 of the 1nput.", "the number of odd elements 8n the str8ng 8 of the 8nput."]')
        ]
        new_res = []
        for item in tmp:
            new_res.append(
                {
                    'input': item[0],
                    'output': item[1],
                    'relation': '=='
                }
            )
        return new_res
    return example_test_case_list


def get_example_test_cases_after(problem):
    description = problem['prompt']
    entry_point = problem['entry_point']
    # exceptional cases
    if problem['name'] == 'HumanEval/68':
        tmp = [
            ('[4,2,3]', '[2, 1]'),
            ('[1,2,3]', '[2, 1]'),
            ('[]', '[]'),
            ('[5, 0, 3, 0, 4, 2]', '[0, 1]')
        ]
        new_res = []
        for item in tmp:
            new_res.append(
                {
                    'input': item[0],
                    'output': item[1],
                    'relation': '=='
                }
            )
        return new_res
    elif problem['name'] == 'HumanEval/105':
        tmp =  [
            ('[2, 1, 1, 4, 5, 8, 2, 3]', "['Eight', 'Five', 'Four', 'Three', 'Two', 'Two', 'One', 'One']"),
            ('[]', '[]'),
            ('[1, -1 , 55]', "['One']")
        ]
        new_res = []
        for item in tmp:
            new_res.append(
                {
                    'input': item[0],
                    'output': item[1],
                    'relation': '=='
                }
            )
        return new_res
    elif problem['name'] == 'HumanEval/107':
        tmp = [
            ('3', '(1, 2)'),
            ('12', '(4, 6)'),
        ]
        new_res = []
        for item in tmp:
            new_res.append(
                {
                    'input': item[0],
                    'output': item[1],
                    'relation': '=='
                }
            )
        return new_res
    elif problem['name'] == 'HumanEval/112':
        tmp = [
            ('"abcde", "ae"', "('bcd',False)"),
            ('"abcdef", "b"', "('acdef',False)"),
            ('"abcdedcba", "ab"', "('cdedc',True)")
        ]
        new_res = []
        for item in tmp:
            new_res.append(
                {
                    'input': item[0],
                    'output': item[1],
                    'relation': '=='
                }
            )
        return new_res
    elif problem['name'] == 'HumanEval/115':
        tmp = [
            ('[[0,0,1,0], [0,1,0,0], [1,1,1,1]], 1', '6'),
            ('[[0,0,1,1], [0,0,0,0], [1,1,1,1], [0,1,1,1]], 2', '5'),
            ('[[0,0,0], [0,0,0]], 5', '0')
        ]
        new_res = []
        for item in tmp:
            new_res.append(
                {
                    'input': item[0],
                    'output': item[1],
                    'relation': '=='
                }
            )
        return new_res
    elif problem['name'] == 'HumanEval/120':
        tmp = [
            ('[-3, -4, 5], 3', '[-4, -3, 5]'),
            ('[4, -4, 4], 2', '[4, 4]'),
            ('[-3, 2, 1, 2, -1, -2, 1], 1', '[2]')
        ]
        new_res = []
        for item in tmp:
            new_res.append(
                {
                    'input': item[0],
                    'output': item[1],
                    'relation': '=='
                }
            )
        return new_res
    elif problem['name'] == 'HumanEval/122':
        tmp = [
            ('[111,21,3,4000,5,6,7,8,9], 4', '24')
        ]
        new_res = []
        for item in tmp:
            new_res.append(
                {
                    'input': item[0],
                    'output': item[1],
                    'relation': '=='
                }
            )
        return new_res
    elif problem['name'] == 'HumanEval/123':
        tmp = [
            ('5', '[1, 5]')
        ]
        new_res = []
        for item in tmp:
            new_res.append(
                {
                    'input': item[0],
                    'output': item[1],
                    'relation': '=='
                }
            )
        return new_res
    elif problem['name'] == 'HumanEval/129':
        tmp = [
            ('[ [1,2,3], [4,5,6], [7,8,9]], 3', '[1, 2, 1]'),
            ('[ [5,9,3], [4,1,6], [7,8,2]], 1', '[1]')
        ]
        new_res = []
        for item in tmp:
            new_res.append(
                {
                    'input': item[0],
                    'output': item[1],
                    'relation': '=='
                }
            )
        return new_res
    elif problem['name'] == 'HumanEval/143':
        tmp = [
            ('"This is a test"', 'is'),
            ('"lets go for swimming"', 'go for')
        ]
        new_res = []
        for item in tmp:
            new_res.append(
                {
                    'input': item[0],
                    'output': item[1],
                    'relation': '=='
                }
            )
        return new_res
    elif problem['name'] == 'HumanEval/147':
        tmp = [
            ('5', '1')
        ]
        new_res = []
        for item in tmp:
            new_res.append(
                {
                    'input': item[0],
                    'output': item[1],
                    'relation': '=='
                }
            )
        return new_res
    elif problem['name'] == 'HumanEval/160':
        tmp = [
            ('["+", "*", "-"], [2, 3, 4, 5]', '9')
        ]
        new_res = []
        for item in tmp:
            new_res.append(
                {
                    'input': item[0],
                    'output': item[1],
                    'relation': '=='
                }
            )
        return new_res
    split_sign_list = ['==>', '=>', '->', '➞', '==', '=', '# =>']
    # split_sign = split_sign_list[2]
    # written in formula
    new_res = []
    for split_sign in split_sign_list:
        if split_sign in description:
            if problem['name'] == 'HumanEval/81':
                entry_point = 'grade_equation'
            elif problem['name'] == 'HumanEval/149':
                entry_point = 'list_sort'
            pattern = r'(?<!def\s)%s\((.*?)\)\s*%s\s*(.*?)\n' % (entry_point, split_sign)
            # pattern = r'%s\((.*?)\)\s*.*?\s*(.*?)\n' % (entry_point)
            if 'for example' in description:
                description_split_sign = 'for example'
            elif 'For example' in description:
                description_split_sign = 'For example'
            else:
                description_split_sign = 'Example'
            if problem['name'] == 'HumanEval/130':
                description_split_sign = 'Example'
            description = description.strip().split(description_split_sign)[-1]
            if problem['name'] == 'HumanEval/140':
                description = problem['prompt']
            if problem['name'] == 'HumanEval/90':
                description = description.split('\n    \n')[-1]
            res = re.findall(pattern, description, re.DOTALL)
            if not res:
                continue
            if problem['name'] == 'HumanEval/125':
                pattern = r'(?<!def\s)%s\((.*?)\)\s*%s\s*(.*?)\n' % (entry_point, '==')
                res += re.findall(pattern, description)
            for item in res:
                if problem['name'] == 'HumanEval/141':
                    new_res.append(
                        {
                            'input': item[0],
                            'output': item[1].replace(' (the name should start with a latin alphapet letter)', ''),
                            'relation': '=='
                        }
                    )
                elif problem['name'] == 'HumanEval/80':
                    new_res.append(
                        {
                            'input': '\'' + item[0] + '\'',
                            'output': item[1],
                            'relation': '=='
                        }
                    )
                    # new_res.append((item[0], item[1].replace(' (the name should start with a latin alphapet letter)', '')))
                else:
                    if '=' in item[1]:
                        new_res.append(
                            {
                                'input': item[0],
                                'output': item[1].split('=')[-1].strip(),
                                'relation': '=='
                            }
                        )
                        # new_res.append((item[0], item[1].split('=')[-1].strip()))
                    else:
                        new_res.append(
                            {
                                'input': item[0],
                                'output': item[1].strip(),
                                'relation': '=='
                            }
                        )
                        # new_res.append((item[0], item[1].strip()))
            for item in new_res:
                output = item['output']
                if ('\'' in output[0] and '\'' in output[-1]) or ('\"' in output[0] and '\"' in output[-1]):
                    item['output'] = output[1:-1]
            if new_res:
                return new_res


    # written in natural language
    NL_pattern_list = [
        r'(.*?)\s*%s.*?%s\s*(.*?).\n' % (', the sum of digits will be', 'the output should be'),
        r'(.*?)\s*%s\s*(.*?)\.\n' % ('the output should be'),
        r'(.*?)\s*%s\s*(.*?)\n' % ('the output should be'),
        r'%s\((.*?)\)\s*# returns\s*(.*?)\n' % (entry_point),
        r'%s\((.*?)\)\s*returns\s*(.*?)\n' % (entry_point),
        r'%s\((.*?)\)\s*should return\s*(.*?)\.\n' % (entry_point)
    ]
    for NL_pattern in NL_pattern_list:
        # NL_split_sign = NL_split_sign_list[1]
        res = re.findall(NL_pattern, description)
        if not res:
            continue
        for item in res:
            if problem['name'] == 'HumanEval/84':
                new_res.append(
                    {
                        'input': item[0].split('=')[-1].strip(),
                        'output':  item[1][1:-1],
                        'relation': '=='
                    }
                )
            elif '=' in item[0]:
                new_res.append(
                    {
                        'input': item[0].split('=')[-1].strip(),
                        'output':  item[1],
                        'relation': '=='
                    }
                )
                # new_res.append((item[0].split('=')[-1].strip(), item[1]))
            else:
                new_res.append(
                    {
                        'input': item[0].strip(),
                        'output':  item[1],
                        'relation': '=='
                    }
                )
                # new_res.append((item[0].strip(), item[1]))
        for item in new_res:
            output = item['output']
            if ('\'' in output[0] and '\'' in output[-1]) or ('\"' in output[0] and '\"' in output[-1]):
                item['output'] = output[1:-1]

        if new_res:
            return new_res

    return []


def get_example_test_cases(problem):
    example_test_cases = get_example_test_case_list_HumanEval(problem)
    if not example_test_cases:
        example_test_cases = get_example_test_cases_after(problem)
    # change all output ' into "
    example_test_cases = regulate_example_test_cases(example_test_cases)
    return example_test_cases


def regulate_example_test_cases(test_cases):
    for i in range(len(test_cases)):
        if '\"' in test_cases[i]['output']:
            test_cases[i]['output'] = test_cases[i]['output'].replace('\"', '\'')
        if test_cases[i]['output'] == 'true':
            test_cases[i]['output'] = 'True'
        if test_cases[i]['output'] == 'false':
            test_cases[i]['output'] = 'False'
        try:
            if ('[' in test_cases[i]['output'] and ']' in test_cases[i]['output']) or \
                    ('{' in test_cases[i]['output'] and '}' in test_cases[i]['output']) or \
                    ('(' in test_cases[i]['output'] and ')' in test_cases[i]['output']):
                test_cases[i]['output'] = str(eval(test_cases[i]['output']))
        except:
            pass
        # test_cases[i]['output'] = str(eval(test_cases[i]['output']))
    return test_cases


def reduce_description(problem):
    description = problem['prompt']
    if '"""' in description:
        split_sign = '"""'
    elif "'''" in description:
        split_sign = "'''"
    comments = description.split(split_sign)[-2]
    example_test_cases_line_list = []
    test_case_flag = False
    for line in comments.split('\n'):
        if '>>>' in line or 'Example:' in line.strip() or\
                'Examples:' in line.strip() or \
                'for example:' in line.strip() or\
                'Example 1:' in line.strip() or \
                'For example:' in line.strip() or \
                ('Examples' in line.strip() and (problem['name'] == 'HumanEval/74' or
                                                 problem['name'] == 'HumanEval/82' or
                                                 problem['name'] == 'HumanEval/92' or
                                                 problem['name'] == 'HumanEval/99' or
                                                 problem['name'] == 'HumanEval/121' or
                                                 problem['name'] == 'HumanEval/125' or
                                                 problem['name'] == 'HumanEval/126' or
                                                 problem['name'] == 'HumanEval/148' or
                                                 problem['name'] == 'HumanEval/161')) or\
                ('Example' in line.strip() and (problem['name'] == 'HumanEval/84' or
                                        problem['name'] == 'HumanEval/112' or
                                        problem['name'] == 'HumanEval/114' or
                                        problem['name'] == 'HumanEval/138' or
                                        problem['name'] == 'HumanEval/147')) or \
                ('==' in line and (problem['name'] == 'HumanEval/90' or
                                   problem['name'] == 'HumanEval/140' or
                                   problem['name'] == 'HumanEval/151' or
                                   problem['name'] == 'HumanEval/158')) or \
                '[input/output] samples:' in line or \
                ('➞' in line and (problem['name'] == 'HumanEval/132' or problem['name'] == 'HumanEval/137')) or \
                ('=' in line and problem['name'] == 'HumanEval/144') or \
                'example:' in line or \
                '=>' in line:
            test_case_flag = True
        if 'Constraints:' in line or 'Variables:' in line or 'Note:' in line or \
                ('The function will' in line and problem['name'] == 'HumanEval/139') or \
                ('If the input list is empty, return 0.' in line and problem['name'] == 'HumanEval/151'):
            test_case_flag = False
        if test_case_flag:
            example_test_cases_line_list.append(line)
    reduced_description = ''
    count = 0
    for i in description.split('\n'):
        if count >= len(example_test_cases_line_list) or i != example_test_cases_line_list[count]:
            reduced_description += i + '\n'
        else:
            count += 1
    # reduced_description = '\n'.join(i for i in description.split('\n') if i not in example_test_cases_line_list)
    # string, list
    return reduced_description[:-1], example_test_cases_line_list


def pattern_match_and_regenerate_description(problem, example_test_cases_line_list, selected_spoiled_test_case, example_test_case_list, option='replace'):
    match_pattern_list = [
        r'>>> %s\(.*?\).*\n    (.*?)\n' % (problem['entry_point']),
        r'%s\(.*?\)\s*=>\s*(.*?)' % (problem['entry_point']),
        r'%s\(.*?\)\s*->\s*(.*?)' % (problem['entry_point']),
        r'Example.*?\n\s*Input:\s*(.*?)\s*\n\s*Output:(.*?)\s*',
        r'%s\(.*?\)\s*==\s*(.*?)' % (problem['entry_point']),
        r'%s\(.*?\)\s*➞\s*(.*?)' % (problem['entry_point']),
        r'For num = (.*?) the output should be (.*?).',
        r'%s\(.*?\)\s*#\s*returns\s*(.*?)' % (problem['entry_point']),
        r'%s\(.*?\)\s*==>\s*(.*?)' % ('grade_equation'),
        r'For N = (.*?), the sum of digits will be (.*?) the output should be (.*?).',
        r'%s\(.*?\)\s*returns\s*(.*?)' % (problem['entry_point']),
        r'For lst = (.*?) the output should be (.*?)',
        r'%s\((.*?)\) should return (.*?).' % (problem['entry_point']),
        r'%s\((.*?)\) = (.*?)' % (problem['entry_point']),
        r'arr = (.*?)\s*\n.*?return (.*?)',
        r'>>> %s\((.*?)\) == (.*?)' % (problem['entry_point']),
        r'For (.*?), the result should be (.*?)',
        r'%s\((.*?)\) # => (.*?)' % (problem['entry_point']),
        r'assert %s\((.*?)\)\s*=>\s*(.*?)' % ('list_sort'),
        r'operator(.*?)\s*\n\s*array = (.*?)'
    ]
    replaced_test_cases_description = ''
    selected_pattern_index = 0
    for i in range(len(match_pattern_list)):
        if re.findall(match_pattern_list[i], '\n'.join(line for line in example_test_cases_line_list), re.DOTALL):
            selected_pattern_index = i
            break
    if problem['name'] == 'HumanEval/108' or \
            problem['name'] == 'HumanEval/116' or \
            problem['name'] == 'HumanEval/128' or \
            problem['name'] == 'HumanEval/145' or \
            problem['name'] == 'HumanEval/162' or \
            problem['name'] == 'HumanEval/156':
        selected_pattern_index = 15
    if problem['name'] == 'HumanEval/109' or \
            problem['name'] == 'HumanEval/117' or \
            problem['name'] == 'HumanEval/118' or \
            problem['name'] == 'HumanEval/85' or \
            problem['name'] == 'HumanEval/77' or \
            problem['name'] == 'HumanEval/121' or \
            problem['name'] == 'HumanEval/155' or \
            problem['name'] == 'HumanEval/127':
        selected_pattern_index = 8
    if option == 'add':
        count = len(example_test_case_list) + 1
    else:
        count = 1
    for spoiled_case in selected_spoiled_test_case:
        if selected_pattern_index == 0:
            if spoiled_case['relation'] == '==':
                if problem['name'] == 'HumanEval/93' or \
                        problem['name'] == 'HumanEval/10' or \
                        problem['name'] == 'HumanEval/11' or \
                        problem['name'] == 'HumanEval/15' or \
                        problem['name'] == 'HumanEval/19' or \
                        problem['name'] == 'HumanEval/27' or \
                        problem['name'] == 'HumanEval/28' or \
                        problem['name'] == 'HumanEval/51' or \
                        problem['name'] == 'HumanEval/65' or \
                        problem['name'] == 'HumanEval/12':
                    replaced_test_cases_description += '    >>> %s(%s)\n    %s\n' % (problem['entry_point'],
                                                                                     spoiled_case['input'],
                                                                                     '\'' + spoiled_case[
                                                                                         'output'] + '\'')
                else:
                    replaced_test_cases_description += '    >>> %s(%s)\n    %s\n' % (problem['entry_point'],
                                                                                     spoiled_case['input'],
                                                                                     spoiled_case['output'])
            else:
                replaced_test_cases_description += '    >>> %s\n    %s\n' % (
                spoiled_case['relation'].replace('candidate', problem['entry_point']),
                'True')
        elif selected_pattern_index == 1:
            if spoiled_case['relation'] == '==':
                if problem['name'] == 'HumanEval/66':
                    replaced_test_cases_description += '        %s(%s) => %s\n' % (problem['entry_point'],
                                                                                   spoiled_case['input'],
                                                                                   spoiled_case['output'])
                elif problem['name'] == 'HumanEval/88':
                    replaced_test_cases_description += '    * %s(%s) => %s\n' % (problem['entry_point'],
                                                                                 spoiled_case['input'],
                                                                                 spoiled_case['output'])
                elif problem['name'] == 'HumanEval/110':
                    replaced_test_cases_description += '    %s(%s) => %s\n' % (problem['entry_point'],
                                                                                 spoiled_case['input'],
                                                                                 '\"' + spoiled_case['output'] + '\"')
                elif problem['name'] == 'HumanEval/103':
                    if spoiled_case['output'] == '-1':
                        replaced_test_cases_description += '    %s(%s) => %s\n' % (problem['entry_point'],
                                                                                   spoiled_case['input'],
                                                                                   spoiled_case['output'])
                    else:
                        replaced_test_cases_description += '    %s(%s) => %s\n' % (problem['entry_point'],
                                                                                   spoiled_case['input'],
                                                                                   '\"' + spoiled_case['output'] + '\"')
                elif problem['name'] == 'HumanEval/124':
                    replaced_test_cases_description += '    %s(%s) => %s\n\n' % (problem['entry_point'],
                                                                                 spoiled_case['input'],
                                                                                 spoiled_case['output'])
                else:
                    replaced_test_cases_description += '    %s(%s) => %s\n' % (problem['entry_point'],
                                                                               spoiled_case['input'],
                                                                               spoiled_case['output'])
        elif selected_pattern_index == 2:
            if spoiled_case['relation'] == '==':
                if problem['name'] == 'HumanEval/159':
                    replaced_test_cases_description += '    * %s(%s) -> %s\n' % (problem['entry_point'],
                                                                                 spoiled_case['input'],
                                                                                 spoiled_case['output'])
                else:

                    replaced_test_cases_description += '    %s(%s) -> %s\n' % (problem['entry_point'],
                                                                               spoiled_case['input'],
                                                                               spoiled_case['output'])
        elif selected_pattern_index == 3:
            if spoiled_case['relation'] == '==':
                if problem['name'] == 'HumanEval/122':
                    replaced_test_cases_description += '    Example %s:\n        Input: arr = %s, k =%s\n        Output: %s\n\n' % (
                    count,
                    spoiled_case['input'].split('],')[0] + ']',
                    spoiled_case['input'].split('],')[-1],
                    spoiled_case['output'])
                elif problem['name'] == 'HumanEval/143':
                    replaced_test_cases_description += '    Example %s:\n        Input: %s\n        Output: %s\n\n' % (
                    count,
                    spoiled_case['input'],
                    '\"' + spoiled_case['output'] + '\"')
                elif problem['name'] == 'HumanEval/147':
                    replaced_test_cases_description += '    Example %s:\n        Input: %s\n        Output: %s\n\n' % (
                    count,
                    'n = ' + spoiled_case['input'],
                    spoiled_case['output'])

                else:
                    replaced_test_cases_description += '    Example %s:\n        Input: %s\n        Output: %s\n\n' % (
                    count,
                    spoiled_case['input'],
                    spoiled_case['output'])
                count += 1
        elif selected_pattern_index == 4:
            if spoiled_case['relation'] == '==':
                if problem['name'] == 'HumanEval/119' or \
                        problem['name'] == 'HumanEval/140' or \
                        problem['name'] == 'HumanEval/153':
                    replaced_test_cases_description += '    %s(%s) == %s\n' % (problem['entry_point'],
                                                                               spoiled_case['input'],
                                                                               '\'' + spoiled_case['output'] + '\'')
                elif problem['name'] == 'HumanEval/158':
                    replaced_test_cases_description += '    %s(%s) == %s\n' % (problem['entry_point'],
                                                                               spoiled_case['input'],
                                                                               '\"' + spoiled_case['output'] + '\"')

                elif problem['name'] == 'HumanEval/69':
                    replaced_test_cases_description += '        %s(%s) == %s\n' % (problem['entry_point'],
                                                                                   spoiled_case['input'],
                                                                                   spoiled_case['output'])
                else:
                    replaced_test_cases_description += '    %s(%s) == %s\n' % (problem['entry_point'],
                                                                               spoiled_case['input'],
                                                                               spoiled_case['output'])
        elif selected_pattern_index == 5:
            if spoiled_case['relation'] == '==':
                if problem['name'] == 'HumanEval/72' or problem['name'] == 'HumanEval/92':
                    replaced_test_cases_description += '    %s(%s) ➞ %s\n\n' % (problem['entry_point'],
                                                                                spoiled_case['input'],
                                                                                spoiled_case['output'])
                else:
                    replaced_test_cases_description += '    %s(%s) ➞ %s\n' % (problem['entry_point'],
                                                                              spoiled_case['input'],
                                                                              spoiled_case['output'])
        elif selected_pattern_index == 6:
            if spoiled_case['relation'] == '==':
                replaced_test_cases_description += '    For num = %s the output should be %s.\n' % (
                spoiled_case['input'],
                spoiled_case['output'])
        elif selected_pattern_index == 7:
            if spoiled_case['relation'] == '==':
                replaced_test_cases_description += '    %s(%s)   # returns "%s"\n' % (problem['entry_point'],
                                                                                      spoiled_case['input'],
                                                                                      spoiled_case['output'])
        elif selected_pattern_index == 8:
            if spoiled_case['relation'] == '==':
                if problem['name'] == 'HumanEval/118' or problem['name'] == 'HumanEval/127':
                    replaced_test_cases_description += '    %s(%s) ==> %s\n' % (problem['entry_point'],
                                                                                spoiled_case['input'],
                                                                                '\"' + spoiled_case['output'] + '\"')
                elif problem['name'] == 'HumanEval/81':
                    replaced_test_cases_description += '    %s(%s) ==> %s\n' % ('grade_equation',
                                                                                spoiled_case['input'],
                                                                                spoiled_case['output'])
                elif problem['name'] == 'HumanEval/85':
                    replaced_test_cases_description += '        %s(%s) ==> %s\n' % (problem['entry_point'],
                                                                                    spoiled_case['input'],
                                                                                    spoiled_case['output'])
                elif problem['name'] == 'HumanEval/109':
                    replaced_test_cases_description += '    %s(%s)==>%s\n' % (problem['entry_point'],
                                                                                  spoiled_case['input'],
                                                                                  spoiled_case['output'])
                elif problem['name'] == 'HumanEval/155':
                    replaced_test_cases_description += '        %s(%s) ==> %s\n' % (problem['entry_point'],
                                                                                    spoiled_case['input'],
                                                                                    spoiled_case['output'])
                else:
                    replaced_test_cases_description += '    %s(%s) ==> %s\n' % (problem['entry_point'],
                                                                                spoiled_case['input'],
                                                                                spoiled_case['output'])
        elif selected_pattern_index == 9:
            if spoiled_case['relation'] == '==':
                replaced_test_cases_description += '        For N = %s, the sum of digits will be %s the output should be "%s".\n' % (
                spoiled_case['input'],
                sum([int(i) for i in spoiled_case['input']]),
                spoiled_case['output'])
        elif selected_pattern_index == 10:
            if spoiled_case['relation'] == '==':
                if problem['name'] == 'HumanEval/86' or problem['name'] == 'HumanEval/89':
                    replaced_test_cases_description += '    %s(%s) returns \'%s\'\n' % (problem['entry_point'],
                                                                                        spoiled_case['input'],
                                                                                        spoiled_case['output'])
                else:
                    replaced_test_cases_description += '    %s(%s) returns %s\n' % (problem['entry_point'],
                                                                                    spoiled_case['input'],
                                                                                    spoiled_case['output'])
        elif selected_pattern_index == 11:
            if spoiled_case['relation'] == '==':
                replaced_test_cases_description += '    For lst = %s the output should be %s\n' % (
                spoiled_case['input'],
                spoiled_case['output'])
        elif selected_pattern_index == 12:
            if spoiled_case['relation'] == '==':
                replaced_test_cases_description += '    %s(%s) should return %s.\n' % (problem['entry_point'],
                                                                                       spoiled_case['input'],
                                                                                       spoiled_case['output'])
        elif selected_pattern_index == 13:
            if spoiled_case['relation'] == '==':
                if problem['name'] == 'HumanEval/161':
                    replaced_test_cases_description += '    %s(%s) = %s\n' % (problem['entry_point'],
                                                                              spoiled_case['input'],
                                                                              '\"' + spoiled_case['output'] + '\"')
                else:

                    replaced_test_cases_description += '    %s(%s) = %s\n' % (problem['entry_point'],
                                                                              spoiled_case['input'],
                                                                              spoiled_case['output'])
        elif selected_pattern_index == 14:
            if spoiled_case['relation'] == '==':
                replaced_test_cases_description += '      arr = %s\n      return %s\n\n' % (spoiled_case['input'],
                                                                                            spoiled_case['output'])
        elif selected_pattern_index == 15:
            if spoiled_case['relation'] == '==':
                if problem['name'] == 'HumanEval/156' or problem['name'] == 'HumanEval/162':
                    replaced_test_cases_description += '    >>> %s(%s) == %s\n' % (problem['entry_point'],
                                                                                   spoiled_case['input'],
                                                                                   '\'' + spoiled_case['output'] + '\'')
                else:
                    replaced_test_cases_description += '    >>> %s(%s) == %s\n' % (problem['entry_point'],
                                                                                   spoiled_case['input'],
                                                                                   spoiled_case['output'])
        elif selected_pattern_index == 16:
            if spoiled_case['relation'] == '==':
                replaced_test_cases_description += '    For s = %s, c = %s, the result should be %s\n' % (
                spoiled_case['input'].split(',')[0],
                spoiled_case['input'].split(',')[-1],
                spoiled_case['output'])
        elif selected_pattern_index == 17:
            if spoiled_case['relation'] == '==':
                if problem['name'] == 'HumanEval/141':
                    replaced_test_cases_description += '    %s(%s) # => %s\n' % (problem['entry_point'],
                                                                                 spoiled_case['input'],
                                                                                 '\'' + spoiled_case['output'] + '\'')
                else:
                    replaced_test_cases_description += '    %s(%s) # => %s\n' % (problem['entry_point'],
                                                                                 spoiled_case['input'],
                                                                                 spoiled_case['output'])
        elif selected_pattern_index == 18:
            if spoiled_case['relation'] == '==':
                replaced_test_cases_description += '    assert list_sort(%s) => %s\n' % (spoiled_case['input'],
                                                                                         spoiled_case['output'])
        elif selected_pattern_index == 19:
            if spoiled_case['relation'] == '==':
                replaced_test_cases_description += '    operator%s\n    array = %s\n    => result = %s\n\n' % (
                spoiled_case['input'].split('], [')[0] + ']',
                '[' + spoiled_case['input'].split('], [')[-1],
                spoiled_case['output'])

    replaced_description = ''

    old_example_test_case_count = 0
    added_replaced_description_flag = False
    # print(replaced_test_cases_description)
    # if not example_test_cases_line_list and option == 'add':
    if option == 'add':
        if not example_test_cases_line_list:
            return '"""'.join(i for i in problem['prompt'].split('"""')[:-1]).rstrip() + '\n' \
                   + replaced_test_cases_description + '    """' + problem['prompt'].split('"""')[-1]
        else:
            for line in problem['prompt'].split('\n'):
                replaced_description += line + '\n'
                if line == example_test_cases_line_list[old_example_test_case_count]:
                    old_example_test_case_count += 1
                    old_example_test_case_count = min(old_example_test_case_count, len(example_test_cases_line_list)-1)
                if old_example_test_case_count == len(example_test_cases_line_list)-1 and not added_replaced_description_flag:
                    replaced_description += replaced_test_cases_description
                    added_replaced_description_flag = True

                # if old_example_test_case_count >= len(example_test_cases_line_list) or \
                #         line != example_test_cases_line_list[old_example_test_case_count]:
                #     replaced_description += line + '\n'
                # else:
                #     if not re.findall(match_pattern_list[selected_pattern_index], line, re.DOTALL) and \
                #             not added_replaced_description_flag and \
                #             (selected_pattern_index != 3):
                #         if 'xample' in line:
                #             replaced_description += line + '\n'
                #     if old_example_test_case_count == len(example_test_cases_line_list) - 1 and not added_replaced_description_flag:
                #         replaced_description += replaced_test_cases_description
                #         added_replaced_description_flag = True
                #     old_example_test_case_count += 1


        return replaced_description


    for line in problem['prompt'].split('\n'):
        if old_example_test_case_count >= len(example_test_cases_line_list) or \
                line != example_test_cases_line_list[old_example_test_case_count]:
            replaced_description += line + '\n'
        else:
            if not re.findall(match_pattern_list[selected_pattern_index], line, re.DOTALL) and \
                    not added_replaced_description_flag and \
                    (selected_pattern_index != 3):
                if 'xample' in line:
                    replaced_description += line + '\n'
            if not added_replaced_description_flag:
                replaced_description += replaced_test_cases_description
                added_replaced_description_flag = True
            old_example_test_case_count += 1

    return replaced_description


def original_description(problem):
    unspoiled_test_set = copy.deepcopy(problem['test_case'])
    example_test_case_list = get_example_test_cases(problem)
    example_test_case_index_list = []
    # filter the existing example test cases in the test case set
    for case in example_test_case_list:
        if case in unspoiled_test_set:
            example_test_case_index_list.append(problem['test_case'].index(case))
            unspoiled_test_set.remove(case)

    _, example_test_cases_line_list = reduce_description(problem)
    selected_spoiled_test_case = example_test_case_list

    return problem['prompt'], selected_spoiled_test_case, unspoiled_test_set


def replace_description(problem):
    # test case refers to unspoiled test case
    unspoiled_test_set = copy.deepcopy(problem['test_case'])
    example_test_case_list = get_example_test_cases(problem)
    example_test_case_index_list = []
    # filter the existing example test cases in the test case set
    for case in example_test_case_list:
        if case in unspoiled_test_set:
            example_test_case_index_list.append(problem['test_case'].index(case))
            unspoiled_test_set.remove(case)

    reduced_description, example_test_cases_line_list = reduce_description(problem)
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
            example_test_case_index_list.append(problem['test_case'].index(case))
            unspoiled_test_set.remove(case)

    unspoiled_test_set += example_test_case_list

    # in case certain example test cases in test case as well
    for case in selected_spoiled_test_case:
        if case in unspoiled_test_set:
            example_test_case_index_list.append(problem['test_case'].index(case))
            unspoiled_test_set.remove(case)

    # exceptional list
    if problem['name'] == 'HumanEval/32':
        return problem['prompt'], [], unspoiled_test_set
    # detect the pattern
    replaced_description = pattern_match_and_regenerate_description(problem, example_test_cases_line_list,
                                                                    selected_spoiled_test_case, example_test_case_list)

    return replaced_description, selected_spoiled_test_case, unspoiled_test_set


def add_description(problem, spoiled_number):
    # test case refers to unspoiled test case
    unspoiled_test_set = copy.deepcopy(problem['test_case'])
    example_test_case_list = get_example_test_cases(problem)
    example_test_case_index_list = []
    # filter the existing example test cases in the test case set
    for case in example_test_case_list:
        if case in unspoiled_test_set:
            example_test_case_index_list.append(problem['test_case'].index(case))
            unspoiled_test_set.remove(case)

    reduced_description, example_test_cases_line_list = reduce_description(problem)
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

    # exceptional list
    if problem['name'] == 'HumanEval/32':
        return problem['prompt'], [], unspoiled_test_set
    # detect the pattern
    replaced_description = pattern_match_and_regenerate_description(problem, example_test_cases_line_list,
                                                                    selected_spoiled_test_case, example_test_case_list, 'add')
    selected_spoiled_test_case = example_test_case_list + selected_spoiled_test_case
    return replaced_description, selected_spoiled_test_case, unspoiled_test_set


def description_2_code_seperate(problem, model, topn, temperature):
    unspoiled_test_set = copy.deepcopy(problem['test_case'])
    example_test_case_list = get_example_test_cases(problem)
    example_test_case_index_list = []
    # filter the existing example test cases in the test case set
    for case in example_test_case_list:
        if case in unspoiled_test_set:
            example_test_case_index_list.append(problem['test_case'].index(case))
            unspoiled_test_set.remove(case)

    reduced_description, example_test_cases_line_list = reduce_description(problem)
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


def HumanEval_experiment(dataset, option, model, sequence, topn=1, temperature=1.0, data_path='../alpha_code/'):
    openai.api_key = ''
    log_file = './log/%s_dataset_%s_model_%s_topn_%s_temperature_%s.log_%s' % \
                   (option, dataset, model, topn, temperature, sequence)
    problem_list = []
    with open(data_path + 'HumanEval/HumanEval_new.jsonl', 'r') as f:
        for line in f.readlines():
            problem_list.append(json.loads(line))
    names = set()
    if os.path.exists(log_file):
        with open(log_file, 'r') as f:
            for line in f:
                content = json.loads(line)
                names.add(content['name'])

    for problem in problem_list:
        if problem['name'] in names:
            continue
        print('----------------------problem name: %s--------------------------------' % (problem['name']), flush=True)
        print('using %s to generate response' % (model), flush=True)
        selected_spoiled_test_case, unspoiled_test_set = [], []
        try:
            if 'original' in option:
                description, selected_spoiled_test_case, unspoiled_test_set = original_description(problem)
                response_list = description_2_code(description, model, topn, temperature)
            elif 'seperate' in option:
                responses, selected_spoiled_test_case, unspoiled_test_set = description_2_code_seperate(problem, model, topn, temperature)
            elif 'replace' in option:
                description, selected_spoiled_test_case, unspoiled_test_set = replace_description(problem)
                response_list = description_2_code(description, model, topn, temperature)
            elif 'add' in option:
                if not option.replace('add', ''):
                    spoiled_number = 1
                else:
                    spoiled_number = int(option.replace('add', ''))
                description, selected_spoiled_test_case, unspoiled_test_set = add_description(problem, spoiled_number)
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
    print('Done!', flush=True)


def check_data():
    # not useful
    problem_list = []
    with open('../alpha_code/HumanEval/HumanEval_new.jsonl', 'r') as f:
        for line in f.readlines():
            problem_list.append(json.loads(line))

    # start from 66
    # Need explaination 68, 72, 75, 105, 107, 109, 112(need further pattern), 115， 120， 122， 123, 129, 130, 143, 147, 160
    # dataset problem 116
    # formal match 91 93 99 100 104 113 139
    # solution problem: 116

    # replace special case: 32 105
    for problem in problem_list:
        print(problem['name'])
        print(problem['prompt'])
        print('-------------')

        replaced_description, selected_spoiled_test_case, unspoiled_test_set = add_description(problem, 1)
        print(replaced_description)
        print(selected_spoiled_test_case)
        print(unspoiled_test_set)


        # check the whether repeated in list, using following line
        for i in selected_spoiled_test_case:
            if i in unspoiled_test_set:
                print('Error')
        print(len(list(set(json.dumps(i) for i in unspoiled_test_set))) == len(unspoiled_test_set))
        a = input()
        # a = input()


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
#     if args.dataset == 'HumanEval':
#         HumanEval_experiment(args.dataset, args.option, args.model, args.sequence, args.topn, args.temperature, data_path)