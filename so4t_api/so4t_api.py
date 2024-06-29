# Standard Python libraries
import json
import logging
import os
from time import sleep
from urllib.parse import urlparse, urlunparse
import urllib3

# Third-party libraries
import requests

# Request Methods
GET = 'get'
POST = 'post'
PUT = 'put'
DELETE = 'delete'


class StackClient(object):

    def __init__(self, url: str, token: str, key: str = None,
                 proxy: str = None, ssl_verify: bool = True,
                 private_team: str = None, logging_level="INFO"):
        """
        Initialize the StackClient class with the provided parameters.

        Args:
            url (str): The base URL for the Stack Overflow for Teams instance.
            token (str): The authentication token for accessing the API.
            key (str, optional): The key for accessing specific resources, defaults to None.
                Only required for user impersonation, which requires Stack Overflow Enterprise
            proxy (str, optional): The proxy server to be used for the API requests,
                defaults to None.
            ssl_verify (bool, optional): Flag indicating whether SSL verification should be
                performed, defaults to True.
            private_team (str, optional): Used in Enterprise to create an API client for a specific
                private team. The string should be the URL slug for the desired private team.
                Example: "https://subdomain.stackenterprise.co/c/PRIVATE-TEAM-SLUG"
                would be "PRIVATE-TEAM-SLUG". Defaults to None.
            logging_level (str, optional): The level of logging to be used, defaults to "INFO".

        Raises:
            ValueError: If an invalid log level is provided.

        Attributes:
            token (str): The authentication token for accessing the API.
            key (str): The API key. Stack Overflow Enterpise only.
            headers (dict): The headers to be included in the API requests.
            proxies (dict): The proxy settings for the API requests.
            ssl_verify (bool): Flag indicating whether SSL verification should be performed.
            base_url (str): The base URL for the Stack Overflow for Teams instance.
            team_slug (str): The team slug extracted from the URL.
            api_url (str): The full API URL to be used for API requests.
            impersonation_token (str): The token for user impersonation.
            soe (bool): Flag indicating whether the product is Stack Overflow Enterprise.

        Returns:
            None
        """
        # Setup logging
        numeric_level = getattr(logging, logging_level.upper(), None)
        if not isinstance(numeric_level, int):
            raise ValueError(f'Invalid log level: {logging_level}')
        logging.basicConfig(
            level=numeric_level,
            format='%(asctime)s | %(message)s'
        )

        logging.info("Initializing API v3 client...")

        self.token = token
        self.key = key
        self.s = requests.Session()
        self.s.headers = {'Authorization': f'Bearer {self.token}'}
        self.proxies = {'https': proxy} if proxy else {'https': None}
        self.ssl_verify = ssl_verify
        self.private_team = private_team
        if self.ssl_verify:
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        scheme, netloc, path, params, query, fragment = urlparse(url)
        scheme = "https"
        if not netloc:
            netloc = path
            path = ""
        self.base_url = urlunparse((scheme, netloc, path, "", "", ""))

        if "stackoverflowteams.com" in url:  # Stack Overflow Business or Basic
            self.team_slug = url.split("https://stackoverflowteams.com/c/")[1]
            self.api_url = f"https://api.stackoverflowteams.com/v3/teams/{self.team_slug}"
            self.soe = False  # Product is not Stack Overflow Enterprise
        else:  # Stack Overflow Enterprise
            self.api_url = self.base_url + "/api/v3"
            if self.private_team:
                self.api_url = self.api_url + f"/teams/{private_team}"
            self.impersonation_token = None  # Impersonation only available in Enterprise
            self.soe = True  # Product is Stack Overflow Enterprise

        # Test the API connection
        self.test_api_connection()

    def test_api_connection(self):
        """
        Test the API connection by making a request to a test endpoint.

        This method sends a request to a test endpoint ("/users/me") to check the API connection.
        If an SSLError occurs during the request, it attempts to make a GET request to the base URL
        with SSL verification turned off.
        If the error is specific to an SSL error and the base URL is correct, it raises a
        `BadURLError`.
        If a general connection error occurs, it raises a `BadURLError`.

        Raises:
            BadURLError: If there is an issue with the URL or a connection error.
            SSLError: If there is an SSL error during the API connection.

        Returns:
            None
        """
        test_endpoint = "/users/me"

        logging.info("Testing API v3 connection...")
        try:
            response = self.get_items(test_endpoint)
        except requests.exceptions.SSLError:  # Error only happens for Enterprise, not Business
            response = requests.get(self.base_url, verify=False)

            if "stackoverflow.co" in response.url and \
                    response.history[0].url.startswith(self.base_url):
                raise BadURLError(self.base_url)
            else:
                raise SSLError(
                    "Unable to connect to API due to an SSL Error. If you trust the URL, try "
                    "again after setting the `ssl_verify` argument to `False`. "
                    "Example: `stack = StackClient(url, token, ssl_verify=False)`"
                )
        except requests.exceptions.ConnectionError:
            raise BadURLError(self.base_url)

    # ========================
    # --- QUESTION METHODS ---
    # ========================

    def get_questions(self, page: int = None, pagesize: int = None,
                      sort: str = None, order: str = None,
                      is_answered: bool = None, has_accepted_answer: bool = None,
                      question_id: list = None, tag_id: list = None, author_id: int = None,
                      start_date: str = None, end_date: str = None,
                      one_page_limit: bool = False) -> list:
        """
        Returns a list of questions on the site.

        Using the default method (not passing any parameters) will result in returning all
        question objects in the Stack Overflow for Teams instances.

        Args:
            page (int, optional): The pagination offset response. Defaults to 1.
            pagesize (int, optional): The number of articles per page. Can be 15, 30, 50, or 100.
                Defaults to 100.
            sort (str, optional): The field by which the articles should be sorted. Can be
                'creation', 'activity', or 'score'. Defaults to 'creation'.
            order (str, optional): The order in which the articles should be sorted. Can be
                'asc' (ascending) or 'desc' (descending). Defaults to 'asc'.
            is_answered (bool, optional): Whether or not the response should contain only
                questions that have at least one answer.
            has_accepted_answer (bool, optional): Whether or not the response should only contain
                questions that have an accepted answer.
            question_id (list of int, optional): Used to filter questions by a list of specific
                question IDs.
            tag_id (list of int, optional): The IDs of specific tags to filter questions by.
                When using multiple tag IDs, it uses an "OR" logic rather than an "AND" logic.
                In other words, it will get any questions that match any of the tags.
            author_id (int, optional): The User ID of a specific author to filter questions by.
            start_date (str, optional): The earliest date a question should have been created on.
                Date format should be YYYY-MM or YYYY-MM-DD.
            end_date (str, optional): The latest date a question should have been created on. Date
                format should be YYYY-MM or YYYY-MM-DD.
            one_page_limit (bool, optional): Whether to limit the results to one page, rather than
                paging through all results.

        Returns:
            list: A list of questions matching the specified criteria. If no criteria are
                specified, all questions will be returned.
        """
        endpoint = "/questions"
        params = {
            'page': page if isinstance(page, int) else 1,
            'pageSize': pagesize if pagesize in [15, 30, 50, 100] else 100,
            'sort': sort if isinstance(sort, str) else 'creation',
            "order": order if order in ['asc', 'desc'] else 'asc',
            "isAnswered": is_answered if isinstance(is_answered, bool) else None,
            "hasAcceptedAnswer": has_accepted_answer if isinstance(has_accepted_answer, bool)
            else None,
            "questionId": question_id if isinstance(question_id, list) else None,
            "tagId": tag_id if isinstance(tag_id, list) else None,
            "authorId": author_id if isinstance(author_id, int) else None,
            "from": start_date if isinstance(start_date, str) else None,
            "to": end_date if isinstance(end_date, str) else None
        }
        logging.debug(f"Getting questions with params: {params}")

        questions = self.get_items(endpoint, params=params, one_page_limit=one_page_limit)
        return questions

    def get_question_by_id(self, question_id: int) -> dict:
        """
        Retrieve a question by its ID.

        Args:
            question_id (int): The unique identifier of the question to retrieve.

        Returns:
            dict: A dictionary containing the question details as returned by the API.
        """
        endpoint = f"/questions/{question_id}"
        question = self.get_items(endpoint)
        return question

    def get_all_questions_and_answers(self) -> list:
        """
        Combines API calls for questions and answers to create a list of questions with a list
        of answers nested within each question object.

        Returns:
            list: A list of dictionaries representing questions, where each question dictionary
                includes a list of answers.
        """

        questions = self.get_questions()

        for question in questions:
            question['answers'] = self.get_answers(question['id'])

        return questions

    def get_all_questions_answers_and_comments(self) -> list:
        """
        Combines API calls to retrieve questions, answers, and comments for each question.

        Returns:
            list: A list of dictionaries representing questions, where each question dictionary
                includes a list of answers and comments for each answer. If no comments are present
                for an answer, an empty list is included.
        """
        questions = self.get_questions()

        for question in questions:
            question['answers'] = self.get_answers(question['id'])
            question['comments'] = self.get_question_comments(question['id'])

            for answer in question['answers']:
                if answer['commentCount'] > 0:
                    answer['comments'] = self.get_answer_comments(question['id'], answer['id'])
                else:
                    answer['comments'] = []

        return questions

    def add_question(self, title: str, body: str, tags: list, impersonation: bool = False) -> dict:
        """
        Create a new question in the system.

        Args:
            title (str): The title of the question.
            body (str): The body of the question.
            tags (list): A list of strings representing tags for the question. Tags that do not
            already exist will be automatically created.
            impersonation (bool, optional): Flag indicating whether the question should be created
            using user impersonation. Defaults to False.

        Returns:
            dict: A dictionary representing the newly created question.
        """
        endpoint = "/questions"
        params = {
            "title": title,
            "body": body,
            "tags": tags
        }

        new_question = self.add_item(endpoint, params, impersonation=impersonation)
        return new_question

    def edit_question(self, question_id: int, title: str = None, body: str = None,
                      tags: list = None) -> dict:
        """
        Edit all or part of a question by providing new title, body, and/or tags, leaving
        the other parts of the question the same.

        The default API endpoint offers too much opportunity for the user to accidentally
        overwrite portions of a question that they did not intend to. This wrapper method allows
        the user to submit which question fields they wish to edit. The remaining fields will be
        filled in by performing an API call to obtain the current state of the question.

        Args:
            question_id (int): The unique identifier of the question to be edited.
            title (str, optional): The new title for the question. If not provided, the original
                title will be used.
            body (str, optional): The new body content for the question. If not provided, the
                original body will be used.
            tags (list of str, optional): A list of strings representing the new tags for the
                question. If not provided, the original tags will be used.

        Returns:
            dict: A dictionary containing the edited question details as returned by the API.
        """
        endpoint = f"/questions/{question_id}"

        if None in [title, body, tags]:
            original_question = self.get_question_by_id(question_id)

        params = {
            'title': title if title is not None else original_question['title'],
            'body': body if body is not None else original_question['body'],
            'tags': tags if tags is not None else [tag["name"] for tag in original_question['tags']]
        }

        edited_question = self.edit_item(endpoint, params)
        return edited_question

    def get_question_comments(self, question_id: int) -> list:
        """
        Retrieve comments for a specific question identified by its ID.
        Comments are always sorted by creationDate, in ascending order.

        Args:
            question_id (int): The unique identifier of the question for which comments are to be
                retrieved.

        Returns:
            list: A list of dictionaries representing comments associated with the specified
                question.
        """
        endpoint = f"/questions/{question_id}/comments"

        comments = self.get_items(endpoint)
        return comments

    def delete_question(self, question_id: int):
        """
        Delete a question from the Stack Overflow for Teams instance.

        Args:
            question_id (int): The unique identifier of the question to be deleted.

        Returns:
            None
        """
        endpoint = f"/questions/{question_id}"
        self.delete_item(endpoint)
        # Aside from an HTTP 204 response, there is nothing to return

    # ======================
    # --- ANSWER METHODS ---
    # ======================

    def get_answers(self, question_id: int, page: int = None, pagesize: int = None,
                    sort: str = None, order: str = None) -> list:
        """
    Retrieve a list of answers for a specific question identified by its ID.

    Args:
        question_id (int): The unique identifier of the question for which answers are to be
            retrieved.
        page (int, optional): The pagination offset response. Defaults to 1.
        pagesize (int, optional): The number of answers per page. Can be 15, 30, 50, or 100.
            Defaults to 100.
        sort (str, optional): The field by which the answers should be sorted.
            Can be 'creation'. Defaults to 'creation'.
        order (str, optional): The order in which the answers should be sorted.
            Can be 'asc' (ascending) or 'desc' (descending). Defaults to 'desc'.

    Returns:
        list: A list of answers for the specified question, based on the provided criteria.
    """
        endpoint = f"/questions/{question_id}/answers"
        params = {
            'page': page if isinstance(page, int) else 1,
            'pageSize': pagesize if pagesize in [15, 30, 50, 100] else 100,
            'sort': sort if isinstance(sort, str) else 'creation',
            "order": order if order in ['asc', 'desc'] else 'asc',
        }
        answers = self.get_items(endpoint, params)
        return answers

    def get_answer_by_id(self, question_id: int, answer_id: int) -> dict:
        """
        Retrieve a specific answer by its ID for a given question.

        Args:
            question_id (int): The unique identifier of the question to which the answer belongs.
            answer_id (int): The unique identifier of the answer to retrieve.

        Returns:
            dict: A dictionary containing the details of the answer as returned by the API.
        """
        endpoint = f"/questions/{question_id}/answers/{answer_id}"
        answer = self.get_items(endpoint)
        return answer

    def add_answer(self, question_id: int, body: str, impersonation: bool = False) -> dict:
        """
        Add a new answer to a specific question.

        Args:
            question_id (int): The unique identifier of the question to which the answer belongs.
            body (str): The body content of the answer.
            impersonation (bool, optional): Flag indicating whether the answer should be added
                using user impersonation. Defaults to False.

        Returns:
            dict: A dictionary representing the newly created answer.
        """
        endpoint = f"/questions/{question_id}/answers"
        params = {
            "body": body,
        }

        new_answer = self.add_item(endpoint, params, impersonation=impersonation)
        return new_answer

    def get_answer_comments(self, question_id: int, answer_id: int) -> list:
        """
        Retrieve comments for a specific answer identified by its question ID and answer ID.
        Comments are always sorted by creationDate, in ascending order.

        Args:
            question_id (int): The unique identifier of the question to which the answer belongs.
            answer_id (int): The unique identifier of the answer for which comments are to be
                retrieved.

        Returns:
            list: A list of dictionaries representing comments associated with the specified answer.
        """
        endpoint = f"/questions/{question_id}/answers/{answer_id}/comments"
        comments = self.get_items(endpoint)
        return comments

    def get_all_answers(self) -> list:
        """
        Retrieve all answers for all questions.

        This method retrieves all answers for all questions available in the Stack Overflow for
        Teams instance.
            * It first fetches all questions using the 'get_all_questions' method.
            * Then, for each question, it retrieves the answers using the 'get_answers' method.
            * For each answer, it adds a key 'questionTags' containing the tags of the
                corresponding question.
            * Finally, it returns a list of all answers.

        Returns:
            list: A list of dictionaries representing answers, where each answer dictionary
                includes the question tags it belongs to.
        """
        questions = self.get_all_questions()

        all_answers = []
        for question in questions:
            answers = self.get_answers(question['id'])
            for answer in answers:
                answer['questionTags'] = question['tags']

            all_answers.append(answers)

        return answers

    def delete_answer(self, question_id: int, answer_id: int):
        """
        Delete a specific answer from a question in the Stack Overflow for Teams instance.

        Args:
            question_id (int): The unique identifier of the question from which the answer will be
                deleted.
            answer_id (int): The unique identifier of the answer to be deleted.

        Returns:
            None
        """
        endpoint = f"/questions/{question_id}/answers/{answer_id}"
        self.delete_item(endpoint)

    # =======================
    # --- ARTICLE METHODS ---
    # =======================

    def get_articles(self, page: int = None, pagesize: int = None,
                     sort: str = None, order: str = None,
                     tag_ids: list = None, author_id: int = None,
                     start_date: str = None, end_date: str = None,
                     one_page_limit: bool = False) -> list:
        """
        Retrieve a list of articles based on the specified criteria.

        Args:
            page (int, optional): The pagination offset response. Defaults to 1.
            pagesize (int, optional): The number of articles per page. Can be 15, 30, 50, or 100.
                Defaults to 100.
            sort (str, optional): The field by which the articles should be sorted. Can be
                'creation', 'activity', or 'score'. Defaults to 'creation'.
            order (str, optional): The order in which the articles should be sorted. Can be
                'asc' (ascending) or 'desc' (descending). Defaults to 'asc'.
            tag_ids (list of int, optional): The IDs of specific tags to filter articles by.
            author_id (int, optional): The ID of the author to filter articles by.
            start_date (str, optional): The start date for filtering articles.
                Format: 'YYYY-MM' or 'YYYY-MM-DD'.
            end_date (str, optional): The end date for filtering articles.
                Format: 'YYYY-MM' or 'YYYY-MM-DD'.

        Returns:
            list: A list of articles that match the specified criteria.
        """

        endpoint = "/articles"
        params = {
            'page': page if isinstance(page, int) else 1,
            'pageSize': pagesize if pagesize in [15, 30, 50, 100] else 100,
            'sort': sort if isinstance(sort, str) else 'creation',
            "order": order if order in ['asc', 'desc'] else 'asc',
            "tagId": tag_ids if isinstance(tag_ids, list) else None,
            "authorId": author_id if isinstance(author_id, int) else None,
            "from": start_date if isinstance(start_date, str) else None,
            "to": end_date if isinstance(end_date, str) else None
        }

        articles = self.get_items(endpoint, params, one_page_limit=one_page_limit)
        return articles

    def get_article_by_id(self, article_id: int) -> dict:
        """
        Retrieve a specific article by its ID.

        Args:
            article_id (int): The unique identifier of the article to retrieve.

        Returns:
            dict: A dictionary containing the details of the article as returned by the API.
        """
        endpoint = f"/articles/{article_id}"
        article = self.get_items(endpoint)
        return article

    def add_article(self, title: str, body: str, article_type: str, tags: list,
                    editable_by: str = 'ownerOnly', editor_user_ids: list = [],
                    editor_user_group_ids: list = [], impersonation=False) -> dict:
        """
        Create a new article in the system.

        Args:
            title (str): The title of the article.
            body (str): The body of the article.
            article_type (str): The type of the article. Must be one of:
                'knowledgeArticle', 'announcement', 'policy', or 'howToGuide'.
            tags (list): A list of strings representing tags for the article.
            editable_by (str, optional): Who can edit the article. Must be one of:
                'ownerOnly', 'specificEditors', or 'everyone'. Defaults to 'ownerOnly'.
            editorUserIds (list, optional): A list of integers representing specific users
                who can edit the article. Defaults to None.
            editorUserGroupIds (list, optional): A list of integers representing user groups
                who can edit the article. Defaults to None.
            impersonation (bool, optional): Flag indicating whether the article should be
                created using user impersonation. Defaults to False.

        Returns:
            dict: A dictionary representing the newly created article.
        """
        endpoint = "/articles"
        params = {
            "title": title,
            "body": body,
            "type": article_type,
            "tags": tags,
            "permissions": {
                "editableBy": editable_by,
                "editorUserIds": editor_user_ids,
                "editorUserGroupIds": editor_user_group_ids
            }
        }

        new_article = self.add_item(endpoint, params, impersonation=impersonation)
        return new_article

    def edit_article(self, article_id: int, title: str = None, body: str = None,
                     article_type: str = None, tags: list = None, editable_by: str = None,
                     editor_user_ids: list = None, editor_user_group_ids: list = None,
                     impersonation=False) -> dict:
        """
        Edit all or part of a article by providing new title, body, and/or tags, leaving
        the other parts of the article the same.

        The default API endpoint offers too much opportunity for the user to accidentally
        overwrite portions of an article that they did not intend to. This wrapper method allows
        the user to submit which article fields they wish to edit. The remaining fields will be
        filled in by performing an API call to obtain the current state of the article.

        Args:
            article_id (int): The unique identifier of the article to be edited.
            title (str, optional): The new title for the article. If not provided, the original
                title will be used.
            body (str, optional): The new body content for the article. If not provided, the
                original body will be used.
            article_type (str, optional): The new type for the article. If not provided, the
                original type will be used.
            tags (list of str, optional): A list of strings representing the new tags for the
                article. If not provided, the original tags will be used.
            editable_by (str, optional): Who can edit the article. Must be one of:
                'ownerOnly', 'specificEditors', or 'everyone'. If not provided, the original
                editableBy value will be used.
            editor_user_ids (list of int, optional): A list of integers representing specific users
                who can edit the article. If not provided, the original editorUserIds will be used.
            editor_user_group_ids (list of int, optional): A list of integers representing user
                groups who can edit the article. If not provided, the original editorUserGroupIds
                will be used.
            impersonation (bool, optional): Flag indicating whether the article should be
                edited using user impersonation. Defaults to False.

        Returns:
            dict: A dictionary containing the edited article details as returned by the API.
        """
        endpoint = f"/articles/{article_id}"

        if None in [title, body, article_type, tags, editable_by, editor_user_ids,
                    editor_user_group_ids]:
            original_article = self.get_article_by_id(article_id)

        params = {
            'title': title if title is not None else original_article['title'],
            'body': body if body is not None else original_article['body'],
            'type': article_type if article_type is not None else original_article['type'],
            'tags': tags if tags is not None else [tag["name"] for tag in original_article['tags']],
            "permissions": {
                "editableBy": editable_by if editable_by is not None else
                original_article['permissions']['editableBy'],
                "editorUserIds": editor_user_ids if editor_user_ids is not None else
                [user['id'] for user in original_article['permissions']['editorUsers']],
                "editorUserGroupIds": editor_user_group_ids if editor_user_group_ids is not None
                else [group['id'] for group in original_article['permissions']['editorUserGroups']]
            }
        }

        edited_article = self.edit_item(endpoint, params, impersonation=impersonation)
        return edited_article

    def delete_article(self, article_id):
        """
        Delete a specific article from the Stack Overflow for Teams instance.

        Args:
            article_id (int): The unique identifier of the article to be deleted.

        Returns:
            None
        """
        endpoint = f"/articles/{article_id}"
        self.delete_item(endpoint)

    # ===================
    # --- TAG METHODS ---
    # ===================

    def get_tags(self, page: int = None, pagesize: int = None,
                 sort: str = None, order: str = None,
                 partial_name: str = None, has_smes: bool = None,
                 one_page_limit: bool = False) -> list:
        """
        Retrieve a list of tags based on the specified criteria.

        Args:
            page (int, optional): The page number for pagination. Defaults to 1.
            pagesize (int, optional): The number of tags per page. Can be 15, 30, 50, or 100.
                Defaults to 100.
            sort (str, optional): The field by which the tags should be sorted.
                Defaults to 'creationDate'.
            order (str, optional): The order in which the tags should be sorted.
                Can be 'asc' (ascending) or 'desc' (descending). Defaults to 'asc'.
            partial_name (str, optional): A partial name to filter tags by. Defaults to None.
            has_smes (bool, optional): Flag indicating whether the tags should contain subject
                matter experts. Defaults to None.
            one_page_limit (bool, optional): Flag indicating whether to limit the results to one
                page. Defaults to False.

        Returns:
            list: A list of tags matching the specified criteria.
        """
        endpoint = "/tags"
        params = {
            'page': page if isinstance(page, int) else 1,
            'pageSize': pagesize if pagesize in [15, 30, 50, 100] else 100,
            'sort': sort if isinstance(sort, str) else 'creationDate',
            "order": order if order in ['asc', 'desc'] else 'asc',
            "partialName": partial_name if isinstance(partial_name, str) else None,
            "hasSmes": has_smes if isinstance(has_smes, bool) else None
        }

        tags = self.get_items(endpoint, params, one_page_limit=one_page_limit)
        return tags

    def get_tag_by_id(self, tag_id: int) -> dict:
        """
        Retrieve a specific tag by its ID.

        Args:
            tag_id (int): The unique identifier of the tag to retrieve.

        Returns:
            dict: A dictionary containing the details of the tag as returned by the API.
        """
        endpoint = f"/tags/{tag_id}"
        tag = self.get_items(endpoint)
        return tag

    def get_tag_by_name(self, tag_name: str) -> int:
        """
        Retrieve a specific tag by its name.

        This method takes a tag name as input and searches for a tag with an exact match to the
        provided name.
        If a tag with the exact name is found, the method returns the tag details in a dictionary
        format.
        If no tag with the exact name is found, a `NotFoundError` is raised.

        Args:
            tag_name (str): The name of the tag to retrieve.

        Returns:
            dict: A dictionary containing the details of the tag if found.

        Raises:
            NotFoundError: If no tags match the provided tag name.
        """
        tags = self.get_tags(partial_name=tag_name.lower())

        for tag in tags:
            if tag['name'] == tag_name:
                return tag

        raise NotFoundError("No tags match the name '{tag_name}'")

    def get_tag_smes(self, tag_id):
        """
        Retrieve the subject matter experts (SMEs) associated with a specific tag identified by
        its ID.

        Args:
            tag_id (int): The unique identifier of the tag for which SMEs are to be retrieved.

        Returns:
            list: A list of dictionaries representing the SMEs associated with the specified tag.
        """
        endpoint = f"/tags/{tag_id}/subject-matter-experts"
        smes = self.get_items(endpoint)
        return smes

    def edit_tag_smes(self, tag_id: int, user_ids: list = [], group_ids: list = []) -> dict:
        """
        Edit the subject matter experts (SMEs) associated with a specific tag identified by its ID.
        This method overwrites all existing SMEs for the specified tag with the provided
        parameters.

        Args:
            tag_id (int): The unique identifier of the tag for which SMEs are to be edited.
            user_ids (list): A list of integers representing specific users to be set as SMEs for
                the tag.
            group_ids (list): A list of integers representing user groups to be set as SMEs for
                the tag.

        Returns:
            dict: A dictionary containing the edited SMEs details as returned by the API.
        """
        endpoint = f"/tags/{tag_id}/subject-matter-experts"
        params = {
            "userIds": user_ids,
            "userGroupIds": group_ids
        }
        edited_smes = self.edit_item(endpoint, params)
        return edited_smes

    def add_sme_users(self, tag_id: int, user_ids: list) -> dict:
        """
        Add subject matter expert (SME) users to a specific tag identified by its ID.

        Args:
            tag_id (int): The unique identifier of the tag for which SME users are to be added.
            user_ids (list): A list of integers representing specific users to be set as SMEs
                for the tag.

        Returns:
            dict: A dictionary containing the updated SME details as returned by the API.
        """
        endpoint = f"/tags/{tag_id}/subject-matter-experts/users"
        params = user_ids
        updated_smes = self.add_item(endpoint, params)
        return updated_smes

    def add_sme_groups(self, tag_id: int, group_ids: list) -> dict:
        """
        Add subject matter expert (SME) user groups to a specific tag identified by its ID.

        Args:
            tag_id (int): The unique identifier of the tag for which SME user groups are to be
                added.
            group_ids (list): A list of integers representing user groups to be set as SMEs for
                the tag.

        Returns:
            dict: A dictionary containing the updated SME details as returned by the API.
        """
        endpoint = f"/tags/{tag_id}/subject-matter-experts/user-groups"
        params = group_ids
        updated_smes = self.add_item(endpoint, params)
        return updated_smes

    def remove_sme_user(self, tag_id: int, user_id: int):
        """
        Remove a specific user from the subject matter experts (SMEs) associated with a specific
        tag.

        Args:
            tag_id (int): The unique identifier of the tag from which the user is to be removed.
            user_id (int): The unique identifier of the user to be removed from the SMEs of the
                tag.

        Returns:
            None
        """
        endpoint = f"/tags/{tag_id}/subject-matter-experts/users/{user_id}"
        self.delete_item(endpoint)

    def remove_sme_group(self, tag_id: int, group_id: int):
        """
        Remove a specific user group from the subject matter experts (SMEs) associated with a
        specific tag.

        Args:
            tag_id (int): The unique identifier of the tag from which the user group is to
                be removed.
            group_id (int): The unique identifier of the user group to be removed from the
                SMEs of the tag.

        Returns:
            None
        """
        endpoint = f"/tags/{tag_id}/subject-matter-experts/user-groups/{group_id}"
        self.delete_item(endpoint)

    def get_all_tags_and_smes(self) -> list:
        """
        Retrieve all tags and their associated subject matter experts (SMEs).

        This method fetches all tags available in the Stack Overflow for Teams instance and,
        for each tag, retrieves the associated SMEs. If a tag has SMEs, it includes a list
        of users and user groups under the 'smes' key in the tag dictionary. If a tag has no
        SMEs, it includes an empty list for both users and user groups.

        Returns:
            list: A list of dictionaries representing tags, where each tag dictionary may
                include a list of SMEs under the 'smes' key.
        """
        tags = self.get_tags()

        for tag in tags:
            if tag['subjectMatterExpertCount'] > 0:
                tag['smes'] = self.get_tag_smes(tag['id'])
            else:
                tag['smes'] = {'users': [], 'userGroups': []}

        return tags

    # ====================
    # --- USER METHODS ---
    # ====================

    def get_users(self,
                  page: int = None, pagesize: int = None,
                  sort: str = None, order: str = None,
                  one_page_limit: bool = False) -> list:
        """
        Retrieve a list of users from the Stack Overflow for Teams instance.

        Args:
            page (int, optional): The page number for pagination. Defaults to 1.
            pagesize (int, optional): The number of users per page. Can be 15, 30, 50, or 100.
                Defaults to 100.
            sort (str, optional): The field by which the users should be sorted.
                Defaults to 'reputation'.
            order (str, optional): The order in which the users should be sorted.
                Can be 'asc' (ascending) or 'desc' (descending). Defaults to 'desc'.
            one_page_limit (bool, optional): Flag indicating whether to limit the results to one
                page. Defaults to False.

        Returns:
            list: A list of users matching the specified criteria.
        """
        endpoint = "/users"
        params = {
            'page': page if isinstance(page, int) else 1,
            'pageSize': pagesize if pagesize in [15, 30, 50, 100] else 100,
            'sort': sort if isinstance(sort, str) else 'reputation',
            "order": order if order in ['asc', 'desc'] else 'desc',
        }

        users = self.get_items(endpoint, params, one_page_limit=one_page_limit)
        return users

    def get_user_by_id(self, user_id: int) -> dict:
        """
        Retrieve a specific user by their ID.

        Args:
            user_id (int): The unique identifier of the user to retrieve.

        Returns:
            dict: A dictionary containing the details of the user as returned by the API.
        """
        endpoint = f"/users/{user_id}"
        user = self.get_items(endpoint)
        return user

    def get_user_by_email(self, email: str) -> dict:
        """
        Retrieve a specific user by their email address.

        This method requires admin permissions, as only admins can access a user's email
        address via the API. The email comparison is not case-sensitive.

        Args:
            email (str): The email address of the user to retrieve.

        Returns:
            dict: A dictionary containing the details of the user as returned by the API.
        """
        endpoint = f"/users/by-email/{email}"
        user = self.get_items(endpoint)
        return user

    def get_account_id_by_user_id(self, user_id: int) -> int:
        """
        Helpful for other API functions that require the account ID of users, such as
        impersonation or SCIM.

        Args:
            user_id (int): The unique identifier of the user for which the account ID is needed.

        Returns:
            int: The account ID of the specified user.
        """
        user = self.get_user_by_id(user_id)
        account_id = user['accountId']
        return account_id

    def get_account_id_by_email(self, email: str) -> int:
        """
        Helpful for other API functions that require the account ID of users, such as
        impersonation or SCIM.

        Requires admin permissions; only admins can see a user's email address via API.
        Email is not case-sensitive.

        Args:
            email (str): The email address of the user to retrieve the account ID for.

        Returns:
            int: The account ID of the user with the specified email address.
        """
        user = self.get_user_by_email(email)
        account_id = user['accountId']
        return account_id

    def get_myself(self, impersonation: bool = False) -> dict:
        """
        Retrieve the details of the authenticated user.

        Args:
            impersonation (bool, optional): Flag indicating whether the request should be made
                using user impersonation. Defaults to False.

        Returns:
            dict: A dictionary containing the details of the authenticated user as returned by the
                API.
        """
        endpoint = "/users/me"
        myself = self.get_items(endpoint, impersonation=impersonation)
        return myself

    # ==========================
    # --- USER GROUP METHODS ---
    # ==========================

    def get_user_groups(self, page: int = None, pagesize: int = None,
                        sort: str = None, order: str = None) -> list:
        """
        Retrieve a list of user groups from the Stack Overflow for Teams instance.

        Args:
            page (int, optional): The page number for pagination. Defaults to 1.
            pagesize (int, optional): The number of user groups per page.
                Can be 15, 30, 50, or 100. Defaults to 100.
            sort (str, optional): The field by which the user groups should be sorted.
                Can be 'name' or 'size'. Defaults to 'name'.
            order (str, optional): The order in which the user groups should be sorted.
                Can be 'asc' (ascending) or 'desc' (descending). Defaults to 'desc'.

        Returns:
            list: A list of user groups matching the specified criteria.
        """
        endpoint = "/user-groups"
        params = {
            'page': page if isinstance(page, int) else 1,
            'pageSize': pagesize if pagesize in [15, 30, 50, 100] else 100,
            'sort': sort if isinstance(sort, str) else 'name',
            "order": order if order in ['asc', 'desc'] else 'desc',
        }

        user_groups = self.get_items(endpoint, params)
        return user_groups

    def get_user_group_by_id(self, group_id: int) -> dict:
        """
        Retrieve a specific user group by its ID.

        Args:
            group_id (int): The unique identifier of the user group to retrieve.

        Returns:
            dict: A dictionary containing the details of the user group as returned by the API.
        """
        endpoint = f"/user-groups/{group_id}"
        group = self.get_items(endpoint)
        return group

    def add_user_group(self, name: str, user_ids: list, description: str = None) -> dict:
        """
        Add a new user group to the Stack Overflow for Teams instance.

        Args:
            name (str): The name of the user group.
            user_ids (list): A list of user IDs to be added to the user group.
            description (str, optional): A description of the user group, defaults to None.

        Returns:
            dict: A dictionary representing the newly created user group.
        """
        endpoint = "/user-groups"
        params = {
            "name": name,
            "userIds": user_ids,
            "description": description
        }

        new_group = self.add_item(endpoint, params)
        return new_group

    def edit_user_group(self, group_id: int, name: str = None,
                        user_ids: list = None, description: str = None) -> dict:
        """
        Edit a user group by providing new name, user IDs, and/or description.

        Args:
            group_id (int): The unique identifier of the user group to be edited.
            name (str, optional): The new name for the user group. If not provided, the
                original name will be used.
            user_ids (list, optional): A list of integers representing specific users to
                be part of the user group. If not provided, the original user IDs will be used.
            description (str, optional): The new description for the user group. If not
                provided, the original description will be used.

        Returns:
            dict: A dictionary containing the edited user group details as returned by the API.
        """
        endpoint = f"/user-groups/{group_id}"
        if None in [name, user_ids, description]:
            original_group = self.get_user_group_by_id(group_id)

        params = {
            'name': name if name is not None else original_group['name'],
            'userIds': user_ids if user_ids is not None else [user['id'] for user in
                                                              original_group['users']],
            'description': description if description is not None else original_group['description']
        }
        edited_group = self.edit_item(endpoint, params)
        return edited_group

    def add_users_to_group(self, group_id: int, user_ids: list) -> dict:
        """
        Add users to a specific user group identified by its group ID.

        Args:
            group_id (int): The unique identifier of the user group to which users will be added.
            user_ids (list): A list of integers representing the user IDs to be added to the user
                group.

        Returns:
            dict: A dictionary containing the updated user group details as returned by the API.
        """
        endpoint = f"/user-groups/{group_id}/members"
        params = user_ids
        updated_group = self.add_item(endpoint, params)
        return updated_group

    def delete_user_from_group(self, group_id: int, user_id: int):
        """
        Delete a specific user from a user group in the Stack Overflow for Teams instance.

        Args:
            group_id (int): The unique identifier of the user group from which the user is to be
                removed.
            user_id (int): The unique identifier of the user to be removed from the user group.

        Returns:
            None
        """
        endpoint = f"/user-groups/{group_id}/members/{user_id}"
        self.delete_item(endpoint)

    # ======================
    # --- SEARCH METHODS ---
    # ======================

    def get_search_results(self, query: str, page: int = None, pagesize: int = None,
                           sort: str = None, one_page_limit: bool = True) -> list:
        """
        Get a list of search results based on the provided query.

        As of June 2024, the endpoint always returns exactly 100 results, regardless of page size.

        Args:
            query (str): The search query to be used.
            page (int, optional): The page number for pagination. Defaults to 1.
            pagesize (int, optional): The number of search results per page.
                Can be 15, 30, 50, or 100. Defaults to 100.
            sort (str, optional): The field by which the search results should be sorted.
                Can be 'relevance', 'newest', 'active', or 'score'. Defaults to 'relevance'.
                Sorted results are always in descending order.
            one_page_limit (bool, optional): Flag indicating whether to limit the results to
                one page. Defaults to True.

        Returns:
            list: A list of search results matching the specified query.
        """
        endpoint = "/search"
        params = {
            'query': query,
            'page': page if isinstance(page, int) else 1,
            'pageSize': pagesize if pagesize in [15, 30, 50, 100] else 100,
            'sort': sort if isinstance(sort, str) else 'relevance',
        }
        search_results = self.get_items(endpoint, params, one_page_limit=one_page_limit)
        return search_results

    # =========================
    # --- COMMUNITY METHODS ---
    # =========================

    # As of June 2024, there are no API endpoints for creating/deleting communities

    def get_communities(self, page: int = None, pagesize: int = None,
                        sort: str = None, order: str = None) -> list:
        """
        Retrieve a list of communities from the Stack Overflow for Teams instance.

        Args:
            page (int, optional): The page number for pagination. Defaults to 1.
            pagesize (int, optional): The number of communities per page.
                Can be 15, 30, 50, or 100. Defaults to 100.
            sort (str, optional): The field by which the communities should be sorted.
                Can be 'name' or 'size'. Defaults to 'name'.
            order (str, optional): The order in which the communities should be sorted.
                Can be 'asc' (ascending) or 'desc' (descending). Defaults to 'asc'.

        Returns:
            list: A list of communities matching the specified criteria.
        """
        endpoint = "/communities"
        params = {
            'page': page if isinstance(page, int) else 1,
            'pageSize': pagesize if pagesize in [15, 30, 50, 100] else 100,
            'sort': sort if isinstance(sort, str) else 'name',
            "order": order if order in ['asc', 'desc'] else 'asc',
        }

        communities = self.get_items(endpoint, params)
        return communities

    def get_community_by_id(self, community_id: int) -> dict:
        """
        Retrieve a specific community by its ID.

        Args:
            community_id (int): The unique identifier of the community to retrieve.

        Returns:
            dict: A dictionary containing the details of the community as returned by the API.
        """
        endpoint = f"/communities/{community_id}"
        community = self.get_items(endpoint)
        return community

    def join_community(self, community_id: int):
        """
        Join a community in the Stack Overflow for Teams instance.
        This method allows the authenticated user to join a specific community identified by its
        ID.

        Args:
            community_id (int): The unique identifier of the community to join.

        Returns:
            dict: A dictionary containing the updated details of the community after the user has
                joined.
        """
        endpoint = f"/communities/{community_id}/join"
        updated_community = self.add_item(endpoint)
        return updated_community

    def leave_community(self, community_id: int):
        """
        Leave a community in the Stack Overflow for Teams instance.
        This method allows the authenticated user to leave a specific community identified by its
            ID.


        Args:
            community_id (int): The unique identifier of the community to leave.

        Returns:
            dict: A dictionary containing the updated details of the community after leaving.
        """
        endpoint = f"/communities/{community_id}/leave"

        updated_community = self.add_item(endpoint)
        return updated_community

    def add_users_to_community(self, community_id: int, user_ids: list) -> dict:
        """
        Add users to a community in the Stack Overflow for Teams instance.
        This method can add one more users to a specific community identified by its ID.

        Args:
            community_id (int): The unique identifier of the community to which users will
                be added.
            user_ids (list): A list of integers representing the user IDs to be added as members
                to the community.

        Returns:
            dict: A dictionary containing the updated details of the community after adding the
                users as members.
        """
        endpoint = f"/communities/{community_id}/join/bulk"
        params = {
            "memberUserIds": user_ids
        }
        updated_community = self.add_item(endpoint, params)
        return updated_community

    def remove_users_from_community(self, community_id: int, user_ids: list) -> dict:
        """
        Remove users from a community in the Stack Overflow for Teams instance.
        This method can remove one or more users from a specific community identified by its ID.

        Args:
            community_id (int): The unique identifier of the community from which users will be
                removed.
            user_ids (list): A list of integers representing the user IDs to be removed from the
                community.

        Returns:
            dict: A dictionary containing the updated details of the community after removing the
                specified users.
        """
        endpoint = f"/communities/{community_id}/leave/bulk"
        params = {
            "memberUserIds": user_ids
        }
        updated_community = self.add_item(endpoint, params)
        return updated_community

    # ==========================
    # --- COLLECTION METHODS ---
    # ==========================

    def get_collections(self, page: int = None, pagesize: int = None,
                        sort: str = None, order: str = None,
                        partial_title: str = None, author_ids: list = None,
                        permissions: str = None,
                        start_date: str = None, end_date: str = None,
                        one_page_limit: bool = False) -> list:
        """
        sort can be 'creation' or 'lastEdit'
        permissions can be 'all', 'owned', or 'editable'
        """
        """
        Retrieve a list of collections based on the specified criteria.

        Args:
            page (int, optional): The page number for pagination. Defaults to 1.
            pagesize (int, optional): The number of collections per page.
                Can be 15, 30, 50, or 100. Defaults to 100.
            sort (str, optional): The field by which the collections should be sorted.
                Can be 'creation' or 'lastEdit'. Defaults to 'creation'.
            order (str, optional): The order in which the collections should be sorted.
                Can be 'asc' (ascending) or 'desc' (descending). Defaults to 'asc'.
            partial_title (str, optional): A partial title to filter collections by.
                Defaults to None.
            author_ids (list of int, optional): The IDs of specific authors to filter
                collections by. Defaults to None.
            permissions (str, optional): The permissions level for the collections.
                Can be 'all', 'owned', or 'editable'. Defaults to 'all'.
            start_date (str, optional): The start date for filtering collections.
                Format: 'YYYY-MM' or 'YYYY-MM-DD'. Defaults to None.
            end_date (str, optional): The end date for filtering collections.
                Format: 'YYYY-MM' or 'YYYY-MM-DD'. Defaults to None.
            one_page_limit (bool, optional): Flag indicating whether to limit the results
                to one page. Defaults to False.

        Returns:
            list: A list of collections matching the specified criteria.
        """
        endpoint = "/collections"
        params = {
            'page': page if isinstance(page, int) else 1,
            'pageSize': pagesize if pagesize in [15, 30, 50, 100] else 100,
            'sort': sort if isinstance(sort, str) else 'creation',
            "order": order if order in ['asc', 'desc'] else 'asc',
            "partialTitle": partial_title if isinstance(partial_title, str) else None,
            "permissions": permissions if isinstance(permissions, str) else 'all',
            "authorIds": author_ids if isinstance(author_ids, list) else None,
            "from": start_date if isinstance(start_date, str) else None,
            "to": end_date if isinstance(end_date, str) else None
        }

        collections = self.get_items(endpoint, params, one_page_limit=one_page_limit)
        return collections

    def get_collection_by_id(self, collection_id: int) -> dict:
        """
        Retrieve a specific collection by its ID.

        Args:
            collection_id (int): The unique identifier of the collection to retrieve.

        Returns:
            dict: A dictionary containing the details of the collection as returned by the API.
        """
        endpoint = f"/collections/{collection_id}"
        collection = self.get_items(endpoint)
        return collection

    def add_collection(self, title: str, description: str = "", content_ids: list = [],
                       editor_user_ids: list = [], editor_user_group_ids: list = []) -> dict:
        """
        Add a new collection to the Stack Overflow for Teams instance.

        Args:
            title (str): The title of the collection.
            description (str, optional): The description of the collection,
                defaults to an empty string.
            content_ids (list, optional): A list of question and/or article IDs to be associated
                with the collection.
            editor_user_ids (list, optional): A list of user IDs who have editing access to
                the collection.
            editor_user_group_ids (list, optional): A list of user group IDs who have editing
                access to the collection.

        Returns:
            dict: A dictionary representing the newly created collection.
        """
        endpoint = "/collections"
        params = {
            'title': title,
            'description': description,
            'editorUserIds': editor_user_ids,
            'editorUserGroupIds': editor_user_group_ids,
            'contentIds': content_ids
        }

        collection = self.add_item(endpoint, params)
        return collection

    def edit_collection(self, collection_id: int, owner_id: int = None,
                        title: str = None, description: str = None,
                        content_ids: list = None, editor_user_ids: list = None,
                        editor_user_group_ids: list = None) -> dict:
        """
        Edit a collection by providing any or all of the following:
        owner ID, title, description, content IDs, editor user IDs, and/or editor user group IDs.

        Args:
            collection_id (int): The unique identifier of the collection to be edited.
            owner_id (int, optional): The new owner ID for the collection. If not provided, the
                original owner ID will be used.
            title (str, optional): The new title for the collection. If not provided, the original
                title will be used.
            description (str, optional): The new description for the collection. If not provided,
                the original description will be used.
            content_ids (list, optional): A list of questions and/or article IDs to be associated
                with the collection. If not provided, the original content IDs will be used.
            editor_user_ids (list, optional): A list of integers representing specific users who
                have editing access to the collection. If not provided, the original editor user
                IDs will be used.
            editor_user_group_ids (list, optional): A list of integers representing user groups
                who have editing access to the collection. If not provided, the original editor
                user group IDs will be used.

        Returns:
            dict: A dictionary containing the edited collection details as returned by the API.
        """
        endpoint = f"/collections/{collection_id}"
        if None in [owner_id, title, description, content_ids, editor_user_group_ids,
                    editor_user_ids]:
            original_collection = self.get_collection_by_id(collection_id)

        params = {
            'ownerId': owner_id if owner_id is not None else original_collection['owner']['id'],
            'title': title if title is not None else original_collection['title'],
            'description': description if description is not None else
            original_collection['description'],
            'editorUserIds': editor_user_ids if editor_user_ids is not None else
            [user['id'] for user in original_collection['editorUsers']],
            'editorUserGroupIds': editor_user_group_ids if editor_user_group_ids is not None else
            [group['id'] for group in original_collection['editorUserGroups']],
            'contentIds': content_ids if content_ids is not None else
            [content['id'] for content in original_collection['content']]
        }
        edited_collection = self.edit_item(endpoint, params)
        return edited_collection

    def delete_collection(self, collection_id: int):
        """
        Delete a specific collection from the Stack Overflow for Teams instance.

        Args:
            collection_id (int): The unique identifier of the collection to be deleted.

        Returns:
            None
        """
        endpoint = f"/collections/{collection_id}"
        self.delete_item(endpoint)

    # =============================
    # --- IMPERSONATION METHODS ---
    # =============================

    def get_impersonation_token(self, account_id: int) -> str:
        '''
        User impersonation:
        - is only available in Stack Overflow Enterprise
        - uses API v2.3 (rather than API v3)
        - is turned off by default and requires a support ticket to turn it on
            (support@stackoverflow.com)

        Documentation for impersonation can be found here:
        https://support.stackenterprise.co/support/solutions/articles/22000245133-service-keys-identity-delegation-and-impersonation#impersonation

        In addition to a token, an API key is required
        This can be setup during instantiation of the StackClient via the `key=APIKEY` parameter
        Or it can be manually assigned to an existing StackClient via `client_name.key = APIKEY`

        An account ID of `-1` can be used to impersonate the Community user

        Structure of successful API response:
        {
            "items":
                [
                    {
                        "scope":
                        [
                            "custom_timestamps",
                            "write_access"
                        ],
                        "exchange_type": "impersonate",
                        "account_id": 3,
                        "expires_on_date": 1717777554,
                        "original_access_token": "ORIGINAL_TOKEN_STRING",
                        "access_token": "IMPERSONATION_TOKEN_STRING"
                    }
                ],
            "has_more": false,
            "quota_max": 10000,
            "quota_remaining": 9999
        }

        Errors:
        {
            'error_id': 403,
            'error_message': 'Access denied - impersonation is only allowed via service accounts',
            'error_name': 'access_denied'
        }

        When impersonation hasn't been turned on...
        {
            'error_id': 400,
            'error_message': 'access_tokens',
            'error_name': 'bad_parameter'
        }

        Args:
            account_id (int): The account ID for which the impersonation token is requested.

        Returns:
            str: The impersonation token for the specified account ID.

        Raises:
            RequiresEnterpriseError: If user impersonation is attempted outside of Stack Overflow
                Enterprise.
            InvalidRequestError: If an API key is missing for user impersonation.

        Example:
            stack_client = StackClient(url, token, key=API_KEY)
            impersonation_token = stack_client.get_impersonation_token(account_id)
        '''

        if not self.soe:
            raise RequiresEnterpriseError(
                "User impersonation is only available in Stack Overflow Enterprise")

        if not self.key:
            raise InvalidRequestError(
                "An API key is required for user impersonation. Please recreate the StackClient"
                "with a `key=APIKEY` parameter or manually assign a key to an existing StackClient"
                "via `client_name.key = APIKEY`"
            )

        endpoint = '/access-tokens/exchange'
        endpoint_url = self.base_url + '/api/2.3' + endpoint
        headers = {'X-API-Key': self.key}
        request_url = f"{endpoint_url}?access_tokens={self.token}&exchange_type=impersonate&" \
            f"account_id={account_id}"
        logging.info(f'Impersonation token being generated for account ID {account_id}...')
        response = requests.post(request_url, headers=headers)
        self.raise_status_code_exceptions(response)

        json_data = response.json()
        impersonation_token = json_data['items'][0]['access_token']
        logging.info('Impersonation token successfully generated.')

        return impersonation_token

    def impersonate_question_by_user_id(self, title: str, body: str, tags: list,
                                        user_id: int) -> dict:
        """Creates a question on behalf of another user, identified by their user ID.

        Args:
            title (str): The title of the question.
            body (str): The body content of the question.
            tags (list of str): A list of tags associated with the question.
            user_id (int): The ID of the user on whose behalf the question is being asked.

        Returns:
            dict: A dictionary containing the details of the impersonated question, such as
                question ID, title, body, tags, and user ID.
        """
        account_id = self.get_account_id_by_user_id(user_id)
        new_question = self.impersonate_question_by_account_id(title, body, tags, account_id)
        return new_question

    def impersonate_question_by_user_email(self, title: str, body: str, tags: list,
                                           email: str) -> dict:
        """Creates a question on behalf of another user, identified by their email address.

        Args:
            title (str): The title of the question.
            body (str): The body content of the question.
            tags (list of str): A list of tags associated with the question.
            email (str): The email of the user on whose behalf the question is being asked.

        Returns:
            dict: A dictionary containing the details of the impersonated question, such as
                question ID, title, body, tags, and user ID.
        """
        account_id = self.get_account_id_by_email(email)
        new_question = self.impersonate_question_by_account_id(title, body, tags, account_id)
        return new_question

    def impersonate_question_by_account_id(self, title: str, body: str, tags: list,
                                           account_id: int) -> dict:
        """Creates a question on behalf of another user, identified by their account ID.

        Args:
            title (str): The title of the question.
            body (str): The body content of the question.
            tags (list of str): A list of tags associated with the question.
            account_id (int): The ID of the user on whose behalf the question is being asked.

        Returns:
            dict: A dictionary containing the details of the impersonated question, such as
                question ID, title, body, tags, and user ID.
        """
        self.impersonation_token = self.get_impersonation_token(account_id)
        new_question = self.add_question(title, body, tags, impersonation=True)
        return new_question

    def get_impersonated_user(self, account_id: int) -> dict:
        """
        Retrieve the details of a user by impersonating another user identified by their
        account ID.

        This method first obtains an impersonation token by calling the 'get_impersonation_token'
        method with the provided account ID. Then, it uses this token to make an API call to
        retrieve the details of the impersonated user by calling the 'get_myself' method with the
        'impersonation' flag set to True.

        Args:
            account_id (int): The account ID of the user to be impersonated.

        Returns:
            dict: A dictionary containing the details of the impersonated user as returned by the
                API.

        Raises:
            RequiresEnterpriseError: If user impersonation is attempted outside of Stack Overflow
                Enterprise.
            InvalidRequestError: If an API key is missing for user impersonation.
        """
        self.impersonation_token = self.get_impersonation_token(account_id)
        user = self.get_myself(impersonation=True)
        return user

    # ========================
    # --- HELPER FUNCTIONS ---
    # ========================

    def get_items(self, endpoint: str, params: dict = {}, impersonation: bool = False,
                  one_page_limit: bool = False):
        """
        Retrieve items from the API endpoint with pagination support.

        This method sends GET requests to the specified API endpoint with optional parameters
        for pagination and user impersonation. It retrieves items from the API response and
        combines them into a list until all items are fetched or a one-page limit is reached.

        Args:
            endpoint (str): The API endpoint to retrieve items from.
            params (dict, optional): Additional parameters to be included in the API request,
                defaults to an empty dictionary.
            impersonation (bool, optional): Flag indicating whether user impersonation should be
                used, defaults to False.
            one_page_limit (bool, optional): Flag indicating whether to limit the results to
                one page, defaults to False.

        Returns:
            list: A list of items retrieved from the API endpoint.

        Raises:
            Exception: If an unexpected response is received from the server.
            InvalidRequestError: If the request to the API endpoint is invalid.
            UnauthorizedError: If the request to the API endpoint is unauthorized.
            ForbiddenError: If the request to the API endpoint is forbidden.
            NotFoundError: If the requested resource is not found.
            BadURLError: If there is an issue with the URL.
        """
        method = GET
        items = []
        while True:
            try:
                response = self.get_api_response(method, endpoint, params=params,
                                                 impersonation=impersonation)
            except TooManyRequestsError:
                logging.warning("HTTP 429 response. Pausing API calls for 60 seconds. \n"
                                "See 'Token bucket rate limiter' for more details: \n"
                                "https://stackoverflowteams.help/en/articles/9085836-api-v3#token-bucket-rate-limiter"
                                )
                sleep(60)
                continue
            json_data = response.json()

            try:
                items += json_data['items']
            except (KeyError, TypeError):  # API endpoint only returns a single result
                logging.info(f"Successfully received data from {endpoint}")
                return json_data

            total_item_count = json_data['totalCount']
            current_count = params['page'] * params['pageSize']
            if current_count > total_item_count:
                current_count = total_item_count
            logging.info(f"Received {current_count} of {total_item_count} items from {endpoint}")

            if params['page'] == json_data['totalPages'] or one_page_limit:
                break
            params['page'] += 1

        return items

    def add_item(self, endpoint: str, params: dict = {}, impersonation: bool = False):
        """
        Add a new item to the API endpoint using a POST request.

        Args:
            endpoint (str): The API endpoint to add the item to.
            params (dict, optional): Additional parameters to be included in the API request,
                defaults to an empty dictionary.
            impersonation (bool, optional): Flag indicating whether user impersonation should
                be used, defaults to False.

        Returns:
            dict: A dictionary representing the newly created item.

        Raises:
            Exception: If an unexpected response is received from the server.
            InvalidRequestError: If the request to the API endpoint is invalid.
            UnauthorizedError: If the request to the API endpoint is unauthorized.
            ForbiddenError: If the request to the API endpoint is forbidden.
            NotFoundError: If the requested resource is not found.
            BadURLError: If there is an issue with the URL.
        """
        method = POST
        response = self.get_api_response(method, endpoint, params, impersonation=impersonation)
        new_item = response.json()
        return new_item

    def edit_item(self, endpoint: str, params: dict, impersonation: bool = False):
        """
        Edit an item in the Stack Overflow for Teams instance using the PUT method.

        Args:
            endpoint (str): The API endpoint for editing the item.
            params (dict): A dictionary containing the parameters to be updated for the item.
            impersonation (bool, optional): Flag indicating whether the request should be made
                using user impersonation. Defaults to False.

        Returns:
            dict: A dictionary containing the updated item details as returned by the API.
        """
        method = PUT
        response = self.get_api_response(method, endpoint, params, impersonation=impersonation)
        updated_item = response.json()
        return updated_item

    def delete_item(self, endpoint: str, impersonation: bool = False):
        """
        Deletes an item from the Stack Overflow for Teams instance using the specified API
        endpoint.

        Args:
            endpoint (str): The API endpoint for deleting the item.
            impersonation (bool, optional): Flag indicating whether the request should be
                made using user impersonation. Defaults to False.

        Returns:
            None
        """
        method = DELETE
        response = self.get_api_response(method, endpoint, impersonation=impersonation)

        if response.status_code == 204:
            logging.info(f"Successfully deleted item from {endpoint}")
        else:
            logging.error(f"Failed to delete item from {endpoint}")

    def get_api_response(self, method: str, endpoint: str, params: dict = {},
                         impersonation: bool = False):
        """
        Perform an API request using the specified HTTP method to the given endpoint.

        Args:
            method (str): The HTTP method to be used for the request
                (e.g., 'GET', 'POST', 'PUT', 'DELETE').
            endpoint (str): The endpoint to which the request will be made.
            params (dict, optional): The parameters to be included in the request,
                defaults to an empty dictionary.
            impersonation (bool, optional): Flag indicating whether user impersonation should
                be used, defaults to False.

        Returns:
            requests.Response: The response object containing the API response data.

        Raises:
            Custom exceptions based on the response status code:
                - BadRequestError: If the request is invalid (status code 400).
                - UnauthorizedError: If authentication is required and has failed or has not been
                    provided (status code 401).
                - ForbiddenError: If the client does not have permission to access the resource
                    (status code 403).
                - NotFoundError: If the requested resource is not found (status code 404).
                - MethodNotAllowedError: If the requested method is not allowed for the resource
                    (status code 405).
                - TooManyRequestsError: If the rate limit has been exceeded (status code 429).
                - ServerError: If the server encountered an unexpected condition (status code 500).
        """
        endpoint_url = self.api_url + endpoint
        if impersonation:
            headers = {'Authorization': f'Bearer {self.impersonation_token}'}
        else:
            headers = self.s.headers

        request_type = getattr(self.s, method, None)  # get the method from the requests library
        if method == GET:
            response = request_type(endpoint_url, headers=headers, params=params,
                                    verify=self.ssl_verify, proxies=self.proxies)
        else:
            response = request_type(endpoint_url, headers=headers, json=params,
                                    verify=self.ssl_verify, proxies=self.proxies)

        self.raise_status_code_exceptions(response)  # check errors and raise exceptions as needed

        return response

    def raise_status_code_exceptions(self, response: requests.Response) -> None:
        """
            Parses the response codes and raises appropriate errors if necessary.

            Args:
                response (requests.Response): The response object from the API request.

            Raises:
                InvalidRequestError: If the response status code is 400.
                UnauthorizedError: If the response status code is 401 and the product is Stack
                    Overflow Enterprise.
                BadURLError: If the response status code is 401 and the URL is incorrect, or if
                    the URL domain is correct but the team slug is not.
                ForbiddenError: If the response status code is 403.
                NotFoundError: If the response status code is 404 and the requested object is not
                    found.
                BadURLError: If the response status code is 404 and the URL is incorrect.
                BadURLError: If the response status code is 500 and the product is not Stack
                    Overflow Enterprise.
                Exception: If an unexpected response is received from the server.

            Returns:
                None
        """
        if response.status_code not in [200, 201, 204]:
            try:
                error_message = response.json()
            except json.decoder.JSONDecodeError:
                error_message = response.text

            if response.status_code == 400:
                if error_message.get('error_message') == 'access_tokens' and \
                        error_message.get('error_name') == 'bad_parameter':
                    raise InvalidRequestError('Please make sure you have enabled impersonation.'
                                              ' If not, please contact support@stackoverflow.com'
                                              f'\n {error_message}')
                else:
                    raise InvalidRequestError(error_message)

            elif response.status_code == 401 and self.soe:
                raise UnauthorizedError(error_message)

            elif response.status_code == 401:
                # On Business, a 401 error can be a false positive when the URL is incorrect
                # Particularly when the URL domain is correct, but the team slug is not
                # The following test is used to distinguish between the two possible scenarios
                url_test = requests.get(self.base_url)
                if url_test.status_code == 404:
                    raise BadURLError(self.base_url)
                else:
                    raise UnauthorizedError(error_message)

            elif response.status_code == 403:
                raise ForbiddenError(error_message)

            elif response.status_code == 404:
                if type(error_message) is dict:
                    # If a dictionary is returned, the 404 means the requested object is not found
                    raise NotFoundError(error_message)
                else:  # Otherwise, it's likely a bad URL
                    raise BadURLError(response.url)

            elif response.status_code == 429:
                # Throttling documentation:
                # https://stackoverflowteams.help/en/articles/9085836-api-v3
                raise TooManyRequestsError(f"Too many API requests being sent. Headers: "
                                           f"{response.headers}")

            elif response.status_code == 500 and not self.soe:
                # 500 errors can happen when the URL for a Business instance is incorrect
                raise BadURLError(self.base_url)

            # elif response.status_code >= 500:
            #     raise ServerError(error_message)
            # elif response.status_code >= 400:
            #     raise ClientError(error_message)

            else:
                raise Exception(f"Encountered an unexpected response from server: {error_message}."
                                f" Status Code: {response.status_code}")

    def export_to_json(self, file_name: str, data: list | dict, directory: str = None):
        """
        Write the contents of the provided data (list or dictionary) to a JSON file.

        Args:
            file_name (str): The name of the JSON file to be created or overwritten.
            data (list or dict): The data to be written to the JSON file.
            directory (str, optional): The directory where the JSON file should be saved.
                If provided and the directory does not exist, it will be created. Defaults to None.

        Returns:
            None
        """
        json_extension = '.json'
        if not file_name.endswith(json_extension):
            file_name = file_name + json_extension

        if directory:
            if not os.path.exists(directory):
                os.makedirs(directory)
            file_path = os.path.join(directory, file_name)
        else:
            file_path = file_name

        with open(file_path, 'w') as f:
            json.dump(data, f, indent=4)


