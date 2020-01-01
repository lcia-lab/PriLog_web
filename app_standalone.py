#!/home/prilog/.pyenv/versions/3.6.9/bin/python
# -*- coding: utf-8 -*-
from flask import Flask, render_template, request, flash, Response, abort, session, redirect
from wtforms import Form, StringField, SubmitField, validators, ValidationError
import numpy as np
import os
import re
from pytube import YouTube
import sys
import time as tm
sys.path.append('/home/prilog/lib')
import cv2
import os, tkinter, tkinter.filedialog, tkinter.messagebox
import sys


characters_data = np.load("model/UB_name.npy")

sec_data = np.load("model/timer_sec.npy")

characters = [
    "アオイ",
    "アオイ(編入生)",
    "アカリ",
    "アキノ",
    "アヤネ",
    "アヤネ(クリスマス)",
    "アユミ",
    "アリサ",
    "アン",
    "アンナ",
    "イオ",
    "イオ",      # ☆6以降
    "イオ(サマー)",
    "イリヤ",
    "イリヤ(クリスマス)",
    "エミリア",
    "エリコ",
    "エリコ(バレンタイン)",
    "カオリ",
    "カオリ(サマー)",
    "カスミ",
    "カヤ",
    "キャル",
    "キャル",      # ☆6以降
    "キャル(サマー)",
    "キョウカ",
    "キョウカ(ハロウィン)",
    "クウカ",
    "クウカ(オーエド)",
    "クリスティーナ",
    "クリスティーナ(クリスマス)",
    "クルミ",
    "クルミ(クリスマス)",
    "グレア",
    "クロエ",
    "コッコロ",
    "コッコロ",      # ☆6以降
    "コッコロ(サマー)",
    "サレン",
    "サレン(サマー)",
    "ジータ",
    "シオリ",
    "シズル",
    "シズル(バレンタイン)",
    "シノブ",
    "シノブ(ハロウィン)",
    "ジュン",
    "スズナ",
    "スズナ(サマー)",
    "スズメ",
    "スズメ(サマー)",
    "タマキ",
    "タマキ(サマー)",
    "チカ",
    "チカ(クリスマス)",
    "ツムギ",
    "トモ",
    "ナナカ",
    "ニノン",
    "ニノン(オーエド)",
    "ネネカ",
    "ノゾミ",
    "ノゾミ(クリスマス)",
    "ハツネ",
    "ヒヨリ",
    "ヒヨリ(ニューイヤー)",
    "ペコリーヌ",
    "ペコリーヌ",      # ☆6以降
    "ペコリーヌ(サマー)",
    "マコト",
    "マコト(サマー)",
    "マツリ",
    "マヒル",
    "マホ",
    "マホ(サマー)",
    "ミサキ",
    "ミサキ(ハロウィン)",
    "ミサト",
    "ミソギ",
    "ミソギ(ハロウィン)",
    "ミツキ",
    "ミフユ",
    "ミフユ(サマー)",
    "ミミ",
    "ミミ(ハロウィン)",
    "ミヤコ",
    "ミヤコ(ハロウィン)",
    "ムイミ",
    "モニカ",
    "ユイ",
    "ユイ(ニューイヤー)",
    "ユカリ",
    "ユキ",
    "ヨリ",
    "ラム",
    "リノ",
    "リノ",      # ☆6以降
    "リマ",
    "リマ",      # ☆6以降
    "リン",
    "ルゥ",
    "ルカ",
    "ルナ",
    "レイ",
    "レイ(ニューイヤー)",
    "レム",
]

