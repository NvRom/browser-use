import os
import sys

from examples.models.test_agent.register_custom_actions import register_custom_actions
from examples.models.test_agent.replay.replay_runner import get_test_replay_steps

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


from browser_use import BrowserConfig, Browser, Agent, Controller, ActionResult
from browser_use.browser.context import BrowserContext, BrowserContextConfig

def _init_browser():
	browser = Browser(
		config=BrowserConfig(
			# NOTE: you need to close your chrome browser - so that this can open your browser in debug mode
			chrome_instance_path='C:\\Users\\weixche\\AppData\\Local\\Microsoft\\Edge SxS\\Application\\msedge.exe',
			extra_chromium_args=['--profile-directory=Profile 1'] + ['--user-data-dir=C:\\Users\\weixche\\AppData\\Local\\Microsoft\\Edge SxS\\User Data\\', '--enable-features=msWalletCheckoutDebugDAF'],
			new_context_config=BrowserContextConfig(
				pane_url='edge://wallet-drawer/',
			)   
		)
	)
	return browser

async def run_agent(llm,task: str,domain:str):
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
	controller = Controller()
	
	@controller.action(
		'switch to checkout page - call this function when the agent need to monitor checkout page',
	)
	def switch_checkout_page(browser: BrowserContext):
		browser.config.is_focus_on_pane = False
		msg = f'🔗  switch to checkout page'
		return ActionResult(extracted_content=msg, include_in_memory=True)

	@controller.action(
		'switch to side pane - call this function when the agent need to monitor side pane',
	)
	def switch_side_pane(browser: BrowserContext):
		browser.config.is_focus_on_pane = True
		msg = f'🔗  switch to side pane'
		return ActionResult(extracted_content=msg, include_in_memory=True)

	@controller.action('refesh current page',)
	async def refresh_page(browser: BrowserContext):
		browser.config.is_focus_on_pane = False
		await browser.refresh_page()
		msg = f'🔗  refresh the page'
		return ActionResult(extracted_content=msg, include_in_memory=False)
	# register_custom_actions(controller)

	try:
		agent = Agent(
			task=task,
			llm=llm,
			max_actions_per_step=4,
			browser=browser,
			controller=controller,
		)
		historyList = await agent.run(max_steps=10)

		replaySteps = get_test_replay_steps(historyList)
		return replaySteps
	finally:
		await agent.close_tab_with_domain(domain)


	