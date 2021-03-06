# -*- coding: utf-8 -*-
"""view module prilog application

     * view function, and run Flask

"""
from flask import Flask, render_template, request, session, redirect, jsonify
import os
import re
import json
import urllib.parse
import time as tm
import analyze as al
import common as cm
import error_list as err

stream_dir = "/tmp/stream_"
#if not os.path.exists(stream_dir):
#    os.mkdir(stream_dir)
    
cache_dir = "/tmp/cache_"
#if not os.path.exists(cache_dir):
#    os.mkdir(cache_dir)
    
download_dir = "/tmp/download_"
#if not os.path.exists(download_dir):
#    os.mkdir(download_dir)
    
def get_rest_result(title, time_line, time_data, total_damage, debuff_value):
    rest_result = {"title": title, "timeline": time_line, "process_time": time_data, "total_damage": total_damage,
                   "debuff_value": debuff_value}

    if time_line:
        rest_result["timeline_txt"] = "\r\n".join(time_line)
        if debuff_value:
            rest_result["timeline_txt_debuff"] = "\r\n".join(list(
                map(lambda x: "↓{} {}".format(str(debuff_value[x[0]][0:]).rjust(3, " "), x[1]),
                    enumerate(time_line))))
        else:
            rest_result["timeline_txt_debuff"] = False
    else:
        rest_result["timeline_txt"] = False
        rest_result["timeline_txt_debuff"] = False

    return rest_result

def do_analyze(url):

    # ID部分の取り出し
    youtube_id = al.get_youtube_id(url)
    if not youtube_id:
        return

    cached = cm.cache_check(youtube_id)
    # 5分経過した3xx キャッシュ以外は再解析しない
    if cached:
        return

    # youtube動画検索/検証
    path, title, length, thumbnail, url_result = al.search(youtube_id)
    if url_result % 100 // 10 == 2:
        cm.save_cache(youtube_id, title, False, False, False, False, url_result)
    else:
        # TL解析
        time_line, time_data, total_damage, debuff_value, analyze_result = al.analyze_movie(path)
        # キャッシュ保存
        cm.save_cache(youtube_id, title, time_line, False, total_damage, debuff_value, analyze_result)

app = Flask(__name__)
app.config.from_object(__name__)
app.config['SECRET_KEY'] = 'zJe09C5c3tMf5FnNL09C5e6SAzZuY'
app.config['JSON_AS_ASCII'] = False

# @app.route("/", methods=["GET", "POST"])
# def index():
#     if request.method == "POST":
#         url = (request.form["Url"])

#         # urlからid部分の抽出
#         youtube_id = al.get_youtube_id(url)
#         if youtube_id is False:
#             error = err.get_error_message(err.ERR_BAD_URL)
#             return render_template("index.html", error=error)

#         cache = cm.cache_check(youtube_id)

#         if cache is not False:
#             title, time_line, time_data, total_damage, debuff_value, past_status = cache
#             if past_status % 100 // 10 == 0:
#                 debuff_dict, data_txt, data_url, total_damage = get_web_txt(youtube_id, title,
#                                                                             time_line, debuff_value, total_damage)

#                 return render_template("result.html", title=title, timeLine=time_line,
#                                        timeData=time_data, totalDamage=total_damage, debuffDict=debuff_dict,
#                                        data_txt=data_txt, data_url=data_url)

#             else:
#                 error = err.get_error_message(past_status)
#                 return render_template("index.html", error=error)

#         # start download
#         dl_queue_path = dl_queue_dir + str(youtube_id)
#         dl_doing_path = dl_doing_dir + str(youtube_id)

#         # 既にキューに登録されているか確認
#         queued = os.path.exists(dl_queue_path)
#         if not queued:  # 既にダウンロード待機中ではない場合、ダウンロード待機キューに登録
#             cm.queue_append(dl_queue_path)
#             # キューが回ってきたか確認し、来たらダウンロード実行
#             while True:
#                 if not cm.is_path_exists(dl_doing_path) and cm.is_path_current(dl_queue_path):
#                     break

#                 timeout = cm.watchdog_download(youtube_id, 5)  # 5分間タイムアウト監視

#                 if timeout:
#                     cm.clear_path(dl_queue_path)
#                     error = "動画の解析待ちでタイムアウトが発生しました。再実行をお願いします。"
#                     return render_template("index.html", error=error)

#                 tm.sleep(1)

