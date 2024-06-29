"""
Much of the testing requires admin permissions, particular when checking the deletion status of
content or looking up users by email address. Some testing requires impersonation to be enabled.

For Stack Overflow Enterprise, turn off duplicate checking at this URL (requires admin); otherwise,
the testing will fail since it creates the same content over and over.
<SITE_URL>/developer/site-settings/edit?name=Questions.Testing.EnableDuplicateCheckForQuestions

There is no endpoint for deleting user groups, so user groups created during testing will need to
be cleaned up (deleted) manually.

There is not endpoint for creating communities, so at least one community must be created manually
prior to testing
"""

import os
import pytest
import random
import shutil
from so4t_api import StackClient, BadURLError, UnauthorizedError, InvalidRequestError
import string

try:
    GOOD_URL = os.environ['GOOD_URL']
    GOOD_TOKEN = os.environ['GOOD_TOKEN']
    GOOD_KEY = os.environ['GOOD_KEY']
except KeyError:
    raise SystemExit("Please set the environment variables GOOD_URL, GOOD_TOKEN, and GOOD_KEY")

BAD_TOKEN = "CheesePuffs"
BAD_KEY = "CheesePuffs"

TEST_TITLE = "How to use Python's requests library?"
TEST_BODY = "I am trying to make API calls using Python's requests library, but I am facing " \
            "some issues. Can someone provide a simple example?"
TEST_TYPE = "knowledgeArticle"
TEST_TAGS = ["python", "requests", "api", "cheesepuffs"]
TEST_TAG_NAME = "cheesepuffs"
TEST_COLLECTION_TITLE = "Cheese Puffs"
TEST_DESCRIPTION = "For all fans of cheese puffs"
EDITED_TITLE = "This has been changed to something new"
BAD_ID = 99999999


@pytest.fixture(scope="session")
def client():
    return create_client()


def create_client(url: str = GOOD_URL, token: str = GOOD_TOKEN, key: str = GOOD_KEY) -> StackClient:
    return StackClient(url, token, key)


@pytest.fixture(scope="class")
def question(client):
    question = client.add_question(TEST_TITLE, TEST_BODY, TEST_TAGS)
    yield question


@pytest.fixture(scope="class")
def question_and_answer(client, question):
    answer = client.add_answer(question['id'], TEST_BODY)
    yield question, answer


@pytest.fixture(scope="class")
def user(client):

    users = client.get_users(one_page_limit=True)
    return users[0]


@pytest.fixture(scope="class")
def myself(client):
    myself = client.get_myself()
    yield myself


@pytest.fixture(scope="class")
def group(client, user):

    user_ids = [user['id']]
    group_name = random_string(15)
    group = client.add_user_group(group_name, user_ids, TEST_DESCRIPTION)
    yield group


@pytest.fixture(scope="class")
def article(client):
    article = client.add_article(TEST_TITLE, TEST_BODY, TEST_TYPE, TEST_TAGS)
    yield article


@pytest.fixture(scope="class")
def tag(client):
    tag = client.get_tag_by_name(TEST_TAG_NAME)
    yield tag


@pytest.fixture(scope="class")
def community(client):
    communities = client.get_communities()
    validate_communities(communities)
    community = communities[0]
    yield community


@pytest.fixture(scope="class")
def collection(client):
    collection = client.add_collection(TEST_COLLECTION_TITLE, TEST_DESCRIPTION)
    yield collection


@pytest.fixture(scope="class")
def search_question(client):
    questions = client.get_questions(one_page_limit=True)
    question = questions[0]
    yield question


