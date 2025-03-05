"""
Simple try of the agent.

@dev You need to add AZURE_OPENAI_API_KEY and AZURE_OPENAI_ENDPOINT to your environment variables.
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio

from langchain_openai import AzureChatOpenAI
from azure.identity import DefaultAzureCredential

from browser_use import BrowserConfig, Browser, Agent, Controller
from browser_use.browser.context import BrowserContext, BrowserContextConfig

# Get the Azure Credential
credential = DefaultAzureCredential()
# Set the API type to `azure_ad`
os.environ["OPENAI_API_TYPE"] = "azure_ad"
# Set the API_KEY to the token from the Azure credential
os.environ["OPENAI_API_KEY"] = credential.get_token("https://cognitiveservices.azure.com/.default").token

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

# config=BrowserConfig(
#     headless=False,
#     disable_security=True,
#     chrome_instance_path='C:\\Users\\wjia\\AppData\\Local\\Microsoft\\Edge SxS\\Application\\msedge.exe',
#     extra_chromium_args=['--profile-directory=Profile 1'] + ['--user-data-dir=C:\\Users\\wjia\\AppData\\Local\\Microsoft\\Edge SxS\\User Data\\', '--enable-features=msWalletCheckoutDebugDAF'],
#     )

azure_openai_endpoint = os.environ.get('AZURE_OPENAI_ENDPOINT')
azure_openai_api_key = os.environ.get('OPENAI_API_KEY')

llm = AzureChatOpenAI(
    model_name='gpt-4o-mini', 
    openai_api_key=azure_openai_api_key,
    # azure_ad_token_provider=token_provider,
    azure_endpoint=azure_openai_endpoint,  # Corrected to use azure_endpoint instead of openai_api_base
    deployment_name='gpt-4o-mini',  # Use deployment_name for Azure models
    api_version='2024-05-01-preview'  # Explicitly set the API version here
)

from browser_use import Controller, ActionResult
# Initialize the controller
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

# https://www.alexandani.com/checkouts/cn/Z2NwLXVzLWVhc3QxOjAxSktaNThXNzFLUUdYN1dHTVdES0tGRTlF/payment
# goal: test if EC(Express Checkout) could overwrite fields which are already filled by the user

overwrite_task = """
You are a professional tester. 
You should do the following steps in order, and then validate the result in the end.
steps:
1. go to https://www.alexandani.com/checkouts/cn/Z2NwLXVzLWVhc3QxOjAxSktaNThXNzFLUUdYN1dHTVdES0tGRTlF/payment
2. refresh the page
3. fill few fields in the checkout page with below value:
    - First name: browser use
    - Last name: test
4. switch to side pane and wait pane to appear
5. find `precessed and review` button and click it
6. wait 'continue to checkout' button to be visible
validate:
1. switch to checkout page
2. value of below fields' should be:
    - First name: browser use
    - Last name: test
3. if above expectations are not met, please output 'overwrite tests failed'; else output 'overwrite tests passed'
"""

auto_dismiss_task = """
You are a professional tester. 
I'll provide you a detailed test steps, each step includes action and validation part.
You should execute action part at first, then validation part. Only pass the validation part, you can move to the next step.
If no value in validation part, just move next step.

step 1:{
action: go to https://nordcheckout.com/payment/?product_group=nordvpn&ff%5Bplan-period-dropdown%5D=on&cart_id=0bbd686e-0c38-469b-b869-7fddb0d47434&product_xs=dedicated_ip,
validation: 
},
step 2:{
action: refresh the page,
validation: 
},
step 3:{
action: find `Credit or debit card` label and click it,
validation: if first name field found, go to next step; else retry step 3, the maxium retry times is 5. if retry times is over, output 'step 3 failed' and stop the test,
}
step 4:{
action: switch to side pane and wait pane to appear, 
validation: if 'Proceed and review' button found, go to next step; else retry step 4, the maxium retry times is 5. if retry times is over, output 'step 4 failed' and stop the test,
}
step 5:{
action: switch to checkout page,
validation:
}
step 6:{
action: find 'Paypal' label and click it,
validation: if 'buy with' button found, go to next step; else retry step 6, the maxium retry times is 5. if retry times is over, output 'step 6 failed' and stop the test,
}
step 7:{
action: switch to side pane,
validation: if `Autofill checkout details` words is not found, output 'auto dismiss test passed'; else output 'auto dismiss test failed'
}
"""

auto_dismiss_task_fill_form = """
You are a professional tester. 
I'll provide you a detailed test steps, each step includes action and validation part.
You should execute action part at first, then validation part. Only pass the validation part, you can move to the next step.
If no value in validation part, just move next step.

