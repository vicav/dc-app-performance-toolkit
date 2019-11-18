import xmlrpc.client

from util.data_preparation.api.abstract_clients import RestClient, Client


BATCH_SIZE_SEARCH = 500


class ConfluenceRestClient(RestClient):

    def get_content_search(self, start=0, limit=100, cql=None, expand="space"):
        """
        Returns all content. This only includes pages that the user has permission to view.
        :param start: The starting index of the returned boards. Base index: 0.
        :param limit: The maximum number of boards to return per page. Default: 50.
        :param cql: Filters results to boards of the specified type. Valid values: page, blogpost
        :param expand: Responds with additional values. Valid values: space,history,body.view,metadata.label
        :return: Returns the requested content, at the specified page of the results.
        """
        fetched_records_per_call = 200
        loop_count = limit // fetched_records_per_call + 1
        content = list()
        last_loop_remainder = limit % fetched_records_per_call

        while loop_count > 0:
            api_url = (
                    self.host + f'/rest/api/content/search?cql={cql}'
                                f'&start={start}'
                                f'&limit={limit}'
                                f'&expand={expand}'
            )
            request = self.get(api_url, "Could not retrieve content")

            content.extend(request.json()['results'])
            if len(content) < 0:
                raise Exception(f"Content with {cql} is empty")

            loop_count -= 1
            if loop_count == 1:
                limit = last_loop_remainder

            start += len(request.json()['results'])

        return content

    def get_users(self, prefix, count):
        users_list = self.search(f"user~{prefix}", limit=count)
        return users_list

    def search(self, cql, cqlcontext=None, expand=None, start=0, limit=500):
        """
        Fetch a list of content using the Confluence Query Language (CQL).
        :param cql: a cql query string to use to locate content
        :param cqlcontext: the context to execute a cql search in, this is the json serialized form of SearchContext
        :param expand: a comma separated list of properties to expand on the content
        :param start: the start point of the collection to return
        :param limit: the limit of the number of items to return, this may be restricted by fixed system limits
        :return:
        """
        loop_count = limit // BATCH_SIZE_SEARCH + 1
        last_loop_remainder = limit % BATCH_SIZE_SEARCH

        search_results_list = list()
        limit = BATCH_SIZE_SEARCH if limit > BATCH_SIZE_SEARCH else limit

        while loop_count > 0:
            api_url = f'{self.host}/rest/api/search?cql={cql}&start={start}&limit={limit}'
            response = self.get(api_url, "Search failed")

            search_results_list.extend(response.json()['results'])
            loop_count -= 1
            start += len(response.json())
            if loop_count == 1:
                limit = last_loop_remainder

        return search_results_list


class ConfluenceRpcClient(Client):

    def create_user(self, username=None, password=None):
        """
        Creates user. Uses XML-RPC protocol
        (https://developer.atlassian.com/server/confluence/confluence-xml-rpc-and-soap-apis/)
        :param username: Username to create
        :param password: Password for user
        :return: user
        """
        proxy = xmlrpc.client.ServerProxy(self.host + "/rpc/xmlrpc")
        token = proxy.confluence2.login(self.user, self.password)

        if not proxy.confluence2.hasUser(token, username):
            user_definition = {
                "email": f"{username}@test.com",
                "fullname": username.capitalize(),
                "name": username,
                "url": self.host + f"/display/~{username}"
            }
            proxy.confluence2.addUser(token, user_definition, password)
            user_definition['password'] = password
            return user_definition
        else:
            raise Exception(f"Can't create user {username}: user already exists.")
