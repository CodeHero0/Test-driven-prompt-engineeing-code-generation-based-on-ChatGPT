import argparse
import json
import os
import re
import subprocess
import numpy as np
import platform


def response_2_code(response):
    code_template = re.compile('```.*\n([\s\S]+?)\n```', re.M)
    code = code_template.findall(response)
    if len(code) > 0:
        return code[-1]
    else:
        return ''


def solution_evaluation_HumanEval(solution, test_cases, demo_file, call_demo_file, entry_point, time_limit):
    passed_case = []
    case_status = []
    with open(demo_file, 'w', encoding='UTF-8') as f:
        f.write(solution)
    for i in range(len(test_cases)):
        if test_cases[i]['relation'] == '==':
            with open(call_demo_file, 'w') as f:
                f.write('from %s import %s\nprint(%s(%s))' % (
                    demo_file.split('.')[0],
                    entry_point,
                    entry_point,
                    test_cases[i]['input']
                ))
            try:
                output = subprocess.run(["python", call_demo_file], capture_output=True, text=True, timeout=time_limit)

            except subprocess.TimeoutExpired as e:
                print(e, flush=True)
                case_status.append('Timeout')
                continue
            except Exception as e:
                print(e, flush=True)
                case_status.append('Exception')
                continue
            if output.returncode != 0:
                case_status.append('execution error: %s' % output.returncode)
            else:
                case_status.append(output.stdout.strip())
            if test_cases[i]['output'].strip() == output.stdout.strip():
                passed_case.append(i)
        else:
            if '$input$' in test_cases[i]['relation'] or '$demo$' in test_cases[i]['relation']:
                with open(call_demo_file, 'w') as f:
                    f.write('from %s import %s\n%s' % (
                        demo_file.split('.')[0],
                        entry_point,
                        test_cases[i]['relation'].replace('$input$', str(test_cases[i]['input'])).replace('$demo$', demo_file.split('.')[0])
                    ))
            else:
                with open(call_demo_file, 'w') as f:
                    f.write('from %s import %s\nprint(%s)' % (demo_file.split('.')[0],
                        entry_point,
                        test_cases[i]['relation'].replace('candidate', entry_point)))
                try:
                    output = subprocess.run(["python", call_demo_file], capture_output=True, text=True, timeout=time_limit)

                except subprocess.TimeoutExpired as e:
                    print(e, flush=True)
                    case_status.append('Timeout')
                    continue
                except Exception as e:
                    print(e, flush=True)
                    case_status.append('Exception')
                    continue
                if output.returncode != 0:
                    case_status.append('execution error: %s' % output.returncode)
                else:
                    case_status.append(output.stdout.strip())
                if output.stdout.strip() == 'True':
                    passed_case.append(i)

    pass_num = len(passed_case)
    print('%s/%s pass.' % (pass_num, len(test_cases)), flush=True)
    return passed_case, case_status


def solution_evaluation_HumanEval_plus(solution, test_cases, demo_file, call_demo_file, entry_point, time_limit, atol):
    passed_case = []
    case_status = []
    with open(demo_file, 'w', encoding='UTF-8') as f:
        f.write(solution)
    for i in range(len(test_cases)):
        with open(call_demo_file, 'w') as f:
            f.write('from %s import %s\nprint(%s(%s))' % (
                demo_file.split('.')[0],
                entry_point,
                entry_point,
                test_cases[i]['input']
            ))
        try:
            output = subprocess.run(["python", call_demo_file], capture_output=True, text=True, timeout=time_limit)
        except subprocess.TimeoutExpired as e:
            print(e, flush=True)
            case_status.append('Timeout')
            continue
        except Exception as e:
            print(e, flush=True)
            case_status.append('Exception')
            continue
        if output.returncode != 0:
            case_status.append('execution error: %s' % output.returncode)
        else:
            case_status.append(output.stdout.strip())
        # special for HumanEval plus
        if atol == 0:
            if test_cases[i]['output'].strip() == output.stdout.strip():
                passed_case.append(i)
        else:
            try:
                if abs(float(test_cases[i]['output'].strip()) - float(output.stdout.strip())) <= atol:
                    passed_case.append(i)
            except:
                pass

    pass_num = len(passed_case)
    print('%s/%s pass.' % (pass_num, len(test_cases)), flush=True)
    return passed_case, case_status


