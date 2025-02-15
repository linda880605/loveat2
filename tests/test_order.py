import json

from bson.objectid import ObjectId

URL_PREFIX = "/api/order"


class TestOrder(object):
    new_order = {
        "takenAt": "2019-10-31T12:00",
        "notes": "不要番茄醬",
        "total": 600,
        "content": [
            {
                "id": "5dd67f098f0f6afb3ebc1b68",
                "category": "item",
                "quantity": 3,
            }
        ],
    }
    wrong_order = {
        "wrong_format": "2019-10-31T12:00",
        "notes": "不要番茄醬",
        "total": 600,
        "content": [
            {
                "id": "5dd67f098f0f6afb3ebc1b68",
                "category": "item",
                "quantity": 3,
            }
        ],
    }
    update_order_id = "5dd8f94ff5a90a5568400a57"
    update_nonexist_order_id = "6dd8f94ff5a90a5568400a57"

    """ can't test, because mongomock haven't supported "$addFields"
    def test_add_success(self, client, customer, mock_item):
        url = URL_PREFIX + "/new"
        print(url)
        rv = client.post(
            url,
            data=json.dumps(self.new_order),
            content_type="application/json",
        )
        assert rv.status_code == 200
    """

    def test_add_unauthorized(self, client, mock_item):
        # test add api
        url = URL_PREFIX + "/new"
        rv = client.post(
            url,
            data=json.dumps(self.new_order),
            content_type="application/json",
        )
        assert rv.status_code == 401

    """ can't test, because mongomock haven't supported "$addFields"
    def test_add_wrong_format(self , client, customer, mock_item):
        # test add api
        url = URL_PREFIX + "/new"
        rv = client.post(
            url,
            data=json.dumps(self.new_order),
            content_type="application/json",
        )
        assert rv.status_code == 422
    """

    def test_update_success(self, client, admin):
        url = URL_PREFIX + "/update"
        state_enum = ["doing", "cancel", "finish", "end"]
        for state in state_enum:
            rv = client.post(
                url,
                data=json.dumps({"id": self.update_order_id, "state": state}),
                content_type="application/json",
            )
            assert rv.status_code == 200
            cur_state = client.application.config["db"][
                "ORDER_COLLECTION"
            ].find_one({"_id": ObjectId(self.update_order_id)}, {"state": 1})[
                "state"
            ]
            assert cur_state == state

    def test_update_unauthorized(self, client):
        # test update api
        url = URL_PREFIX + "/update"
        rv = client.post(
            url,
            data=json.dumps({"id": self.update_order_id, "state": "cancel"}),
            content_type="application/json",
        )
        assert rv.status_code == 403
        # test if order update state
        cur_state = client.application.config["db"][
            "ORDER_COLLECTION"
        ].find_one({"_id": ObjectId(self.update_order_id)}, {"state": 1})[
            "state"
        ]
        assert cur_state == "unknown"

    def test_update_by_customer(self, client, customer):
        # test update api
        url = URL_PREFIX + "/update"
        rv = client.post(
            url,
            data=json.dumps({"id": self.update_order_id, "state": "cancel"}),
            content_type="application/json",
        )
        assert rv.status_code == 403
        # test if order update state
        cur_state = client.application.config["db"][
            "ORDER_COLLECTION"
        ].find_one({"_id": ObjectId(self.update_order_id)}, {"state": 1})[
            "state"
        ]
        assert cur_state == "unknown"

    def test_update_nonexist_order(self, client, admin):
        # test update api
        url = URL_PREFIX + "/update"
        rv = client.post(
            url,
            data=json.dumps(
                {"id": self.update_nonexist_order_id, "state": "cancel"}
            ),
            content_type="application/json",
        )
        assert rv.status_code == 404