class TestClientCreation(object):
    def test_create_client_happy_path(self):

        client = StackClient(GOOD_URL, GOOD_TOKEN)
        assert client.base_url == GOOD_URL
        assert client.token == GOOD_TOKEN
        assert client.s.headers == {'Authorization': f'Bearer {GOOD_TOKEN}'}
        assert client.proxies == {'https': None}
        assert client.ssl_verify is True

    def test_create_client_with_bad_business_team_slug(self):

        url = "https://stackoverflowteams.com/c/cheese-puffs"
        token = BAD_TOKEN
        with pytest.raises(BadURLError):
            # client = StackClient(url, token)
            StackClient(url, token)

    def test_create_client_with_bad_enterprise_subdomain(self):

        url = "https://cheesepuffs.stackenterprise.co"
        token = BAD_TOKEN
        with pytest.raises(BadURLError):
            # client = StackClient(url, token)
            StackClient(url, token)

    def test_create_client_with_wrong_domain(self):

        url = "google.com"
        token = BAD_TOKEN
        with pytest.raises(BadURLError):
            # client = StackClient(url, token)
            StackClient(url, token)

    def test_create_client_with_nonexistent_domain(self):

        url = "thisisnotarealdomainabcxyz.com"
        token = BAD_TOKEN
        with pytest.raises(BadURLError):
            # client = StackClient(url, token)
            StackClient(url, token)

    def test_create_client_with_good_url_no_https(self):

        url = "soedemo.stackenterprise.co"
        token = BAD_TOKEN
        with pytest.raises(UnauthorizedError):
            # stack = StackClient(url, token)
            StackClient(url, token)


class TestQuestionMethods(object):
    def test_add_question_happy_path(self, client):

        new_question = client.add_question(TEST_TITLE, TEST_BODY, TEST_TAGS)
        assert type(new_question) is dict
        assert TEST_TITLE == new_question['title']
        assert TEST_BODY in new_question['body']
        assert new_question['tags'][0]['name'] in TEST_TAGS

    def test_get_question_by_id_happy_path(self, client, question):

        # test_question = generate_test_question(stack)
        question = client.get_question_by_id(question['id'])
        assert type(question) is dict
        assert question['title'] == TEST_TITLE

    def test_get_question_with_bad_id(self, client):

        with pytest.raises(Exception) as e:
            client.get_question_by_id(BAD_ID)

        assert "404" in str(e.value)

    def test_edit_question_happy_path(self, client, question):

        # test_question = generate_test_question(stack)
        edited_question = client.edit_question(question['id'], title=EDITED_TITLE)
        assert type(edited_question) is dict
        assert edited_question['title'] == EDITED_TITLE
        assert edited_question['body'] == question['body']
        assert edited_question['tags'] == question['tags']

    def test_get_questions_happy_path(self, client):

        questions = client.get_questions()
        assert type(questions) is list
        assert len(questions) > 0

    def test_get_questions_sorting_by_creation_descending(self, client):

        questions = client.get_questions(sort="creation", order="desc")
        assert questions[0]['creationDate'] > questions[1]['creationDate']
        assert questions[1]['creationDate'] > questions[2]['creationDate']

    def test_delete_question_happy_path(self, client, question):

        client.delete_question(question['id'])
        question = client.get_question_by_id(question['id'])

        assert question['isDeleted'] is True


