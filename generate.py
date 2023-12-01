import generate_APPS
import generate_HumanEval
import platform
import argparse

if __name__ == "__main__":
    # check the system
    if platform.system() == 'Linux':
        data_path = '../ChatGPT_stability/'
    else:
        data_path = '../alpha_code/'

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-d",
        "--dataset",
        type=str,
        choices=['APPS', 'code_contest', 'HumanEval'],
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
        choices=['original', 'add', 'replace', 'seperate'],
        help="Choose the option of modification",
        required=True,
    )
    parser.add_argument(
        "-s",
        "--sequence",
        type=str,
        help="Choose the order of the experiment",
        default='0'
    )
    args = parser.parse_args()
    if args.dataset == 'HumanEval':
        generate_HumanEval.HumanEval_experiment(args.dataset, args.option, args.model, args.sequence, args.topn,
                                                args.temperature, data_path)
    elif args.dataset == 'APPS':
        generate_APPS.APPS_experiment(args.dataset, args.option, args.model, args.sequence, args.topn,
                                      args.temperature, data_path)