def analyze_process_HumanEval(log_file, data_path, demo_file, call_demo_file, option):
    problem_dic = {}
    names = []
    problem_list = []
    # res_list = []
    with open(data_path + 'HumanEval/HumanEval_new.jsonl', 'r') as f:
        for line in f.readlines():
            problem_list.append(json.loads(line))

    for i in range(len(problem_list)):
        if not problem_list[i]['name'] in names:
            problem_dic[problem_list[i]['name']] = {
                'name': problem_list[i]['name'],
                'index_num': i,
                'time_limit': int(3) # by default
            }
    with open(log_file, 'r') as f:
        for line_number, line in enumerate(f.readlines(), start=1):
            if option == 'reduce':
                if line_number % 2 == 0:
                    continue
            elif option == 'seperate':
                if line_number % 2 == 1:
                    continue
            content = json.loads(line)
            name = content['name']
            if name in names:
                continue
            index = content['index']
            response = content['response']
            if index == 0:
                print('----------------------problem name: %s--------------------------------' % (name),
                      flush=True)
            # initialize
            if 'code_candidates' not in problem_dic[name]:
                problem_dic[name]['response_candidates'] = []
                problem_dic[name]['code_candidates'] = []
            print('generate code from response', flush=True)

            if 'selected_spoiled_test_case' in content and 'unspoiled_test_set' in content:
                selected_spoiled_test_case = content['selected_spoiled_test_case']
                unspoiled_test_set = content['unspoiled_test_set']
            else:
                selected_spoiled_test_case = []
                unspoiled_test_set = []

            # load from code_contest dataset
            problem = problem_list[problem_dic[name]['index_num']]
            # test_set = problem['test_case']
            test_set = selected_spoiled_test_case + unspoiled_test_set
            # get code from response
            code = response_2_code(response)
            # use code to run test cases
            time_limit = problem_dic[name]['time_limit']
            test_case_solved = solution_evaluation_HumanEval(code, test_set, demo_file, call_demo_file,
                                                             problem['entry_point'], time_limit)
            problem_dic[name]['response_candidates'].append(response)

            res = {
                'code': code,
                'index': index,
                'passed_case': test_case_solved[0],
                'case_status': test_case_solved[1],
                'selected_spoiled_test_case': selected_spoiled_test_case,
                'unspoiled_test_set': unspoiled_test_set
            }
            problem_dic[name]['code_candidates'].append(res)
            # json_str = json.dumps(problem_dic[name])
            # with open('./log/record/%s' % (log_file.split('/')[1]), 'a') as f:
            #     f.write(json_str + '\n')
            # problem_dic.pop(name)
    return problem_dic


def analyze_process_HumanEval_plus(log_file, data_path, demo_file, call_demo_file, option, mini=False):
    problem_dic = {}
    names = []
    problem_list = []
    if mini:
        with open(data_path + 'HumanEval/HumanEval_plus_mini.jsonl', 'r') as f:
            for line in f.readlines():
                problem_list.append(json.loads(line))
    else:
        with open(data_path + 'HumanEval/HumanEval_plus.jsonl', 'r') as f:
            for line in f.readlines():
                problem_list.append(json.loads(line))

    for i in range(len(problem_list)):
        if not problem_list[i]['name'] in names:
            problem_dic[problem_list[i]['name']] = {
                'name': problem_list[i]['name'],
                'index_num': i,
                'time_limit': int(3)  # by default
            }
    with open(log_file, 'r') as f:
        for line_number, line in enumerate(f.readlines(), start=1):
            if option == 'reduce':
                if line_number % 2 == 0:
                    continue
            elif option == 'seperate':
                if line_number % 2 == 1:
                    continue

            content = json.loads(line)
            name = content['name']
            if name in names:
                continue
            index = content['index']
            response = content['response']
            if index == 0:
                print('----------------------problem name: %s--------------------------------' % (name),
                      flush=True)
            # initialize
            if 'code_candidates' not in problem_dic[name]:
                problem_dic[name]['response_candidates'] = []
                problem_dic[name]['code_candidates'] = []
            print('generate code from response', flush=True)

            if 'selected_spoiled_test_case' in content and 'unspoiled_test_set' in content:
                selected_spoiled_test_case = content['selected_spoiled_test_case']
                unspoiled_test_set = content['unspoiled_test_set']
            else:
                selected_spoiled_test_case = []
                unspoiled_test_set = []

            # load from code_contest dataset
            problem = problem_list[problem_dic[name]['index_num']]
            # test_set = problem['test_case']
            test_set = selected_spoiled_test_case + unspoiled_test_set
            # get code from response
            code = response_2_code(response)
            # use code to run test cases
            time_limit = problem_dic[name]['time_limit']
            test_case_solved = solution_evaluation_HumanEval(code, test_set, demo_file, call_demo_file,
                                                             problem['entry_point'], time_limit)
            problem_dic[name]['response_candidates'].append(response)

            # plus
            test_set_plus = problem['test_case_plus']
            test_case_plus_solved = solution_evaluation_HumanEval_plus(code, test_set_plus, demo_file, call_demo_file,
                                                             problem['entry_point'], time_limit, problem['atol'])

            res = {
                'code': code,
                'index': index,
                'passed_case': test_case_solved[0],
                'case_status': test_case_solved[1],
                'selected_spoiled_test_case': selected_spoiled_test_case,
                'unspoiled_test_set': unspoiled_test_set,
                'passed_case_plus': test_case_plus_solved[0],
                'case_status_plus': test_case_plus_solved[1]
            }
            problem_dic[name]['code_candidates'].append(res)

        return problem_dic


