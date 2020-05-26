# -*- coding: utf-8 -*-
"""view module prilog application

     * view function, and run Flask

"""
from flask import Flask, render_template, request, session, redirect, jsonify
import os
import re
import traceback
from pytube import YouTube
import time as tm
import cv2
import json
import urllib.parse
import characters as cd
import after_caluculation as ac

# キャラクター名テンプレート
characters_data = np.load("model/UB_name.npy")

# 時間テンプレート
sec_data = np.load("model/timer_sec.npy")

# MENUテンプレート
menu_data = np.load("model/menu.npy")

# ダメージレポートテンプレート
damage_menu_data = np.load("model/damage_menu.npy")

# ダメージ数値テンプレート
damage_data = np.load("model/damage_data.npy")

# アンナアイコンテンプレート
icon_data = np.load("model/icon_data.npy")

# キャラクター名一覧
characters = cd.characters_name

# 数値一覧
numbers = [
    "0",
    "1",
    "2",
    "3",
    "4",
    "5",
    "6",
    "7",
    "8",
    "9",
]

# 解析可能な解像度
FRAME_COLS = 1280
FRAME_ROWS = 720

# 画像認識範囲
UB_ROI = (490, 98, 810, 132)
MIN_ROI = (1070, 22, 1089, 44)
TEN_SEC_ROI = (1091, 22, 1107, 44)
ONE_SEC_ROI = (1105, 22, 1121, 44)
MENU_ROI = (1100, 0, 1280, 90)
DAMAGE_MENU_ROI = (1040, 36, 1229, 66)
DAMAGE_DATA_ROI = (60, 54, 230, 93)
CHARACTER_ICON_ROI = (234, 506, 1046, 668)

MENU_LOC = (63, 23)

DAMAGE_NUMBER_ROI = [
    (0, 0, 26, 39),
    (22, 0, 50, 39),
    (46, 0, 74, 39),
    (70, 0, 98, 39),
    (94, 0, 122, 39),
    (118, 0, 146, 39),
    (142, 0, 170, 39)
]

# 時刻格納位置
TIMER_MIN = 2
TIMER_TEN_SEC = 1
TIMER_SEC = 0

# 認識判定値
UB_THRESH = 0.65
TIMER_THRESH = 0.7
MENU_THRESH = 0.6
DAMAGE_THRESH = 0.7
ICON_THRESH = 0.65

FOUND = 1
NOT_FOUND = 0

# エラーリスト
NO_ERROR = 0
ERROR_BAD_URL = 1
ERROR_TOO_LONG = 2
ERROR_NOT_SUPPORTED = 3
ERROR_CANT_GET_MOVIE = 4
ERROR_REQUIRED_PARAM = 5
ERROR_PROCESS_FAILED = 6

# キャッシュ格納数
CACHE_NUM = 5

stream_dir = "/tmp/stream/"
cache_dir = "/tmp/cache/"
pending_dir = "/tmp/pending/"

def cache_check(youtube_id):
    # キャッシュ有無の確認
    try:
        cache_path = cache_dir + urllib.parse.quote(youtube_id) + '.json'
        ret = json.load(open(cache_path))
        if len(ret) is CACHE_NUM:
            # キャッシュから取得した値の数が規定値
            return ret
        else:
            # 異常なキャッシュの場合
            clear_path(cache_path)
            return False

    except FileNotFoundError:
        return False

def pending_append(path):
    # 解析中のIDを保存
    try:
        with open(path, mode='w'):
            pass
    except FileExistsError:
        pass

    return


def clear_path(path):
    # ファイルの削除
    try:
        os.remove(path)
    except PermissionError:
        pass
    except FileNotFoundError:
        pass

    return


def get_youtube_id(url):
    # ID部分の取り出し
    work_id = re.findall('.*watch(.{14})', url)
    if not work_id:
        work_id = re.findall('.youtu.be/(.{11})', url)
        if not work_id:
            return False

    ret = work_id[0].replace('?v=', '')

    return ret


