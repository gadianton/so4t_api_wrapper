# Standard Python libraries
import json
import logging
import os
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
                 logging_level="INFO"):
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
            api_url (str): The full API URL to be used for requests.
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
        self.headers = {'Authorization': f'Bearer {self.token}'}
        self.proxies = {'https': proxy} if proxy else {'https': None}
        self.ssl_verify = ssl_verify
        if self.ssl_verify:
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        if not url.startswith('https://'):
            url = 'https://' + url

        if "stackoverflowteams.com" in url: # Stack Overflow Business or Basic
            self.base_url = url
            self.team_slug = url.split("https://stackoverflowteams.com/c/")[1]
            self.api_url = f"https://api.stackoverflowteams.com/v3/teams/{self.team_slug}"
            self.soe = False # Product is not Stack Overflow Enterprise
        else: # Stack Overflow Enterprise
            self.base_url = url # Used to craft a URL in get_impersonation_token
            self.api_url = self.base_url + "/api/v3"
            self.impersonation_token = None # Impersonation only available in Enterprise
            self.soe = True # Product is Stack Overflow Enterprise

        # Test the API connection
        self.test_api_connection()

    
    def test_api_connection(self):

        test_endpoint = "/users/me"

        logging.info("Testing API v3 connection...")
        try:
            response = self.get_items(test_endpoint)
        except requests.exceptions.SSLError: # Error only happens for Enterprise, not Business
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
            

    ########################
    ### QUESTION METHODS ###
    ########################

    def get_questions(self, 
                      page: int = None, pagesize: int = None,
                      sort: str = None, order: str = None, 
                      is_answered: bool = None, has_accepted_answer: bool = None,
                      question_id: list=None, tag_id: list = None, author_id: int = None,
                      start_date: str = None, end_date: str = None,
                      one_page_limit: bool=False) -> list:
        """Returns a list of questions on the site.

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
            "tagId": tag_id if tag_id is None or isinstance(tag_id, list) else None,
            "authorId": author_id if author_id is None or isinstance(author_id, int) else None,
            "from": start_date if start_date is None or isinstance(start_date, str) else None,
            "to": end_date if end_date is None or isinstance(end_date, str) else None
        }
        logging.debug(f"Getting questions with params: {params}")
        
        questions = self.get_items(endpoint, params=params, one_page_limit=one_page_limit)
        return questions


    def get_question_by_id(self, question_id: int) -> dict:
        """Retrieve a question by its ID.

        Args:
            question_id (int): The unique identifier of the question to retrieve.

        Returns:
            dict: A dictionary containing the question details as returned by the API.
        """
        endpoint = f"/questions/{question_id}"
        question = self.get_items(endpoint)
        return question


    def get_all_questions_and_answers(self) -> list:
        """Combines API calls for questions and answers to create a list of questions with a list
        of answers nested within each question object.

        Returns:
            list: A list of dictionaries representing questions, where each question dictionary 
                includes a list of answers.
        """
        
        questions = self.get_questions()
        
        for question in questions:
            question['answers'] = self.get_question_answers(question['id'])

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
    

    def get_question_by_id(self, question_id: int) -> dict:
        """Retrieve a question by its ID.

        Args:
            question_id (int): The unique identifier of the question to retrieve.

        Returns:
            dict: A dictionary containing the question details as returned by the API.
        """
        endpoint = f"/questions/{question_id}"
        
        response = self.get_items(endpoint)
        return response
    

    def add_question(self, title: str, body: str, tags: list, impersonation: bool=False) -> dict:
        """Create a new question in the system.

        Args:
            title (str): The title of the question.
            body (str): The body of the question.
            tags (list): A list of strings representing tags for the question. Tags that do not already exist will be automatically created.
            impersonation (bool, optional): Flag indicating whether the question should be created using user impersonation. Defaults to False.

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


    def edit_question(self, question_id: int, title: str=None, body:str=None, 
                            tags: list=None) -> dict:
        """Edit all or part of a question by providing new title, body, and/or tags, leaving
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
            'title': title if title != None else original_question['title'],
            'body': body if body != None else original_question['body'],
            'tags': tags if tags != None else [tag["name"] for tag in original_question['tags']]
        }
        
        edited_question = self.edit_item(endpoint, params)
        return edited_question


    def get_question_comments(self, question_id: int) -> list:
        """Retrieve comments for a specific question identified by its ID.

        Args:
            question_id (int): The unique identifier of the question for which comments are to be retrieved.

        Returns:
            list: A list of dictionaries representing comments associated with the specified question.
        """
        endpoint = f"/questions/{question_id}/comments"
        
        comments = self.get_items(endpoint)
        return comments


    def delete_question(self, question_id: int):
    
        endpoint = f"/questions/{question_id}"
        self.delete_item(endpoint)
        # Aside from an HTTP 204 response, there is nothing to return


    ######################
    ### ANSWER METHODS ###
    ######################

    def get_answers(self, question_id: int, page: int=None, pagesize: int=None,
                    sort: str=None, order: str=None) -> list:

        endpoint = f"/questions/{question_id}/answers"
        params = {
            'page': page if isinstance(page, int) else 1,
            'pageSize': pagesize if pagesize in [15, 30, 50, 100] else 100,
            'sort': sort if isinstance(sort, str) else 'creation',
            "order": order if order in ['asc', 'desc'] else 'desc',
        }
        answers = self.get_items(endpoint, params)
        return answers


    def get_answer_by_id(self, question_id: int, answer_id: int):

        endpoint = f"/questions/{question_id}/answers/{answer_id}"
        answer = self.get_items(endpoint)
        return answer


    def add_answer(self, question_id: int, body: str, impersonation: bool=False):
   
        endpoint = f"/questions/{question_id}/answers"
        params = {
            "body": body,
        }

        new_answer = self.add_item(endpoint, params, impersonation=impersonation)
        return new_answer


    def get_answer_comments(self, question_id: int, answer_id: int) -> list:

        endpoint = f"/questions/{question_id}/answers/{answer_id}/comments"
        comments = self.get_items(endpoint)
        return comments


    def get_all_answers(self) -> list:

        questions = self.get_all_questions()

        all_answers = []
        for question in questions:
            answers = self.get_answers(question['id'])
            for answer in answers:
                answer['questionTags'] = question['tags']

            all_answers.append(answers)

        return answers


    def delete_answer(self, question_id: int, answer_id: int):

        endpoint = f"/questions/{question_id}/answers/{answer_id}"
        self.delete_item(endpoint)


    #######################
    ### ARTICLE METHODS ###
    #######################

    def get_articles(self, page: int=None, pagesize: int=None,
                    sort: str=None, order: str=None,
                    tag_ids: list=None, author_id: int=None,
                    start_date: str=None, end_date: str=None,
                    one_page_limit: bool=False) -> list:
        """Retrieve a list of articles based on the specified criteria.

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
            "authorId": author_id if author_id is None or isinstance(author_id, int) else None,
            "from": start_date if start_date is None or isinstance(start_date, str) else None,
            "to": end_date if end_date is None or isinstance(end_date, str) else None
        }

        articles = self.get_items(endpoint, params, one_page_limit=one_page_limit)
        return articles


    def get_article_by_id(self, article_id: int) -> dict:

        endpoint = f"/articles/{article_id}"
        article = self.get_items(endpoint)
        return article


    def add_article(self, title: str, body: str, article_type: str, tags: list, 
                    editable_by: str='ownerOnly', editor_user_ids: list=[], 
                    editor_user_group_ids: list=[], impersonation=False) -> dict:
        """Create a new article in the system.

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
    

    def edit_article(self, article_id: int, title: str=None, body: str=None, 
                     article_type: str=None, tags: list=None, editable_by: str=None, 
                     editor_user_ids: list=None, editor_user_group_ids: list=None, 
                     impersonation=False) -> dict:
        
        endpoint = f"/articles/{article_id}"

        if None in [title, body, article_type, tags, editable_by, editor_user_ids, 
                    editor_user_group_ids]:
            original_article = self.get_article_by_id(article_id)
        
        params = {
            'title': title if title != None else original_article['title'],
            'body': body if body != None else original_article['body'],
            'type': article_type if article_type != None else original_article['type'],
            'tags': tags if tags != None else [tag["name"] for tag in original_article['tags']],
            "permissions": {
                "editableBy": editable_by if editable_by != None else 
                    original_article['permissions']['editableBy'],
                "editorUserIds": editor_user_ids if editor_user_ids != None else 
                    [user['id'] for user in original_article['permissions']['editorUsers']],
                "editorUserGroupIds": editor_user_group_ids if editor_user_group_ids != None else
                    [group['id'] for group in original_article['permissions']['editorUserGroups']]
            }
        }

        edited_article = self.edit_item(endpoint, params, impersonation=impersonation)
        return edited_article


    def delete_article(self, article_id):

        endpoint = f"/articles/{article_id}"
        self.delete_item(endpoint)


    ###################
    ### TAG METHODS ###
    ###################

    def get_tags(self, page: int=None, pagesize: int=None,
                    sort: str=None, order: str=None,
                    partial_name: str=None, has_smes: bool= None,
                    one_page_limit: bool=False) -> list:

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

        endpoint = f"/tags/{tag_id}"
        tag = self.get_items(endpoint)
        return tag
    

    def get_tag_by_name(self, tag_name: str) -> int:
        
        tags = self.get_tags(partial_name=tag_name.lower())
        
        for tag in tags:
            if tag['name'] == tag_name:
                return tag
        
        raise NotFoundError("No tags match the name '{tag_name}'")
    

    def get_tag_smes(self, tag_id):

        endpoint = f"/tags/{tag_id}/subject-matter-experts"
        smes = self.get_items(endpoint)
        return smes
    

    def edit_tag_smes(self, tag_id: int, user_ids: list=[], group_ids: list=[]) -> dict:
        """ Overwrites all existing tag SMEs with the provided parameters
        
        """
        endpoint = f"/tags/{tag_id}/subject-matter-experts"
        params = {
            "userIds": user_ids,
            "userGroupIds": group_ids
        }
        edited_smes = self.edit_item(endpoint, params)
        return edited_smes


    def add_sme_users(self, tag_id: int, user_ids: list) -> dict:

        endpoint = f"/tags/{tag_id}/subject-matter-experts/users"
        params = user_ids
        updated_smes = self.add_item(endpoint, params)
        return updated_smes


    def add_sme_groups(self, tag_id: int, group_ids: list) -> dict:

        endpoint = f"/tags/{tag_id}/subject-matter-experts/user-groups"
        params = group_ids
        updated_smes = self.add_item(endpoint, params)
        return updated_smes


    def remove_sme_user(self, tag_id: int, user_id: int):

        endpoint = f"/tags/{tag_id}/subject-matter-experts/users/{user_id}"
        self.delete_item(endpoint)


    def remove_sme_group(self, tag_id: int, group_id: int):

        endpoint = f"/tags/{tag_id}/subject-matter-experts/user-groups/{group_id}"
        self.delete_item(endpoint)


    def get_all_tags_and_smes(self) -> list:

        tags = self.get_tags()

        for tag in tags:
            if tag['subjectMatterExpertCount'] > 0:
                tag['smes'] = self.get_tag_smes(tag['id'])
            else:
                tag['smes'] = {'users': [], 'userGroups': []}

        return tags


    ####################
    ### USER METHODS ###
    ####################

    def get_users(self,
                  page: int = None, pagesize: int = None,
                  sort: str = None, order: str = None, 
                  one_page_limit: bool=False) -> list:
        
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

        endpoint = f"/users/{user_id}"
        user = self.get_items(endpoint)
        return user
    

    def get_user_by_email(self, email: str) -> dict:
        '''
        Email is not case-sensitive. 
        '''

        endpoint = f"/users/by-email/{email}"

        user = self.get_items(endpoint)
        return user
    

    def get_account_id_by_user_id(self, user_id: int) -> int:

        user = self.get_user_by_id(user_id)
        account_id = user['accountId']
        return account_id


    def get_account_id_by_email(self, email: str) -> int:

        user = self.get_user_by_email(email)
        account_id = user['accountId']
        return account_id


    def get_myself(self, impersonation: bool=False) -> dict:

        endpoint = "/users/me"
        myself = self.get_items(endpoint, impersonation=impersonation)
        return myself


    ##########################
    ### USER GROUP METHODS ###
    ##########################

    def get_user_groups(self, page: int = None, pagesize: int = None,
                        sort: str = None, order: str = None) -> list:
        # sort can be 'name' or 'size'

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

        endpoint = f"/user-groups/{group_id}"
        group = self.get_items(endpoint)
        return group


    def add_user_group(self, name: str, user_ids: list, description: str=None) -> dict:

        endpoint = "/user-groups"
        params = {
            "name": name,
            "userIds": user_ids,
            "description": description
        }

        new_group = self.add_item(endpoint, params)
        return new_group
    

    def edit_user_group(self, group_id: int, name: str=None, 
                        user_ids: list=None, description: str=None) -> dict:

        endpoint = f"/user-groups/{group_id}"
        if None in [name, user_ids, description]:
            original_group = self.get_user_group_by_id(group_id)

        params = {
            'name': name if name != None else original_group['name'],
            'userIds': user_ids if user_ids != None else original_group['userIds'],
            'description': description if description != None else original_group['description']
        }
        edited_group = self.edit_item(endpoint, params)
        return edited_group


    ######################
    ### SEARCH METHODS ###
    ######################

    def get_search_results(self, query, sort='relevance'):
        '''
        As of June 2024, the endpoint always returns exactly 100 results
        `sort` can be one of four string values: 'relevance', 'newest', 'active', or 'score'
        '''
        endpoint = "/search"
        params = {
            'query': query,
            'page': 1,
            'pagesize': 100,
            'sort': sort
        }

        search_results = self.get_items(endpoint, params)
        return search_results


    #########################
    ### COMMUNITY METHODS ###
    #########################

    # As of June 2024, there are no API endpoints for creating/deleting communities

    def get_communities(self):
            
        endpoint = "/communities"
        params = {
            'page': 1,
            'pagesize': 100,
        }

        communities = self.get_items(endpoint, params)
        return communities
    

    def get_community_by_id(self, community_id: int):

        endpoint = f"/communities/{community_id}"

        community = self.get_items(endpoint)
        return community


    def join_community(self, community_id: int, impersonation: bool=False):

        method = POST
        endpoint = f"/communities/{community_id}/join"

        updated_community = self.send_api_call(method, endpoint, impersonation=impersonation)
        return updated_community
    

    def leave_community(self, community_id: int, impersonation: bool=False):

        method = POST
        endpoint = f"/communities/{community_id}/leave"

        updated_community = self.send_api_call(method, endpoint, impersonation=impersonation)
        return updated_community


    ##########################
    ### COLLECTION METHODS ###
    ##########################

    def get_collections(self) -> list:
                
        endpoint = "/collections"
        params = {
            'page': 1,
            'pagesize': 100,
        }

        collections = self.get_items(endpoint, params)
        return collections


    #############################
    ### IMPERSONATION METHODS ###
    #############################

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
        params = {
            'access_tokens': self.token,
            'exchange_type': 'impersonate',
            'account_id': account_id
        }

        response = requests.post(endpoint_url, params=params, headers=headers)
        self.raise_status_code_exceptions(response)

        json_data = response.json()
        impersonation_token = json_data['items'][0]['access_token']

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
            dict: A dictionary containing the details of the impersonated question, such as question ID, title, body, tags, and user ID.
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

        self.impersonation_token = self.get_impersonation_token(account_id)
        user = self.get_myself(impersonation=True)
        return user


    def add_community_member_by_user_id(self, user_id: int, community_id: int):
        '''
        Requires user impersonation, which is only available in the Enterprise tier
        '''
        account_id = self.get_account_id_by_user_id(user_id)
        updated_community = self.add_community_member_by_account_id(account_id, community_id)
        return updated_community


    def add_community_member_by_email(self, email: str, community_id: int):
        '''
        Requires user impersonation, which is only available in the Enterprise tier
        '''
        account_id = self.get_account_id_by_email(email)
        updated_community = self.add_community_member_by_account_id(account_id, community_id)
        return updated_community


    def add_community_member_by_account_id(self, account_id: int, community_id: int):
        '''
        Requires user impersonation, which is only available in the Enterprise tier
        '''
        self.impersonation_token = self.get_impersonation_token(account_id)
        updated_community = self.join_community(community_id, impersonation=True)
        return updated_community
    

    ########################
    ### HELPER FUNCTIONS ###
    ########################

    def get_items(self, endpoint: str, params: dict={}, impersonation: bool=False,
                  one_page_limit: bool=False):

        method = GET
        items = []
        while True:
            response = self.get_api_response(method, endpoint, params=params, 
                                             impersonation=impersonation)
            json_data = response.json()

            try:
                items += json_data['items']
            except KeyError: # API endpoint only returns a single result
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
    

    def add_item(self, endpoint: str, params: dict, impersonation: bool=False):

        method = POST

        response = self.get_api_response(method, endpoint, params, impersonation=impersonation)
        new_item = response.json()

        return new_item
    

    def edit_item(self, endpoint: str, params: dict, impersonation: bool=False):

        method = PUT

        response = self.get_api_response(method, endpoint, params, impersonation=impersonation)
        updated_item = response.json()

        return updated_item

    
    def delete_item(self, endpoint: str, impersonation: bool=False):

        method = DELETE
        response = self.get_api_response(method, endpoint, impersonation=impersonation)

        if response.status_code == 204:
            logging.info(f"Successfully deleted item from {endpoint}")
        else:
            logging.error(f"Failed to delete item from {endpoint}")


    def get_api_response(self, method: str, endpoint: str, params: dict={}, 
                         impersonation: bool=False):

        endpoint_url = self.api_url + endpoint
        if impersonation:
            headers = {'Authorization': f'Bearer {self.impersonation_token}'}
        else:
            headers = self.headers

        request_type = getattr(requests, method, None) # get the method from the requests library
        if method == GET:
            response = request_type(endpoint_url, headers=headers, params=params, 
                                    verify=self.ssl_verify, proxies=self.proxies)
        else:
            response = request_type(endpoint_url, headers=headers, json=params, 
                                    verify=self.ssl_verify, proxies=self.proxies)
            
        self.raise_status_code_exceptions(response) # check for errors and raise exceptions if necessary
        
        return response

                        
        #     try:
        #         json_data = response.json()
        #     except json.decoder.JSONDecodeError: # some API calls do not return JSON data
        #         logging.info(f"API request successfully sent to {endpoint_url}")
        #         logging.debug(f"Response text: {response.text}")
        #         return

        #     if type(params) == dict and params.get('page'): # check request for pagination
        #         logging.info(f"Received page {params['page']} from {endpoint_url}")
        #         data += json_data['items']
        #         if params['page'] == json_data['totalPages']:
        #             break
        #         params['page'] += 1
        #     else:
        #         logging.info(f"API request successfully sent to {endpoint_url}")
        #         data = json_data
        #         break


    def raise_status_code_exceptions(self, response: requests.Response) -> None:
        """Parses the response codes and raises appropriate errors if necessary."""

        if response.status_code not in [200, 201, 204]:
            try:
                error_message = response.json()
            except json.decoder.JSONDecodeError: 
                error_message = response.text
        
            if response.status_code == 400:
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
            
            # elif response.status_code == 401:
            #     raise UnauthorizedError(error_message)

            elif response.status_code == 403:
                raise ForbiddenError(error_message)
            
            elif response.status_code == 404:
                if type(error_message) == dict:
                    # If a dictionary is returned, the 404 means the requested object is not found
                    raise NotFoundError(error_message)
                else:  # Otherwise, it's likely a bad URL
                    raise BadURLError(response.url)
                
            # elif response.status_code == 409:
            #     raise ConflictError(error_message)

            elif response.status_code == 500 and not self.soe:
                # 500 errors can happen when the URL for a Business instance is incorrect
                raise BadURLError(self.base_url)
            
            # elif response.status_code >= 500:
            #     raise ServerError(error_message)
            # elif response.status_code >= 400:
            #     raise ClientError(error_message)

            else:
                raise Exception(f"Encountered an unexpected response from server: {error_message}")
        

    def export_to_json(self, file_name: str, data: list|dict, directory: str=None):

        json_extension = '.json'
        if not file_name.endswith(json_extension):
            file_name = file_name + json_extension

        if directory and not os.path.exists(directory):
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
