"""
Simple try of the agent.

@dev You need to add AZURE_OPENAI_API_KEY and AZURE_OPENAI_ENDPOINT to your environment variables.
"""

import os
import sys
import json
from langchain_core.load import dumpd, load
from pydantic.json import pydantic_encoder
from typing import Optional, Any
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio

from langchain_openai import AzureChatOpenAI
from azure.identity import DefaultAzureCredential

from pathlib import Path
from examples.models.test_agent.view import ECTest,TestCase,TestStepEncoder
from agent_runner import run_agent
from replay.replay_runner import replay_test

system_prompt = """
You are a professional tester. 
I'll provide you a json input, you should execute the step in order under steps key.
Each step includes step_name, step_description and expected_result:
    - step_name: placeholder
    - step_description: actionable step
    - expected_result: the expected result after executing the step
You should execute step_description at first, then check if the expected_result is met condition. 
If the expected_result is met, you can move to the next step. else retry the current step, the maxium retry times is 3. if retry times is over, output 'step failed' and stop the test.
If no value in expected_result, just move next step.
Close any pop-up windows when opening an app.
all input is clear, do not add any extra information.
If the last step failed at expected_result, output 'test failed'; else output 'test passed'.
"""


# Get the Azure Credential
credential = DefaultAzureCredential()
# Set the API type to `azure_ad`
os.environ["OPENAI_API_TYPE"] = "azure_ad"
# Set the API_KEY to the token from the Azure credential
os.environ["OPENAI_API_KEY"] = credential.get_token("https://cognitiveservices.azure.com/.default").token

def _init_llm():
	azure_openai_endpoint = os.environ.get('AZURE_OPENAI_ENDPOINT')
	azure_openai_api_key = os.environ.get('OPENAI_API_KEY')
	llm = AzureChatOpenAI(
    	model_name='gpt-4o-mini',  # type: ignore
    	openai_api_key=azure_openai_api_key, # type: ignore
    	# azure_ad_token_provider=token_provider,
    	azure_endpoint=azure_openai_endpoint,  # Corrected to use azure_endpoint instead of openai_api_base
    	deployment_name='gpt-4o-mini',  # Use deployment_name for Azure models # type: ignore
    	api_version='2024-05-01-preview'  # Explicitly set the API version here
	)
	return llm

async def run_test(llm,test:TestCase):
    # run task with agent or replay
    if not test.replay_steps:
        # run task with agent
        replay_steps = await run_agent(llm,system_prompt + json.dumps(test.steps, cls=TestStepEncoder))
        is_replay = False
        return (is_replay, replay_steps)
    else:
        # replay
        await replay_test(llm,test)
        return (True, None)

# run test without filter
async def main(filter: Optional[dict[str,Any]] = None):
    llm = _init_llm()
    for json_file in Path(os.path.dirname(os.path.abspath(__file__))).glob('**/fashionnova.test_copy.json'):
        file_path = json_file.resolve()
        need_save_to_file = False
        with open(file_path, 'r') as f:
            # json_str = json.loads(f.read())
            test_cases = ECTest.model_validate_json(f.read())
            for test_case in test_cases.test_cases:
                (is_replay, replay_steps) = await run_test(llm,test_case)
                if not is_replay and replay_steps:
                    test_case.replay_steps = replay_steps
                    need_save_to_file = True
        if need_save_to_file:
            with open(file_path, 'w') as f:
                json.dump(test_cases, f, indent=4, default=pydantic_encoder)

asyncio.run(main())