def search(youtube_id):
    # youtubeの動画を検索し取得
    youtube_url = 'https://www.youtube.com/watch?v=' + youtube_id
    try:
        yt = YouTube(youtube_url)
    except:
        print(traceback.format_exc())
        return None, None, None, None, ERROR_CANT_GET_MOVIE

    movie_thumbnail = yt.thumbnail_url
    movie_length = yt.length
    if int(movie_length) > 480:
        return None, None, None, None, ERROR_TOO_LONG

    stream = yt.streams.get_by_itag("22")
    if stream is None:
        return None, None, None, None, ERROR_NOT_SUPPORTED

    movie_title = stream.title
    movie_name = tm.time()
    movie_path = stream.download(stream_dir, str(movie_name))

    return movie_path, movie_title, movie_length, movie_thumbnail, NO_ERROR


def analyze_movie(movie_path):
    # 動画解析し結果をリストで返す
    start_time = tm.time()
    video = cv2.VideoCapture(movie_path)

    frame_count = int(video.get(7))  # フレーム数を取得
    frame_rate = int(video.get(5))  # フレームレート(1フレームの時間単位はミリ秒)の取得

    frame_width = int(video.get(3))  # フレームの幅
    frame_height = int(video.get(4))  # フレームの高さ

    if frame_width != int(FRAME_COLS) or frame_height != int(FRAME_ROWS):
        video.release()
        clear_path(movie_path)

        return None, None, None, None, ERROR_NOT_SUPPORTED

    n = 0.34  # n秒ごと*
    ub_interval = 0

    time_min = "1"
    time_sec10 = "3"
    time_sec1 = "0"

    menu_check = False

    min_roi = MIN_ROI
    tensec_roi = TEN_SEC_ROI
    onesec_roi = ONE_SEC_ROI
    ub_roi = UB_ROI
    damage_menu_roi = DAMAGE_MENU_ROI
    damage_data_roi = DAMAGE_DATA_ROI

    ub_data = []
    ub_data_value = []
    time_data = []
    characters_find = []

    tmp_damage = ["0", "0", "0", "0", "0", "0", "0"]
    total_damage = False

    cap_interval = int(frame_rate * n)
    skip_frame = 5 * cap_interval

    if (frame_count / frame_rate) < 600:  # 10分未満の動画しか見ない
        for i in range(frame_count):  # 動画の秒数を取得し、回す
            ret = video.grab()
            if ret is False:
                break

            if i % cap_interval is 0:
                if ((i - ub_interval) > skip_frame) or (ub_interval == 0):
                    ret, work_frame = video.read()

                    if ret is False:
                        break
                    work_frame = edit_frame(work_frame)

                    if menu_check is False:
                        menu_check, menu_loc = analyze_menu_frame(work_frame, menu_data, MENU_ROI)
                        if menu_check is True:
                            loc_diff = np.array(MENU_LOC) - np.array(menu_loc)
                            roi_diff = (loc_diff[0], loc_diff[1], loc_diff[0], loc_diff[1])
                            min_roi = np.array(MIN_ROI) - np.array(roi_diff)
                            tensec_roi = np.array(TEN_SEC_ROI) - np.array(roi_diff)
                            onesec_roi = np.array(ONE_SEC_ROI) - np.array(roi_diff)
                            ub_roi = np.array(UB_ROI) - np.array(roi_diff)
                            damage_menu_roi = np.array(DAMAGE_MENU_ROI) - np.array(roi_diff)
                            damage_data_roi = np.array(DAMAGE_DATA_ROI) - np.array(roi_diff)

                            analyze_anna_icon_frame(work_frame, CHARACTER_ICON_ROI, characters_find)

                    else:
                        if time_min is "1":
                            time_min = analyze_timer_frame(work_frame, min_roi, 2, time_min)

                        time_sec10 = analyze_timer_frame(work_frame, tensec_roi, 6, time_sec10)
                        time_sec1 = analyze_timer_frame(work_frame, onesec_roi, 10, time_sec1)

                        ub_result = analyze_ub_frame(work_frame, ub_roi, time_min, time_sec10, time_sec1,
                                                     ub_data, ub_data_value, characters_find)

                        if ub_result is FOUND:
                            ub_interval = i

                        ret = analyze_menu_frame(work_frame, damage_menu_data, damage_menu_roi)[0]

                        if ret is True:
                            ret, end_frame = video.read()

                            if ret is False:
                                break

                            ret = analyze_damage_frame(end_frame, damage_data_roi, tmp_damage)
                            if ret is True:
                                total_damage = "総ダメージ " + ''.join(tmp_damage)
                            else:
                                ret = analyze_damage_frame(end_frame, DAMAGE_DATA_ROI, tmp_damage)
                                if ret is True:
                                    total_damage = "総ダメージ " + ''.join(tmp_damage)

                            break

    video.release()
    clear_path(movie_path)

    # TLに対する後処理
    debuff_value = ac.make_ub_value_list(ub_data_value, characters_find)

    time_result = tm.time() - start_time
    time_data.append("動画時間 : {:.3f}".format(frame_count / frame_rate) + "  sec")
    time_data.append("処理時間 : {:.3f}".format(time_result) + "  sec")

    return ub_data, time_data, total_damage, debuff_value, NO_ERROR


