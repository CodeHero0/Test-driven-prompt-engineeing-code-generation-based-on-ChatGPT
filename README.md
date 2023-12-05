# Test-driven-prompt-engineeing-code-generation-based-on-ChatGPT


## Datasets
There are links to the datasets and projects we used in our experiments. (Below are the instructions on how to download and prepare the dataset)

[HumanEval](https://github.com/openai/human-eval) 

1. Click the link will redirect you to the human-eval homepage. On the homepage, you can download the data from '.\data\HumanEval.jsonl.gz'.
2. Decompress the file, then you get the dataset ''.\data\HumanEval.jsonl'
3. Due to the dataset are not perfect for the experiment, we use script [Modify_HumanEval.py](https://github.com/CodeHero0/Test-driven-prompt-engineeing-code-generation-based-on-ChatGPT/blob/main/Modify_HumanEval.py) to reshape the HumanEval dataset.

[APPS](https://github.com/hendrycks/apps)
1. Click the link will redirect you to the apps homepage.
2. Dataset could be downloaded from the link shown in README.md 'Download the APPS dataset here.(~1.3GB)'
3. Decompress the file, then you get the dataset


[EvalPlus](https://github.com/evalplus/evalplus)
1. Follow the instructions of EvalPlus, and install the Evalplus library
2. Use the script file [generate_dataset_HumanEval_plus.py](https://github.com/CodeHero0/Test-driven-prompt-engineeing-code-generation-based-on-ChatGPT/blob/main/generate_dataset_HumanEval_plus.py) to generate HumanEval dataset with a new test case set


## Experiments
Our experiments mainly contain the following scripts:

### 1. Generating response

We use generate_response.py to generate responses with three code problem datasets, and store them into JSON files in '.\log\'. (Below is the example command to run this script). If you want to change the way of requesting ChatGPT, please see [Openai's official website](https://platform.openai.com/docs/api-reference/chat).


```sh
python generate.py -d HumanEval -m gpt-3.5-turbo -n 1 -t 1 -s 0 
```

Some bugs might occur in running this script:
1. Dataset path error (change the dataset store path in the functions, e.g. APPS_experiment and HumanEval_experiment)
2. Paste your own openai.api_key in the file. (**DON'T upload your script with your openai.key to the public repository!!!!!!!!!!!**) If you are still a free user of Openai model API, please config your account as pay-as-you-go before running the script, otherwise it's likely to reach the free trial limitation.
3. Download the library that you don't have in your environment
4. Due to some unexpected error from ChatGPT API such as requesting over time, running the script once cannot guarantee to cover all the problems in the dataset. So our recommended solution is to run the script multiple times.


### 2. Evaluate and analyze the returned code

We use `analyze.py` to generate intermedia based on the test cases and responses we get in the first step, intermedia results will be stored in `'.\log\intermediate_result\'`. (Below is the example command to run this script)

```sh
python analyze.py -f log/dataset_APPS_model_gpt-3.5-turbo_topn_1_temperature_0.0.log_0
```
Some bugs might occur in running this script:
1. The parameter after -f should start with `'log/'`
2. Dataset path error (change the dataset store path in the functions, e.g. 'log_file')