#         else:  # ダウンロード待機中の場合エラーメッセージ表示
#             cm.clear_path(dl_queue_path)
#             error = "同一の動画が解析中です。時間を置いて再実行をお願いします。"
#             return render_template("index.html", error=error)

#         path, title, length, thumbnail, url_result = al.search(youtube_id)
#         cm.clear_path(dl_queue_path)

#         if url_result % 100 // 10 == 2:
#             error = err.get_error_message(url_result)
#             cm.save_cache(youtube_id, title, False, False, False, False, url_result)
#             return render_template("index.html", error=error)

#         session["path"] = path
#         session["title"] = title
#         session["youtube_id"] = youtube_id
#         length = int(int(length) / 8) + 3

#         return render_template("analyze.html", title=title, length=length, thumbnail=thumbnail)

#     elif request.method == "GET":
#         if "v" in request.args:  # ?v=YoutubeID 形式のGETであればリザルト返却
#             youtube_id = request.args.get("v")
#             if re.fullmatch(r"^([a-zA-Z0-9_-]{11})$", youtube_id):
#                 cache = cm.cache_check(youtube_id)
#                 if cache is not False:
#                     title, time_line, time_data, total_damage, debuff_value, past_status = cache
#                     if past_status % 100 // 10 == 0:
#                         debuff_dict, data_txt, data_url, total_damage = get_web_txt(youtube_id, title,
#                                                                                     time_line, debuff_value,
#                                                                                     total_damage)

#                         return render_template("result.html", title=title, timeLine=time_line,
#                                                timeData=time_data, totalDamage=total_damage, debuffDict=debuff_dict,
#                                                data_txt=data_txt, data_url=data_url)

#                     else:
#                         error = err.get_error_message(past_status)
#                         return render_template("index.html", error=error)

#                 else:  # キャッシュが存在しない場合は解析
#                     # start download
#                     dl_queue_path = dl_queue_dir + str(youtube_id)
#                     dl_doing_path = dl_doing_dir + str(youtube_id)

#                     # 既にキューに登録されているか確認
#                     queued = os.path.exists(dl_queue_path)
#                     if not queued:  # 既にダウンロード待機中ではない場合、ダウンロード待機キューに登録
#                         cm.queue_append(dl_queue_path)
#                         # キューが回ってきたか確認し、来たらダウンロード実行
#                         while True:
#                             if not cm.is_path_exists(dl_doing_path) and cm.is_path_current(dl_queue_path):
#                                 break

#                             timeout = cm.watchdog_download(youtube_id, 5)  # 5分間タイムアウト監視

#                             if timeout:
#                                 cm.clear_path(dl_queue_path)
#                                 error = "動画の解析待ちでタイムアウトが発生しました。再実行をお願いします。"
#                                 return render_template("index.html", error=error)

#                             tm.sleep(1)

#                     else:  # ダウンロード待機中の場合エラーメッセージ表示
#                         cm.clear_path(dl_queue_path)
#                         error = "同一の動画が解析中です。時間を置いて再実行をお願いします。"
#                         return render_template("index.html", error=error)

#                     path, title, length, thumbnail, url_result = al.search(youtube_id)
#                     cm.clear_path(dl_queue_path)

#                     if url_result % 100 // 10 == 2:
#                         error = err.get_error_message(url_result)
#                         cm.save_cache(youtube_id, title, False, False, False, False, url_result)
#                         return render_template("index.html", error=error)

#                     session["path"] = path
#                     session["title"] = title
#                     session["youtube_id"] = youtube_id
#                     length = int(int(length) / 8) + 3

#                     return render_template("analyze.html", title=title, length=length, thumbnail=thumbnail)

#             else:  # prilog.jp/(YoutubeID)に該当しないリクエスト
#                 error = "不正なリクエストです"
#                 return render_template("index.html", error=error)
            
#         else:
#             path = session.get("path")
#             session.pop("path", None)
#             session.pop("title", None)
#             session.pop("youtube_id", None)

#             error = None
#             if str(path).isdecimal():
#                 error = err.get_error_message(path)

#             elif path is not None:
#                 cm.clear_path(path)

#             return render_template("index.html", error=error)


# @app.route("/analyze", methods=["GET", "POST"])
# def analyze():
#     path = session.get("path")
#     title = session.get("title")
#     youtube_id = session.get("youtube_id")
#     session.pop("path", None)