class TestAnswerMethods(object):
    def test_add_answer_happy_path(self, client, question):

        test_answer = client.add_answer(question['id'], TEST_BODY)
        assert type(test_answer) is dict
        assert TEST_BODY in test_answer['body']

    def test_get_answers_happy_path(self, client, question_and_answer):

        question, answer = question_and_answer
        answers = client.get_answers(question['id'])
        assert type(answers) is list
        assert answer['body'] == answers[0]['body']

    def test_get_answers_with_bad_question_id(self, client):

        with pytest.raises(Exception) as e:
            client.get_answers(BAD_ID)

        assert "404" in str(e.value)

    def test_get_answer_by_id_happy_path(self, client, question_and_answer):

        question, answer = question_and_answer
        answer = client.get_answer_by_id(question['id'], answer['id'])
        assert type(answer) is dict
        assert TEST_BODY in answer['body']

    def test_get_answer_with_bad_answer_id(self, client, question_and_answer):

        question, answer = question_and_answer
        with pytest.raises(Exception) as e:
            client.get_answer_by_id(question['id'], BAD_ID)

        assert "404" in str(e.value)

    def test_get_answer_with_bad_question_id(self, client, question_and_answer):

        question, answer = question_and_answer
        with pytest.raises(Exception) as e:
            client.get_answer_by_id(BAD_ID, answer['id'])

        assert "404" in str(e.value)

    def test_delete_answer_happy_path(self, client, question_and_answer):

        question, answer = question_and_answer
        client.delete_answer(question['id'], answer['id'])
        answer = client.get_answer_by_id(question['id'], answer['id'])
        assert answer['isDeleted'] is True

    def test_get_all_questions_answers_and_comments_happy_path(self, client):

        questions = client.get_all_questions_answers_and_comments()
        assert type(questions) is list
        assert type(questions[0]['comments']) is list
        assert type(questions[0]['answers']) is list


class TestArticleMethods(object):

    def test_add_article_happy_path(self, client):

        new_article = client.add_article(TEST_TITLE, TEST_BODY, TEST_TYPE, TEST_TAGS)
        assert type(new_article) is dict
        assert TEST_TITLE == new_article['title']
        assert TEST_BODY in new_article['body']
        assert TEST_TYPE == new_article['type']
        assert new_article['tags'][0]['name'] in TEST_TAGS

    def test_get_article_by_id_happy_path(self, client, article):

        article = client.get_article_by_id(article['id'])
        assert type(article) is dict
        assert TEST_TITLE == article['title']

    def test_get_article_with_bad_id(self, client):

        with pytest.raises(Exception) as e:
            client.get_article_by_id(BAD_ID)
        assert "404" in str(e.value)

    def test_edit_article_happy_path(self, client, article):

        edited_article = client.edit_article(article['id'], title=EDITED_TITLE)
        assert type(edited_article) is dict
        assert edited_article['title'] == EDITED_TITLE
        assert edited_article['body'] == article['body']
        assert edited_article['tags'] == article['tags']

    def test_get_articles_happy_path(self, client):

        articles = client.get_articles()
        assert type(articles) is list
        assert len(articles) > 0

    def test_delete_question_happy_path(self, client, article):

        client.delete_article(article['id'])
        article = client.get_article_by_id(article['id'])
        assert article['isDeleted'] is True


