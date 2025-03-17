from typing import Optional, Any
from pydantic import SecretStr, BaseModel
from pydantic.json import pydantic_encoder

from browser_use import Agent, AgentHistoryList, Controller, Browser, ActionResult, ActionModel
from browser_use.dom.history_tree_processor.view import DOMHistoryElement
from browser_use.browser.browser import BrowserConfig
from browser_use.browser.context import BrowserContext, BrowserContextConfig

from replay.replay_browser_context import ReplayBrowserContext
from view import TestCaseReplayStep, TestCaseReplayAction, TestCase
from examples.models.test_agent.register_custom_actions import register_custom_actions

# todo: refine the recover logic, consider more factors
async def _recover_step_using_agent(
	llm,
	controller: Controller,
	browser: Browser,
	browser_context: BrowserContext,
	replayStep: TestCaseReplayStep,
	stepIndex: int,
	replayAction: TestCaseReplayAction,
	action_name: str,
	action_model: ActionModel,
):
	# todo: compose the prompt
	task = f"""please help to finish this goal: '''{replayStep.next_goal}''' on current page"""

	agent = Agent(
		llm=llm,
		max_actions_per_step=4,
		task=task,
		use_vision=False,  # avoid too many data in log
		controller=controller,
		browser=browser,
		browser_context=browser_context,
		# sensitive_data=sensitive_data
	)
	ret = await agent.run(max_steps=25)

	# check actionResult of last item in ret
	lastResult = ret.history[-1].result[-1]
	if lastResult.is_done and lastResult.error is None:
		print('❇️ Recovered step successfully')
		return True

	return False

async def _validate_replay_result(llm, test_case: TestCase, controller: Controller, browser_context: BrowserContext):
	last_step = test_case.steps[-1]
	task = f"""please help to validate the test case: '''{last_step.step_description + last_step.expected_result}''' on current page, and complete the task"""
	agent = Agent(
		llm=llm,
		max_actions_per_step=4,
		task=task,
		use_vision=False,  # avoid too many data in log
		controller=controller,
		browser_context=browser_context,
	)
	ret = await agent.run(max_steps=25)
	return ret.history[-1].result[-1]

async def _replay_test_steps(
	llm,
	replaySteps: list[TestCaseReplayStep],
	controller: Controller,
	browser_context: ReplayBrowserContext,
	browser: Browser,
):
	"""
	Executes a series of replay steps for testing purposes.

	Args:
		llm: The language model used for recovery steps.
		replaySteps (list[TestCaseReplayStep]): A list of replay steps to execute.
		controller (Controller): The controller managing the actions.
		browser_context (ReplayBrowserContext): The browser context for the replay.
		browser (Browser): The browser instance used for the replay.

	Raises:
		Exception: If a step fails and recovery is not successful.
	"""
	print('🍏 RUN TEST: ##########################################')
	# input('🍏 Press Enter to continue...')

	TActionModel = controller.registry.create_action_model()

	for stepIndex, replayStep in enumerate(replaySteps):

		nextStep = replaySteps[stepIndex + 1] if stepIndex + 1 < len(replaySteps) else None
		evaluation_current_goal = nextStep.evaluation_previous_goal if nextStep else None

		if nextStep is not None and (evaluation_current_goal is None or evaluation_current_goal.startswith("Failed")):  # Success|Failed|Unknown
			print(f'🍏 Step {stepIndex} failed, skipping to next step, {evaluation_current_goal}')
			continue

		# log
		print('🌷 ========================================')
		replayStep.print()
		# input('🌷 Press Enter to continue...')

		for replayAction in replayStep.replayActions:

			# ignore failed actions
			if replayAction.result.error is not None:
				continue

			await browser_context._wait_for_page_and_frames_load()

			for action_name, params in replayAction.action.items():
				print(f'>> 💎💎💎💎💎 Action {action_name}: {params}')
				# input('💎 Press Enter to continue...')
				try:
					if action_name == 'click_element':
						element = replayAction.element
						if element is not None:
							await browser_context._click_element_node(element)
					elif action_name == 'input_text':
						element = replayAction.element
						if element is not None:
							await browser_context._input_text_element_node(element, params['text'])
					elif action_name == 'done':
						# input("Done, press Enter to continue...")
						break
					else:
						# Get the parameter model for this action from registry
						action_info = controller.registry.registry.actions[action_name]
						param_model = action_info.param_model

						# Create validated parameters using the appropriate param model
						validated_params = param_model(**params)

						# Create ActionModel instance with the validated parameters
						action_model = TActionModel(**{action_name: validated_params})

						await controller.act(
							action=action_model,
							browser_context=browser_context,
						)

				except Exception as e:
					print(f'‼️‼️‼️‼️ Step Failed: action_name: {action_name}, stepIndex: {stepIndex}, actionIndex: {replayAction.actionIndex}')
					replayStep.print()
					print(f'✚✚✚✚✚')
					replayAction.print()
					# input(f'‼️‼️‼️‼️ try to recover now, press Enter to continue...')
					successOrNot = await _recover_step_using_agent(
						llm,
						controller=controller,
						browser=browser,
						browser_context=browser_context,
						replayStep=replayStep,
						stepIndex=stepIndex,
						replayAction=replayAction,
						action_name=action_name,
						action_model=action_model,
					)
					# input(f'‼️‼️‼️‼️ recover done, success: {successOrNot}, press Enter to continue...')
					if not successOrNot:
						raise e


