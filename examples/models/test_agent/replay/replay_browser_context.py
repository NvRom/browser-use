import logging
import os
from typing import TYPE_CHECKING, Optional, TypedDict

from playwright._impl._errors import TimeoutError

from browser_use.browser.context import BrowserContext, BrowserContextConfig
from browser_use.browser.views import (
	BrowserError,
	URLNotAllowedError,
)
from browser_use.dom.history_tree_processor.service import DOMHistoryElement

logger = logging.getLogger(__name__)

class ReplayBrowserContext(BrowserContext):
	async def _input_text_element_node(self, element_node: DOMHistoryElement, text: str):
		"""
		Input text into an element with proper error handling and state management.
		Handles different types of input fields and ensures proper element state before input.
		"""
		try:
			page = await self.get_current_page()

			selectors = element_node.css_selector.split('>') if element_node.css_selector else []
			selectors = [s for s in selectors if any(c in s for c in ['[', '.', '#'])]
			finalSelector = ' > '.join(selectors)

			print(f'🥶🥶🥶🥶🥶🥶🥶🥶🥶🥶🥶🥶🥶 FINAL SELECTOR: {finalSelector}')

			element_handle = await page.query_selector(finalSelector)
			if element_handle is None:
				raise BrowserError(f'Element: {repr(element_node)} not found')

			# Ensure element is ready for input
			try:
				await element_handle.wait_for_element_state('stable', timeout=1000)
				await element_handle.scroll_into_view_if_needed(timeout=1000)
			except Exception:
				pass

			# Get element properties to determine input method
			is_contenteditable = await element_handle.get_property('isContentEditable')

			# Different handling for contenteditable vs input fields
			if await is_contenteditable.json_value():
				await element_handle.evaluate('el => el.textContent = ""')
				await element_handle.type(text, delay=5)
			else:
				await element_handle.fill(text)

		except Exception as e:
			logger.debug(f'Failed to input text into element: {repr(element_node)}. Error: {str(e)}')
			raise BrowserError(f'Failed to input text into index {element_node.highlight_index}')

	async def _click_element_node(self, element_node: DOMHistoryElement) -> Optional[str]:
		"""
		Optimized method to click an element using xpath.
		"""
		page = await self.get_current_page()

		try:
			selectors = element_node.css_selector.split('>') if element_node.css_selector else []
			selectors = [s for s in selectors if any(c in s for c in ['[', '.', '#'])]
			finalSelector = ' > '.join(selectors)

			print(f'😀🥶🥶🥶🥶🥶🥶🥶🥶🥶🥶🥶🥶🥶 FINAL SELECTOR: {finalSelector}')

			element_handle = await page.query_selector(finalSelector)
			if element_handle is None:
				raise Exception(f'Element: {repr(element_node)} not found')

			await element_handle.scroll_into_view_if_needed()

			async def perform_click(click_func):
				"""Performs the actual click, handling both download
				and navigation scenarios."""
				if self.config.save_downloads_path:
					try:
						# Try short-timeout expect_download to detect a file download has been been triggered
						async with page.expect_download(timeout=5000) as download_info:
							await click_func()
						download = await download_info.value
						# Determine file path
						suggested_filename = download.suggested_filename
						unique_filename = await self._get_unique_filename(self.config.save_downloads_path, suggested_filename)
						download_path = os.path.join(self.config.save_downloads_path, unique_filename)
						await download.save_as(download_path)
						logger.debug(f'Download triggered. Saved file to: {download_path}')
						return download_path
					except TimeoutError:
						# If no download is triggered, treat as normal click
						logger.debug('No download triggered within timeout. Checking navigation...')
						await page.wait_for_load_state()
						await self._check_and_handle_navigation(page)
				else:
					# Standard click logic if no download is expected
					await click_func()
					await page.wait_for_load_state()
					await self._check_and_handle_navigation(page)

			try:
				return await perform_click(lambda: element_handle.click(timeout=1500))
			except URLNotAllowedError as e:
				raise e
			except Exception as e:
				try:
					print(f">>>>> ${e}")
					return await perform_click(lambda: page.evaluate('(el) => el.click()', element_handle))
				except URLNotAllowedError as e:
					raise e
				except Exception as e:
					raise Exception(f'Failed to click element: {str(e)}')

		except URLNotAllowedError as e:
			raise e
		except Exception as e:
			raise Exception(f'Failed to click element: {repr(element_node)}. Error: {str(e)}')

