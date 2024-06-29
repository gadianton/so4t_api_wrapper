# Stack Overflow for Teams API Wrapper
A Python wrapper for the Stack Overflow for Teams API, replicating the functionality of the Stack Overflow for Teams API in a more user-friendly way.

Full documentation for the API can be found at one of the following locations:
* Basic/Business API: https://api.stackoverflowteams.com/v3
* Enterprise API: https://YOUR.INSTANCE.URL/api/v3

## Table of Contents
* [Setup](https://github.com/jklick-so/so4t_api_wrapper?tab=readme-ov-file#setup)
* [Basic Usage](https://github.com/jklick-so/so4t_api_wrapper?tab=readme-ov-file#basic-usage)
* [Wrapper Methods](https://github.com/jklick-so/so4t_api_wrapper?tab=readme-ov-file#wrapper-methods)
* [Support](https://github.com/jklick-so/so4t_api_wrapper?tab=readme-ov-file#support)


# Setup

**Install**

Install the package using pip:

```python
python3 -m pip install so4t_api
```
> If you're running Windows, you'll probably need to use `py` instead of `python3`

**API Authentication**

To authenticate with the Stack Overflow API, you will need to generate a valid access token.

* For Basic or Business, instructions for creating a personal access token (PAT) can be found in [this KB article](https://stackoverflow.help/en/articles/4385859-stack-overflow-for-teams-api).
* For Enterprise, follow the instructions in the KB article titled [Secure API Token Generation Using OAuth with PKCE](https://support.stackenterprise.co/support/solutions/articles/22000286119-secure-api-token-generation-using-oauth-with-pkce)

> NOTE: For Enterprise, if you'll be performing any API tasks that require posting or editing content (i.e. anything beyond just getting/reading content), you'll need to make sure to include the `write_access` scope when generating your token; otherwise, you will not be able to make the necessary updates to content via the API.

> ANOTHER NOTE: For Enterprise, if you'll be using any of the impersonation methods, this will additionally require an API key, which will be submitted as an argument when instantiating StackClient. It will also require enabling impersonation, which involves sending a request to support@stackoverflow.com.


# Basic Usage
A basic example of how to use the wrapper in an application:

```python
import os
from so4t_api import StackClient

# instantiate the StackClient
stack = StackClient(url=os.environ["SO_URL"], token=os.environ["SO_TOKEN"]) 

# get all questions
questions = stack.get_questions() 

# Calculate total page views
total_views = 0
for question in questions:
    total_views += question["viewCount"]
print(f"Total page views across {len(questions)} questions: {total_views}")
```

# Wrapper Methods

At this time, most/all the documentation for wrapper methods is found alongside the methods (i.e. in the code). Here is a current list of all the methods available in the wrapper:

## Questions
- `get_questions` - Returns a list of questions on the site based on specified criteria.
- `get_question_by_id` - Retrieves a question by its ID.
- `get_all_questions_and_answers` - Combines API calls for questions and answers to create a list of questions with answers nested within each question object.
- `get_all_questions_answers_and_comments` - Combines API calls to retrieve questions, answers, and comments for each question.
- `add_question` - Creates a new question in the system.
- `edit_question` - Edits a question by providing new title, body, and/or tags.
- `get_question_comments` - Retrieves comments for a specific question identified by its ID.
- `delete_question` - Deletes a question from the Stack Overflow for Teams instance.

## Answers
- `get_answers` - Retrieves a list of answers for a specific question identified by its ID.
- `get_answer_by_id` - Retrieves a specific answer by its ID for a given question.
- `add_answer` - Adds a new answer to a specific question.
- `get_answer_comments` - Retrieves comments for a specific answer identified by its question ID and answer ID.
- `get_all_answers` - Retrieves all answers for all questions.
- `delete_answer` - Deletes a specific answer from a question in the Stack Overflow for Teams instance.

## Articles
- `get_articles`
  - Retrieves a list of articles based on the specified criteria.
- `get_article_by_id` - Retrieves a specific article by its ID.
- `add_article` - Creates a new article in the system.
- `edit_article` - Edits an article by providing new title, body, and/or tags.
- `delete_article` - Deletes a specific article from the Stack Overflow for Teams instance.

## Tags
- `get_tags` - Retrieves a list of tags based on the specified criteria.
- `get_tag_by_id` - Retrieves a specific tag by its ID.
- `get_tag_by_name` - Retrieves a specific tag by its name.
- `get_tag_smes` - Retrieves the subject matter experts (SMEs) associated with a specific tag identified by its ID.
- `edit_tag_smes` - Edits the SMEs associated with a specific tag identified by its ID.
- `add_sme_users` - Adds SME users to a specific tag identified by its ID.
- `add_sme_groups` - Adds SME user groups to a specific tag identified by its ID.
- `remove_sme_user` - Removes a specific user from the SMEs associated with a specific tag.
- `remove_sme_group` - Removes a specific user group from the SMEs associated with a specific tag.
- `get_all_tags_and_smes` - Retrieves all tags and their associated SMEs.

## Users
- `get_users` - Retrieves a list of users from the Stack Overflow for Teams instance.
- `get_user_by_id` - Retrieves a specific user by their ID.
- `get_user_by_email` - Retrieves a specific user by their email address.
- `get_account_id_by_user_id` - Retrieves the account ID of a user by their user ID.
- `get_account_id_by_email` - Retrieves the account ID of a user by their email address.
- `get_myself` - Retrieves the details of the authenticated user.

## User Groups
- `get_user_groups` - Retrieves a list of user groups from the Stack Overflow for Teams instance.
- `get_user_group_by_id` - Retrieves a specific user group by its ID.
- `add_user_group` - Adds a new user group to the Stack Overflow for Teams instance.
- `edit_user_group` - Edits a user group by providing new name, user IDs, and/or description.
- `add_users_to_group` - Adds users to a specific user group identified by its group ID.
- `delete_user_from_group` - Deletes a specific user from a user group in the Stack Overflow for Teams instance.

## Search
- `get_search_results` - Retrieves a list of search results based on the provided query.

## Communities
- `get_communities` - Retrieves a list of communities from the Stack Overflow for Teams instance.
- `get_community_by_id` - Retrieves a specific community by its ID.
- `join_community` - Joins a community in the Stack Overflow for Teams instance.
- `leave_community` - Leaves a community in the Stack Overflow for Teams instance.
- `add_users_to_community` - Adds users to a community in the Stack Overflow for Teams instance.
- `remove_users_from_community` - Removes users from a community in the Stack Overflow for Teams instance.

## Collections
- `get_collections` - Retrieves a list of collections based on the specified criteria.
- `get_collection_by_id` - Retrieves a specific collection by its ID.
- `add_collection` - Adds a new collection to the Stack Overflow for Teams instance.
- `edit_collection` - Edits a collection by providing new title, description, content IDs, and/or editor user IDs.
- `delete_collection` - Deletes a specific collection from the Stack Overflow for Teams instance.

## Impersonation
- `get_impersonation_token` - Retrieves an impersonation token for a specified account ID.
- `impersonate_question_by_user_id` - Creates a question on behalf of another user, identified by their user ID.
- `impersonate_question_by_user_email` - Creates a question on behalf of another user, identified by their email address.
- `impersonate_question_by_account_id` - Creates a question on behalf of another user, identified by their account ID.
- `get_impersonated_user` - Retrieves the details of a user by impersonating another user identified by their account ID.

> NOTE: Impersonation needs to be turned on for your Stack Overflow for Teams instance in order to use these methods ([documentation link](https://support.stackenterprise.co/support/solutions/articles/22000245133-service-keys-identity-delegation-and-impersonation#impersonation)). You can enable this by reaching out to support@stackoverlow.com. Also, you will need to provide a `key` parameter when instantiating the StackClient class. 


# Support
Disclaimer: the creator of this project works at Stack Overflow, but it is a labor of love that comes with no formal support from Stack Overflow. 

If you run into issues using the script, please [open an issue](https://github.com/jklick-so/so4t_api_wrapper/issues). You are also welcome to edit the script to suit your needs, steal the code, or do whatever you want with it.