def edit_frame(frame):
    """
    フレーム前処理

    下記を行う
    ・グレースケール
    ・閾値による2値化
    ・色調反転

    """
    work_frame = frame

    # グレースケール
    work_frame = cv2.cvtColor(work_frame, cv2.COLOR_RGB2GRAY)
    # 2値化
    work_frame = cv2.threshold(work_frame, 200, 255, cv2.THRESH_BINARY)[1]
    # 反転
    work_frame = cv2.bitwise_not(work_frame)

    return work_frame


def analyze_ub_frame(frame, roi, time_min, time_10sec, time_sec, ub_data, ub_data_value, characters_find):
    """
    UB検出

    parameter
    ======================
    frame: frame
        対象フレーム
    roi: roi
        対象の矩形(x1, y1, x2, y2)
    time_min: string
        分桁
    time_10sec: string
        10秒桁
    time_sec: string
        1秒桁
    ub_data: UBモデル
        UBテンプレート
    characters_find: list
        検出キャラクター

    return
    ==================
    string: 一致したした場合：数値文字列 or 未一致の場合：現在値
    """
    analyze_frame = frame[roi[1]:roi[3], roi[0]:roi[2]]

    characters_num = len(characters)

    if len(characters_find) < 5:
        # キャラクター5人を見つけるまで、すべてのキャラクターのUB判定を行う。
        for j in range(characters_num):
            result_temp = cv2.matchTemplate(analyze_frame, characters_data[j], cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result_temp)
            if max_val > UB_THRESH:
                ub_data.append(time_min + ":" + time_10sec + time_sec + " " + characters[j])
                ub_data_value.extend([[int(int(time_min) * 60 + int(time_10sec) * 10 + int(time_sec)), int(j)]])
                if j not in characters_find:
                    characters_find.append(j)

                return FOUND
    else:
        # 5人見つかった場合は、そのキャラのみのUB判定で時間を省略する
        for j in range(5):
            # 5キャラのみの探索
            result_temp = cv2.matchTemplate(analyze_frame, characters_data[characters_find[j]], cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result_temp)
            if max_val > UB_THRESH:
                ub_data.append(time_min + ":" + time_10sec + time_sec + " " + characters[characters_find[j]])
                ub_data_value.extend([[(int(time_min) * 60 + int(time_10sec) * 10 + int(time_sec)),
                                       characters_find[j]]])

                return FOUND

    return NOT_FOUND


def analyze_timer_frame(frame, roi, data_num, time_data):
    """
    残り時間検出

    下記の検出に利用する
    ・1分桁
    ・10秒桁
    ・1秒桁

    parameter
    ======================
    frame: frame
        対象フレーム
    roi: roi
        対象の矩形(x1, y1, x2, y2)
    data_num: int
        数値の個数 (分：2 (0~1) 10秒:6 (0~5) 1秒：10 (0~9))
    time_data: string
        現在値

    return
    ==================
    string: 一致したした場合：数値文字列 or 未一致の場合：現在値
    """
    analyze_frame = frame[roi[1]:roi[3], roi[0]:roi[2]]

    for j in range(data_num):
        result_temp = cv2.matchTemplate(analyze_frame, sec_data[j], cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result_temp)
        if max_val > TIMER_THRESH:
            return numbers[j]

    return time_data