#     if request.method == "GET" and path is not None:
#         # TL解析
#         time_line, time_data, total_damage, debuff_value, status = al.analyze_movie(path)

#         # キャッシュ保存
#         status = cm.save_cache(youtube_id, title, time_line, False, total_damage, debuff_value, status)

#         if status % 100 // 10 == 0:
#             # 解析が正常終了ならば結果を格納
#             session["time_line"] = time_line
#             session["time_data"] = time_data
#             session["total_damage"] = total_damage
#             session["debuff_value"] = debuff_value
#             return render_template("analyze.html")
#         else:
#             session["path"] = status
#             return render_template("analyze.html")
#     else:
#         return redirect("/")


# @app.route("/result", methods=["GET", "POST"])
# def result():
#     title = session.get("title")
#     time_line = session.get("time_line")
#     time_data = session.get("time_data")
#     total_damage = session.get("total_damage")
#     debuff_value = session.get("debuff_value")
#     youtube_id = session.get("youtube_id")
#     session.pop("title", None)
#     session.pop("time_line", None)
#     session.pop("time_data", None)
#     session.pop("total_damage", None)
#     session.pop("debuff_value", None)
#     session.pop("youtube_id", None)

#     if request.method == "GET" and time_line is not None:
#         debuff_dict, data_txt, data_url, total_damage = get_web_txt(youtube_id, title,
#                                                                     time_line, debuff_value, total_damage)

#         return render_template("result.html", title=title, timeLine=time_line,
#                                timeData=time_data, totalDamage=total_damage, debuffDict=debuff_dict,
#                                data_txt=data_txt, data_url=data_url)
#     else:
#         return redirect("/")


# @app.route("/download", methods=["GET", "POST"])
# def download():
#     if request.method == "GET":
#         return render_template("download.html")
#     else:
#         return redirect("/")


# @app.route("/rest", methods=["GET", "POST"])
# def rest():
#     if request.method == "GET":
#         return render_template("rest.html")
#     else:
#         return redirect("/")


@app.route("/rest/analyze", methods=["POST", "GET"])
def rest_analyze():
    status = err.ERR_REQ_UNEXPECTED
    is_parent = False
    rest_result = {}
    ret = {}
    url = ""
    raw_url = ""
    if request.method == "POST":
        if "Url" not in request.form:
            status = err.ERR_BAD_REQ

            ret["result"] = rest_result
            ret["msg"] = err.get_error_message(status)
            ret["status"] = status
            return jsonify(ret)
        else:
            raw_url = request.form["Url"]

    elif request.method == "GET":
        if "Url" not in request.args:
            status = err.ERR_BAD_REQ

            ret["result"] = rest_result
            ret["msg"] = err.get_error_message(status)
            ret["status"] = status
            return jsonify(ret)
        else:
            raw_url = request.args.get("Url")

    # URL抽出
    tmp_group = re.search('(?:https?://)?(?P<host>.*?)(?:[:#?/@]|$)', raw_url)

    if tmp_group:
        host = tmp_group.group('host')
        if host == "www.youtube.com" or host == "youtu.be":
            url = raw_url

    # キャッシュ確認
    youtube_id = al.get_youtube_id(url)
    if youtube_id is False:
        # 不正なurlの場合
        status = err.ERR_BAD_URL
    else:
        # 正常なurlの場合
        cache = cm.cache_check(youtube_id)
        if cache is not False:
            # キャッシュ有りの場合
            # キャッシュを返信
            title, time_line, time_data, total_damage, debuff_value, past_status = cache
            if past_status % 100 // 10 == 0:
                rest_result = get_rest_result(title, time_line, time_data, total_damage, debuff_value)

                ret["result"] = rest_result
                ret["msg"] = err.get_error_message(past_status)
                ret["status"] = past_status
                return jsonify(ret)

            else:
                ret["result"] = rest_result
                ret["msg"] = err.get_error_message(past_status)
                ret["status"] = past_status
                return jsonify(ret)

        # start analyze
        do_analyze(url)
        cache = cm.cache_check(youtube_id)
        if cache is not False:
            title, time_line, time_data, total_damage, debuff_value, past_status = cache
            rest_result = get_rest_result(title, time_line, time_data, total_damage, debuff_value)

            status = past_status

    ret["result"] = rest_result
    ret["msg"] = err.get_error_message(status)
    ret["status"] = status
    return jsonify(ret)


if __name__ == "__main__":
    app.run()