def solution_evaluation(solution, test_cases, demo_file, time_limit):
    passed_case = []
    case_status = []
    with open(demo_file, 'w') as f:
        f.write(solution)
    for i in range(len(test_cases)):
        try:
            output = subprocess.run(["python", demo_file], capture_output=True, text=True,
                                    input=test_cases[i]['input'], timeout=time_limit)
        except subprocess.TimeoutExpired as e:
            print(e, flush=True)
            case_status.append('timeout')
            continue
        except Exception as e:
            print(e, flush=True)
            case_status.append('exception')
            continue
        if output.returncode != 0:
            case_status.append('execution error: %s' % output.returncode)
        else:
            case_status.append(output.stdout.strip())
        if test_cases[i]['output'].strip() == output.stdout.strip():
            passed_case.append(i)

    pass_num = len(passed_case)
    print('%s/%s pass.' % (pass_num, len(test_cases)), flush=True)
    return passed_case, case_status


def analyze_process_APPS(log_file, demo_file):
    problem_dic = {}
    names = []

    data_count = 0
    dir_num = 0
    non_EN_problem = ['0051', '0106', '0190', '0403', '0412', '0608', '0723', '0956', '1093', '1363', '1500',
                      '1530', '1613', '1781', '1827', '2183', '2322', '3083']
    while data_count <= 500:
        dirname = str(dir_num).zfill(4)
        if data_count == 500:
            break
        if dirname not in non_EN_problem:
            problem_dic[dirname] = {
                'name': dirname,
                'index_num': data_count,
                'time_limit': int(3)  # by default
            }
            data_count += 1
        dir_num += 1

    with open(log_file, 'r') as f:
        for line in f.readlines():
            content = json.loads(line)
            name = content['name']
            if name in names:
                continue
            index = content['index']
            response = content['response']
            if index == 0:
                print('----------------------problem name: %s--------------------------------' % (name),
                      flush=True)
            # initialize
            if 'code_candidates' not in problem_dic[name]:
                problem_dic[name]['response_candidates'] = []
                problem_dic[name]['code_candidates'] = []
            print('generate code from response', flush=True)

            if 'selected_spoiled_test_case' in content and 'unspoiled_test_set' in content:
                selected_spoiled_test_case = content['selected_spoiled_test_case']
                unspoiled_test_set = content['unspoiled_test_set']
            else:
                selected_spoiled_test_case = []
                unspoiled_test_set = []

            test_set = selected_spoiled_test_case + unspoiled_test_set
            # get code from response
            code = response_2_code(response)
            # use code to run test cases
            time_limit = problem_dic[name]['time_limit']
            test_case_solved = solution_evaluation(code, test_set, demo_file, time_limit)
            problem_dic[name]['response_candidates'].append(response)

            res = {
                'code': code,
                'index': index,
                'passed_case': test_case_solved[0],
                'case_status': test_case_solved[1],
                'selected_spoiled_test_case': selected_spoiled_test_case,
                'unspoiled_test_set': unspoiled_test_set
            }
            problem_dic[name]['code_candidates'].append(res)

    return problem_dic


def initialize_demo_file(dataset):
    demo_file = 'demo.py'
    call_demo_file = 'call_demo.py'
    if 'HumanEval' in dataset:
        count = 0
        while os.path.exists(demo_file) or os.path.exists(call_demo_file):
            demo_file = 'demo_%s.py' % count
            call_demo_file = 'call_demo_%s.py' % count
            count += 1
        return demo_file, call_demo_file

    else:
        count = 0
        while os.path.exists(demo_file):
            demo_file = 'demo_%s.py' % count
            count += 1

        return demo_file, call_demo_file


