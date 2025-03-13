from typing import Optional, Any
from pydantic import SecretStr, BaseModel
from browser_use import ActionResult
from browser_use.dom.history_tree_processor.view import DOMHistoryElement
from pydantic.json import pydantic_encoder
from json import JSONEncoder

class TestCaseReplayAction(BaseModel):
	action: dict[str, Any] #ActionModel
	result: ActionResult
	element: Optional[DOMHistoryElement] = None # todo: remove it, only keep css selectors
	stepIndex: int
	actionIndex: int

	def print(self):
		print(f'>> 🟢🟢 Action {self.actionIndex}: {self.action.items()}')
		print(f'>> 🟡🟡 Action Result {self.result}')
		print(f'>> 🔴🔴 Action Element {self.element}')

class TestCaseReplayStep(BaseModel):
	stepIndex: int
	evaluation_previous_goal: str
	memory: str
	next_goal: str
	replayActions: list[TestCaseReplayAction] = []
	
	def add_action(self, action: TestCaseReplayAction):
		self.replayActions.append(action)
	
	def print(self):
		print(f'🔥🔥 Step {self.stepIndex}:')
		print(f'🍉🍉 Evaluation Previous Goal: {self.evaluation_previous_goal}')
		print(f'🍉🍉 Memory: {self.memory}')
		print(f'🍉🍉 Next Goal: {self.next_goal}')
		for action in self.replayActions:
			action.print()

class TestStep(BaseModel):
    step_name: str
    step_description: str
    expected_result: str
	
class TestStepEncoder(JSONEncoder):
	def default(self, obj):
		if isinstance(obj, TestStep):
			return {
        'step_name': obj.step_name,
        'step_description': obj.step_description,
        'expected_result': obj.expected_result
      }

class TestCase(BaseModel):
	test_case_name: str
	test_case_description: str
	priority: Optional[int]
	steps: list[TestStep] = []
	replay_steps: Optional[list[TestCaseReplayStep]] = None

class ECTest(BaseModel):
  domain: Optional[str]
  test_cases: list[TestCase] = []