#
# replay the test case
async def replay_test(llm, test_case: TestCase, domain: str):
	# Placeholder for additional logic if needed
	if not test_case.replay_steps:
		raise ValueError("no replay steps found in test case")

	browser = Browser(
		config=BrowserConfig(
			# NOTE: you need to close your chrome browser - so that this can open your browser in debug mode
			chrome_instance_path='C:\\Users\\weixche\\AppData\\Local\\Microsoft\\Edge SxS\\Application\\msedge.exe',
        	extra_chromium_args=['--profile-directory=Profile 1'] + ['--user-data-dir=C:\\Users\\weixche\\AppData\\Local\\Microsoft\\Edge SxS\\User Data\\', '--enable-features=msWalletCheckoutDebugDAF'],
        	new_context_config=BrowserContextConfig(
            	# save_recording_path='./tmp/recordings',
            	# should_lauch_persistent= True,
            	pane_url='edge://wallet-drawer/',
        	)   
		)
	)
	browser_context = ReplayBrowserContext(browser=browser, config=browser.config.new_context_config)
	controller = Controller()  # todo: replay controller
	register_custom_actions(controller)

	# start browser
	await browser_context.get_session()
	try:
		print("=================ready to run...")
		await _replay_test_steps(
			llm, test_case.replay_steps if test_case.replay_steps is not None else [],
			controller=controller,
			browser_context=browser_context,
			browser=browser,
		)
		# validation the final result
		return await _validate_replay_result(llm, test_case, controller, browser_context)
	finally:
		await browser_context.close_tab_with_domain(domain)


#
# generate playwright test cases based on the LLM run result
def get_test_replay_steps(historyList: AgentHistoryList) -> list[TestCaseReplayStep]:

	replaySteps: list[TestCaseReplayStep] = []

	for stepIndex, history in enumerate(historyList.history):
		model_output = history.model_output
		if model_output:
			current_state = model_output.current_state
			actionList = model_output.action

			evaluation_previous_goal = current_state.evaluation_previous_goal
			memory = current_state.memory
			next_goal = current_state.next_goal

			actionResultList = history.result
			elementList = history.state.interacted_element

			replayStep = TestCaseReplayStep(
				stepIndex=stepIndex,
				evaluation_previous_goal=evaluation_previous_goal,
				memory=memory,
				next_goal=next_goal,
			)

			for actionIndex, action in enumerate(actionList):
				actionResult = actionResultList[actionIndex]
				elementIndex = action.get_index()
				# Find the element in elementList with matching highlight_index
				element: DOMHistoryElement | None = next((elem for elem in elementList if elem and elem.highlight_index == elementIndex), None)

				testCaseReplayAction = TestCaseReplayAction(
					action=action.model_dump(exclude_unset=True),
					result=actionResult,
					element=element,
					stepIndex=stepIndex,
					actionIndex=actionIndex,
				)
				replayStep.add_action(testCaseReplayAction)

		replaySteps.append(replayStep)

	return replaySteps