step 1:{
action: go to https://nordcheckout.com/payment/?product_group=nordvpn&ff%5Bplan-period-dropdown%5D=on&cart_id=0bbd686e-0c38-469b-b869-7fddb0d47434&product_xs=dedicated_ip,
validation: 
},
step 2:{
action: refresh the page,
validation: 
},
step 3:{
action: find `Credit or debit card` label and click it,
validation: if first name field found, go to next step; else retry step 3, the maxium retry times is 5. if retry times is over, output 'step 3 failed' and stop the test,
}
step 4:{
action: switch to side pane and wait pane to appear, 
validation: if 'Proceed and review' button found, go to next step; else retry step 4, the maxium retry times is 5. if retry times is over, output 'step 4 failed' and stop the test,
}
step 5:{
action: switch to checkout page,
validation:
}
step 6:{
action: fill the fields in the checkout page with below value:
    - Card number: 4111 1111 1111 1111,
    - Expiration date: 12/25,
    - CVC: 123,
validation: if value in 'Card number' is equal to '4111 1111 1111 1111', go to next step; else retry step 6, the maxium retry times is 5. if retry times is over, output 'step 4 failed' and stop the test,
}
step 7:{
action: switch to side pane,
validation: if `Autofill checkout details` words is not found, output 'auto dismiss test passed'; else output 'auto dismiss test failed'
}
"""

coupon_apply_task = """
You are a professional tester. 
I'll provide you a detailed test steps, each step includes action and validation part.
You should execute action part at first, then validation part. Only pass the validation part, you can move to the next step.
If no value in validation part, just move next step.

step 1:{
action: go to https://www.fashionnova.com/checkouts/cn/Z2NwLXVzLWVhc3QxOjAxSk5GSFFZUEFRRUQzQTFXRDBXV0ZKRDVR,
validation: 
},
step 2:{
action: refresh the page,
validation: 
},
step 3:{
action: switch to side pane and wait pane to appear, 
validation: if `apply savings` words found, go to next step; else retry step 4, the maxium retry times is 5. if retry times is over, output 'step 4 failed' and stop the test,
}
step 4:{
action: select `apply savings` checkout box
validation:
}
step 5:{
action: find 'Proceed and review' button and click it
validation:
}
step 6:{
action: find 'continue to checkout' button。 important: do not click any button, just find it
validation: if button found, complete the task. else retry step 7 in 5 seconds, the maxium retry times is 5. if retry times is over, output 'step 7 failed' and stop the test,
}
"""

# json format
sample_task_json = """
You are a professional tester. 
I'll provide you a json input, you should execute the step in order under steps key.
Each step includes step_name, step_description and expected_result:
    - step_name: placeholder
    - step_description: actionable step
    - expected_result: the expected result after executing the step
You should execute step_description at first, then check if the expected_result is met condition. 
If the expected_result is met, you can move to the next step. else retry the current step, the maxium retry times is 5. if retry times is over, output 'step failed' and stop the test.
If no value in expected_result, just move next step.
If the last step failed at expected_result, output 'test failed'; else output 'test passed'.