class TestTagMethods(object):

    def test_get_tags_happy_path(self, client):

        tags = client.get_tags()
        assert type(tags) is list
        assert len(tags) > 0

    def test_get_tag_by_name_happy_path(self, client):

        tag = client.get_tag_by_name(TEST_TAG_NAME)
        assert tag['name'] == TEST_TAG_NAME

    def test_get_tag_by_id_happy_path(self, client, tag):

        tag = client.get_tag_by_id(tag['id'])
        assert type(tag) is dict
        assert tag['name'] == TEST_TAG_NAME

    def test_get_tag_smes_happy_path(self, client, tag):

        smes = client.get_tag_smes(tag['id'])
        assert type(smes) is dict
        assert type(smes['users']) is list
        assert type(smes['userGroups']) is list

    def test_edit_tag_smes_happy_path(self, client, tag, user, group):

        edited_smes = client.edit_tag_smes(tag['id'], [user['id']], [group['id']])
        assert type(edited_smes) is dict
        assert len(edited_smes['users']) == 1
        assert edited_smes['users'][0]['id'] == user['id']
        # assert len(edited_smes['userGroups']) == 1
        assert group['id'] in [group['id'] for group in edited_smes['userGroups']]

    def test_add_sme_users_happy_path(self, client, tag, user):

        self.reset_smes(client, tag)
        updated_smes = client.add_sme_users(tag['id'], [user['id']])
        assert type(updated_smes) is dict
        assert len(updated_smes['users']) == 1
        assert updated_smes['users'][0]['id'] == user['id']
        # assert len(updated_smes['userGroups']) == 0

    def test_add_sme_groups_happy_path(self, client, tag, group):

        self.reset_smes(client, tag)
        updated_smes = client.add_sme_groups(tag['id'], [group['id']])
        assert type(updated_smes) is dict
        assert len(updated_smes['users']) == 0
        # assert len(updated_smes['userGroups']) == 1
        assert group['id'] in [group['id'] for group in updated_smes['userGroups']]

    def test_remove_sme_user_happy_path(self, client, tag, user):

        tag_id = tag['id']
        user_id = user['id']
        smes = client.add_sme_users(tag_id, [user_id])
        client.remove_sme_user(tag_id, user_id)
        smes = client.get_tag_smes(tag_id)
        assert user_id not in [user['id'] for user in smes['users']]

    def test_remove_sme_group_happy_path(self, client, tag, group):

        tag_id = tag['id']
        group_id = group['id']
        smes = client.add_sme_groups(tag_id, [group_id])
        client.remove_sme_group(tag_id, group_id)
        smes = client.get_tag_smes(tag_id)
        assert group_id not in [group['id'] for group in smes['userGroups']]

    def test_get_all_tags_and_smes_happy_path(self, client):

        tags = client.get_all_tags_and_smes()
        assert type(tags) is list
        assert type(tags[0]) is dict
        assert type(tags[0]['smes']) is dict
        assert type(tags[0]['smes']['users']) is list
        assert type(tags[0]['smes']['userGroups']) is list

    def reset_smes(self, client, tag):
        """Removes all SMES from a tag to create a blank slate for testing"""
        # client.edit_tag_smes(tag['id'], [], [])
        client.edit_tag_smes(tag['id'], [], [])


class TestUserMethods(object):
    def test_get_users_happy_path(self, client):

        users = client.get_users()
        assert type(users) is list
        assert len(users) > 0

    def test_get_user_by_id_happy_path(self, client, user):

        user_id = user['id']
        user = client.get_user_by_id(user_id)
        self.assert_user_object(user)
        assert user['id'] == user_id

    def test_get_user_by_email_happy_path(self, client, user):

        user_email = user['email']
        user = client.get_user_by_email(user_email)
        self.assert_user_object(user)
        assert user['email'] == user_email

    def test_get_account_id_by_user_id_happy_path(self, client, user):

        account_id = client.get_account_id_by_user_id(user['id'])
        self.assert_account_id(account_id)

    def test_get_account_id_by_email_happy_path(self, client, user):

        account_id = client.get_account_id_by_email(user['email'])
        self.assert_account_id(account_id)

    def test_get_myself_happy_path(self, client):

        myself = client.get_myself()
        self.assert_user_object(myself)

    def assert_user_object(self, user_object):

        assert type(user_object) is dict
        assert type(user_object['accountId']) is int

    def assert_account_id(self, account_id):

        assert type(account_id) is int