def analyze_menu_frame(frame, menu, roi):
    """
    メニューフレーム判定

    parameter
    ======================
    frame: frame
        対象フレーム
    menu: ndarray
        メニューテンプレート
    roi: roi
        対象の矩形(x1, y1, x2, y2)
    
    return
    ======================
    boolean: 検出：true 未検出: false, loc
    """
    analyze_frame = frame[roi[1]:roi[3], roi[0]:roi[2]]

    result_temp = cv2.matchTemplate(analyze_frame, menu, cv2.TM_CCOEFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result_temp)
    if max_val > MENU_THRESH:
        return True, max_loc

    return False, None


def analyze_damage_frame(frame, roi, damage):
    """
    ダメージフレーム数値検出

    parameter
    ======================
    frame: frame
        対象フレーム
    menu: ndarray
        ダメージテンプレート
    roi: roi
        対象の矩形(x1, y1, x2, y2)
    
    return
    ======================
    string: ダメージ数値
    """
    analyze_frame = frame[roi[1]:roi[3], roi[0]:roi[2]]

    analyze_frame = cv2.cvtColor(analyze_frame, cv2.COLOR_BGR2HSV)
    analyze_frame = cv2.inRange(analyze_frame, np.array([10, 120, 160]), np.array([40, 255, 255]))

    ret = False
    damage_num = len(damage)
    number_num = len(numbers)

    for i in range(damage_num):
        check_roi = DAMAGE_NUMBER_ROI[i]
        check_frame = analyze_frame[check_roi[1]:check_roi[3], check_roi[0]:check_roi[2]]
        tmp_damage = [0, NOT_FOUND]
        damage[i] = "?"
        for j in range(number_num):
            result_temp = cv2.matchTemplate(check_frame, damage_data[j], cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result_temp)
            if max_val > DAMAGE_THRESH:
                if max_val > tmp_damage[1]:
                    tmp_damage[0] = j
                    tmp_damage[1] = max_val
                    ret = True

        if tmp_damage[1] != NOT_FOUND:
            damage[i] = str(tmp_damage[0])

    return ret


def analyze_anna_icon_frame(frame, roi, characters_find):
    # アンナの有無を確認 UBを使わない場合があるため
    analyze_frame = frame[roi[1]:roi[3], roi[0]:roi[2]]

    icon_num = len(icon_data)

    for j in range(icon_num):
        result_temp = cv2.matchTemplate(analyze_frame, icon_data[j], cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result_temp)
        if max_val > ICON_THRESH:
            characters_find.append(characters.index('アンナ'))

    return


