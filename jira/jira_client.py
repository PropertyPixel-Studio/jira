# Copyright (c) 2021, ALYF GmbH and contributors
# For license information, please see license.txt
#
# OPRAVENO (2026): migrace ze zrušeného /rest/api/3/search na /rest/api/3/search/jql
# (Atlassian endpoint odstranil k 1.5.2025 -> 410 Gone). Nové stránkování přes nextPageToken.
# Zároveň oprava logování chyb pro Frappe v15 (title vs message).

from typing import Iterator

import requests
from requests.auth import HTTPBasicAuth

import frappe

from .jira_issue import JiraIssue
from .jira_worklog import JiraWorklog


class JiraClient:
	def __init__(self, url, user, api_key) -> None:
		self.url = url
		self.session = requests.Session()
		self.session.auth = HTTPBasicAuth(user, api_key)
		self.session.headers = {"Accept": "application/json"}

	def get(self, url: str, params=None):
		response = self.session.get(url, params=params)

		try:
			response.raise_for_status()
		except requests.HTTPError:
			# v15-safe: krátký title, dlouhý traceback do message
			frappe.log_error(
				title="Jira Sync Error",
				message=frappe.get_traceback(),
			)
			return {}

		return response.json()

	def get_issues(self, project: str) -> "Iterator[JiraIssue]":
		# Nový endpoint nahrazující zrušený /rest/api/3/search
		url = f"{self.url}/rest/api/3/search/jql"
		params = {
			"jql": f"project = {project}",
			"fields": "summary",
			"maxResults": 100,
		}

		while True:
			response = self.get(url, params=params)

			if not response:
				break

			for issue in response.get("issues") or []:
				yield JiraIssue.from_dict(issue)

			# Nové stránkování: pokud přijde nextPageToken, pokračuj, jinak konec
			next_page_token = response.get("nextPageToken")
			if not next_page_token:
				break

			params["nextPageToken"] = next_page_token

	def get_worklogs(self, issue: str) -> "list[JiraWorklog]":
		# Worklog endpoint zrušen NEBYL -> beze změny
		url = f"{self.url}/rest/api/3/issue/{issue}/worklog"
		response = self.get(url)
		results = response.get("worklogs", [])

		return [JiraWorklog.from_dict(result) for result in results]
