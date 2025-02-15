from flask import Blueprint, current_app, make_response, send_from_directory

from models import image

root = Blueprint("root", __name__)


@root.route("/img/<uuid>")
def show_image(uuid):
    pic = image.get_by_uuid(uuid)
    if pic is None:
        return send_from_directory(
            current_app.static_folder, "img/default.png"
        )
    else:
        response = make_response(pic)
        response.headers.set("Content-Type", "image/jpeg")
        response.headers.set(
            "Content-Disposition", "attachment", filename="{}.jpg".format(uuid)
        )
        return response


@root.route("/firebase-messaging-sw.js", methods=["GET"])
def service_worker():
    return send_from_directory(
        current_app.static_folder,
        "js/lib/firebase-messaging-sw.js",
        mimetype="application/javascript",
    )


@root.route("/favicon.ico", methods=["GET"])
def favicon():
    return send_from_directory(current_app.static_folder, "favicon.ico")
