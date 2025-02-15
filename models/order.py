from datetime import datetime, timedelta

from bson.objectid import ObjectId

from config import URL

from pymongo import MongoClient

DB = MongoClient(URL)["loveat2"]
ORDER_COLLECTION = DB["order"]
ITEM_COLLECTION = DB["item"]
COMBO_COLLECTION = DB["combo"]
BUSINESS_COLLECTION = DB["businessTime"]

MAX_ORDERID = -1


def find_by_time(start, end):
    return {"takenAt": {"$gte": start, "$lte": end}, "state": "end"}


def get_raw_history(start, end):
    return ORDER_COLLECTION.find(
        find_by_time(start, end),
        {
            "content._id": 0,
            "content.type": 0,
            "_id": 0,
            "takenAt": 0,
            "state": 0,
            "total": 0,
            "userName": 0,
        },
    )


def build_analysis_struct(interval, slot):
    result = {
        "interval": [],
        "itemAnalysis": {},
        "genderAnalysis": [
            {"female": 0, "male": 0, "total": 0} for i in range(slot)
        ],
    }
    for i in range(slot):
        if i == slot - 1:
            result["interval"].append("{}+".format(i * interval))
        else:
            result["interval"].append(
                "{}-{}".format(i * interval, interval * (i + 1) - 1)
            )
    return result