def analyze(dataset, option, model, topn, temperature, data_path, total_number=5):
    problem_dic_list = []
    # run the code on the test cases
    demo_file, call_demo_file = initialize_demo_file(dataset)
    for i in range(total_number):
        if option == 'reduce':
            tmp_option = 'seperate'
        else:
            tmp_option = option
        if dataset == 'HumanEval_plus' or dataset == 'HumanEval_plus_mini':
            target_log_file = 'log/%s_dataset_%s_model_%s_topn_%s_temperature_%s.log_%s' % \
                       (tmp_option, 'HumanEval', model, topn, temperature, i)
        else:
            target_log_file = '../transfer_file/%s_dataset_%s_model_%s_topn_%s_temperature_%s.log_%s' % \
                       (tmp_option, dataset, model, topn, temperature, i)
            # target_log_file = 'log/%s_dataset_%s_model_%s_topn_%s_temperature_%s.log_%s' % \
            #            (tmp_option, dataset, model, topn, temperature, i)

        if dataset == 'HumanEval':
            problem_dic = analyze_process_HumanEval(target_log_file, data_path, demo_file, call_demo_file, option)
        elif dataset == 'HumanEval_plus':
            problem_dic = analyze_process_HumanEval_plus(target_log_file, data_path, demo_file, call_demo_file, option)
        elif dataset == 'HumanEval_plus_mini':
            problem_dic = analyze_process_HumanEval_plus(target_log_file, data_path, demo_file, call_demo_file, option, True)
        elif dataset == 'APPS':
            problem_dic = analyze_process_APPS(target_log_file, demo_file)
        else:
            problem_dic = {}
        problem_dic_list.append(problem_dic)
        # with open('tmp.json', 'a', encoding='utf-8') as f:
        #     json_str = json.dumps(problem_dic)
        #     f.write(json_str + '\n')
    log_file = 'log/intermediate_result/%s_dataset_%s_model_%s_topn_%s_temperature_%s.json' % \
                   (option, dataset, model, topn, temperature)
    if not os.path.exists('log/intermediate_result/'):
        os.makedirs('log/intermediate_result/')

    if option == 'seperate':
        # passed_spoiled_unspoiled_cases_dic_1 = {}
        passed_spoiled_unspoiled_cases_dic_2 = {}
        # record the spoiled and unspoiled test cases
        for i in range(total_number):
            for key in problem_dic_list[i]:
                test_set = problem_dic_list[i][key]['code_candidates'][0]['selected_spoiled_test_case'] + \
                           problem_dic_list[i][key]['code_candidates'][0]['unspoiled_test_set']
                selected_spoiled_test_case = []
                unspoiled_test_set = []

                for case in problem_dic_list[i][key]['code_candidates'][0]['selected_spoiled_test_case']:
                    selected_spoiled_test_case.append(test_set.index(case))
                for case in problem_dic_list[i][key]['code_candidates'][0]['unspoiled_test_set']:
                    unspoiled_test_set.append(test_set.index(case))

                # # reduced
                # if key not in passed_spoiled_unspoiled_cases_dic_1:
                #     passed_spoiled_unspoiled_cases_dic_1[key] = {
                #         'passed_case': [problem_dic_list[i][key]['code_candidates'][0]['passed_case']],
                #         'selected_spoiled_test_case': [],
                #         'unspoiled_test_set': selected_spoiled_test_case + unspoiled_test_set
                #     }
                # else:
                #     passed_spoiled_unspoiled_cases_dic_1[key]['passed_case'].append(
                #         problem_dic_list[i][key]['code_candidates'][0]['passed_case'])

                # seperate request
                if key not in passed_spoiled_unspoiled_cases_dic_2:
                    passed_spoiled_unspoiled_cases_dic_2[key] = {
                        'passed_case': [problem_dic_list[i][key]['code_candidates'][0]['passed_case']],
                        'selected_spoiled_test_case': selected_spoiled_test_case,
                        'unspoiled_test_set': unspoiled_test_set
                    }
                else:
                    passed_spoiled_unspoiled_cases_dic_2[key]['passed_case'].append(
                        problem_dic_list[i][key]['code_candidates'][0]['passed_case'])


        # count the overall, spoiled, and unspoiled passed test case
        # pass_rate_dic_1 = {}
        pass_rate_dic_2 = {}
        # for key in passed_spoiled_unspoiled_cases_dic_1:
        #     for i in range(len(passed_spoiled_unspoiled_cases_dic_1[key]['passed_case'])):
        #         spoiled_cases = []
        #         unspoiled_cases = []
        #         for index in passed_spoiled_unspoiled_cases_dic_1[key]['passed_case'][i]:
        #             if index in passed_spoiled_unspoiled_cases_dic_1[key]['selected_spoiled_test_case']:
        #                 spoiled_cases.append(index)
        #             if index in passed_spoiled_unspoiled_cases_dic_1[key]['unspoiled_test_set']:
        #                 unspoiled_cases.append(index)
        #         if len(passed_spoiled_unspoiled_cases_dic_1[key]['selected_spoiled_test_case']) != 0:
        #             spoiled_pass_rate = len(spoiled_cases)/len(passed_spoiled_unspoiled_cases_dic_1[key]['selected_spoiled_test_case'])
        #         else:
        #             spoiled_pass_rate = -1
        #         if len(passed_spoiled_unspoiled_cases_dic_1[key]['unspoiled_test_set']) != 0:
        #             unspoiled_pass_rate = len(unspoiled_cases) / len(
        #                 passed_spoiled_unspoiled_cases_dic_1[key]['unspoiled_test_set'])
        #         else:
        #             unspoiled_pass_rate = -1
        #         if (len(passed_spoiled_unspoiled_cases_dic_1[key]['selected_spoiled_test_case']) +
        #                              len(passed_spoiled_unspoiled_cases_dic_1[key]['unspoiled_test_set'])) != 0:
        #             overall_pass_rate = (len(spoiled_cases) + len(unspoiled_cases)) / \
        #                                 (len(passed_spoiled_unspoiled_cases_dic_1[key]['selected_spoiled_test_case']) +
        #                                  len(passed_spoiled_unspoiled_cases_dic_1[key]['unspoiled_test_set']))
        #         else:
        #             overall_pass_rate = -1
        #
        #         if key not in pass_rate_dic_1:
        #             pass_rate_dic_1[key] = {
        #                 'spoiled_pass_rate': [spoiled_pass_rate],
        #                 'unspoiled_pass_rate': [unspoiled_pass_rate],
        #                 'overall_pass_rate': [overall_pass_rate]
        #             }
        #         else:
        #             pass_rate_dic_1[key]['spoiled_pass_rate'].append(spoiled_pass_rate)
        #             pass_rate_dic_1[key]['unspoiled_pass_rate'].append(unspoiled_pass_rate)
        #             pass_rate_dic_1[key]['overall_pass_rate'].append(overall_pass_rate)


        for key in passed_spoiled_unspoiled_cases_dic_2:
            for i in range(len(passed_spoiled_unspoiled_cases_dic_2[key]['passed_case'])):
                spoiled_cases = []
                unspoiled_cases = []
                for index in passed_spoiled_unspoiled_cases_dic_2[key]['passed_case'][i]:
                    if index in passed_spoiled_unspoiled_cases_dic_2[key]['selected_spoiled_test_case']:
                        spoiled_cases.append(index)
                    if index in passed_spoiled_unspoiled_cases_dic_2[key]['unspoiled_test_set']:
                        unspoiled_cases.append(index)
                if len(passed_spoiled_unspoiled_cases_dic_2[key]['selected_spoiled_test_case']) != 0:
                    spoiled_pass_rate = len(spoiled_cases)/len(passed_spoiled_unspoiled_cases_dic_2[key]['selected_spoiled_test_case'])
                else:
                    spoiled_pass_rate = -1
                if len(passed_spoiled_unspoiled_cases_dic_2[key]['unspoiled_test_set']) != 0:
                    unspoiled_pass_rate = len(unspoiled_cases) / len(
                        passed_spoiled_unspoiled_cases_dic_2[key]['unspoiled_test_set'])
                else:
                    unspoiled_pass_rate = -1
                if (len(passed_spoiled_unspoiled_cases_dic_2[key]['selected_spoiled_test_case']) +
                                     len(passed_spoiled_unspoiled_cases_dic_2[key]['unspoiled_test_set'])) != 0:
                    overall_pass_rate = (len(spoiled_cases) + len(unspoiled_cases)) / \
                                        (len(passed_spoiled_unspoiled_cases_dic_2[key]['selected_spoiled_test_case']) +
                                         len(passed_spoiled_unspoiled_cases_dic_2[key]['unspoiled_test_set']))
                else:
                    overall_pass_rate = -1


                if key not in pass_rate_dic_2:
                    pass_rate_dic_2[key] = {
                        'spoiled_pass_rate': [spoiled_pass_rate],
                        'unspoiled_pass_rate': [unspoiled_pass_rate],
                        'overall_pass_rate': [overall_pass_rate]
                    }
                else:
                    pass_rate_dic_2[key]['spoiled_pass_rate'].append(spoiled_pass_rate)
                    pass_rate_dic_2[key]['unspoiled_pass_rate'].append(unspoiled_pass_rate)
                    pass_rate_dic_2[key]['overall_pass_rate'].append(overall_pass_rate)

        if dataset == 'HumanEval_plus_mini' or dataset == 'HumanEval_plus':
            for i in range(total_number):
                for key in problem_dic_list[i]:
                    # reduced
                    # if len(problem_dic_list[i][key]['code_candidates'][0]['case_status_plus']) != 0:
                    #     plus_pass_rate1 = len(problem_dic_list[i][key]['code_candidates'][0]['passed_case_plus'])/ \
                    #                      len(problem_dic_list[i][key]['code_candidates'][0]['case_status_plus'])
                    # else:
                    #     plus_pass_rate1 = -1
                    #
                    # if 'plus_pass_rate' not in pass_rate_dic_1[key]:
                    #     pass_rate_dic_1[key]['plus_pass_rate'] = [plus_pass_rate1]
                    # else:
                    #     pass_rate_dic_1[key]['plus_pass_rate'].append(plus_pass_rate1)

                    # seperate
                    if len(problem_dic_list[i][key]['code_candidates'][0]['case_status_plus']) != 0:
                        plus_pass_rate2 = len(problem_dic_list[i][key]['code_candidates'][0]['passed_case_plus'])/ \
                                         len(problem_dic_list[i][key]['code_candidates'][0]['case_status_plus'])
                    else:
                        plus_pass_rate2 = -1

                    if 'plus_pass_rate' not in pass_rate_dic_2[key]:
                        pass_rate_dic_2[key]['plus_pass_rate'] = [plus_pass_rate2]
                    else:
                        pass_rate_dic_2[key]['plus_pass_rate'].append(plus_pass_rate2)

        res_dic = {
            'problem_dic_list': problem_dic_list,
            # 'passed_spoiled_unspoiled_cases_dic_1': passed_spoiled_unspoiled_cases_dic_1,
            # 'pass_rate_dic_1': pass_rate_dic_1,
            'passed_spoiled_unspoiled_cases_dic': passed_spoiled_unspoiled_cases_dic_2,
            'pass_rate_dic': pass_rate_dic_2
        }

    elif option == 'reduce':
        passed_spoiled_unspoiled_cases_dic_1 = {}
        for i in range(total_number):
            for key in problem_dic_list[i]:
                test_set = problem_dic_list[i][key]['code_candidates'][0]['selected_spoiled_test_case'] + \
                           problem_dic_list[i][key]['code_candidates'][0]['unspoiled_test_set']
                selected_spoiled_test_case = []
                unspoiled_test_set = []

                for case in problem_dic_list[i][key]['code_candidates'][0]['selected_spoiled_test_case']:
                    selected_spoiled_test_case.append(test_set.index(case))
                for case in problem_dic_list[i][key]['code_candidates'][0]['unspoiled_test_set']:
                    unspoiled_test_set.append(test_set.index(case))

                # # reduced
                if key not in passed_spoiled_unspoiled_cases_dic_1:
                    passed_spoiled_unspoiled_cases_dic_1[key] = {
                        'passed_case': [problem_dic_list[i][key]['code_candidates'][0]['passed_case']],
                        'selected_spoiled_test_case': [],
                        'unspoiled_test_set': selected_spoiled_test_case + unspoiled_test_set
                    }
                else:
                    passed_spoiled_unspoiled_cases_dic_1[key]['passed_case'].append(
                        problem_dic_list[i][key]['code_candidates'][0]['passed_case'])

        pass_rate_dic_1 = {}
        for key in passed_spoiled_unspoiled_cases_dic_1:
            for i in range(len(passed_spoiled_unspoiled_cases_dic_1[key]['passed_case'])):
                spoiled_cases = []
                unspoiled_cases = []
                for index in passed_spoiled_unspoiled_cases_dic_1[key]['passed_case'][i]:
                    if index in passed_spoiled_unspoiled_cases_dic_1[key]['selected_spoiled_test_case']:
                        spoiled_cases.append(index)
                    if index in passed_spoiled_unspoiled_cases_dic_1[key]['unspoiled_test_set']:
                        unspoiled_cases.append(index)
                if len(passed_spoiled_unspoiled_cases_dic_1[key]['selected_spoiled_test_case']) != 0:
                    spoiled_pass_rate = len(spoiled_cases)/len(passed_spoiled_unspoiled_cases_dic_1[key]['selected_spoiled_test_case'])
                else:
                    spoiled_pass_rate = -1
                if len(passed_spoiled_unspoiled_cases_dic_1[key]['unspoiled_test_set']) != 0:
                    unspoiled_pass_rate = len(unspoiled_cases) / len(
                        passed_spoiled_unspoiled_cases_dic_1[key]['unspoiled_test_set'])
                else:
                    unspoiled_pass_rate = -1
                if (len(passed_spoiled_unspoiled_cases_dic_1[key]['selected_spoiled_test_case']) +
                                     len(passed_spoiled_unspoiled_cases_dic_1[key]['unspoiled_test_set'])) != 0:
                    overall_pass_rate = (len(spoiled_cases) + len(unspoiled_cases)) / \
                                        (len(passed_spoiled_unspoiled_cases_dic_1[key]['selected_spoiled_test_case']) +
                                         len(passed_spoiled_unspoiled_cases_dic_1[key]['unspoiled_test_set']))
                else:
                    overall_pass_rate = -1

                if key not in pass_rate_dic_1:
                    pass_rate_dic_1[key] = {
                        'spoiled_pass_rate': [spoiled_pass_rate],
                        'unspoiled_pass_rate': [unspoiled_pass_rate],
                        'overall_pass_rate': [overall_pass_rate]
                    }
                else:
                    pass_rate_dic_1[key]['spoiled_pass_rate'].append(spoiled_pass_rate)
                    pass_rate_dic_1[key]['unspoiled_pass_rate'].append(unspoiled_pass_rate)
                    pass_rate_dic_1[key]['overall_pass_rate'].append(overall_pass_rate)

        if dataset == 'HumanEval_plus_mini' or dataset == 'HumanEval_plus':
            for i in range(total_number):
                for key in problem_dic_list[i]:
                    # reduced
                    if len(problem_dic_list[i][key]['code_candidates'][0]['case_status_plus']) != 0:
                        plus_pass_rate1 = len(problem_dic_list[i][key]['code_candidates'][0]['passed_case_plus'])/ \
                                         len(problem_dic_list[i][key]['code_candidates'][0]['case_status_plus'])
                    else:
                        plus_pass_rate1 = -1

                    if 'plus_pass_rate' not in pass_rate_dic_1[key]:
                        pass_rate_dic_1[key]['plus_pass_rate'] = [plus_pass_rate1]
                    else:
                        pass_rate_dic_1[key]['plus_pass_rate'].append(plus_pass_rate1)

        res_dic = {
            'problem_dic_list': problem_dic_list,
            'passed_spoiled_unspoiled_cases_dic': passed_spoiled_unspoiled_cases_dic_1,
            'pass_rate_dic': pass_rate_dic_1,
        }

    else:
        passed_spoiled_unspoiled_cases_dic = {}
        # record the spoiled and unspoiled test cases
        for i in range(total_number): # i is the order of attempts (total is five)
            for key in problem_dic_list[i]: # for every problem in problem list
                test_set = problem_dic_list[i][key]['code_candidates'][0]['selected_spoiled_test_case'] + \
                           problem_dic_list[i][key]['code_candidates'][0]['unspoiled_test_set']
                selected_spoiled_test_case = []
                unspoiled_test_set = []
                for case in problem_dic_list[i][key]['code_candidates'][0]['selected_spoiled_test_case']:
                    selected_spoiled_test_case.append(test_set.index(case))
                for case in problem_dic_list[i][key]['code_candidates'][0]['unspoiled_test_set']:
                    unspoiled_test_set.append(test_set.index(case))
                if key not in passed_spoiled_unspoiled_cases_dic:
                    passed_spoiled_unspoiled_cases_dic[key] = {
                        'passed_case': [problem_dic_list[i][key]['code_candidates'][0]['passed_case']],
                        'selected_spoiled_test_case': selected_spoiled_test_case,
                        'unspoiled_test_set': unspoiled_test_set
                    }
                else:
                    passed_spoiled_unspoiled_cases_dic[key]['passed_case'].append(
                        problem_dic_list[i][key]['code_candidates'][0]['passed_case'])

        # count the overall, spoiled, and unspoiled passed test case
        # if plus exist, count plus passed test case as well
        pass_rate_dic = {}

        for key in passed_spoiled_unspoiled_cases_dic:
            for i in range(len(passed_spoiled_unspoiled_cases_dic[key]['passed_case'])):
                spoiled_cases = []
                unspoiled_cases = []
                for index in passed_spoiled_unspoiled_cases_dic[key]['passed_case'][i]:
                    if index in passed_spoiled_unspoiled_cases_dic[key]['selected_spoiled_test_case']:
                        spoiled_cases.append(index)
                    if index in passed_spoiled_unspoiled_cases_dic[key]['unspoiled_test_set']:
                        unspoiled_cases.append(index)
                if len(passed_spoiled_unspoiled_cases_dic[key]['selected_spoiled_test_case']) != 0:
                    spoiled_pass_rate = len(spoiled_cases)/len(passed_spoiled_unspoiled_cases_dic[key]['selected_spoiled_test_case'])
                else:
                    spoiled_pass_rate = -1
                if len(passed_spoiled_unspoiled_cases_dic[key]['unspoiled_test_set']) != 0:
                    unspoiled_pass_rate = len(unspoiled_cases) / len(
                        passed_spoiled_unspoiled_cases_dic[key]['unspoiled_test_set'])
                else:
                    unspoiled_pass_rate = -1
                if (len(passed_spoiled_unspoiled_cases_dic[key]['selected_spoiled_test_case']) +
                                     len(passed_spoiled_unspoiled_cases_dic[key]['unspoiled_test_set'])) != 0:
                    overall_pass_rate = (len(spoiled_cases) + len(unspoiled_cases)) / \
                                        (len(passed_spoiled_unspoiled_cases_dic[key]['selected_spoiled_test_case']) +
                                         len(passed_spoiled_unspoiled_cases_dic[key]['unspoiled_test_set']))
                else:
                    overall_pass_rate = -1


                if key not in pass_rate_dic:
                    pass_rate_dic[key] = {
                        'spoiled_pass_rate': [spoiled_pass_rate],
                        'unspoiled_pass_rate': [unspoiled_pass_rate],
                        'overall_pass_rate': [overall_pass_rate]
                    }
                else:
                    pass_rate_dic[key]['spoiled_pass_rate'].append(spoiled_pass_rate)
                    pass_rate_dic[key]['unspoiled_pass_rate'].append(unspoiled_pass_rate)
                    pass_rate_dic[key]['overall_pass_rate'].append(overall_pass_rate)

        if dataset == 'HumanEval_plus_mini' or dataset == 'HumanEval_plus':
            for i in range(total_number):
                for key in problem_dic_list[i]:
                    if len(problem_dic_list[i][key]['code_candidates'][0]['case_status_plus']) != 0:
                        plus_pass_rate = len(problem_dic_list[i][key]['code_candidates'][0]['passed_case_plus'])/ \
                                         len(problem_dic_list[i][key]['code_candidates'][0]['case_status_plus'])
                    else:
                        plus_pass_rate = -1

                    if 'plus_pass_rate' not in pass_rate_dic[key]:
                        pass_rate_dic[key]['plus_pass_rate'] = [plus_pass_rate]
                    else:
                        pass_rate_dic[key]['plus_pass_rate'].append(plus_pass_rate)

        # store the intermediate result
        res_dic = {
            'problem_dic_list': problem_dic_list,
            'passed_spoiled_unspoiled_cases_dic': passed_spoiled_unspoiled_cases_dic,
            'pass_rate_dic': pass_rate_dic
        }

    with open(log_file, 'w') as f:
        json_str = json.dumps(res_dic)
        f.write(json_str)


if __name__ == "__main__":
    if platform.system() == 'Linux':
        data_path = '../ChatGPT_stability/'
    else:
        data_path = '../alpha_code/'

    # analyze('APPS', 'reduce', 'gpt-3.5-turbo', '1', '1.0', data_path)

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-d",
        "--dataset",
        type=str,
        choices=['APPS', 'code_contest', 'HumanEval', 'HumanEval_plus', 'HumanEval_plus_mini'],
        help="Choose dataset",
        required=True,
    )
    parser.add_argument(
        "-m",
        "--model",
        help="Choose your Openai Model",
        type=str,
        required=True,
    )
    parser.add_argument(
        "-n",
        "--topn",
        type=int,
        help="Top N candidates",
        required=True,
    )
    parser.add_argument(
        "-t",
        "--temperature",
        type=float,
        help="Set the temperature",
        required=True,
    )
    parser.add_argument(
        "-o",
        "--option",
        type=str,
        choices=['original', 'add', 'replace', 'seperate', 'reduce'],
        help="Choose the option of modification",
        required=True,
    )
    args = parser.parse_args()
    analyze(args.dataset, args.option, args.model, args.topn, args.temperature, data_path)
