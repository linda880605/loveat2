import json

URL_PREFIX = "/api/user"


class TestUser(object):
    def test_login_success(self, client):
        url = URL_PREFIX + "/login"
        rv = client.post(
            url,
            data=json.dumps(
                {"userName": "admin_name", "password": "123456789"}
            ),
            content_type="application/json",
        )
        assert rv.status_code == 200

    def test_login_nonexist_user(self, client):
        url = URL_PREFIX + "/login"
        rv = client.post(
            url,
            data=json.dumps({"userName": "nonexist", "password": "123456789"}),
            content_type="application/json",
        )
        assert rv.status_code == 401

    def test_login_wrong_pwd(self, client):
        url = URL_PREFIX + "/login"
        rv = client.post(
            url,
            data=json.dumps(
                {"userName": "admin_name", "password": "12345678"}
            ),
            content_type="application/json",
        )
        assert rv.status_code == 401

    def test_register_success(self, client):
        # check if there is no customer_name2 in user collection
        new_user = client.application.config["db"]["USER_COLLECTION"].find_one(
            {"userName": "customer_name2"}
        )
        assert new_user is None
        # test register api
        url = URL_PREFIX + "/register"
        rv = client.post(
            url,
            data=json.dumps(
                {
                    "userName": "customer_name2",
                    "password": "123456789",
                    "gender": "female",
                    "phone": "0920198409",
                    "email": "customer@gmail.com",
                    "age": 20,
                }
            ),
            content_type="application/json",
        )
        assert rv.status_code == 200
        # check if insert customer_name2 success
        new_user = client.application.config["db"]["USER_COLLECTION"].find_one(
            {"userName": "customer_name2"}
        )
        assert new_user is not None

    def test_register_duplicate_account(self, client):
        # check if there is only one customer_name in user collection
        new_user = list(
            client.application.config["db"]["USER_COLLECTION"].find(
                {"userName": "customer_name"}
            )
        )
        assert len(new_user) == 1
        # test register api
        url = URL_PREFIX + "/register"
        rv = client.post(
            url,
            data=json.dumps(
                {
                    "userName": "customer_name",
                    "password": "123456789",
                    "gender": "female",
                    "phone": "0920198409",
                    "email": "customer@gmail.com",
                    "age": 20,
                }
            ),
            content_type="application/json",
        )
        assert rv.status_code == 409
        # check if there is only one customer_name in user collection
        new_user = list(
            client.application.config["db"]["USER_COLLECTION"].find(
                {"userName": "customer_name"}
            )
        )
        assert len(new_user) == 1

    def test_register_wrong_fomat(self, client):
        # check if there is no customer_name3 in user collection
        new_user = client.application.config["db"]["USER_COLLECTION"].find_one(
            {"userName": "customer_name3"}
        )
        assert new_user is None
        # test register api
        url = URL_PREFIX + "/register"
        rv = client.post(
            url,
            data=json.dumps(
                {
                    "userName": "customer_name3",
                    "password": "123456789",
                    "wrong-fild": "female",
                    "phone": "0920198409",
                    "email": "customer@gmail.com",
                    "age": 20,
                }
            ),
            content_type="application/json",
        )
        assert rv.status_code == 400
        # check if there is no customer_name3 in user collection
        new_user = client.application.config["db"]["USER_COLLECTION"].find_one(
            {"userName": "customer_name3"}
        )
        assert new_user is None

    def test_update_token_success(self, client, customer):
        # check original token is empty
        token = client.application.config["db"]["USER_COLLECTION"].find_one(
            {"userName": "customer_name"}, {"token": 1}
        )
        assert token["token"] == ""
        # check update token api
        update_token = "this is a new token"
        url = URL_PREFIX + "/token"
        rv = client.post(
            url,
            data=json.dumps({"token": update_token}),
            content_type="application/json",
        )
        assert rv.status_code == 200
        # check if update token of cutomer_name success
        token = client.application.config["db"]["USER_COLLECTION"].find_one(
            {"userName": "customer_name"}, {"token": 1}
        )
        assert token["token"] == update_token

    def test_update_token_unauthorized(self, client):
        # check update token api
        update_token = "this is a new token"
        url = URL_PREFIX + "/token"
        rv = client.post(
            url,
            data=json.dumps({"token": update_token}),
            content_type="application/json",
        )
        assert rv.status_code == 401