app = Flask(__name__)
app.config.from_object(__name__)
app.config['SECRET_KEY'] = 'zJe09C5c3tMf5FnNL09C5e6SAzZuY'
app.config['JSON_AS_ASCII'] = False

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        url = (request.form["Url"])

        # urlからid部分の抽出
        youtube_id = al.get_youtube_id(url)
        if youtube_id is False:
            error = err.get_error_message(err.ERR_BAD_URL)
            return render_template("index.html", error=error)

        cache = cm.cache_check(youtube_id)

        if cache is not False:
            title, time_line, time_data, total_damage, debuff_value, past_status = cache
            if past_status % 100 // 10 == 0:
                debuff_dict, data_txt, data_url, total_damage = get_web_txt(youtube_id, title,
                                                                            time_line, debuff_value, total_damage)

                return render_template("result.html", title=title, timeLine=time_line,
                                       timeData=time_data, totalDamage=total_damage, debuffDict=debuff_dict,
                                       data_txt=data_txt, data_url=data_url)

            else:
                error = err.get_error_message(past_status)
                return render_template("index.html", error=error)

        # start download
        dl_queue_path = dl_queue_dir + str(youtube_id)
        dl_doing_path = dl_doing_dir + str(youtube_id)

        # 既にキューに登録されているか確認
        queued = os.path.exists(dl_queue_path)
        if not queued:  # 既にダウンロード待機中ではない場合、ダウンロード待機キューに登録
            cm.queue_append(dl_queue_path)
            # キューが回ってきたか確認し、来たらダウンロード実行
            while True:
                if not cm.is_path_exists(dl_doing_path) and cm.is_path_current(dl_queue_path):
                    break

                timeout = cm.watchdog_download(youtube_id, 5)  # 5分間タイムアウト監視

                if timeout:
                    cm.clear_path(dl_queue_path)
                    error = "動画の解析待ちでタイムアウトが発生しました。再実行をお願いします。"
                    return render_template("index.html", error=error)

                tm.sleep(1)

        else:  # ダウンロード待機中の場合エラーメッセージ表示
            cm.clear_path(dl_queue_path)
            error = "同一の動画が解析中です。時間を置いて再実行をお願いします。"
            return render_template("index.html", error=error)

        path, title, length, thumbnail, url_result = al.search(youtube_id)
        cm.clear_path(dl_queue_path)

        if url_result % 100 // 10 == 2:
            error = err.get_error_message(url_result)
            cm.save_cache(youtube_id, title, False, False, False, False, url_result)
            return render_template("index.html", error=error)

        session["path"] = path
        session["title"] = title
        session["youtube_id"] = youtube_id
        length = int(int(length) / 8) + 3

        return render_template("analyze.html", title=title, length=length, thumbnail=thumbnail)

    elif request.method == "GET":
        if "v" in request.args:  # ?v=YoutubeID 形式のGETであればリザルト返却
            youtube_id = request.args.get("v")
            if re.fullmatch(r"^([a-zA-Z0-9_-]{11})$", youtube_id):
                cache = cm.cache_check(youtube_id)
                if cache is not False:
                    title, time_line, time_data, total_damage, debuff_value, past_status = cache
                    if past_status % 100 // 10 == 0:
                        debuff_dict, data_txt, data_url, total_damage = get_web_txt(youtube_id, title,
                                                                                    time_line, debuff_value,
                                                                                    total_damage)

                        return render_template("result.html", title=title, timeLine=time_line,
                                               timeData=time_data, totalDamage=total_damage, debuffDict=debuff_dict,
                                               data_txt=data_txt, data_url=data_url)

                    else:
                        error = err.get_error_message(past_status)
                        return render_template("index.html", error=error)

                else:  # キャッシュが存在しない場合は解析
                    # start download
                    dl_queue_path = dl_queue_dir + str(youtube_id)
                    dl_doing_path = dl_doing_dir + str(youtube_id)

                    # 既にキューに登録されているか確認
                    queued = os.path.exists(dl_queue_path)
                    if not queued:  # 既にダウンロード待機中ではない場合、ダウンロード待機キューに登録
                        cm.queue_append(dl_queue_path)
                        # キューが回ってきたか確認し、来たらダウンロード実行
                        while True:
                            if not cm.is_path_exists(dl_doing_path) and cm.is_path_current(dl_queue_path):
                                break

                            timeout = cm.watchdog_download(youtube_id, 5)  # 5分間タイムアウト監視

                            if timeout:
                                cm.clear_path(dl_queue_path)
                                error = "動画の解析待ちでタイムアウトが発生しました。再実行をお願いします。"
                                return render_template("index.html", error=error)

                            tm.sleep(1)

                    else:  # ダウンロード待機中の場合エラーメッセージ表示
                        cm.clear_path(dl_queue_path)
                        error = "同一の動画が解析中です。時間を置いて再実行をお願いします。"
                        return render_template("index.html", error=error)

                    path, title, length, thumbnail, url_result = al.search(youtube_id)
                    cm.clear_path(dl_queue_path)

                    if url_result % 100 // 10 == 2:
                        error = err.get_error_message(url_result)
                        cm.save_cache(youtube_id, title, False, False, False, False, url_result)
                        return render_template("index.html", error=error)

                    session["path"] = path
                    session["title"] = title
                    session["youtube_id"] = youtube_id
                    length = int(int(length) / 8) + 3

                    return render_template("analyze.html", title=title, length=length, thumbnail=thumbnail)

            else:  # prilog.jp/(YoutubeID)に該当しないリクエスト
                error = "不正なリクエストです"
                return render_template("index.html", error=error)
            
        else:
            path = session.get("path")
            session.pop("path", None)
            session.pop("title", None)
            session.pop("youtube_id", None)

            error = None
            if str(path).isdecimal():
                error = err.get_error_message(path)

            elif path is not None:
                cm.clear_path(path)

            return render_template("index.html", error=error)