def get_analysis_data(start, end):
    interval = 10
    slot = 7
    result = build_analysis_struct(interval, slot)
    # query
    raw_data = ORDER_COLLECTION.aggregate(
        [
            {"$match": find_by_time(start, end)},
            {
                "$lookup": {
                    "from": "user",
                    "localField": "userName",
                    "foreignField": "userName",
                    "as": "user",
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "content.name": 1,
                    "content.quantity": 1,
                    "user.birth": 1,
                    "user.gender": 1,
                    "user.userName": 1,
                    "takenAt": 1,
                }
            },
            {
                "$unwind": {
                    "path": "$user",
                    "preserveNullAndEmptyArrays": False,
                }
            },
        ]
    )
    # first calc
    for data in raw_data:
        age = (data["takenAt"] - data["user"]["birth"]).days // 365
        index = min(age // interval, slot - 1)
        # build gender analysis
        result["genderAnalysis"][index][data["user"]["gender"]] += 1
        # build item analysis
        for content in data["content"]:
            if content["name"] not in result["itemAnalysis"]:
                result["itemAnalysis"][content["name"]] = {
                    "female": [0] * slot,
                    "male": [0] * slot,
                    "sum": [0] * slot,
                    "femaleTotal": 0,
                    "maleTotal": 0,
                    "total": 0,
                }
            result["itemAnalysis"][content["name"]][data["user"]["gender"]][
                index
            ] += 1
    # sum
    for genderAnalysis in result["genderAnalysis"]:
        genderAnalysis["total"] = (
            genderAnalysis["female"] + genderAnalysis["male"]
        )
    for itemAnalysis in result["itemAnalysis"].values():
        itemAnalysis["femaleTotal"] = sum(itemAnalysis["female"])
        itemAnalysis["maleTotal"] = sum(itemAnalysis["male"])
        itemAnalysis["sum"] = [
            itemAnalysis["male"][i] + itemAnalysis["female"][i]
            for i in range(slot)
        ]
        itemAnalysis["total"] = (
            itemAnalysis["femaleTotal"] + itemAnalysis["maleTotal"]
        )
    return result


def get_max_orderid():
    result = list(
        ORDER_COLLECTION.aggregate(
            [
                {"$addFields": {"orderID": {"$toInt": "$orderID"}}},
                {"$group": {"_id": None, "max": {"$max": "$orderID"}}},
            ]
        )
    )
    if len(result) == 0:
        return 0
    else:
        return result[0]["max"]


def get_not_end_by_username(user_name):
    return ORDER_COLLECTION.aggregate(
        [
            {
                "$match": {
                    "userName": user_name,
                    "state": {"$nin": ["end"]},
                    "takenAt": {"$gte": datetime.now() - timedelta(days=1)},
                }
            },
            {
                "$addFields": {
                    "takenAt": {
                        "$dateToString": {
                            "format": "%Y/%m/%d %H:%M",
                            "date": "$takenAt",
                        }
                    }
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "createdAt": 0,
                    "userName": 0,
                    "total": 0,
                    "content._id": 0,
                    "content.type": 0,
                }
            },
        ]
    )


def add_order(data):
    def build_business_time(time_str):
        result = data["takenAt"][:-6] + "-" + time_str
        return datetime.strptime(result, "%Y-%m-%d-%H:%M")

    # init max orderid
    global MAX_ORDERID
    if MAX_ORDERID == -1:
        MAX_ORDERID = get_max_orderid()

    # check if takenAt is in business time insterval
    taken_at = datetime.strptime(data["takenAt"], "%Y-%m-%dT%H:%M")
    business_time = list(BUSINESS_COLLECTION.find_one({}, {"_id": 0}).values())
    business_time = business_time[taken_at.isoweekday() - 1]
    start = build_business_time(business_time["start"])
    end = build_business_time(business_time["end"])

    if start <= taken_at <= end:
        MAX_ORDERID += 1
        for meal in data["content"]:
            meal["id"] = ObjectId(meal["id"])
            if meal["category"] == "item":
                tar = ITEM_COLLECTION.find_one({"id": meal["id"]}, {"name": 1})
            else:
                tar = COMBO_COLLECTION.find_one(
                    {"id": meal["id"]}, {"name": 1}
                )
            meal["name"] = tar["name"]

        ORDER_COLLECTION.insert_one(
            {
                "userName": data["userName"],
                "notes": data["notes"],
                "total": data["total"],
                "content": data["content"],
                "state": "unknown",
                "createdAt": datetime.now(),
                "takenAt": taken_at,
                "orderID": str(MAX_ORDERID),
            }
        )
        return True
    else:
        return False


def update_state(data):
    state = ["doing", "cancel", "finish", "end"]
    if data["state"] in state:
        ORDER_COLLECTION.update_one(
            {"_id": ObjectId(data["id"])}, {"$set": {"state": data["state"]}}
        )
        result = ORDER_COLLECTION.find_one(
            {"_id": ObjectId(data["id"])}, {"userName": 1, "_id": 0}
        )
        return result["userName"] if result is not None else result
    else:
        return None


def get_todo_order():
    result = ORDER_COLLECTION.aggregate(
        [
            {"$match": {"state": {"$in": ["doing", "finish"]}}},
            {
                "$lookup": {
                    "from": "user",
                    "localField": "userName",
                    "foreignField": "userName",
                    "as": "user",
                }
            },
            {"$unwind": {"path": "$user"}},
            {"$project": {"content._id": 0, "content.type": 0}},
            {
                "$project": {
                    "_id": {"$toString": "$_id"},
                    "orderID": {"$toInt": "$orderID"},
                    "takenAt": {
                        "$dateToString": {
                            "format": "%Y/%m/%d %H:%M",
                            "date": "$takenAt",
                        }
                    },
                    "state": 1,
                    "content": 1,
                    "notes": 1,
                    "user_id": {"$toString": "$user._id"},
                    "phone": "$user.phone",
                }
            },
            {"$sort": {"orderID": -1}},
        ]
    )
    return result


def get_unknown_order():
    result = ORDER_COLLECTION.aggregate(
        [
            {"$match": {"state": "unknown"}},
            {"$project": {"content.id": 0, "content.type": 0}},
            {
                "$project": {
                    "_id": {"$toString": "$_id"},
                    "takenAt": {
                        "$dateToString": {
                            "format": "%Y/%m/%d %H:%M",
                            "date": "$takenAt",
                        }
                    },
                    "content": 1,
                    "notes": 1,
                }
            },
            {"$sort": {"orderID": 1}},
        ]
    )
    return result