class TestUserGroupMethods(object):

    def test_add_user_group_happy_path(self, client, user):

        group_name = random_string(15)
        new_group = client.add_user_group(group_name, [user['id']], TEST_DESCRIPTION)
        assert type(new_group) is dict
        assert new_group['name'] == group_name
        assert new_group['description'] == TEST_DESCRIPTION
        assert new_group['users'][0]['id'] == user['id']

    def test_get_user_groups_happy_path(self, client):

        groups = client.get_user_groups()
        assert type(groups) is list
        assert type(groups[0]) is dict
        assert type(groups[0]['users']) is list

    def test_get_user_group_by_id_happy_path(self, client, group):

        group = client.get_user_group_by_id(group['id'])
        assert type(group) is dict
        assert type(group['users']) is list
        assert type(group['description']) is str

    def test_edit_user_group_happy_path(self, client, group):

        new_name = random_string(7)
        updated_group = client.edit_user_group(group['id'], name=new_name)
        assert type(updated_group) is dict
        assert updated_group['name'] == new_name
        assert updated_group['users'] == group['users']
        assert updated_group['description'] == group['description']

    def test_add_users_to_group_happy_path(self, client, group, user):

        group = client.edit_user_group(group['id'], user_ids=[])  # remove users
        assert group['users'] == []
        updated_group = client.add_users_to_group(group['id'], [user['id']])
        assert type(updated_group) is dict
        assert type(updated_group['users']) is list
        assert len(updated_group['users']) == 1
        assert user['id'] in [user['id'] for user in updated_group['users']]

    def test_delete_user_from_group(self, client, group, user):

        client.delete_user_from_group(group['id'], user['id'])
        group = client.get_user_group_by_id(group['id'])
        assert group['users'] == []


class TestCommunityMethods(object):

    def test_get_communities_happy_path(self, client):

        communities = client.get_communities()
        assert type(communities) is list
        validate_communities(communities)
        self.assert_community_object(communities[0])

    def test_community_by_id_happy_path(self, client, community):

        community_id = community['id']
        community = client.get_community_by_id(community_id)
        self.assert_community_object(community)
        assert community['id'] == community_id

    def test_join_community_happy_path(self, client, community, myself):

        updated_community = client.join_community(community['id'])
        self.assert_community_object(updated_community)
        self.assert_user_in_community(myself['id'], updated_community)

    def test_leave_community_happy_path(self, client, community, myself):

        updated_community = client.leave_community(community['id'])
        self.assert_community_object(updated_community)
        self.assert_user_not_in_community(myself['id'], updated_community)

    def test_add_users_to_community_happy_path(self, client, community, user):

        updated_community = client.add_users_to_community(community['id'], [user['id']])
        self.assert_community_object(updated_community)
        self.assert_user_in_community(user['id'], updated_community)

    def test_remove_users_from_community_happy_path(self, client, community, user):

        updated_community = client.remove_users_from_community(community['id'], [user['id']])
        self.assert_community_object(updated_community)
        self.assert_user_not_in_community(user['id'], updated_community)

    def assert_community_object(self, community_object):
        assert type(community_object) is dict
        assert type(community_object['memberCount']) is int

    def assert_user_in_community(self, user_id, community):
        assert user_id in [member['id'] for member in community["members"]]

    def assert_user_not_in_community(self, user_id, community):
        assert user_id not in [member['id'] for member in community["members"]]


class TestCollectionMethods(object):

    def test_add_collection_happy_path(self, client, question, article):

        content_ids = [question['id'], article['id']]
        collection = client.add_collection(TEST_COLLECTION_TITLE, content_ids=content_ids)
        self.assert_collection_object(collection)
        self.assert_content_in_collection(question['id'], collection)
        self.assert_content_in_collection(article['id'], collection)

    def test_get_collection_by_id_happy_path(self, client, collection):

        collection_id = collection['id']
        collection = client.get_collection_by_id(collection_id)
        self.assert_collection_object(collection)
        assert collection['id'] == collection_id

    def test_edit_collection_happy_path(self, client, collection):

        new_title = "New Collection Name"
        updated_collection = client.edit_collection(collection['id'], title=new_title)
        self.assert_collection_object(updated_collection)
        assert updated_collection['title'] == new_title
        assert updated_collection['description'] == collection['description']
        assert updated_collection['content'] == collection['content']
        assert updated_collection['id'] == collection['id']

    def test_delete_collection_happy_path(self, client, collection):

        client.delete_collection(collection['id'])
        deleted_collection = client.get_collection_by_id(collection['id'])
        assert deleted_collection['isDeleted'] is True

    def assert_collection_object(self, collection):

        assert type(collection) is dict
        assert type(collection['content']) is list

    def assert_content_in_collection(self, content_id, collection):

        assert content_id in [content['id'] for content in collection['content']]