class APIError(Exception):
    """Base class for API errors."""
    pass


class InvalidRequestError(APIError):
    """Raised when an invalid request is made.

    Results in an HTTP 400 status code.
    This can happen when a required parameter is missing or an invalid value is provided.

    Example error messages:

    {
        "errors": {
            "Title": [
                "The Title field is required."
            ]
        },
        "type": "https://tools.ietf.org/html/rfc7231#section-6.5.1",
        "title": "One or more validation errors occurred.",
        "status": 400,
        "traceId": "00-66618f1300000000827d0749a0630a8d-f2a87cd674860b4b-01"
    }

    {
        "type": "/v3/errors/questions/ValidationErrors",
        "title": "Question not created",
        "status": 400,
        "detail": "Title cannot be longer than 150 characters."
    }

    {
        "type": "/v3/errors/questions/ValidationErrors",
        "title": "Question not created",
        "status": 400,
        "detail": "This post appears to be a duplicate of another post."
    }

    {
        "type": "/v3/errors/questions/ValidationErrors",
        "title": "Question not created",
        "status": 400,
        "detail": "A question with that title already exists; please be more specific."
    }

    {
        'type': '/v3/errors/delete/QuestionAlreadyDeleted',
        'title': 'Question already deleted.',
        'status': 400,
        'detail': 'This post is already deleted'
    }
    """
    pass


