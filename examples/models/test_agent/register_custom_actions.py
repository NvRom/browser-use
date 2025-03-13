import os
import sys

from browser_use.agent.views import ActionResult

# In essence, this line adds the parent directory's parent directory of the current file
# to the Python module search path. This is often done to allow importing modules from
# sibling directories within a project.
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import Optional

from langchain_core.language_models.chat_models import BaseChatModel
from pydantic import BaseModel

from browser_use import Agent, Controller
from browser_use.browser.browser import Browser, BrowserConfig
from browser_use.browser.context import BrowserContext
from browser_use.agent.views import ActionModel, ActionResult

class LoginToMSA(BaseModel):
	userName: str
	password: str

class BingSearchModel(BaseModel):
	text: str
	bingUrl: Optional[str]

def register_custom_actions(controller: Controller):

	async def call_agent(
		task: str,
		browser_instance: Browser,  # todo: the name is not clear
		browser: BrowserContext,    # todo: the name is not clear
		agent_llm: BaseChatModel,
	) -> ActionResult:
		agent = Agent(
			llm=agent_llm,
			max_actions_per_step=4,
			task=task,
			use_vision=False,  # avoid too many data in log
			controller=controller,
			browser=browser_instance,
			browser_context=browser,
		)
		ret = await agent.run(max_steps=25)

		# check actionResult of last item in ret
		lastResult = ret.history[-1].result[-1]

		finalResult = ActionResult(
			extracted_content=lastResult.extracted_content,
			error=lastResult.error,
			include_in_memory=True,
		)

		# input('Press Enter to continue...')

		return finalResult

	@controller.action(
		"""Search on Bing for a specific query; if Bing url is specified, use that specified Url.
		always use this tool for searching on **Bing** before considering others
		""",
		param_model=BingSearchModel
	)
	async def search_on_bing(
		params: BingSearchModel,
		browser_instance: Browser,
		browser: BrowserContext,
		agent_llm: BaseChatModel,
	) -> ActionResult:
		print('🔶🔶🔶🔶🔶🔶🔶🔶🔶🔶🔶🔶🔶🔶🔶🔶🔶🔶🔶🔶🔶🔶🔶🔶🔶🔶🔶🔶🔶🔶🔶🔶 search_on_bing')
		bingUrl = params.bingUrl if params.bingUrl is not None else 'https://www.bing.com'
		# todo: load from external file?
		task = f"""
			1. goto {bingUrl} if current url is not {bingUrl}
			2. type "{params.text}" in the search bar
			3. press enter 
			"""
		final_result = await call_agent(task, browser_instance, browser, agent_llm)
		print('🟧🟧🟧🟧🟧🟧🟧🟧🟧🟧🟧🟧🟧🟧🟧🟧🟧🟧🟧🟧🟧🟧🟧🟧🟧🟧🟧🟧🟧🟧🟧🟧🟧 search_on_bing')
		return final_result

	@controller.action(
		"""sign in to bing.com, using the provided username and password.
		always use this tool to sign in to bing.com before considering others.
		""",
		param_model=LoginToMSA
	)
	async def login_to_bing(
		params: LoginToMSA,
		browser_instance: Browser,
		browser: BrowserContext,
		agent_llm: BaseChatModel,
	) -> ActionResult:
		# todo: load from external file?
		print('🟣🟣🟣🟣🟣🟣🟣🟣🟣🟣🟣🟣🟣🟣🟣🟣🟣🟣🟣🟣🟣🟣🟣🟣🟣🟣🟣🟣🟣🟣🟣🟣 in to MSA')
		task = f"""
		1. click sign in button in bing.com, and then a dropdown menu will appear
		2. select the option to use a personal account in the dropdown menu
		3. complete the sign in process using user name: {params.userName}, and password: {params.password}
		login to MSA using username: {params.userName} and password: {params.password}
		"""
		final_result = await call_agent(task, browser_instance, browser, agent_llm)
		print('🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩 in to MSA')
		return final_result

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