{
  "test_cases": [
    {
      "test_case_name": "...",
      "test_case_description": "...",
      "steps": [
        {
          "step_name": "1",
          "step_description": "go to https://lobsteranywhere.com/checkout/",
          "expected_result": ""
        },
        {
          "step_name": "2",
          "step_description": "refresh the page",
          "expected_result": ""
        },
        {
          "step_name": "3",
          "step_description": "switch to side pane and wait pane to appear",
          "expected_result": "'Autofill checkout details' words should be found"
        },
        {
          "step_name": "4",
          "step_description": "find 'Proceed and review' button and click it",
          "expected_result": "'Cancel' button should be visible"
        },
        {
          "step_name": "5",
          "step_description": "find 'continue to checkout' button。 important: do not click any button, just find it",
          "expected_result": "'continue to checkout' button should be found"
        }
      ]
    }
  ]
}
"""

coupon_apply_task_json = """
You are a professional tester. 
I'll provide you a json input, you should execute the step in order under steps key.
Each step includes step_name, step_description and expected_result:
    - step_name: placeholder
    - step_description: actionable step
    - expected_result: the expected result after executing the step
You should execute step_description at first, then check if the expected_result is met condition. 
If the expected_result is met, you can move to the next step. else retry the current step after 5s, the maxium retry times is 10. if retry times is over, output 'step failed' and stop the test.
If no value in expected_result, just move next step.
If the last step failed at expected_result, output 'test failed'; else output 'test passed'.

{
  "test_cases": [
    {
      "test_case_name": "...",
      "test_case_description": "...",
      "steps": [
        {
          "step_name": "1",
          "step_description": "go to https://www.fashionnova.com/checkouts/cn/Z2NwLXVzLWVhc3QxOjAxSk5GSFFZUEFRRUQzQTFXRDBXV0ZKRDVR,",
          "expected_result": ""
        },
        {
          "step_name": "2",
          "step_description": "refresh the page",
          "expected_result": ""
        },
        {
          "step_name": "3",
          "step_description": "switch to side pane",
          "expected_result": "'Autofill checkout details' words should be found"
        },
        {
          "step_name": "4",
          "step_description": "select `apply savings` checkout box",
          "expected_result": 
        },
        {
          "step_name": "5",
          "step_description": "find 'Proceed and review' button and click it",
          "expected_result": "'Skip Coupon' button should be visible"
        },
        {
          "step_name": "6",
          "step_description": "wait for 60 seconds. important: do not click any button, just wait",
          "expected_result": 
        }
        {
          "step_name": "7",
          "step_description": "find 'continue to checkout' button。 important: do not click any button, just find it",
          "expected_result": "'Your checkout details were filled in' should be found"
        }
      ]
    }
  ]
}
"""

toggle_task_json = """
You are a professional tester. 
I'll provide you a json input, you should execute the step in order under steps key.
Each step includes step_name, step_description and expected_result:
    - step_name: placeholder
    - step_description: actionable step
    - expected_result: the expected result after executing the step
You should execute step_description at first, then check if the expected_result is met condition. 
If the expected_result is met, you can move to the next step. else retry the current step after 5s, the maxium retry times is 10. if retry times is over, output 'step failed' and stop the test.
If no value in expected_result, just move next step.
If the last step failed at expected_result, output 'test failed'; else output 'test passed'.

{
  "test_cases": [
    {
      "test_case_name": "...",
      "test_case_description": "...",
      "steps": [
        {
          "step_name": "1",
          "step_description": "find and click `Settings` button",
          "expected_result": "`Paymrnt methods`, 'Order tracking' words should be visible"
        },
        {
          "step_name": "2",
          "step_description": "find  and click `Show Express checkout on sites when you shop` toggle",
          "expected_result": ""
        },
        {
          "step_name": "3",
          "step_description": "go to https://www.fashionnova.com/checkouts/cn/Z2NwLXVzLWVhc3QxOjAxSk5GSFFZUEFRRUQzQTFXRDBXV0ZKRDVR,",
          "expected_result": ""
        },
        {
          "step_name": "4",
          "step_description": "refresh the page",
          "expected_result": ""
        },
        {
          "step_name": "5",
          "step_description": "switch to side pane",
          "expected_result": "'Autofill checkout details' words should not be found"
        },
      ]
    }
  ]
}
"""


agent = Agent(
    # task= "go to https://environmentamerica.org/take-action/donate-today/?amount=50&recurring=no",
    task = coupon_apply_task_json,
    llm=llm,
    browser=browser,
    # browser_context=context,
    controller=controller,
    use_vision_for_planner=False,
)

async def main():
    await agent.run(max_steps=15)
    input('Press Enter to continue...')


asyncio.run(main())