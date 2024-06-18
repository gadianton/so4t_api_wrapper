# Stack Overflow for Teams API Wrapper
A Python wrapper for the Stack Overflow for Teams API, replicating the functionality of the Stack Overflow for Teams API in a more user-friendly way.

Full documentation for the API can be found at one of the following locations:
* Basic/Business API: https://api.stackoverflowteams.com/v3
* Enterprise API: https://YOUR.INSTANCE.URL/api/v3

## Table of Contents
* [Setup](https://github.com/jklick-so/so4t_api_wrapper?tab=readme-ov-file#setup)
* [Usage](https://github.com/jklick-so/so4t_api_wrapper?tab=readme-ov-file#basic-usage)
* [Support](https://github.com/jklick-so/so4t_api_wrapper?tab=readme-ov-file#support)


## Setup

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


## Usage
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

At this time, most/all the documentation for wrapper methods is documented along side the methods (i.e. in the code)

## Support
Disclaimer: the creator of this project works at Stack Overflow, but it is a labor of love that comes with no formal support from Stack Overflow. 

If you run into issues using the script, please [open an issue](https://github.com/jklick-so/so4t_api_wrapper/issues). You are also welcome to edit the script to suit your needs, steal the code, or do whatever you want with it.