class TestSearchMethods(object):

    def test_get_search_results_happy_path(self, client, search_question):

        results = client.get_search_results(search_question['title'])

        search_match = None
        for result in results:
            if result['title'] == search_question['title']:
                search_match = result
                break

        assert type(search_match) is dict
        assert search_match['tags'] == search_question['tags']
        assert search_question['creationDate'] in search_match['creationDate']


class TestImpersonationMethods(object):
    def test_get_impersonation_token_happy_path(self, client, user):

        impersonation_token = client.get_impersonation_token(user['accountId'])
        assert type(impersonation_token) is str
        assert impersonation_token.endswith("))")  # token strings always end in double parentheses

    def test_get_impersonation_token_with_no_key(self, user):

        client = create_client(key=None)
        # account_id = self.get_account_id(client=stack)
        with pytest.raises(InvalidRequestError):
            # impersonation_token = client.get_impersonation_token(user['accountId'])
            client.get_impersonation_token(user['accountId'])

    def test_get_impersonation_token_with_bad_key(self, user):

        client = create_client(key=BAD_KEY)
        # account_id = self.get_account_id(client=stack)
        with pytest.raises(InvalidRequestError):
            # impersonation_token = client.get_impersonation_token(user['accountId'])
            client.get_impersonation_token(user['accountId'])

    def impersonate_question_by_account_id_happy_path(self, client, user, myself):

        question = client.impersonate_question_by_account_id(TEST_TITLE, TEST_BODY, TEST_TAGS,
                                                             user['accountId'])
        question_owner = question['owner']
        self.assert_different_user_id(question_owner, myself)
        assert question_owner['accountId'] == user['accountId']

    def impersonate_question_by_user_id_happy_path(self, client, user, myself):

        question = client.impersonate_question_by_account_id(TEST_TITLE, TEST_BODY, TEST_TAGS,
                                                             user['id'])
        question_owner = question['owner']
        self.assert_different_user_id(question_owner, myself)
        assert question_owner['id'] == user['id']

    def impersonate_question_by_email_happy_path(self, client, user, myself):

        question = client.impersonate_question_by_account_id(TEST_TITLE, TEST_BODY, TEST_TAGS,
                                                             user['email'])
        question_owner = question['owner']
        self.assert_different_user_id(question_owner, myself)
        assert question_owner['id'] == user['id']

    def assert_different_user_id(self, user1, user2):

        assert user1['id'] != user2['id']


class TestOtherFunctions(object):

    def test_export_to_json_happy_path(self, client):

        file_name = "questions.json"
        directory = "cheesepuffs"
        file_path = os.path.join(directory, file_name)

        questions = client.get_questions()
        client.export_to_json(file_name, questions, directory=directory)
        assert os.path.exists(directory)
        assert os.path.isdir(directory)
        assert os.path.exists(file_path)

        shutil.rmtree(directory)  # clean up creation of directory and file


def test_clean_up_questions_created_by_tests(client):

    questions = client.get_questions(page=1, pagesize=30, one_page_limit=False, sort="creation",
                                     order="desc")
    for question in questions:
        if question['title'] == TEST_TITLE:
            client.delete_question(question['id'])


def test_clean_up_articles_created_by_tests(client):

    articles = client.get_articles(page=1, pagesize=30, one_page_limit=False, sort="creation",
                                   order="desc")
    for article in articles:
        if article['title'] == TEST_TITLE:
            client.delete_article(article['id'])


def random_string(length):
    return ''.join(random.choice(string.ascii_letters) for x in range(length))


def validate_communities(communities):

    if not communities:
        raise NoObjectTypeError("There are no communities available to complete test. "
                                "Create at least one community and rerun tests.")


class NoObjectTypeError(Exception):
    """If there are no objects required for testing"""
    pass