class UnauthorizedError(APIError):
    """Raised when an invalid access token is encountered.

    Results in an HTTP 401 status code.
    """
    pass


class ForbiddenError(APIError):
    """Raised when an invalid access token is encountered.

    Results in an HTTP 403 status code.
    Can be the result of a few different scenarios:

    - The access token is being used to perform a write operation and the token has not been
        write-enabled
    - The access token was created by a user who does not have permissions to perform a given
        operation. Certain API actions require the user to have moderator or administrator
        priveleges in the product.

    In the latter case, the `get_myself` endpoint can be used to validate the user's permissions.
    For the `role` field are two different permissions values: 'Registered' and 'Moderator'.
    Registered users have the most basic access and canleverage a subset of the API's full
    capabilities.

    Example error message:

    {
        "type": "/v3/errors/forbidden",
        "title": "Forbidden Action",
        "status": 403
    }
    """
    pass


class NotFoundError(APIError):
    """Raised when an object is not found.

    Results in an HTTP 404 status code.
    Most often encountered when a specific item (e.g. user, question, tag, etc.) is requested,
    but cannot be found. This can occur when trying to get, edit, or delete an existing item.

    Example error messages:

    {
        "type": "/v3/errors/user/not-found",
        "title": "User not found",
        "status": 404,
        "detail": "User ID 40000 not found"
    }

    {
        "type": "/v3/errors/vote/QuestionNotFound",
        "title": "Question not found.",
        "status": 404,
        "detail": "Question with id 999999 not found"
    }
    """
    pass


class BadURLError(APIError):

    def __init__(self, url: str):
        self.message = f"Bad URL: {url}. Please fix the URL and try again."

    def __str__(self):
        return self.message


class RequiresEnterpriseError(APIError):
    """Raised when a Basic or Business user attempts to access an API feature this is only
        available in Enterprise.
    """
    pass


class SSLError(APIError):
    """Raised when an SSL error occurs during API calls

    """
    pass


class TooManyRequestsError(APIError):
    """Raised when the API is receiving too many requests
    """
    pass
