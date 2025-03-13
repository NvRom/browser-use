import json
from typing import Optional, Any
from pydantic.json import pydantic_encoder
from pathlib import Path

from browser_use import  Controller, Browser, BrowserConfig, BrowserContextConfig, Agent

from examples.models.test_agent.register_custom_actions import register_custom_actions
from replay.replay_runner import get_test_replay_steps, replay_test
from view import TestCase

# todo: use sensitive data in generated test cases
# 1. Open https://www.bing.com/?setlang=en&cc=us in Edge and login to MSA with test_username and test_password!
# 1. Open https://www.bing.com/?setlang=en&cc=us in Edge and login using mail: mstest_wanju1@outlook.com, the password is: asdlkj1234!

# ultimate_task = f"""
# 1. Open https://www.bing.com/?setlang=en&cc=us in Edge
# 2. Search "MIT"
# 3. Scroll down the searched page and find the Donate with Microsoft section.
# 4. Click the Donate button.
# """

# ultimate_task = f"""
# 1. Open https://www.bing.com/?setlang=en&cc=us in Edge
# 2. Input "MIT" and press enter to search in Bing
# 3. Scroll down the searched page and find the Donate with Microsoft section.
# 4. Click the Donate button.
# """

# ultimate_task = f"""
# 1. search "MIT" on Bing (https://www.bing.com/?setlang=en&cc=us)
# 2. Scroll down the searched page and find the Donate with Microsoft section.
# 3. Click the Donate button.
# """

# ultimate_task = f"""
# 1. Open https://www.bing.com/?setlang=en&cc=us
# 2. sign in, username: mstest_wanju1@outlook.com, password: asdlkj1234!
# 3. search "MIT" on Bing (https://www.bing.com/?setlang=en&cc=us)
# 4. Scroll down the searched page and find the Donate with Microsoft section.
# 5. Click the Donate button.
# """

# todo: expected result
# 1. Bing search page is opened
# 2. Search result page is opened 
# 3. Donate with Microsoft section is displayed well
# 4. ...

async def _run_agent(llm, test_case: TestCase, params: Optional[dict[str, Any]] = None):
	# init controller with custom actions
	controller = Controller()

	# 🚗🚗🚗🚗🚗🚗🚗🚗🚗🚗🚗🚗🚗🚗🚗🚗🚗
	register_custom_actions(controller)

	browser = Browser(
		config=BrowserConfig(
			new_context_config=BrowserContextConfig(viewport_expansion=0)
		)
	)

	# todo: replace template with actual values from params
	ultimate_task = '\n'.join(test_case.test_steps)

	agent = Agent(
		task=ultimate_task,
		llm=llm,
		max_actions_per_step=4,
		browser=browser,
		# sensitive_data=sensitive_data,
		use_vision=False, # avoid too many data in log
		controller=controller,
	)

	historyList = await agent.run(max_steps=25)

	replaySteps = get_test_replay_steps(historyList)
	return replaySteps


#
# run a single test case, replay or run the test using llm
async def run_test_case(llm, test_case: TestCase, params: Optional[dict[str, Any]] = None):

	# check if test_case.replay_steps is empty or not
	if not test_case.replay_steps:
		# run ultimate_task
		replay_steps = await _run_agent(llm, test_case, params)
		is_replay = False
		return (is_replay, replay_steps)
	else:
		# replay
		# todo: return the replay result
		await replay_test(llm, test_case)
		return (True, None)


#
# todo: accept path as string type?
async def run_test_case_file(llm, test_case_json_file: Path, params: Optional[dict[str, Any]] = None):
	has_data_changed = False
	with open(test_case_json_file, 'r') as f:
		test_case = TestCase.model_validate_json(f.read())
		(is_replay, replay_steps) = await run_test_case(llm, test_case, params)

		# todo: save recover info for replaying
		# todo: generate running report
		if not is_replay and replay_steps:
			# save replay_steps to test_case
			test_case.replay_steps = replay_steps
			has_data_changed = True

	# Save testCaseSteps to a file
	if has_data_changed:
		with open(test_case_json_file, 'w') as f:
			json.dump(test_case, f, default=pydantic_encoder, indent=2)