timer = [
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

FRAME_COLS = 1280
FRAME_ROWS = 720

UB_ROI = (440, 100, 860, 130)
MIN_ROI = (1072, 24, 1090, 42)
TENSEC_ROI = (1090, 24, 1108, 42)
ONESEC_ROI = (1104, 24, 1122, 42)

TIMER_MIN = 2
TIMER_TENSEC = 1
TIMER_SEC = 0

UB_THRESH = 0.6
TIMER_THRESH = 0.75

FOUND = 1
NOT_FOUND = 0


def edit_frame(frame):
    work_frame_a = frame

#    work_frame = cv2.resize(work_frame, dsize=(FRAME_COLS, FRAME_ROWS))
    work_frame_a = cv2.cvtColor(work_frame_a, cv2.COLOR_RGB2GRAY)
    ret_a, work_frame_a = cv2.threshold(work_frame_a, 200, 255, cv2.THRESH_BINARY)
    work_frame_a = cv2.bitwise_not(work_frame_a)

    return work_frame_a


def analyze_ub_frame(frame, time_min, time_10sec, time_sec, characters_find):
    analyze_frame = frame[UB_ROI[1]:UB_ROI[3], UB_ROI[0]:UB_ROI[2]]

    characters_num = len(characters)

    if len(characters_find) < 5:
        for j in range(characters_num):
            result_temp = cv2.matchTemplate(analyze_frame, characters_data[j], cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result_temp)
            if max_val > UB_THRESH:
                print(time_min + ":" + time_10sec + time_sec + "	" + characters[j])
                if j not in characters_find:
                    characters_find.append(j)
                return FOUND

    else:
        for j in range(5):
            result_temp = cv2.matchTemplate(analyze_frame, characters_data[characters_find[j]], cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result_temp)
            if max_val > UB_THRESH:
                print(time_min + ":" + time_10sec + time_sec + "	" + characters[characters_find[j]])
                return FOUND

    return NOT_FOUND


def analyze_timer_frame(frame, roi, data_num, time_data):
    analyze_frame = frame[roi[1]:roi[3], roi[0]:roi[2]]

    """
    cv2.namedWindow('window')
    cv2.imshow('window', analyze_frame)
    cv2.waitKey(0)
    cv2.destroyAllWindows()
    """

    for j in range(data_num):
        result_temp = cv2.matchTemplate(analyze_frame, sec_data[j], cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result_temp)
        if max_val > TIMER_THRESH:
            return timer[j]

    return time_data


root = tkinter.Tk()
root.withdraw()

fTyp = [("", "*.mp4;*.avi;*.mov;*.m4a;*.flv")]

iDir = os.path.abspath(os.path.dirname(__file__))
file = tkinter.filedialog.askopenfilename(filetypes=fTyp, initialdir=iDir)

if file == "":
    print("No video source found")
    sys.exit(1)

movie_path = file
startTime = tm.time()
video = cv2.VideoCapture(movie_path)

frame_count = int(video.get(7))  # フレーム数を取得
frame_rate = int(video.get(5))  # フレームレート(1フレームの時間単位はミリ秒)の取得

frame_width = int(video.get(3))  # フレームの幅
frame_height = int(video.get(4))  # フレームの高さ

n = 0.5  # n秒ごと*
ubInterval = 0

timeMin = "1"
timeSec10 = "3"
timeSec1 = "0"

ubData = []
characters_find = []

cap_interval = int(frame_rate * n)
skip_frame = 4 * cap_interval

if (frame_count / frame_rate) < 600:  # 10分未満の動画しか見ない
    for i in range(frame_count):  # 動画の秒数を取得し、回す
        ret = video.grab()
        if ret is False:
            break

        if i % cap_interval is 0:
            ret, work_frame = video.read()
            if ret is False:
                break
            work_frame = edit_frame(work_frame)

            if ((i - ubInterval) > skip_frame) or (ubInterval == 0):

                timeMin = analyze_timer_frame(work_frame, MIN_ROI, 2, timeMin)

                timeSec10 = analyze_timer_frame(work_frame, TENSEC_ROI, 6, timeSec10)
                timeSec1 = analyze_timer_frame(work_frame, ONESEC_ROI, 10, timeSec1)

                result = analyze_ub_frame(work_frame, timeMin, timeSec10, timeSec1, characters_find)

                if result is FOUND:
                    ubInterval = i

video.release()
time_after = tm.time() - startTime
print("\n動画時間 : {:.3f}".format(frame_count / frame_rate) + "  sec")
print("処理時間 : {:.3f}".format(time_after) + "  sec")