@app.route("/analyze", methods=["GET", "POST"])
def analyze():
    path = session.get("path")
    title = session.get("title")
    youtube_id = session.get("youtube_id")
    session.pop("path", None)

    if request.method == "GET" and path is not None:
        # TL解析
        time_line, time_data, total_damage, debuff_value, status = al.analyze_movie(path)

        # キャッシュ保存
        status = cm.save_cache(youtube_id, title, time_line, False, total_damage, debuff_value, status)

        if status % 100 // 10 == 0:
            # 解析が正常終了ならば結果を格納
            session["time_line"] = time_line
            session["time_data"] = time_data
            session["total_damage"] = total_damage
            session["debuff_value"] = debuff_value
            return render_template("analyze.html")
        else:
            session["path"] = status
            return render_template("analyze.html")
    else:
        return redirect("/")


@app.route("/result", methods=["GET", "POST"])
def result():
    title = session.get("title")
    time_line = session.get("time_line")
    time_data = session.get("time_data")
    total_damage = session.get("total_damage")
    debuff_value = session.get("debuff_value")
    youtube_id = session.get("youtube_id")
    session.pop("title", None)
    session.pop("time_line", None)
    session.pop("time_data", None)
    session.pop("total_damage", None)
    session.pop("debuff_value", None)
    session.pop("youtube_id", None)

    if request.method == "GET" and time_line is not None:
        debuff_dict, data_txt, data_url, total_damage = get_web_txt(youtube_id, title,
                                                                    time_line, debuff_value, total_damage)

        return render_template("result.html", title=title, timeLine=time_line,
                               timeData=time_data, totalDamage=total_damage, debuffDict=debuff_dict,
                               data_txt=data_txt, data_url=data_url)
    else:
        return redirect("/")


@app.route("/download", methods=["GET", "POST"])
def download():
    if request.method == "GET":
        return render_template("download.html")
    else:
        return redirect("/")


@app.route("/rest", methods=["GET", "POST"])
def rest():
    if request.method == "GET":
        return render_template("rest.html")
    else:
        return redirect("/")


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
    queue_path = queue_dir + str(youtube_id)
    pending_path = pending_dir + str(youtube_id)
    dl_queue_path = dl_queue_dir + str(youtube_id)
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
        # 既にキューに登録されているか確認
        queued = os.path.exists(queue_path)
        if not queued:  # 既に解析中ではない場合、解析キューに登録
            cm.queue_append(queue_path)
            # キューが回ってきたか確認し、来たら解析実行
            while True:
                cm.watchdog(youtube_id, is_parent, 30, err.ERR_QUEUE_TIMEOUT)
                rest_pending = cm.is_path_exists(pending_path)
                rest_queue = cm.is_path_current(queue_path)
                web_download = cm.is_path_exists(dl_queue_path)
                if not rest_pending and rest_queue and not web_download:
                    analyzer_path = f'python exec_analyze.py {url}'
                    cm.pending_append(pending_path)
                    subprocess.Popen(analyzer_path.split())
                    is_parent = True
                    break

                tm.sleep(1)

        while True:  # キューが消えるまで監視
            queued = os.path.exists(queue_path)
            if queued:
                if is_parent:
                    # 親ならばpendingを監視
                    cm.watchdog(youtube_id, is_parent, 5, err.ERR_ANALYZE_TIMEOUT)
                else:
                    # 子ならばqueueを監視
                    cm.watchdog(youtube_id, is_parent, 36, err.ERR_QUEUE_TIMEOUT)
                tm.sleep(1)
                continue
            else:  # 解析が完了したら、そのキャッシュJSONを返す
                cache = cm.cache_check(youtube_id)
                if cache is not False:
                    title, time_line, time_data, total_damage, debuff_value, past_status = cache
                    rest_result = get_rest_result(title, time_line, time_data, total_damage, debuff_value)

                    status = past_status
                    break
                else:  # キャッシュ未生成の場合
                    # キャッシュを書き出してから解析キューから削除されるため、本来起こり得ないはずのエラー
                    status = err.ERR_TMP_UNEXPECTED
                    break

    ret["result"] = rest_result
    ret["msg"] = err.get_error_message(status)
    ret["status"] = status
    return jsonify(ret)


if __name__ == "__main__":
    app.run()
